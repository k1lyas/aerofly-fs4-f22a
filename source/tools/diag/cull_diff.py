"""Does the exported .tgi show what DCS shows? Both are viewed with back-face culling (as the game does) along many
directions; where the DCS source has a visible surface and the export has none (see-through hole) or a different one
(wrong layer visible), that spot is reported.

    AC=ac_su35 AC_DIR=aircraft/su35 Blender --background <pose.blend> --python tools/diag/cull_diff.py -- \
        <model.tgi> [step m = 0.08] [tolerance m = 0.03]

Source = the objects the exporter would use (not excluded by the aircraft config) of the imported EDM, triangles oriented
by the DCS normals exactly as in the exporter (tgi_write.object_arrays). Parts the export adds (gap plates, burner
sleeves, display quads) only add surfaces; parts it deliberately drops (pilot, pylons ...) are excluded from the source.
"""
import sys, os, re, math, importlib, collections
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if os.environ.get('AC_DIR'):
    sys.path.insert(0, os.environ['AC_DIR'])
import tgi_write as T
C = importlib.import_module(os.environ.get('AC', 'ac_su35'))
a = sys.argv[sys.argv.index('--') + 1:]
TGI = a[0]
STEP = float(a[1]) if len(a) > 1 else 0.08
TOL = float(a[2]) if len(a) > 2 else 0.03


def excluded(o):
    if getattr(C, 'BURNER', None) and C.BURNER.match(o.name):
        return bool(getattr(C, 'BURNER_DROP', False))
    return bool(C.EXCLUDE_NAME.search(o.name) or C.EXCLUDE_MATERIAL.search(o.get('edm_material', '')) or
                C.EXCLUDE_KIND.search(o.get('edm_mat_kind', '')))


