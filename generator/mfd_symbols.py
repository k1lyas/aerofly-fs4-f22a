"""Picture symbols of our MFD pages (avionics block G, 2026-11-22, after the AOA X-Plane F-22's stores page and round
engine gauges): the F-22 seen from above with its three weapon bays, their missiles and the ferry tanks (BAY page),
and a round N2 gauge (ENG page).

The game draws a picture on a display with texture_animation_rectangle: a rectangle of a texture, picked from a list
of source positions by a value (the SDK sample: display_source_light, an RGB sheet - the sprites are opaque and carry
their own background; source positions from the bottom left). Ours lie in the free corners of the display2 atlas's
colour map (the lower MFD, the UFDs and the ICP take only part of its 2048 x 2048), painted on the DDI page's own
background green (GreenBackgroundColor 0.035 0.082 0.039, a constant), so that an opaque sprite does not show as a box.

Every variable element (a bay with its doors and load, a tank) is a sprite of its own; its variants are cut from the
whole picture drawn with that element in that state, so an element may cross the outline. Elements must not overlap
each other.

The layout is plain Python (make_f22 and the player's installer read it, without numpy); the drawing needs numpy - the
exporter in Blender (ac_f22.DISPLAY_SYMBOLS) and the offline preview."""
import math

ATLAS = 2048
# the DDI page background, as make_f22 sets GreenBackgroundColor: a colour the compressed texture keeps exactly (5-6-5
# bits: 1/31, 5/63, 1/31 - in-game 2026-11-22 the F/A-18's 0.035 0.082 0.039 came out of the texture a step off and
# the sprites showed as boxes of another shade)
BG = (1 / 31.0, 5 / 63.0, 1 / 31.0)
GREEN = (0.30, 1.00, 0.30)          # our pages' green (mfd_f22.GREEN)
DIM = (0.10, 0.34, 0.12)
SS = 3                              # supersampling


class Canvas:
    """RGB picture, row 0 at the bottom (the atlas's and the game's source positions)."""

    def __init__(self, w, h):
        global np
        import numpy as np
        self.w, self.h = w, h
        self.img = np.empty((h * SS, w * SS, 3), np.float32)
        self.img[:] = BG
        self.ys, self.xs = np.mgrid[0:h * SS, 0:w * SS].astype(np.float32)
        self.xs = (self.xs + 0.5) / SS
        self.ys = (self.ys + 0.5) / SS

    def paint(self, mask, colour):
        m = mask.astype(np.float32)[..., None]
        self.img[:] = self.img * (1 - m) + np.array(colour, np.float32) * m

    def _seg_dist(self, a, b):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy or 1e-9
        t = np.clip(((self.xs - ax) * dx + (self.ys - ay) * dy) / l2, 0.0, 1.0)
        return np.hypot(self.xs - (ax + t * dx), self.ys - (ay + t * dy)), t, math.sqrt(l2)

    def line(self, pts, width, colour, closed=False, dash=None):
        """Polyline; dash = (on, off) in pixels along each segment."""
        pts = list(pts) + ([pts[0]] if closed else [])
        mask = np.zeros(self.xs.shape, bool)
        for a, b in zip(pts[:-1], pts[1:]):
            d, t, length = self._seg_dist(a, b)
            m = d <= width / 2.0
            if dash:
                m &= ((t * length) % (dash[0] + dash[1])) < dash[0]
            mask |= m
        self.paint(mask, colour)

    def polygon(self, pts, colour):
        """Filled polygon (even-odd)."""
        inside = np.zeros(self.xs.shape, bool)
        n = len(pts)
        for i in range(n):
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
            if y1 == y2:
                continue
            cond = (self.ys >= min(y1, y2)) & (self.ys < max(y1, y2))
            xc = x1 + (self.ys - y1) * (x2 - x1) / (y2 - y1)
            inside ^= cond & (self.xs < xc)
        self.paint(inside, colour)

    def capsule(self, a, b, width, colour, filled=True, edge=2.0):
        d, _, _ = self._seg_dist(a, b)
        self.paint((d <= width / 2.0) if filled else (np.abs(d - width / 2.0) <= edge / 2.0), colour)

    def arc(self, c, r_in, r_out, a_from, a_to, colour):
        """Ring sector between the angles (degrees, maths sense: 0 east, counter-clockwise), a_from > a_to clockwise."""
        dx, dy = self.xs - c[0], self.ys - c[1]
        r = np.hypot(dx, dy)
        ang = np.degrees(np.arctan2(dy, dx))
        lo, hi = min(a_from, a_to), max(a_from, a_to)
        rel = (ang - lo) % 360.0
        self.paint((r >= r_in) & (r <= r_out) & (rel <= hi - lo), colour)

    def result(self):
        return self.img.reshape(self.h, SS, self.w, SS, 3).mean(axis=(1, 3))


