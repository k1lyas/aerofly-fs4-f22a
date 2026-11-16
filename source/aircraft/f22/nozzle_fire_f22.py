"""The inside of the F-22 nozzles at afterburner, lit as the stock F/A-18 and F-15E are.

Those two do not paint a flame on one surface: f18.tmd / f15e.tmd give InputLuminance (1000 x 2 x afterburner) to the whole engine, its
rings and the inner nozzle flaps (rigidbodygraphics EngineLeft, graphics_ring InnerEjactorFlap*), real geometry with _light maps, so the
flaps carry their glow as they move. The DCS F-22 has a real engine too: a deep round duct, a disc, a ball and 10 rods (renders 2026-11-01).
The flat sheets of 2026-10-30 here hid all of that, which is why they read as a picture. So each face that looks into a tunnel gets a lit copy
1.5 mm off it, keeping the DCS shape:
    duct        objects _26, _52, _73 forward of the flaps' rear end
    turbine     a real wheel behind the rods, which turns with the engine as the stock B737's and LJ45's fans (the integral of the spool speed)
                and itself lights up at afterburner: its map is even around the wheel, so turning shows no moving picture. A separate disc of
                flame in front of it changed the whole picture at light-up (user, 2026-11-01)
    hub         ball and rods, on the turbine: they turn with it, by the user's wish
    flaps       the inner faces of the DCS flaps, in the flaps' own parts: they open, close and vector with them
    walls       a plate on each fixed side wall behind the throat
    seals       no fire on the seal pieces outside the flaps, and an underlay closing the open seams beside them
The pictures are made here (no stock texture in the package); the way of building is the stock aircraft's, the colours are from photos of
the real F-22 at afterburner (user, 2026-11-01). burner_f22.py wires
the luminance, set in the .tmd, so it can be tuned with no conversion. Luminous surfaces have no shading: the hub's map is indexed by
the surface normal, so that it still reads as round.
"""
import numpy as np

CENTRE = 0.665, 0.265       # y, z of the left engine: the DCS burner disc
RADIUS = 0.41
X_HOLDER = -3.395           # the front of the duct, aft of the DCS disc (-3.37) and the turbine wheel; the rods reach -3.41 .. -3.74
X_TURBINE = -3.378, -3.390  # blade edges
TURBINE_BLADES = 48
X_DUCT = -4.66              # the rear end of duct object _52: aft of it the side walls
WIDTH = 0.515               # half width of the tunnel, the flaps' own. Beyond it and outside TUNNEL_Z the same objects are outer skin
TUNNEL_Z = -0.15, 0.68      # higher and lower the duct shows through the outer seams of the nozzle
SEAL_X = -4.70              # the DCS seal pieces in front of the flaps end forward of this; the flaps themselves run on to -5.4
SEAL_INSET, SEAL_REACH = 0.025, 0.06     # the forward end rises 2.1 cm at 20 deg of the plate inwards: it stays under the fuselage skin
FLAP_Z = -0.09, 0.64
SKIN_OFFSET = 0.0015


class _Mesh:
    def __init__(self):
        self.verts, self.faces, self.uvs = [], [], []

    def poly(self, pts, uvs, toward=None, normal=None):
        """pts in order; turned to face the point `toward` (or along `normal`). Blender winding: right hand gives the front."""
        p = np.array(pts, float)
        n = np.zeros(3)
        for i in range(1, len(p) - 1):
            n += np.cross(p[i] - p[0], p[i + 1] - p[0])
        want = np.array(normal, float) if normal is not None else np.array(toward, float) - p.mean(axis=0)
        if np.dot(n, want) < 0:
            pts, uvs = list(pts)[::-1], list(uvs)[::-1]
        b = len(self.verts)
        self.verts += [tuple(float(x) for x in q) for q in pts]
        self.faces.append(tuple(range(b, b + len(pts))))
        self.uvs.append([tuple(float(x) for x in q) for q in uvs])


def _normal_uv(n):
    n = np.array(n, float) / np.linalg.norm(n)
    return 0.5 + 0.48 * n[1], 0.5 + 0.48 * n[2]