# --- source: imported DCS objects, as the exporter orients them --------------------------------------
verts, polys = [], []
face_owner = []
coll = bpy.data.collections[C.COLLECTION]
n_obj = 0
for o in coll.objects:
    if o.type != 'MESH' or not len(o.data.polygons) or excluded(o):
        continue
    pos = T.object_arrays(o)[0]
    base = len(verts)
    verts.extend(map(tuple, pos))
    polys.extend((base + 3 * t, base + 3 * t + 1, base + 3 * t + 2) for t in range(len(pos) // 3))
    face_owner.extend([o.name] * (len(pos) // 3))
    n_obj += 1
SRC_V = np.array(verts); SRC_T = np.array(polys); SRC_OWNER = np.array(face_owner, dtype=object)
print('source: %d objects, %d triangles' % (n_obj, len(polys)))

# --- export: the .tgi as written --------------------------------------------------------------------
text = open(TGI).read()
tv, tp, n = [], [], 0
for gtext in re.split(r'<\[tmxglgeometry_impexp\]\[element\]\[\d+\]', text)[1:]:
    name = re.search(r'<\[string8\]\[name\]\[([^\]]*)\]>', gtext).group(1)
    if name.startswith('Col'):
        continue
    for p in re.finditer(r'\[vertex_list\]\[([^\]]*)\]>\s*<\[list_uint32\]\[index_list\]\[([^\]]*)\]', gtext):
        v = np.array(p.group(1).split(), float).reshape(-1, 8)[:, :3]
        idx = np.array(p.group(2).split(), int).reshape(-1, 3)
        tp.extend((idx + n).tolist())
        tv.extend(v.tolist())
        n += len(v)
EXP_V = np.array(tv); EXP_T = np.array(tp)
print('export: %d triangles' % len(tp))

pts = np.array(verts)
lo, hi = pts.min(0), pts.max(0)
centre, radius = (lo + hi) / 2, float(np.linalg.norm(hi - lo)) / 2 + 1.0


def culled_bvh(V, Tri, d):
    """BVH of the triangles that face the viewer (n . d < 0): what a back-face-culling GPU can draw for direction d."""
    P = V[Tri]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    keep = n @ np.asarray(d) < 0
    idx = np.nonzero(keep)[0]
    bvh = BVHTree.FromPolygons([tuple(x) for x in V], [tuple(x) for x in Tri[idx]], epsilon=0.0)
    return bvh, idx


def first_hit(bvh, idx, o, d):
    loc, nrm, fi, dist = bvh.ray_cast(o, d, 2 * radius + 2.0)
    return (loc, int(idx[fi])) if loc is not None else (None, None)


dirs = []
for i in (-1, 0, 1):
    for j in (-1, 0, 1):
        for k in (-1, 0, 1):
            if (i, j, k) != (0, 0, 0):
                v = np.array([i, j, k], float)
                dirs.append(v / np.linalg.norm(v))
debug_rays = []
holes = collections.Counter()
hole_obj = collections.Counter()
wrong = collections.Counter()
total = n_hit = 0
for d0 in dirs:
    d = Vector(d0)
    sb, si = culled_bvh(SRC_V, SRC_T, d0)
    eb, ei = culled_bvh(EXP_V, EXP_T, d0)
    ref = np.array([0.0, 0.0, 1.0]) if abs(d.z) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(d, ref); u /= np.linalg.norm(u)
    w = np.cross(d, u)
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]) - centre
    ur, wr = corners @ u, corners @ w
    for uu in np.arange(ur.min(), ur.max(), STEP):
        for ww in np.arange(wr.min(), wr.max(), STEP):
            o = Vector(centre + u * uu + w * ww) - d * radius
            hs, src_face = first_hit(sb, si, o, d)
            if hs is None:
                continue
            total += 1
            he, _ = first_hit(eb, ei, o, d)
            key = tuple((np.array(hs) // 0.3).astype(int))
            if he is None:
                holes[key] += 1
                hole_obj[face_owner[src_face]] += 1
            elif (he - hs).length > TOL and (he - o).dot(d) > (hs - o).dot(d) + TOL:
                wrong[key] += 1           # a surface BEHIND the one DCS shows: the DCS surface is missing
print('rays hitting the source: %d' % total)
print('HOLES (DCS shows a surface, the export lets the ray through): %d' % sum(holes.values()))
print('FARTHER (the export shows a surface behind the DCS one): %d' % sum(wrong.values()))
for title, cnt in (('holes', holes), ('farther', wrong)):
    if title == 'holes':
        print('source objects whose surface is missing: %s' % hole_obj.most_common(8))
    print('top %s (x y z of the DCS surface, 0.3 m cells; rays):' % title)
    for key, c in cnt.most_common(14):
        print('   (%5.1f %5.1f %5.1f)  %d' % tuple(np.array(key) * 0.3 + 0.15 + [0, 0, 0]) + (c,) if False else
              '   (%5.1f %5.1f %5.1f)  %d' % (key[0] * 0.3 + 0.15, key[1] * 0.3 + 0.15, key[2] * 0.3 + 0.15, c))


# --- enclosed see-through cells along the six axes: in the source (DCS itself) and in the export ----------------
def enclosed_holes(V, Tri, ax, sign, step=0.04, rng=0.4):
    d0 = [0.0, 0.0, 0.0]; d0[ax] = float(sign)
    bvh, idx = culled_bvh(V, Tri, d0)
    u_ax, v_ax = [i for i in range(3) if i != ax]
    us = np.arange(lo[u_ax], hi[u_ax], step)
    vs = np.arange(lo[v_ax], hi[v_ax], step)
    hit = np.zeros((len(vs), len(us)), bool)
    d = Vector(d0)
    for j, vv in enumerate(vs):
        for i, uu in enumerate(us):
            o = [0.0, 0.0, 0.0]; o[u_ax] = uu; o[v_ax] = vv; o[ax] = (lo[ax] - 1.0) if sign > 0 else (hi[ax] + 1.0)
            hit[j, i] = bvh.ray_cast(Vector(o), d, hi[ax] - lo[ax] + 2.0)[0] is not None
    R = int(rng / step)
    l = np.zeros_like(hit); r = np.zeros_like(hit); up = np.zeros_like(hit); dn = np.zeros_like(hit)
    for k in range(1, R + 1):
        l[:, k:] |= hit[:, :-k]; r[:, :-k] |= hit[:, k:]; up[k:, :] |= hit[:-k, :]; dn[:-k, :] |= hit[k:, :]
    miss = ~hit & l & r & up & dn
    out = {}
    for j, i in zip(*np.nonzero(miss)):
        k = (round(us[i] / 0.2), round(vs[j] / 0.2))
        out[k] = out.get(k, 0) + 1
    return int(miss.sum()), out, (u_ax, v_ax)


print('\nenclosed see-through cells (4 cm) per axis direction: source (DCS) / export, and where only the export has them')
for ax, nm in ((0, 'x'), (1, 'y'), (2, 'z')):
    for sign in (-1, 1):
        ns, hs_, axes = enclosed_holes(SRC_V, SRC_T, ax, sign)
        ne, he_, _ = enclosed_holes(EXP_V, EXP_T, ax, sign)
        only = {k: v for k, v in he_.items() if k not in hs_}
        top = sorted(only.items(), key=lambda kv: -kv[1])[:4]
        names = 'xyz'
        print('  axis %s%s: source %4d  export %4d  export-only clusters %d %s' % (
            '-' if sign < 0 else '+', nm, ns, ne, len(only),
            ' '.join('%s=%.1f,%s=%.1f(%d)' % (names[axes[0]], k[0] * 0.2, names[axes[1]], k[1] * 0.2, v) for k, v in top)))
