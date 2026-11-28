"""Ground equipment on the ramp (0.9.3).

Shown only after a ground start with both engines off (cold & dark, before engine start), modelled after photos of
F-22s on the ramp:

  boarding ladder   hooked on the left cockpit sill; 1.5 s into the canopy's closing it is laid down and dragged to
                    the power cart
  wheel chocks      yellow, a pair per wheel joined by a rope; pulled out sideways when the parking brake is released
  intake covers     red plugs with REMOVE BEFORE FLIGHT pushed into the ducts, two handles; when the APU starts they are
                    pulled straight out along the duct and laid on the ramp beside the intakes
  exhaust covers    black padded plugs deep in the open (parked) nozzles at the throat, rigid handles; pulled straight
                    out aft and laid behind the tail
  probe covers      red sleeves on the two nose probes with their streamers; control surface locks across the
                    flaperons' and ailerons' side gaps and under the flaperon / stabilator gap; the hook's safety pin
                    (all go with the intake covers)
  RBF streamers     gear pins in the gear locks (nose, main) and yellow seeker caps on the AIM-9X (when loaded): go with
                    the chocks
  munitions trailer two AIM-120C and two AIM-9X on it with the CLEAN load, empty with a load that carries them
  power cart        the DCS model's own ground power cart (Grinnelli, GPL-3; ac_f22.py _ground_cart), outside the wing
                    span, our hose from it along the ramp to a receptacle under the fuselage behind the nose gear bay
                    (the DCS hose ran into the side bay, through the AIM-9X) - real external power: with the battery
                    switch on it feeds the aircraft (the F/A-18's ExternalPower chain, which the donor drives from the
                    APU only); when the APU has run 3 s the hose is unplugged and coiled on the cart
  extinguisher, tool cart   stay where they are, outside the wing span

Everything removed stays on the ramp. Releasing the parking brake takes all of it off the aircraft at once (ladder,
covers, hose too), so nothing is left hanging when the aircraft rolls.

How it stands still (test 2026-11-27, in game): the ground items are graphics on one `fixed_body` - a body held in the
world where it was placed at the start (the stock glider winch's chassis type; no Group field - none in stock). The
aircraft taxis away from them; nothing collides with the aircraft, so the tall items stand outside the wing span and
the low ones out of the wheel tracks (in game 2026-11-27 the power cart under the wing tip and the tool cart beside
the ferry tank were swept by the wing when taxiing: both outside the span now). Items on the aircraft (covers, streamers) are drawn on the fuselage; a cover's
removal is a second copy on the fixed body, shown from the moment it moves.

The ground at the start is the plane under the contact spheres (f22.tmc ContactSpheres): 2 deg against the aircraft's
x axis - everything standing on it is sheared onto it (ground_z). Placement from the export pose (ray casts,
2026-11-27): intake opening corners and lip, the cockpit side under the sill, nose chine, nozzle flap edges, gear.

Removal motions are graphics transforms on a progress 0..1 per item (integrated in the dynamics, latched: nothing comes
back). In the first 2 s of a flight the progress jumps to the state the start preset implies (APU running, canopy
closed: covers and ladder already down).
"""
import math


# ---------------------------------------------------------------------------------------------- the ground at the start
_NOSE = (5.983, -1.613 - 0.294)            # f22.tmc ContactSpheres (bottoms), make_f22_meta.py
_MAIN = (-0.462, -1.266 - 0.411)
SLOPE = (_NOSE[1] - _MAIN[1]) / (_NOSE[0] - _MAIN[0])          # dz / dx, ~ -0.036


def ground_z(x):
    return _MAIN[1] + SLOPE * (x - _MAIN[0])


FIXED_R0 = (0.0, 0.0, ground_z(0.0))       # the fixed body (and its radar altimeter) under the aircraft
LADDER_AFTER_S, CANOPY_RATE = 1.5, 0.1      # s into the canopy's closing; the canopy servo's speed (CanopySequence)

# ---------------------------------------------------------------------------------------------- placement (left side;
# the right mirrors y)
# intake opening (front projection) corners, x on the lip: inboard bottom, outboard bottom, outboard top, inboard top
INTAKE = [(5.78, 0.46, -0.53), (5.38, 1.09, -0.60), (5.89, 1.52, 0.13), (6.40, 0.97, 0.28)]
LIP_PLANE = (6.631, -0.568, 1.083)          # x = a + b y + c z through the four corners (2 cm)
# a plug pushed in (2026-11-27, as the real ones: recessed, pulled out by two handles); the duct keeps the
# opening's front projection 20 cm in (ray casts)
COVER_RECESS, COVER_INSET, COVER_DEPTH = 0.18, 0.012, 0.30
COVER_SPOT = (5.75, 3.50)                  # laid on the ramp out of the intake (ahead of a ferry tank, clear of the hose)
# exhaust: the nozzle between the sidewalls (inner faces y 0.123 / 1.202) and the flaps as parked open (make_f22
# NOZZLE_PARKED 0.7 x NOZZLE_OPEN 0.52 rad about the hinges; ray casts with the plates turned so: the inner surfaces at
# x -5.45 z -0.291 / 0.901, at -5.10 z -0.158 / 0.731 - the nozzle widens aft): a wedge plug 2 cm inside them
# (in-game 2026-11-27: as the reference - a padded panel filling the nozzle at that depth, rigid handles left and right)
# 2026-11-28 (reference photos): deep in, at the throat where the vectoring flaps begin - ray casts of the parked
# nozzle (work/f22_pose.blend: the exported blend's plates do not take the pose): the flaps' inner surfaces at x -4.60
# z 0.022 / 0.509 (the narrowest), at -4.75 z -0.025 / 0.562; the sidewalls y 0.143 / 1.182. Face at -4.75, back at
# the throat, 1.5 cm inside all round
EXHAUST_Y, EXHAUST_X = (0.158, 1.167), (-4.75, -4.60)
EXHAUST_Z = {'aft': (-0.010, 0.547), 'fwd': (0.037, 0.494)}
EXHAUST_SPOT = (-8.00, 1.90)               # behind the tail
# the face is 1.0 m wide, 0.56 m tall: its texture drawn in a band of that height (text and border not squashed)
EXHAUST_BAND = (0.5 - 0.28, 0.5 + 0.28)
EXHAUST_FLAP_TE = -5.45                    # the parked flaps' trailing edges (x)
# nose probes (ray-cast bumps, 2026-11-27): root and tip of the left probe's outer line
PROBE = ((9.10, 0.622, -0.062), (9.315, 0.605, -0.088))
PROBE_CAP_R, PROBE_CAP = 0.022, (0.07, 0.05)   # m: sleeve radius, from 7 cm behind the tip to 5 cm beyond
# ladder: rails at x, from the foot on the ground (y) to the sill (y, z); the chine (y 0.82 at z 0.35) cleared by 5 cm
LADDER_X = (6.72, 7.18)
LADDER_FOOT_Y, LADDER_TOP = 2.05, (0.72, 0.70)
LADDER_RAIL_R, LADDER_STEP = 0.022, 0.28
LADDER_AWAY = (0.0, 2.6)                   # laid flat outward, then dragged out to lie beside the power cart (m)
# wheels at the start (export pose): centre x, y, radius, tyre width
WHEELS = {'N': (5.985, 0.0, 0.294, 0.18), 'L': (-0.462, 1.598, 0.411, 0.307), 'R': (-0.462, -1.598, 0.411, 0.307)}
CHOCK_H, CHOCK_L, CHOCK_GAP = 0.15, 0.22, 0.02
CHOCK_OUT = {'N': 0.8, 'L': 0.9, 'R': -0.9}  # pulled sideways (m, +y left)
# RBF streamers: attachment points (pin at the top, ribbon hanging down)
# gear lock pins, in the locks themselves (2026-11-27, reference picture: the pin through the lock link, its
# streamer from the ring): the nose gear's drag brace knee (links _1/_2 of the export pose meet at x 5.95 z -0.50), the
# main gears' side brace lock links (around x -0.39, y +-1.43, z -0.47). (point, pin axis, streamer length)
RBF_GEAR = [((5.955, 0.0, -0.495), (0.0, 1.0, 0.0), 0.40), ((-0.39, 1.435, -0.47), (1.0, 0.0, 0.0), 0.30),
            ((-0.39, -1.435, -0.47), (1.0, 0.0, 0.0), 0.30)]
RIBBON_W, RIBBON_L = 0.05, 0.45
# control surface locks (2026-11-27, second pass: in the gaps between the fixed structure and the surfaces): a
# clamp across the side gap at each surface's outboard end - the flaperon's against the fixed wing (y 4.50, flaperon
# hinge at x -2.43, the fixed wing outboard of it to x -2.78), the aileron's against the wing tip (y 5.845, hinge at
# -2.39). Ray casts on the footprint (+-6 cm of the gap): (x fwd, x aft, y, top z, bottom z fwd, bottom z aft); the top is
# flat there, the lower skin rises towards the trailing edge. Left side.
SURFACE_LOCKS = {'flaperon': (-2.49, -2.75, 4.50, 0.345, 0.249, 0.265),
                 'aileron': (-2.47, -2.73, 5.845, 0.243, 0.168, 0.187)}
LOCK_HALF_SPAN, LOCK_T, LOCK_PAD = 0.06, 0.012, 0.005
# the stabilators: a padded block under the gap between the flaperon's trailing edge and the stabilator's leading edge
# near the root (reference pictures: red block, black rubber face against the skin, the streamer from a bolt in its
# middle; it ties the stabilator to the wing). Gap centre line from ray casts: x -3.583 at y 2.05 .. -3.958 at 2.45;
# the block's centre, the gap's direction (outboard-aft), the skin top / bottom over its footprint (+-12 x +-7 cm).
STAB_LOCK = ((-3.744, 2.22), (-0.684, 0.730), 0.293, 0.253)
STAB_HALF = (0.12, 0.07)
# the arresting hook: its point under the centre boom between the nozzles - the sloping underside steps up there
# (z 0.063 at x -5.465, 0.107 at -5.47): a safety pin across it, ring and streamer (reference picture)
HOOK_PIN = (-5.49, 0.095)                  # x, z of the pin
# ramp props (x, y, yaw deg)
EXTINGUISHER_AT = (-6.0, -8.0, 30.0)
TOOLCART_AT = (-2.2, -8.5, 15.0)
# munitions trailer (as the MHU-110 class on the photos: steel frame, tread-plate decks over the axles, four wheels,
# tow bar; adapter rails with cradles): left, aft, outside the span, tow bar forward. With the CLEAN load its rails
# carry the missiles - 2 AIM-120C above, 2 AIM-9X outboard below - loaded, the trailer is empty (2026-11-27)
TRAILER_AT = (-4.6, 9.0, 0.0)
TRAILER_UP = (0.32, 1.10)                  # upper rails: y, top z (AIM-120C)
TRAILER_LOW = (0.70, 0.88)                 # lower rails: y, top z (AIM-9X)
CRADLES = {'aim120': (0.60, 2.70), 'aim9x': (0.80, 2.25)}   # m aft of the nose: clear of the wings and fins
# the DCS power cart (ac_f22.py): its pose is half way along its drive-in (arg 617 at 0), parked 2.69 m further aft;
# it stood on a flat ground at z -1.70 (wheels), here sheared onto ground_z and moved out past the wing tip
CART_SHIFT_X, CART_SHIFT_Y, CART_GROUND = -2.687, 3.45, -1.70
CART_SOCKET = (5.056, 4.927, -0.37)        # where the DCS hose entered the cart (export pose)
PLUG = (4.95, 0.50, -0.70)                 # the receptacle under the fuselage behind the nose gear bay (skin z -0.697)
HOSE_R = 0.025
HOSE_LIFT = 0.05                           # m over the plane (in-game 2026-11-27 the real ramp rose above it out there)
COIL_AT = (5.75, 5.42 + CART_SHIFT_Y)      # the unplugged hose coiled on the cart's top
# the beacon's dome (a glass material here: it would be canopy glass) and lamp; the DCS hose (replaced)
CART_SKIP = ('Plastic', '_1.007', 'CART_HOSE')


