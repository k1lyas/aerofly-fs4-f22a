# Import a DCS .edm model into Blender 5 (geometry + UVs + diffuse textures),
# save a .blend and render preview images.
#
#   Blender --background --factory-startup --python edm_to_blend.py -- \
#       <ioEDM io_EDM dir> <model.edm> <textures dir> <out.blend> <render prefix>
#
# Uses the ioEDM `edm` package only as a file parser; all Blender-side code is here.
#
# Optional environment variables:
#   EDM_ARGS="0=1,3=1,5=1"   animation argument values for the pose (default: all 0)
#   EDM_ANIM_JSON=path        write world-space pivots/axes of animated nodes
import sys, os, math, time, json
import bpy, bmesh
from mathutils import Matrix, Vector, Quaternion

args = sys.argv[sys.argv.index('--') + 1:]
IOEDM, EDM_PATH, TEX_DIR, OUT_BLEND, RENDER_PREFIX = args[:5]
sys.path.insert(0, IOEDM)
from edm import EDMFile
from edm.types import TransformNode, ArgAnimationNode, ArgVisibilityNode, RenderNode, SkinNode, Bone

# Some EDM v10 files (e.g. the Su-35 mod) split a render node between several parents per vertex instead of by
# index range: the parent ranges are all 0/-1 and the 4th position component is the index into the parent list.
_split_by_range = RenderNode.split


def _split_render_node(self):
    pd = self.parentData
    if not pd or len(pd) < 2 or pd[-1][-2] == len(self.indexData):
        return _split_by_range(self)
    tri_parent = [int(round(self.vertexData[self.indexData[i]][3])) for i in range(0, len(self.indexData), 3)]
    children = []
    for k, (parent, _to, damage) in enumerate(pd):
        idx = [v for t, p in enumerate(tri_parent) if p == k for v in self.indexData[3 * t:3 * t + 3]]
        if not idx:
            continue
        node = RenderNode()
        node.version, node.props, node.material = self.version, self.props, self.material
        node.name, node.name_unknown = '{}_{}'.format(self.name, k), True
        node.parent, node.damage_argument = parent, damage
        node.indexData, node.vertexData = idx, self.vertexData
        children.append(node)
    return children


RenderNode.split = _split_render_node

# EDM is Y-up; Blender is Z-up
EDM_TO_BLENDER = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))

ARG_VALUES = {int(k): float(v) for k, v in
              (kv.split('=') for kv in os.environ.get('EDM_ARGS', '').split(',') if kv)}


def sample_keys(keys, t, lerp):
    """Interpolate keyframes (sorted by frame) at argument value t."""
    if t <= keys[0].frame:
        return keys[0].value
    for a, b in zip(keys, keys[1:]):
        if a.frame <= t <= b.frame:
            u = 0.0 if b.frame == a.frame else (t - a.frame) / (b.frame - a.frame)
            return lerp(a.value, b.value, u)
    return keys[-1].value


def anim_offsets(node):
    """Animated translation vector and rotation quaternion for the current ARG_VALUES."""
    pos = Vector((0.0, 0.0, 0.0))
    rot = Quaternion((1.0, 0.0, 0.0, 0.0))
    for arg, keys in node.posData:
        v = sample_keys(keys, ARG_VALUES.get(arg, 0.0), lambda a, b, u: Vector(a).lerp(Vector(b), u))
        pos = pos + Vector(v)
    for arg, keys in node.rotData:
        q = sample_keys(keys, ARG_VALUES.get(arg, 0.0), lambda a, b, u: Quaternion(a).slerp(Quaternion(b), u))
        rot = rot @ Quaternion(q)
    return pos, rot


def node_local(node):
    """Local transform of a transform-graph node for the current pose, in EDM space:
    matrix * T(position) * T(anim_pos) * R(quat_1) * R(anim_rot) * S(scale)"""
    if isinstance(node, TransformNode):
        return Matrix(node.matrix)
    if isinstance(node, Bone):
        return Matrix(node.data[0])
    if isinstance(node, ArgAnimationNode):
        b = node.base
        apos, arot = anim_offsets(node)
        scale = Matrix.Diagonal(Vector(tuple(b.scale) + (1.0,)))
        return Matrix(b.matrix) @ Matrix.Translation(Vector(b.position) + apos) @ \
            Quaternion(b.quat_1).to_matrix().to_4x4() @ arot.to_matrix().to_4x4() @ scale
    return Matrix.Identity(4)


