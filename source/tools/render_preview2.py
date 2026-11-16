"""Aircraft selection preview like the SDK sample (preview_dr400.tif): 4096 px, transparent background, aircraft seen
from front-left above with the nose to the left, framed to fill the width. Uses the converted Aerofly textures
(<build dir>/<material>_color.png), so it shows exactly the livery the game draws; a repaint folder overrides them.

    AC=ac_su35 Blender --background <posed.blend> --python tools/render_preview2.py -- <out.tif> <build dir> [repaint dir]
"""
import sys, os, re, json, math, importlib
import bpy
from mathutils import Vector

A = sys.argv[sys.argv.index('--') + 1:]
OUT, BUILD = A[0], A[1]
REPAINT = A[2] if len(A) > 2 else None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.environ.get('AC_DIR'):          # aircraft folder holding ac_<name>.py (aircraft/<name>/)
    sys.path.insert(0, os.environ['AC_DIR'])
C = importlib.import_module(os.environ.get('AC', 'ac_su35'))
RES = 4096
VIEW = Vector((0.55, 1.0, 0.42)).normalized()      # from the aircraft towards the camera (x fwd, y left, z up)


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


def material_for(o):
    glass = bool(C.GLASS_KIND.search(o.get('edm_mat_kind', '')))
    key = 'GLASS' if glass else tex0(o).lower()
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
coll = bpy.data.collections[C.COLLECTION]
shown = []
for o in sc.objects:
    if o.type != 'MESH':
        continue
    vis = o.name in coll.objects and len(o.data.polygons) and not excluded(o)
    o.hide_render = not vis
    if vis:
        o.data.materials.clear()
        o.data.materials.append(material_for(o))
        shown.append(o)

# stores of a load repaint (ac PREVIEW_OBJECTS: name of the repaint folder -> objects with edm_textures)
if REPAINT and hasattr(C, 'PREVIEW_OBJECTS'):
    for o in C.PREVIEW_OBJECTS(os.path.basename(os.path.normpath(REPAINT))):
        o.data.materials.clear()
        o.data.materials.append(material_for(o))
        shown.append(o)

# camera: orthographic along -VIEW, framed on the projected bounds of every shown vertex
right = VIEW.cross(Vector((0, 0, 1))).normalized() * -1
up = right.cross(-VIEW).normalized()
us, vs, ds = [], [], []
for o in shown:
    mw = o.matrix_world
    for v in o.data.vertices:
        p = mw @ v.co
        us.append(p.dot(right)); vs.append(p.dot(up)); ds.append(p.dot(VIEW))
cu, cv = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
size = max(max(us) - min(us), max(vs) - min(vs)) * 1.06
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = 'ORTHO'
cam.data.ortho_scale = size
cam.data.clip_end = 500
cam.location = right * cu + up * cv + VIEW * (max(ds) + 50)
cam.rotation_euler = (-VIEW).to_track_quat('-Z', 'Y').to_euler()

sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3.2
sun.rotation_euler = (-(VIEW + Vector((0.3, -0.4, 1.2)))).normalized().to_track_quat('-Z', 'Y').to_euler()
sc.collection.objects.link(sun)
w = bpy.data.worlds.new('w')
sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.62, 0.70, 0.82, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 1.1

sc.render.engine = 'BLENDER_EEVEE'
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = RES
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'TIFF'
sc.render.image_settings.color_mode = 'RGBA'
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('PREVIEW', OUT, len(shown), 'objects, ortho %.1f m' % size)
