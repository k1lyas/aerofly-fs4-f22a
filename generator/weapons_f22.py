"""F-22 missile release (0.9.2, 2026-11-25; the launch for good pictures only - after MDIvey, forum #54).

No targets, no guidance: a selected missile leaves the bay as on the real aircraft and flies on along its axis.

- Each missile of the combat load is a body of its own (157 kg AIM-120C, 85 kg AIM-9X, stores_f22.MASS) on a
  breakable joint to a kinematic rack, as the ferry tanks (breakage_f22._kicked / eject_stroke). The six AIM-120C in
  the main bay are thrown down by the LAU-142 ejector (0.25 m at 8 m/s, as the tanks' racks), the motor lights
  IGNITE_S later; each AIM-9X waits on the LAU-141 trapeze swung out with its side bay door (the body sits at that
  extended place from the start, out of sight) and leaves forward off the rail with its motor lit at once.
- Thrust: `force` on the missile's body along its own axis (docs/reference/ENGINE_CATALOG.md: tested in game
  2026-11-25 - it pushes a free body along X0 in the body's axes); Control = MaxForce = the thrust in N. Real motor
  data are not public: THRUST / BURN are estimates that give each missile about the speed gain published for it
  (AIM-120 ~Mach 4, AIM-9X ~Mach 2.5) - see MISSILES. The motor glows with point-light sprites as our afterburner
  (burner_f22.py); no smoke trail (the game has no particles for configs).
- From the release on a second force holds the missile up by its weight (the lift a guided missile makes at a small
  angle of attack; guidance itself is not simulated): it flies on level and out of sight and never comes down - a
  missile falling onto water ended the flight (any body of the aircraft touching water is a crash to the game).
- Attitude: the missile keeps the one it was launched with (large moment of inertia, no body aerodynamics - only a
  no drag) and flies along the aircraft's nose: fins of any kind, and aerofuselage's own moment, turned them over
  (2026-11-25).
- Graphics: the held missile is drawn on the fuselage (AIM-120: its own part; AIM-9X: the part riding the trapeze),
  its copy on its own body from the release on (ac_f22.py adds the copies 'Stores_AIM120F_<station>' /
  'Stores_AIM9F_<side>', the AIM-9X copy at the trapeze's full extension).
- Release (base aircraft): MASTER ARM (Weapons.MasterArm) ARM, in the air, DC ESS power, the combat load; the SMS
  page selects AIM-120 or AIM-9X; REL on the SMS page or the game's Strobe key (Controls.Lighting.Strobe: the F-22
  has no strobe lights) releases the next missile of that kind. The bay opens by itself for the launch and closes
  BAY_CLOSE_S after the missile has left (unless the pilot keeps it open). One launch at a time.
- Rearming: start the flight again with the combat load (a livery change in the menu reloads the aircraft in place).
"""
import math
import loads_f22

import stores_f22 as S
import breakage_f22 as B

L120, L9 = 3.657, 3.02
DIA120, DIA9 = 0.178, 0.127
# the AIM-120 release order: left / right alternately, outer to inner (the middle missiles sit 0.225 m ahead)
ORDER_120 = ('Pylon3', 'Pylon9', 'Pylon4', 'Pylon8', 'Pylon5', 'Pylon7')
# Motor estimates (no public thrust curves): a boost of ~6 s at ~9 g for the AIM-120C (157 kg), ~5 s at ~12 g for the
# AIM-9X (85 kg); the mass stays the launch mass (no propellant burn). First flight 2026-11-25 at 20 / 14 kN: wanted
# a little slower (pictures) - 14 / 10 kN, then still too fast - 8 / 6 kN (~5 / ~7 g)
KIND = {
    '120': dict(mass=S.MASS['aim120'], length=L120, dia=DIA120, thrust=8000.0, burn=6.0,
                ignite=0.35, eject_speed=8.0, kf=1.5e6, df=3.0e3, kt={'x': 3.0e6, 'y': 3.0e6, 'z': 3.0e6},
                dt={'x': 2.0e4, 'y': 2.0e4, 'z': 2.0e4}, fmax=4.0e4, tmax=2.0e5, inertia=(3.66, 8.0, 8.0), pitch=0.9),
    '9x': dict(mass=S.MASS['aim9x'], length=L9, dia=DIA9, thrust=6000.0, burn=5.0,
               ignite=0.05, eject_speed=3.0, kf=8.0e5, df=1.5e3, kt={'x': 1.5e6, 'y': 1.5e6, 'z': 1.5e6},
               dt={'x': 1.1e4, 'y': 1.1e4, 'z': 1.1e4}, fmax=2.5e4, tmax=1.0e5, inertia=(3.02, 8.0, 8.0), pitch=1.2)}