def cart_point(p):
    """A point of the DCS cart (export pose) -> parked on the start's ground."""
    x = p[0] + CART_SHIFT_X
    return (x, p[1] + CART_SHIFT_Y, p[2] + ground_z(x) - CART_GROUND)

# ---------------------------------------------------------------------------------------------- timing
LADDER_S, COVER_S, CHOCK_S, HOSE_S = 4.5, 2.6, 3.0, 1.0      # (the ladder twice as fast, 2026-11-27)
APU_HOSE_S = 3.0                           # the APU on line this long: the hose comes off
START_DECIDE = (1.0, 1.4)                  # s: shown or not, decided once here
SNAP_S = 2.0                               # s: states the start preset implies, at once
AIR_START_M = 1.0

# ---------------------------------------------------------------------------------------------- materials
# one texture set per surface (store-style maps, ac_f22.py STORE_TEXTURES): name -> (kind, base colour, metres the
# texture spans, size). Faces are mapped by planar projection in metres ('auto'); the painted faces (cover faces,
# ribbons, the extinguisher label) by their own UVs over the whole texture.
MATS = {'alu': ('brushed', (0.70, 0.71, 0.73), 1.0, 512), 'blue': ('paint', (0.08, 0.25, 0.60), 0.8, 512),
        'yellow': ('paint', (0.86, 0.66, 0.06), 0.8, 512), 'capyellow': ('plastic', (0.88, 0.70, 0.05), 0.8, 256), 'green': ('paint', (0.64, 0.72, 0.12), 0.8, 512),
        'red': ('fabric', (0.50, 0.05, 0.05), 0.8, 512), 'black': ('fabric', (0.055, 0.055, 0.06), 0.8, 512),
        'rubber': ('rubber', (0.035, 0.035, 0.035), 0.6, 512), 'hose': ('rubber', (0.20, 0.20, 0.19), 1.0, 512),
        'tool': ('powder', (0.055, 0.055, 0.06), 1.0, 512), 'dark': ('paint', (0.20, 0.20, 0.21), 0.6, 512),
        'redpaint': ('paint', (0.60, 0.07, 0.06), 0.5, 512), 'redrubber': ('rubber', (0.50, 0.06, 0.05), 0.4, 512),
        'trailer': ('paint', (0.46, 0.48, 0.50), 1.0, 1024), 'tread': ('tread', (0.44, 0.46, 0.48), 0.6, 512),
        'webbing': ('fabric', (0.58, 0.53, 0.36), 0.5, 512), 'stencil': ('stencil', (0.46, 0.48, 0.50), None, 1024),
        'cover': ('cover', (0.50, 0.05, 0.05), None, 1024), 'exhaust': ('exhaust', (0.05, 0.05, 0.055), None, 1024),
        'ribbon': ('ribbon', (0.55, 0.05, 0.06), None, 1024), 'label': ('label', (0.86, 0.86, 0.84), None, 256)}
RIBBON_STRIP = 0.125                       # the ribbon texture holds 8 strips across: u 0 .. 1/8 is one ribbon
TEXT = 'REMOVE BEFORE FLIGHT'


def material(key):
    return 'gnd_' + key


# ---------------------------------------------------------------------------------------------- small vector helpers
def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _mul(a, k):
    return tuple(x * k for x in a)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a))
    return _mul(a, 1.0 / n)


def _rot(v, axis, ang):
    """Rodrigues: v turned by ang about the unit axis."""
    c, s = math.cos(ang), math.sin(ang)
    return _add(_add(_mul(v, c), _mul(_cross(axis, v), s)), _mul(axis, _dot(axis, v) * (1 - c)))


def _mirror(p):
    return (p[0], -p[1], p[2])


# ---------------------------------------------------------------------------------------------- mesh building
class Mesh:
    def __init__(self):
        self.v, self.f, self.uv, self.sm = [], [], [], []

    def add(self, verts, faces, uvs, smooth=False, refs=None, oriented=False):
        """Add one closed piece. Each face is turned to face out of it (seen from outside its vertices run
        counter-clockwise: Blender's normal outward, as ac_f22's stores): away from refs[i] (a point inside the piece
        near that face), by default the piece's centroid - the pieces are convex, tubes give their own points. The
        game draws front faces only, and the split by material (split) leaves single faces whose outside could not be
        told any more (the intake covers' painted faces were drawn inward, in-game 2026-11-27)."""
        verts = [tuple(map(float, p)) for p in verts]
        faces, uvs = [tuple(q) for q in faces], list(uvs)
        if not oriented:
            cen = tuple(sum(p[k] for p in verts) / len(verts) for k in range(3))
            for i, q in enumerate(faces):
                pts = [verts[j] for j in q]
                nx = ny = nz = 0.0
                for a, b in zip(pts, pts[1:] + pts[:1]):            # Newell
                    nx += (a[1] - b[1]) * (a[2] + b[2])
                    ny += (a[2] - b[2]) * (a[0] + b[0])
                    nz += (a[0] - b[0]) * (a[1] + b[1])
                fc = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
                ref = refs[i] if refs else cen
                if nx * (fc[0] - ref[0]) + ny * (fc[1] - ref[1]) + nz * (fc[2] - ref[2]) < 0:
                    faces[i] = q[::-1]
                    if uvs[i][0] == 'fix':
                        uvs[i] = ('fix', uvs[i][1], tuple(uvs[i][2])[::-1])
        n = len(self.v)
        self.v += verts
        self.f += [tuple(i + n for i in q) for q in faces]
        self.uv += uvs
        self.sm += smooth if isinstance(smooth, list) else [smooth] * len(faces)

    def merge(self, other):
        self.add(other.v, other.f, other.uv, list(other.sm), oriented=True)

    @staticmethod
    def _reoriented(m):
        return m

    def map(self, fn):
        self.v = [fn(p) for p in self.v]
        return self


def _flat(mat, n=4):
    """A face mapped by projection (objects())."""
    return ('auto', mat)


def _fixed(mat, uvs):
    return ('fix', mat, tuple(uvs))


def box(c, axes, half, sw, uv_front=None, front_mat=None):
    """Box at centre c, unit axes (3), half sizes (3); uv_front: corner UVs for the +axes[0] face (front_mat)."""
    m = Mesh()
    vs = []
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                vs.append(_add(c, _add(_mul(axes[0], i * half[0]), _add(_mul(axes[1], j * half[1]), _mul(axes[2], k * half[2])))))
    # index = 4 i + 2 j + k (i, j, k in 0/1)
    faces = [(4, 6, 7, 5), (0, 1, 3, 2), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    uvs = [_fixed(front_mat or sw, uv_front) if uv_front else _flat(sw)] + [_flat(sw)] * 5
    m.add(vs, faces, uvs)
    return m


def bar(a, b, w, sw, h=None):
    """Square (w x h) bar from a to b."""
    d = _norm(_sub(b, a))
    up = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 0.0, 1.0)
    s = _norm(_cross(d, up))
    t = _cross(d, s)
    L = math.sqrt(_dot(_sub(b, a), _sub(b, a)))
    return box(_mul(_add(a, b), 0.5), (d, s, t), (L / 2, w / 2, (h or w) / 2), sw)


def tube(path, r, sw, seg=8, closed=False):
    """Round tube along a polyline (end caps unless closed)."""
    m = Mesh()
    n = len(path)
    rings = []
    for i, p in enumerate(path):
        if closed:
            d = _norm(_sub(path[(i + 1) % n], path[i - 1]))
        else:
            d = _norm(_sub(path[min(i + 1, n - 1)], path[max(i - 1, 0)]))
        up = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
        s = _norm(_cross(d, up))
        t = _cross(d, s)
        rings.append([_add(p, _add(_mul(s, r * math.cos(2 * math.pi * k / seg)), _mul(t, r * math.sin(2 * math.pi * k / seg))))
                      for k in range(seg)])
    vs = [p for ring in rings for p in ring]
    faces = []
    for i in range(n if closed else n - 1):
        a, b = i * seg, ((i + 1) % n) * seg
        for k in range(seg):
            faces.append((a + k, a + (k + 1) % seg, b + (k + 1) % seg, b + k))
    refs = []
    for i in range(n if closed else n - 1):
        mid = _mul(_add(path[i], path[(i + 1) % n]), 0.5)
        refs += [mid] * seg
    side_faces = len(faces)
    if not closed:
        faces.append(tuple(range(seg))[::-1])
        faces.append(tuple((n - 1) * seg + k for k in range(seg)))
        refs += [_add(path[0], _mul(_sub(path[1], path[0]), 0.5)), _add(path[-1], _mul(_sub(path[-2], path[-1]), 0.5))]
    m.add(vs, faces, [_flat(sw, len(q)) for q in faces], [True] * side_faces + [False] * (len(faces) - side_faces),
          refs=refs)
    return m


def cylinder(a, b, r, sw, seg=12):
    return tube([a, b], r, sw, seg)


def ribbon(top, down, side, sw='red'):
    """REMOVE BEFORE FLIGHT ribbon: from top along `down` (unit) RIBBON_L, width along `side` (unit); a thin closed box
    (both faces painted), the text along its length."""
    n = _norm(_cross(side, down))
    c = _add(top, _mul(down, RIBBON_L / 2))
    u0, v0, u1, v1 = 0.0, 0.0, RIBBON_STRIP, 1.0
    # face +n: corners in box() order for the +axes[0] face are (+, -, -) (+, +, -) (+, +, +) (+, -, +) of (n, down, side)
    front = ((u0, v1), (u0, v0), (u1, v0), (u1, v1))
    m = box(c, (n, down, side), (0.0015, RIBBON_L / 2, RIBBON_W / 2), sw, uv_front=front, front_mat='ribbon')
    # the back face painted as well
    m.uv[1] = _fixed('ribbon', ((u1, v1), (u0, v1), (u0, v0), (u1, v0)))
    return m


def ribbon_path(points, side, outward, sw='red'):
    """A ribbon laid along points (skin, then hanging): thin segments, the text running on along it; `outward` turns
    each segment's face away from the skin."""
    m = Mesh()
    L = [0.0]
    for a, b in zip(points, points[1:]):
        L.append(L[-1] + math.sqrt(_dot(_sub(b, a), _sub(b, a))))
    total = L[-1]
    for k, (a, b) in enumerate(zip(points, points[1:])):
        d = _norm(_sub(b, a))
        n = _norm(_cross(side, d))
        if _dot(n, outward) < 0:
            n = _mul(n, -1)
        sd = _cross(d, n)
        v0, v1 = 1 - L[k] / total, 1 - L[k + 1] / total
        u0, u1 = 0.0, RIBBON_STRIP
        seg = box(_mul(_add(a, b), 0.5), (n, d, sd), (0.0015, (L[k + 1] - L[k]) / 2 + 0.001, RIBBON_W / 2), sw,
                  uv_front=((u0, v0), (u0, v1), (u1, v1), (u1, v0)), front_mat='ribbon')
        seg.uv[1] = _fixed('ribbon', ((u1, v0), (u0, v0), (u0, v1), (u1, v1)))
        m.merge(Mesh._reoriented(seg))
    return m


def gear_pin(p, axis, ribbon_len, length=0.10):
    """A lock pin through a link: dark shank, red knob, a ring off the knob, the streamer hanging from the ring."""
    m = Mesh()
    a, b = _sub(p, _mul(axis, length / 2)), _add(p, _mul(axis, length / 2))
    m.merge(cylinder(a, b, 0.0065, 'dark', seg=8))
    m.merge(cylinder(b, _add(b, _mul(axis, 0.018)), 0.013, 'redpaint', seg=10))
    rc = _add(_add(b, _mul(axis, 0.026)), (0.0, 0.0, -0.016))
    ring = [_add(rc, _add(_mul(axis, 0.013 * math.sin(t)), (0.0, 0.0, 0.013 * math.cos(t)))) for t in [i * 2 * math.pi / 12 for i in range(12)]]
    m.merge(tube(ring, 0.0022, 'alu', seg=5, closed=True))
    side = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.5 else (0.0, 1.0, 0.0)
    global RIBBON_L
    keep, RIBBON_L = RIBBON_L, ribbon_len
    m.merge(ribbon(_add(rc, (0.0, 0.0, -0.016)), (0.0, 0.0, -1.0), side))
    RIBBON_L = keep
    return m


