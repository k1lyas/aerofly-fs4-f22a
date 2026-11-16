"""Still pictures of the F-22 screens for the display caps (seen from outside the cockpit, where the live displays
draw nothing useful): the start pages as the screens show them in flight - ENG (left MFD), FUEL (right), the SA map
(PMFD), FCS (lower), the up-front displays (engines, standby ADI) and the ICP lines. Green strokes and text on black,
in the screen's own pixel units (y up), rendered flat (Workbench) at the screen's aspect ratio.

    Blender --background --factory-startup --python mfd_pages.py -- <out dir>
"""
import sys, os, math
import bpy

OUT = sys.argv[sys.argv.index('--') + 1]
os.makedirs(OUT, exist_ok=True)
G = (0.12, 1.0, 0.22)
C = (0.30, 0.90, 1.0)
W = (0.92, 0.96, 0.92)
Y = (1.0, 0.85, 0.15)
SKY = (0.05, 0.30, 0.75)
GROUND = (0.42, 0.25, 0.08)


def reset(w, h):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT'
    sc.display.shading.color_type = 'OBJECT'
    sc.display.render_aa = '16'
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new('w')
    sc.world.color = (0.0, 0.0, 0.0)
    sc.view_settings.view_transform = 'Standard'
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = max(w, h)
    cam.location = (w / 2, h / 2, 50.0)
    sc.camera = cam


def _link(o, col, z=0.0):
    o.color = (*col, 1.0)
    o.location.z = z
    bpy.context.scene.collection.objects.link(o)
    return o


def text(s, x, y, size=34, col=G, align='LEFT'):
    cu = bpy.data.curves.new('t', 'FONT')
    cu.body = s
    cu.size = size
    cu.align_x = align
    cu.align_y = 'CENTER'
    o = bpy.data.objects.new('t', cu)
    o.location = (x, y, 0)
    return _link(o, col, 1.0)


def line(pts, width=4, col=G, closed=False):
    cu = bpy.data.curves.new('l', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = width / 2
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts):
        p.co = (x, y, 0, 1)
    sp.use_cyclic_u = closed
    return _link(bpy.data.objects.new('l', cu), col, 1.0)


def box(x0, y0, x1, y1, width=4, col=G):
    return line([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], width, col, closed=True)


def arc(cx, cy, r, a0=0, a1=360, width=4, col=G, n=96):
    pts = [(cx + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)))
           for i in range(n + 1)]
    return line(pts, width, col, closed=(a1 - a0) >= 360)


def fill(x0, y0, x1, y1, col, z=0.0):
    me = bpy.data.meshes.new('f')
    me.from_pydata([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], [], [(0, 1, 2, 3)])
    return _link(bpy.data.objects.new('f', me), col, z)


def menu(labels):
    """Bottom row labels at the five DDI buttons (the Hornet DDI layout of our pages)."""
    for i, s in enumerate(labels):
        if s:
            text(s, 130 + 190 * i, 70, 30, G, 'CENTER')


def render(name):
    bpy.context.scene.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('PAGE', name)


# ---- FUEL (right MFD, our start page): totals, the Hornet tank boxes in lb
reset(1024, 1024)
text('TOTAL', 165, 905, 34, G, 'CENTER'); text('18080', 165, 860, 46, G, 'CENTER')
text('INTERNAL', 165, 810, 34, G, 'CENTER'); text('18080', 165, 765, 46, G, 'CENTER')
text('BINGO', 870, 820, 34, G, 'CENTER'); text('3000', 870, 775, 46, G, 'CENTER')
for label, val, y0, y1 in (('TK 1', '4750', 760, 900), ('L FD', '2990', 620, 700), ('R FD', '2340', 520, 600),
                           ('TK 4', '6050', 300, 470)):
    text(label, 512, y1 + 22, 30, G, 'CENTER')
    box(370, y0, 654, y1)
    text(val, 512, (y0 + y1) / 2, 46, G, 'CENTER')
for x, label in ((210, 'L WG'), (814, 'R WG')):
    text(label, x, 650, 30, G, 'CENTER')
    box(x - 70, 560, x + 70, 625)
    text('970', x, 592, 44, G, 'CENTER')
menu(['', '', 'MENU', '', ''])
render('cap_fuel')

# ---- ENG (left MFD): left / right engine columns
reset(1024, 1024)
text('ENG', 512, 920, 40, G, 'CENTER')
text('L', 360, 840, 38, G, 'CENTER'); text('R', 700, 840, 38, G, 'CENTER')
rows = [('RPM %', '92', '92'), ('EGT C', '742', '748'), ('FF PPH', '7400', '7520'), ('NOZ %', '18', '18'),
        ('OIL PSI', '52', '51'), ('THRUST %', '88', '88')]
for i, (lab, l, r) in enumerate(rows):
    y = 760 - 95 * i
    text(lab, 530, y, 30, G, 'CENTER')
    text(l, 360, y, 44, G, 'RIGHT'); text(r, 700, y, 44, G, 'LEFT')
    line([(250, y - 40), (410, y - 40)], 2); line([(650, y - 40), (810, y - 40)], 2)
menu(['', '', 'MENU', '', ''])
render('cap_eng')

# ---- SA (PMFD): ownship, range rings, compass arc, route and fields
reset(1024, 1024)
ox, oy = 512, 300
for r in (180, 360, 540):
    arc(ox, oy, r, -70, 70, 3, G)
