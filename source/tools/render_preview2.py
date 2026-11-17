"""Aircraft selection preview like the SDK sample (preview_dr400.tif): 4096 px, transparent background, aircraft seen
from front-left above with the nose to the left, framed to fill the width. Uses the converted Aerofly textures
(<build dir>/<material>_color.png), so it shows exactly the livery the game draws; a repaint folder overrides them.

    AC=ac_f22 Blender --background <posed.blend> --python tools/render_preview2.py -- <out.tif> <build dir> [repaint dir]
"""
import sys, os, re, json, math, importlib
import bpy
from mathutils import Vector, Matrix

A = sys.argv[sys.argv.index('--') + 1:]
OUT, BUILD = A[0], A[1]
REPAINT = A[2] if len(A) > 2 else None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.environ.get('AC_DIR'):          # aircraft folder holding ac_<name>.py (aircraft/<name>/)
    sys.path.insert(0, os.environ['AC_DIR'])
C = importlib.import_module(os.environ.get('AC', 'ac_f22'))
RES = 4096
VIEW = Vector((0.62, 1.0, 0.45)).normalized()      # from the aircraft towards the camera (x fwd, y left, z up)


def tex0(o):
    return json.loads(o.get('edm_textures', '{}')).get('0', '')


def excluded(o):
    if getattr(C, 'BURNER', None) and C.BURNER.match(o.name):
        return True
    return bool(C.EXCLUDE_NAME.search(o.name) or C.EXCLUDE_MATERIAL.search(o.get('edm_material', '')) or
                C.EXCLUDE_KIND.search(o.get('edm_mat_kind', '')))


def colour_png(t):
    name = re.sub(r'[^a-z0-9_]', '_', t.lower()) + '_color.png'
    for d in ([REPAINT] if REPAINT else []) + [BUILD]:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


images, materials = {}, {}


EXPORTED = 'exported' in bpy.data.collections      # the export's own triangles (PREVIEW_BLEND), as the game draws them
GLASS_MATS = ('glass_outside', 'glass_inside', 'glass_plain')


def material_key(o):
    if EXPORTED:
        n = o.data.materials[0].name[3:] if o.data.materials and o.data.materials[0] else ''
        return 'GLASS' if n in GLASS_MATS else n
    return 'GLASS' if C.GLASS_KIND.search(o.get('edm_mat_kind', '')) else tex0(o).lower()


def shown_in_game(part, repaint):
    """What the aircraft shows as loaded with this repaint: no broken / debris / damage pieces, flat tyres, burner glow,
    HUD symbology, lamps lit only in some states; stores only those of the repaint (C.PREVIEW_PARTS)."""
    if part in getattr(C, 'PREVIEW_PARTS', {}).get(repaint, ()):
        return True
    if part.startswith('Stores_') or part.endswith('__S'):
        return False
    if part.startswith('D_') and part not in ('D_FinLeftBase', 'D_FinRightBase'):
        return False
    return not any(k in part for k in ('__B', '__FLAT', 'Flat', 'Burner_', 'HudProjection', 'Amber', '__LGearHandle'))


def material_for(o):
    key = material_key(o)
    glass = key == 'GLASS'
    if key in materials:
        return materials[key]
    m = bpy.data.materials.new('PV_' + key)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    if glass:
        bsdf.inputs['Base Color'].default_value = (0.05, 0.06, 0.07, 1)
        bsdf.inputs['Roughness'].default_value = 0.05
        bsdf.inputs['Alpha'].default_value = 0.35
        m.surface_render_method = 'BLENDED'
    else:
        p = colour_png(key)
        if p:
            if p not in images:
                images[p] = bpy.data.images.load(p)
            tn = nt.nodes.new('ShaderNodeTexImage')
            tn.image = images[p]
            nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
        else:
            bsdf.inputs['Base Color'].default_value = (0.5, 0.5, 0.52, 1)
        bsdf.inputs['Roughness'].default_value = 0.55
    materials[key] = m
    return m