def _turbine(y0, z0):
    """The last turbine wheel, seen through the rods when the afterburner is off: real saw-tooth blades, each shaded across its width by
    the map, since a picture on a flat disc only turns as a picture. Turned by burner_f22.py."""
    m = _Mesh()
    r0, r1 = 0.10, RADIUS - 0.004
    for i in range(TURBINE_BLADES):
        a0, a1 = 2 * np.pi * i / TURBINE_BLADES, 2 * np.pi * (i + 1) / TURBINE_BLADES
        pt = lambda r, a, x: (x, y0 + r * np.cos(a), z0 + r * np.sin(a))
        q = [pt(r0, a0, X_TURBINE[1]), pt(r1, a0, X_TURBINE[1]), pt(r1, a1, X_TURBINE[0]), pt(r0, a1, X_TURBINE[0])]
        # some blades a little lighter, unevenly: identical ones strobe to a still pattern
        u0 = 0.25 if i % 7 in (0, 3) else 0.0
        m.poly(q, [(u0, 0.0), (u0, 1.0), (1.0, 1.0), (1.0, 0.0)], normal=(-1, 0, 0))
        wall = [pt(r0, a1, X_TURBINE[0]), pt(r1, a1, X_TURBINE[0]), pt(r1, a1, X_TURBINE[1]), pt(r0, a1, X_TURBINE[1])]
        m.poly(wall, [(0.02, 0.0), (0.02, 1.0), (0.0, 1.0), (0.0, 0.0)], normal=(-0.2, -np.sin(a1), np.cos(a1)))
    return m


def _side_walls(y0, z0):
    """The fixed side walls behind the throat. The DCS ones are coincident double sheets at varying angles: a clean plate just outboard of
    the flap edges instead, ending where the V-shaped flaps' corners do (x -4.8), so that nothing stands out of the nozzle."""
    m = _Mesh()
    for s in (1.0, -1.0):
        y = y0 + s * 0.508
        q = [(X_DUCT + 0.06, y, -0.03), (X_DUCT + 0.06, y, 0.56), (-4.80, y, 0.50), (-4.80, y, 0.03)]
        m.poly(q, [(0.5 + 0.5 * (p[2] - z0), (p[0] + 5.45) / 1.15) for p in q], normal=(0, -s, 0))
    return m


def _source_faces(o):
    """World corners, face normal of a DCS object's polygons (normal as authored: mirrored objects turned right)."""
    from mathutils import Vector
    mw = o.matrix_world
    nm = mw.inverted_safe().transposed().to_3x3()
    for p in o.data.polygons:
        n = np.array((nm @ p.normal).normalized())
        co = [np.array(mw @ o.data.vertices[i].co) for i in p.vertices]
        yield co, n


def _skins(objs, y0, z0):
    """Lit copies of the DCS faces looking into this tunnel: {part or None: {material: mesh}}."""
    from mathutils import Vector
    out = {}

    def add(part, material, pts, uv, n):
        out.setdefault(part, {}).setdefault(material, _Mesh()).poly(pts, uv, normal=n)

    for o in objs:
        if o.type != 'MESH':
            continue
        args = {int(a) for a in str(o.get('edm_anim_args', '')).split(',') if a}
        flap = bool(args & {610, 611})
        if not flap:
            # the duct is in several DCS objects (each engine its own): any skin object that reaches into this tunnel
            box = [o.matrix_world @ Vector(c) for c in o.bound_box]
            if args or o.get('edm_material') != 'F22A_FUSE' or min(b[0] for b in box) > -3.38 or \
                    min(b[1] for b in box) > y0 + WIDTH or max(b[1] for b in box) < y0 - WIDTH:
                continue
        if flap and min((o.matrix_world @ Vector(c)).x for c in o.bound_box) > SEAL_X:
            continue            # a seal piece: no fire, it is seen from outside
        part = 'A_' + str(o.get('edm_anim_nodes', '')).replace(',', '_') if flap else None
        turning = str(o.get('aerofly_part', '')).startswith('Turbine_')
        for co, n in _source_faces(o):
            c = sum(co) / len(co)
            if turning:         # the ball and rods, taken out of the airframe object for the turbine part (ac_f22.py TURBINE_HUBS)
                add(o['aerofly_part'], 'f22_fire_hub', [p + SKIN_OFFSET * n for p in co], [_normal_uv(n)] * len(co), n)
                continue
            if abs(c[1] - y0) > (0.60 if flap else WIDTH) or not -5.55 < c[0] < -3.38:
                continue
            # aft of the hinges the duct above and below the flaps shows through the outer gap of the nozzle: only between them
            zone = FLAP_Z if c[0] < -4.2 else TUNNEL_Z
            if not flap and not zone[0] < c[2] < zone[1]:
                continue
            pts = [p + SKIN_OFFSET * n for p in co]
            if flap:
                if abs(n[2]) >= 0.4 and (c[2] - z0) * n[2] < 0 and FLAP_Z[0] < c[2] < FLAP_Z[1]:      # not the outer seals
                    add(part, 'f22_fire_flap', pts, [(0.5 + (p[1] - y0), (p[0] + 5.45) / 1.15) for p in co], n)
                continue
            # looks towards the axis, or aft (the steps of the duct)
            if (y0 - c[1]) * n[1] + (z0 - c[2]) * n[2] < 0.0 and n[0] > -0.5:
                continue
            if c[0] > X_DUCT:
                # around the duct, the seam below, behind the lower flap
                th = [(np.arctan2(p[2] - z0, p[1] - y0) + np.pi / 2) / (2 * np.pi) % 1.0 for p in co]
                th = [t + 1.0 if max(th) - t > 0.5 else t for t in th]
                add(None, 'f22_fire_liner', pts, [(t, (p[0] - X_DUCT) / (X_HOLDER - X_DUCT)) for t, p in zip(th, co)], n)
    return out