def streamer(at, down=(0.0, 0.0, -1.0), side=(1.0, 0.0, 0.0)):
    """A pin (dark) with its ribbon."""
    m = Mesh()
    m.merge(bar(_add(at, _mul(side, -0.05)), _add(at, _mul(side, 0.05)), 0.012, 'dark'))
    m.merge(ribbon(_add(at, (0.0, 0.0, -0.01)), down, side))
    return m


def on_ground(m):
    """Local ground (z = 0) -> the start's ground plane."""
    return m.map(lambda p: (p[0], p[1], p[2] + ground_z(p[0])))


def placed(m, x, y, yaw_deg):
    a = math.radians(yaw_deg)
    c, s = math.cos(a), math.sin(a)
    return on_ground(m.map(lambda p: (x + c * p[0] - s * p[1], y + s * p[0] + c * p[1], p[2])))


# ---------------------------------------------------------------------------------------------- the items
def ladder():
    """Boarding ladder at the left cockpit sill: two round rails, yellow treads, a blue spreader foot, standoff pads on
    the chine, hooks over the sill."""
    m = Mesh()
    yt, zt = LADDER_TOP
    foot = {x: (x, LADDER_FOOT_Y, ground_z(x) + 0.03) for x in LADDER_X}
    top = {x: (x, yt, zt) for x in LADDER_X}
    for x in LADDER_X:
        m.merge(cylinder(foot[x], top[x], LADDER_RAIL_R, 'alu'))
        # blue band near the foot (as on the photos), hooks over the sill
        m.merge(cylinder(foot[x], _add(foot[x], _mul(_norm(_sub(top[x], foot[x])), 0.35)), LADDER_RAIL_R + 0.003, 'blue'))
        m.merge(tube([top[x], (x, yt - 0.08, zt + 0.06), (x, yt - 0.15, zt + 0.04), (x, yt - 0.16, zt - 0.04)], 0.012, 'dark'))
        # standoff pad against the chine (y 0.82 at z 0.35)
        f = (0.35 - foot[x][2]) / (zt - foot[x][2])
        p = _add(foot[x], _mul(_sub(top[x], foot[x]), f))
        m.merge(box(_add(p, (0.0, -0.035, 0.0)), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0.025, 0.02, 0.04), 'rubber'))
    # treads every LADDER_STEP along the rails, level
    L = math.hypot(LADDER_FOOT_Y - yt, zt - foot[LADDER_X[0]][2])
    k = 1
    while k * LADDER_STEP < L - 0.15:
        f = k * LADDER_STEP / L
        y = LADDER_FOOT_Y + (yt - LADDER_FOOT_Y) * f
        z = foot[LADDER_X[0]][2] + (zt - foot[LADDER_X[0]][2]) * f
        x0, x1 = LADDER_X
        m.merge(box(((x0 + x1) / 2, y, z), ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                    ((x1 - x0) / 2 - LADDER_RAIL_R, 0.055, 0.012), 'yellow'))
        k += 1
    # spreader foot: a blue bar along x with rubber pads, braces up to the rails
    xm = sum(LADDER_X) / 2
    fy = LADDER_FOOT_Y + 0.05
    ends = [(xm - 0.45, fy, ground_z(xm - 0.45) + 0.03), (xm + 0.45, fy, ground_z(xm + 0.45) + 0.03)]
    m.merge(bar(ends[0], ends[1], 0.04, 'blue'))
    for e in ends:
        m.merge(box(_add(e, (0, 0, -0.015)), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0.05, 0.06, 0.015), 'rubber'))
    for e, x in zip(ends, LADDER_X):
        p = _add(foot[x], _mul(_norm(_sub(top[x], foot[x])), 0.45))
        m.merge(bar(e, p, 0.025, 'blue'))
    return m


def ladder_motion():
    """(pivot, axis, keys [(p, dx, dy, dz, angle)]): turned outward about the foot line until flat, then carried."""
    yt, zt = LADDER_TOP
    zf = ground_z(sum(LADDER_X) / 2) + 0.03
    vy, vz = yt - LADDER_FOOT_Y, zt - zf
    # about +x: (y, z) -> (y c - z s, y s + z c); flat (z' = 0) with the top outward (y' > 0)
    ang = math.atan2(-vz, vy)
    if vy * math.cos(ang) - vz * math.sin(ang) < 0:
        ang += math.pi
    ang = (ang + math.pi) % (2 * math.pi) - math.pi
    pivot = (sum(LADDER_X) / 2, LADDER_FOOT_Y, zf)
    ax, ay = LADDER_AWAY
    way = [(0.0, 0, 0, 0, 0.0), (0.55, 0, 0, 0.02, ang), (1.0, ax, ay, 0.02, ang)]
    return pivot, (1.0, 0.0, 0.0), eased(way)


def _lip_x(y, z):
    a, b, c = LIP_PLANE
    return a + b * abs(y) + c * z


def _cover_corners(side):
    """The plug's face corners (IB, OB, OT, IT): the opening's corners, inset, COVER_RECESS behind the lip plane."""
    s = 1 if side == 'L' else -1
    yz = [(s * y, z) for _, y, z in INTAKE]
    cy, cz = sum(p[0] for p in yz) / 4, sum(p[1] for p in yz) / 4
    face = []
    for y, z in yz:
        d = math.hypot(cy - y, cz - z)
        y2, z2 = y + (cy - y) / d * COVER_INSET, z + (cz - z) / d * COVER_INSET
        face.append((_lip_x(y2, z2) - COVER_RECESS, y2, z2))
    c = _mul(_add(_add(face[0], face[1]), _add(face[2], face[3])), 0.25)
    return face, c


def _face_frame(face):
    """(normal out of the intake, 'up' along the face, 'side' IB -> OB) of a cover face."""
    n = _norm(_cross(_sub(face[2], face[0]), _sub(face[3], face[1])))
    if n[0] < 0:
        n = _mul(n, -1)
    up = _norm(_sub(_mul(_add(face[2], face[3]), 0.5), _mul(_add(face[0], face[1]), 0.5)))
    side = _norm(_sub(face[1], face[0]))
    return n, up, side


def handles(face, n, up, side, mat='black', across=(0.22, 0.78), along=(0.30, 0.70), stand=0.05):
    """Two webbing loops on a face (pulled by hand): across the face at `across`, from `along` low to high."""
    m = Mesh()
    lo = lambda t, a: _add(_add(face[0], _mul(_sub(face[1], face[0]), t)), _mul(_sub(_add(face[3], _mul(_sub(face[2], face[3]), t)),
                                                                                    _add(face[0], _mul(_sub(face[1], face[0]), t))), a))
    for t in across:
        a, b = lo(t, along[0]), lo(t, along[1])
        mid = _mul(_add(a, b), 0.5)
        pts = [a, _add(_add(a, _mul(n, stand * 0.7)), _mul(up, 0.03)), _add(mid, _mul(n, stand)),
               _add(_add(b, _mul(n, stand * 0.7)), _mul(up, -0.03)), b]
        for p, q in zip(pts, pts[1:]):
            d = _norm(_sub(q, p))
            L = math.sqrt(_dot(_sub(q, p), _sub(q, p)))
            m.merge(box(_mul(_add(p, q), 0.5), (d, side, _cross(d, side)), (L / 2 + 0.004, 0.019, 0.004), mat))
        # stitched end tabs on the face
        for e in (a, b):
            m.merge(box(_add(e, _mul(n, 0.003)), (side, up, n), (0.024, 0.03, 0.003), mat))
    return m


def pillow(m, face, back, out, front_mat, side_mat, fuv, bulge=0.025, grid=6):
    """A plug: the front (face corners in UV order, uv corners fuv) a padded fabric face bulging `bulge` along `out`
    in a grid, the back and the sides plain; one closed piece."""
    def bil(c, u, v):
        return _add(_add(_mul(c[0], (1 - u) * (1 - v)), _mul(c[1], u * (1 - v))), _add(_mul(c[2], u * v), _mul(c[3], (1 - u) * v)))
    vs, faces, uvs = [], [], []
    for j in range(grid + 1):
        for i in range(grid + 1):
            u, v = i / grid, j / grid
            b = bulge * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)
            vs.append(_add(bil(face, u, v), _mul(out, b)))
    fu = lambda u, v: bil([tuple(x) + (0.0,) for x in fuv], u, v)[:2]
    for j in range(grid):
        for i in range(grid):
            a = j * (grid + 1) + i
            faces.append((a, a + 1, a + grid + 2, a + grid + 1))
            uvs.append(_fixed(front_mat, [fu(i / grid, j / grid), fu((i + 1) / grid, j / grid),
                                          fu((i + 1) / grid, (j + 1) / grid), fu(i / grid, (j + 1) / grid)]))
    nb = len(vs)
    vs += list(back)
    faces.append((nb, nb + 1, nb + 2, nb + 3))
    uvs.append(_flat(side_mat))
    ring = [j * (grid + 1) + i for i in range(grid + 1) for j in [0]] + \
           [j * (grid + 1) + grid for j in range(1, grid + 1)] + \
           [grid * (grid + 1) + i for i in range(grid - 1, -1, -1)] + \
           [j * (grid + 1) for j in range(grid - 1, 0, -1)]
    corner_k = [0, grid, 2 * grid, 3 * grid]          # ring indices of the four corners
    # the sides: each ring edge to the back edge of its side
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]
        side_i = k // grid
        faces.append((a, b, nb + (side_i + 1) % 4, nb + side_i) if (k + 1) % grid == 0 else (a, b, nb + side_i))
        uvs.append(_flat(side_mat))
    m.add(vs, faces, uvs)
    return m


def cover(side):
    """Intake plug: a cushion pushed into the duct, its face COVER_RECESS behind the lip (painted: REMOVE BEFORE
    FLIGHT, stitched border), two handles, a strap hanging from its lower edge."""
    face, _ = _cover_corners(side)
    n, up, sd = _face_frame(face)
    back = []
    cb = _mul(_add(_add(face[0], face[1]), _add(face[2], face[3])), 0.25)
    for p in face:
        q = _add(p, _mul(_norm(_sub(cb, p)), 0.02))
        back.append((q[0] - COVER_DEPTH, q[1], q[2]))
    # left: inboard on the viewer's left (seen from ahead); right: outboard on the left
    fuv = ((0, 0), (1, 0), (1, 1), (0, 1)) if side == 'L' else ((1, 0), (0, 0), (0, 1), (1, 1))
    m = Mesh()
    pillow(m, face, back, n, 'cover', 'red', fuv)
    m.merge(handles(face if side == 'L' else [face[1], face[0], face[3], face[2]], n, up,
                    sd if side == 'L' else _mul(sd, -1), stand=0.06))
    return m


def cover_motion(side):
    """(pivot, axis, keys): pulled out of the duct ahead, lowered, laid face up on the ramp beside the intake."""
    face, c = _cover_corners(side)
    n, _, _ = _face_frame(face)
    axis = _cross(n, (0.0, 0.0, 1.0))
    ang = math.asin(min(1.0, math.sqrt(_dot(axis, axis))))
    if _dot(n, (0, 0, 1)) < 0:
        ang = math.pi - ang
    axis = _norm(axis)
    s = 1 if side == 'L' else -1
    sx, sy = COVER_SPOT[0], s * COVER_SPOT[1]
    target = (sx, sy, ground_z(sx) + COVER_DEPTH / 2 + 0.01)
    d = _sub(target, c)
    # pulled straight out along the duct by its handles (the face's normal: forward, outboard and down - in-game
    # 2026-11-28 a pull along x alone, then the turn, read as lifting it up), then laid face up on the ramp beside it
    pull = _mul(n, COVER_RECESS + COVER_DEPTH + 0.08)
    way = [(0.0, 0, 0, 0, 0.0), (0.40, pull[0], pull[1], pull[2], 0.0), (0.82, d[0], d[1], d[2] + 0.12, ang),
           (1.0, d[0], d[1], d[2], ang)]
    return c, axis, eased(way)