# ------------------------------------------------------------------------------------------------ the aircraft
# From above, nose up: the outline, canopy and fins come from our own model (mfd_silhouette.py renders its masks; the
# first outline drawn by eye did not look like the F-22 - user 2026-11-22); bays, missiles and tanks are placed from
# the model's own store positions. FRAME: the picture's extent in model metres (x forward, y left), 25 px a metre.
SIL_W, SIL_H = 400, 480
FRAME = (-7.75, 11.45, -8.0, 8.0)
PX_M = SIL_H / (FRAME[1] - FRAME[0])
MASKS = {}                               # 'airframe' / 'canopy' / 'fins': bool arrays (SIL_H x SIL_W) x SS, rows from the bottom


def set_masks(**masks):
    """The model's top-view masks (mfd_silhouette.py's PNGs, read by the caller: Blender or PIL), rows from the bottom."""
    MASKS.update(masks)


def _px(x, y):
    """Model metres (x forward, y left) -> sprite pixels (from the bottom left)."""
    return (SIL_W / 2.0 - y * PX_M, (x - FRAME[0]) * PX_M)


# measured on the exported model (2026-11-22): AIM-120C x 0.70 .. 4.35 (the middle pair 0.92 .. 4.58), y +-0.24 /
# 0.49 / 0.79; AIM-9X x 1.04 .. 4.06, y +-1.41; the ferry tanks x -1.70 .. 5.00 on the pylon line y +-3.17, 0.85 wide
BAY_RECT = {'Center': (0.50, -0.98, 4.80, 0.98), 'Left': (0.85, 1.16, 4.25, 1.66), 'Right': (0.85, -1.66, 4.25, -1.16)}
AIM120 = [(y, 0.92 if abs(y) == 0.49 else 0.70) for y in (0.79, 0.49, 0.24, -0.24, -0.49, -0.79)]
TANK_X, TANK_Y, TANK_W = (-1.70, 5.00), 3.17, 0.85


def _erode(m, r):
    import numpy as np
    out = m.copy()
    for _ in range(r):
        sh = out.copy()
        sh[1:] &= out[:-1]
        sh[:-1] &= out[1:]
        sh[:, 1:] &= out[:, :-1]
        sh[:, :-1] &= out[:, 1:]
        out = sh
    return out


def _edge(m, width_px):
    return m & ~_erode(m, max(1, int(round(width_px * SS))))


def draw_base(cv):
    if 'airframe' not in MASKS:
        raise RuntimeError('mfd_symbols: the model masks are not loaded (mfd_silhouette.py)')
    cv.paint(_edge(MASKS['airframe'], 2.5), GREEN)
    if 'fins' in MASKS:
        cv.paint(_edge(MASKS['fins'], 1.5), GREEN)
    if 'canopy' in MASKS:
        cv.paint(_edge(MASKS['canopy'], 1.5), GREEN)


def _box(rect):
    x0, y0, x1, y1 = rect
    a, b = _px(x0, y0), _px(x1, y1)
    lo, hi = (min(a[0], b[0]), min(a[1], b[1])), (max(a[0], b[0]), max(a[1], b[1]))
    return lo, hi


