"""Measure a posed DCS import for the Aerofly configuration (wheels, wing/stab/fin stations, fuselage, eye).

    AC=ac_su35 Blender --background <pose.blend> --python measure_parts.py -- <anim_pivots.json> <out.json>

Exact plane sections of the triangle soup (vertex slabs miss large wing triangles). Axes: X fwd, Y left, Z up.
"""
import sys, os, json, importlib
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.environ.get('AC_DIR'):          # aircraft folder holding ac_<name>.py (aircraft/<name>/)
    sys.path.insert(0, os.environ['AC_DIR'])
C = importlib.import_module(os.environ.get('AC', 'ac_su35'))
ANIM, OUT = sys.argv[sys.argv.index('--') + 1:][:2]
anim = json.load(open(ANIM))
M = C.MEASURE


def args_of(o):
    return {int(a) for a in str(o.get('edm_anim_args', '')).split(',') if a}


def keep(o):
    m = o.get('edm_material', '')
    return not (C.EXCLUDE_NAME.search(o.name) or C.EXCLUDE_MATERIAL.search(m) or
                C.EXCLUDE_KIND.search(o.get('edm_mat_kind', '')))


def triangles(objs):
    out = []
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        if not len(me.loop_triangles):
            continue
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get('co', co)
        mw = np.array(o.matrix_world)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        tv = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
        me.loop_triangles.foreach_get('vertices', tv)
        out.append(co[tv].reshape(-1, 3, 3))
    return np.vstack(out) if out else np.zeros((0, 3, 3))


def section(T, axis, value):
    lo, hi = T[:, :, axis].min(1), T[:, :, axis].max(1)
    tri = T[(lo <= value) & (hi >= value)]
    pts = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        pa, pb = tri[:, a], tri[:, b]
        da, db = pa[:, axis] - value, pb[:, axis] - value
        m = (da * db <= 0) & (da != db)
        t = (da[m] / (da[m] - db[m]))[:, None]
        pts.append(pa[m] + t * (pb[m] - pa[m]))
    return np.vstack(pts) if pts else np.zeros((0, 3))


coll = bpy.data.collections[C.COLLECTION]
objs = [o for o in coll.objects if o.type == 'MESH' and len(o.data.polygons) and keep(o)]
stab_objs = {s: [o for o in objs if args_of(o) & {a}] for a, s in C.STAB_ARGS.items()}
stab_set = {id(o) for v in stab_objs.values() for o in v}
gear_args = set(M['gear_args'])
airframe = [o for o in objs if id(o) not in stab_set and not (args_of(o) & gear_args)]
T = triangles(airframe)
V = T.reshape(-1, 3)
res = {'bounds': [V.min(0).tolist(), V.max(0).tolist()]}

# wheels
wheels = []
for arg, which in C.WHEEL_ARGS.items():
    wo = [o for o in objs if arg in args_of(o)]
    groups = {'nose': wo} if which == 'nose' else {
        'left': [o for o in wo if (o.matrix_world @ o.data.vertices[0].co).y > 0],
        'right': [o for o in wo if (o.matrix_world @ o.data.vertices[0].co).y < 0]}
    for side, g in groups.items():
        if not g:       # one wheel argument per side (F-22: 102 left, 103 right)
            continue
        P = triangles(g).reshape(-1, 3)
        lo, hi = P.min(0), P.max(0)
        wheels.append({'which': side, 'arg': arg, 'center': ((lo + hi) / 2).tolist(), 'radius': float((hi[2] - lo[2]) / 2),
                       'width': float(hi[1] - lo[1]), 'lowest_z': float(lo[2])})
res['wheels'] = wheels

# wing stations (static wing + flaps/slats), z band excludes fins and stores
wing = []
for y in np.arange(M['wing_root'], V[:, 1].max() - 0.05, 0.25):
    S = section(T, 1, y)
    S = S[(S[:, 2] > M['wing_z'][0]) & (S[:, 2] < M['wing_z'][1]) & (S[:, 0] > M['wing_x_min'])]
    if len(S) < 6:
        continue
    wing.append({'y': float(y), 'le': float(S[:, 0].max()), 'te': float(S[:, 0].min()), 'z': float(S[:, 2].mean())})
res['wing'] = wing

# stabilator stations (left one, mirrored)
TS = triangles(stab_objs['left'])
stab = []
for y in np.arange(TS[:, :, 1].min() + 0.05, TS[:, :, 1].max() - 0.02, 0.2):
    S = section(TS, 1, y)
    if len(S) < 4:
        continue
    stab.append({'y': float(y), 'le': float(S[:, 0].max()), 'te': float(S[:, 0].min()), 'z': float(S[:, 2].mean())})
res['stab'] = stab

# fin stations (left fin: y > 0, above the fuselage)
fin = []
for z in np.arange(M['fin_z0'], V[:, 2].max() - 0.05, 0.25):
    S = section(T, 2, z)
    S = S[(S[:, 1] > 0.3) & (S[:, 0] < M['fin_x_max'])]
    if len(S) < 4:
        continue
    fin.append({'z': float(z), 'le': float(S[:, 0].max()), 'te': float(S[:, 0].min()), 'y': float(np.median(S[:, 1]))})
res['fin'] = fin

# fuselage sections (centre body incl. nacelles; wing outboard of fuselage_half_width, fins above fin_z0 cut)
fus = []
for x in np.arange(V[:, 0].min() + 0.1, V[:, 0].max(), 0.5):
    S = section(T, 0, x)
    S = S[(np.abs(S[:, 1]) < M['fuselage_half_width']) & ((S[:, 2] < M['fin_z0']) | (np.abs(S[:, 1]) < 0.9))]
    if len(S) < 6:
        continue
    fus.append({'x': float(x), 'width': float(S[:, 1].max() - S[:, 1].min()), 'z_min': float(S[:, 2].min()),
                'z_max': float(S[:, 2].max())})
res['fuselage'] = fus

# engines: nozzle exit centres from the configured nodes
res['eye'] = M['eye']
json.dump(res, open(OUT, 'w'), indent=1)
print('MEASURE bounds', np.round(res['bounds'], 2).tolist())
for w in wheels:
    print('MEASURE wheel', w['which'], np.round(w['center'], 3).tolist(), 'r %.3f w %.2f low %.3f' % (w['radius'], w['width'], w['lowest_z']))
print('MEASURE wing', len(wing), 'rows', [(round(r['y'], 2), round(r['le'], 2), round(r['te'], 2), round(r['z'], 2)) for r in wing[::3]])
print('MEASURE stab', [(round(r['y'], 2), round(r['le'], 2), round(r['te'], 2), round(r['z'], 2)) for r in stab[::2]])
print('MEASURE fin', [(round(r['z'], 2), round(r['le'], 2), round(r['te'], 2), round(r['y'], 2)) for r in fin[::2]])
print('MEASURE fuselage', [(round(r['x'], 1), round(r['width'], 2), round(r['z_min'], 2), round(r['z_max'], 2)) for r in fus[::4]])
