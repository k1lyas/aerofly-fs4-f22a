"""Sample every driven DCS animation of every exported part into rotation/translation tables.

    AC=ac_su35 Blender --background --factory-startup --python anim_tables.py -- \
        <io_EDM dir> <model.edm> - <parts.json> <geometry.json> <out anim.json>

For a part (chain of animated nodes, nearest first) and each DRIVERS argument on that chain, the world motion
relative to the export pose D(a) = W(a) W(export)^-1 is sampled with all other arguments at the export pose and
decomposed into rotations (XYZ Euler about the part pivot) + translation. Applying the per-argument motions from
the innermost node outwards reproduces the combined DCS motion exactly. Wheel spin ('spin') stores the axis, 'carry' only
the physics body that makes the motion.
Parts of a separate cockpit model (merge_cockpit.py: node ids from COCKPIT_NODE_BASE, arguments from
COCKPIT_ARG_BASE) are sampled from COCKPIT_EDM, shifted by COCKPIT_OFFSET, at COCKPIT_POSE (default all 0).
"""
import sys, os, json, math, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edm_to_blend as E
from mathutils import Matrix, Vector

if os.environ.get('AC_DIR'):          # aircraft folder holding ac_<name>.py (aircraft/<name>/)
    sys.path.insert(0, os.environ['AC_DIR'])
C = importlib.import_module(os.environ.get('AC', 'ac_su35'))
PARTS_JSON, GEOM_JSON, OUT_JSON = E.args[3:6]
parts = json.load(open(PARTS_JSON))['parts']
geo = json.load(open(GEOM_JSON))
f = E.EDMFile(E.EDM_PATH)
nodes = f.nodes
POSE = dict(C.POSE)


NODE_BASE = getattr(C, 'COCKPIT_NODE_BASE', None)
ARG_BASE = getattr(C, 'COCKPIT_ARG_BASE', 0)
if os.environ.get('COCKPIT_EDM'):
    cp_nodes = E.EDMFile(os.environ['COCKPIT_EDM']).nodes
    cp_shift = Matrix.Translation([float(v) for v in os.environ['COCKPIT_OFFSET'].split(',')])
    POSE.update({ARG_BASE + a: v for a, v in getattr(C, 'COCKPIT_POSE', {}).items()})


def is_cockpit(idx):
    return NODE_BASE is not None and idx >= NODE_BASE


def node_of(idx):
    return cp_nodes[idx - NODE_BASE] if is_cockpit(idx) else nodes[idx]


def world(node, pose, cockpit=False):
    E.ARG_VALUES.clear()
    if cockpit:
        E.ARG_VALUES.update({a - ARG_BASE: v for a, v in pose.items() if a >= ARG_BASE})
        return cp_shift @ E.EDM_TO_BLENDER @ E.world_matrix(cp_nodes, node, {})
    E.ARG_VALUES.update({a: v for a, v in pose.items() if not ARG_BASE or a < ARG_BASE})
    return E.EDM_TO_BLENDER @ E.world_matrix(nodes, node, {})


def node_args(n, cockpit=False):
    k = ARG_BASE if cockpit else 0
    return [k + a for a, _ in getattr(n, 'rotData', [])] + [k + a for a, _ in getattr(n, 'posData', [])]


def decompose(D, pivot, prev=None):
    e = D.to_3x3().to_euler('XYZ', prev) if prev else D.to_3x3().to_euler('XYZ')
    u = D.to_3x3() @ pivot + D.translation - pivot
    return e, u


out = {}
for name, info in sorted(parts.items()):
    if not name.startswith('A_'):
        continue
    chain = [int(i) for i in info['nodes'].split(',') if i]
    cockpit = is_cockpit(chain[0])
    nearest = node_of(chain[0])
    rest = world(nearest, POSE, cockpit)
    rest_inv = rest.inverted()
    pivot = rest.translation.copy()
    links = []  # innermost first
    seen = set()
    for idx in chain:
        for arg in node_args(node_of(idx), cockpit):
            if arg in seen or arg not in C.DRIVERS:
                continue
            seen.add(arg)
            d = C.DRIVERS[arg]
            if d['kind'] == 'carry':     # drawn on a physics body: the body makes the motion
                links.append({'arg': arg, 'kind': 'carry', 'body': d['body']})
                continue
            if d['kind'] == 'spin':
                pose = dict(POSE); pose[arg] = 0.25
                D = world(nearest, pose, cockpit) @ rest_inv
                q = D.to_3x3().to_quaternion()
                axis = q.axis if q.angle <= math.pi else -q.axis
                if 'angle' in d:     # engine discs: spin about their own node, angle from a dynamics value
                    links.append({'arg': arg, 'kind': 'spin', 'axis': list(axis), 'pivot': list(pivot), 'angle': d['angle']})
                    continue
                side = 'left' if pivot.y > 0.2 else 'right' if pivot.y < -0.2 else 'nose'
                wheel = next(w for w in geo['wheels'] if w['which'] == side)
                hull = d['hull'] if isinstance(d['hull'], str) else d['hull'][side]
                links.append({'arg': arg, 'kind': 'spin', 'axis': list(axis), 'pivot': wheel['center'], 'hull': hull})
                continue
            lo, hi = d['range']
            samples = [lo + (hi - lo) * i / (C.SAMPLES - 1) for i in range(C.SAMPLES)]
            eul, trn, prev = [], [], None
            for a in samples:
                pose = dict(POSE); pose[arg] = a
                e, u = decompose(world(nearest, pose, cockpit) @ rest_inv, pivot, prev)
                prev = e
                eul.append(list(e)); trn.append(list(u))
            links.append({'arg': arg, 'kind': 'table', 'samples': samples, 'euler': eul, 'translation': trn})
    out[name] = {'pivot': list(pivot), 'links': links}

json.dump(out, open(OUT_JSON, 'w'), indent=1, default=float)
print('ANIM parts', len(out))
for n, p in sorted(out.items()):
    desc = []
    for l in p['links']:
        if l['kind'] == 'spin':
            desc.append('spin%d' % l['arg'])
        elif l['kind'] == 'carry':
            desc.append('on ' + l['body'])
        else:
            span = max(abs(math.degrees(e[i] - l['euler'][0][i])) for e in l['euler'] for i in range(3))
            mv = max(math.dist(t, l['translation'][0]) for t in l['translation'])
            desc.append('a%d:%.0fdeg/%.2fm' % (l['arg'], span, mv))
    print('ANIM %-30s %s' % (n, ' '.join(desc)))
