"""F-22 afterburner flame without geometry: a chain of light sprites behind each nozzle, longer with more afterburner.

The standard shader ignores the colour alpha and the glass shader the luminance, so a translucent plume mesh cannot be
drawn (tests 11-13, 2026-10-20). Light sprites are the game's own glow, and they need no conversion. The DCS mod draws its
flame the same way: afterburner_circles_count = 8 discs along the jet (F-22A.lua). Stock F/A-18 and F-15E light the
nozzle surroundings with two cones, kept here as the glow on the airframe and the ground. All of it hangs on the nozzle
bodies of tvc_f22.py (R0 stays in model coordinates, as the stock lights on NoseGearUpper), so it swings with the thrust.

Tests 2026-10-30: brightness 3 .. 1.2, size 0.55 .. 0.18, 8 sprites over 5 m: too much bloom near the nozzle, but the shape read as
flame (preferred). 12 sprites over 4 m, close together: a hatched streak. 3 over 0.9 m: too little. Now the proportions of the
photos of the real aircraft: a column about 7 m long from the nozzle, flat and about as wide as the nozzle at its root (a pair of
sprites side by side there), orange at the root, then pale peach to pink with a brighter band every 1.2 m (the shock diamonds), thinning
and fading to the tip. 7 m with 0.58 m spacing then read as too long, gaps between dots: 4.2 m and 0.38 m. The growth with thrust: small cores run
out from the nozzle, the full body fills out behind them.

2026-11-26 (colours and placements tried, sprites overlapping in part; two rounds of an in-flight test with the
looks on an SMS key): the flat column of the 2D nozzle won (the "dense" look) - violet at the exit (the hot, clean core of
night photos) through magenta and pink to orange-red at the tip, 4.2 m, three sprites across at the root, two in the
middle, one at the tip, close enough to overlap into one column, four pink-white shock-diamond bars. In daylight the sprites wash out, as the real flame nearly does; the engine gives the configs no
daylight signal, and it is kept so (realistic, and fine at night).
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import tmd

ENGINES = (('Engine1', 0.66), ('Engine2', -0.66))     # Engine1 = left (+y), as in make_f22.py
Z, X_EXIT = 0.27, -5.55
FLICKER = (0.09, 0.13, 0.17)            # s: flame shimmer, sprites share three flashers out of step
AB_START = 0.3        # Engine<n>Afterburner jumps to 0.3 as the afterburner lights, then runs to 1.0
# at 600 the first picture was right at part afterburner and flat yellow at full (screenshots, 2026-11-01)
FIRE_LUMINANCE = 350.0
ROOT_GAP = 0.12          # m: the flame column starts this far behind the exit (0 until 2026-11-27)
ROOT_BRIGHT = 0.22       # the column's brightness at its root (0.30 until 2026-11-27)
# the inside's light x FIRE_GAIN (2026-11-27 test, x1 / x1.6 / x2.5 with the new high-contrast maps: between
# the last two, nearer x2.5): 2.2
FIRE_GAIN = 2.2
# the pulse (depth, period s, phase as part of the period): the wave, the same period in every zone, its phase later aft
# (zone 0 aft: last), and a quick jitter of each zone's own, out of step between zones and engines. The wave's period is
# 1 s: the stock files do not show whether Phase is in seconds or in periods (all theirs with a phase run at 1 s) - at 1 s
# both read the same
# (first test 0.10 / 0.06: not seen - measured in the video, a patch of the liner moved +-3 %, under the flame's steady glow)
PULSE_WAVE = lambda k, n: (0.25, 1.0, (n - 1 - k) / float(n))
PULSE_JITTER = lambda k, y: (0.12, (0.17, 0.23, 0.19, 0.29, 0.21)[k % 5] * (1.0 if y > 0 else 1.13), 0.37 * k)
# Drawn shaft speed. The game draws 60 frames/s (main.mcf graphics_frame_rate): a pattern seems to turn only up to half its period a frame, past that it
# folds. 300 rad/s at full N1 looked nearly still at N2 72 %, fast at 75, slow and backwards at 100 (computed; 2026-11-01). So not the true speed
# (thousands of rpm, which no frame rate shows) but what reads true: rising with the spool, the same at full dry and afterburner, as
# the real engine's rpm (make_f22.py: N2 100 % at full dry). rad/s at the top: below half a period a frame of the 10 rods (18.8), and of the fan's ~24 painted blades (7.8)
TURBINE_SPEED = 14.0
FAN_SPEED = 6.0
SPEED_MAP = ((0.0, 0.0), (0.65, 0.45), (1.0, 1.0), (1.1, 1.0))         # N2 -> part of the top speed: a turbine's low pressure spool is slow at idle

# A flame sprite: (distance behind the exit m, side offset m, size, brightness, colour, afterburner level it starts at,
# window over which it comes up)


def _grad(stops, f):
    """Colour along the flame: stops [(f, rgb)], f 0 at the exit .. 1 at the tip."""
    for (fa, ca), (fb, cb) in zip(stops, stops[1:]):
        if f <= fb:
            return tuple(_lerp(x, y, (f - fa) / (fb - fa)) for x, y in zip(ca, cb))
    return stops[-1][1]


VIOLET, MAGENTA, PINK, ORANGE = (0.55, 0.45, 1.0), (1.0, 0.5, 0.85), (1.0, 0.55, 0.55), (1.0, 0.42, 0.25)


def _flat(length, n, w0, w1, s0, s1, b0, b1, stops, lo0=0.3, lo1=0.9, win=0.2):
    """A flat column from the 2D nozzle: sprites close enough to overlap (spacing < size), three across at the root,
    two in the middle, one at the tip, the width narrowing; brightness shared out among those across."""
    out = []
    for i in range(n):
        f = i / (n - 1.0)
        across = 3 if f < 0.25 else (2 if f < 0.6 else 1)
        w = _lerp(w0, w1, f)
        for k in range(across):
            dy = 0.0 if across == 1 else _lerp(-w, w, k / (across - 1.0))
            out.append((length * f, dy, _lerp(s0, s1, f), _lerp(b0, b1, f) / (0.6 + 0.4 * across), _grad(stops, f),
                        _lerp(lo0, lo1, f), win))
    return out


def _diamonds(xs, size, b0, b1, col, lo0=0.5):
    """Shock diamonds: a short bright bar of two sprites across at each x."""
    out = []
    for k, x in enumerate(xs):
        f = k / max(len(xs) - 1.0, 1.0)
        for dy in (-0.05, 0.05):
            out.append((x, dy, size * (1.0 - 0.25 * f), _lerp(b0, b1, f), col, lo0 + 0.1 * k, 0.1))
    return out


def flame():
    """The afterburner flame of one engine (sprites as above): the 2D nozzle's flat column, 16 stations over 4.2 m
    (0.28 m apart, sprites 0.26 .. 0.14 m - they overlap into one column), four diamond bars closing up downstream."""
    # 2026-11-27 (the nozzle's inside dull, no contrast): the root's violet glow lay over the inside seen from behind
    # (measured: blue 116 - 131 on the orange flaps) - the column starts ROOT_GAP behind the exit and its root is dimmer
    stops = [(0.0, VIOLET), (0.2, MAGENTA), (0.45, PINK), (1.0, ORANGE)]
    out = _flat(4.2, 16, 0.17, 0.04, 0.26, 0.14, ROOT_BRIGHT, 0.08, stops) + \
        _diamonds((0.8, 1.55, 2.25, 2.9), 0.15, 0.45, 0.2, (1.0, 0.8, 0.9))
    return [(dx + ROOT_GAP,) + tuple(rest) for dx, *rest in out]


def _node(type_, name, **fields):
    n = tmd.Node(type_, name, leaf=False)
    for k, v in fields.items():
        t, v = v if isinstance(v, tuple) else ('float64' if isinstance(v, float) else 'string8', v)
        n.children.append(tmd.Node(t, k, v if isinstance(v, str) else '%.6g' % v))
    return n


def _vec(v):
    return ('tmvector3d', ' %s ' % ' '.join('%.4f' % x for x in v))


def _lerp(a, b, f):
    return a + (b - a) * f


def apply(gfx, dyn, parts=()):
    """parts: the model's parts, when it carries the nozzle fire of ac_f22.py _burner_objects (a conversion)."""
    for k, period in enumerate(FLICKER):
        gfx.children.append(_node('graphics_flasher', 'FlameFlicker%d' % k, InputTime='GfxLightTime.Output', Function='Rectangle',
                                  Period=period, Minimum=0.9, Maximum=1.0))
    for eng, y in ENGINES:
        body = dict(PositionID=('uint32', eng + 'Nozzle.R'), OrientationID=('uint32', eng + 'Nozzle.Q'))
        ab = 'Gfx%sAfterburner' % eng
        gfx.children.append(_node('graphics_input', ab, InputID=('uint32', '%sAfterburner.Output' % eng)))
        for name, x, col, bright in (('Glow', -5.4, (0.8, 0.3, 0.0, 1.0), 0.15), ('GlowCore', -5.0, (1.0, 0.6, 0.2, 1.0), 0.15)):
            gfx.children.append(_node('graphics_conelight', '%sAfterBurner%s' % (eng, name), **body, R0=_vec((x, y, Z)),
                                      X0=_vec((-1.0, 0.0, 0.0)), Color=_vec(col), Brightness=bright, ConeCenter=0.9,
                                      ConeCutoff=-0.3, InputModulation=ab + '.Output'))
        for j, (dx, dy, size, bright, col, lo, win) in enumerate(flame()):
            t = '%sFlame%d' % (eng, j)
            gfx.children.append(_node('graphics_linear_interpolation', t + 'Fade', Input=ab + '.Output',
                                      Map=('tmvector2d', ' (%.3f 0.0) (%.3f 1.0) ' % (lo, min(lo + win, 1.0)))))
            gfx.children.append(_node('graphics_product', t + 'Live', Input0=t + 'Fade.Output',
                                      Input1='FlameFlicker%d.Output' % (j % len(FLICKER))))
            gfx.children.append(_node('graphics_pointlight', t, **body, R0=_vec((X_EXIT - dx, y + dy, Z)),
                                      X0=_vec((-1.0, 0.0, 0.0)), Color=_vec(list(col) + [1.0]), Brightness=bright,
                                      Size=size, ConeCenter=0.0, ConeCutoff=-1.0, InputModulation=t + 'Live.Output'))
        side = 'Left' if y > 0 else 'Right'
        fire = 'Burner_%s_C' % side
        if fire in parts:           # the engine inside the nozzle (nozzle_fire_f22.py), lit as the stock F/A-18's and F-15E's
            # the fire's light (2026-11-07: right at the least afterburner, too bright at full -> half at full; then
            # half again): 2/3 of the first at light-off (0.3 -> 0.2), a quarter at full (1.0 -> 0.25)
            gfx.children.append(_node('graphics_linear_interpolation', eng + 'FireLevel', Input=ab + '.Output',
                                      Map=('tmvector2d', ' (0.0 0.0) (0.3 %.3f) (1.0 %.3f) ' % (0.2 * FIRE_GAIN, 0.25 * FIRE_GAIN))))
            fire_in = eng + 'FireLevel.Output'
            # the liner's zones (nozzle_fire_f22.ZONES: Burner_<side>_C aft, _C1 .. forward), each its light times a pulse:
            # a slow wave running aft (PULSE_WAVE, the phase later for each zone further aft) times a quick jitter of its own
            # (PULSE_JITTER) - 2026-11-27: the fire to look alive. Each factor 1 - depth x triangle (0 .. 1), so the
            # light only dips below what it was; the flaps go with the aft zone
            zones = [z for z in [fire] + ['%s%d' % (fire, k) for k in range(1, 10)] if z in parts]
            for k, zone in enumerate(zones):
                col = eng + 'FireColor' + ('' if k == 0 else str(k))
                level = fire_in
                for kind, (depth, period, phase) in (('Wave', PULSE_WAVE(k, len(zones))), ('Jitter', PULSE_JITTER(k, y))):
                    t = '%sFire%s%d' % (eng, kind, k)
                    gfx.children.append(_node('graphics_flasher', t + 'Tri', InputTime='GfxLightTime.Output', Function='Triangle',
                                              Period=period, Phase=phase, Minimum=0.0, Maximum=1.0))
                    src = t + 'Tri.Output'
                    top = 1.0
                    gfx.children.append(_node('graphics_linear_interpolation', t, Input=src,
                                              Map=('tmvector2d', ' (0.0 1.0) (%.2f %.3f) ' % (top, 1.0 - top * depth))))
                    gfx.children.append(_node('graphics_product', t + 'Level', Input0=level, Input1=t + '.Output'))
                    level = t + 'Level.Output'
                gfx.children.append(_node('graphics_color', col, Input=level,
                                          Color=('tmvector3d', ' %.1f %.1f %.1f ' % ((FIRE_LUMINANCE,) * 3))))
                gfx.children.append(_node('rigidbodygraphics', zone, GeometryList=' %s ' % zone,
                                          PositionID=('uint32', 'Fuselage.R'), OrientationID=('uint32', 'Fuselage.Q'),
                                          InputLuminance=col + '.Output'))
            # the turbine: as the stock B737 and LJ45 turn their fans, the integral of the spool speed in rad/s through a graphics_rotation
            speed_map = ' %s ' % ' '.join('(%.2f %.3f)' % (n2, f * TURBINE_SPEED) for n2, f in SPEED_MAP)
            at = [c.name for c in dyn.children].index('GfxOutVectorPitch')
            dyn.children[at:at] = [
                _node('linear_interpolation', eng + 'TurbineSpeed', Input=eng + 'N2.Output', Map=('tmvector2d', speed_map)),
                _node('integral', eng + 'TurbineAngle', Input=eng + 'TurbineSpeed.Output'),
                # not <name>Output: the stock files write that with no Input, and it publishes <name>.Output. Graphics reading
                # Engine1TurbineAngleOutput.Output got nothing, the wheels stood still (2026-11-01). GfxOut* as make_f22.py's published()
                _node('output', 'GfxOut%sTurbineAngle' % eng, Input=eng + 'TurbineAngle.Output'),
            ]
            gfx.children.append(_node('graphics_input', 'Gfx%sTurbineAngle' % eng, InputID=('uint32', 'GfxOut%sTurbineAngle.Output' % eng)))
            gfx.children.append(_node('graphics_rotation', eng + 'TurbineSpin', Input='Gfx%sTurbineAngle.Output' % eng,
                                      Axis=_vec(parts['Turbine_' + side]['hinge']['axis']), Pivot=_vec(parts['Turbine_' + side]['hinge']['pivot'])))
            # one wheel, cold and at afterburner: unlit until the afterburner, then the fire
            gfx.children.append(_node('graphics_linear_interpolation', eng + 'TurbineHeat', Input=ab + '.Output',
                                      Map=('tmvector2d', ' (0.0 0.0) (0.3 %.3f) (1.0 %.3f) ' % (0.33 * FIRE_GAIN, 0.25 * FIRE_GAIN))))   # as the fire's light
            heat_in = eng + 'TurbineHeat.Output'
            gfx.children.append(_node('graphics_color', eng + 'TurbineColor', Input=heat_in,
                                      Color=('tmvector3d', ' %.1f %.1f %.1f ' % ((FIRE_LUMINANCE,) * 3))))
            gfx.children.append(_node('rigidbodygraphics', 'Turbine_' + side, GeometryList=' Turbine_%s ' % side,
                                      PositionID=('uint32', 'Fuselage.R'), OrientationID=('uint32', 'Fuselage.Q'),
                                      InputTransform=eng + 'TurbineSpin.Output', InputLuminance=eng + 'TurbineColor.Output'))
            # the fan at the end of the intake, on the same shaft
            fan = parts['K_Fan' + side].get('hinge') if 'K_Fan' + side in parts else None
            if fan:
                gfx.children.append(_node('graphics_input', 'Gfx%sFanAngle' % eng, InputID=('uint32', 'GfxOut%sTurbineAngle.Output' % eng),
                                          Scaling=FAN_SPEED / TURBINE_SPEED))
                gfx.children.append(_node('graphics_rotation', eng + 'FanSpin', Input='Gfx%sFanAngle.Output' % eng,
                                          Axis=_vec(fan['axis']), Pivot=_vec(fan['pivot'])))
                gfx.children.append(_node('rigidbodygraphics', 'K_Fan' + side, GeometryList=' K_Fan%s ' % side,
                                          PositionID=('uint32', 'Fuselage.R'), OrientationID=('uint32', 'Fuselage.Q'),
                                          InputTransform=eng + 'FanSpin.Output'))
            # the flaps carry their skin in their own animated parts
            flap_arg = 611 if y > 0 else 610
            for pname, p in parts.items():
                if flap_arg in p.get('args', ()):
                    gfx.find(pname).children.append(tmd.Node('string8', 'InputLuminance', eng + 'FireColor.Output'))