def chocks():
    """Per wheel: two chocks (wedge toward the tyre) and the rope between them on the outboard side."""
    out = {}
    for key, (x, y, r, w) in WHEELS.items():
        m = Mesh()
        reach = math.sqrt(r * r - (r - CHOCK_H) ** 2) + CHOCK_GAP
        width = w + 0.14
        for sgn in (-1, 1):
            xn = x + sgn * reach                 # face toward the tyre
            xb = xn + sgn * CHOCK_L              # back
            # wedge: bottom xn..xb, top from xn + 0.07 (sloping face) to xb
            xt = xn + sgn * 0.07
            vs = []
            for yy in (y - width / 2, y + width / 2):
                vs += [(xn, yy, 0.0), (xb, yy, 0.0), (xb, yy, CHOCK_H), (xt, yy, CHOCK_H)]
            faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
            m.add(vs, faces, [_flat('yellow', 4)] * 6)
        # rope on the outboard side (the nose wheel: its left), a little bowed, lying on the ground
        so = 1 if key in ('N', 'L') else -1
        yr = y + so * (width / 2 + 0.03)
        ends = [(x - reach - CHOCK_L * 0.5, y + so * width / 2, 0.08), (x + reach + CHOCK_L * 0.5, y + so * width / 2, 0.08)]
        path = [ends[0], (ends[0][0] + 0.05, yr, 0.012), (x, yr + so * 0.08, 0.012), (ends[1][0] - 0.05, yr, 0.012), ends[1]]
        m.merge(tube(path, 0.008, 'black', seg=6))
        out[key] = on_ground(m)
    return out


def extinguisher():
    """Wheeled extinguisher (yellow-green cylinder on a hand truck), local frame on the ground, facing +x."""
    m = Mesh()
    R, H = 0.17, 0.85
    m.merge(cylinder((0.0, 0.0, 0.12), (0.0, 0.0, 0.12 + H), R, 'green', seg=16))
    m.merge(cylinder((0.0, 0.0, 0.12 + H), (0.0, 0.0, 0.12 + H + 0.05), 0.06, 'dark'))     # valve
    for s in (-1, 1):
        m.merge(cylinder((-0.12, s * 0.22, 0.20), (-0.12, s * 0.28, 0.20), 0.20, 'rubber', seg=14))   # wheels
        m.merge(cylinder((-0.12, s * 0.20, 0.20), (-0.12, s * 0.30, 0.20), 0.07, 'dark', seg=10))
        m.merge(bar((-0.12, s * 0.20, 0.20), (-0.20, s * 0.20, 1.15), 0.03, 'dark'))           # frame / handle
        m.merge(bar((0.05, s * 0.20, 0.03), (-0.12, s * 0.20, 0.20), 0.03, 'dark'))
    m.merge(bar((-0.20, 0.21, 1.15), (-0.20, -0.21, 1.15), 0.03, 'dark'))
    m.merge(bar((0.05, 0.21, 0.03), (0.05, -0.21, 0.03), 0.03, 'dark'))
    m.merge(cylinder((-0.12, -0.21, 0.20), (-0.12, 0.21, 0.20), 0.015, 'dark'))              # axle
    # hose coiled on the side, the nozzle on top
    coil = [(0.0 + 0.10 * math.cos(a), R + 0.03, 0.55 + 0.10 * math.sin(a)) for a in [i * 2 * math.pi / 12 for i in range(12)]]
    m.merge(tube(coil, 0.015, 'rubber', seg=6, closed=True))
    m.merge(tube([(0.0, 0.0, 0.12 + H + 0.05), (0.08, 0.08, 1.05), (0.12, R + 0.03, 0.65)], 0.015, 'rubber', seg=6))
    m.merge(box((0.0, R + 0.005, 0.60), ((0, 1, 0), (1, 0, 0), (0, 0, 1)), (0.004, 0.08, 0.10), 'green',
                uv_front=((1, 0), (0, 0), (0, 1), (1, 1)), front_mat='label'))         # label, read from outside
    return m


def toolcart():
    """Black tool cart with yellow corner guards on four casters, a handle at one end."""
    m = Mesh()
    lx, ly, z0, z1 = 0.45, 0.30, 0.16, 0.95
    eye = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    m.merge(box((0.0, 0.0, (z0 + z1) / 2), eye, (lx, ly, (z1 - z0) / 2), 'tool'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.merge(box((sx * (lx - 0.02), sy * (ly - 0.02), z1 - 0.05), eye, (0.035, 0.035, 0.06), 'yellow'))
            m.merge(box((sx * (lx - 0.02), sy * (ly - 0.02), z0 + 0.05), eye, (0.035, 0.035, 0.06), 'yellow'))
            m.merge(bar((sx * (lx - 0.06), sy * (ly - 0.06), z0), (sx * (lx - 0.06), sy * (ly - 0.06), 0.09), 0.025, 'dark'))
            m.merge(cylinder((sx * (lx - 0.06) - 0.02, sy * (ly - 0.06) - 0.02, 0.06),
                             (sx * (lx - 0.06) - 0.02, sy * (ly - 0.06) + 0.02, 0.06), 0.06, 'rubber', seg=10))
    m.merge(tube([(-lx, 0.22, z1 - 0.10), (-lx - 0.15, 0.22, z1 + 0.05), (-lx - 0.15, -0.22, z1 + 0.05), (-lx, -0.22, z1 - 0.10)],
                 0.012, 'alu'))
    # drawer lines (thin dark strips on the long side)
    for k in range(4):
        z = z0 + 0.15 + k * 0.17
        m.merge(box((0.0, ly + 0.002, z), eye, (lx - 0.06, 0.003, 0.006), 'dark'))
    return m


def hose_coil(top_z):
    """The unplugged hose, three turns on the cart's top."""
    m = Mesh()
    cx, cy = COIL_AT
    for k in range(3):
        ring = [(cx + (0.24 - 0.04 * k) * math.cos(a), cy + (0.24 - 0.04 * k) * math.sin(a), top_z + 0.025 + 0.04 * k)
                for a in [i * 2 * math.pi / 16 for i in range(16)]]
        m.merge(tube(ring, 0.02, 'hose', seg=6, closed=True))
    return m


def surface_lock(xf, xa, y, top, bot_f, bot_a, half=LOCK_HALF_SPAN):
    """Gust lock across a surface's side gap: a red plate on the upper skin and one on the lower skin (each on a thin
    black rubber pad), joined by a blade through the gap; two clamp knobs on top, the streamer from the lower plate's
    aft edge."""
    m = Mesh()
    yy = (0.0, 1.0, 0.0)
    xm, half_c = (xf + xa) / 2, abs(xf - xa) / 2
    m.merge(box((xm, y, top + LOCK_PAD / 2), ((1, 0, 0), yy, (0, 0, 1)), (half_c, half, LOCK_PAD / 2), 'rubber'))
    m.merge(box((xm, y, top + LOCK_PAD + LOCK_T / 2), ((1, 0, 0), yy, (0, 0, 1)), (half_c, half, LOCK_T / 2), 'redpaint'))
    u = _norm((xf - xa, 0.0, bot_f - bot_a))
    w = _cross(u, yy)                   # up, square to the lower skin
    mid = (xm, y, (bot_f + bot_a) / 2)
    m.merge(box(_add(mid, _mul(w, -LOCK_PAD / 2)), (u, yy, w), (half_c, half, LOCK_PAD / 2), 'rubber'))
    m.merge(box(_add(mid, _mul(w, -LOCK_PAD - LOCK_T / 2)), (u, yy, w), (half_c, half, LOCK_T / 2), 'redpaint'))
    zb = (bot_f + bot_a) / 2
    m.merge(box((xm, y, (top + zb) / 2), ((1, 0, 0), yy, (0, 0, 1)), (half_c * 0.6, 0.004, (top - zb) / 2), 'redpaint'))
    for sx in (-0.5, 0.5):              # clamp knobs on the top plate
        p = (xm + sx * half_c, y, top + LOCK_PAD + LOCK_T)
        m.merge(cylinder(p, _add(p, (0, 0, 0.02)), 0.012, 'dark', seg=8))
    t = (xa + 0.02, y, bot_a - LOCK_PAD - LOCK_T)
    m.merge(bar(t, _add(t, (0, 0, -0.03)), 0.006, 'dark'))
    m.merge(ribbon(_add(t, (0, 0, -0.03)), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0)))
    return m


def stab_lock(s):
    """Stabilator lock (side s = 1 left, -1 right): a red block with a black rubber face pressed under the gap between
    the flaperon's trailing edge and the stabilator's leading edge, a blade up through the gap to a strap over it; the
    streamer from a bolt in the block's middle."""
    (x, y), (ux, uy), top, bot = STAB_LOCK
    c = (x, s * y)
    u = (ux, s * uy, 0.0)
    n = _norm(_cross((0.0, 0.0, 1.0), u))      # across the gap, in the wing plane
    z = (0.0, 0.0, 1.0)
    hu, hn = STAB_HALF
    m = Mesh()
    m.merge(box((c[0], c[1], bot - 0.006), (u, n, z), (hu, hn, 0.006), 'rubber'))
    m.merge(box((c[0], c[1], bot - 0.012 - 0.0125), (u, n, z), (hu, hn, 0.0125), 'redpaint'))
    m.merge(box((c[0], c[1], (top + bot) / 2), (u, n, z), (hu * 0.7, 0.006, (top - bot) / 2), 'redpaint'))
    m.merge(box((c[0], c[1], top + 0.004), (u, n, z), (hu * 0.85, 0.035, 0.004), 'redpaint'))
    b = (c[0], c[1], bot - 0.037)
    m.merge(cylinder(_add(b, (0, 0, 0.004)), _add(b, (0, 0, -0.012)), 0.010, 'dark', seg=8))
    m.merge(bar(_add(b, (0, 0, -0.012)), _add(b, (0, 0, -0.035)), 0.006, 'dark'))
    m.merge(ribbon(_add(b, (0, 0, -0.035)), (0.0, 0.0, -1.0), u))
    return m


def start_covers():
    """Everything taken off before engine start besides the plugs: probe sleeves, control surface locks (flaperon,
    aileron: across their outboard side gaps), stabilator locks (wing to stabilator), the hook's safety pin - each with
    its streamer. (No covers on the nose's diamond panels: not every livery has them, 2026-11-27.)"""
    m = probe_covers()
    for s in (1, -1):
        for xf, xa, y, top, bf, ba in SURFACE_LOCKS.values():
            m.merge(surface_lock(xf, xa, s * y, top, bf, ba))
        m.merge(stab_lock(s))
    # hook: a safety pin across its point, a ring under it, the streamer hanging from the ring
    hx, hz = HOOK_PIN
    m.merge(cylinder((hx, -0.045, hz), (hx, 0.045, hz), 0.0045, 'alu', seg=8))
    m.merge(box((hx, 0.05, hz), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0.006, 0.008, 0.012), 'dark'))      # its head
    ring = [(hx + 0.014 * math.sin(a), 0.0, hz - 0.016 + 0.014 * math.cos(a)) for a in [i * 2 * math.pi / 12 for i in range(12)]]
    m.merge(tube(ring, 0.002, 'alu', seg=5, closed=True))
    m.merge(ribbon((hx, 0.0, hz - 0.032), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)))
    return m


