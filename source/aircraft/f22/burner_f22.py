"""F-22 afterburner flame without geometry: a chain of light sprites behind each nozzle, longer with more afterburner.

The standard shader ignores the colour alpha and the glass shader the luminance, so a translucent plume mesh cannot be
drawn (tests 11-13, 2026-10-20). Light sprites are the game's own glow, and they need no conversion. The DCS mod draws its
flame the same way: afterburner_circles_count = 8 discs along the jet (F-22A.lua). Stock F/A-18 and F-15E light the
nozzle surroundings with two cones, kept here as the glow on the airframe and the ground. All of it hangs on the nozzle
bodies of tvc_f22.py (R0 stays in model coordinates, as the stock lights on NoseGearUpper), so it swings with the thrust.

Tests 2026-10-30: brightness 3 .. 1.2, size 0.55 .. 0.18, 8 sprites over 5 m: too much bloom near the nozzle, but the shape read as
flame (user's preference). 12 sprites over 4 m, close together: a hatched streak. 3 over 0.9 m: too little. Now the proportions of the
user's photos of the real aircraft: a column about 7 m long from the nozzle, flat and about as wide as the nozzle at its root (a pair of
sprites side by side there), orange at the root, then pale peach to pink with a brighter band every 1.2 m (the shock diamonds), thinning
and fading to the tip. 7 m with 0.58 m spacing then read as too long, gaps between dots (user): 4.2 m and 0.38 m. The growth with thrust: small cores run
out from the nozzle, the full body fills out behind them.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import tmd

ENGINES = (('Engine1', 0.66), ('Engine2', -0.66))     # Engine1 = left (+y), as in make_f22.py
Z, X_EXIT, LENGTH = 0.27, -5.55, 4.2
COUNT = 12
ROOT_WIDTH = 0.14                       # y offset of the side-by-side sprites at the nozzle
ROOT, MID, TIP = (1.0, 0.62, 0.22), (1.0, 0.66, 0.50), (0.95, 0.45, 0.36)
SIZE_NEAR, SIZE_FAR = 0.28, 0.18
BRIGHTNESS_NEAR, BRIGHTNESS_FAR = 0.56, 0.20    # 0.70, 0.25 before the cores: the same light at full afterburner
DIAMOND = 1.15                          # the brighter band, every second sprite
FLICKER = (0.09, 0.13, 0.17)            # s: flame shimmer, sprites share three flashers out of step
AB_START = 0.3        # Engine<n>Afterburner jumps to 0.3 as the afterburner lights, then runs to 1.0
# Each station has two sprites, as sprites keep their size whatever their brightness (the first big dim ball, then a second, then the small ones: user,
# 2026-11-01). Afterburner level at which the first .. last station's core and body start, and how long each takes to come up. At light-off (0.3) the
# first cores are already on
CORE_START, CORE_END, CORE_WINDOW = 0.20, 0.85, 0.08
BODY_START, BODY_END, BODY_WINDOW = 0.40, 0.92, 0.25
CORE_SIZE_NEAR, CORE_SIZE_FAR, CORE_BRIGHTNESS = 0.10, 0.07, 0.60
# at 600 the first picture was right at part afterburner and flat yellow at full (user's screenshots, 2026-11-01)
FIRE_LUMINANCE = 350.0
# Drawn shaft speed. The game draws 60 frames/s (main.mcf graphics_frame_rate): a pattern seems to turn only up to half its period a frame, past that it
# folds. 300 rad/s at full N1 looked nearly still at N2 72 %, fast at 75, slow and backwards at 100 (computed; user, 2026-11-01). So not the true speed
# (thousands of rpm, which no frame rate shows) but what reads true: rising with the spool, the same at full dry and afterburner, as
# the real engine's rpm (make_f22.py: N2 100 % at full dry). rad/s at the top: below half a period a frame of the 10 rods (18.8), and of the fan's ~24 painted blades (7.8)
TURBINE_SPEED = 14.0
FAN_SPEED = 6.0
SPEED_MAP = ((0.0, 0.0), (0.65, 0.45), (1.0, 1.0), (1.1, 1.0))         # N2 -> part of the top speed: a turbine's low pressure spool is slow at idle


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
        for i in range(COUNT):
            f = i / (COUNT - 1.0)
            col = [_lerp(a, b, f / 0.25) for a, b in zip(ROOT, MID)] if f < 0.25 else \
                [_lerp(a, b, (f - 0.25) / 0.75) for a, b in zip(MID, TIP)]
            flicker = 'FlameFlicker%d.Output' % (i % len(FLICKER))
            diamond = DIAMOND if i % 2 else 1.0

            def fade(tag, lo, hi):      # comes up between afterburner lo and hi, with the flicker
                gfx.children.append(_node('graphics_linear_interpolation', '%sFlame%s%dFade' % (eng, tag, i), Input=ab + '.Output',
                                          Map=('tmvector2d', ' (%.3f 0.0) (%.3f 1.0) ' % (lo, hi))))
                gfx.children.append(_node('graphics_product', '%sFlame%s%dLive' % (eng, tag, i), Input0='%sFlame%s%dFade.Output' % (eng, tag, i),
                                          Input1=flicker))
                return '%sFlame%s%dLive.Output' % (eng, tag, i)

            # a small core: the flame runs out from the nozzle
            lo = _lerp(CORE_START, CORE_END, f)
            live = fade('Core', lo, lo + CORE_WINDOW)
            gfx.children.append(_node('graphics_pointlight', '%sFlameCore%d' % (eng, i), **body, R0=_vec((X_EXIT - LENGTH * f, y, Z)),
                                      X0=_vec((-1.0, 0.0, 0.0)), Color=_vec(col + [1.0]),
                                      Brightness=_lerp(CORE_BRIGHTNESS, BRIGHTNESS_FAR, f) * diamond,
                                      Size=_lerp(CORE_SIZE_NEAR, CORE_SIZE_FAR, f), ConeCenter=0.0, ConeCutoff=-1.0, InputModulation=live))
            # the full body of the flame fills out behind it: a large sprite on its own at low brightness read as a big dim ball
            lo = _lerp(BODY_START, BODY_END, f)
            live = fade('Body', lo, min(lo + BODY_WINDOW, 1.0))
            bright = _lerp(BRIGHTNESS_NEAR, BRIGHTNESS_FAR, f) * diamond
            size = _lerp(SIZE_NEAR, SIZE_FAR, f)
            for tag, dy in ((('', 0.0),) if i > 1 else (('A', -ROOT_WIDTH), ('B', ROOT_WIDTH))):
                gfx.children.append(_node('graphics_pointlight', '%sFlame%d%s' % (eng, i, tag), **body,
                                          R0=_vec((X_EXIT - LENGTH * f, y + dy, Z)), X0=_vec((-1.0, 0.0, 0.0)),
                                          Color=_vec(col + [1.0]), Brightness=bright, Size=size, ConeCenter=0.0,
                                          ConeCutoff=-1.0, InputModulation=live))
        side = 'Left' if y > 0 else 'Right'
        fire = 'Burner_%s_C' % side
        if fire in parts:           # the engine inside the nozzle (nozzle_fire_f22.py), lit as the stock F/A-18's and F-15E's
            # the fire's light (user 2026-11-07: right at the least afterburner, too bright at full -> half at full; then
            # "half again"): 2/3 of the first at light-off (0.3 -> 0.2), a quarter at full (1.0 -> 0.25)
            gfx.children.append(_node('graphics_linear_interpolation', eng + 'FireLevel', Input=ab + '.Output',
                                      Map=('tmvector2d', ' (0.0 0.0) (0.3 0.2) (1.0 0.25) ')))
            gfx.children.append(_node('graphics_color', eng + 'FireColor', Input=eng + 'FireLevel.Output',
                                      Color=('tmvector3d', ' %.1f %.1f %.1f ' % ((FIRE_LUMINANCE,) * 3))))
            gfx.children.append(_node('rigidbodygraphics', fire, GeometryList=' %s ' % fire,
                                      PositionID=('uint32', 'Fuselage.R'), OrientationID=('uint32', 'Fuselage.Q'),
                                      InputLuminance=eng + 'FireColor.Output'))
            # the turbine: as the stock B737 and LJ45 turn their fans, the integral of the spool speed in rad/s through a graphics_rotation
            speed_map = ' %s ' % ' '.join('(%.2f %.3f)' % (n2, f * TURBINE_SPEED) for n2, f in SPEED_MAP)
            at = [c.name for c in dyn.children].index('GfxOutVectorPitch')
            dyn.children[at:at] = [
                _node('linear_interpolation', eng + 'TurbineSpeed', Input=eng + 'N2.Output', Map=('tmvector2d', speed_map)),
                _node('integral', eng + 'TurbineAngle', Input=eng + 'TurbineSpeed.Output'),
                # not <name>Output: the stock files write that with no Input, and it publishes <name>.Output. Graphics reading
                # Engine1TurbineAngleOutput.Output got nothing, the wheels stood still (user, 2026-11-01). GfxOut* as make_f22.py's published()
                _node('output', 'GfxOut%sTurbineAngle' % eng, Input=eng + 'TurbineAngle.Output'),
            ]
            gfx.children.append(_node('graphics_input', 'Gfx%sTurbineAngle' % eng, InputID=('uint32', 'GfxOut%sTurbineAngle.Output' % eng)))
            gfx.children.append(_node('graphics_rotation', eng + 'TurbineSpin', Input='Gfx%sTurbineAngle.Output' % eng,
                                      Axis=_vec(parts['Turbine_' + side]['hinge']['axis']), Pivot=_vec(parts['Turbine_' + side]['hinge']['pivot'])))
            # one wheel, cold and at afterburner: unlit until the afterburner, then the fire
            gfx.children.append(_node('graphics_linear_interpolation', eng + 'TurbineHeat', Input=ab + '.Output',
                                      Map=('tmvector2d', ' (0.0 0.0) (0.3 0.33) (1.0 0.25) ')))   # as the fire's light, 2026-11-07
            gfx.children.append(_node('graphics_color', eng + 'TurbineColor', Input=eng + 'TurbineHeat.Output',
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
