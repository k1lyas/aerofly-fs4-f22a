"""Top views of our own model for the BAY page's picture (mfd_symbols.py, 2026-11-22: the first outline was drawn by
eye from published figures and did not look like the F-22). Renders masks of the exported model straight from
above (orthographic, flat white on black, Workbench): the airframe (every F22A_FUSE mesh), the canopy glass and the
fins, at the sprite's size x mfd_symbols.SS, framed by mfd_symbols.FRAME (metres: x forward, y left).

    Blender --background work/f22_exported.blend --python mfd_silhouette.py -- <out dir>
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mfd_symbols as M

OUT = sys.argv[sys.argv.index('--') + 1]
os.makedirs(OUT, exist_ok=True)


def mats(o):
    return [m.name for m in o.data.materials if m]


def world_bounds(o):
    import mathutils
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    return (min(v.x for v in bb), max(v.x for v in bb), min(v.y for v in bb), max(v.y for v in bb),
            min(v.z for v in bb), max(v.z for v in bb))


def exterior(o):
    n = o.name
    return o.type == 'MESH' and not n.startswith(('pv_', 'CP')) and 'DEBRIS' not in n.upper()


SETS = {
    'airframe': lambda o: exterior(o) and any(m.startswith('F22A_FUSE') for m in mats(o)) and 'Gear' not in o.name,
    'canopy': lambda o: exterior(o) and any('CANOPY_GLASS_CLEAR' in m for m in mats(o)) and o.name != 'Sunglasses',
    # the fins: airframe meshes standing high over the rear fuselage
    'fins': lambda o: SETS['airframe'](o) and world_bounds(o)[1] < -0.5 and world_bounds(o)[5] > 1.4,
}

objs = [o for o in bpy.data.objects if o.type == 'MESH']
x0, x1, y0, y1 = M.FRAME
for name, pick in SETS.items():
    chosen = [o for o in objs if pick(o)]
    # a clean scene of its own for each mask: the exported file keeps its objects in collections the render skips
    sc = bpy.data.scenes.new('mfd_sil_' + name)
    for o in chosen:
        sc.collection.objects.link(o)
        o.hide_render = False
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT'
    sc.display.shading.color_type = 'SINGLE'
    sc.display.shading.single_color = (1.0, 1.0, 1.0)
    sc.display.render_aa = 'OFF'
    sc.render.dither_intensity = 0.0
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new('w')
    sc.world.color = (0.0, 0.0, 0.0)
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x, sc.render.resolution_y = M.SIL_W * M.SS, M.SIL_H * M.SS
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'BW'
    # camera over the frame's centre, looking down, the nose (+x) up in the picture and +y (left wing) to the left
    cam = bpy.data.objects.new('mfd_sil_cam_' + name, bpy.data.cameras.new('mfd_sil_cam_' + name))
    sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = max(x1 - x0, (y1 - y0) * M.SIL_H / float(M.SIL_W))
    cam.data.clip_end = 100.0
    cam.location = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, 30.0)
    cam.rotation_euler = (0.0, 0.0, -1.5707963)         # image up = +x, image right = -y (the right wing)
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT, 'sil_%s.png' % name)
    bpy.ops.render.render(write_still=True, scene=sc.name)
    print('SIL %s: %d meshes' % (name, len(chosen)))
