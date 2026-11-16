"""Bake cockpit ambient occlusion and flood light into texture space (Cycles), for the interior ambient and lighting
maps export_parts.py writes.

    blender --background <aircraft>_pose.blend --python bake_cockpit_light.py -- <out dir>
    (AC / AC_DIR as export_parts.py)

ac BAKE_AO: materials baked as ambient occlusion -> <out>/<material>_ao.png (0 occluded .. 1 open).
ac BAKE_FLOOD = dict(materials=[...], lamps=[(position, target, radius, cone angle deg, power W)], reference=[...]):
the light of the flood lamps alone (direct + bounces off matt grey, no texture colour) -> <out>/<material>_flood.png,
all materials scaled by one factor (99.5th percentile of the reference materials' lit texels = 1) so their brightness
matches across texture borders. BAKE_ONLY=ao / flood bakes one of the two; BAKE_ONLY=wear only <material>_wear.png (edge, 3D noise: wear_shader).
Only materials with a unique UV layout bake correctly (overlapping islands overwrite each other).
"""
import sys, os, re, json, importlib, math
import bpy
import bmesh
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.environ.get('AC_DIR'):
    sys.path.insert(0, os.environ['AC_DIR'])
C = importlib.import_module(os.environ.get('AC', 'ac_su35'))
OUT = sys.argv[sys.argv.index('--') + 1:][0]
os.makedirs(OUT, exist_ok=True)
SIZE = getattr(C, 'BAKE_SIZE', 2048)


def mats(o):
    return [m.name if m else '' for m in o.data.materials]


def int_list(s):
    return [int(a) for a in str(s).split(',') if a]


def prepare_scene():
    """Hide what the game will not draw (as export_parts.py excludes it) and glass; remove REMOVE_FACES."""
    pilot = getattr(C, 'PILOT_MATERIAL', None)
    for o in bpy.data.objects:
        if o.type == 'LIGHT':
            o.hide_render = True
        if o.type != 'MESH':
            continue
        mat = o.get('edm_material', '')
        if (C.EXCLUDE_NAME.search(o.name) or C.EXCLUDE_MATERIAL.search(mat) or C.EXCLUDE_KIND.search(o.get('edm_mat_kind', ''))
                or C.GLASS_KIND.search(o.get('edm_mat_kind', '')) or any(re.search('glass', n, re.I) for n in mats(o))
                or (pilot and pilot.match(mat)) or set(int_list(o.get('edm_anim_args', ''))) & set(getattr(C, 'EXCLUDE_ARGS', ()))):
            o.hide_render = True
    import face_filter as FF                                    # (same selection as export_parts.remove_faces)
    for entry in getattr(C, 'REMOVE_FACES', ()):
        for o in bpy.data.objects:
            if o.type != 'MESH':
                continue
            names = mats(o) or ['']
            bm = bmesh.new()
            bm.from_mesh(o.data)
            gone = [f for f in bm.faces
                    if FF.matches(entry, names[min(f.material_index, len(names) - 1)] or o.get('edm_material', '')) and
                    FF.face_inside(entry, [o.matrix_world @ v.co for v in f.verts])]
            if gone:
                bmesh.ops.delete(bm, geom=gone, context='FACES')
                bm.to_mesh(o.data)
            bm.free()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = 'GPU'
    except Exception as e:                       # CPU fallback
        print('BAKE cpu only:', e)
    sc.render.bake.margin = 16
    sc.render.bake.use_clear = True
    if sc.world is None:
        sc.world = bpy.data.worlds.new('bake')