BAY_CLOSE_S = 1.5            # the bay shuts this long after the missile has gone
RACK_MASS = 2.0
# the cockpit layer's volume: the file is made at 0.35 of full (make_launch_sound INT_GAIN) - heard 'very, very quiet'
# (2026-11-25), so x3 here: about the outside layer's level, muffled
IN_VOLUME = 3.0
# the cockpit layer over the engines (2026-11-26: at full afterburner the launch was not heard, only at idle): its
# volume grows with the louder engine - x (1 + IN_N2_GAIN) from idle to full dry, + IN_AB_GAIN more at full afterburner
IN_N2_GAIN, IN_AB_GAIN = 1.2, 1.5
# the LAU-141 trapeze at full extension (DCS arguments 601 / 602 at 1.0, the chain A_63_62__S / A_36_35__S in
# f22.tmd): translation (x, y, z), rotations about x, y, z, pivot
AIM9_EXTEND = {'L': ((0.431396, 0.340079, -0.300093), (0.002781, 0.054776, 0.068068), (2.5484, 1.2396, -0.0642)),
               'R': ((0.431395, -0.341285, -0.298720), (-0.003630, 0.056000, -0.066995), (2.5484, -1.2396, -0.0642))}
# sprites of the motor: (distance behind the nozzle in m, size, brightness, colour)
PLUME = ((0.05, 0.16, 0.9, (1.0, 0.92, 0.75)), (0.35, 0.22, 0.6, (1.0, 0.72, 0.40)), (0.8, 0.26, 0.4, (1.0, 0.58, 0.30)),
         (1.4, 0.24, 0.25, (0.95, 0.48, 0.30)), (2.1, 0.20, 0.15, (0.90, 0.42, 0.30)))


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _rot(v, rx, ry, rz):
    """R = Rz Ry Rx applied to v."""
    x, y, z = v
    c, s = math.cos(rx), math.sin(rx)
    y, z = c * y - s * z, s * y + c * z
    c, s = math.cos(ry), math.sin(ry)
    x, z = c * x + s * z, -s * x + c * z
    c, s = math.cos(rz), math.sin(rz)
    x, y = c * x - s * y, s * x + c * y
    return (x, y, z)


def aim9_extended(p, side, vector=False):
    """A point (or with vector=True a direction) of the stowed AIM-9X at the trapeze's full extension."""
    t, (rx, ry, rz), piv = AIM9_EXTEND[side]
    if vector:
        return _rot(p, rx, ry, rz)
    q = _rot(tuple(a - b for a, b in zip(p, piv)), rx, ry, rz)
    return tuple(a + b + c for a, b, c in zip(q, piv, t))


def missiles():
    """The eight missiles in release order: dicts k (1..8), name, kind, station, bay, centre, axis, tail, held (part
    drawn while held), free (part on its own body), side ('L' / 'R' for the AIM-9X)."""
    out = []
    for st in ORDER_120:
        y0 = S.CONN[st][1]
        cx, shift, za = S.MAIN_BAY[st]
        y = y0 + shift * (1 if y0 > 0 else -1)
        out.append(dict(kind='120', station=st, bay='Center', centre=(cx, y, za), axis=(1.0, 0.0, 0.0),
                        tail=(cx - L120 / 2, y, za), held='Stores_AIM120_' + st, free='Stores_AIM120F_' + st))
    for st, side, bay in (('Pylon1', 'L', 'Left'), ('Pylon11', 'R', 'Right')):
        X, Y = (_unit(a) for a in S.AIM9_FRAME[st])
        c = tuple(a - S.AIM9_DROP * b for a, b in zip(S.CONN[st], Y))
        nodes = S.AIM9_RAIL[st][0]
        tail = tuple(a - b * L9 / 2 for a, b in zip(c, X))
        out.append(dict(kind='9x', station=st, bay=bay, side=side, centre=aim9_extended(c, side),
                        axis=_unit(aim9_extended(X, side, vector=True)), tail=aim9_extended(tail, side),
                        held='A_%s__S' % nodes.replace(',', '_'), free='Stores_AIM9F_' + side))
    for k, m in enumerate(out):
        m['k'] = k + 1
        m['name'] = 'F22Msl%d' % (k + 1)
    return out