def _seal_underlays(objs):
    """The DCS nozzle has open seams either side of the seal pieces (fuselage to seal, seal to flap), through which the inside of the engine shows, lit or dark; none on the real
    aircraft (user's photos, 2026-11-01). The outer faces of each seal again, in the same skin and the seal's own part, under it and reaching further fore and aft. The plate turns about
    the seal's forward edge (ac_f22.py NOZZLE_PLATES), so nothing moves between seal, flap and underlay."""
    import bmesh
    from mathutils import Vector
    out = []
    for o in objs:
        if o.type != 'MESH':
            continue
        args = {int(a) for a in str(o.get('edm_anim_args', '')).split(',') if a}
        if not args & {610, 611}:
            continue
        mw = o.matrix_world
        xs = [(mw @ Vector(c)).x for c in o.bound_box]
        if min(xs) <= SEAL_X:
            continue
        y0 = CENTRE[0] if sum((mw @ Vector(c)).y for c in o.bound_box) > 0 else -CENTRE[0]
        nm = mw.inverted_safe().transposed().to_3x3()
        bm = bmesh.new()
        bm.from_mesh(o.data)
        drop = [f for f in bm.faces if not (lambda n, c: abs(n.z) > 0.3 and (c.z - CENTRE[1]) * n.z > 0)((nm @ f.normal).normalized(), mw @ f.calc_center_median())]
        bmesh.ops.delete(bm, geom=drop, context='FACES')
        mid, inv = (min(xs) + max(xs)) / 2, mw.inverted_safe()
        for v in bm.verts:
            w = mw @ v.co
            up = 1.0 if w.z > CENTRE[1] else -1.0
            w.x += SEAL_REACH if w.x > mid else -SEAL_REACH
            w.z -= up * SEAL_INSET
            v.co = inv @ w
        me = o.data.copy()
        bm.to_mesh(me)
        bm.free()
        ob = o.copy()
        ob.data = me
        ob.name = 'SealUnderlay' + o.name
        out.append(ob)          # keeps the animation keys: same part as its seal
        print('nozzle seal underlay %s: %d faces' % (ob.name, len(me.polygons)))
    return out


def objects(objs, mesh_object, axes):
    res = _seal_underlays(objs)
    for side, y0 in (('Left', CENTRE[0]), ('Right', -CENTRE[0])):
        z0 = CENTRE[1]
        fire = 'Burner_%s_C' % side
        skins = _skins(objs, y0, z0)
        fixed = skins.pop(None, {})
        fixed['f22_fire_flap'] = _side_walls(y0, z0)
        groups = [(fire, fixed)] + sorted(skins.items())
        res.append(_object(mesh_object, 'Turbine' + side, _turbine(*axes[side]), 'f22_fire_turbine', 'Turbine_' + side))
        for k, (part, mats) in enumerate(groups):
            for material, mesh in sorted(mats.items()):
                if mesh.faces:
                    res.append(_object(mesh_object, 'Fire%s%d%s' % (side, k, material[8:]), mesh, material, part))
    return res