def bake(material, kind, suffix, **kw):
    users = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render and material in mats(o)]
    if not users:
        print('BAKE no visible user of', material)
        return None
    img = bpy.data.images.new(material + suffix, SIZE, SIZE, float_buffer=True)
    scratch = bpy.data.images.new('bake_scratch', 8, 8)
    added = []
    for o in users:                    # every material of the baked objects needs an active image node
        for m in o.data.materials:
            if m is None or any(m is a for a, _ in added):
                continue
            m.use_nodes = True
            n = m.node_tree.nodes.new('ShaderNodeTexImage')
            n.image = img if m.name == material else scratch
            m.node_tree.nodes.active = n
            added.append((m, n))
    bpy.ops.object.select_all(action='DESELECT')
    for o in users:
        o.select_set(True)
    bpy.context.view_layer.objects.active = users[0]
    bpy.ops.object.bake(type=kind, **kw)
    for m, n in added:
        m.node_tree.nodes.remove(n)
    a = np.array(img.pixels[:], np.float32).reshape(SIZE, SIZE, 4)[..., 0]
    print('BAKE %s %s: %d objects, mean %.3f' % (material, kind, len(users), a.mean()))
    return a


def save(a, path):
    img = bpy.data.images.new(os.path.basename(path), a.shape[1], a.shape[0])
    rgba = np.ones(a.shape + (4,), np.float32)
    rgba[..., :3] = np.clip(a, 0, 1)[..., None]
    img.pixels = rgba.ravel()
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()


def wear_shader(m):
    """Emission = (convex edge, coarse 3D noise, fine 3D noise): the wear masks export_parts / TEXTURE_HOOK paint with.
    Edge: how far a 4 mm bevel bends the normal (1 on a sharp edge), times a short-range AO so concave corners (also
    bevelled) do not count; noise on object coordinates in metres, so it runs on across UV island seams."""
    nt = m.node_tree
    N = nt.nodes
    out = next((n for n in N if n.type == 'OUTPUT_MATERIAL'), None) or N.new('ShaderNodeOutputMaterial')
    geo = N.new('ShaderNodeNewGeometry')
    bev = N.new('ShaderNodeBevel')
    bev.samples = 8
    bev.inputs['Radius'].default_value = getattr(C, 'WEAR_BEVEL', 0.004)
    dot = N.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    nt.links.new(bev.outputs['Normal'], dot.inputs[0])
    nt.links.new(geo.outputs['True Normal'], dot.inputs[1])
    edge = N.new('ShaderNodeMath')                       # (1 - dot) * gain
    edge.operation = 'MULTIPLY_ADD'
    edge.inputs[1].default_value = -getattr(C, 'WEAR_EDGE_GAIN', 12.0)
    edge.inputs[2].default_value = getattr(C, 'WEAR_EDGE_GAIN', 12.0)
    nt.links.new(dot.outputs['Value'], edge.inputs[0])
    edge.use_clamp = True
    ao = N.new('ShaderNodeAmbientOcclusion')
    ao.samples = 16
    ao.inputs['Distance'].default_value = 0.02
    convex = N.new('ShaderNodeMath')
    convex.operation = 'MULTIPLY'
    nt.links.new(edge.outputs[0], convex.inputs[0])
    nt.links.new(ao.outputs['AO'], convex.inputs[1])
    comb = N.new('ShaderNodeCombineColor')
    nt.links.new(convex.outputs[0], comb.inputs[0])
    for k, scale in ((1, 6.0), (2, 60.0)):
        nz = N.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = scale
        nz.inputs['Detail'].default_value = 4.0
        nt.links.new(geo.outputs['Position'], nz.inputs['Vector'])
        nt.links.new(nz.outputs['Fac'], comb.inputs[k])
    em = N.new('ShaderNodeEmission')
    nt.links.new(comb.outputs[0], em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])


ZONE_BOX = ((5.5, -1.2, -0.2), (9.5, 1.2, 2.2))     # cockpit box (m) the position bake is normalised to (8 bit: ~1 cm)


def zone_shader(m, what):
    """Emission = world position normalised to ZONE_BOX ('pos') or the world normal * 0.5 + 0.5 ('nrm')."""
    nt = m.node_tree
    N = nt.nodes
    out = next((n for n in N if n.type == 'OUTPUT_MATERIAL'), None) or N.new('ShaderNodeOutputMaterial')
    geo = N.new('ShaderNodeNewGeometry')
    vm = N.new('ShaderNodeVectorMath')
    if what == 'pos':
        lo, hi = ZONE_BOX
        vm.operation = 'MULTIPLY_ADD'
        vm.inputs[1].default_value = [1.0 / (h - l) for l, h in zip(lo, hi)]
        vm.inputs[2].default_value = [-l / (h - l) for l, h in zip(lo, hi)]
        nt.links.new(geo.outputs['Position'], vm.inputs[0])
    else:
        vm.operation = 'MULTIPLY_ADD'
        vm.inputs[1].default_value = (0.5, 0.5, 0.5)
        vm.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(geo.outputs['True Normal'], vm.inputs[0])
    em = N.new('ShaderNodeEmission')
    nt.links.new(vm.outputs[0], em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])


