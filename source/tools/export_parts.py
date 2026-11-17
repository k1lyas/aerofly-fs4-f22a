"""Generic export of an imported DCS model (.blend from edm_to_blend.py) to Aerofly converter input.

    AC=ac_su35 Blender --background <pose.blend> --python export_parts.py -- <out dir> [geometry.json]

Parts: objects whose animated ancestors include a DRIVERS argument become one part per animated node chain
("A_<nodes>"); body-driven parts are named "Body_<donor body>"; everything else is "Fuselage".
Materials come from the EDM texture references (0 diffuse, 1 normal, 2 RoughMet); glass gets the SDK-style
glass material, drawn from outside and (reversed) from inside. Writes <name>.tgi, textures and parts.json.
"""
import sys, os, re, json, math, time, importlib
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgi_write as T
import aerofly_tex as X

if os.environ.get('AC_DIR'):          # aircraft folder holding ac_<name>.py (aircraft/<name>/)
    sys.path.insert(0, os.environ['AC_DIR'])
C = importlib.import_module(os.environ.get('AC', 'ac_su35'))
args = sys.argv[sys.argv.index('--') + 1:]
OUT = args[0]
GEOM = json.load(open(args[1])) if len(args) > 1 and os.path.exists(args[1]) else None
TEX = os.path.abspath(C.TEXTURES)
os.makedirs(OUT, exist_ok=True)
GLASS_OUT, GLASS_IN, GLASS_PLAIN = 'glass_outside', 'glass_inside', 'glass_plain'
DISPLAY_MATERIAL = getattr(C, 'DISPLAY_TEXTURE', 'displays')     # render target <name>_light of the donor's displays
# Aerofly CULLS back faces (see-through shards in the F-22 game screenshots, reproduced offline with culling on),
# and so does DCS: the EDM winding is what the game shows. SINGLE_SIDED keeps every triangle as authored (oriented
# by the DCS normals, which agree with the winding for 99.9 %) and skips the clean-up passes below that assumed
# two-sided drawing (they deleted the faces that face into cavities: intakes, nozzles, gear bays).
SINGLE_SIDED = bool(getattr(C, 'SINGLE_SIDED', True))      # the old clean-up (False) is obsolete: see FIGHTER_LESSONS section 2


def int_list(s):
    return [int(a) for a in str(s).split(',') if a]


def textures(o):
    return {int(k): v for k, v in json.loads(o.get('edm_textures', '{}')).items()}


def is_burner(o):
    return bool(getattr(C, 'BURNER', None) and C.BURNER.match(o.name))


def lamp_key(o):
    """Exterior light lens / formation strip (C.LAMPS): exported self-lit, brightness from the light switches."""
    for d in getattr(C, 'LAMPS', ()):
        if (d.get('name') and re.search(d['name'], o.name)) or \
                (d.get('material') and re.search(d['material'], o.get('edm_material', ''))):
            return d['key']
    return None


def excluded(o):
    if is_burner(o):
        return bool(getattr(C, 'BURNER_DROP', False))
    if lamp_key(o):
        return False
    if getattr(C, 'HUD_GLASS', None) and o.name == C.HUD_GLASS:
        return True     # replaced by one combiner plate (hud_projection)
    if set(int_list(o.get('edm_anim_args', ''))) & set(getattr(C, 'EXCLUDE_ARGS', ())):
        return True     # parts driven by these DCS arguments (removed from the model)
    return bool(C.EXCLUDE_NAME.search(o.name) or C.EXCLUDE_MATERIAL.search(o.get('edm_material', '')) or
                C.EXCLUDE_KIND.search(o.get('edm_mat_kind', '')))


def in_cockpit(o):
    box = getattr(C, 'COCKPIT_BOX', None)
    if box is None:
        return False
    c = sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / max(len(o.data.vertices), 1)
    return all(box[0][i] <= c[i] <= box[1][i] for i in range(3))


def keep_all(o):
    """Damage stubs (ac HIDDEN_PARTS) share triangles with the intact skin they replace: drawn only one at a time, both
    keep every triangle (out of the duplicate pass both ways)."""
    return bool(o.get('aerofly_keep_all'))


_VIS = None


def edm_visibility(o):
    """DCS visibility ranges on the object's EDM chain (edm_vis.py), [] for cockpit / synthetic objects."""
    global _VIS
    if _VIS is None:
        import edm_vis
        _VIS = edm_vis.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ioEDM_dart', 'io_EDM'), C.EDM)
    if o.get('edm_source') == 'cockpit' or o.get('edm_parent_node') is None:
        return []
    return _VIS.get(int(o['edm_parent_node']), [])


def synthetic(o):
    """Objects made here (collision hulls, display quads, HUD projection) - not DCS geometry to clean up."""
    return o.name.startswith('Col') or 'aerofly_material' in o


def part_of(o):
    if o.get('aerofly_part'):            # synthetic geometry with its own part (aircraft stores: ac EXTRA_OBJECTS)
        return o['aerofly_part']
    for part, pat in getattr(C, 'STATIC_PARTS', {}).items():     # static DCS objects drawn as a part of their own
        if re.search(pat, o.name):
            return part
    if is_burner(o):
        y = sum((o.matrix_world @ v.co).y for v in o.data.vertices) / max(len(o.data.vertices), 1)
        counter = getattr(C, 'BURNER_COUNTER', None) and C.BURNER_COUNTER.match(o.name)
        static = getattr(C, 'BURNER_STATIC', None) and C.BURNER_STATIC.match(o.name)
        return ('Burner_Left' if y > 0 else 'Burner_Right') + ('_C' if static else '_B' if counter else '')
    driven = [a for a in int_list(o.get('edm_anim_args', '')) if a in C.DRIVERS and
              (not C.DRIVERS[a].get('cockpit') or in_cockpit(o))]
    lamp = lamp_key(o)
    for a in driven:
        if C.DRIVERS[a]['kind'] == 'body':
            return 'Body_' + C.DRIVERS[a]['body']
    if driven:
        return 'A_' + str(o.get('edm_anim_nodes', '')).replace(',', '_') + ('__L' + lamp if lamp else '')
    return 'L_' + lamp if lamp else 'Fuselage'


def material_of(o):
    """(aerofly material name, shader hint, texture refs, kind)"""
    kind = o.get('edm_mat_kind', '')
    tex = textures(o)
    if lamp_key(o):
        return 'lamp_' + lamp_key(o).lower(), 'standard exterior', {}, 'lamp'
    if C.GLASS_KIND.search(kind):
        # ac GLASS_PLAIN: glass that keeps the plain tint when the canopy has its own (GLASS_OUTSIDE, e.g. a coating)
        if getattr(C, 'GLASS_PLAIN', None) and C.GLASS_PLAIN.search(o.get('edm_material', '')):
            return GLASS_PLAIN, 'glass exterior', tex, kind
        return GLASS_OUT, 'glass exterior', tex, kind
    if 'aerofly_material' in o:
        if o['aerofly_material'] == GLASS_IN:
            return GLASS_IN, 'glass interior', {}, 'glass'
        if o['aerofly_material'] == 'gapfill':
            return 'gapfill', 'standard exterior', {}, 'gap'
        if o['aerofly_material'].startswith('burner:'):
            return o['aerofly_material'][7:], 'standard exterior', {}, 'burner'
        if o['aerofly_material'].startswith('store:'):     # textures from C.STORE_TEXTURES
            return o['aerofly_material'][6:], 'standard exterior', {}, 'store'
        if o['aerofly_material'].startswith('cap:'):       # display caps: textures from C.CAP_TEXTURES
            return o['aerofly_material'][4:], 'standard interior', {}, 'cap'
        return o['aerofly_material'], 'standard interior', {}, 'display'
    base = re.sub(r'[^a-z0-9_]', '_', tex.get(0, o.get('edm_material', 'material')).lower())
    interior = getattr(C, 'INTERIOR_TEXTURE', None)
    return base, 'standard interior' if interior and interior.search(tex.get(0, '')) else 'standard exterior', tex, kind


def illumination_texture(tex):
    """DCS self-lit cockpit labels: <diffuse>_i next to the diffuse texture (not referenced by the material)."""
    if not tex.get(0) or not getattr(C, 'INTERIOR_TEXTURE', None) or not C.INTERIOR_TEXTURE.search(tex[0]):
        return None
    return X.find_texture(TEX, tex[0] + '_i')


