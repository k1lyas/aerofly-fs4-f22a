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
# a released missile stopped and hidden (2026-11-27): this long after the release, or this near the ground / water
STOP_AFTER_S, STOP_AGL_M = 10.0, 15.0
TEST_STOP = __import__('os').environ.get('F22_TEST') == 'mslstop'
# F22_TEST=mslrec - the missile recorder (2026-11-28): the missiles in the base aircraft (not the stores add-on) with the
# MSL TEST page on the MFD (mfd_f22.msl_test_page: their sensors and forces next to the aircraft's, filmed and read back
# by tools/msl_video.py); stopped at the release time, but left in sight
TEST_REC = __import__('os').environ.get('F22_TEST') == 'mslrec'
TEST_SHOW = TEST_STOP or TEST_REC
CLIMB_T_S = 0.1              # s, the climb filter's time constant
CLIMB_HIDDEN = 2.0           # m/s the stopped missile climbs (hidden; never sinks back to the ground)
SPIN_TAU_S = 0.4             # s, the spin damper's time constant (a finned missile settles its rates about as fast)
SPIN_RATE_MAX = 3.0          # rad/s the damper is sized for
# the rate gyro's sign: the IRS rates are right-handed about the body axes (x forward, y left, z up) - a nose-down pitch
# rate and a nose-left yaw rate are positive (MSL TEST recording 4, 2026-11-28: the aircraft's pitch rose 7 -> 21 deg
# with Q -6..-9 deg/s). With +1 (aviation signs, the first guess) the damper drove every missile's spin up, doubling
# every quarter second to 16000 deg/s, and the flight paused
SPIN_SIGN = -1.0
SPIN_GUARD = 1.5             # x SPIN_RATE_MAX: above it the damper lets go (it must never be what spins a missile up)
CLIMB_LOW, LOW_GUARD_M = 20.0, 150.0   # m/s it climbs while closer than this to the ground or water (radar altitude)
STOP_LEAD_S = 0.6            # s of its closing speed with the ground added to STOP_AGL_M (twice the brakes' tau)
STOP_TAU_S = 0.3             # the brakes' time constant (force = mass / tau x speed; ~1 s to a stand from Mach 2)
STOP_V_MAX = 900.0           # m/s the brakes are sized for (and the climb rate clamped to)
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
        o('integral_clamped', n + 'Age', Input=n + 'Gone.Output', Range=' 0.0 %.1f ' % (3600.0 if TEST_REC else 60.0),
          Value=0.0)
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
        # (cut at the stop: launched at the ground and stopped near it while still burning, it must not be driven on)
        dyn.append(o('product', n + 'ThrustLive', Inputs=' %sThrust.Output %sFlying.Output ' % (n, n)))
        dyn.append(o('force', n + 'Motor', Body=body, R0=vec(c), X0=vec((1.0, 0.0, 0.0)), MaxForce=kd['thrust'] * r,
                     Control=n + 'ThrustLive.Output'))
        # holding its line: the lift a real missile makes under its guidance (not simulated) - its weight, straight up.
        # Without it the missiles sank ~170 m under the aircraft's path in a burn (2026-11-25). Up in its own axes it
        # held only a missile launched wings level: launched in a bank or climb its weight was carried by cos(bank) x
        # cos(pitch) of it, the spent missile sank away, into the ground, onto water - and the game, which counts any
        # body of the aircraft touching water a crash, paused the flight again and again after a launch (reported
        # 2026-11-27 and seen in our own launch tests). Now the world's up in the missile's axes from its own attitude
        # (an attitude_indicator on its body; x forward, y left, z up, pitch + nose up, bank + right wing down, as
        # Auto-GCAS reads them): up = (sin P, cos P sin B, cos P cos B), each component a pair of forces (+ / -)
        W = kd['mass'] * 9.81 * r
        mass = kd['mass'] * r
        att = n + 'Att'
        dyn.append(o('attitude_indicator', att, Body=body))
        # Stopped in the air (2026-11-27: not flying on for ever, not into the ground): STOP_AFTER_S after the
        # release (the motor out at 6.4 s, the missile 5 - 8 km away, unseen) or within STOP_AGL_M of the ground or
        # water (by its own radar altimeter: launched at the ground it vanishes there, as a hit - no pull-up), it is
        # hidden, its motor cut; its weight stays held up and a brake on its climb (the pressure altitude's rate) sets a
        # slow climb - it never comes down. Horizontally it coasts on, unseen (see 'No horizontal brake' below)
        dyn.append(o('radar_altimeter', n + 'RadAlt', Body=body, R0=vec(c), Calibration=('float64', '0.0')))
        dyn.append(o('pitot_tube', n + 'Pitot', Body=body))
        # (an inertial reference on its body for the height above the sea, 2026-11-27: with its climb in the brakes a
        # level launch paused the flight 8 s after the stop - it may not measure the body it is put on; out again)
        # climb rate from the radar altitude by our own first-order filter (climb = (alt - lag) / T, lag the integral
        # of the climb): its sign and lag are known. With the engine's differentiator a stopped missile ran away
        # downwards within a second (F22_TEST=mslstop, 2026-11-27) - the brake pushed the way it sank
        # (2026-11-28, MSL TEST recording: on the radar altitude the climb was the terrain's - over hilly ground it swung
        # +-30 m/s at 450 m/s, the brake threw the missile up and down with up to 11 x its weight. Now the pressure
        # altitude from its own pitot's static port: the missile's own height, terrain does not enter)
        dyn.append(o('altimeter', n + 'BaroAlt', StaticPressure=n + 'Pitot.StaticPressure', AltimeterSetting='101325.0'))
        dyn.append(o('mixlinear', n + 'Climb', Input0=n + 'BaroAlt.PressureAltitude', Input1=n + 'AltLag.Output',
                     Weight0=1.0 / CLIMB_T_S, Weight1=-1.0 / CLIMB_T_S))
        dyn.append(o('integral_clamped', n + 'AltLag', Input=n + 'Climb.Output', Range=' -1000.0 100000.0 ', Value=0.0))
        # near the ground by its closing speed too: the brakes take ~tau x speed to stop it (~100 m at 300 m/s) - with
        # a flat 15 m a missile launched at the ground went in before it stopped and paused the flight (in-game
        # 2026-11-27, launched level it never came near): stopped STOP_LEAD_S of its closing speed + STOP_AGL_M up
        dyn.append(o('linear', n + 'SinkRaw', Input=n + 'Climb.Output', Scaling=-1.0))
        dyn.append(o('clamp', n + 'Sink', Input=n + 'SinkRaw.Output', Range=' 0.0 %.1f ' % STOP_V_MAX))
        dyn.append(o('mixlinear', n + 'LowAt', Input0=n + 'Sink.Output', Input1='1.0', Weight0=STOP_LEAD_S, Weight1=STOP_AGL_M))
        dyn.append(o('logic_greater', n + 'Low', Input0=n + 'LowAt.Output', Input1=n + 'RadAlt.Output'))
        dyn.append(o('logic_greater', n + 'Old', Input0=n + 'Age.Output', Input1='%.1f' % (2.0 if TEST_STOP else STOP_AFTER_S)))
        dyn.append(o('logic_or', n + 'StopNow', Inputs=' %sLow.Output %sOld.Output ' % (n, n)))
        dyn.append(o('logic_and', n + 'StopGo', Inputs=' %sStopNow.Output %sGone.Output ' % (n, n)))
        dyn.append(o('mixlinear', n + 'StopRate', Input0=n + 'StopGo.Output', Input1='0.0', Weight0=50.0, Weight1=0.0))
        dyn.append(o('integral_clamped', n + 'StopLatch', Input=n + 'StopRate.Output', Range=' 0.0 1.0 ', Value=0.0))
        dyn.append(o('logic_greater', n + 'Stopped', Input0=n + 'StopLatch.Output', Input1='0.5'))
        dyn.append(o('logic_invert', n + 'Flying', Input=n + 'Stopped.Output'))
        # once stopped it climbs slowly (CLIMB_HIDDEN), faster near the ground or water (CLIMB_LOW under LOW_GUARD_M of
        # radar altitude - a hill in its drift): the brake pushes the climb to that
        dyn.append(o('logic_greater', n + 'LowGuard', Input0='%.1f' % LOW_GUARD_M, Input1=n + 'RadAlt.Output'))
        dyn.append(o('mixlinear', n + 'ClimbTarget', Input0=n + 'LowGuard.Output', Input1='1.0',
                     Weight0=CLIMB_LOW - CLIMB_HIDDEN, Weight1=CLIMB_HIDDEN))
        dyn.append(o('mixlinear', n + 'ClimbError', Input0=n + 'ClimbTarget.Output', Input1=n + 'Climb.Output',
                     Weight0=1.0, Weight1=-1.0))
        dyn.append(o('clamp', n + 'ClimbClamped', Input=n + 'ClimbError.Output', Range=' %.1f %.1f ' % (-STOP_V_MAX, STOP_V_MAX)))
        dyn.append(o('product', n + 'ClimbBrake', Inputs=' %sStopped.Output %sClimbClamped.Output %.6f ' % (n, n, mass / STOP_TAU_S)))
        # the force up: its weight, and the brake on its climb / sink once stopped
        dyn.append(o('mixlinear', n + 'UpForce', Input0=n + 'Hold.Output', Input1=n + 'ClimbBrake.Output', Weight0=1.0, Weight1=1.0))
        # (the tables run -2 pi .. 2 pi: whichever range the engine gives an angle in - -pi..pi, 0..2pi, -pi/2..pi/2 - it
        # reads right. Over 0..2pi only, a pitch given as -0.3 rad read sin 0: a nose-down missile got no backward share
        # of the force up, and the climb brake's push leaked along its axis - in-game 2026-11-27 a stopped missile bobbed
        # up and down, then shot off horizontally and the flight paused)
        angles = [-2 * math.pi + i * math.pi / 24 for i in range(97)]
        # (a force's Control reads as a share of its MaxForce, clipped to 1 - in-game 2026-11-27: with MaxForce raised
        # for the brakes and Control left in newtons, every launch put 15 kN on the 5 kg missile at once and the flight
        # paused as a crash. Before, Control and MaxForce were always equal and both readings agreed)
        brake_max = mass * STOP_V_MAX / STOP_TAU_S
        up_max = W + brake_max                  # weight + the climb brake, the most any body axis can get
        # No horizontal brake once stopped (final design, 2026-11-28, after MSL TEST recordings 1 - 10): every horizontal
        # brake tried leaned on a sensor whose direction folds - the pitot's angle of attack and sideslip and the IRS's
        # drift angle all stay within +-90 deg, so a motion backwards reads as forwards and the brake, once it had
        # overshot through nought (cross wind, a near-vertical dive turned round by the climb brake, a lagging IRS
        # speed), pushed the missile on: 6 -> 756 m/s and a paused flight. Hidden, its horizontal motion is nobody's
        # business: it coasts on, its weight held and its climb set (both proven in every recording since the 2nd),
        # passing through hills harmlessly (no collision geometry - recording 8: 168 m into a slope, no pause) and
        # kept off the water by the climb. The motor is cut at the stop (below)
        irs = n + 'Irs'                         # its rate gyro (the spin damper's input)
        dyn.append(o('inertial_reference_system', irs, Body=body))
        # Spin damper (2026-11-28, MSL TEST recording 3: an AIM-9X released while the aircraft pulled out of a dive at
        # ~20 deg/s kept that rate for good and tumbled over and over - the body has no aerodynamics to damp it, a
        # real missile's fins and autopilot settle it within a fraction of a second). Its pitch and yaw rates from a
        # rate gyro on its own body (inertial_reference_system: OutputQRate / OutputRRate, rad/s), a couple against
        # each - equal and opposite forces at its nose and tail. Only in its visible flight (released, not stopped):
        # on the launcher it would fight the aircraft, hidden it does not matter
        # (on from the release for good, also once stopped - MSL TEST recording 9: two AIM-120 kept a roll of 10 - 13
        # deg/s after the stop, and as the bank went through 90 deg the horizontal brake's sideways part turned over)
        dyn.append(o('linear', n + 'DampOn', Input=n + 'Gone.Output', Scaling=1.0))
        lx, ly, lz = kd['inertia']
        arm = 0.4 * L                                   # nose and tail force points, ahead of / behind the centre
        nose, tail = (c[0] + arm, c[1], c[2]), (c[0] - arm, c[1], c[2])
        # (rate, inertia about that axis (a box of the InertiaLength sides), the nose force's way for a positive
        # SPIN_SIGN x rate: nose up -> push the nose down (-z); nose right -> push the nose left (+y; y points left))
        # roll too (P, + right wing down - right-handed about x as Q and R): a couple of up / down forces at two points
        # ROLL_ARM left and right of the axis (points of the rigid body, need not be on its skin)
        roll_arm = 0.5
        left, right = (c[0], c[1] + roll_arm, c[2]), (c[0], c[1] - roll_arm, c[2])
        for tag, rate, inertia, way, pts, arm_ in (
                ('Q', irs + '.OutputQRate', mass * (lx * lx + lz * lz) / 12.0, (0.0, 0.0, -1.0), (nose, tail), arm),
                ('R', irs + '.OutputRRate', mass * (lx * lx + ly * ly) / 12.0, (0.0, 1.0, 0.0), (nose, tail), arm),
                ('P', irs + '.OutputPRate', mass * (ly * ly + lz * lz) / 12.0, (0.0, 0.0, 1.0), (left, right), roll_arm)):
            f_per_rate = inertia / SPIN_TAU_S / (2.0 * arm_)       # N per rad/s on each point (a couple: 2 arm)
            f_max = f_per_rate * SPIN_RATE_MAX
            # (a guard: off above SPIN_GUARD x the rate it is sized for - a damper of the wrong sign stops there)
            dyn.append(o('product', n + 'Spin%sSq' % tag, Inputs=' %s %s ' % (rate, rate)))
            dyn.append(o('logic_greater', n + 'Spin%sSane' % tag, Input0='%.4f' % (SPIN_GUARD * SPIN_RATE_MAX) ** 2,
                         Input1=n + 'Spin%sSq.Output' % tag))
            dyn.append(o('product', n + 'Spin' + tag, Inputs=' %sDampOn.Output %sSpin%sSane.Output %s %.10f '
                         % (n, n, tag, rate, SPIN_SIGN * f_per_rate / f_max)))
            dyn.append(o('maximum', n + 'Spin%sPos' % tag, Inputs=' %sSpin%s.Output 0.0 ' % (n, tag)))
            dyn.append(o('linear', n + 'Spin%sNegRaw' % tag, Input=n + 'Spin%s.Output' % tag, Scaling=-1.0))
            dyn.append(o('maximum', n + 'Spin%sNeg' % tag, Inputs=' %sSpin%sNegRaw.Output 0.0 ' % (n, tag)))
            for at_, k in ((pts[0], 1.0), (pts[1], -1.0)):
                for sgn, sh in ((1.0, 'Pos'), (-1.0, 'Neg')):
                    d = tuple(k * sgn * v for v in way)
                    dyn.append(o('force', n + 'Spin%s%s%s' % (tag, 'A' if k > 0 else 'B', sh), Body=body,
                                 R0=vec(at_), X0=vec(d), MaxForce=f_max, Control=n + 'Spin%s%s.Output' % (tag, sh)))
        # hidden once stopped: the missile and its plume
        # (F22_TEST=mslstop: stopped 2 s after the release and left in sight - to watch what a stopped missile does)
        dyn.append(o('logic_or', n + 'FreeHidden', Inputs=(' %sNotGone.Output ' % n) if TEST_SHOW else
                     ' %sNotGone.Output %sStopped.Output ' % (n, n)))
        dyn.append(o('logic_and', n + 'BurnShown', Inputs=' %sBurn.Output %sFlying.Output ' % (n, n)))
        dyn.append(o('output', 'GfxOut%sFreeHidden' % n, Input=n + 'FreeHidden.Output'))
        dyn.append(o('output', 'GfxOut%sBurnShown' % n, Input=n + 'BurnShown.Output'))
        for fn, f in (('Sin', math.sin), ('Cos', math.cos)):        # (over -2 pi .. 2 pi, see angles)
            table = ' %s ' % ' '.join('(%.5f %.5f)' % (a, f(a)) for a in angles)
            dyn.append(o('linear_interpolation', n + 'Pitch' + fn, Input=att + '.PitchAngle', Map=table))
            dyn.append(o('linear_interpolation', n + 'Bank' + fn, Input=att + '.BankAngle', Map=table))
        # (constants in an Inputs list in plain decimals: '6.64494e-05' was read as object '6' - STOP, 2026-11-27)
        comps = {'X': ' %sUpForce.Output %sPitchSin.Output %.10f ' % (n, n, 1.0 / up_max),
                 'Y': ' %sUpForce.Output %sPitchCos.Output %sBankSin.Output %.10f ' % (n, n, n, 1.0 / up_max),
                 'Z': ' %sUpForce.Output %sPitchCos.Output %sBankCos.Output %.10f ' % (n, n, n, 1.0 / up_max)}
        axes = {'X': (1.0, 0.0, 0.0), 'Y': (0.0, 1.0, 0.0), 'Z': (0.0, 0.0, 1.0)}
        for comp, ins in comps.items():         # (not `ax`: the missile's axis below)
            dyn.append(o('product', n + 'Up' + comp, Inputs=ins))
            dyn.append(o('maximum', n + 'Up%sPos' % comp, Inputs=' %sUp%s.Output 0.0 ' % (n, comp)))
            dyn.append(o('linear', n + 'Up%sNegRaw' % comp, Input=n + 'Up%s.Output' % comp, Scaling=-1.0))
            dyn.append(o('maximum', n + 'Up%sNeg' % comp, Inputs=' %sUp%sNegRaw.Output 0.0 ' % (n, comp)))
            for sgn, tag in ((1.0, 'Pos'), (-1.0, 'Neg')):
                dyn.append(o('force', n + 'Lift%s%s' % (comp, tag), Body=body, R0=vec(c),
                             X0=vec([sgn * v for v in axes[comp]]), MaxForce=up_max,
                             Control=n + 'Up%s%s.Output' % (comp, tag)))
        if TEST_REC:        # for the MSL TEST page: its state (0 flying, 1 stopped) and the force up / weight
            dyn.append(o('mixlinear', n + 'DbgState', Input0=n + 'Stopped.Output', Input1='0.0', Weight0=1.0, Weight1=0.0))
            dyn.append(o('mixlinear', n + 'DbgUpW', Input0=n + 'UpForce.Output', Input1='0.0', Weight0=1.0 / W, Weight1=0.0))
        # graphics: the copy on its own body once released, the plume while the motor burns
        gfx.append(o('graphics_input', 'GfxF22Msl%dNotGone' % m['k'], InputID=('uint32', 'GfxOut%sFreeHidden.Output' % n)))
        gfx.append(o('graphics_input', 'GfxF22Msl%dBurn' % m['k'], InputID=('uint32', 'GfxOut%sBurnShown.Output' % n)))
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