def ancestors(nodes, node):
    """Transform-graph ancestors of a node, nearest first (including the node itself)."""
    chain, seen = [], set()
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        chain.append(node)
        parent = getattr(node, 'parent', None)
        node = resolve(nodes, parent) if parent is not None else None
    return chain


def is_visible(chain):
    """Evaluate DCS visibility nodes for the current ARG_VALUES (default 0)."""
    for n in chain:
        if isinstance(n, ArgVisibilityNode):
            for arg, ranges in n.visData:
                v = ARG_VALUES.get(arg, 0.0)
                if not any(lo <= v < hi for lo, hi in ranges):
                    return False
    return True


def anim_tags(nodes, chain):
    """Indices and argument numbers of animated ancestors."""
    idx, args = [], set()
    for n in chain:
        if isinstance(n, ArgAnimationNode):
            idx.append(nodes.index(n))
            args.update(a for a, _ in n.rotData)
            args.update(a for a, _ in n.posData)
    return idx, sorted(args)


def anim_pivots(nodes, cache):
    """World-space (Blender/Aerofly axes) pivot and rotation axis of every animated node."""
    out = []
    for i, n in enumerate(nodes):
        if not isinstance(n, ArgAnimationNode):
            continue
        b = n.base
        parent = getattr(n, 'parent', None)
        pw = world_matrix(nodes, resolve(nodes, parent), cache) if parent is not None else Matrix.Identity(4)
        apos, _ = anim_offsets(n)
        frame = EDM_TO_BLENDER @ pw @ Matrix(b.matrix) @ Matrix.Translation(Vector(b.position) + apos) @ \
            Quaternion(b.quat_1).to_matrix().to_4x4()
        entry = {'index': i, 'name': n.name, 'pivot': list(frame.translation), 'rot': [], 'pos': []}
        for arg, keys in n.rotData:
            qmax = max((Quaternion(k.value) for k in keys), key=lambda q: q.angle)
            axis = (frame.to_3x3() @ qmax.axis).normalized() if qmax.angle > 1e-5 else Vector()
            entry['rot'].append({'arg': arg, 'axis': list(axis),
                                 'keys': [[k.frame, math.degrees(Quaternion(k.value).angle)] for k in keys]})
        for arg, keys in n.posData:
            entry['pos'].append({'arg': arg, 'keys': [[k.frame] + list(frame.to_3x3() @ Vector(k.value)) for k in keys]})
        out.append(entry)
    return out


def resolve(nodes, ref):
    return nodes[ref] if isinstance(ref, int) else ref


def world_matrix(nodes, node, cache):
    key = id(node)
    if key in cache:
        return cache[key]
    parent = getattr(node, 'parent', None)
    parent_m = Matrix.Identity(4)
    if parent is not None and parent is not node:
        p = resolve(nodes, parent)
        if p is not None and p is not node:
            parent_m = world_matrix(nodes, p, cache)
    m = parent_m @ node_local(node)
    cache[key] = m
    return m


def load_image(name):
    for ext in ('.dds', '.png', '.tga', '.bmp'):
        p = os.path.join(TEX_DIR, name + ext)
        if os.path.exists(p):
            try:
                return bpy.data.images.load(p, check_existing=True)
            except RuntimeError as e:
                print("image load failed:", p, e)
                return None
    return None


_materials = {}


def blender_material(edm_mat):
    name = getattr(edm_mat, 'name', None) or 'edm_material'
    tex_names = [getattr(t, 'name', None) for t in getattr(edm_mat, 'textures', [])]
    key = (name, tuple(tex_names))
    if key in _materials:
        return _materials[key]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    diffuse = next((t for t in getattr(edm_mat, 'textures', []) if getattr(t, 'index', None) == 0), None)
    img = load_image(diffuse.name) if diffuse is not None else None
    if img is not None:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = img
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    _materials[key] = mat
    return mat