def collision_proxies(material):
    """Convex hulls from the measured geometry (not rendered; referenced by the collisionhull objects)."""
    out = {}
    pts = []
    for r in GEOM['fuselage']:
        zc, hw, hh = (r['z_min'] + r['z_max']) / 2, r['width'] / 2, (r['z_max'] - r['z_min']) / 2
        for k in range(8):
            a = k * math.pi / 4
            pts.append((r['x'], hw * math.cos(a), zc + hh * math.sin(a)))
    out['ColFuselage'] = pts
    for side, s in (('Left', 1), ('Right', -1)):
        out['ColWing' + side] = [(x, s * r['y'], z) for r in GEOM['wing'] for x in (r['le'], r['te'])
                                 for z in (r['z'] - 0.08, r['z'] + 0.08)]
        out['ColStab' + side] = [(x, s * r['y'], r['z'] + dz) for r in GEOM['stab'] for x in (r['le'], r['te'])
                                 for dz in (-0.06, 0.06)]
        out['ColFin' + side] = [(x, s * r['y'] + dy, r['z']) for r in GEOM['fin'] for x in (r['le'], r['te'])
                                for dy in (-0.08, 0.08)]
    return {n: [T.hull_object(n, p, material)] for n, p in out.items() if len(p) >= 4}


def _mesh_object(name, verts, faces, uvs, material):
    """Mesh object (not linked to the scene) with one UV per face corner; tagged as synthetic geometry."""
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    layer = bm.loops.layers.uv.new('UV')
    for f, fuv in zip(faces, uvs):
        face = bm.faces.new([vs[i] for i in f])
        for loop, uv in zip(face.loops, fuv):
            loop[layer].uv = uv
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o['aerofly_material'] = material
    return o


def _tris_world(o):
    pos = T.object_arrays(o)[0].reshape(-1, 3, 3)
    n = np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0])
    return pos, n


def _display_cap(out, name, corners, normal):
    """C.DISPLAY_CAPS {display: page}: a still picture of the screen 2 mm in front of the live one (part Cap<display>,
    material cap_<page>, textures from C.CAP_TEXTURES) - the game shows it outside the pilot's view only."""
    page = getattr(C, 'DISPLAY_CAPS', {}).get(name)
    if page:
        cc = [tuple(np.array(v) + normal * 0.002) for v in corners]
        out['Cap' + name] = [_mesh_object('Cap' + name, cc, [(0, 1, 2, 3)], [[(0, 0), (1, 0), (1, 1), (0, 1)]],
                                          'cap:cap_' + page)]