def bake_zones():
    """<material>_pos.png / _nrm.png for the BAKE_AO materials: where each texel is in the cockpit and which way it faces
    (the wear zones in ac TEXTURE_HOOK: hands, boots, elbows). Emission only - one sample."""
    sc = bpy.context.scene
    sc.cycles.samples = 1
    sc.render.bake.margin = 16
    only = [m for m in os.environ.get('BAKE_MATS', '').split(',') if m]
    for what in ('pos', 'nrm'):
        for m in bpy.data.materials:
            m.use_nodes = True
            zone_shader(m, what)
        for mat in [m for m in getattr(C, 'BAKE_AO', ()) if not only or m in only]:
            users = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render and mat in mats(o)]
            if not users:
                continue
            img = bpy.data.images.new(mat + '_' + what, SIZE, SIZE, float_buffer=True)
            scratch = bpy.data.images.new('bake_scratch', 8, 8)
            added = []
            for o in users:
                for mm in o.data.materials:
                    if mm is None or any(mm is a for a, _ in added):
                        continue
                    n = mm.node_tree.nodes.new('ShaderNodeTexImage')
                    n.image = img if mm.name == mat else scratch
                    mm.node_tree.nodes.active = n
                    added.append((mm, n))
            bpy.ops.object.select_all(action='DESELECT')
            for o in users:
                o.select_set(True)
            bpy.context.view_layer.objects.active = users[0]
            bpy.ops.object.bake(type='EMIT')
            for mm, n in added:
                mm.node_tree.nodes.remove(n)
            a = np.array(img.pixels[:], np.float32).reshape(SIZE, SIZE, 4)[..., :3]
            if what == 'pos':       # 16 bit (0.06 mm over the box; the 8-bit png steps ~16 mm): the wear's mm-scale noise
                np.savez_compressed(os.path.join(OUT, '%s_pos16.npz' % mat),
                                    p=np.round(np.clip(a, 0, 1) * 65535).astype(np.uint16))
            path = os.path.join(OUT, '%s_%s.png' % (mat, what))
            im = bpy.data.images.new(os.path.basename(path), SIZE, SIZE)
            rgba = np.ones((SIZE, SIZE, 4), np.float32)
            rgba[..., :3] = np.clip(a, 0, 1)
            im.pixels = rgba.ravel()
            im.filepath_raw = path
            im.file_format = 'PNG'
            im.save()
            print('BAKE %s %s' % (mat, what))


def bake_wear():
    """<material>_wear.png (RGB, wear_shader) for the BAKE_AO materials (unique UVs)."""
    sc = bpy.context.scene
    sc.cycles.samples = getattr(C, 'BAKE_WEAR_SAMPLES', 64)
    for m in bpy.data.materials:
        m.use_nodes = True
        wear_shader(m)
    only = [m for m in os.environ.get('BAKE_MATS', '').split(',') if m]
    for mat in [m for m in getattr(C, 'BAKE_AO', ()) if not only or m in only]:
        users = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render and mat in mats(o)]
        if not users:
            print('BAKE no visible user of', mat)
            continue
        img = bpy.data.images.new(mat + '_wear', SIZE, SIZE, float_buffer=True)
        scratch = bpy.data.images.new('bake_scratch', 8, 8)
        added = []
        for o in users:
            for m in o.data.materials:
                if m is None or any(m is a for a, _ in added):
                    continue
                n = m.node_tree.nodes.new('ShaderNodeTexImage')
                n.image = img if m.name == mat else scratch
                m.node_tree.nodes.active = n
                added.append((m, n))
        bpy.ops.object.select_all(action='DESELECT')
        for o in users:
            o.select_set(True)
        bpy.context.view_layer.objects.active = users[0]
        bpy.ops.object.bake(type='EMIT')
        for m, n in added:
            m.node_tree.nodes.remove(n)
        a = np.array(img.pixels[:], np.float32).reshape(SIZE, SIZE, 4)[..., :3]
        path = os.path.join(OUT, mat + '_wear.png')
        im = bpy.data.images.new(os.path.basename(path), SIZE, SIZE)
        rgba = np.ones((SIZE, SIZE, 4), np.float32)
        rgba[..., :3] = np.clip(a, 0, 1)
        im.pixels = rgba.ravel()
        im.filepath_raw = path
        im.file_format = 'PNG'
        im.save()
        print('BAKE %s wear: %d objects, edge mean %.3f p99 %.3f' % (mat, len(users), a[..., 0].mean(),
                                                                   np.percentile(a[..., 0], 99)))


