"""Merge a separate DCS cockpit model (Cockpit_*.edm) into the imported exterior scene.

    Blender --background <name>_pose.blend --python merge_cockpit.py -- <io_EDM dir> <cockpit.edm> <textures dir> \
        <x,y,z offset in Aerofly axes> [<out.blend>]

DCS draws either the exterior model or the cockpit model; Aerofly draws everything at once, so the cockpit is added
to the exterior collection, shifted by the DCS CockpitLocalPoint (Views.lua; DCS x, y up -> Aerofly x, z up).
Objects are named CP_<name>. The DCS animation tags are kept in edm_cockpit_nodes / edm_cockpit_args; objects moved
by an argument the aircraft drives (DRIVERS key COCKPIT_ARG_BASE + cockpit argument) get edm_anim_nodes /
edm_anim_args shifted by COCKPIT_NODE_BASE / COCKPIT_ARG_BASE, apart from the exterior's (anim_tables.py samples
them from the cockpit model). Objects DCS hides at argument 0 go to the
hidden collection as in edm_to_blend.py.
"""
import sys, os, json, importlib
import bpy
from mathutils import Matrix

a = sys.argv[sys.argv.index('--') + 1:]
IOEDM, EDM_PATH, TEX_DIR, OFFSET = a[:4]
OUT = a[4] if len(a) > 4 else bpy.data.filepath
sys.argv = [sys.argv[0], '--', IOEDM, EDM_PATH, TEX_DIR, '-', '-']
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edm_to_blend as E
if os.environ.get('AC_DIR'):
    sys.path.insert(0, os.environ['AC_DIR'])
C = importlib.import_module(os.environ.get('AC', 'ac_f22'))

off = [float(v) for v in OFFSET.split(',')]
f = E.EDMFile(EDM_PATH)
nodes = f.nodes
coll = next(c for c in bpy.data.collections if c.name != 'hidden_by_dcs_visibility' and c.objects)
hidden = bpy.data.collections['hidden_by_dcs_visibility']
for o in [o for o in bpy.data.objects if o.name.startswith('CP_')]:      # re-run: replace the previous merge
    bpy.data.objects.remove(o, do_unlink=True)
cache, made = {}, 0
node_index = {id(n): i for i, n in enumerate(nodes)}
render_nodes = []
for rn in f.renderNodes:
    render_nodes.extend(E.skin_parts(nodes, rn, cache) if isinstance(rn, E.SkinNode) else [rn])
for rn in render_nodes:
    mat = rn.material
    fmt = getattr(mat, 'vertex_format', None)
    if fmt is None or not rn.indexData:
        continue
    me = E.build_mesh(rn, fmt)
    me.materials.append(E.blender_material(mat))
    ob = bpy.data.objects.new('CP_' + (rn.name or 'edm_obj'), me)
    parent = E.resolve(nodes, rn.parent) if getattr(rn, 'parent', None) is not None else None
    local_world = E.world_matrix(nodes, parent, cache) if parent is not None else Matrix.Identity(4)
    ob.matrix_world = Matrix.Translation(off) @ E.EDM_TO_BLENDER @ local_world
    chain = E.ancestors(nodes, parent)
    idx, anim_args = E.anim_tags(nodes, chain)
    follow = [getattr(C, 'COCKPIT_FOLLOW', {})[a] for a in anim_args if a in getattr(C, 'COCKPIT_FOLLOW', {})]
    if follow:                                   # moves with an exterior part: take its animation chain
        ext_part = next(o for o in bpy.data.objects if not o.name.startswith('CP_') and
                        str(follow[0]) in str(o.get('edm_anim_args', '')).split(','))
        ob['edm_anim_nodes'] = ext_part['edm_anim_nodes']
        ob['edm_anim_args'] = ext_part['edm_anim_args']
    elif any(C.COCKPIT_ARG_BASE + a in C.DRIVERS for a in anim_args):
        ob['edm_anim_nodes'] = ','.join(str(C.COCKPIT_NODE_BASE + i) for i in idx)
        ob['edm_anim_args'] = ','.join(str(C.COCKPIT_ARG_BASE + a) for a in anim_args)
    else:
        ob['edm_anim_nodes'] = ''
        ob['edm_anim_args'] = ''
    ob['edm_cockpit_nodes'] = ','.join(map(str, idx))
    ob['edm_cockpit_args'] = ','.join(map(str, anim_args))
    ob['edm_source'] = 'cockpit'
    ob['edm_material'] = getattr(mat, 'name', '')
    ob['edm_mat_kind'] = getattr(mat, 'material_name', '')
    try:
        ob['edm_normal_value'] = float(getattr(mat, 'uniforms', {}).get('normalMapValue', 1.0))
    except (AttributeError, TypeError, ValueError):
        ob['edm_normal_value'] = 1.0
    ob['edm_textures'] = json.dumps({int(t.index): t.name for t in getattr(mat, 'textures', [])})
    ob['edm_parent_node'] = -1000 - node_index.get(id(parent), 0)       # kept apart from the exterior's node ids
    vis_node = getattr(rn, 'vis_node', None)
    visible = E.is_visible(chain) and (vis_node is None or E.is_visible(E.ancestors(nodes, E.resolve(nodes, vis_node))))
    (coll if visible else hidden).objects.link(ob)
    made += 1