def display_quads(objs, eye):
    """One quad per C.DISPLAYS entry, 2 mm in front of the DCS screen triangles, sized to the image region's
    aspect ratio and UV-mapped into the 2048 display atlas (Blender UVs: region (x, y) from the bottom-left)."""
    out = {}
    conn = json.loads(bpy.context.scene.get('cockpit_connectors', '{}'))
    for name, d in getattr(C, 'DISPLAYS', {}).items():
        material = d.get('texture', DISPLAY_MATERIAL)
        if 'quad' in d or 'rect' in d:
            # the screen as the DCS indicator lies: connectors centre, middle of the bottom edge, middle of the right
            # edge (or a measured rectangle: centre, half right and half up vectors); the image fills it at the
            # region's aspect ratio
            if 'rect' in d:
                c, right, up = (np.array(v, float) for v in d['rect'])
            else:
                c, dn, rt = (np.array(conn[k]) for k in d['quad'])
                right, up = rt - c, c - dn
            hw, hh = np.linalg.norm(right), np.linalg.norm(up)
            right, up = right / hw, up / hh
            normal = np.cross(right, up)
            if np.dot(normal, eye - c) < 0:
                normal = -normal
            x, y, w, h = d['region']
            if 'half' in d:                 # measured half width / height of the visible glass (the picture spans it)
                hw, hh = d['half']
            elif hw / hh > float(w) / h:
                hw = hh * float(w) / h
            else:
                hh = hw * float(h) / w
            mid = c + normal * 0.002
            corners = [mid + right * sr * hw + up * su * hh for sr, su in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            S = 2048.0
            uvs = [(x / S, y / S), ((x + w) / S, y / S), ((x + w) / S, (y + h) / S), (x / S, (y + h) / S)]
            if 'warp' in d:
                # piecewise-linear image -> glass mapping: per axis knots (t, metres from the centre), t = -1 .. 1
                # across the image region; a grid of quads, the texture linear inside each
                kx, ky = d['warp']
                verts, faces, fuv = [], [], []
                for j, (ty, my) in enumerate(ky):
                    for i, (tx, mx) in enumerate(kx):
                        verts.append(tuple(mid + right * mx + up * my))
                for j in range(len(ky) - 1):
                    for i in range(len(kx) - 1):
                        q = [j * len(kx) + i, j * len(kx) + i + 1, (j + 1) * len(kx) + i + 1, (j + 1) * len(kx) + i]
                        faces.append(tuple(q))
                        fuv.append([((x + (kx[a % len(kx)][0] + 1) / 2 * w) / S, (y + (ky[a // len(kx)][0] + 1) / 2 * h) / S)
                                    for a in q])
                out[name] = [_mesh_object(name, verts, faces, fuv, material)]
            else:
                out[name] = [_mesh_object(name, [tuple(v) for v in corners], [(0, 1, 2, 3)], [uvs], material)]
            _display_cap(out, name, corners, normal)
            # zoom-click radius of the donor display: the screen only, the bezel buttons outside it stay clickable
            d['centre'], d['radius'] = mid.round(4).tolist(), round(float(min(hw, hh)), 4)
            print('display %-16s centre %s size %.3f x %.3f m normal %s' % (name, d['centre'], 2 * hw, 2 * hh,
                                                                             normal.round(2)))
            continue
        lo, hi = np.array(d['box'][0]), np.array(d['box'][1])
        pts = []
        for o in objs:
            if o.get('edm_material', '') != d['material']:
                continue
            pos, n = _tris_world(o)
            c = pos.mean(1)
            sel = np.all((c >= lo) & (c <= hi), axis=1)
            if sel.any():
                pts.append(pos[sel].reshape(-1, 3))
        if not pts:
            print('WARNING display %s: no screen triangles in its box' % name)
            continue
        p = np.vstack(pts)
        ctr = p.mean(0)
        # plane normal = smallest principal axis, turned towards the pilot's eye
        _, _, vt = np.linalg.svd(p - ctr)
        normal = vt[2] if np.dot(vt[2], eye - ctr) > 0 else -vt[2]
        ref = np.array([0.0, 0.0, 1.0]) if abs(normal[2]) < 0.7 else np.array([1.0, 0.0, 0.0])
        up = ref - normal * np.dot(ref, normal)
        up /= np.linalg.norm(up)
        right = np.cross(up, normal)          # the pilot's right on the screen
        r, u = (p - ctr) @ right, (p - ctr) @ up
        r0, r1, u0, u1 = r.min(), r.max(), u.min(), u.max()
        x, y, w, h = d['region']
        aspect = float(w) / h
        cw, ch = r1 - r0, u1 - u0
        if cw / ch > aspect:
            cw = ch * aspect
        else:
            ch = cw / aspect
        mid = ctr + right * (r0 + r1) / 2 + up * (u0 + u1) / 2 + normal * 0.002
        corners = [mid + right * sr * cw / 2 + up * su * ch / 2 for sr, su in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        S = 2048.0
        uvs = [(x / S, y / S), ((x + w) / S, y / S), ((x + w) / S, (y + h) / S), (x / S, (y + h) / S)]
        out[name] = [_mesh_object(name, [tuple(v) for v in corners], [(0, 1, 2, 3)], [uvs], material)]
        _display_cap(out, name, corners, normal)
        d['centre'], d['radius'] = mid.round(4).tolist(), round(float(np.hypot(cw, ch) / 2), 4)
        print('display %-16s centre %s size %.3f x %.3f m normal %s' % (name, d['centre'], cw, ch, normal.round(2)))
    return out


HUD_GEOM = {}      # centre / radius of the HUD projection (the donor's HUD display window is placed there)


def hud_projection(eye):
    """The HUD glass of the DCS model is 3 plates x 2 faces; as Aerofly glass (+ inside copies) that stacked up to
    a milky pane hiding the symbology. Only the largest plate is kept, its pilot side only: once as glass
    (HudCombiner) and 2 mm closer to the eye as the projection surface of the collimated HUD (HudProjection)."""
    name = getattr(C, 'HUD_GLASS', None)
    src = bpy.data.objects.get(name) if name else None
    if src is None:
        return {}
    pos, n = _tris_world(src)
    area = np.linalg.norm(n, axis=1) / 2
    unit = n / (2 * area[:, None] + 1e-12)
    facing = np.einsum('ij,ij->i', unit, eye - pos.mean(1)) > 0
    # plates = groups of eye-facing triangles with the same plane (normal and offset)
    plates = {}
    for t in np.nonzero(facing & (area > 1e-8))[0]:
        key = tuple(np.round(unit[t], 1)) + (round(float(np.dot(unit[t], pos[t, 0])), 2),)
        plates.setdefault(key, []).append(t)
    best = max(plates.values(), key=lambda ts: area[ts].sum())
    tris = pos[best]
    normal = unit[best].mean(0)
    normal /= np.linalg.norm(normal)
    faces = [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))]
    uvs = [[(0.0, 0.0)] * 3 for _ in faces]
    glass = [tuple(v) for v in tris.reshape(-1, 3)]
    # projection surface: a rectangle in the plate's plane, larger than the glass (the symbology is collimated, the
    # surface only decides where it can be seen; the plate alone cut off the heading tape, the side boxes and the
    # flight path vector on approach). Margins (left/right, down, up) in metres from C.HUD_MARGINS.
    pts = tris.reshape(-1, 3)
    ctr = pts.mean(0)
    up = np.array([0.0, 0.0, 1.0]) - normal * normal[2]
    up /= np.linalg.norm(up)
    right = np.cross(up, normal)
    r, u = (pts - ctr) @ right, (pts - ctr) @ up
    side, down, top = getattr(C, 'HUD_MARGINS', (0.0, 0.0, 0.0))
    r0, r1, u0, u1 = r.min() - side, r.max() + side, u.min() - down, u.max() + top
    proj = [tuple(ctr + right * a + up * b + normal * 0.002) for a, b in ((r0, u0), (r1, u0), (r1, u1), (r0, u1))]
    mid = ctr + right * (r0 + r1) / 2 + up * (u0 + u1) / 2
    HUD_GEOM.update(centre=mid.round(4).tolist(), radius=round(float(np.hypot(r1 - r0, u1 - u0) / 2), 4))
    print('hud projection: 1 of %d plates, %d triangles, %.4f m2; projection %.3f x %.3f m, centre %s'
          % (len(plates), len(best), area[best].sum(), r1 - r0, u1 - u0, HUD_GEOM['centre']))
    out = {'HudProjection': [_mesh_object('HudProjection', proj, [(0, 1, 2, 3)], [[(0.0, 0.0)] * 4], 'hud')],
           'HudCombiner': [_mesh_object('HudCombiner', glass, faces, uvs, GLASS_IN)]}
    # ac HUD_LAYERS > 1: further projection surfaces 1 mm apart towards the eye, each drawn by its own graphics_hud
    # (the game refuses one geometry in two graphics objects) - the HUD light adds up, for a brighter HUD
    for k in range(2, getattr(C, 'HUD_LAYERS', 1) + 1):
        layer = [tuple(np.array(p) + normal * 0.001 * (k - 1)) for p in proj]
        out['HudProjection%d' % k] = [_mesh_object('HudProjection%d' % k, layer, [(0, 1, 2, 3)], [[(0.0, 0.0)] * 4], 'hud')]
    return out


def gap_plates(parts, info):
    """Dark plates on the mid-thickness surface of thin structure (C.GAP_PLATES): one per moving surface (in its own
    part, so it moves with it) and one per fixed box (part Fuselage). Grid nodes cast a ray along the plate normal
    from both sides of the part's own geometry; cells whose four corners have a skin thickness inside the range and
    a smooth mid surface become two triangles."""
    from mathutils.bvhtree import BVHTree
    cfg = getattr(C, 'GAP_PLATES', None)
    if not cfg:
        return {}
    step, (tmin, tmax) = cfg['step'], cfg['thickness']
    jobs = []
    for p, members in parts.items():
        args = set(info.get(p, {}).get('args', []))
        if p.startswith(('A_', 'Body_')) and args & set(cfg['args']):
            jobs.append((p, 1 if args & set(cfg.get('vertical_args', [])) else 2, None))
    jobs += [('Fuselage', f['axis'], f['box']) for f in cfg.get('fixed', [])]
    out = {}
    for n, (p, axis, box) in enumerate(jobs):
        tris = [_tris_world(o)[0] for o in parts[p] if o.type == 'MESH' and not synthetic(o)]
        if not tris:
            continue
        tri = np.concatenate(tris)
        if box is not None:
            lo, hi = np.array(box[0]), np.array(box[1])
            c = tri.mean(1)
            tri = tri[np.all((c >= lo - 0.5) & (c <= hi + 0.5), 1)]
        else:
            lo, hi = tri.reshape(-1, 3).min(0) - 0.05, tri.reshape(-1, 3).max(0) + 0.05
        if not len(tri):
            continue
        verts = tri.reshape(-1, 3).tolist()
        bvh = BVHTree.FromPolygons(verts, [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tri))], epsilon=0.0)
        u_ax, v_ax = [a for a in range(3) if a != axis]
        us = np.arange(lo[u_ax], hi[u_ax] + step, step)
        vs = np.arange(lo[v_ax], hi[v_ax] + step, step)
        mid = np.full((len(us), len(vs)), np.nan)
        dn = Vector([0.0, 0.0, 0.0]); dn[axis] = -1.0
        up = Vector([0.0, 0.0, 0.0]); up[axis] = 1.0
        span = float(hi[axis] - lo[axis]) + 1.0
        for i, u in enumerate(us):
            for j, v in enumerate(vs):
                o1 = Vector([0.0, 0.0, 0.0]); o1[u_ax] = u; o1[v_ax] = v; o1[axis] = hi[axis] + 0.5
                o2 = o1.copy(); o2[axis] = lo[axis] - 0.5
                h1 = bvh.ray_cast(o1, dn, span)[0]
                h2 = bvh.ray_cast(o2, up, span)[0]
                if h1 is None or h2 is None:
                    continue
                t = h1[axis] - h2[axis]
                if tmin <= t <= tmax:
                    mid[i, j] = (h1[axis] + h2[axis]) / 2
        pts, faces = [], []
        index = {}
        def vid(i, j):
            if (i, j) not in index:
                q = [0.0, 0.0, 0.0]; q[u_ax] = us[i]; q[v_ax] = vs[j]; q[axis] = mid[i, j]
                index[(i, j)] = len(pts); pts.append(tuple(q))
            return index[(i, j)]
        for i in range(len(us) - 1):
            for j in range(len(vs) - 1):
                c4 = mid[i:i + 2, j:j + 2]
                if np.isnan(c4).any() or np.ptp(c4) > 0.06:
                    continue
                a, b, c_, d = vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)
                faces += [(a, b, c_), (a, c_, d)]
        if faces:
            name = 'Gap_%s_%d' % (p, n)
            o = _mesh_object(name, pts, faces, [[(0.0, 0.0)] * 3] * len(faces), 'gapfill')
            out.setdefault(p, []).append(o)
            print('gap plate %-24s axis %d: %d triangles' % (name, axis, len(faces)))
    return out


def burner_sleeves():
    """Open tubes inside the nozzles (C.BURNER_SLEEVES) with the burner flame texture: parts Burner_<side> and
    Burner_<side>_B, spun in opposite directions by make_su35.py (the Concorde's reheat 'Dimrotor' sleeves)."""
    cfg = getattr(C, 'BURNER_SLEEVES', None)
    if not cfg:
        return {}
    out = {}
    n, prof = cfg['segments'], cfg['profile']
    length = sum(math.hypot(prof[k + 1][0] - prof[k][0], prof[k + 1][1] - prof[k][1]) for k in range(len(prof) - 1))
    for side, (_, cy, cz) in C.BURNER_AXIS.items():
        for k, inset in enumerate(cfg['inset']):
            verts, faces, uvs = [], [], []
            vpos = [0.0]
            for m in range(len(prof) - 1):
                vpos.append(vpos[-1] + math.hypot(prof[m + 1][0] - prof[m][0], prof[m + 1][1] - prof[m][1]) / length)
            rings = len(prof)
            for i in range(n + 1):
                a = 2 * math.pi * i / n
                for x, r in prof:
                    r -= inset
                    verts.append((x, cy + r * math.cos(a), cz + r * math.sin(a)))
            for i in range(n):
                u0, u1 = 3.0 * i / n, 3.0 * (i + 1) / n
                for m in range(rings - 1):
                    a, b = i * rings + m, i * rings + m + 1
                    c, d = (i + 1) * rings + m + 1, (i + 1) * rings + m
                    faces.append((a, b, c, d))
                    uvs.append([(u0, vpos[m]), (u0, vpos[m + 1]), (u1, vpos[m + 1]), (u1, vpos[m])])
            pname = 'Burner_' + side + ('' if k == 0 else '_B')
            out.setdefault(pname, []).append(_mesh_object('Sleeve_%s_%d' % (side, k), verts, faces, uvs,
                                                          'burner:' + cfg['material']))
    return out


def write_preview_blend(path, exported, materials, mat_src):
    """The triangles exactly as exported (after de-duplication), one object per source object, textured with the
    DCS diffuse - render it with backface culling off to see what Aerofly will draw."""
    mats = {}
    for i, (n, hint) in enumerate(materials):
        m = bpy.data.materials.new('pv_' + n)
        m.use_nodes = True
        tex = mat_src.get(n, ({}, '', 1.0))[0]
        f = X.find_texture(TEX, tex.get(0, '')) if tex else None
        if f:
            node = m.node_tree.nodes.new('ShaderNodeTexImage')
            node.image = bpy.data.images.load(f, check_existing=True)
            m.node_tree.links.new(node.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        mats[i] = m
    coll = bpy.data.collections.new('exported')
    bpy.context.scene.collection.children.link(coll)
    for o, mi, pos, uv in exported:
        n = len(pos) // 3
        me = bpy.data.meshes.new('pv')
        me.from_pydata([tuple(p) for p in pos], [], [(3 * t, 3 * t + 1, 3 * t + 2) for t in range(n)])
        layer = me.uv_layers.new()
        for li, loop in enumerate(me.loops):
            u, v = uv[loop.vertex_index]
            layer.data[li].uv = (u, 1.0 - v)
        me.materials.append(mats[mi])
        ob = bpy.data.objects.new('pv_' + o.name, me)
        ob['aerofly_part'] = part_of(o)                    # (for pictures of the moving controls in their end positions)
        if o.get('aerofly_hinge'):
            ob['aerofly_hinge'] = o['aerofly_hinge']
        coll.objects.link(ob)
    for c in list(bpy.data.collections):
        if c.name != 'exported':
            c.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path), copy=True)
    print('preview blend written:', path)