for a in range(-70, 71, 10):
    r0, r1 = 540, 560 if a % 30 else 580
    line([(ox + r0 * math.sin(math.radians(a)), oy + r0 * math.cos(math.radians(a))),
          (ox + r1 * math.sin(math.radians(a)), oy + r1 * math.cos(math.radians(a)))], 3)
for a, s in ((-60, '33'), (-30, 'N'), (0, '3'), (30, '6'), (60, 'E')):
    text(s, ox + 610 * math.sin(math.radians(a)), oy + 610 * math.cos(math.radians(a)), 32, G, 'CENTER')
box(462, 930, 562, 985); text('030', 512, 957, 38, G, 'CENTER')
line([(ox, oy + 30), (ox - 22, oy - 25), (ox, oy - 12), (ox + 22, oy - 25)], 4, W, closed=True)
route = [(ox, oy), (600, 560), (560, 780), (720, 900)]
line(route, 4, C)
for x, y in route[1:]:
    arc(x, y, 16, 0, 360, 4, C, 32)
for i, (x, y) in enumerate(route[1:]):
    text('%d' % (i + 2), x + 34, y + 10, 28, C, 'LEFT')
for x, y in ((330, 620), (800, 470)):
    arc(x, y, 18, 0, 360, 4, G, 32); line([(x - 30, y), (x + 30, y)], 4); line([(x, y - 30), (x, y + 30)], 4)
text('SA', 70, 950, 34, G, 'LEFT'); text('RNG 40', 70, 900, 30, G, 'LEFT')
text('HDG 030  GS 452', 954, 950, 30, G, 'RIGHT')
menu(['', 'HSI', 'MENU', '', ''])
render('cap_sa')

# ---- FCS (lower SMFD): control surface table and the g limit
reset(1024, 1024)
text('FCS', 160, 140, 46, G, 'LEFT')
for i, (lab, l, r) in enumerate((('LEF', '12', '12'), ('TEF', '30', '30'), ('AIL', '30', '30'), ('RUD', '30', '30'),
                                 ('STAB', '2', '2'))):
    y = 860 - 70 * i
    text(lab, 512, y, 34, G, 'CENTER'); text(l, 400, y, 34, G, 'RIGHT'); text(r, 640, y, 34, G, 'LEFT')
    line([(330, y - 32), (700, y - 32)], 3)
for x0 in (120, 790):
    for k in range(5):
        line([(x0 + 26 * k, 590), (x0 + 26 * k, 900)], 3)
    for k in range(5):
        line([(x0, 590 + 77 * k), (x0 + 104, 590 + 77 * k)], 3)
text('G-LIM 9.0G', 150, 420, 46, G, 'LEFT')
for i, s in enumerate(('CAS', 'N ACC', 'L ACC', 'STICK', 'PEDAL', 'AOA')):
    y = 560 - 60 * i
    text(s, 640, y, 30, G, 'LEFT'); box(800, y - 25, 900, y + 25, 3)
menu(['', '', 'MENU', '', ''])
render('cap_fcs')

# ---- left UFD (740 x 570): the engine numbers, ICAWS area clear
reset(740, 570)
text('L', 250, 520, 30, G, 'CENTER'); text('R', 490, 520, 30, G, 'CENTER')
for i, (lab, l, r) in enumerate((('RPM', '92', '92'), ('EGT', '742', '748'), ('FF', '74', '75'), ('NOZ', '18', '18'),
                                 ('OIL', '52', '51'))):
    y = 465 - 52 * i
    text(lab, 370, y, 30, G, 'CENTER'); text(l, 290, y, 34, G, 'RIGHT'); text(r, 450, y, 34, G, 'LEFT')
line([(30, 190), (710, 190)], 3)
render('cap_ufd_left')

# ---- right UFD (740 x 570): standby attitude, speed and altitude, radios, fuel, clock
reset(740, 570)
fill(170, 290, 570, 540, SKY, 0.0)
fill(170, 120, 570, 290, GROUND, 0.0)
line([(170, 290), (570, 290)], 4, W)
for p in (-10, -5, 5, 10):
    y = 290 + p * 10
    w = 60 if p % 10 else 100
    line([(370 - w, y), (370 + w, y)], 3, W)
    text('%d' % abs(p), 370 + w + 22, y, 22, W, 'LEFT')
line([(300, 290), (345, 290), (370, 270), (395, 290), (440, 290)], 6, Y)
box(30, 260, 150, 320, 3); text('452', 90, 290, 36, G, 'CENTER')
box(590, 260, 720, 320, 3); text('25000', 655, 290, 32, G, 'CENTER')
text('COM1 123.45', 40, 70, 28, G, 'LEFT'); text('COM2 251.00', 40, 30, 28, G, 'LEFT')
text('FUEL 18080', 700, 70, 28, G, 'RIGHT'); text('14:32:05', 700, 30, 28, G, 'RIGHT')
render('cap_ufd_right')

# ---- ICP: scratchpad and the five option lines (as the F-22's: frequency, TACAN, ILS, IFF, autopilot)
reset(460, 86)
text('UHF 251.00', 30, 43, 46, G, 'LEFT')
render('cap_icp_scratch')
for i, s in enumerate((':VHF 123.45', ' UHF 251.00', ' TCN 077X', ' ILS 110.30', ' IFF 4  7400')):
    reset(430, 80)
    text(s, 20, 40, 44, G, 'LEFT')
    render('cap_icp%d' % (i + 1))