def draw_bay(cv, bay, state, load):
    (ax, ay), (bx, by) = _box(BAY_RECT[bay])
    box = [(ax, ay), (bx, ay), (bx, by), (ax, by)]
    if state == 1:
        cv.line(box, 2.0, GREEN, closed=True, dash=(6, 5))
    else:
        cv.line(box, 3.5 if state == 2 else 2.0, GREEN, closed=True)
    if state == 2 and bay == 'Center':   # open: a second frame inside (the side bays sit right beside it - no room
        cv.line([(ax + 5, ay + 5), (bx - 5, ay + 5), (bx - 5, by - 5), (ax + 5, by - 5)], 1.5, GREEN, closed=True)   # for doors)
    elif state == 2:                     # the side bay's door, folded out
        out = 0.55 * PX_M
        for x_ in ((ax,) if bay == 'Left' else (bx,)):
            s = -1 if x_ == ax else 1
            cv.line([(x_, ay + 6), (x_ + s * out, ay + 6 + out * 0.5)], 2.5, GREEN)
            cv.line([(x_, by - 6), (x_ + s * out, by - 6 - out * 0.5)], 2.5, GREEN)
    if load:
        if bay == 'Center':              # 6 AIM-120C where the model carries them
            for y, x in AIM120:
                cv.capsule(_px(x + 0.1, y), _px(x + 3.55, y), 4.0, GREEN)
        else:                            # one AIM-9X
            y = 1.41 if bay == 'Left' else -1.41
            cv.capsule(_px(1.10, y), _px(4.00, y), 4.0, GREEN)


def draw_tank(cv, side, on):
    if not on:
        return
    y = TANK_Y if side == 'Left' else -TANK_Y
    cv.capsule(_px(TANK_X[0] + TANK_W / 2, y), _px(TANK_X[1] - TANK_W / 2, y), TANK_W * PX_M, GREEN, filled=False, edge=2.0)


def _bbox(bay=None, side=None):
    """An element's rectangle in the silhouette's pixels: its drawing in every variant, with a margin."""
    if bay:
        (ax, ay), (bx, by) = _box(BAY_RECT[bay])
        out = 0.55 * PX_M + 4
        # (elements must not overlap: the centre bay and the side bays are 4 px apart - 2 px margins between them)
        l = ax - {'Center': 2, 'Left': out, 'Right': 2}[bay]
        r = bx + {'Center': 2, 'Left': 2, 'Right': out}[bay]
        return (int(math.floor(l)), int(ay - 4), int(math.ceil(r) - math.floor(l)), int(by - ay + 8) + 1)
    y = TANK_Y if side == 'Left' else -TANK_Y
    hw = TANK_W * PX_M / 2 + 3
    (cx, ya), (_, yb) = _px(TANK_X[0], y), _px(TANK_X[1], y)
    return (int(cx - hw), int(ya - 3), int(2 * hw) + 1, int(yb - ya + 6) + 1)


def silhouette(states):
    """The whole picture: states {bay: (state, load), 'TankLeft': on, 'TankRight': on}."""
    cv = Canvas(SIL_W, SIL_H)
    draw_base(cv)
    for bay in BAY_RECT:
        draw_bay(cv, bay, *states.get(bay, (0, 0)))
    for side in ('Left', 'Right'):
        draw_tank(cv, side, states.get('Tank' + side, 0))
    return cv.result()


# ------------------------------------------------------------------------------------------------ N2 gauge
DIAL = 140
N2_STEPS = [0, 10, 20, 30, 40, 50, 55, 60, 64, 68, 72, 76, 80, 84, 87, 90, 92, 94, 96, 98, 99, 100]
N2_FULL = 100.0                          # 0 .. 100 % over 270 deg, from 7:30 clockwise (the arc full at 100 %: user, a
                                         # 100 .. 110 % end nothing could fill was dead space)