def probe_covers():
    """Red sleeves over the two nose probes' tips, a streamer hanging from each sleeve's end."""
    m = Mesh()
    for s in (1, -1):
        root, tip = [(p[0], s * p[1], p[2]) for p in PROBE]
        d = _norm(_sub(tip, root))
        a, b = _sub(tip, _mul(d, PROBE_CAP[0])), _add(tip, _mul(d, PROBE_CAP[1]))
        m.merge(cylinder(a, b, PROBE_CAP_R, 'red', seg=10))
        m.merge(ribbon(_add(b, (-0.01, 0.0, -PROBE_CAP_R)), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0)))
    return m


def _exhaust_corners(side):
    """Aft face corners seen from behind: viewer's left bottom, right bottom, right top, left top (+y is on the left)."""
    s = 1 if side == 'L' else -1
    ys = sorted((s * EXHAUST_Y[0], s * EXHAUST_Y[1]))
    yl, yr = ys[1], ys[0]
    return {k: [(yl, z0), (yr, z0), (yr, z1), (yl, z1)] for k, (z0, z1) in EXHAUST_Z.items()}


def exhaust_cover(side):
    """Plug filling the open nozzle between the sidewalls and the parked flaps (black padded face: REMOVE BEFORE
    FLIGHT, stitched border), two rigid handles near the sidewalls."""
    xa, xf = EXHAUST_X
    c = _exhaust_corners(side)
    face = [(xa, y, z) for y, z in c['aft']]
    back = [(xf, y, z) for y, z in c['fwd']]
    m = Mesh()
    v0, v1 = EXHAUST_BAND
    pillow(m, face, back, (-1.0, 0.0, 0.0), 'exhaust', 'black', ((0, v0), (1, v0), (1, v1), (0, v1)), bulge=0.03)
    z0, z1 = EXHAUST_Z['aft']
    for t in (0.13, 0.87):
        y = face[0][1] + (face[1][1] - face[0][1]) * t
        lo, hi = z0 + (z1 - z0) * 0.30, z0 + (z1 - z0) * 0.70
        x = xa - 0.03
        m.merge(tube([(x + 0.02, y, lo), (x - 0.05, y, lo + 0.02), (x - 0.05, y, hi - 0.02), (x + 0.02, y, hi)], 0.011, 'alu'))
        for zz in (lo, hi):
            m.merge(box((x + 0.015, y, zz), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0.012, 0.025, 0.03), 'dark'))
    return m


def exhaust_motion(side):
    """Pulled out aft, turned face up, laid on the ramp behind the tail."""
    s = 1 if side == 'L' else -1
    xa, xf = EXHAUST_X
    c = ((xa + xf) / 2, s * sum(EXHAUST_Y) / 2, sum(EXHAUST_Z['aft']) / 2)
    ang = math.pi / 2                       # about +y: the aft face (-x) turns up
    tx, ty = EXHAUST_SPOT[0], s * EXHAUST_SPOT[1]
    target = (tx, ty, ground_z(tx) + abs(xa - xf) / 2 + 0.01)
    d = _sub(target, c)
    # pulled straight out aft, clear of the flaps' trailing edges (x -5.45) with room for its turn, then laid face up
    # on the ramp behind the tail (2026-11-28: pull it out, then put it down)
    clear = (xa - EXHAUST_FLAP_TE) + 0.05 + (EXHAUST_Z['aft'][1] - EXHAUST_Z['aft'][0]) / 2
    way = [(0.0, 0, 0, 0, 0.0), (0.40, -abs(clear), 0.0, 0.0, 0.0), (0.82, d[0], d[1], d[2] + 0.12, ang),
           (1.0, d[0], d[1], d[2], ang)]
    return c, (0.0, 1.0, 0.0), eased(way)


def _catmull(points, n=6):
    out = []
    P = [points[0]] + list(points) + [points[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t +
                                    (-a + 3 * b - 3 * c + d) * t ** 3) for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(points[-1])
    return out


def power_hose():
    """From the cart's socket down to the ramp, along it in an easy curve to under the fuselage and up to the
    receptacle (a dark plug at the end)."""
    g = lambda x: ground_z(x) + HOSE_R + HOSE_LIFT
    sx, sy, sz = CART_SOCKET[0], CART_SOCKET[1] + CART_SHIFT_Y, CART_SOCKET[2] + ground_z(CART_SOCKET[0]) - CART_GROUND
    px, py, pz = PLUG
    ctrl = [(sx, sy, sz), (sx - 0.05, sy - 0.12, g(sx) + 0.30), (sx - 0.15, sy - 0.40, g(sx)), (4.70, 7.0, g(4.7)),
            (4.75, 5.5, g(4.75)), (5.05, 4.0, g(5.05)), (5.10, 2.5, g(5.1)), (4.98, 1.25, g(4.98)),
            (px, py + 0.30, g(px) + 0.06), (px, py + 0.12, -1.10), (px, py + 0.03, -0.88), (px, py, pz - 0.08)]
    m = tube(_catmull(ctrl), HOSE_R, 'hose', seg=8)
    m.merge(cylinder((px, py, pz - 0.12), (px, py, pz), 0.04, 'dark', seg=10))
    return m


def aim9_caps():
    """Yellow seeker caps on the AIM-9X noses (stores_f22 placement, retracted in the side bays), a streamer each."""
    import stores_f22 as S
    out = {}
    for st, side in (('Pylon1', 'L'), ('Pylon11', 'R')):
        X, Y = (_norm(a) for a in S.AIM9_FRAME[st])
        c = _sub(S.CONN[st], _mul(Y, S.AIM9_DROP))
        nose = _add(c, _mul(X, 3.02 / 2))
        m = Mesh()
        m.merge(cylinder(_sub(nose, _mul(X, 0.13)), _add(nose, _mul(X, 0.02)), 0.075, 'capyellow', seg=14))
        m.merge(ribbon(_add(nose, (-0.02, 0.0, -0.075)), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0)))
        out[side] = m
    return out


def _tf(p):
    """Trailer frame (x along the tow bar, ground z 0) -> aircraft axes on the start's ground."""
    x0, y0, yaw = TRAILER_AT
    a = math.radians(yaw)
    c, s_ = math.cos(a), math.sin(a)
    x, y = x0 + c * p[0] - s_ * p[1], y0 + s_ * p[0] + c * p[1]
    return (x, y, p[2] + ground_z(x))


TRAILER_MSL = [('aim120', 3.657, 0.0889, s_ * TRAILER_UP[0], TRAILER_UP[1]) for s_ in (1, -1)] + \
              [('aim9x', 3.02, 0.0635, s_ * TRAILER_LOW[0], TRAILER_LOW[1]) for s_ in (1, -1)]
TRAILER_NOSE_X = 1.85                      # missile noses at the trailer's front deck edge
TRAILER_DECK_FRONT = 1.875                 # the front deck's edge channel, its forward face


def _msl_axis_z(r, rail_top):
    return rail_top + 0.03 + r


def trailer():
    """The trailer itself (trailer frame)."""
    m = Mesh()
    eye = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    B = lambda c, h, mat: m.merge(box(c, eye, h, mat))
    # frame: two main beams, cross members
    for sy in (1, -1):
        B((0.0, sy * 0.55, 0.62), (1.85, 0.075, 0.09), 'trailer')
    for x in (-1.78, -1.0, -0.2, 0.6, 1.0, 1.78):
        B((x, 0.0, 0.62), (0.05, 0.55, 0.06), 'trailer')
    # tread-plate decks over the axles, channel edges, shackles
    for xc in (1.42, -1.42):
        B((xc, 0.0, 0.75), (0.43, 0.95, 0.02), 'tread')
        for sy in (1, -1):
            B((xc, sy * 0.93, 0.73), (0.43, 0.025, 0.05), 'trailer')
            for k in (-1, 1):
                pts = [(xc + 0.25 * k + 0.03 * math.cos(t), sy * 0.972, 0.66 + 0.03 * math.sin(t))
                       for t in [i * 2 * math.pi / 10 for i in range(10)]]
                m.merge(tube(pts, 0.007, 'dark', seg=5, closed=True))
        B((xc + 0.43 * (1 if xc > 0 else -1), 0.0, 0.73), (0.025, 0.95, 0.05), 'trailer')
    # wheels, hubs, axles, spring hangers
    for xw in (1.30, -1.30):
        for sy in (1, -1):
            m.merge(cylinder((xw, sy * 0.70, 0.36), (xw, sy * 0.91, 0.36), 0.36, 'rubber', seg=24))
            m.merge(cylinder((xw, sy * 0.905, 0.36), (xw, sy * 0.93, 0.36), 0.19, 'dark', seg=16))
            m.merge(cylinder((xw, sy * 0.93, 0.36), (xw, sy * 0.96, 0.36), 0.06, 'dark', seg=10))
            B((xw, sy * 0.55, 0.47), (0.25, 0.04, 0.04), 'dark')
            B((xw, sy * 0.55, 0.42), (0.04, 0.04, 0.10), 'trailer')
        m.merge(cylinder((xw, -0.70, 0.36), (xw, 0.70, 0.36), 0.04, 'dark', seg=10))
    # tow bar: A-frame to a lunette ring, a jack stand
    for sy in (1, -1):
        m.merge(tube([(1.70, sy * 0.45, 0.55), (2.6, sy * 0.12, 0.48), (3.35, 0.0, 0.45)], 0.035, 'trailer', seg=8))
    ring = [(3.47 + 0.08 * math.cos(t), 0.08 * math.sin(t), 0.45) for t in [i * 2 * math.pi / 14 for i in range(14)]]
    m.merge(tube(ring, 0.018, 'dark', seg=6, closed=True))
    m.merge(cylinder((3.0, 0.0, 0.47), (3.0, 0.0, 0.06), 0.025, 'dark'))
    B((3.0, 0.0, 0.03), (0.07, 0.07, 0.03), 'dark')
    # adapter rails on uprights, cradles
    for (y, top), kind in ((TRAILER_UP, 'aim120'), (TRAILER_LOW, 'aim9x')):
        r = 0.0889 if kind == 'aim120' else 0.0635
        L = 3.657 if kind == 'aim120' else 3.02
        for sy in (1, -1):
            yy = sy * y
            B((TRAILER_NOSE_X - L / 2, yy, top - 0.03), (L / 2 - 0.1, 0.05, 0.03), 'trailer')
            for x in (TRAILER_NOSE_X - 0.35, TRAILER_NOSE_X - L + 0.35):
                h = top - 0.06 - 0.68
                if h > 0.02:
                    B((x, yy, 0.68 + h / 2), (0.04, 0.04, h / 2), 'trailer')
                    m.merge(bar((x, yy, 0.69), (x, yy * 0.6 if abs(yy) > 0.6 else yy, 0.69 + h * 0.6), 0.03, 'trailer'))
            for d in CRADLES[kind]:
                x = TRAILER_NOSE_X - d
                B((x, yy, top + 0.015), (0.035, r + 0.04, 0.015), 'trailer')
                for sw in (1, -1):
                    B((x, yy + sw * (r + 0.025), top + 0.03 + r * 0.6), (0.035, 0.012, r * 0.6), 'trailer')
                    B((x, yy + sw * (r + 0.022), top + 0.03 + r * 0.6), (0.036, 0.004, r * 0.5), 'rubber')
    # reflectors and the stencil plates on the main beams' outer faces
    for sy in (1, -1):
        for xr in (-1.86, 1.86):
            m.merge(box((xr, sy * 0.80, 0.70), eye, (0.005, 0.04, 0.025), 'redpaint'))
        for k, (x, v0) in enumerate(((1.15, 0.75), (0.15, 0.40), (-0.95, 0.05))):
            y = sy * (0.625 + 0.002)
            uv = ((1, v0), (0, v0), (0, v0 + 0.2), (1, v0 + 0.2)) if sy > 0 else ((0, v0), (1, v0), (1, v0 + 0.2), (0, v0 + 0.2))
            m.merge(box((x, y, 0.62), ((0, sy, 0), (1, 0, 0), (0, 0, 1)), (0.0015, 0.30, 0.06), 'trailer',
                        uv_front=uv, front_mat='stencil'))
    return m.map(_tf)