sc = bpy.context.scene
shown = []
repaint_name = os.path.basename(os.path.normpath(REPAINT)) if REPAINT else ''
if EXPORTED:
    # (the pose scene's own DCS meshes have mixed face winding and inner shells - dark patches at the nose and the intakes,
    # chequered with back faces hidden, user 2026-11-17; the export has sorted that out)
    for o in sc.objects:
        o.hide_render = True
    for o in bpy.data.collections['exported'].objects:
        if o.type == 'MESH' and len(o.data.polygons) and shown_in_game(o.get('aerofly_part', ''), repaint_name):
            m = material_for(o)
            o.data.materials.clear()
            o.data.materials.append(m)
            o.hide_render = False
            shown.append(o)
else:
    coll = bpy.data.collections[C.COLLECTION]
    for o in sc.objects:
        if o.type != 'MESH':
            continue
        vis = o.name in coll.objects and len(o.data.polygons) and not excluded(o)
        o.hide_render = not vis
        if vis:
            o.data.materials.clear()
            o.data.materials.append(material_for(o))
            shown.append(o)

# stores of a load repaint from the pose scene (ac PREVIEW_OBJECTS: name of the repaint folder -> objects with edm_textures)
if REPAINT and hasattr(C, 'PREVIEW_OBJECTS') and not EXPORTED:
    for o in C.PREVIEW_OBJECTS(os.path.basename(os.path.normpath(REPAINT))):
        o.data.materials.clear()
        o.data.materials.append(material_for(o))
        shown.append(o)

# ---- studio render as the stock previews (user 2026-11-17: IPACS' cards - lit, glossy, a mirror reflection under the
# aircraft, nose left, from front-left above). Cycles: a soft key light from above-front, a sky fill, the aircraft
# rendered twice - as it stands and mirrored about the ground plane (its underside, as a real mirror shows it) - and
# the mirror image laid under it at REFLECTION opacity, fading downwards (the SDK sample's DR400 card).
REFLECTION = 0.5
from bpy_extras.object_utils import world_to_camera_view
import numpy as np

# standing on all its wheels (user 2026-11-17: the main wheels hung over their reflection - in the export pose they are
# 23 cm higher than the nose wheel): pitched about the main wheels until the wheel bottoms are level (geometry.json)
geom_path = os.path.join(os.environ.get('AC_DIR', ''), 'work', 'geometry.json')
if os.path.exists(geom_path):
    wheels = json.load(open(geom_path)).get('wheels', [])
    nose = [w for w in wheels if w['which'] == 'nose']
    mains = [w for w in wheels if w['which'] != 'nose']
    if nose and mains:
        mx = sum(w['center'][0] for w in mains) / len(mains)
        mz = sum(w['lowest_z'] for w in mains) / len(mains)
        dx, dz = nose[0]['center'][0] - mx, nose[0]['lowest_z'] - mz
        pitch = math.atan2(-dz, dx)                       # + = nose up
        rot = Matrix.Translation((mx, 0, mz)) @ Matrix.Rotation(-pitch, 4, 'Y') @ Matrix.Translation((-mx, 0, -mz))
        for o in shown:
            o.matrix_world = rot @ o.matrix_world
        bpy.context.view_layer.update()
        print('PREVIEW levelled on the wheels: %.2f deg nose up' % math.degrees(pitch))


def bake(o, M):
    """The object's transform (times M) into its own mesh, normals flipped where it mirrors: a mirrored DCS object
    (negative scale) reversed its faces' front for the back-face test below (the whole skin went chequered)."""
    full = M @ o.matrix_world
    me = o.data.copy()
    me.transform(full)
    if full.determinant() < 0:
        me.flip_normals()
    o.data = me
    o.matrix_world = Matrix.Identity(4)


for o in shown:
    bake(o, Matrix.Identity(4))