def main():
    prepare_scene()
    sc = bpy.context.scene
    if os.environ.get('BAKE_ONLY') == 'wear':           # wear masks only (AO and flood stay as accepted)
        bake_wear()
        bake_zones()
        return
    if os.environ.get('BAKE_ONLY') == 'zones':          # position / normal maps only (fast)
        bake_zones()
        return
    # ambient occlusion: the cockpit's own crevices (distance about a hand's width - longer rays darken the whole tub
    # under the canopy rails)
    sc.cycles.samples = getattr(C, 'BAKE_AO_SAMPLES', 128)
    sc.world.light_settings.distance = getattr(C, 'BAKE_AO_DISTANCE', 0.12)
    only = os.environ.get('BAKE_ONLY')              # 'ao' / 'flood': one of the two
    for m in getattr(C, 'BAKE_AO', ()) if only != 'flood' else ():
        a = bake(m, 'AO', '_ao')
        if a is not None:
            save(a, os.path.join(OUT, m + '_ao.png'))
    fl = getattr(C, 'BAKE_FLOOD', None)
    if not fl or only == 'ao':
        if not only:
            bake_wear()
            bake_zones()
        return
    # flood light: a black world, only the flood lamps, every surface plain matt grey - the imported DCS materials are
    # metal / roughness shaders, and on the panels (metallic in RoughMet) the diffuse bake came out black
    for m in bpy.data.materials:
        m.use_nodes = True
        out = next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if out is None:
            out = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
        dif = m.node_tree.nodes.new('ShaderNodeBsdfDiffuse')
        dif.inputs['Color'].default_value = (0.3, 0.3, 0.3, 1.0)
        m.node_tree.links.new(dif.outputs[0], out.inputs['Surface'])
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Strength'].default_value = 0.0
    sc.cycles.samples = getattr(C, 'BAKE_FLOOD_SAMPLES', 256)
    sc.cycles.max_bounces = 2
    for k, (pos, target, radius, angle, power) in enumerate(fl['lamps']):
        ld = bpy.data.lights.new('flood%d' % k, 'SPOT')
        ld.energy, ld.shadow_soft_size = power, radius
        ld.spot_size, ld.spot_blend = math.radians(angle), 1.0
        lo = bpy.data.objects.new('flood%d' % k, ld)
        sc.collection.objects.link(lo)
        lo.location = pos
        lo.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    raw = {}
    for m in fl['materials']:
        a = bake(m, 'DIFFUSE', '_flood', pass_filter={'DIRECT', 'INDIRECT'})
        if a is not None:
            raw[m] = a
    # brightness reference: the console panels (knobs and grips close to a lamp would set it and leave the panels dark)
    lit = np.concatenate([a[a > 1e-4] for m, a in raw.items() if m in fl.get('reference', raw)])
    ref = float(np.percentile(lit, 99.5)) if lit.size else 1.0
    for m, a in raw.items():
        save(a / ref, os.path.join(OUT, m + '_flood.png'))
    json.dump({'flood_reference': ref}, open(os.path.join(OUT, 'bake.json'), 'w'))
    print('BAKE flood reference %.4g' % ref)
    if not only:                                     # full run: the wear masks too (their own shaders)
        bake_wear()
        bake_zones()


main()