def trailer_load():
    """The missiles' own pieces on the trailer: yellow seeker caps, straps over them, streamers (trailer frame)."""
    m = Mesh()
    for kind, L, r, y, top in TRAILER_MSL:
        z = _msl_axis_z(r, top)
        nose = (TRAILER_NOSE_X, y, z)
        m.merge(cylinder((TRAILER_NOSE_X - 0.13, y, z), (TRAILER_NOSE_X + 0.02, y, z), r + 0.011, 'capyellow', seg=14))
        # the streamer from the cap's front rim, hanging clear in front of the deck's edge channel (x 1.875 - in-game
        # 2026-11-28 it hung from under the cap straight through the deck)
        rim = (TRAILER_NOSE_X + 0.02, y, z - r * 0.6)
        tie = (TRAILER_DECK_FRONT + 0.035, y, z - r - 0.02)
        m.merge(bar(rim, tie, 0.004, 'dark'))
        m.merge(ribbon(tie, (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)))
        for d in CRADLES[kind]:
            x = TRAILER_NOSE_X - d
            arc = [(x, y + (r + 0.008) * math.cos(t), z + (r + 0.008) * math.sin(t)) for t in [i * math.pi / 8 for i in range(9)]]
            for a, b in zip(arc, arc[1:]):
                dd = _norm(_sub(b, a))
                Ls = math.sqrt(_dot(_sub(b, a), _sub(b, a)))
                m.merge(box(_mul(_add(a, b), 0.5), (dd, (1.0, 0.0, 0.0), _cross(dd, (1.0, 0.0, 0.0))), (Ls / 2 + 0.002, 0.022, 0.0025), 'webbing'))
    return m.map(_tf)


def trailer_missiles():
    """Mesh dicts of the missiles on the trailer (stores_f22 geometry and materials; their faces turned by ac_f22)."""
    import stores_f22 as S
    out = []
    for i, (kind, L, r, y, top) in enumerate(TRAILER_MSL):
        v, f, u, sm, mp, _ = S.placed(kind, (TRAILER_NOSE_X, y, _msl_axis_z(r, top)))
        out.append(dict(name='Ground_TrailerMsl_%s_%d' % (kind, i), part='Ground_TrailerMsl',
                        material='store_aim120' if kind == 'aim120' else 'store_aim9x', verts=[_tf(p) for p in v],
                        faces=[tuple(q) for q in f], uvs=list(u), smooth=list(sm), oriented=False))
    return out


def objects(cart_top_z=None):
    """Our mesh dicts for ac_f22.py (as stores_f22.aircraft_stores): name, part, material, verts, faces, uvs, smooth.
    cart_top_z: the parked cart's top (from its geometry, ac_f22.py) for the hose coil."""
    items = [('Ground_Ladder', ladder())]
    for side in ('L', 'R'):
        items.append(('Ground_Cover' + side, cover(side)))           # moving copy, on the fixed body
        items.append(('Ground_CoverK' + side, cover(side)))          # in the intake, on the fuselage
    ch = chocks()
    for key in ('N', 'L', 'R'):
        items.append(('Ground_Chock' + key, ch[key]))
    for side in ('L', 'R'):
        items.append(('Ground_Exhaust' + side, exhaust_cover(side)))
        items.append(('Ground_ExhaustK' + side, exhaust_cover(side)))
    items.append(('Ground_RbfStart', start_covers()))
    caps = aim9_caps()
    for side in ('L', 'R'):
        items.append(('Ground_Aim9Cap' + side, caps[side]))
    items.append(('Ground_CartHose', power_hose()))
    items.append(('Ground_Trailer', trailer()))
    items.append(('Ground_TrailerLoad', trailer_load()))
    rg = Mesh()
    for p, axis, rl in RBF_GEAR:
        rg.merge(gear_pin(p, axis, rl))
    items.append(('Ground_RbfGear', rg))
    props = Mesh()
    props.merge(placed(extinguisher(), *EXTINGUISHER_AT))
    props.merge(placed(toolcart(), *TOOLCART_AT))
    items.append(('Ground_Props', props))
    if cart_top_z is not None:
        items.append(('Ground_HoseCoil', hose_coil(cart_top_z)))
    out = []
    for name, m in items:
        out += split(name, m)
    try:
        out += trailer_missiles()
    except ImportError:                 # (numpy: in Blender only; make_f22.py needs no geometry)
        pass
    return out


def _auto_uv(pts, span):
    """Planar projection in metres along the face's main axis, shifted to start inside the texture and squeezed into
    it if the face is larger than `span`."""
    n = _cross(_sub(pts[1], pts[0]), _sub(pts[-1], pts[0]))
    if len(pts) > 3:
        n = _add(n, _cross(_sub(pts[2], pts[1]), _sub(pts[0], pts[1])))
    ax = max(range(3), key=lambda i: abs(n[i]))
    a, b = [i for i in range(3) if i != ax]
    us = [p[a] / span for p in pts]
    vs = [p[b] / span for p in pts]
    out = []
    for w in (us, vs):
        lo = math.floor(min(w))
        w = [x - lo for x in w]
        hi = max(w)
        if hi > 1.0:
            w = [x / hi for x in w]
        out.append(w)
    return list(zip(*out))


def split(name, m):
    """Mesh dicts per material (one part, several objects): name, part, material, verts, faces, uvs, smooth."""
    groups = {}
    for f, uv, sm in zip(m.f, m.uv, m.sm):
        mat = uv[1]
        if uv[0] == 'fix':
            corners = list(uv[2])
        else:
            corners = _auto_uv([m.v[i] for i in f], MATS[mat][2])
        groups.setdefault(mat, []).append((f, corners, sm))
    out = []
    for mat, fs in sorted(groups.items()):
        used = sorted({i for f, _, _ in fs for i in f})
        remap = {i: k for k, i in enumerate(used)}
        out.append(dict(name='%s_%s' % (name, mat), part=name, material=material(mat), verts=[m.v[i] for i in used],
                        faces=[tuple(remap[i] for i in f) for f, _, _ in fs], uvs=[c for _, c, _ in fs],
                        smooth=[sm for _, _, sm in fs]))
    return out


# ---------------------------------------------------------------------------------------------- textures
# Painted in numpy (stores_f22's value noise), rows bottom-up: colour, height (bump), gloss, metal.
def _fbm(n, cells, amps, rng):
    import numpy as np
    import stores_f22 as S
    out = np.zeros((n, n), np.float32)
    for c, a in zip(cells, amps):
        cc = c if isinstance(c, tuple) else (c, c)
        out += a * S._noise(n, n, cc, rng).astype(np.float32)
    return out


def _lines(n, count, length, rng, width=1, axis_bias=None):
    """Mask of random short straight scratches."""
    import numpy as np
    m = np.zeros((n, n), np.float32)
    for _ in range(count):
        x0, y0 = rng.uniform(0, n, 2)
        a = rng.uniform(0, math.pi) if axis_bias is None else axis_bias + rng.normal(0, 0.15)
        L = rng.uniform(*length)
        t = np.linspace(0, L, int(L * 2) + 2)
        xs = np.clip((x0 + t * math.cos(a)).astype(int), 0, n - 1)
        ys = np.clip((y0 + t * math.sin(a)).astype(int), 0, n - 1)
        for w in range(width):
            m[np.clip(ys + w, 0, n - 1), xs] = 1.0
    return m


def _blur(a, r=1):
    import numpy as np
    out = a.copy()
    for ax in (0, 1):
        acc = np.zeros_like(out)
        for d in range(-r, r + 1):
            acc += np.roll(out, d, axis=ax)
        out = acc / (2 * r + 1)
    return out


def _maps(col, height, gloss, metal):
    import numpy as np
    return {'colour': np.clip(col, 0, 1).astype(np.float32), 'height': np.clip(height, 0, 1).astype(np.float32),
            'gloss': np.clip(gloss, 0, 1).astype(np.float32), 'metal': np.clip(metal, 0, 1).astype(np.float32)}