def _object(mesh_object, name, mesh, material, part):
    ob = mesh_object(name, mesh.verts, mesh.faces, mesh.uvs, 'burner:' + material)
    ob['aerofly_part'] = part
    print('nozzle fire %s: %d faces, %s in %s' % (name, len(mesh.faces), material, part))
    return ob


# ---------------------------------------------------------------------------------------------- pictures
HEAT = [(0.0, (0.03, 0.004, 0.0)), (0.2, (0.26, 0.03, 0.005)), (0.42, (0.72, 0.17, 0.01)), (0.62, (1.0, 0.45, 0.03)),
        (0.8, (1.0, 0.72, 0.12)), (1.0, (1.0, 0.93, 0.55))]


def _palette(h, stops=HEAT):
    h = np.clip(h, 0.0, 1.0)
    xs = [s[0] for s in stops]
    return np.dstack([np.interp(h, xs, [s[1][k] for s in stops]) for k in range(3)])


def _noise(u, v, seed, kx=(1, 2, 3, 5, 8, 13), ky=(1, 2, 3, 5, 8), periodic_u=True):
    """Summed cosines; a whole number of waves around u, so that the liner closes on itself."""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(u)
    for k in kx:
        for _ in range(4):
            f = k if periodic_u else k + rng.uniform(0, 1)
            g = rng.choice(ky)
            a, b = rng.uniform(0, 2 * np.pi, 2)
            out += np.cos(2 * np.pi * f * u + a) * np.cos(2 * np.pi * g * v + b) / k ** 0.7
    return (out - out.min()) / (out.max() - out.min())


def _liner_map(n=1024):
    v, u = np.mgrid[0:n, 0:n] / float(n - 1)
    # v 0 at the rear of the duct .. 1 at the flame holder: red, orange, a broad yellow front. Tongues of flame licking aft
    tongues = _noise(u, v, 3, kx=(3, 5, 8, 13), ky=(1, 2))
    streaks = _noise(u, v, 7, kx=(11, 17, 24, 31), ky=(1,))
    heat = 0.34 + 0.56 * v ** 1.3 + 0.30 * (tongues - 0.5) * (0.5 + v) + 0.10 * (streaks - 0.5)
    # bright lip of the inner liner, as the stock arc around the holder
    heat += 0.20 * np.exp(-((v - 0.86) / 0.02) ** 2)
    heat = np.where(v > 0.86, np.maximum(heat, 0.92 + 0.08 * (v - 0.86) / 0.14), heat)
    # panels: thin dark seams with a hot edge on one side, and a small round cooling hole in each
    columns, rows = 24, 5
    pu, pv = u * columns, v * rows / 0.86
    fu, fv = pu - np.floor(pu), pv - np.floor(pv)
    aft = v < 0.85
    seam = np.exp(-(np.minimum(fu, 1 - fu) / 0.018) ** 2) + np.exp(-(np.minimum(fv, 1 - fv) / 0.014) ** 2)
    hot = np.exp(-((fu - 0.06) / 0.03) ** 2) * 0.08
    d = np.hypot(fu - 0.5, (fv - 0.5) * 0.7)
    holes = np.clip((0.085 - d) / 0.03, 0.0, 1.0)
    heat = np.where(aft, heat + hot - 0.34 * np.clip(seam, 0, 1) - 0.55 * holes, heat)
    rgb = _palette(heat)
    return np.dstack((rgb, np.ones((n, n)))).astype(np.float32)


def _hub_map(n=256):
    """Ball, rods and gutters: dark against the flame, lit from behind at their turned-away edges."""
    v, u = np.mgrid[0:n, 0:n] / float(n - 1)
    y, z = (u - 0.5) / 0.48, (v - 0.5) / 0.48
    r = np.clip(np.sqrt(y * y + z * z), 0.0, 1.0)
    return np.dstack((_palette(0.05 + 0.42 * r ** 2.5), np.ones((n, n)))).astype(np.float32)


