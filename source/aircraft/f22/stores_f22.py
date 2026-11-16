"""F-22 stores built from references (REFERENCES.md): AIM-120C, AIM-9X Block II, 600 gal ferry tank and its pylon.

Geometry in store axes: x forward from the nose tip (x = 0) aft to x = -L, y left, z up; placed() moves it onto the
aircraft. UV layout of a store texture: the body of revolution takes u 0 .. BODY_U (nose .. tail) and v = angle / 2 pi
around (0 left side, 0.25 top, 0.5 right, 0.75 bottom); u > SWATCH_U holds swatches for fins, lugs and dark parts.

Each store has a full map set (Maps): colour, height (Aerofly bump), gloss, metal - painted in metres on the body
(seams, hatches with rivet rings, filler caps, stencils in a 5x7 stencil font, bands), plus soft weathering (mottling,
streaks aft along the flow, darker seams). Arrays are rows bottom-up as Blender / aerofly_tex.save_png.
"""
import math
try:
    import numpy as np
except ImportError:                # make_f22.py (system python) reads only the layout constants
    np = None

BODY_U, SWATCH_U = 0.84, 0.86
SW_FIN, SW_METAL, SW_DARK = (0.93, 0.28), (0.93, 0.69), (0.93, 0.91)      # swatch centres (u, v)


# ---------------------------------------------------------------------------------------------- shapes
def revolve(prof, length, radius, seg, n_axial=2):
    """Body of revolution: prof [(x / length, r / radius)] nose (0) .. tail (1); smooth, phase 0 = left side."""
    xs = sorted({p[0] for p in prof} | set(np.linspace(0, 1, n_axial)))
    px, pr = zip(*prof)
    rings = [(x, float(np.interp(x, px, pr))) for x in xs]
    verts, faces, uvs = [], [], []
    for x, r in rings:
        for k in range(seg + 1):
            a = 2 * math.pi * k / seg
            verts.append((-x * length, r * radius * math.cos(a), r * radius * math.sin(a)))
    for i in range(len(rings) - 1):
        for k in range(seg):
            a, b = i * (seg + 1) + k, (i + 1) * (seg + 1) + k
            faces.append((a, a + 1, b + 1, b))
            u0, u1 = BODY_U * rings[i][0], BODY_U * rings[i + 1][0]
            uvs.append(((u0, k / seg), (u0, (k + 1) / seg), (u1, (k + 1) / seg), (u1, k / seg)))
    return verts, faces, uvs, {'smooth': True}


def plate(root_le, root_te, tip_le, tip_te, r_root, r_tip, thick, angle, uv=SW_FIN, n_span=3):
    """Fin / wing: trapezoid at `angle` about the x axis (0 = up), root on the body at radius r_root, tip at r_tip.
    Diamond-wedge section: rounded leading edge, flat middle, sharp trailing edge."""
    c, s = math.cos(angle), math.sin(angle)
    out, nrm = np.array([0.0, -s, c]), np.array([0.0, c, s])
    # chordwise stations (fraction, half-thickness factor): rounded LE, flat, tapered TE
    st = [(0.0, 0.0), (0.02, 0.55), (0.07, 0.9), (0.18, 1.0), (0.70, 1.0), (0.92, 0.45), (1.0, 0.1)]
    verts = []
    for j in range(n_span + 1):
        t = j / n_span
        le, te, r = root_le + (tip_le - root_le) * t, root_te + (tip_te - root_te) * t, r_root + (r_tip - r_root) * t
        for f, h in st:
            x = le + (te - le) * f
            for side in (1, -1):
                verts.append(tuple(np.array([x, 0.0, 0.0]) + out * r + nrm * side * thick / 2 * h))
    ns = len(st)
    vi = lambda j, i, sd: (j * ns + i) * 2 + sd
    faces = []
    for j in range(n_span):
        for i in range(ns - 1):
            faces.append((vi(j, i, 0), vi(j, i + 1, 0), vi(j + 1, i + 1, 0), vi(j + 1, i, 0)))
            faces.append((vi(j, i, 1), vi(j + 1, i, 1), vi(j + 1, i + 1, 1), vi(j, i + 1, 1)))
        faces.append((vi(j, ns - 1, 0), vi(j, ns - 1, 1), vi(j + 1, ns - 1, 1), vi(j + 1, ns - 1, 0)))   # TE
    top = [vi(n_span, i, 0) for i in range(ns)] + [vi(n_span, i, 1) for i in range(ns)][::-1]
    faces.append(tuple(top[::-1]))
    root = [vi(0, i, 0) for i in range(ns)] + [vi(0, i, 1) for i in range(ns)][::-1]
    faces.append(tuple(root))                         # closed piece (sunk in the body), so its outside is defined
    return verts, faces, [tuple(uv for _ in f) for f in faces], {'smooth': False}