def remove_faces():
    """ac REMOVE_FACES (tools/face_filter.py): faces of the given DCS material with their centre inside the region are
    deleted (details merged into a larger object, e.g. decorative lenses and their panel)."""
    import bmesh
    import face_filter as FF
    for entry in getattr(C, 'REMOVE_FACES', ()):
        n = 0
        for o in bpy.data.collections[C.COLLECTION].objects:
            if o.type != 'MESH':
                continue
            names = [m.name if m else '' for m in o.data.materials] or ['']
            if not any(FF.matches(entry, s) for s in names + [o.get('edm_material', '')]):
                continue
            bm = bmesh.new()
            bm.from_mesh(o.data)
            gone = [f for f in bm.faces
                    if FF.matches(entry, names[min(f.material_index, len(names) - 1)] or o.get('edm_material', '')) and
                    FF.face_inside(entry, [o.matrix_world @ v.co for v in f.verts])]
            if gone:
                bmesh.ops.delete(bm, geom=gone, context='FACES')
                bm.to_mesh(o.data)
                n += len(gone)
            bm.free()
        print('parts: removed %d faces of %s (%s)' % (n, entry['material'], entry.get('note', '')))


def within_radius(k, verts):
    """ac KNOB_PARTS radius=((y, z), r): only faces inside a cylinder along x as well as the box (a fan inside its fixed ring)."""
    if 'radius' not in k:
        return True
    (cy, cz), r = k['radius']
    return all(math.hypot(v.y - cy, v.z - cz) < r for v in verts)


def within_cylinder(k, verts):
    """ac KNOB_PARTS cylinder=((point), (axis), r): only faces within r of the line through point along axis (a knob on
    its mount plate, a button inside its guard ring)."""
    if 'cylinder' not in k:
        return True
    p, a, r = k['cylinder']
    for v in verts:
        d = (v.x - p[0], v.y - p[1], v.z - p[2])
        t = d[0] * a[0] + d[1] * a[1] + d[2] * a[2]
        if (d[0] - a[0] * t) ** 2 + (d[1] - a[1] * t) ** 2 + (d[2] - a[2] * t) ** 2 > r * r:
            return False
    return True


def whole_pieces(k, bm, sel):
    """ac KNOB_PARTS whole=True: only connected pieces of the object that are selected as a whole go (a piece of the
    housing with some faces inside the box or the cylinder stays in one piece)."""
    if not k.get('whole'):
        return sel
    ids = {f.index for f in sel}
    keep, seen = [], set()
    for f in sel:
        if f.index in seen:
            continue
        comp, stack, ok = [], [f], True
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for v in g.verts:
                for g2 in v.link_faces:
                    if g2.index not in seen:
                        seen.add(g2.index)
                        stack.append(g2)
                        if g2.index not in ids:
                            ok = False
        if ok:
            keep += [g for g in comp if g.index in ids]
    return keep


def above_plane(k, verts):
    """ac KNOB_PARTS above=((normal), base, h): only faces reaching h or more above the plane normal . p = base with
    their highest vertex (a toggle's bat and ball move, its nut and guard stay - they share one DCS object; by the
    centre, the bat's long stem faces from the nut up stayed behind as slivers in the turned switch)."""
    if 'above' not in k:
        return True
    n, base, h = k['above']
    return max(v.x * n[0] + v.y * n[1] + v.z * n[2] for v in verts) - base >= h


def island_filter(k, bm, sel, M):
    """ac KNOB_PARTS island_top=h: whole connected pieces (edge-linked among the box's faces) whose top reaches h above
    the plane of 'above' go; the rest stay (a toggle's nut dome is a few loose pieces up to ~9 mm, its top vertices
    reached the 7 mm face criterion: some went with the bat, the nut was left with holes - black triangles, 2026-11-05)."""
    if 'island_top' not in k:
        return sel
    n, base, _ = k['above']
    h = lambda f: max(sum(a * b for a, b in zip(M @ v.co, n)) for v in f.verts) - base
    ids = {f.index for f in sel}
    keep, seen = [], set()
    for f in sel:
        if f.index in seen:
            continue
        comp, stack = [], [f]
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for g2 in e.link_faces:
                    if g2.index in ids and g2.index not in seen:
                        seen.add(g2.index)
                        stack.append(g2)
        if max(h(g) for g in comp) >= k['island_top']:
            keep += comp
    return keep


def extract_knobs():
    """ac KNOB_PARTS [dict(part='K_<name>', material=<regex>, box=((lo), (hi)), axis=(xyz), ...)]: faces of a static
    control merged into a larger DCS object (no animation argument), e.g. a thumbwheel, become a part of their own,
    turned by make_<name>.py about its axis. The pivot is fitted to the faces' vertices (circle in the plane across the
    axis, least squares): the control turns about its own centre."""
    import bmesh
    import face_filter as FF
    coll = bpy.data.collections[C.COLLECTION]
    for k in getattr(C, 'KNOB_PARTS', ()):
        entry = dict(material=k['material'], box=k['box'])
        pieces, pts = [], []
        for o in list(coll.objects):
            if o.type != 'MESH' or o.get('aerofly_part'):
                continue
            names = [m.name if m else '' for m in o.data.materials] or ['']
            bm = bmesh.new()
            bm.from_mesh(o.data)
            sel = [f for f in bm.faces
                   if FF.matches(entry, names[min(f.material_index, len(names) - 1)] or o.get('edm_material', '')) and
                   FF.face_inside(entry, [o.matrix_world @ v.co for v in f.verts]) and
                   within_radius(k, [o.matrix_world @ v.co for v in f.verts]) and
                   within_cylinder(k, [o.matrix_world @ v.co for v in f.verts]) and
                   ('island_top' in k or above_plane(k, [o.matrix_world @ v.co for v in f.verts])) and
                   k.get('select', lambda vs: True)([o.matrix_world @ v.co for v in f.verts])]
            sel = island_filter(k, bm, sel, o.matrix_world)
            sel = whole_pieces(k, bm, sel)
            if not sel:
                bm.free()
                continue
            keep = bm.copy()                       # the knob: a copy of the object with only the selected faces
            idx = {f.index for f in sel}
            keep.faces.ensure_lookup_table()
            bmesh.ops.delete(keep, geom=[f for f in keep.faces if f.index not in idx], context='FACES')
            bmesh.ops.delete(bm, geom=sel, context='FACES')
            bm.to_mesh(o.data)
            bm.free()
            me = o.data.copy()
            keep.to_mesh(me)
            keep.free()
            ob = o.copy()
            ob.data = me
            for key in ('edm_anim_args', 'edm_anim_nodes'):
                if key in ob:
                    del ob[key]
            ob['aerofly_part'] = k['part']
            coll.objects.link(ob)
            pieces.append(ob)
            pts += [tuple(ob.matrix_world @ v.co) for v in me.vertices]
        if not pts:
            print('WARNING knob %s: no faces in %s' % (k['part'], k['box']))
            continue
        P = np.array(pts)
        ax = np.array(k['axis'], float) / np.linalg.norm(k['axis'])
        e1 = np.cross(ax, [0.0, 0.0, 1.0] if abs(ax[2]) < 0.9 else [1.0, 0.0, 0.0])
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(ax, e1)
        u, v = P @ e1, P @ e2
        A = np.c_[2 * u, 2 * v, np.ones_like(u)]
        (cu, cv, c0), *_ = np.linalg.lstsq(A, u * u + v * v, rcond=None)
        r = math.sqrt(max(c0 + cu * cu + cv * cv, 0.0))
        pivot = cu * e1 + cv * e2 + ax * float((P @ ax).mean())
        resid = np.abs(np.hypot(u - cu, v - cv) - r)
        if 'pivot' in k:         # known centre: a fit to all the vertices of a fan means little
            pivot = np.array(k['pivot'], float)
        hinge = dict(pivot=[round(float(x), 5) for x in pivot], axis=[float(x) for x in ax], radius=round(r, 4))
        for ob in pieces:
            ob['aerofly_hinge'] = json.dumps(hinge)
        print('parts: knob %s from %d objects, %d vertices, radius %.4f m (fit residual median %.4f), pivot %s'
              % (k['part'], len(pieces), len(P), r, float(np.median(resid)), hinge['pivot']))