def build_mesh(rn, fmt):
    verts = rn.vertexData
    idx = rn.indexData
    used = sorted(set(idx))
    remap = {old: new for new, old in enumerate(used)}
    pos_i = fmt.position_indices
    uv_i = fmt.texture_indices[:2] if fmt.ntexture >= 2 else []

    bm = bmesh.new()
    bverts = [bm.verts.new(tuple(verts[i][k] for k in pos_i)) for i in used]
    bm.verts.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.verify() if uv_i else None
    for t in range(0, len(idx) - 2, 3):
        tri = (idx[t], idx[t + 1], idx[t + 2])
        try:
            face = bm.faces.new([bverts[remap[i]] for i in tri])
        except ValueError:
            continue  # duplicate/degenerate face
        if uv_layer is not None:
            for loop, vi in zip(face.loops, tri):
                u, v = verts[vi][uv_i[0]], verts[vi][uv_i[1]]
                loop[uv_layer].uv = (u, 1.0 - v)
    for face in bm.faces:
        face.smooth = True
    me = bpy.data.meshes.new(rn.name or 'edm_mesh')
    bm.to_mesh(me)
    bm.free()
    # use the authored DCS vertex normals instead of recomputed (faceted) ones
    nrm_i = fmt.normal_indices
    if len(nrm_i) == 3:
        normals = []
        for i in used:
            n = Vector(tuple(verts[i][k] for k in nrm_i))
            normals.append(n.normalized() if n.length > 1e-8 else Vector((0.0, 0.0, 1.0)))
        me.normals_split_custom_set_from_vertices(normals)
    return me


class SkinPart:
    """Rigid piece of a skinned DCS mesh: the triangles whose dominant bone is `parent`, posed with that bone.
    Bone indices are the 4 bytes of the position w component (offset by one into SkinNode.bones, whose first
    entry is the mesh's own bind node), weights are the 4-float channel 21."""

    def __init__(self, name, material, parent, vertexData, indexData):
        self.name, self.material, self.parent = name, material, parent
        self.vertexData, self.indexData = vertexData, indexData


def skin_parts(nodes, sn, cache):
    import struct
    fmt = sn.material.vertex_format
    wi = fmt.data and sum(fmt.data[:21])  # first column of channel 21 (bone weights)
    verts = sn.vertexData
    groups = {}
    for t in range(0, len(sn.indexData) - 2, 3):
        score = {}
        for vi in sn.indexData[t:t + 3]:
            v = verts[vi]
            bones = struct.pack('<f', v[3])
            for k in range(4):
                w = v[wi + k]
                if w > 0:
                    score[bones[k]] = score.get(bones[k], 0.0) + w
        b = max(score, key=score.get) if score else 0
        groups.setdefault(b, []).extend(sn.indexData[t:t + 3])
    rest_args = dict(ARG_VALUES)
    parts = []
    for b, idx in sorted(groups.items()):
        bone = sn.bones[min(b + 1, len(sn.bones) - 1)]
        # pose relative to the bind pose (all arguments 0): W(pose) * W(bind)^-1
        ARG_VALUES.clear()
        w_bind = world_matrix(nodes, bone, {})
        ARG_VALUES.update(rest_args)
        # vertices go into the bone's bind frame; the object is then placed with the bone's posed world matrix
        to_local = w_bind.inverted()
        r = to_local.to_3x3()
        pi, ni = fmt.position_indices, fmt.normal_indices
        new = {}
        for vi in set(idx):
            v = list(verts[vi])
            p = to_local @ Vector([v[k] for k in pi])
            for k, x in zip(pi, p):
                v[k] = x
            if len(ni) == 3:
                n = r @ Vector([v[k] for k in ni])
                for k, x in zip(ni, n):
                    v[k] = x
            new[vi] = v
        order = sorted(new)
        remap = {old: k for k, old in enumerate(order)}
        part = SkinPart('%s_b%d' % (sn.name, b), sn.material, bone,
                        [new[o] for o in order], [remap[i] for i in idx])
        # visibility (e.g. the damaged-wing variants, shown only for damage args >= 1) hangs above the mesh's own
        # bind node bones[0], not above the bone that poses the piece
        part.vis_node = sn.bones[0]
        parts.append(part)
    return parts