print('merged %d cockpit objects into %s (offset %s)' % (made, coll.name, off))
# connectors (DCS indicator placement: <name>-CENTER / -DOWN / -RIGHT, button points) for export_parts.py
conn = {}
for c in f.connectors:
    p = E.resolve(nodes, c.parent) if getattr(c, 'parent', None) is not None else None
    W = Matrix.Translation(off) @ E.EDM_TO_BLENDER @ (E.world_matrix(nodes, p, cache) if p is not None else Matrix.Identity(4))
    conn[c.name] = [round(x, 5) for x in W.translation]
bpy.context.scene['cockpit_connectors'] = json.dumps(conn)
print('merged: %d cockpit connectors' % len(conn))

# Flat fans (the MFD button caps: a fan of triangles about a centre vertex) showed a dark cross along the fan edges
# in the game: coplanar faces of the materials in COCKPIT_DISSOLVE are merged (within UV islands) and triangulated
# again at export without the centre vertex; custom normals are dropped (export_parts flattens the hard edges)
import math as _m
import bmesh as _bm
dis = getattr(C, 'COCKPIT_DISSOLVE', None)
if dis:
    gone = 0
    for o in [o for o in bpy.data.objects if o.name.startswith('CP_') and o.type == 'MESH' and
              dis.search(o.get('edm_material', ''))]:
        bm = _bm.new()
        bm.from_mesh(o.data)
        n0 = len(bm.verts)
        _bm.ops.dissolve_limit(bm, angle_limit=_m.radians(2.0), use_dissolve_boundaries=False,
                               verts=bm.verts[:], edges=bm.edges[:], delimit={'UV', 'MATERIAL'})
        gone += n0 - len(bm.verts)
        for e in bm.edges:                       # hard edges stay hard without the DCS custom normals
            e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > _m.radians(30.0))
        bm.to_mesh(o.data)
        bm.free()
        if o.data.has_custom_normals:
            o.data.normals_split_custom_set([(0.0, 0.0, 0.0)] * len(o.data.loops))   # zero = default normal
    print('merged: flat fans dissolved, %d vertices removed' % gone)

# The two DCS models are never drawn together in DCS; here they are. Cockpit faces outside the exterior skin (the
# cockpit's canopy frame stood 2 cm proud of the exterior frame behind the canopy) are removed, and where the two
# models share a surface only one copy stays: facing into the cockpit the detailed cockpit face, facing out the
# exterior face (coincident same-facing triangles z-fight).
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def excluded(o):
    return bool(C.EXCLUDE_NAME.search(o.name) or C.EXCLUDE_MATERIAL.search(o.get('edm_material', '')) or
                C.EXCLUDE_KIND.search(o.get('edm_mat_kind', '')))


def world_bm(objs):
    bm = bmesh.new()
    for o in objs:
        t = bmesh.new()
        t.from_mesh(o.data)
        t.transform(o.matrix_world)
        me = bpy.data.meshes.new('tmp')
        t.to_mesh(me)
        bm.from_mesh(me)
        t.free()
        bpy.data.meshes.remove(me)
    return bm


shown = [o for o in coll.objects if o.type == 'MESH' and not excluded(o)]
ext = [o for o in shown if not o.name.startswith('CP_')]
cpt = [o for o in shown if o.name.startswith('CP_')]
ext_tree = BVHTree.FromBMesh(world_bm(ext))
cp_bm = world_bm(cpt)
cp_tree = BVHTree.FromBMesh(cp_bm)
cp_bm.faces.ensure_lookup_table()
INSIDE = Vector(C.MEASURE.get('eye', (0.0, 0.0, 0.0)))          # a point inside the cockpit
# 26 directions (cube faces, edges, corners): a cockpit face is seen from outside past the glass when rays leave in
# two or more of them without meeting the exterior skin or glass (one may slip through a seam)
DIRS = [Vector((x, y, z)).normalized() for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)]


def coincident(tree, c, n, faces_n):
    """Same-facing surface of the other model within 1.5 mm."""
    for d in (n, -n):
        hit = tree.ray_cast(c - d * 0.0015, d, 0.003)
        if hit[0] is not None and hit[1].dot(n) > 0.9:
            return True
    return False