def _fabric(base, n, rng):
    """Coated fabric: wrinkles, a fine weave, grime stains, faded spots."""
    import numpy as np
    wr = _fbm(n, [(n // 3, n // 7), n // 12, n // 30], [1.0, 0.5, 0.25], rng)
    fine = _fbm(n, [3], [1.0], rng)
    i = np.arange(n)
    weave = (np.sin(i * 2 * math.pi / 3.0)[:, None] * np.sin(i * 2 * math.pi / 3.0)[None, :]).astype(np.float32)
    stain = np.clip((_fbm(n, [n // 5, n // 14], [1.0, 0.5], rng) - 0.35) * 2.5, 0, 1)
    fade = np.clip((_fbm(n, [n // 4], [1.0], rng) - 0.5) * 2.0, 0, 1)
    shade = 1 + 0.10 * wr + 0.05 * fine + 0.03 * weave - 0.22 * stain + 0.12 * fade
    col = np.array(base, np.float32)[None, None, :] * shade[..., None] + 0.015 * fade[..., None]
    return _maps(col, 0.5 + 0.18 * wr + 0.04 * weave - 0.03 * stain, 0.12 + 0.05 * wr - 0.05 * stain, np.zeros((n, n)))


def _paint(base, n, rng, under=(0.40, 0.41, 0.43)):
    """Painted metal in service: mottled, chipped down to metal / primer, scratched, grime and dust."""
    import numpy as np
    mott = _fbm(n, [n // 6, n // 18, 5], [1.0, 0.5, 0.3], rng)
    chip = np.clip((_fbm(n, [n // 40, n // 12], [1.0, 0.7], rng) - 0.78) * 8.0, 0, 1)
    scr = _blur(_lines(n, max(n // 6, 20), (6, n / 10), rng), 1)
    grime = np.clip((_fbm(n, [n // 4, n // 10], [1.0, 0.5], rng) - 0.1) * 1.2, 0, 1)
    dust = np.clip(_fbm(n, [n // 3], [1.0], rng), 0, 1)
    paint = np.array(base, np.float32)[None, None, :] * (1 + 0.07 * mott)[..., None]
    metal_c = np.array(under, np.float32)[None, None, :] * (1 + 0.15 * _fbm(n, [2], [1.0], rng))[..., None]
    col = paint * (1 - chip[..., None]) + metal_c * chip[..., None]
    col = col * (1 - 0.30 * grime[..., None]) * (1 - 0.25 * scr[..., None]) + 0.05 * dust[..., None]
    return _maps(col, 0.5 - 0.15 * chip - 0.08 * scr + 0.02 * mott, 0.40 - 0.18 * grime + 0.15 * chip, 0.8 * chip)


def _brushed(base, n, rng):
    import numpy as np
    streak = _fbm(n, [(1, n // 2), (2, n // 6)], [1.0, 0.5], rng)
    spots = np.clip((_fbm(n, [n // 10, 6], [1.0, 0.6], rng) - 0.7) * 3, 0, 1)
    scr = _blur(_lines(n, n // 8, (5, n / 6), rng), 1)
    col = np.array(base, np.float32)[None, None, :] * (1 + 0.07 * streak - 0.25 * spots - 0.12 * scr)[..., None]
    return _maps(col, 0.5 + 0.03 * streak - 0.05 * scr, 0.55 + 0.1 * streak - 0.2 * spots, np.full((n, n), 1.0) - 0.3 * spots)


def _rubber(base, n, rng):
    import numpy as np
    fine = _fbm(n, [2, 6], [1.0, 0.5], rng)
    dust = np.clip(_fbm(n, [n // 4, n // 12], [1.0, 0.5], rng), 0, 1)
    col = np.array(base, np.float32)[None, None, :] * (1 + 0.20 * fine)[..., None] + 0.06 * dust[..., None]
    return _maps(col, 0.5 + 0.10 * fine, 0.10 + 0.04 * fine - 0.05 * dust, np.zeros((n, n)))


def _plastic(base, n, rng):
    """Moulded plastic (the seeker caps): even colour, a faint mottle, no wear - the yellow paint's chipped edges read as
    artefacts on a cap (2026-11-28)."""
    import numpy as np
    mot = _fbm(n, [3, 8], [1.0, 0.4], rng)
    col = np.array(base, np.float32)[None, None, :] * (1 + 0.025 * mot)[..., None]
    return _maps(col, 0.5 + 0.02 * mot, 0.45 + 0.0 * mot, 0.0 * mot)


def _powder(base, n, rng):
    """Powder-coated steel: orange peel, scuffs (lighter), worn edges of use."""
    import numpy as np
    peel = _fbm(n, [4, 10], [1.0, 0.5], rng)
    scuff = 0.5 * _blur(_lines(n, n // 16, (6, n / 8), rng, width=1), 1)
    wear = np.clip((_fbm(n, [n // 8, n // 20], [1.0, 0.5], rng) - 0.55) * 3, 0, 1)
    col = np.array(base, np.float32)[None, None, :] * (1 + 0.05 * peel)[..., None] + (0.10 * scuff + 0.06 * wear)[..., None]
    return _maps(col, 0.5 + 0.06 * peel - 0.05 * scuff, 0.35 - 0.12 * wear, 0.3 * wear)


def _tread(base, n, rng):
    """Tread plate: raised diamond lugs in alternate directions, worn bright on top, grime in between."""
    import numpy as np
    cell = max(n // 16, 8)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cy, cx = (yy % cell) - cell / 2, (xx % cell) - cell / 2
    alt = ((yy // cell + xx // cell) % 2) * 2 - 1
    u = (cx + alt * cy) / (cell * 0.42)
    v = (cx - alt * cy) / (cell * 0.11)
    lug = np.clip(1.0 - (u * u + v * v), 0, 1)
    lug = np.clip(lug * 3, 0, 1)
    grime = np.clip(_fbm(n, [n // 6, n // 16], [1.0, 0.5], rng), 0, 1)
    shade = (1 + 0.06 * _fbm(n, [5], [1.0], rng)) * (1 - 0.25 * grime * (1 - lug)) + 0.18 * lug
    col = np.array(base, np.float32)[None, None, :] * shade[..., None]
    return _maps(col, 0.45 + 0.35 * lug, 0.30 + 0.25 * lug, 0.6 * lug)


def _text(col, height, s, row, colp, unit, colour, vertical=False, soft=True):
    """5x7 stencil text (stores_f22._FONT): horizontal from (row, colp) left to right, or turned to read upward."""
    import numpy as np
    import stores_f22 as S
    R, C = col.shape[:2]                    # (rectangular too: a band of a map)
    mask = np.zeros(col.shape[:2], np.float32)
    for i, ch in enumerate(s):
        for r, bits in enumerate(S._FONT.get(ch, S._FONT[' ']).split()):
            for k, b in enumerate(bits):
                if b != '1':
                    continue
                if not vertical:
                    rr, cc = row + (6 - r) * unit, colp + (i * 6 + k) * unit
                else:
                    rr, cc = row + (i * 6 + k) * unit, colp + r * unit
                mask[max(rr, 0):min(rr + unit, R), max(cc, 0):min(cc + unit, C)] = 1.0
    if soft:
        mask = _blur(mask, 1)
    col[:] = col * (1 - mask[..., None]) + np.array(colour, np.float32)[None, None, :] * mask[..., None]
    height[:] = height + 0.04 * mask
    return mask


def _stitched(col, height, inset, colour, dash=10, gap=6, w=3):
    """A stitched seam all round, inset px from the edge (a rectangular map or band too)."""
    R, C = col.shape[:2]
    for k in range(inset, C - inset, dash + gap):           # along the top and bottom
        for a in (slice(inset, inset + w), slice(R - inset - w, R - inset)):
            b = slice(k, min(k + dash, C - inset))
            col[a, b] = colour
            height[a, b] -= 0.06
    for k in range(inset, R - inset, dash + gap):           # along the sides
        a = slice(k, min(k + dash, R - inset))
        for b in (slice(inset, inset + w), slice(C - inset - w, C - inset)):
            col[a, b] = colour
            height[a, b] -= 0.06


def _face(base, n, rng, lines, ink, band=(0.0, 1.0)):
    """A cover's painted face: the fabric, a stitched border, text near the top and the bottom - all within the rows
    `band` (fractions of the map) when the face is wider than tall (its UVs then span that band only)."""
    m = _fabric(base, n, rng)
    rows = slice(int(band[0] * n), int(band[1] * n))
    col, h = m['colour'][rows], m['height'][rows]          # views: drawn into the map
    nb = col.shape[0]
    _stitched(col, h, n // 40, tuple(min(1.0, c * 1.6 + 0.25) for c in base))
    _stitched(col, h, n // 40 + n // 60, tuple(c * 0.6 for c in base), dash=n, gap=0, w=2)
    for txt, at in lines:
        unit = max(int((n * 0.80) / (len(txt) * 6)), 1)
        unit = min(unit, n // 50)
        w = len(txt) * 6 * unit
        _text(col, h, txt, int(at * nb) - 3 * unit, (n - w) // 2, unit, ink)
    return m


def textures():
    """{material name: maps} for every ground material."""
    import numpy as np
    out = {}
    for k, (kind, base, span, n) in sorted(MATS.items()):
        rng = np.random.default_rng(sum(map(ord, k)) * 7919)
        if kind == 'fabric':
            m = _fabric(base, n, rng)
        elif kind == 'paint':
            m = _paint(base, n, rng)
        elif kind == 'brushed':
            m = _brushed(base, n, rng)
        elif kind == 'rubber':
            m = _rubber(base, n, rng)
        elif kind == 'plastic':
            m = _plastic(base, n, rng)
        elif kind == 'powder':
            m = _powder(base, n, rng)
        elif kind == 'tread':
            m = _tread(base, n, rng)
        elif kind == 'stencil':
            m = _paint(base, n, rng)
            col, h = m['colour'], m['height']
            for txt, v0 in (('MHU-110/E', 0.75), ('MAX 7600 LB', 0.40), ('TP 50  198', 0.05)):
                unit = max(min(int(n * 0.2 * 0.62 / 7), int(n * 0.94 / (len(txt) * 6))), 1)
                _text(col, h, txt, int((v0 + 0.1) * n) - 3 * unit - unit // 2, (n - len(txt) * 6 * unit) // 2, unit,
                      (0.04, 0.04, 0.04))
        elif kind == 'cover':
            m = _face(base, n, rng, [(TEXT, 0.88), (TEXT, 0.12)], (0.86, 0.85, 0.80))
        elif kind == 'exhaust':
            m = _face(base, n, rng, [(TEXT, 0.82), ('ENGINE EXHAUST', 0.18)], (0.80, 0.80, 0.78), band=EXHAUST_BAND)
        elif kind == 'ribbon':
            m = _fabric(base, n, rng)
            col, h = m['colour'], m['height']
            w = int(n * RIBBON_STRIP)
            unit = max(min((w - 10) // 7, (n // 2 - 24) // (len(TEXT) * 6)), 1)
            L = len(TEXT) * 6 * unit
            for strip in range(int(1 / RIBBON_STRIP)):
                c0 = strip * w
                col[:, c0:c0 + 2] *= 0.7                  # hemmed edges
                col[:, c0 + w - 2:c0 + w] *= 0.7
                for k2 in range(2):
                    start = k2 * n // 2 + (n // 2 - L) // 2
                    _text(col, h, TEXT, start, c0 + (w - 7 * unit) // 2, unit, (0.90, 0.89, 0.86), vertical=True)
        elif kind == 'label':
            col = np.full((n, n, 3), base, np.float32) * (1 + 0.03 * _fbm(n, [8], [1.0], rng))[..., None]
            h = np.full((n, n), 0.5, np.float32)
            col[int(n * 0.80):int(n * 0.95)] = (0.70, 0.08, 0.06)
            for txt, at in (('FIRE', 0.62), ('EXTINGUISHER', 0.47), ('HALON 1211', 0.28), ('150 LB', 0.14)):
                unit = max(min(int(n * 0.85 / (len(txt) * 6)), n // 30), 1)
                _text(col, h, txt, int(at * n) - 3 * unit, (n - len(txt) * 6 * unit) // 2, unit, (0.05, 0.05, 0.05))
            m = _maps(col, h, np.full((n, n), 0.3), np.zeros((n, n)))
        out[material(k)] = m
    return out


# ---------------------------------------------------------------------------------------------- configs (make_f22.py)
def eased(way, step=0.05):
    """Keys sampled from waypoints [(p, dx, dy, dz, ang)], each leg eased in and out (hands start and stop)."""
    out = []
    n = int(round(1 / step))
    for k in range(n + 1):
        p = k / n
        for a, b in zip(way, way[1:]):
            if a[0] <= p <= b[0]:
                t = (p - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 1.0
                t = t * t * (3 - 2 * t)
                out.append((p,) + tuple(x + (y - x) * t for x, y in zip(a[1:], b[1:])))
                break
    return out


def _keys_maps(g, name, src, keys, pivot, axis):
    """Graphics chain for keys [(p, dx, dy, dz, ang)]: turned about pivot first, then moved. -> transform name."""
    chain = []
    for i, ax in enumerate(('X', 'Y', 'Z')):
        vals = [k[1 + i] for k in keys]
        if max(vals) - min(vals) > 1e-4:
            m = g('graphics_linear_interpolation', '%s_T%sMap' % (name, ax), Input=src,
                  Map=' %s ' % ' '.join('(%.3f %.4f)' % (k[0], k[1 + i]) for k in keys))
            chain.append(('graphics_translation', '%s_T%s' % (name, ax), dict(Input=m.name + '.Output',
                                                                            Axis=[float(i == j) for j in range(3)])))
    if any(abs(k[4]) > 1e-6 for k in keys):
        m = g('graphics_linear_interpolation', name + '_RMap', Input=src,
              Map=' %s ' % ' '.join('(%.3f %.5f)' % (k[0], k[4]) for k in keys))
        chain.append(('graphics_rotation', name + '_R', dict(Input=m.name + '.Output', Axis=list(axis), Pivot=list(pivot))))
    # outermost first (applied last): the translations after the turn
    for k, (t, n, fields) in enumerate(chain):
        if k + 1 < len(chain):
            fields = dict(fields, InputTransform=chain[k + 1][1] + '.Output')
        g(t, n, **fields)
    return chain[0][1] if chain else None


def configs(obj, dyn, g, D, G):
    """Dynamics (start decision, triggers, progress per item, real external power) and graphics, into the base tmd."""
    vec = lambda v: ('tmvector3d', ' %.4f %.4f %.4f ' % tuple(v))
    eye = ('tmmatrix3d', ' 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0 ')
    o = lambda type_, name, **f: obj(dyn, type_, name, **f)
    out = lambda name, src: o('output', 'GfxOut' + name, Input=src)
    o('fixed_body', 'F22GroundFixed', Mass=1000.0, InertiaLength=vec([1.0, 1.0, 1.0]), R0=vec(FIXED_R0), B0=eye)
    o('radar_altimeter', 'F22GndAlt', Body='F22GroundFixed', R0=vec(FIXED_R0), Calibration=('float64', '0.0'))
    # the start: decided once (START_DECIDE) - on the ground, both engines off, the fixed body on the ground
    o('integral_clamped', 'F22GndClock', Input='1.0', Range=' 0.0 10.0 ', Value=0.0)
    o('logic_greater', 'F22GndAfterStart', Input0='F22GndClock.Output', Input1='%.2f' % START_DECIDE[0])
    o('logic_greater', 'F22GndBeforeDecide', Input0='%.2f' % START_DECIDE[1], Input1='F22GndClock.Output')
    o('logic_greater', 'F22GndEarly', Input0='%.2f' % SNAP_S, Input1='F22GndClock.Output')
    o('logic_greater', 'F22GndLow', Input0='%.1f' % AIR_START_M, Input1='F22GndAlt.Output')
    o('logic_and', 'F22GndColdStart', Inputs=' F22GndAfterStart.Output F22GndBeforeDecide.Output Engine1NotRunning.Output '
      'Engine2NotRunning.Output OnGroundSensor.Output F22GndLow.Output ')
    o('mixlinear', 'F22GndShowRate', Input0='F22GndColdStart.Output', Input1='0.0', Weight0=20.0, Weight1=0.0)
    o('integral_clamped', 'F22GndShowLatch', Input='F22GndShowRate.Output', Range=' 0.0 1.0 ', Value=0.0)
    o('logic_greater', 'F22GndShown', Input0='F22GndShowLatch.Output', Input1='0.5')
    o('logic_invert', 'F22GndHidden', Input='F22GndShown.Output')
    # triggers
    o('logic_and', 'F22GndBrakeOff', Inputs=' F22GndShown.Output ParkingBrakeOff.Output ')
    o('mixlinear', 'F22GndMovedRate', Input0='F22GndBrakeOff.Output', Input1='0.0', Weight0=20.0, Weight1=0.0)
    o('integral_clamped', 'F22GndMovedLatch', Input='F22GndMovedRate.Output', Range=' 0.0 1.0 ', Value=0.0)
    o('logic_greater', 'F22GndMoved', Input0='F22GndMovedLatch.Output', Input1='0.5')
    # the ladder goes LADDER_AFTER_S into the canopy's closing (2026-11-28; it waited for the canopy to shut): the
    # canopy runs CANOPY_RATE of its travel a second from open (1.0)
    o('logic_greater', 'F22GndCanopyClosing', Input0='%.3f' % (1.0 - LADDER_AFTER_S * CANOPY_RATE),
      Input1='CanopySequence.Output')
    o('logic_greater', 'F22GndApuTurning', Input0='APUN1.Output', Input1='0.05')
    o('integral_clamped', 'F22GndApuOnFor', Input='APUAvailable.Output', Range=' 0.0 %.1f ' % (APU_HOSE_S + 1), Value=0.0)
    o('logic_greater', 'F22GndApuOnLong', Input0='F22GndApuOnFor.Output', Input1='%.1f' % APU_HOSE_S)
    trig = {'Ladder': ('F22GndCanopyClosing', LADDER_S), 'Cover': ('F22GndApuTurning', COVER_S), 'Chock': (None, CHOCK_S),
            'Hose': ('F22GndApuOnLong', HOSE_S)}
    for item, (t, dur) in trig.items():
        ins = ' F22GndMoved.Output ' if t is None else ' %s.Output F22GndMoved.Output ' % t
        o('logic_or', 'F22Gnd%sGo' % item, Inputs=ins)
        o('logic_and', 'F22Gnd%sGoShown' % item, Inputs=' F22Gnd%sGo.Output F22GndShown.Output ' % item)
        o('logic_and', 'F22Gnd%sSnap' % item, Inputs=' F22Gnd%sGoShown.Output F22GndEarly.Output ' % item)
        o('mixlinear', 'F22Gnd%sRate' % item, Input0='F22Gnd%sGoShown.Output' % item, Input1='F22Gnd%sSnap.Output' % item,
          Weight0=1.0 / dur, Weight1=50.0)
        o('integral_clamped', 'F22Gnd%sProg' % item, Input='F22Gnd%sRate.Output' % item, Range=' 0.0 1.0 ', Value=0.0)
        o('logic_greater', 'F22Gnd%sOff' % item, Input0='F22Gnd%sProg.Output' % item, Input1='0.001')
        o('logic_invert', 'F22Gnd%sOn' % item, Input='F22Gnd%sOff.Output' % item)
        out('F22Gnd%sProg' % item, 'F22Gnd%sProg.Output' % item)
    o('logic_greater', 'F22GndHoseUnplugged', Input0='F22GndHoseProg.Output', Input1='0.5')
    o('logic_invert', 'F22GndHosePlugged', Input='F22GndHoseUnplugged.Output')
    o('logic_greater', 'F22GndCombatAboard', Input0='F22CombatLoad.Output', Input1='0.5')
    # hide signals (1 = hidden)
    hides = {'All': ' F22GndHidden.Output ',
             'CoverOn': ' F22GndHidden.Output F22GndCoverOff.Output ',     # in the intake (and the start streamers)
             'CoverMoving': ' F22GndHidden.Output F22GndCoverOn.Output ',
             'GearPins': ' F22GndHidden.Output F22GndChockOff.Output ',
             'Hose': ' F22GndHidden.Output F22GndHoseUnplugged.Output ',
             'Coil': ' F22GndHidden.Output F22GndHosePlugged.Output ',
             'TrailerMsl': ' F22GndHidden.Output F22GndCombatAboard.Output '}   # on the trailer with the CLEAN load
    for k, ins in hides.items():
        o('logic_or', 'F22GndHide' + k, Inputs=ins)
        out('F22GndHide' + k, 'F22GndHide%s.Output' % k)
    # real external power: the cart, plugged, with the battery switch on (the donor's chain ran it from the APU only)
    o('logic_and', 'F22GpuPower', Inputs=' F22GndShown.Output F22GndHosePlugged.Output BatterySwitchSetOn.Output ')
    ep = D['ExternalPowerConnected']
    assert ep.type == 'logic_and' and ep.get('Inputs').split() == ['APUAvailable.Output'], ep.get('Inputs')
    ep.type = 'logic_or'
    ep.set('Inputs', ' APUAvailable.Output F22GpuPower.Output ', 'string8')

    # the AIM-9X seeker caps: with the gear pins, and only while the missile is aboard (weapons_f22: HeldHidden)
    import weapons_f22
    aim9 = [m for m in weapons_f22.missiles() if m['kind'] == '9x']
    for m in aim9:
        o('logic_or', 'F22GndHideAim9' + m['side'], Inputs=' F22GndHideGearPins.Output %sHeldHidden.Output ' % m['name'])
        out('F22GndHideAim9' + m['side'], 'F22GndHideAim9%s.Output' % m['side'])
    hides.update({'Aim9' + m['side']: None for m in aim9})

    # graphics
    for name in ['F22GndHide' + k for k in hides] + ['F22Gnd%sProg' % k for k in trig]:
        g('graphics_input', 'Gfx' + name, InputID=('uint32', 'GfxOut%s.Output' % name))
    fixed = {'PositionID': ('uint32', 'F22GroundFixed.R'), 'OrientationID': ('uint32', 'F22GroundFixed.Q')}
    fus = {'PositionID': ('uint32', 'Fuselage.R'), 'OrientationID': ('uint32', 'Fuselage.Q')}

    def draw(part, where, hide, xform=None):
        f = dict(GeometryList=' %s ' % part, InputHide='GfxF22GndHide%s.Output' % hide, **where)
        if xform:
            f['InputTransform'] = xform + '.Output'
        g('rigidbodygraphics', part, **f)

    # The plugs' moving copies are on the fixed body, anchored at the start - but the aircraft then settles on its
    # struts (the nose strut more: nose down), so a copy started above its intake (in-game 2026-11-28: it jumped up out
    # of the duct as the removal began). Measured live at each plug's centre: the height of the fuselage point over the
    # fixed body's (two radar altimeters) and the pitch between them; the copy turned and moved by that at the start,
    # by nothing at the end (on the ramp, the fixed body's frame)
    o('attitude_indicator', 'F22GndAttFixed', Body='F22GroundFixed')
    o('mixlinear', 'F22GndPitchDiff', Input0='PhysicalAttitudeIndicator.PitchAngle', Input1='F22GndAttFixed.PitchAngle',
      Weight0=1.0, Weight1=-1.0)
    o('mixlinear', 'F22GndCoverLeft', Input0='F22GndCoverProg.Output', Input1='1.0', Weight0=-1.0, Weight1=1.0)

    def settled(key, c, inner):
        for tag, body in (('F', 'Fuselage'), ('G', 'F22GroundFixed')):
            o('radar_altimeter', 'F22GndRa%s%s' % (key, tag), Body=body, R0=vec(c), Calibration=('float64', '0.0'))
        o('mixlinear', 'F22GndDz%s' % key, Input0='F22GndRa%sF.Output' % key, Input1='F22GndRa%sG.Output' % key,
          Weight0=1.0, Weight1=-1.0)
        o('product', 'F22GndDzLeft%s' % key, Inputs=' F22GndDz%s.Output F22GndCoverLeft.Output ' % key)
        # (nose down relative to the fixed body = a turn about +y by minus the pitch difference)
        o('product', 'F22GndTurnLeft%s' % key, Inputs=' F22GndPitchDiff.Output F22GndCoverLeft.Output -1.0 ')
        for nm in ('F22GndDzLeft' + key, 'F22GndTurnLeft' + key):
            out(nm, nm + '.Output')
            g('graphics_input', 'Gfx' + nm, InputID=('uint32', 'GfxOut%s.Output' % nm))
        g('graphics_rotation', 'Ground_%sSettleR' % key, Input='GfxF22GndTurnLeft%s.Output' % key, Axis=[0.0, 1.0, 0.0],
          Pivot=list(c), InputTransform=inner + '.Output')
        g('graphics_translation', 'Ground_%sSettleZ' % key, Input='GfxF22GndDzLeft%s.Output' % key, Axis=[0.0, 0.0, 1.0],
          InputTransform='Ground_%sSettleR.Output' % key)
        return 'Ground_%sSettleZ' % key

    pivot, axis, keys = ladder_motion()
    draw('Ground_Ladder', fixed, 'All', _keys_maps(g, 'Ground_LadderMove', 'GfxF22GndLadderProg.Output', keys, pivot, axis))
    for side in ('L', 'R'):
        pivot, axis, keys = cover_motion(side)
        draw('Ground_Cover' + side, fixed, 'CoverMoving',
             settled('Cover' + side, pivot, _keys_maps(g, 'Ground_Cover%sMove' % side, 'GfxF22GndCoverProg.Output', keys,
                                                      pivot, axis)))
        draw('Ground_CoverK' + side, fus, 'CoverOn')
        pivot, axis, keys = exhaust_motion(side)
        draw('Ground_Exhaust' + side, fixed, 'CoverMoving',
             settled('Exhaust' + side, pivot, _keys_maps(g, 'Ground_Exhaust%sMove' % side, 'GfxF22GndCoverProg.Output',
                                                        keys, pivot, axis)))
        draw('Ground_ExhaustK' + side, fus, 'CoverOn')
    for m in aim9:
        held = next(n for n in G if n.type == 'rigidbodygraphics' and n.name == m['held'])
        xf = held.get('InputTransform')         # the trapeze chain the missile rides
        draw('Ground_Aim9Cap' + m['side'], fus, 'Aim9' + m['side'], xf[:-len('.Output')] if xf else None)
    for key in ('N', 'L', 'R'):
        keys = [(0.0, 0, 0, 0, 0.0), (1.0, 0, CHOCK_OUT[key], 0, 0.0)]
        draw('Ground_Chock' + key, fixed, 'All',
             _keys_maps(g, 'Ground_Chock%sMove' % key, 'GfxF22GndChockProg.Output', keys, (0, 0, 0), (1, 0, 0)))
    draw('Ground_RbfStart', fus, 'CoverOn')
    draw('Ground_RbfGear', fus, 'GearPins')
    draw('Ground_Props', fixed, 'All')
    draw('Ground_Cart', fixed, 'All')
    draw('Ground_CartHose', fixed, 'Hose')
    draw('Ground_HoseCoil', fixed, 'Coil')
    draw('Ground_Trailer', fixed, 'All')
    draw('Ground_TrailerLoad', fixed, 'TrailerMsl')
    draw('Ground_TrailerMsl', fixed, 'TrailerMsl')
    return sorted(n.name for n in G if n.type == 'rigidbodygraphics' and n.name.startswith('Ground_'))