def main():
    t0 = time.time()
    f = EDMFile(EDM_PATH)
    nodes = f.nodes
    print("parsed %s in %.1fs: %d nodes, %d render nodes" % (os.path.basename(EDM_PATH), time.time() - t0, len(nodes), len(f.renderNodes)))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = bpy.data.collections.new(os.path.splitext(os.path.basename(EDM_PATH))[0])
    bpy.context.scene.collection.children.link(coll)

    hidden = bpy.data.collections.new('hidden_by_dcs_visibility')
    bpy.context.scene.collection.children.link(hidden)
    hidden.hide_render = True
    cache = {}
    made = 0
    node_index = {id(n): i for i, n in enumerate(nodes)}
    render_nodes = []
    for rn in f.renderNodes:
        render_nodes.extend(skin_parts(nodes, rn, cache) if isinstance(rn, SkinNode) else [rn])
    for rn in render_nodes:
        mat = rn.material
        fmt = getattr(mat, 'vertex_format', None)
        if fmt is None or not rn.indexData:
            continue
        me = build_mesh(rn, fmt)
        me.materials.append(blender_material(mat))
        ob = bpy.data.objects.new(rn.name or 'edm_obj', me)
        parent = resolve(nodes, rn.parent) if getattr(rn, 'parent', None) is not None else None
        local_world = world_matrix(nodes, parent, cache) if parent is not None else Matrix.Identity(4)
        ob.matrix_world = EDM_TO_BLENDER @ local_world
        chain = ancestors(nodes, parent)
        idx, anim_args = anim_tags(nodes, chain)
        ob["edm_anim_nodes"] = ",".join(map(str, idx))
        ob["edm_anim_args"] = ",".join(map(str, anim_args))
        ob["edm_material"] = getattr(mat, 'name', '')
        ob["edm_mat_kind"] = getattr(mat, 'material_name', '')
        try:
            ob["edm_normal_value"] = float(getattr(mat, 'uniforms', {}).get('normalMapValue', 1.0))
        except (AttributeError, TypeError, ValueError):
            ob["edm_normal_value"] = 1.0
        ob["edm_textures"] = json.dumps({int(t.index): t.name for t in getattr(mat, 'textures', [])})
        ob["edm_parent_node"] = node_index.get(id(parent), -1)
        vis_node = getattr(rn, 'vis_node', None)
        visible = is_visible(chain) and (vis_node is None or is_visible(ancestors(nodes, resolve(nodes, vis_node))))
        (coll if visible else hidden).objects.link(ob)
        made += 1
    print("created %d objects in %.1fs (args %s)" % (made, time.time() - t0, ARG_VALUES))
    if os.environ.get('EDM_ANIM_JSON'):
        with open(os.environ['EDM_ANIM_JSON'], 'w') as fh:
            json.dump(anim_pivots(nodes, cache), fh, indent=1)

    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    render_previews(coll)
    print("done in %.1fs" % (time.time() - t0))


def render_previews(coll):
    scene = bpy.context.scene
    objs = [o for o in coll.objects if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center, size = (lo + hi) / 2, (hi - lo)
    print("bounds size (m): %.2f x %.2f x %.2f" % tuple(size))

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.color_type = 'TEXTURE'
    scene.display.shading.light = 'STUDIO'
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
    scene.world = bpy.data.worlds.new('w')
    radius = max(size) * 1.1
    cam_data = bpy.data.cameras.new('cam')
    cam_data.clip_end = radius * 10
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    views = {
        'front34': (Vector((1.0, -1.0, 0.45)), 50),
        'side': (Vector((0.0, -1.0, 0.0)), 50),
        'top': (Vector((0.0, 0.0, 1.0)), 50),
        'rear34': (Vector((-1.0, 1.0, 0.35)), 50),
    }
    for name, (d, lens) in views.items():
        cam_data.lens = lens
        cam.location = center + d.normalized() * radius * 1.6
        cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y' if name != 'top' else 'Y').to_euler()
        scene.render.filepath = "%s_%s.png" % (RENDER_PREFIX, name)
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