def box(x0, x1, half_w, z0, z1, angle, uv=SW_METAL):
    """Lug / raceway / panel: a box from radius z0 to z1 at `angle` about the x axis."""
    c, s = math.cos(angle), math.sin(angle)
    out, side = np.array([0.0, -s, c]), np.array([0.0, c, s])
    vs = [tuple(np.array([x, 0, 0]) + out * z + side * w) for x in (x0, x1) for z in (z0, z1) for w in (-half_w, half_w)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    f = [q[::-1] for q in f]
    return vs, f, [tuple(uv for _ in q) for q in f], {'smooth': False}


def merge(parts):
    """-> verts, faces, uvs, smooth flag per face."""
    verts, faces, uvs, smooth = [], [], [], []
    for v, f, u, o in parts:
        n = len(verts)
        verts += [tuple(map(float, p)) for p in v]
        faces += [tuple(i + n for i in q) for q in f]
        uvs += list(u)
        smooth += [o['smooth']] * len(f)
    return verts, faces, uvs, smooth


# ---------------------------------------------------------------------------------------------- 5x7 stencil font
_FONT = {
    'A': '01110 10001 10001 11111 10001 10001 10001', 'B': '11110 10001 10001 11110 10001 10001 11110',
    'C': '01110 10001 10000 10000 10000 10001 01110', 'D': '11100 10010 10001 10001 10001 10010 11100',
    'E': '11111 10000 10000 11110 10000 10000 11111', 'F': '11111 10000 10000 11110 10000 10000 10000',
    'G': '01110 10001 10000 10111 10001 10001 01111', 'H': '10001 10001 10001 11111 10001 10001 10001',
    'I': '01110 00100 00100 00100 00100 00100 01110', 'J': '00111 00010 00010 00010 00010 10010 01100',
    'K': '10001 10010 10100 11000 10100 10010 10001', 'L': '10000 10000 10000 10000 10000 10000 11111',
    'M': '10001 11011 10101 10101 10001 10001 10001', 'N': '10001 10001 11001 10101 10011 10001 10001',
    'O': '01110 10001 10001 10001 10001 10001 01110', 'P': '11110 10001 10001 11110 10000 10000 10000',
    'Q': '01110 10001 10001 10001 10101 10010 01101', 'R': '11110 10001 10001 11110 10100 10010 10001',
    'S': '01111 10000 10000 01110 00001 00001 11110', 'T': '11111 00100 00100 00100 00100 00100 00100',
    'U': '10001 10001 10001 10001 10001 10001 01110', 'V': '10001 10001 10001 10001 10001 01010 00100',
    'W': '10001 10001 10001 10101 10101 10101 01010', 'X': '10001 10001 01010 00100 01010 10001 10001',
    'Y': '10001 10001 10001 01010 00100 00100 00100', 'Z': '11111 00001 00010 00100 01000 10000 11111',
    '0': '01110 10001 10011 10101 11001 10001 01110', '1': '00100 01100 00100 00100 00100 00100 01110',
    '2': '01110 10001 00001 00010 00100 01000 11111', '3': '11111 00010 00100 00010 00001 10001 01110',
    '4': '00010 00110 01010 10010 11111 00010 00010', '5': '11111 10000 11110 00001 00001 10001 01110',
    '6': '00110 01000 10000 11110 10001 10001 01110', '7': '11111 00001 00010 00100 01000 01000 01000',
    '8': '01110 10001 10001 01110 10001 10001 01110', '9': '01110 10001 10001 01111 00001 00010 01100',
    '-': '00000 00000 00000 11111 00000 00000 00000', '/': '00000 00001 00010 00100 01000 10000 00000',
    '.': '00000 00000 00000 00000 00000 01100 01100', ' ': '00000 00000 00000 00000 00000 00000 00000',
}


def _noise(h, w, cell, rng):
    """Smooth value noise, cell size in pixels (rows, cols), roughly -1 .. 1."""
    ch, cw = max(int(cell[0]), 1), max(int(cell[1]), 1)
    g = rng.uniform(-1, 1, (h // ch + 3, w // cw + 3))
    yi, xi = np.arange(h) / ch, np.arange(w) / cw
    y0, x0 = np.floor(yi).astype(int), np.floor(xi).astype(int)
    fy, fx = (yi - y0)[:, None], (xi - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a, b = g[y0][:, x0], g[y0][:, x0 + 1]
    c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


# ---------------------------------------------------------------------------------------------- the F-22 skin's wear
# Weathering borrowed from the mod's own skin (F-22A_Default): a clean patch of the wing underside (~3 x 3 m) gives
# the paint tone and the pattern of mottles, streaks and grain; its thin panel lines and small markings are blurred
# away and the contrast clipped. The pattern is laid on the stores at the skin's own scale (SKIN_PXM pixels per metre),
# mirrored and offset per store so it does not visibly repeat.
SKIN = {'detail': None, 'colour': None}
SKIN_PXM = 210.0
SKIN_REGION = (2280, 2140, 2890, 2720)      # x0, y0, x1, y1 in the 6000 px texture, rows top-down


def _boxblur(a, r):
    r = int(r)
    if r < 1:
        return a
    out = a
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(out, pad, mode='reflect'), axis=axis)
        hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis)
        lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
        out = (hi - lo) / (2 * r + 1)
    return out


def set_skin(rgb_topdown, region=SKIN_REGION):
    """rgb_topdown: the skin texture (rows top-down, float 0..1)."""
    x0, y0, x1, y1 = region
    crop = np.asarray(rgb_topdown[y0:y1, x0:x1, :3], np.float32)
    lum = crop.mean(axis=2)
    mid, big = _boxblur(lum, 7), _boxblur(lum, 120)
    ratio = np.clip(mid / np.maximum(big, 1e-3), 0.88, 1.12)
    grain = np.clip(lum - mid, -0.02, 0.02) / max(float(lum.mean()), 1e-3)
    SKIN['detail'] = (ratio + 0.6 * grain).astype(np.float32)
    SKIN['colour'] = tuple(float(c) for c in np.median(crop.reshape(-1, 3), axis=0))


def skin_detail(xm, sm, seed):
    """Detail factor (~1) at metres xm (along, row vector) and sm (around / up, column vector)."""
    d = SKIN['detail']
    h, w = d.shape
    rng = np.random.default_rng(seed)
    ox, oy = rng.uniform(0, 4 * w), rng.uniform(0, 4 * h)
    mirror = lambda t, n: np.abs(((t % (2 * n)) + 2 * n) % (2 * n) - n).astype(int).clip(0, n - 1)
    cols = mirror(np.asarray(xm) * SKIN_PXM + ox, w)
    rows = mirror(np.asarray(sm) * SKIN_PXM + oy, h)
    return d[rows, cols]


# ---------------------------------------------------------------------------------------------- maps
class Maps:
    """Texture set painted in metres on a body of length L, radius R: x from the nose, angle a (0 left side,
    pi/2 top). Row = v, column = u (rows bottom-up as Blender, v = row / size)."""

    def __init__(self, length, radius, base, gloss, size=2048, seed=1):
        self.L, self.R, self.n = length, radius, size
        self.col = np.empty((size, size, 3), np.float32)
        self.col[:] = base
        self.h = np.full((size, size), 0.5, np.float32)
        self.gloss = np.full((size, size), gloss, np.float32)
        self.metal = np.zeros((size, size), np.float32)
        self.rng = np.random.default_rng(seed)
        self.fin_wear = 0.03
        self.px_x = size * BODY_U / length                 # pixels per metre along the body
        self.px_a = size / (2 * math.pi * radius)          # pixels per metre around (at radius R)
        self.body = (slice(0, size), slice(0, int(size * BODY_U) + 2))

    # coordinates
    def u(self, x):
        return x * self.px_x

    def v(self, a):
        return (a % (2 * math.pi)) / (2 * math.pi) * self.n

    def _grid(self, x0, x1, a0, a1):
        """Pixel rows / cols covering x0..x1, angle a0..a1 (unwrapped: rows wrap around, angles stay continuous)."""
        c0, c1 = int(max(self.u(min(x0, x1)) - 1, 0)), int(min(self.u(max(x0, x1)) + 2, self.n * BODY_U + 2))
        r0 = int(math.floor(a0 / (2 * math.pi) * self.n)) - 1
        r1 = int(math.ceil(a1 / (2 * math.pi) * self.n)) + 1
        rr = np.arange(r0, r1)
        cols = np.arange(c0, max(c1, c0 + 1))
        xs = (cols + 0.5) / self.px_x
        As = (rr + 0.5) / self.n * 2 * math.pi
        return rr % self.n, cols, xs[None, :], As[:, None]

    # painting primitives (metres / radians)
    def band(self, x0, x1, colour=None, dh=0.0, gloss=None):
        c = slice(int(self.u(x0)), max(int(self.u(x1)), int(self.u(x0)) + 1))
        if colour is not None:
            self.col[:, c] = colour
        if dh:
            self.h[:, c] += dh
        if gloss is not None:
            self.gloss[:, c] = gloss

    def seam(self, x, depth=0.12, w=0.003, dark=0.75):
        self.band(x - w / 2, x + w / 2, dh=-depth)
        c = slice(int(self.u(x - w)), int(self.u(x + w)) + 1)
        self.col[:, c] *= dark

    def ellipse(self, x, a, rx, ra_m, colour=None, dh=0.0, ring=None, gloss=None, metal=None):
        """Filled ellipse (rx along x, ra_m around, metres) or a ring of width `ring`; anti-aliased edges."""
        span = (ra_m + 0.01) / self.R
        rows, cols, X, A = self._grid(x - rx - 0.01, x + rx + 0.01, a - span, a + span)
        d = np.sqrt(((X - x) / rx) ** 2 + ((A - a) * self.R / ra_m) ** 2)
        k = min(rx, ra_m)
        pix = 1.0 / self.px_x
        if ring is None:
            w = np.clip(0.5 - (d - 1.0) * k / pix, 0, 1)
        else:
            w = np.clip(0.5 - (np.abs(d - 1.0) * k - ring / 2) / pix, 0, 1)
        self._apply(rows, cols, w, colour, dh, gloss, metal)

    def rect(self, x0, x1, a0, a1, colour=None, dh=0.0, outline=None, gloss=None, metal=None):
        rows, cols, X, A = self._grid(x0, x1, a0, a1)
        m = (X >= min(x0, x1)) & (X <= max(x0, x1)) & (A >= a0) & (A <= a1)
        if outline:
            w = outline
            inner = (X >= min(x0, x1) + w) & (X <= max(x0, x1) - w) & (A >= a0 + w / self.R) & (A <= a1 - w / self.R)
            m = m & ~inner
        self._apply(rows, cols, m, colour, dh, gloss, metal)

    def rivets(self, pts, r=0.0035, dh=0.06):
        for x, a in pts:
            self.ellipse(x, a, r, r, dh=dh)
            self.ellipse(x, a, r * 1.3, r * 1.3, ring=r * 0.5, colour=None, dh=-dh * 0.5)

    def text(self, s, x, a, h, colour=(0.08, 0.08, 0.08), side=1):
        """Stencil text, letter height h (m), starting at x (nose side), centred on angle a. side 1: read on the
        left side (+y) of the store, -1: on the right side (letters mirrored so they read from outside)."""
        p = h / 7.0
        cx = x
        for ch in s.upper():
            g = _FONT.get(ch, _FONT[' ']).split()
            for row, bits in enumerate(g):
                for k, b in enumerate(bits):
                    if b == '1':
                        xx = cx + k * p if side > 0 else cx + k * p
                        zz = (3 - row) * p                    # +z up on the left side
                        aa = a + side * zz / self.R
                        self.rect(xx, xx + p * 0.95, aa - p * 0.48 / self.R, aa + p * 0.48 / self.R, colour)
            cx += 6 * p

    def _apply(self, rows, cols, m, colour, dh, gloss, metal):
        """m: mask (bool) or coverage 0..1 - blended."""
        w = m.astype(np.float32)
        if not w.any():
            return
        sub = np.ix_(rows, cols)
        if colour is not None:
            c = self.col[sub]
            self.col[sub] = c * (1 - w[..., None]) + np.array(colour, np.float32) * w[..., None]
        if dh:
            self.h[sub] = self.h[sub] + dh * w
        if gloss is not None:
            self.gloss[sub] = self.gloss[sub] * (1 - w) + gloss * w
        if metal is not None:
            self.metal[sub] = self.metal[sub] * (1 - w) + metal * w

    def weather(self, amount=1.0, grime_bottom=0.05):
        """Paint wear: the F-22 skin's pattern (set_skin) at `amount` of its contrast, the underside a little
        dirtier; darker areas also less glossy. Without the skin: soft value noise."""
        n = self.n
        stop = self.body[1].stop
        v = (np.arange(n) + 0.5) / n
        bottom = np.clip(-np.sin(v * 2 * math.pi), 0, 1)[:, None]          # 1 at the bottom (v 0.75)
        if SKIN['detail'] is not None:
            xm = ((np.arange(stop) + 0.5) / self.px_x)[None, :]
            sm = ((np.arange(n) + 0.5) / self.px_a)[:, None]
            seed = int(self.rng.integers(1 << 30))
            det = skin_detail(xm, sm, seed)
            # the texture wraps around the body at v 0: cross-fade the last tenth into the pattern's start, no seam
            circ = n / self.px_a
            t = np.clip((sm - 0.9 * circ) / (0.1 * circ), 0, 1)
            t = t * t * (3 - 2 * t)
            det = det * (1 - t) + skin_detail(xm, sm - circ, seed) * t
        else:
            det = 1.0 + 0.04 * _noise(n, stop, (n / 6, n / 10), self.rng)
        shade = 1.0 + amount * (det - 1.0) - grime_bottom * bottom
        self.col[self.body] *= shade[..., None]
        self.gloss[self.body] *= np.clip(1.0 + 1.5 * amount * (det - 1.0) - grime_bottom * bottom, 0.5, 1.2)
        self.h[self.body] += 0.08 * amount * (det - 1.0)

    def swatches(self, fin, metal=(0.42, 0.43, 0.45), dark=(0.10, 0.10, 0.11), fin_gloss=None):
        n = self.n
        s0 = int(n * SWATCH_U)
        rng = self.rng
        if SKIN['detail'] is not None:
            det = skin_detail(((np.arange(n - s0) + 0.5) / self.px_x)[None, :], ((np.arange(n) + 0.5) / self.px_x)[:, None],
                              int(rng.integers(1 << 30)))
            fine = (det - 1.0) / 0.04
        else:
            fine = _noise(n, n - s0, (12, 12), rng)
        self.col[:, s0:] = np.array(fin, np.float32) * (1 + self.fin_wear * fine)[..., None]
        if fin_gloss is not None:
            self.gloss[:, s0:] = fin_gloss
        mr = slice(int(n * 0.6), int(n * 0.78))
        self.col[mr, s0:] = metal
        self.gloss[mr, s0:] = 0.6
        self.metal[mr, s0:] = 1.0
        dr = slice(int(n * 0.82), n)
        self.col[dr, s0:] = dark
        self.gloss[dr, s0:] = 0.3

    def result(self):
        return {'colour': np.clip(self.col, 0, 1), 'height': np.clip(self.h, 0, 1),
                'gloss': np.clip(self.gloss, 0, 1), 'metal': np.clip(self.metal, 0, 1)}


# ---------------------------------------------------------------------------------------------- paint
LIGHT_GREY = (0.74, 0.75, 0.77)          # missile bodies, light gull grey
WHITE = (0.86, 0.86, 0.85)
RADOME = (0.90, 0.89, 0.85)
YELLOW = (0.82, 0.64, 0.10)               # live warhead band
BROWN = (0.36, 0.22, 0.12)                # live rocket motor band
TANK_GREY = (0.55, 0.57, 0.60)            # tank (photos: lighter than the skin)
PYLON_GREY = (0.60, 0.62, 0.65)
TOP, BOTTOM, LEFT, RIGHT = math.pi / 2, 3 * math.pi / 2, 0.0, math.pi


def _skin_tone(k, fallback):
    """The skin's paint (set_skin) scaled by k - the tank and pylon wear the airframe grey (photos: a touch lighter)."""
    c = SKIN['colour']
    return tuple(min(k * x, 1.0) for x in c) if c is not None else fallback


# ---------------------------------------------------------------------------------------------- stores
def aim120c():
    """AIM-120C: body from the AIM-120A profile drawing (radome 0.495 m, cylinder to 3.657 m), clipped wings and fins
    (span 0.447 m: the 12.5 in box), X configuration, two lugs on top."""
    L, R = 3.657, 0.0889
    radome = [(0.0, 0.0), (0.0015, 0.10), (0.004, 0.16), (0.010, 0.226), (0.0248, 0.387), (0.0397, 0.533),
              (0.0545, 0.650), (0.0693, 0.752), (0.0841, 0.839), (0.0989, 0.912), (0.1137, 0.956), (0.1285, 0.99),
              (0.1354, 1.0)]
    prof = radome + [(0.99, 1.0), (0.9965, 0.97), (0.9995, 0.90), (1.0, 0.55), (1.0, 0.0)]
    parts = [revolve(prof, L, R, seg=48, n_axial=8)]
    tip = 0.2235
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        parts.append(plate(-1.721, -2.022, -1.955, -2.022, R, tip, 0.009, a))
        parts.append(plate(-3.323, -3.649, -3.479, -3.649, R, tip, 0.007, a))
    for x in (2.368, 3.235):
        parts.append(box(-x + 0.03, -x - 0.03, 0.012, R - 0.003, R + 0.022, 0.0))
    m = Maps(L, R, LIGHT_GREY, 0.55, seed=120)
    m.band(0.0, 0.495, RADOME, gloss=0.7)
    for x in (0.495, 0.532, 0.973, 3.245, 3.48):
        m.seam(x)
    m.band(1.656, 1.713, YELLOW)
    m.band(2.236, 2.290, BROWN)
    m.band(2.946, 3.000, BROWN)
    m.band(3.483, 3.535, (0.32, 0.32, 0.33))
    m.band(3.60, 3.657, (0.52, 0.52, 0.53), gloss=0.3)
    m.rect(1.72, 2.12, TOP - 0.25, TOP + 0.25, (0.28, 0.28, 0.30), dh=0.04)       # umbilical cover / connector
    for side, a in ((1, LEFT), (-1, RIGHT)):
        m.text('AIM-120C-7', 0.62, a + side * 0.12, 0.022, side=side)
        m.text('GUIDED MISSILE', 0.62, a - side * 0.10, 0.014, side=side)
        m.text('SERNO 8817342', 0.62, a - side * 0.30, 0.012, side=side)
        m.text('WARHEAD', 1.45, a, 0.016, side=side)
        m.text('ROCKET MOTOR', 2.36, a, 0.016, side=side)
        m.rivets([(xx, a + d) for xx in (0.51, 0.955, 3.26) for d in np.linspace(-1.2, 1.2, 9)])
    m.fin_wear = 0.015
    m.weather(amount=0.35, grime_bottom=0.02)
    m.swatches(LIGHT_GREY, fin_gloss=0.5)
    return merge(parts), m.result(), L


def aim9x():
    """AIM-9X Block II from the side render: seeker dome, forward fixed canards, tail fins, three lugs, raceway."""
    L, R = 3.02, 0.0635
    prof = [(0.0, 0.0), (0.002, 0.25), (0.0056, 0.45), (0.0195, 0.61), (0.033, 0.77), (0.048, 0.93), (0.055, 0.97),
            (0.06, 1.0), (0.995, 1.0), (0.999, 0.92), (1.0, 0.6), (1.0, 0.0)]
    parts = [revolve(prof, L, R, seg=40, n_axial=8)]
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        parts.append(plate(-0.30, -0.50, -0.46, -0.50, R, R + 0.075, 0.006, a))
        parts.append(plate(-2.72, -3.02, -2.88, -2.98, R, 0.175, 0.007, a))
    for x in (1.07, 1.86, 2.45):
        parts.append(box(-x + 0.025, -x - 0.025, 0.010, R - 0.003, R + 0.022, 0.0))
    parts.append(box(-0.53, -2.70, 0.014, R - 0.004, R + 0.012, math.pi, uv=SW_FIN))
    m = Maps(L, R, WHITE, 0.55, seed=9)
    m.band(0.0, 0.035, (0.20, 0.21, 0.23), gloss=0.9)                  # seeker dome
    m.band(0.035, 0.56, (0.60, 0.61, 0.62), gloss=0.45)                # control section
    m.band(0.56, 1.0, (0.47, 0.47, 0.48), gloss=0.35)                  # guidance / target detector
    m.band(0.70, 0.73, YELLOW)
    m.band(1.33, 1.37, BROWN)
    for x in (0.035, 0.56, 1.0, 2.70):
        m.seam(x, w=0.0025)
    for side, a in ((1, LEFT), (-1, RIGHT)):
        m.text('AIM-9X-2', 1.12, a + side * 0.18, 0.026, side=side)
        m.text('GUIDED MISSILE', 1.12, a - side * 0.25, 0.012, side=side)
        m.text('ROCKET MOTOR', 1.45, a - side * 0.65, 0.012, side=side)
        m.rivets([(xx, a + d) for xx in (0.55, 1.01, 2.69) for d in np.linspace(-1.2, 1.2, 7)], r=0.003)
    m.fin_wear = 0.015
    m.weather(amount=0.35, grime_bottom=0.02)
    m.swatches((0.80, 0.81, 0.82), fin_gloss=0.5)
    return merge(parts), m.result(), L


def tank600():
    """600 gal tank from the Akela Freedom three-view and photos: 6.7 x 0.85 m, ogive nose 0.40 L with a pointed
    cap, cylinder 0.40 .. 0.66 L, convex aft taper to 0.53 D at 0.94 L, short end cylinder, flat base. Top: two lugs
    on a raised panel, three red filler caps, the aft sway hook; sides: five oval access hatches with rivet rings;
    underneath: the two black cradle stripes with their stencil."""
    L, R = 6.70, 0.425
    ln = 0.40
    rho = (1.0 + (ln * L / R) ** 2) / 2.0
    nose = []
    for t in np.linspace(0.0, 1.0, 22):
        x = t * ln * L / R
        nose.append((t * ln, max(math.sqrt(max(rho ** 2 - (ln * L / R - x) ** 2, 0.0)) + 1.0 - rho, 0.0)))
    nose[0] = (0.0, 0.0)
    nose.insert(1, (0.003, 0.03))
    aft = [(0.66 + 0.28 * t, 1.0 - 0.47 * t ** 1.8) for t in np.linspace(0, 1, 13)]
    prof = nose + aft[1:] + [(0.97, 0.525), (0.998, 0.515), (1.0, 0.47), (1.0, 0.0)]
    parts = [revolve(prof, L, R, seg=72, n_axial=14)]
    parts.append(box(-0.44 * L, -0.62 * L, 0.11, R - 0.01, R + 0.008, 0.0, uv=SW_FIN))         # raised panel
    for f in (0.467, 0.594):
        parts.append(box(-f * L + 0.025, -f * L - 0.025, 0.012, R + 0.005, R + 0.05, 0.0))   # lugs
    parts.append(box(-0.955 * L, -0.99 * L, 0.03, 0.52 * R, 0.52 * R + 0.10, 0.0))         # sway hook
    m = Maps(L, R, _skin_tone(1.05, TANK_GREY), 0.32, seed=600)
    for f in (0.0845, 0.40, 0.66, 0.94):
        m.seam(f * L, depth=0.18, w=0.006)
    m.band(0.995 * L, L, (0.40, 0.41, 0.43))
    # access hatches (sides): oval, groove outline, rivet ring
    for side, a in ((1, LEFT), (-1, RIGHT)):
        for f in (0.364, 0.43, 0.53, 0.629, 0.716):
            x = f * L
            m.ellipse(x, a, 0.075, 0.12, ring=0.006, dh=-0.12, colour=(0.45, 0.46, 0.48))
            m.rivets([(x + 0.098 * math.cos(t), a + 0.145 * math.sin(t) / R) for t in np.linspace(0, 2 * math.pi, 16,
                                                                                                 endpoint=False)])
        m.text('FUEL TANK 600 GAL', 0.47 * L, a + side * 0.55, 0.05, side=side)
        m.text('JP-8', 0.47 * L, a + side * 0.38, 0.05, side=side)
        m.text('NO STEP', 0.20 * L, a + side * 0.75, 0.035, side=side)
    # top: filler caps (red, white ring), raised-panel outline, rivet rows along the panel
    for f in (0.35, 0.632, 0.714):
        m.ellipse(f * L, TOP, 0.065, 0.065, colour=(0.68, 0.07, 0.05), dh=0.08, gloss=0.6)
        m.ellipse(f * L, TOP, 0.045, 0.045, ring=0.006, colour=(0.85, 0.85, 0.82))
        m.ellipse(f * L, TOP, 0.012, 0.012, colour=(0.2, 0.2, 0.2))
    m.rect(0.44 * L, 0.62 * L, TOP - 0.11 / R, TOP + 0.11 / R, outline=0.006, dh=-0.1)
    # bottom: cradle stripes and their stencil
    for f in (0.456, 0.60):
        m.rect(f * L - 0.025, f * L + 0.025, BOTTOM - 0.55, BOTTOM + 0.55, (0.04, 0.04, 0.04))
    m.text('CRADLE SUPPORT POSITION', 0.47 * L, BOTTOM - 0.62, 0.03, side=1)
    m.text('EMPTY TANK ONLY', 0.50 * L, BOTTOM - 0.72, 0.03, side=1)
    # rivet lines along the seams
    for f in (0.40, 0.66):
        m.rivets([(f * L + 0.02, a) for a in np.linspace(0, 2 * math.pi, 60, endpoint=False)], r=0.003)
    m.fin_wear = 0.04
    m.weather(amount=1.0, grime_bottom=0.05)
    m.swatches(_skin_tone(1.05, TANK_GREY))
    return merge(parts), m.result(), L


STORES = {'aim120': aim120c, 'aim9x': aim9x, 'tank': tank600}
MASS = {'aim120': 157.0, 'aim9x': 85.0}

# wing underside along the pylon line (y 3.17, sampled from the model): x -> z
WING_UNDERSIDE = [(1.84, 0.170), (1.60, 0.162), (1.24, 0.159), (1.00, 0.154), (0.64, 0.150), (0.28, 0.152),
                  (-0.08, 0.157), (-0.44, 0.164), (-0.80, 0.172), (-1.16, 0.181), (-1.52, 0.193), (-1.88, 0.207)]
# placement, from the bottom-view photo of an F-22 with both tanks, by the aircraft's own landmarks (not by scale): the
# wing leading edge crosses the tank at 0.35 L on one side and 0.56 L on the other (the oblique view shifts them in
# opposite directions) - 0.46 L on average; the pylon starts at the leading edge (0.48 .. 0.50 L) and runs to ~0.97 L.
# The model's leading edge over the tank is at x 1.9 -> tank nose at 1.9 + 0.46 x 6.7 = 5.0 (AK 06-4108 photo: ~5.2)
TANK_NOSE_X = 5.00
TANK_TOP_Z = -0.14            # pylon height ~0.2 m (ramp photo) .. 0.35 m (AK photo): ~0.28 m under the wing
TANK_LUGS = (0.467, 0.594)    # lug positions, fraction of the tank length


def pylon(y, tank_top_z, x_front=1.80, x_top_front=1.60, x_rear=-1.37, half_w=0.07):
    """Wing pylon of the ferry tank (photo AK 06-4108, Steel Oxide model): a low blade (~0.35 m) from the wing
    underside to a straight bottom lying on the tank; a short raked nose over the tank's front seam, under the wing;
    two sway-brace pads over the tank lugs; the rear end square with the wing hinge fitting. Aircraft axes at
    lateral y; planar side UVs (u along x, v up) into its own texture. Returns (geometry, maps)."""
    wx, wz = zip(*sorted(WING_UNDERSIDE))
    top = lambda x: float(np.interp(x, wx, wz)) + 0.01
    zb = tank_top_z + 0.003
    length, height = x_front - x_rear, top(x_rear) - zb
    xs = [x_front, x_front - 0.015, (x_front + x_top_front) / 2] + list(np.linspace(x_top_front, x_rear, 18))
    uvp = lambda x, z: (BODY_U * (x_front - x) / length, 0.05 + 0.9 * (z - zb) / height)
    verts, uvv = [], []
    for x in xs:
        if x > x_top_front + 1e-6:
            t = (x - x_top_front) / (x_front - x_top_front)
            zt = top(x_top_front) + (zb + 0.02 - top(x_top_front)) * t
            w = half_w * (1.0 - 0.75 * t)
        else:
            zt, w = top(x), half_w
        for py, pz in ((w, zt), (w, zb + 0.03), (0.6 * w, zb), (-0.6 * w, zb), (-w, zb + 0.03), (-w, zt)):
            verts.append((x, y + py, pz))
            uvv.append(uvp(x, pz))
    n = 6
    faces = []
    for i in range(len(xs) - 1):
        for k in range(n - 1):
            a, b = i * n + k, (i + 1) * n + k
            faces.append((a, b, b + 1, a + 1))
        a, b = i * n + n - 1, (i + 1) * n + n - 1
        faces.append((a, b, (i + 1) * n, i * n))
    faces.append(tuple(range(n))[::-1])
    last = (len(xs) - 1) * n
    faces.append(tuple(range(last, last + n)))
    body = (verts, faces, [tuple(uvv[i] for i in f) for f in faces], {'smooth': False})
    parts = [body]
    for xb in [TANK_NOSE_X - f * 6.70 for f in TANK_LUGS]:             # sway braces over the tank lugs
        v, f, u, o = box(xb + 0.04, xb - 0.04, 0.13, 0.0, 0.025, 0.0)
        parts.append(([(px, py + y, pz + zb - 0.02) for px, py, pz in v], f, u, o))
    v, f, u, o = box(x_rear + 0.12, x_rear + 0.02, 0.03, 0.0, 0.08, 0.0)        # wing hinge fitting
    parts.append(([(px, py + y, pz + top(x_rear) - 0.06) for px, py, pz in v], f, u, o))
    # texture: side view of the blade (u along x from the nose, v up), panel lines, fasteners, stencil
    m = Maps(length, 0.5, _skin_tone(1.0, PYLON_GREY), 0.35, size=1024, seed=7)
    pu = lambda x: BODY_U * (x_front - x) / length * m.n
    pv = lambda z: (0.05 + 0.9 * (z - zb) / height) * m.n
    m.col[:, :] = _skin_tone(1.0, PYLON_GREY)
    for xp in (1.35, 0.40, -0.55):                                       # panel joints
        c = int(pu(xp))
        m.h[:, c - 1:c + 2] -= 0.12
        m.col[:, c - 1:c + 2] *= 0.8
    r = int(pv(zb + 0.07))
    m.h[r - 1:r + 2, :int(m.n * BODY_U)] -= 0.1
    m.col[r - 1:r + 2, :int(m.n * BODY_U)] *= 0.85
    for xp in np.arange(1.55, x_rear + 0.1, -0.11):                     # fastener rows
        for zp in (zb + 0.10, top(xp) - 0.04):
            cc, rr = int(pu(xp)), int(pv(zp))
            if 0 <= cc < m.n - 2 and 2 <= rr < m.n - 2:
                m.h[rr - 1:rr + 2, cc - 1:cc + 2] += 0.07
                m.col[rr - 1:rr + 2, cc - 1:cc + 2] *= 0.88
    c0, c1, r0, r1 = int(pu(0.30)), int(pu(-0.20)), int(pv(zb + 0.08)), int(pv(zb + 0.18))  # access panel
    m.h[r0:r1, c0:c0 + 2] -= 0.1
    m.h[r0:r1, c1 - 2:c1] -= 0.1
    m.h[r0:r0 + 2, c0:c1] -= 0.1
    m.h[r1 - 2:r1, c0:c1] -= 0.1
    m.body = (slice(0, m.n), slice(0, int(m.n * BODY_U) + 2))
    m.fin_wear = 0.04
    m.weather(amount=1.0, grime_bottom=0.0)
    m.swatches(_skin_tone(1.0, PYLON_GREY))
    return merge(parts), m.result()


def placed(kind, nose, axis_dir=(1.0, 0.0, 0.0), roll=0.0):
    """Store geometry in aircraft axes: nose tip at `nose`, body axis along axis_dir (forward), rolled by `roll`.
    -> verts, faces, uvs, smooth, maps, length"""
    (verts, faces, uvs, smooth), maps, L = STORES[kind]()
    v = np.array(verts)
    c, s = math.cos(roll), math.sin(roll)
    v = v @ np.array([[1, 0, 0], [0, c, s], [0, -s, c]])
    d = np.array(axis_dir, float)
    d /= np.linalg.norm(d)
    pitch = math.atan2(d[2], math.hypot(d[0], d[1]))
    yaw = math.atan2(d[1], d[0])
    cp, sp, cy, sy = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    Ry = np.array([[cp, 0, -sp], [0, 1, 0], [sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    v = v @ Ry.T @ Rz.T + np.array(nose)
    return [tuple(p) for p in v], faces, uvs, smooth, maps, L


# ---------------------------------------------------------------------------------------------- on the aircraft
# DCS model connectors (F-22A.EDM, Aerofly axes) of the stations: 1 / 11 side bays (AIM-9X on the LAU-141 trapeze),
# 3-5 / 7-9 main bay (AIM-120C on LAU-142), 2 / 10 the wing pylons (ferry tanks)
CONN = {'Pylon1': (2.548, 1.344, -0.152), 'Pylon11': (2.548, -1.336, -0.148), 'Pylon2': (-0.136, 3.173, -0.14),
        'Pylon10': (-0.15, -3.177, -0.133), 'Pylon3': (2.278, 0.699, -0.441), 'Pylon4': (2.278, 0.473, -0.441),
        'Pylon5': (2.279, 0.237, -0.441), 'Pylon7': (2.279, -0.23, -0.441), 'Pylon8': (2.279, -0.471, -0.441),
        'Pylon9': (2.28, -0.7, -0.442)}
# the six AMRAAMs in the main bay (body axis centre x, shift outboard, axis z), fitted to the mod's bay by clash tests
# against the airframe with the doors shut (offline, Blender): nothing through the doors, no two missiles touching.
# Staggered as on the photos of the open bay - the middle missile of each three 0.225 m ahead (the bay is 3.99 m for a
# 3.66 m missile); the axis 0.09 m under the hardpoints, as the mod's own attach points (0.10 / 0.11 down). Left over:
# the lugs 10 mm into the launchers (as held), the middle missiles' nose top 45 mm into the sloping front roof, the
# outer missiles' upper wing corner 86 mm into the structure by the bay wall (the mod's bay is tight for six)
MAIN_BAY = {'Pylon3': (2.525, 0.09, -0.535), 'Pylon4': (2.75, 0.02, -0.53), 'Pylon5': (2.525, 0.0, -0.535),
            'Pylon7': (2.525, 0.0, -0.535), 'Pylon8': (2.75, 0.02, -0.53), 'Pylon9': (2.525, 0.09, -0.535)}
# side-bay connector frames on the stowed rail (EDM, Aerofly axes): forward X and the DCS 'up' Y, tilted ~50 deg
# inboard - the AIM-9X hangs along -Y and is rolled with it, at the connector (the mod's attach point {-0.02, -0.043}
# in that frame put the tail fins 66 mm into the rail's aft end): 85 mm down Y, clear of the rail (clash tests)
AIM9_FRAME = {'Pylon1': ((0.991, -0.002, -0.003), (0.0, -0.759, 0.638)),
              'Pylon11': ((0.991, 0.001, -0.001), (0.0, 0.758, 0.639))}
AIM9_DROP = 0.085
# side-bay launch rails (EDM nodes, arguments): the AIM-9X rides the rail
AIM9_RAIL = {'Pylon1': ('63,62', '601'), 'Pylon11': ('36,35', '602')}
TANK_MASS = 236.0 + 1814.0          # empty tank and pylon (est.) + 600 US gal of JP-8
TANK_FUEL = 1814.0


def tank_hull(y):
    """Convex low-poly hull of a ferry tank (collision)."""
    L, R = 6.70, 0.425
    prof = [(0.0, 0.05), (0.1, 0.45), (0.25, 0.85), (0.40, 1.0), (0.66, 1.0), (0.94, 0.53), (1.0, 0.5)]
    v, f, u, o = revolve(prof + [(1.0, 0.0)], L, R, seg=12)
    return [(TANK_NOSE_X + p[0], y + p[1], TANK_TOP_Z - R + p[2]) for p in v], f


def aircraft_stores():
    """Every store object on the aircraft: dicts name, part, material, verts, faces, uvs, smooth, maps, nodes, args
    (part 'A_<nodes>__S' rides that animation chain; the tanks' part carries the tank and its pylon)."""
    out = []

    def add(name, part, mat, geo, maps, nodes='', args=''):
        v, f, u, sm = geo
        out.append(dict(name=name, part=part, material=mat, verts=v, faces=f, uvs=u, smooth=sm, maps=maps,
                        nodes=nodes, args=args))

    for st in ('Pylon3', 'Pylon4', 'Pylon5', 'Pylon7', 'Pylon8', 'Pylon9'):
        y0 = CONN[st][1]
        cx, shift, za = MAIN_BAY[st]
        v, f, u, sm, mp, L = placed('aim120', (cx + 3.657 / 2, y0 + shift * (1 if y0 > 0 else -1), za))
        add('StoreAim120' + st, 'Stores_AIM120', 'store_aim120', (v, f, u, sm), mp)
    for st, side in (('Pylon1', 'L'), ('Pylon11', 'R')):
        nodes, args = AIM9_RAIL[st]
        X, Y = (np.array(a) / np.linalg.norm(a) for a in AIM9_FRAME[st])
        c = np.array(CONN[st]) - AIM9_DROP * Y
        v, f, u, sm, mp, L = placed('aim9x', tuple(c + X * 3.02 / 2), axis_dir=tuple(X), roll=math.atan2(-Y[1], Y[2]))
        add('StoreAim9' + side, 'A_%s__S' % nodes.replace(',', '_'), 'store_aim9x', (v, f, u, sm), mp, nodes, args)
    for st, side in (('Pylon2', 'L'), ('Pylon10', 'R')):
        y = CONN[st][1]
        v, f, u, sm, mp, L = placed('tank', (TANK_NOSE_X, y, TANK_TOP_Z - 0.425))
        add('StoreTank' + side, 'Stores_Tank' + side, 'store_tank', (v, f, u, sm), mp)
        geo, pm = pylon(y, TANK_TOP_Z)
        add('StorePylon' + side, 'Stores_Tank' + side, 'store_pylon', geo, pm)
    return out