def base(obj, dyn, anchor):
    """Release logic in f22.tmd. Before the bay servos read it: F22Bay<bay>Launch (the bay opened for a launch)."""
    o = lambda type_, name, **f: obj(dyn, type_, name, anchor, **f) and name + '.Output'
    ms = missiles()
    o('product', 'F22WpnArmed', Inputs=' MasterArmSafeSwitch.Output F22JettAirborne.Output DCBusEssentialOn.Output '
                                      'F22CombatLoad.Output ')
    # the selected kind: 1 AIM-120, 2 AIM-9X (the SMS page's buttons)
    o('variable', 'F22WpnSel', Value='1.0')
    for kind, v in (('120', 1.0), ('9x', 2.0)):
        o('event_value', 'F22WpnSelect' + kind, Input='%.1f' % v, Events=' F22WpnSel.Set ')
        o('logic_equal', 'F22WpnIs' + kind, Input0='F22WpnSel.Output', Input1='%.1f' % v)
    o('variable', 'F22WpnTarget', Value='0.0')
    busy, picks = [], []
    for m in ms:
        n, kd = m['name'], KIND[m['kind']]
        # requested: latched the moment the target names it (the integral holds at 1)
        o('logic_equal', n + 'Named', Input0='F22WpnTarget.Output', Input1='%.1f' % m['k'])
        o('product', n + 'ReqRate', Inputs=' %s.Output 50.0 ' % (n + 'Named'))
        o('integral_clamped', n + 'ReqHeld', Input=n + 'ReqRate.Output', Range=' 0.0 1.0 ', Value=0.0)
        o('logic_greater', n + 'Req', Input0=n + 'ReqHeld.Output', Input1='0.5')
        # released once its bay is fully open
        o('logic_and', n + 'Fire', Inputs=' %s.Output F22Bay%sFullOpen.Output ' % (n + 'Req', m['bay']))
        o('product', n + 'GoneRate', Inputs=' %s.Output 50.0 ' % (n + 'Fire'))
        o('integral_clamped', n + 'GoneHeld', Input=n + 'GoneRate.Output', Range=' 0.0 1.0 ', Value=0.0)
        o('logic_greater', n + 'Gone', Input0=n + 'GoneHeld.Output', Input1='0.5')
        o('logic_invert', n + 'NotGone', Input=n + 'Gone.Output')
        o('integral_clamped', n + 'Age', Input=n + 'Gone.Output', Range=' 0.0 60.0 ', Value=0.0)
        o('logic_greater', n + 'Clear', Input0=n + 'Age.Output', Input1='%.2f' % BAY_CLOSE_S)
        o('logic_invert', n + 'NotClear', Input=n + 'Clear.Output')
        o('logic_and', n + 'Busy', Inputs=' %s.Output %s.Output ' % (n + 'Req', n + 'NotClear'))
        # the motor
        o('logic_greater', n + 'Lit', Input0=n + 'Age.Output', Input1='%.2f' % kd['ignite'])
        o('logic_greater', n + 'Burning', Input0='%.2f' % (kd['ignite'] + kd['burn']), Input1=n + 'Age.Output')
        o('logic_and', n + 'Burn', Inputs=' %s.Output %s.Output ' % (n + 'Lit', n + 'Burning'))
        r = loads_f22.ratio(m['kind'], kd['mass'])     # a light body (loads_f22): its forces scaled alike
        o('product', n + 'Thrust', Inputs=' %s.Output %.2f ' % (n + 'Burn', kd['thrust'] * r))
        # held up by its weight from the release on (the lift of a guided missile; the guidance is not simulated): it
        # flies on level and out of sight and never comes down - a spent missile falling onto water ended the flight,
        # the game counting any body of the aircraft touching water a crash (2026-11-25). No drag either: the first
        # one, a force from the missile's own speed, stopped the missiles dead (the inertial reference's vertical
        # speed is not in m/s) - unseen far away, a spent missile simply coasts on
        o('product', n + 'Hold', Inputs=' %s.Output %.2f ' % (n + 'Gone', kd['mass'] * 9.81 * r))
        # on the aircraft: the combat load less the gone ones
        o('product', n + 'Held', Inputs=' F22CombatLoad.Output %s.Output ' % (n + 'NotGone'))
        o('logic_invert', n + 'HeldHidden', Input=n + 'Held.Output')
        # outputs for the graphics (held part: base graphics; free copy and plume: the add-on's)
        for sig in ('HeldHidden', 'NotGone', 'Burn', 'Lit'):
            o('output', 'GfxOut%s%s' % (n, sig), Input='%s%s.Output' % (n, sig))
        busy.append(n + 'Busy.Output')
    o('logic_or', 'F22WpnBusy', Inputs=' %s ' % ' '.join(busy))
    # the cockpit launch layer's volume over the engines' noise (IN_N2_GAIN, IN_AB_GAIN)
    o('maximum', 'F22LaunchInN2', Inputs=' Engine1N2.Output Engine2N2.Output ')
    o('maximum', 'F22LaunchInAb', Inputs=' Engine1Afterburner.Output Engine2Afterburner.Output ')
    o('linear_interpolation', 'F22LaunchInN2Gain', Input='F22LaunchInN2.Output',
      Map=' (0.70 0.0) (1.00 %.2f) ' % IN_N2_GAIN)
    o('linear_interpolation', 'F22LaunchInAbGain', Input='F22LaunchInAb.Output', Map=' (0.0 0.0) (1.0 %.2f) ' % IN_AB_GAIN)
    o('sum', 'F22LaunchInLoud', Inputs=' 1.0 F22LaunchInN2Gain.Output F22LaunchInAbGain.Output ')
    o('product', 'F22LaunchInVolume', Inputs=' F22LaunchInLoud.Output %.2f ' % IN_VOLUME)
    o('output', 'GfxOutF22LaunchInVolume', Input='F22LaunchInVolume.Output')
    o('logic_invert', 'F22WpnIdle', Input='F22WpnBusy.Output')
    # the next missile of each kind: not yet requested, every one before it of its kind requested; one press names it
    for kind in KIND:
        prev = None
        for m in [x for x in ms if x['kind'] == kind]:
            n = m['name']
            o('logic_invert', n + 'Free', Input=n + 'Req.Output')
            ins = ['F22WpnIs%s.Output' % kind, 'F22WpnArmed.Output', 'F22WpnIdle.Output', n + 'Free.Output']
            if prev:
                ins.append(prev + 'Req.Output')
            o('product', n + 'Next', Inputs=' %s ' % ' '.join(ins))
            o('product', n + 'Pick', Inputs=' %s.Output %.1f ' % (n + 'Next', m['k']))
            picks.append(n + 'Pick.Output')
            prev = n
    o('sum', 'F22WpnPick', Inputs=' %s ' % ' '.join(picks))
    o('event_value', 'F22WpnRelPress', Input='F22WpnPick.Output', Events=' F22WpnTarget.Set ')
    # the key: the game's Strobe command (the F-22 has no strobe lights, make_f22.py 'exterior lights')
    o('input_event', 'F22WpnRelKey', Message='Controls.Lighting.Strobe', Events=' F22WpnRelPress.Trigger ')
    # bays opened for a launch (make_f22.py: the door servo takes the larger of the pilot's command and this)
    for bay in ('Center', 'Left', 'Right'):
        ins = [m['name'] + 'Busy.Output' for m in ms if m['bay'] == bay]
        o('logic_or' if len(ins) > 1 else 'linear', 'F22Bay%sLaunch' % bay,
          **({'Inputs': ' %s ' % ' '.join(ins)} if len(ins) > 1 else {'Input': ins[0]}))
    # counts and the mass still on board (ENG page gross weight)
    for kind in KIND:
        o('sum', 'F22WpnCount' + kind, Inputs=' %s ' % ' '.join(m['name'] + 'Held.Output' for m in ms if m['kind'] == kind))
    o('mixlinear', 'F22StoresMass', Input0='F22WpnCount120.Output', Input1='F22WpnCount9x.Output',
      Weight0=KIND['120']['mass'], Weight1=KIND['9x']['mass'])
    # the selected kind's count, and the SMS status: 0 SAFE, 1 GND, 2 LAUNCH, 3 EMPTY, 4 READY
    o('product', 'F22WpnSelCount120', Inputs=' F22WpnIs120.Output F22WpnCount120.Output ')
    o('product', 'F22WpnSelCount9x', Inputs=' F22WpnIs9x.Output F22WpnCount9x.Output ')
    o('sum', 'F22WpnSelLeft', Inputs=' F22WpnSelCount120.Output F22WpnSelCount9x.Output ')
    o('logic_greater', 'F22WpnHasAny', Input0='F22WpnSelLeft.Output', Input1='0.5')
    o('sum', 'F22WpnSt1', Inputs=' 1.0 F22WpnHasAny.Output ')
    o('product', 'F22WpnSt2', Inputs=' F22WpnIdle.Output F22WpnSt1.Output ')
    o('sum', 'F22WpnSt3', Inputs=' 1.0 F22WpnSt2.Output ')
    o('product', 'F22WpnSt4', Inputs=' F22JettAirborne.Output F22WpnSt3.Output ')
    o('sum', 'F22WpnSt5', Inputs=' 1.0 F22WpnSt4.Output ')
    o('product', 'F22WpnStatus', Inputs=' MasterArmSafeSwitch.Output F22WpnSt5.Output ')
    print('weapons: %d missiles, release order %s; REL on the SMS page or the Strobe key' % (
        len(ms), ' '.join(m['station'] for m in ms)))