# Cockpit surfaces crossing the outer shell (the glare shield and sill panels came 1-5 cm through the exterior skin at
# the windshield base, showing as black arcs and edges outside; testing face centres missed them) are pressed under
# it. Moving vertices leaves no holes, a dropped face would open a window to the sky (the exterior skin is single
# sided). The outer shell is the exterior faces seen from outside: open sky along their normal (the exterior model's
# own cockpit tub and sills under the glass are not). A vertex more than OUTSIDE outside the shell needs to go to SINK
# under it along the shell normal; the move fades out over BLEND around it (the neighbours go part of the way, the
# direction is the weighted mean of the shell normals): moving only the vertices outside tore the sill tops into
# dents and slits, seen from the seat; sinking the vertices on the shell too sawtoothed the sill edges along the glass.
from mathutils.kdtree import KDTree
SINK, OUTSIDE, REACH, BLEND = 0.006, 0.002, 0.05, 0.03
shell_v, shell_p = [], []
for o in ext:
    M, R = o.matrix_world, o.matrix_world.to_3x3()
    base = len(shell_v)
    shell_v.extend(M @ v.co for v in o.data.vertices)
    for p in o.data.polygons:
        c, n = M @ p.center, (R @ p.normal).normalized()
        if ext_tree.ray_cast(c + n * 0.003, n, 20.0)[0] is None:
            shell_p.append([base + i for i in p.vertices])
shell = BVHTree.FromPolygons(shell_v, shell_p)
pts = [(o, v.index, o.matrix_world @ v.co) for o in cpt for v in o.data.vertices]
kd = KDTree(len(pts))
for i, (_, _, p) in enumerate(pts):
    kd.insert(p, i)
kd.balance()
depth = {}                                   # vertex -> [largest faded depth, weighted normal sum]
need = 0
for o, vi, p in pts:
    q, n, _, _ = shell.find_nearest(p, REACH)
    if q is None or (p - q).dot(n) <= OUTSIDE:
        continue
    need += 1
    a = (p - q).dot(n) + SINK
    for _, j, d in kd.find_range(p, BLEND):
        w = a * (1.0 - d / BLEND)
        e = depth.setdefault(j, [0.0, Vector()])
        e[0] = max(e[0], w)
        e[1] += n * w
touched = set()
for j, (a, nsum) in depth.items():
    o, vi, p = pts[j]
    if a <= 0.0 or nsum.length == 0.0:
        continue
    o.data.vertices[vi].co = o.matrix_world.inverted() @ (p - nsum.normalized() * a)
    touched.add(o)
for o in touched:
    o.data.update()
print('cockpit vertices sunk under the outer shell: %d outside, %d moved (%d shell faces)'
      % (need, len(depth), len(shell_p)))
cp_bm.free()
cp_bm = world_bm(cpt)
cp_tree = BVHTree.FromBMesh(cp_bm)

cut_out = cut_dup = cut_ext = 0
for o in cpt:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    M, R = o.matrix_world, o.matrix_world.to_3x3()
    drop = []
    for f in bm.faces:
        c = M @ f.calc_center_median()
        n = (R @ f.normal).normalized()
        # outside: open sky along the face normal or in two of the 26 directions (the windshield-base wedges and the
        # frame edges along the glass seam lay on the skin next to the glass)
        if ext_tree.ray_cast(c + n * 0.003, n, 20.0)[0] is None or \
                sum(1 for d in DIRS if ext_tree.ray_cast(c + d * 0.002, d, 20.0)[0] is None) >= 2:
            drop.append(f); cut_out += 1
        elif n.dot(INSIDE - c) < 0 and ext_tree.ray_cast(c - n * 0.0005, n, 0.0045)[0] is not None:
            # facing out of the cockpit within 4 mm under the exterior skin/frame/glass: hidden from inside, z-fights
            # with the exterior surface seen from outside (windshield arch: the two models triangulated differently)
            drop.append(f); cut_dup += 1
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='FACES')
        bm.to_mesh(o.data)
    bm.free()
for o in ext:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    M, R = o.matrix_world, o.matrix_world.to_3x3()
    drop = [f for f in bm.faces if (R @ f.normal).normalized().dot(INSIDE - M @ f.calc_center_median()) > 0 and
            coincident(cp_tree, M @ f.calc_center_median(), (R @ f.normal).normalized(), None)]
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='FACES')
        bm.to_mesh(o.data)
        cut_ext += len(drop)
    bm.free()
print('cockpit clipped: %d faces outside the skin, %d duplicating exterior faces; %d exterior faces replaced'
      % (cut_out, cut_dup, cut_ext))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
