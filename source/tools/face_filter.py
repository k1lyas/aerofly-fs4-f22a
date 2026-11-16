"""Face selection of ac REMOVE_FACES (shared by export_parts.py and bake_cockpit_light.py).

REMOVE_FACES entries: dict(material=<regex>, box=((lo xyz), (hi xyz))) - an axis-aligned box - or
dict(material=<regex>, centre=(xyz), axes=((u xyz), (v xyz), (n xyz)), ranges=((u0, u1), (v0, v1), (n0, n1))) - a box
along the given unit axes (a slanted panel); mirror_y=True adds the mirror image across the plane y = 0. A face goes
when its material matches and ALL its vertices lie inside: by the centre alone, long faces of neighbouring structure
went too (2026-10-22: 30 triangles of the ICP / UFD hood walls, 19 cm long, centred in the map light box - a
see-through hole beside the ICP keys).
"""
import re


def _regions(entry):
    if 'box' in entry:
        yield ('box', entry['box'])
        if entry.get('mirror_y'):
            (x0, y0, z0), (x1, y1, z1) = entry['box']
            yield ('box', ((x0, -y1, z0), (x1, -y0, z1)))
        return
    c, axes, ranges = entry['centre'], entry['axes'], entry['ranges']
    yield ('obox', (c, axes, ranges))
    if entry.get('mirror_y'):
        flip = lambda v: (v[0], -v[1], v[2])
        yield ('obox', (flip(c), tuple(flip(a) for a in axes), ranges))


def inside(entry, p):
    for kind, r in _regions(entry):
        if kind == 'box':
            lo, hi = r
            if all(lo[i] <= p[i] <= hi[i] for i in range(3)):
                return True
        else:
            c, axes, ranges = r
            q = [p[i] - c[i] for i in range(3)]
            if all(rg[0] <= sum(a[i] * q[i] for i in range(3)) <= rg[1] for a, rg in zip(axes, ranges)):
                return True
    return False


def matches(entry, material):
    return bool(re.search(entry['material'], material or ''))


def face_inside(entry, verts):
    """All vertices (world positions) of a face inside the region."""
    return all(inside(entry, v) for v in verts)