def press_parts():
    """ac PRESS_PARTS [dict(part='P_<name>', point=<connector name or (x, y, z)>, ...)]: a key that is an object of its
    own in the DCS cockpit (static there) - the cockpit object at its click point becomes a part of its own, which
    make_<name>.py pushes in while the key is held. Only whole small objects (under 5 cm) without a DCS animation."""
    keys = [k for k in getattr(C, 'PRESS_PARTS', ()) if not k.get('cut')]      # (cut: pieces of a larger object, extract_knobs)
    if not keys:
        return
    conn = json.loads(bpy.context.scene.get('cockpit_connectors', '{}'))
    coll = bpy.data.collections[C.COLLECTION]
    cands = []
    for o in coll.objects:
        if o.type != 'MESH' or o.get('aerofly_part') or o.get('edm_source') != 'cockpit' or not len(o.data.polygons):
            continue
        if int_list(o.get('edm_anim_args', '')) or excluded(o) or lamp_key(o):
            continue
        w = [o.matrix_world @ v.co for v in o.data.vertices]
        lo = [min(v[i] for v in w) for i in range(3)]
        hi = [max(v[i] for v in w) for i in range(3)]
        if max(h - l for l, h in zip(lo, hi)) <= 0.05:
            cands.append((o, lo, hi))
    done, missing = 0, []
    for k in keys:
        p = conn.get(k['point']) if isinstance(k['point'], str) else k['point']
        best = None
        for o, lo, hi in cands:
            if o.get('aerofly_part') or p is None:
                continue
            d = math.sqrt(sum(max(l - x, 0.0, x - h) ** 2 for x, l, h in zip(p, lo, hi)))
            if d <= 0.008 and (best is None or d < best[0]):
                best = (d, o)
        if best is None:
            missing.append(k['part'])
            continue
        best[1]['aerofly_part'] = k['part']
        done += 1
    print('parts: %d of %d keys are parts of their own (PRESS_PARTS)%s'
          % (done, len(keys), ('; WARNING no object at: ' + ', '.join(missing)) if missing else ''))


def attach_legends():
    """ac LEGEND_MATERIAL: the lettering of a key is a flat object of its own (DCS material F22_SCREEN) lying a fraction
    of a millimetre over the key's face. It joins the key's part - left in the fuselage it stayed in the air while
    the key went in under it (user 2026-11-17, every ICP key). A legend is a small cockpit object without animation
    whose box lies inside the box of a key (PRESS_PARTS) or of a part marked legend=True (KNOB_PARTS: the rockers)."""
    pat = getattr(C, 'LEGEND_MATERIAL', None)
    if not pat:
        return
    hosts_ok = {k['part'] for k in getattr(C, 'PRESS_PARTS', ())} | {k['part'] for k in getattr(C, 'KNOB_PARTS', ()) if k.get('legend')}
    coll = bpy.data.collections[C.COLLECTION]

    def box(o):
        w = [o.matrix_world @ v.co for v in o.data.vertices]
        return [min(v[i] for v in w) for i in range(3)], [max(v[i] for v in w) for i in range(3)]
    hosts = [(o, *box(o)) for o in coll.objects if o.type == 'MESH' and o.get('aerofly_part') in hosts_ok and len(o.data.polygons)]
    done, parts = 0, set()
    for o in coll.objects:
        if o.type != 'MESH' or o.get('aerofly_part') or not len(o.data.polygons) or o.get('edm_source') != 'cockpit':
            continue
        if not re.search(pat, o.get('edm_material', '')) or int_list(o.get('edm_anim_args', '')):
            continue
        lo, hi = box(o)
        if max(h - l for l, h in zip(lo, hi)) > 0.03:
            continue
        for h, hlo, hhi in hosts:
            if all(hlo[i] - 0.0015 <= lo[i] and hi[i] <= hhi[i] + 0.0015 for i in range(3)):
                o['aerofly_part'] = h['aerofly_part']
                if h.get('aerofly_hinge'):
                    o['aerofly_hinge'] = h['aerofly_hinge']
                done += 1
                parts.add(h['aerofly_part'])
                break
    missing = sorted(hosts_ok - parts - {k['part'] for k in getattr(C, 'PRESS_PARTS', ()) if k.get('blank')})
    print('parts: %d key legends joined their keys (%d keys); keys without a legend: %d' % (done, len(parts), len(missing)))