def held_graphics(g, parts):
    """Base graphics: the held missiles hide as they go. Returns the parts handled."""
    done = []
    for m in missiles():
        hide = 'GfxF22Msl%dHeldHidden' % m['k']
        g('graphics_input', hide, InputID=('uint32', 'GfxOut%sHeldHidden.Output' % m['name']))
        if m['kind'] == '120' and m['held'] in parts:
            g('rigidbodygraphics', m['held'], GeometryList=' %s ' % m['held'], PositionID=('uint32', 'Fuselage.R'),
              OrientationID=('uint32', 'Fuselage.Q'), InputHide=hide + '.Output')
            done.append(m['held'])
    return done


def addon(obj, holder):
    """The missiles' part of the stores add-on (stores/system.tmd, loads_f22): light bodies, their station tanks with
    the rest of the mass; returns (dynamics, graphics, sounds)."""
    o = lambda type_, name, **f: obj(holder, type_, name, **f)
    vec = lambda v: ('tmvector3d', ' %.4f %.4f %.4f ' % tuple(v))
    farr = lambda xs: ('float64', '[ %s ]' % ' '.join('%.4f' % x for x in xs))
    eye = ('tmmatrix3d', ' 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0 ')
    dyn, gfx, snd = [], [], []
    import failures_f22
    sound = failures_f22._have_sound('missile_launch') and failures_f22._have_sound('missile_launch_int')
    for m in missiles():
        n, kd = m['name'], KIND[m['kind']]
        body = n + 'Body'
        c, ax, L = m['centre'], m['axis'], kd['length']
        at = lambda d: tuple(a + b * d for a, b in zip(c, ax))           # a point d m ahead of the centre on the axis
        kick_axis = (0.0, 0.0, 1.0) if m['kind'] == '120' else tuple(-a for a in ax)   # down / forward off the rail
        nodes, pos = B.eject_stroke(lambda t, nm, **f: o(t, nm, **f), n + 'Stroke', n + 'Gone.Output',
                                    kd['eject_speed'])
        dyn += nodes
        r = loads_f22.ratio(m['kind'], kd['mass'])     # a light body (loads_f22): mass, mount and forces scaled alike
        sc = lambda v: {a: x * r for a, x in v.items()} if isinstance(v, dict) else v * r
        dyn.append(o('rigidbody', body, Mass=kd['mass'] * r, InertiaLength=vec(kd['inertia']), R0=vec(c), B0=eye))
        _, nodes = B._kicked(lambda t, nm, **f: o(t, nm, **f), n, 'Fuselage', body, c, pos, sc(kd['kf']), sc(kd['df']),
                             sc(kd['kt']), sc(kd['dt']), sc(kd['fmax']), sc(kd['tmax']), RACK_MASS, axis=kick_axis)
        dyn += nodes
        # Holding its line (2026-11-25, six flights: with tail fins as lift the missiles dived - the coefficient is a
        # steady force; with fins as cross-flow drag they wandered down, up and aside; with no fins and a body's
        # cross-flow drag even about the centre of gravity they flew straight, then turned over within a second or
        # two - aerofuselage has a moment of its own). Now no body aerodynamics at all: a drag force at the centre of
        # gravity along the missile (below) slows it and turns it nowhere; with the large moment of inertia the missile keeps the attitude it was launched with, as the guidance we do not
        # simulate would hold it
        # the motor at the centre of gravity, R0 in the aircraft's axes as every dynamics object (second flight
        # 2026-11-25, left / right missiles: R0 = the centre of gravity flew straight; R0 = 0 0 0 - the aircraft's
        # origin, ahead of and above the missile - nosed them down)
        # (X0 along the body's own x: the body starts in the aircraft's axes even where the drawn AIM-9X sits yawed 4 deg
        # outboard on its trapeze - thrust along that drawn axis pushed the AIM-9X sideways, 2026-11-25)
        dyn.append(o('force', n + 'Motor', Body=body, R0=vec(c), X0=vec((1.0, 0.0, 0.0)), MaxForce=kd['thrust'] * r,
                     Control=n + 'Thrust.Output'))
        # holding its line while the motor burns: the lift a real missile makes at a small angle of attack under its
        # guidance (which we do not simulate) - its weight, up in its own axes. Without it the missiles sank ~170 m
        # under the aircraft's path in a burn and read as diving (2026-11-25); spent, they fall
        dyn.append(o('force', n + 'Lift', Body=body, R0=vec(c), X0=vec((0.0, 0.0, 1.0)), MaxForce=kd['mass'] * 9.81 * r,
                     Control=n + 'Hold.Output'))
        # graphics: the copy on its own body once released, the plume while the motor burns
        gfx.append(o('graphics_input', 'GfxF22Msl%dNotGone' % m['k'], InputID=('uint32', 'GfxOut%sNotGone.Output' % n)))
        gfx.append(o('graphics_input', 'GfxF22Msl%dBurn' % m['k'], InputID=('uint32', 'GfxOut%sBurn.Output' % n)))
        gfx.append(o('rigidbodygraphics', m['free'], GeometryList=' %s ' % m['free'], PositionID=('uint32', body + '.R'),
                     OrientationID=('uint32', body + '.Q'), InputHide='GfxF22Msl%dNotGone.Output' % m['k']))
        for i, (d, size, bright, col) in enumerate(PLUME):
            p = tuple(a - b * d for a, b in zip(m['tail'], ax))
            gfx.append(o('graphics_pointlight', '%sPlume%d' % (n, i), PositionID=('uint32', body + '.R'),
                         OrientationID=('uint32', body + '.Q'), R0=vec(p), X0=vec(tuple(-a for a in ax)),
                         Color=('tmvector3d', ' %.2f %.2f %.2f 1.0 ' % col), Brightness=bright, Size=size,
                         ConeCenter=0.0, ConeCutoff=-1.0, InputModulation='GfxF22Msl%dBurn.Output' % m['k']))
        # the launch sound at the motor's ignition (make_launch_sound.py; the larger AIM-120 motor a little lower, the
        # AIM-9X's higher - one recording, 2026-11-25: alike they sounded the same): outside at the missile itself - it goes away
        # with it, the game adds distance and Doppler; inside muffled, at the bay (the cockpit's impression of it).
        # Only once the converter has made the .tsb (failures_f22._have_sound: a configs-only build must not point at
        # a missing file)
        if sound:
            src = 'GfxOutF22Msl%dLit.Output' % m['k']
            snd.append(o('soundinput', n + 'LitIn', InputID=('uint32', src)))
            if not any(x.name == 'F22LaunchInVolumeIn' for x in snd):
                snd.append(o('soundinput', 'F22LaunchInVolumeIn', InputID=('uint32', 'GfxOutF22LaunchInVolume.Output')))
            # (the game's flags: External false = heard only inside, Internal false = only outside, as the engine
            # loops of engine_sound_f22; External true, the first try, played the long outside layer in the cockpit too)
            for tag, wav, flag, pos, vol, rng in (
                    ('Out', 'missile_launch.wav', 'Internal', body, 1.0, 3000.0),
                    ('In', 'missile_launch_int.wav', 'External', 'Fuselage', 'F22LaunchInVolumeIn.Output', 50.0)):
                snd.append(o('soundsingle', '%sLaunch%s' % (n, tag), PositionID=('uint32', pos + '.R'),
                             OrientationID=('uint32', pos + '.Q'), VelocityID=('uint32', pos + '.V'),
                             InputTrigger=n + 'LitIn.Output', InputVolume=vol if isinstance(vol, str) else '%.2f' % vol, InputPitch='%.2f' % kd['pitch'],
                             SoundFile=wav,
                             Threshold=0.9, Direction=('uint32', '1'), R0=vec(m['tail']), Radius=3.0,
                             Range=('float64', '%.1f' % rng), **{flag: ('bool', 'false')}))
        # the rest of its mass at its station while it is held (loads_f22): the light body's share is its own
        want = o('product', 'F22MassMsl%dWant' % m['k'], Inputs=' %s.Output %.1f ' % (n + 'Held', kd['mass'] - kd['mass'] * r))
        dyn.append(want)
        dyn += loads_f22.station_tank(obj, holder, 'Msl%d' % m['k'], 'Fuselage', c, 'F22MassMsl%dWant.Output' % m['k'])
    return dyn, gfx, snd