def dial(value):
    cv = Canvas(DIAL, DIAL)
    c = (DIAL / 2.0, DIAL / 2.0)
    start = 225.0
    cv.arc(c, 57, 63, start, start - 270.0, DIM)        # (the figure inside: '100' at 30 is 81 wide)
    if value > 0:
        cv.arc(c, 57, 63, start, start - 270.0 * value / N2_FULL, GREEN)
    for v in range(0, 101, 10):
        a = math.radians(start - 270.0 * v / N2_FULL)
        r0 = 64 if v != 100 else 63
        r1 = 68 if v != 100 else 70
        cv.line([(c[0] + r0 * math.cos(a), c[1] + r0 * math.sin(a)), (c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a))],
                2.5 if v == 100 else 1.5, GREEN)
    return cv.result()


def n2_index_map():
    """N2 (0 .. 1.1) -> the dial variant: step map for linear_interpolation (halfway between the steps)."""
    pts = ['(0.0 0.0)']
    for k in range(1, len(N2_STEPS)):
        mid = (N2_STEPS[k - 1] + N2_STEPS[k]) / 200.0
        pts += ['(%.4f %d.0)' % (mid - 0.0005, k - 1), '(%.4f %d.0)' % (mid, k)]
    pts.append('(1.2 %d.0)' % (len(N2_STEPS) - 1))
    return ' %s ' % ' '.join(pts)


# ------------------------------------------------------------------------------------------------ the atlas
# free corners of display2 (ac_f22 DISPLAYS regions, bottom-left pixels): A x 1612 .. 2048 the whole height
# (the left UFD ends at 1600); B x 0 .. 850, y 680 .. 1220 (between the ICP scratchpad and the lower MFD)
SIL_AT = (1620, 1556)
DIAL_AT = (1616, 8)                      # 3 columns of 140, upwards
B_AT, B_W, B_TOP = (4, 684), 846, 1216


def layout():
    """{sprite: dict(src=[(x, y) per variant], size=(w, h), at=(x, y) in the silhouette or None)}."""
    out = {'Silhouette': dict(src=[SIL_AT], size=(SIL_W, SIL_H), at=None)}
    out['N2'] = dict(src=[(DIAL_AT[0] + DIAL * (k % 3), DIAL_AT[1] + DIAL * (k // 3)) for k in range(len(N2_STEPS))],
                     size=(DIAL, DIAL), at=None)
    assert DIAL_AT[1] + DIAL * ((len(N2_STEPS) - 1) // 3 + 1) <= SIL_AT[1]
    x, y, row_h = B_AT[0], B_AT[1], 0
    for name, n, box in [('Bay' + b, 6, _bbox(bay=b)) for b in BAY_RECT] + [('Tank' + s, 2, _bbox(side=s)) for s in ('Left', 'Right')]:
        src = []
        for _ in range(n):
            if x + box[2] > B_AT[0] + B_W:
                x, y, row_h = B_AT[0], y + row_h + 4, 0
            src.append((x, y))
            x += box[2] + 4
            row_h = max(row_h, box[3])
        out[name] = dict(src=src, size=(box[2], box[3]), at=(box[0], box[1]))
    assert y + row_h <= B_TOP, 'atlas region B overflow'
    return out


def variants(name):
    """The pictures of a sprite's variants (index = the game's value)."""
    if name == 'Silhouette':
        base = silhouette({})
        return [base]
    if name == 'N2':
        return [dial(v) for v in N2_STEPS]
    lay = layout()[name]
    x, y = lay['at']
    w, h = lay['size']
    pics = []
    if name.startswith('Bay'):
        bay = name[3:]
        for k in range(6):
            pics.append(silhouette({bay: (k % 3, k // 3)})[y:y + h, x:x + w])
    else:
        for on in (0, 1):
            pics.append(silhouette({name: on})[y:y + h, x:x + w])
    return pics


def paint(atlas):
    """Paint every sprite into an atlas array (rows from the bottom, ATLAS x ATLAS x 3, 0..1)."""
    lay = layout()
    for name, d in lay.items():
        w, h = d['size']
        for (sx, sy), pic in zip(d['src'], variants(name)):
            atlas[sy:sy + h, sx:sx + w] = pic[:h, :w]
    return atlas