def _flap_map(n=1024):
    """Photos: the flaps glow copper over their whole width, red-orange towards the exit, with a thin yellow-white line at the throat."""
    v, u = np.mgrid[0:n, 0:n] / float(n - 1)
    flame = _noise(u, v, 19, kx=(2, 3, 5, 8), ky=(1, 2), periodic_u=False)
    streak = _noise(u, v, 23, kx=(9, 14, 20), ky=(1,), periodic_u=False)
    heat = (0.42 + 0.34 * v) * (0.86 + 0.28 * flame) + 0.07 * (streak - 0.5)
    plates = 8
    fu = (u * plates) % 1.0
    seam = np.exp(-(np.minimum(fu, 1 - fu) / 0.016) ** 2)
    rows = np.exp(-(((v * 5) % 1.0 - 0.5) / 0.010) ** 2)
    heat = heat * (1.0 - 0.28 * np.clip(seam + rows, 0, 1))
    heat = np.maximum(heat, 0.98 * np.clip((v - 0.70) / 0.14, 0.0, 1.0))      # the throat line, at the flaps' forward end
    return np.dstack((_palette(heat), np.ones((n, n)))).astype(np.float32)


def _turbine_map(n=512):
    """Lit: across a blade (u) dark at the tooth's root, bright at its edge; along it (v, root to tip) dark to yellow: from behind, a dark centre in a
    ring of fire, as in the user's photo of the real F-22, with no feature that would show as a turning picture."""
    v, u = np.mgrid[0:n, 0:n] / float(n - 1)
    heat = (0.12 + 0.88 * v ** 1.4) * (0.72 + 0.28 * u ** 1.3)
    heat = heat * (1.0 - 0.7 * np.exp(-(u / 0.04) ** 2))
    return np.dstack((_palette(heat), np.ones((n, n)))).astype(np.float32)


def _panels(n, columns, rows, span=1.0):
    v, u = np.mgrid[0:n, 0:n] / float(n - 1)
    fu, fv = (u * columns) % 1.0, (v * rows / span) % 1.0
    return v, u, fu, fv


def _cold_liner(n=1024):
    """Unlit: sooty grey-brown metal going to black deep inside, as the stock F/A-18's: no fire colour when there is no fire."""
    v, u, fu, fv = _panels(n, 24, 5, 0.86)
    seam = np.clip(np.exp(-(np.minimum(fu, 1 - fu) / 0.018) ** 2) + np.exp(-(np.minimum(fv, 1 - fv) / 0.014) ** 2), 0, 1)
    holes = np.clip((0.085 - np.hypot(fu - 0.5, (fv - 0.5) * 0.7)) / 0.03, 0.0, 1.0)
    stain = _noise(u, v, 5, kx=(2, 3, 5, 8), ky=(1, 2, 3))
    level = (0.20 - 0.17 * v) * (0.7 + 0.6 * stain) * (1.0 - 0.6 * seam) * (1.0 - 0.8 * holes)
    return np.dstack((level * 1.25, level, level * 0.78))


def _cold_flap(n=1024):
    """Unlit: the grey of the real flaps (user's photos), with soot towards the throat."""
    v, u, fu, _ = _panels(n, 8, 5)
    seam = np.clip(np.exp(-(np.minimum(fu, 1 - fu) / 0.016) ** 2) + np.exp(-(((v * 5) % 1.0 - 0.5) / 0.010) ** 2), 0, 1)
    stain = _noise(u, v, 29, kx=(2, 3, 5, 8), ky=(1, 2, 3), periodic_u=False)
    level = (0.30 - 0.20 * v) * (0.75 + 0.5 * stain) * (1.0 - 0.45 * seam)
    return np.dstack((level * 1.08, level * 1.02, level))


def _cold_turbine(n=256):
    v, u = np.mgrid[0:n, 0:n] / float(n - 1)
    level = 0.03 + 0.09 * u ** 1.6
    return np.dstack((level * 1.05, level, level * 0.95))


def cold(name):
    if name == 'f22_fire_liner':
        return _cold_liner()
    if name == 'f22_fire_flap':
        return _cold_flap()
    if name == 'f22_fire_turbine':
        return _cold_turbine()
    return np.full((64, 64, 3), 0.03)       # the ball and rods


def texture(name):
    return {'f22_fire_liner': _liner_map, 'f22_fire_hub': _hub_map, 'f22_fire_flap': _flap_map, 'f22_fire_turbine': _turbine_map}[name]()