def main():
    t0 = time.time()
    remove_faces()
    extract_knobs()
    press_parts()
    attach_legends()
    coll = bpy.data.collections[C.COLLECTION]
    objs = [o for o in coll.objects if o.type == 'MESH' and len(o.data.polygons) and not excluded(o)]
    if getattr(C, 'EXTRA_OBJECTS', None):     # aircraft-specific synthetic geometry (e.g. formation light panels)
        objs = objs + C.EXTRA_OBJECTS(objs, _mesh_object, X, TEX)
    # damage stubs: DCS objects hidden in the export pose (shown at a damage argument >= 1), each in a part of its own
    hidden = bpy.data.collections.get('hidden_by_dcs_visibility')
    for pat, pname in getattr(C, 'HIDDEN_PARTS', {}).items():
        found = [o for o in (hidden.all_objects if hidden else []) if o.type == 'MESH' and re.search(pat, o.name)
                 and len(o.data.polygons)]
        if not found:
            raise SystemExit('HIDDEN_PARTS %s: no hidden object matches %s' % (pname, pat))
        for o in found:
            o['aerofly_part'], o['aerofly_keep_all'] = pname, 1
        objs = objs + found
        print('hidden part %-14s %s' % (pname, ', '.join(o.name for o in found)))
    parts, info = {}, {}
    body_parts = {}
    grouped = []
    for o in objs:
        p = part_of(o)
        # breakable pieces (ac PART_BODY: a wing console, a fin) twice: '<part>__K<body>' drawn on the fuselage while the
        # part holds (a sprung body moves centimetres against the fuselage: gaps, in-game 2026-11-11), '<part>__B<body>'
        # on the body once it is torn off. One geometry cannot be drawn by two graphics objects: two parts, the same
        # triangles (arrays cached per object below)
        b = C.PART_BODY(o, edm_visibility(o)) if getattr(C, 'PART_BODY', None) else None
        if b:
            for tag in ('K', 'B'):
                grouped.append(('%s__%s%s' % (p, tag, b), o))
            body_parts[p + '__B' + b] = body_parts.get(p + '__B' + b, 0) + len(o.data.polygons)
        else:
            grouped.append((p, o))
    for p, o in grouped:
        parts.setdefault(p, []).append(o)
        e = info.setdefault(p, {'nodes': str(o.get('edm_anim_nodes', '')), 'args': [], 'parent_nodes': []})
        e['args'] = sorted(set(e['args']) | set(int_list(o.get('edm_anim_args', ''))))
        pn = int(o.get('edm_parent_node', -1))
        if pn not in e['parent_nodes']:
            e['parent_nodes'].append(pn)
        if o.get('aerofly_hinge'):          # a static control made a turning part (extract_knobs)
            e['hinge'] = json.loads(o['aerofly_hinge'])
        if p.startswith('A_'):           # extent of animated parts (cockpit click volumes are placed on them)
            w = [o.matrix_world @ v.co for v in o.data.vertices]
            lo = [min(v[i] for v in w) for i in range(3)]
            hi = [max(v[i] for v in w) for i in range(3)]
            if 'bbox' in e:
                lo = [min(a, b) for a, b in zip(lo, e['bbox'][0])]
                hi = [max(a, b) for a, b in zip(hi, e['bbox'][1])]
            e['bbox'] = [[round(x, 4) for x in lo], [round(x, 4) for x in hi]]

    for p, n in sorted(body_parts.items()):
        print('body part %-40s %6d polygons' % (p, n))
    # cockpit displays and HUD projection (synthetic parts; display content is drawn by the game)
    eye = np.array(C.MEASURE.get('eye', [0.0, 0.0, 0.0]), float)
    for pname, members in list(display_quads(objs, eye).items()) + list(hud_projection(eye).items()):
        parts[pname] = members
        info[pname] = {'nodes': '', 'args': [], 'parent_nodes': [], 'display': getattr(C, 'DISPLAYS', {}).get(pname, {})}
        if pname.startswith('Cap'):
            info[pname]['cap'] = pname[3:]
        if pname == 'HudProjection':
            info[pname]['hud'] = dict(HUD_GEOM)
        objs = objs + members

    # afterburner sleeves (spinning flame walls inside the nozzles)
    for pname, members in burner_sleeves().items():
        parts[pname] = parts.get(pname, []) + members
        info.setdefault(pname, {'nodes': '', 'args': [], 'parent_nodes': []})
        objs = objs + members

    # gap plates (moving surfaces carry their own, fixed structure in part Fuselage)
    for pname, members in gap_plates(parts, info).items():
        parts[pname] = parts[pname] + members
        objs = objs + members

    # materials: index order of first use; glass also gets the inside copy
    materials, mat_index, mat_src = [], {}, {}
    for o in objs:
        n, hint, tex, kind = material_of(o)
        if n not in mat_index:
            mat_index[n] = len(materials)
            materials.append((n, hint))
            mat_src[n] = (tex, 'burner' if is_burner(o) else kind, float(o.get('edm_normal_value', 1.0)))
            if is_burner(o) or kind in ('display', 'lamp', 'burner') or illumination_texture(tex):
                T.LUMINANCE_MATERIALS.add(n)
        if o.get('edm_source') == 'cockpit':
            T.FINE_MATERIALS.add(mat_index[n])      # fine weld for the cockpit's sub-millimetre detail
        if n in (GLASS_OUT, GLASS_PLAIN) and GLASS_IN not in mat_index:      # their inside copies
            mat_index[GLASS_IN] = len(materials)
            materials.append((GLASS_IN, 'glass interior'))
    hull_mat = bpy.data.materials.new('collision')
    if GEOM:
        parts.update(collision_proxies(hull_mat))
        mat_index.setdefault('collision', mat_index[next(n for n, _ in materials if n not in (GLASS_OUT, GLASS_IN, GLASS_PLAIN))])

    # DCS models carry some surfaces twice (same triangles, same facing, often a different UV set); in Aerofly
    # both are drawn and z-fight ("glitter" on the wings). Keep the first copy of every facing triangle.
    seen_tris = set()
    dropped = [0]

    # Duplicate keys: corners on a 2 mm grid catch the exterior skin's doubled panels (~1e-5 m noise), but in the
    # cockpit model the parts themselves are millimetres in size - neighbouring bevel / knob / switch-tip triangles
    # shared 2 mm keys and 20 % of the cockpit (79 000 triangles) was dropped as "duplicates": the black wedges and
    # crooked buttons. Cockpit objects are keyed at 0.01 mm (real duplicates only: 300 triangles).
    def quantum(o):
        return 1e-5 if o.get('edm_source') == 'cockpit' else 0.002

    def tri_keys(p, quantum=0.002):
        q = np.round(p / quantum).astype(np.int64)
        face_n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        unit = face_n / (np.linalg.norm(face_n, axis=1, keepdims=True) + 1e-12)
        corners = [tuple(sorted(map(tuple, q[t]))) for t in range(len(p))]
        signs = [tuple(np.sign(np.round(unit[t], 1)).astype(int)) for t in range(len(p))]
        return corners, signs, unit

    # Back-to-back copies (same triangle, opposite facing) are the two sides of a skin panel in DCS, which culls
    # back faces; Aerofly draws both sides, so they z-fight. Keep the copy whose normal points out of the
    # aircraft: a ray along the inward copy's normal hits the airframe, the outward one escapes.
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    all_tris = {}
    owner = {}
    tri_pts = []
    verts, polys = [], []
    for o in (o for ms in parts.values() for o in ms if not synthetic(o) and not keep_all(o)):
        pos = T.object_arrays(o)[0]
        p = pos.reshape(-1, 3, 3)
        base = len(verts)
        verts.extend(map(tuple, pos))
        polys.extend((base + 3 * t, base + 3 * t + 1, base + 3 * t + 2) for t in range(len(p)))
        corners, signs, unit = tri_keys(p, quantum(o))
        opaque = material_of(o)[0] not in (GLASS_OUT, GLASS_PLAIN, 'ruid_number', 'su35_numbers')
        for t in range(len(p)):
            all_tris.setdefault(corners[t], []).append((signs[t], unit[t], p[t].mean(0)))
            tri_pts.append((corners[t], signs[t], unit[t], p[t], opaque))
            # same triangle, same facing in several objects: the main skin (largest object) wins over overlays
            k = (corners[t], signs[t])
            if k not in owner or len(p) > owner[k][1]:
                owner[k] = (o.name, len(p))
    bvh = BVHTree.FromPolygons(verts, polys, epsilon=0.0)
    inward = set()
    for corners, lst in ([] if SINGLE_SIDED else all_tris.items()):
        if len({s for s, _, _ in lst}) < 2:
            continue
        hits = {}
        for s, u, c in lst:
            loc = bvh.ray_cast(Vector(c + u * 0.005), Vector(u), 6.0)[0]
            hits[s] = loc is not None
        if any(hits.values()) and not all(hits.values()):
            inward.update((corners, s) for s, h in hits.items() if h)
    print('back-to-back triangle pairs resolved: %d inward copies dropped' % len(inward))

    # Coincident opposite surfaces that are triangulated differently (e.g. the outer wing skin and the inner
    # wall of the flap bay behind it) are missed by the corner keys above. Find them with a short ray and keep
    # the side that faces out of the solid: along the normal of an inward-facing triangle the ray leaves the
    # solid more often than it enters it (crossing sum of sign(normal . ray) > 0, hits within 1 mm merged).
    clean_v, clean_p, seen_k = [], [], set()
    for corners, sgn, u, pt, opaque in tri_pts:
        if (corners, sgn) in inward or (corners, sgn) in seen_k:
            continue
        seen_k.add((corners, sgn))
        clean_v.extend(map(tuple, pt))
        clean_p.append((len(clean_v) - 3, len(clean_v) - 2, len(clean_v) - 1))
    clean = BVHTree.FromPolygons(clean_v, clean_p, epsilon=0.0)

    def exposure(i):
        """Fraction of 17 rays (normal, 8 at 39 deg, 8 at 68 deg) that leave the aircraft; the first 1 cm is ignored, where
        decal-like overlay sheets lie on the skin."""
        if i in exp_cache:
            return exp_cache[i]
        corners, sgn, u, pt, opaque = tri_pts[i]
        c = pt.mean(0)
        t1 = np.cross(u, [0.0, 0.0, 1.0] if abs(u[2]) < 0.9 else [1.0, 0.0, 0.0])
        t1 /= np.linalg.norm(t1)
        t2 = np.cross(u, t1)
        dirs = [u] + [u + tilt * (math.cos(k * math.pi / 4 + off) * t1 + math.sin(k * math.pi / 4 + off) * t2)
                      for tilt, off in ((0.8, 0.0), (2.5, math.pi / 8)) for k in range(8)]
        free = 0
        for dv in dirs:
            dv = dv / np.linalg.norm(dv)
            if clean.ray_cast(Vector(c + dv * 0.01), Vector(dv), 30.0)[0] is None:
                free += 1
        exp_cache[i] = free / float(len(dirs))
        return exp_cache[i]

    exp_cache = {}
    near_inward = 0
    for i, (corners, sgn, u, pt, opaque) in enumerate([] if SINGLE_SIDED else tri_pts):
        if (corners, sgn) in inward:
            continue
        d, c = Vector(u), pt.mean(0)
        o, left, j = Vector(c + u * 1e-3), 2e-3, None
        for _ in range(6):      # skip same-facing duplicates inside the +-1 mm window
            loc, n, k, dist = bvh.ray_cast(o, -d, left)
            if loc is None:
                break
            if n.dot(d) < -0.9:
                j = k
                break
            o, left = loc - d * 1e-5, left - dist - 1e-5
        if os.environ.get('DEBUG_AT') and np.linalg.norm(c - np.array([float(v) for v in os.environ['DEBUG_AT'].split(',')])) < 0.05:
            print('DEBUG i', i, c.round(3), np.round(u, 2), 'partner', j, None if j is None else (np.round(tri_pts[j][3].mean(0), 3), np.round(tri_pts[j][2], 2), (tri_pts[j][0], tri_pts[j][1]) in inward))
        if j is None or (tri_pts[j][0], tri_pts[j][1]) in inward:
            continue
        # exactly one of the two sides survives (both would z-fight in Aerofly): the more exposed one, on a tie
        # the one facing away from the fuselage axis
        ei, ej = exposure(i), exposure(j)
        radial = np.array([0.0, c[1], c[2]])
        if ei < ej or (ei == ej and (np.dot(u, radial), u[2]) < (np.dot(tri_pts[j][2], radial), tri_pts[j][2][2])):
            inward.add((corners, sgn))
            near_inward += 1
    print('coincident opposite surfaces: %d inward-facing triangles dropped' % near_inward)

    # Aerofly does not cull back faces. DCS models contain inside-out slivers (e.g. at the outer wing trailing
    # edge: a downward-facing sheet 4 mm above the upward-facing skin) that DCS never shows, because from their
    # front side they are covered by another layer facing the same way, and from the back they are culled. In
    # Aerofly their back side shows through as a dark patch. Drop a triangle whose front is fully covered (at the
    # centroid and near each corner) by an opaque face facing the same way within COVER m; faces turned away
    # from that viewer are transparent to it (culled) and skipped.
    COVER = 0.01
    vis_verts, vis_polys = [], []
    for corners, sgn, u, pt, opaque in tri_pts:
        if opaque and (corners, sgn) not in inward:
            b0 = len(vis_verts)
            vis_verts.extend(map(tuple, pt))
            vis_polys.append((b0, b0 + 1, b0 + 2))
    vis = BVHTree.FromPolygons(vis_verts, vis_polys, epsilon=0.0)

    def covered_at(c, d):
        o, travelled = Vector(c), 0.0
        for _ in range(8):
            loc, n, _, dist = vis.ray_cast(o, d, COVER - travelled)
            if loc is None:
                return False
            if n.dot(d) > 0:       # same facing: it hides the triangle from a viewer on that side
                return True
            travelled += dist + 1e-4
            o = loc + d * 1e-4
        return False

    hovering = set()
    for corners, sgn, u, pt, opaque in ([] if SINGLE_SIDED else tri_pts):
        if (corners, sgn) in inward:
            continue
        d = Vector(u)
        c = pt.mean(0)
        samples = [c] + [c + 0.8 * (q - c) for q in pt]
        if all(covered_at(x + u * 5e-4, d) for x in samples):
            hovering.add((corners, sgn))
    print('covered triangles dropped (hidden in DCS): %d' % len(hovering))

    # Left/right consistency: the airframe is symmetric, so a triangle off the centreline whose mirror image
    # exists only with the opposite facing is inside out (e.g. a left outer wing panel facing down 4 mm above
    # the upward skin, where the right wing panel faces up). DCS hides such faces by culling; Aerofly would show
    # their dark back, so they are flipped. Triangles with no exact mirror image are left alone.
    kept = {(corners, sgn) for corners, sgn, u, pt, opaque in tri_pts
            if (corners, sgn) not in inward and (corners, sgn) not in hovering}

    def mirror_corners(corners):
        return tuple(sorted((x, -y, z) for x, y, z in corners))

    # of the two mismatched mirror images, the inside-out one has its front facing another face that looks
    # straight back at it within HOVER m (the skin it hovers over)
    HOVER = 0.02
    kv, kp = [], []
    for corners, sgn, u, pt, opaque in tri_pts:
        if (corners, sgn) in kept:
            kv.extend(map(tuple, pt))
            kp.append((len(kv) - 3, len(kv) - 2, len(kv) - 1))
    kbvh = BVHTree.FromPolygons(kv, kp, epsilon=0.0)
    inverted = set()
    # (mirror check: in single-sided mode only when the aircraft asks for it - MIRROR_FIX - because some mirrored DCS
    # objects carry vertex normals that disagree with their winding on one side, e.g. the Su-35 right wing)
    for corners, sgn, u, pt, opaque in ([] if SINGLE_SIDED and not getattr(C, 'MIRROR_FIX', False) else tri_pts):
        if (corners, sgn) not in kept or all(abs(y) <= 10 for _, y, _ in corners):   # centreline: no mirror
            continue
        mc = mirror_corners(corners)
        same, opposite = (sgn[0], -sgn[1], sgn[2]), (-sgn[0], sgn[1], -sgn[2])
        if (mc, same) in kept or (mc, opposite) not in kept:
            continue
        d, c = Vector(u), pt.mean(0)
        loc, n, _, _ = kbvh.ray_cast(Vector(c + u * 5e-4), d, HOVER)
        if loc is not None and n.dot(d) < -0.7:
            inverted.add((corners, sgn))
    print('inside-out triangles flipped (mirror check): %d' % len(inverted))

    def dedupe(pos, nrm, uv, oname, q=0.002):
        p = pos.reshape(-1, 3, 3)
        corners_l, signs, _ = tri_keys(p, q)
        keep = np.ones(len(p), bool)
        for t in range(len(p)):
            corners = corners_l[t]
            key = corners + (signs[t],)
            if (corners, signs[t]) in inward or (corners, signs[t]) in hovering or key in seen_tris or owner.get((corners, signs[t]), (oname,))[0] != oname:
                keep[t] = False
            else:
                seen_tris.add(key)
        # zero-area triangles from the DCS source (invisible; the converter's triangle stripping chokes on them)
        area = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
        keep &= area > 1e-9
        dropped[0] += int((~keep).sum())
        flip = np.array([(corners_l[t], signs[t]) in inverted for t in range(len(p))], bool) & keep
        if flip.any():
            order = np.arange(len(pos)).reshape(-1, 3)
            order[flip] = order[flip][:, [0, 2, 1]]
            order = order.reshape(-1)
            pos, nrm, uv = pos[order], nrm[order].copy(), uv[order]
            nrm[np.repeat(flip, 3)] *= -1.0
        k3 = np.repeat(keep, 3)
        return pos[k3], nrm[k3], uv[k3]

    def arrays(o):
        pos, nrm, uv, _ = T.object_arrays(o)
        if o.name.startswith('Col'):
            return [(mat_index['collision'], pos, nrm, uv)]
        if synthetic(o):
            return [(mat_index[material_of(o)[0]], pos, nrm, uv)]
        if keep_all(o):         # damage stubs: every triangle but the zero-area ones
            p3 = pos.reshape(-1, 3, 3)
            k3 = np.repeat(0.5 * np.linalg.norm(np.cross(p3[:, 1] - p3[:, 0], p3[:, 2] - p3[:, 0]), axis=1) > 1e-9, 3)
            return [(mat_index[material_of(o)[0]], pos[k3], nrm[k3], uv[k3])]
        pos, nrm, uv = dedupe(pos, nrm, uv, o.name, quantum(o))
        if not len(pos):
            return []
        crease = getattr(C, 'COCKPIT_NORMAL_CREASE', None)
        if crease and o.get('edm_source') == 'cockpit':
            # corner normals bent more than `crease` degrees off their triangle take the triangle's normal: the
            # cockpit model's small hard-surface parts (MFD button caps: a fan of triangles whose rim normals lean
            # into the bevel) showed dark diagonal crosses in the game (DCS hides them under its normal maps)
            p3, n3 = pos.reshape(-1, 3, 3), nrm.reshape(-1, 3, 3).copy()
            fn = np.cross(p3[:, 1] - p3[:, 0], p3[:, 2] - p3[:, 0])
            fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
            fn *= np.sign(np.einsum('ij,ij->i', fn, n3.sum(1)))[:, None]
            bent = np.einsum('ijk,ik->ij', n3, fn) < math.cos(math.radians(crease))
            n3[bent] = np.repeat(fn[:, None, :], 3, axis=1)[bent]
            nrm = n3.reshape(-1, 3)
        if os.environ.get('NORMAL_CHECK'):
            p3, n3 = pos.reshape(-1, 3, 3), nrm.reshape(-1, 3, 3)
            fn = np.cross(p3[:, 1] - p3[:, 0], p3[:, 2] - p3[:, 0])
            bad = np.einsum('ij,ij->i', fn, n3.sum(1)) < 0
            if bad.any():
                flipped.append((o.name, int(bad.sum()), len(p3), p3[bad].mean(1).round(2).tolist()))
            fu = fn / (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12)
            tilt = np.einsum('ij,ikj->ik', fu, n3).min(1) < 0.5
            if tilt.any():
                flipped.append(('TILT ' + o.name, int(tilt.sum()), len(p3), p3[tilt].mean(1).round(2).tolist()))
        n = material_of(o)[0]
        if n in (GLASS_OUT, GLASS_PLAIN):
            pos, nrm, uv = glass_outer_shell(pos, nrm, uv)
        out = [(mat_index[n], pos, nrm, uv)]
        if n in (GLASS_OUT, GLASS_PLAIN):
            out.append((mat_index[GLASS_IN],) + T.reversed_faces(pos, nrm, uv))
        return out

    def glass_outer_shell(pos, nrm, uv):
        """DCS canopies are often two coincident shells back to back (outward + inward faces). With the inside copy
        made above, the inward shell and the copy of the outward one lie in one plane facing the same way and
        z-fight (the F-22 canopy flickered by itself). Keep the triangle facing away from the glass centroid."""
        p = pos.reshape(-1, 3, 3)
        fn = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
        q = np.round(p / 0.002).astype(np.int64)
        groups = {}
        for t in range(len(p)):
            groups.setdefault(tuple(sorted(map(tuple, q[t]))), []).append(t)
        centre = p.reshape(-1, 3).mean(0)
        keep = np.ones(len(p), bool)
        for ts in groups.values():
            if len(ts) > 1 and fn[ts[0]] @ fn[ts[1]] < -0.9:
                for t in ts:
                    keep[t] = fn[t] @ (p[t].mean(0) - centre) > 0
        k3 = np.repeat(keep, 3)
        return pos[k3], nrm[k3], uv[k3]

    exported = []   # (part, material index, pos, uv) as written, for the optional preview .blend
    flipped = []    # NORMAL_CHECK: triangles whose vertex normals point against the winding

    array_cache = {}

    def arrays_logged(o):
        # an object in two parts (the breakable pieces' __K / __B copies): the second must not lose its triangles to
        # the duplicate pass as copies of the first
        if o.name not in array_cache:
            array_cache[o.name] = arrays(o)
        out = array_cache[o.name]
        if os.environ.get('PREVIEW_BLEND') and not o.name.startswith('Col'):
            exported.extend((o, mi, pos, uv) for mi, pos, nrm, uv in out)
        return out

    stats = T.write_tgi(os.path.join(OUT, C.NAME + '.tgi'), materials, parts, arrays_logged)
    if os.environ.get('PREVIEW_BLEND'):
        write_preview_blend(os.environ['PREVIEW_BLEND'], exported, materials, mat_src)
    total = sum(s[2] for s in stats.values())
    if os.environ.get('NORMAL_CHECK'):
        json.dump(flipped, open(os.environ['NORMAL_CHECK'], 'w'))
        print('NORMAL_CHECK objects with flipped normals: %d, triangles %d' % (len(flipped), sum(f[1] for f in flipped)))
    print('duplicate triangles dropped:', dropped[0])
    for p, s in sorted(stats.items(), key=lambda kv: -kv[1][2])[:12]:
        print('part %-28s objects=%4d vertices=%8d faces=%8d' % ((p,) + s))
    print('parts %d, faces %d, materials %d; tgi in %.1fs' % (len(stats), total, len(materials), time.time() - t0))

    for n, _ in ([] if os.environ.get('SKIP_TEX') else materials):
        if n in (GLASS_OUT, GLASS_IN, GLASS_PLAIN):
            X.write_glass_textures(OUT, n, n == GLASS_IN, **(getattr(C, 'GLASS_OUTSIDE', {}) if n == GLASS_OUT else {}))
            continue
        tex, kind, nstrength = mat_src[n]
        if kind == 'display':
            X.write_display_textures(OUT, n, 512 if n == 'hud' else 2048, **getattr(C, 'DISPLAY_SURFACE', {}))
            continue
        if kind == 'gap':
            X.write_flat_textures(OUT, n, C.GAP_PLATES['colour'])
            continue
        if kind == 'store':
            C.STORE_TEXTURES(OUT, n, X)
            continue
        if kind == 'cap':
            C.CAP_TEXTURES(OUT, n, X)
            continue
        if kind == 'lamp':
            key = next(d['key'] for d in C.LAMPS if 'lamp_' + d['key'].lower() == n)
            X.write_lamp_textures(OUT, n, C.LAMP_COLOURS[key], **getattr(C, 'LAMP_SURFACE', {}).get(key, {}))
            continue
        diffuse = X.find_texture(TEX, tex.get(0, '')) or (X.find_texture(TEX, n) if kind == 'burner' else None)
        if kind == 'burner' and diffuse is None:
            # texture missing in the mod (su-27_afterburn, j11a_afterburn): uniform orange glow; ac BURNER_TEXTURE: its own
            own = getattr(C, 'BURNER_TEXTURE', None)
            cold = getattr(C, 'BURNER_COLD', None)
            X.write_burner_textures(OUT, n, own(n) if own else
                                    X.procedural_burner('flame' if n == 'burner_sleeve' else 'disc' if 'j11a' in n else 'wall'),
                                    cold=cold(n) if cold else None)
            continue
        if diffuse is None:
            print('WARNING no diffuse texture for', n, tex)
            X.write_material_textures(OUT, n, np.full((64, 64, 4), 0.5, np.float32))
            continue
        if kind == 'burner':
            X.write_burner_textures(OUT, n, X.load_image(diffuse))
            continue
        nm = X.find_texture(TEX, tex[1]) if 1 in tex else None
        rm = X.find_texture(TEX, tex[2]) if 2 in tex else None
        if rm and not re.search(r'roughmet', rm, re.I):
            rm = None  # some materials reference the diffuse in slot 2
        # per-material options (ac MATERIAL_TEXTURE_OPTIONS: [(diffuse regex, options)]): roughmet_by_name - the
        # <diffuse>_RoughMet file as DCS finds it when the material lists no slot 2; height - height_from_normals args
        opts = next((o for pat, o in getattr(C, 'MATERIAL_TEXTURE_OPTIONS', ()) if re.search(pat, tex.get(0, ''), re.I)), {})
        if rm is None and opts.get('roughmet_by_name'):
            rm = X.find_texture(TEX, tex.get(0, '') + '_RoughMet')
        size = 4096 if C.FULL_RES.search(tex.get(0, '')) else 2048
        X.write_material_textures(OUT, n, X.load_image(diffuse), X.load_image(nm) if nm else None,
                                  X.load_image(rm) if rm else None, size=size,
                                  kind='chrome' if 'chrome' in kind else 'standard',
                                  normal_strength=opts.get('normal_strength', nstrength), height=opts.get('height'))
        if getattr(C, 'TEXTURE_HOOK', None):
            C.TEXTURE_HOOK(OUT, n, X)          # aircraft-specific edits of the written maps (ac_<name>.py)
        # baked cockpit light (tools/bake_cockpit_light.py): interior ambient from the geometry's AO where baked, a
        # plain level elsewhere (ac BAKE_DIR, BAKED_AMBIENT_MIN, INTERIOR_AMBIENT)
        bake_dir = getattr(C, 'BAKE_DIR', None)
        interior = getattr(C, 'INTERIOR_TEXTURE', None) and C.INTERIOR_TEXTURE.search(tex.get(0, ''))
        flood_map = None
        if bake_dir and interior:
            baked = {f.lower(): os.path.join(bake_dir, f) for f in os.listdir(bake_dir)} if os.path.isdir(bake_dir) else {}
            ao_f = baked.get(tex.get(0, '').lower() + '_ao.png', '')
            if os.path.exists(ao_f):
                ao = X.load_image(ao_f)[..., 0]
                lo = C.BAKED_AMBIENT_MIN
                X.save_png(os.path.join(OUT, n + '_ambient.png'), np.clip(lo + (1 - lo) * ao, 0, 1), limit=min(size, 2048))
            else:
                X.save_png(os.path.join(OUT, n + '_ambient.png'), np.full((64, 64), C.INTERIOR_AMBIENT, np.float32))
            fl_f = baked.get(tex.get(0, '').lower() + '_flood.png', '')
            if os.path.exists(fl_f):
                flood_map = np.clip(X.load_image(fl_f)[..., 0], 0, 1) ** getattr(C, 'FLOOD_GAMMA', 1.0)
        illum = illumination_texture(tex)
        if illum:
            X.save_png(os.path.join(OUT, n + '_light.png'), np.clip(X.load_image(illum)[..., :3], 0, 1), limit=size)
        if getattr(C, 'FLOOD_ILLUMINATION', None) and getattr(C, 'INTERIOR_TEXTURE', None) and \
                C.INTERIOR_TEXTURE.search(tex.get(0, '')):
            # LABEL_ILLUMINATION [(texture regex, channel[, mask texture])]: the alpha of the diffuse (or of the named
            # texture) is the DCS self-illumination mask of the panel lettering -> that channel of the lighting map,
            # at the texture's resolution (small text)
            masks = {e[1]: X.load_image(X.find_texture(TEX, e[2]) if len(e) > 2 else diffuse)[..., 3]
                     for e in getattr(C, 'LABEL_ILLUMINATION', ()) if e[0].search(tex.get(0, ''))}
            # FLOOD_TEXTURE: only these interior textures take the flood light (the panels it is aimed at)
            flood = getattr(C, 'FLOOD_TEXTURE', None)
            level = C.FLOOD_ILLUMINATION if flood is None or flood.search(tex.get(0, '')) else 0.0
            if flood_map is not None:          # baked flood lamps: their own light, not the flat level
                level = getattr(C, 'FLOOD_BAKED_LEVEL', C.FLOOD_ILLUMINATION)
            if level or masks:
                X.write_illumination_texture(OUT, n, level, flood_on_masks=getattr(C, 'FLOOD_ON_LABELS', 1.0), size=size if (masks or flood_map is not None) else 512,
                                             masks=masks, flood=flood_map)
    print('textures written in %.1fs' % (time.time() - t0))
    json.dump({'parts': info, 'connectors': json.loads(bpy.context.scene.get('cockpit_connectors', '{}')),
               'stats': stats, 'materials': {n: h for n, h in materials},
               'full_res': sorted(n for n, _ in materials if n in mat_src and C.FULL_RES.search(mat_src[n][0].get(0, '')))},
              open(os.path.join(OUT, 'parts.json'), 'w'), indent=1)


main()