bpy.context.view_layer.update()
ground = min((o.matrix_world @ v.co).z for o in shown for v in o.data.vertices)
pts = [o.matrix_world @ v.co for o in shown for i, v in enumerate(o.data.vertices) if i % 7 == 0]
pts += [Vector((p.x, p.y, 2 * ground - p.z)) for p in pts]          # the mirror image belongs in the frame
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 85
cam.data.sensor_width = 36
cam.data.clip_end = 2000
centre = sum(pts, Vector()) / len(pts)
rot = (-VIEW).to_track_quat('-Z', 'Y').to_euler()
cam.rotation_euler = rot
sc.render.resolution_x = sc.render.resolution_y = RES
dist = 60.0
for _ in range(40):                    # distance and offset so the projected bounds fill 94 % of the width
    cam.location = centre + VIEW * dist
    bpy.context.view_layer.update()
    pr = [world_to_camera_view(sc, cam, p) for p in pts]
    xs, ys = [q.x for q in pr], [q.y for q in pr]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    cx, cy = (max(xs) + min(xs)) / 2 - 0.5, (max(ys) + min(ys)) / 2 - 0.5
    ortho_r = cam.matrix_world.to_3x3()
    centre = centre + ortho_r @ Vector((cx * dist * 36 / 85, cy * dist * 36 / 85, 0))
    dist *= max(w, h) / 0.94
print('PREVIEW frame: distance %.1f m, ground z %.2f' % (dist, ground))

# lighting
for d in bpy.data.lights:
    pass
key = bpy.data.objects.new('key', bpy.data.lights.new('key', 'SUN'))
key.data.energy = 6.0
key.data.angle = math.radians(8)
key.rotation_euler = (-(Vector((0.6, 0.5, 1.0)).normalized())).to_track_quat('-Z', 'Y').to_euler()
sc.collection.objects.link(key)
rim = bpy.data.objects.new('rim', bpy.data.lights.new('rim', 'SUN'))
rim.data.energy = 1.2
rim.data.angle = math.radians(15)
rim.rotation_euler = (-(Vector((-0.8, -0.4, 0.5)).normalized())).to_track_quat('-Z', 'Y').to_euler()
sc.collection.objects.link(rim)
w = bpy.data.worlds.new('w')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
bg.inputs[0].default_value = (0.55, 0.66, 0.85, 1)
bg.inputs[1].default_value = 0.6
for m in materials.values():
    b = m.node_tree.nodes.get('Principled BSDF')
    if b and m.name != 'PV_GLASS':
        b.inputs['Roughness'].default_value = 0.36
        b.inputs['Specular IOR Level'].default_value = 0.65

sc.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for dev in prefs.devices:
        dev.use = True
    sc.cycles.device = 'GPU'
except Exception as e:
    print('PREVIEW cpu render:', e)
sc.cycles.samples = int(os.environ.get('PREVIEW_SAMPLES', '96'))
sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.render.image_settings.file_format = 'OPEN_EXR'
sc.render.image_settings.color_mode = 'RGBA'
tmp = OUT + '.%s.exr'
sc.render.filepath = tmp % 'main'
bpy.ops.render.render(write_still=True)
# the mirror pass: every shown object mirrored about z = ground (its own winding flips; Cycles shades both sides)
for o in shown:
    bake(o, Matrix.Translation((0, 0, 2 * ground)) @ Matrix.Scale(-1, 4, (0, 0, 1)))
sc.render.filepath = tmp % 'mirror'
bpy.ops.render.render(write_still=True)


def load(path):
    im = bpy.data.images.load(path)
    a = np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4)
    bpy.data.images.remove(im)
    return a


main, mirror = load(tmp % 'main'), load(tmp % 'mirror')
rows = np.linspace(0.0, 1.0, RES, dtype=np.float32)[:, None]          # array row 0 = bottom of the picture
mirror[..., 3] *= REFLECTION * np.clip(0.35 + rows * 1.3, 0, 1)      # fainter towards the bottom
out = main.copy()
a_m, a_r = main[..., 3:4], mirror[..., 3:4]
alpha = a_m + a_r * (1 - a_m)
out[..., :3] = (main[..., :3] * a_m + mirror[..., :3] * a_r * (1 - a_m)) / np.maximum(alpha, 1e-6)
out[..., 3:4] = alpha
rgb = np.clip(out[..., :3], 0, 1)               # EXR is scene-linear: to sRGB for the 8-bit card (the first one came out dark)
out[..., :3] = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
img = bpy.data.images.new('preview', RES, RES, alpha=True)
img.pixels.foreach_set(np.clip(out, 0, 1).reshape(-1))
img.filepath_raw = OUT
img.file_format = 'TIFF'
img.save()
for k in ('main', 'mirror'):
    os.remove(tmp % k)
print('PREVIEW', OUT, len(shown), 'objects')
