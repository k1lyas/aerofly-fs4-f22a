"""F-22 structural breakage (block 2 of docs/reference/FAILURES.md).

Wings (always on): each wing body (the donor's, with its fuel tank) hangs on a breakable jointlinear at y 2.6 m, as the
Swift's wings (stock swift.tmd: ForceMax / TorqueMax), with stiff springs. Only the outer console tears off: the donor
had the whole wing's aerodynamics on that body, from the strake at y 0.6 m out; split 2026-11-10 at the joint - the
strake and inner wing (y 0.6 - 2.6) go onto the fuselage as their own aerowing, AspectRatioMultiplier 4 on all four
pieces (SDK wiki: the number of aerowings that make one wing, as the Corsair's folding wings; was 2). Breaks at 13.5 g: the F-22's +9 g limit x 1.5, the usual ultimate factor (estimate:
its real strength is not public). The FCS holds 9 g, so only DIRECT can get there. The wing is still drawn on the
fuselage (block 3 draws the outer wing apart): nothing is seen to leave. The wings' collision hulls sit on the
fuselage (see apply): a torn console falls through the ground, the flight goes on to the aircraft's own impact.

Test 1 wingbreak (in-game 2026-11-09, Kt 6e6 on all axes): TorqueMax 150 kN m on the left wing broke it at ~3 g, so our wing bends its
joint with ~50 kN m per g (the inboard strake's lift works the other way about the joint: estimates had run 20 - 65);
the game then paused on a crash during the tumble (PEAK G 4.2). 13.5 g -> 675 kN m.

Mechanics tests, one per game launch, switched on by the environment for one build, off by the next normal build:

    F22_TEST=wingbreak ./build.sh configs      # test build into the game
    ./build.sh configs                          # back to normal
"""
import math
import os
import re

TEST = os.environ.get('F22_TEST', '')

TORQUE_PER_G = 56000.0              # N m per g at the joint, console only: test 2 (consolebreak, 2026-11-10) broke
                                    # 200 kN m at PEAK G 3.5-3.6 (estimate had been 65; test 1, with the strake's lift
                                    # still on the wing body pulling the other way, 50)
ULTIMATE_G = 13.5                   # 9 g x 1.5
WING_TORQUE_MAX = TORQUE_PER_G * ULTIMATE_G
WING_FORCE_MAX = 5.0e6              # N: out of reach (the lift of one wing at 13.5 g is well under it): the moment breaks it
WINGBREAK_TORQUE_MAX = 150000.0     # test 1: broke at ~3 g
CONSOLEBREAK_TORQUE_MAX = 200000.0  # test 2: broke at 3.5-3.6 g
# Fins. Test 3 finbreak (in-game 2026-11-10): the left fin at 25 kN m did not break with full pedal (keyboard, held)
# up to 600+ kt - the F/A-18 laws wash the rudder out with speed, so the laws keep the fins far from their strength,
# as on real fighters. What breaks fins is flutter: over the speed limit the rudder buzzes beyond what its actuator
# holds (below). Threshold 100 kN m: four times the shown-safe 25; full rudder at 750 kt would load ~200 (estimate:
# ~5 m2, lift coefficient ~0.5, 1.2 m arm)
FINBREAK_TORQUE_MAX = 25000.0
FIN_TORQUE_MAX = 250000.0           # was 100 kN m: in-game 2026-11-10 a right fin went at 551 KCAS, 2.3 g, sideslip -8 deg
                                    # (first-loss snapshot) in a fast rolling pull with the laws on - sideslip loads a fin far
                                    # more than the pedal did (test 3: under 25 kN m at 600 kt); the forced rudder buzz past
                                    # ~820 kt loads it ~350 (estimate), so flutter still tears it off
# fin springs, ~13 Hz - as the wings' twist mode, which flies steady. Tried: 1e7 (~24 Hz on the fin's ~440 kg m2 about
# its root) tore both fins off at the spawn, standing, 1 kt and 1 g (in-game 2026-11-10: too fast for the game's
# physics step on a light body - the explicit spring rings itself apart); 1.1e6 (~8 Hz) twisted under the fin's own
# lift (its aerodynamic centre ~0.9 m ahead of the joint: ~0.4e6 N m / rad of negative stiffness at 550 kt, ~1e6 near
# 800) - the loads grew by half and more, it shook from ~760 kt and lost a fin at 551 kt in a rolling pull. 3e6 keeps
# three times that margin; 30 % of critical damping
FIN_KT, FIN_DT = 3.0e6, 2.2e4
FIN_KF, FIN_DF = 2.0e6, 1.3e4
# flutter (COND on, failures_f22.py): over the speed limit - 800 KCAS, the F-15's and F-16's (the F-22's is not
# public; 750 at first, 2026-11-10: the user flies the mod at 900-1000 kt low, so the onset moved up to the real
# fighters' limit) - the rudders start to buzz, 6 Hz, growing over ~2.5 s, past what the actuators hold (straight
# into the fins' aerodynamics, not through the servos), heard and felt as the buffet; held, the load tears a fin off.
# It builds above ~820 kt and dies out below
FLUTTER_KCAS = (800.0, 850.0)
FLUTTER_RAD = 0.5                   # rudder swing at full flutter
# stiffness: bending (about x) 2 deg at 9 g, twist (about y, z) ~1 deg at 9 g - test 1 had 6e6 on all three, which at
# 9 g would twist the wing ~4 deg nose up (the lift acts ~1 m ahead of the joint) and change the handling. With the
# wing's ~4400 kg m^2 about the joint: ~8 Hz bending, ~13 Hz twist; 18 Hz in translation (1500 kg)
K_TORQUE = {'x': 1.2e7, 'y': 3.0e7, 'z': 3.0e7}    # N m / rad
K_FORCE = 2.0e7                     # N / m
D_TORQUE = 1.0e5
D_FORCE = 1.0e5


def breakable(tmd, joint, torque_max, force_max, k_force=None, d_force=None, k_torque=None, d_torque=None):
    """A multibody_joint made a breakable jointlinear (same place, the Swift's fields)."""
    k_force = K_FORCE if k_force is None else k_force
    d_force = D_FORCE if d_force is None else d_force
    k_torque = K_TORQUE if k_torque is None else k_torque
    d_torque = D_TORQUE if d_torque is None else d_torque
    assert joint.type == 'multibody_joint', joint.type
    body0, body1, r0 = joint.get('Body0'), joint.get('Body1'), joint.get('R0')
    joint.type = 'jointlinear'
    joint.children = [tmd.Node('string8', 'Body0', body0), tmd.Node('string8', 'Body1', body1), tmd.Node('tmvector3d', 'R0', r0)]
    for prefix, k, d in (('f', k_force, d_force), ('t', k_torque, d_torque)):
        for axis in 'xyz':
            joint.children.append(tmd.Node('float64', 'K%s%s' % (prefix, axis), '%.6g' % (k[axis] if isinstance(k, dict) else k)))
        for axis in 'xyz':
            joint.children.append(tmd.Node('float64', 'D%s%s' % (prefix, axis), '%.6g' % d))
    joint.children.append(tmd.Node('float64', 'ForceMax', '%.6g' % force_max))
    joint.children.append(tmd.Node('float64', 'TorqueMax', '%.6g' % torque_max))


SPLIT_Y = 2.6                       # m, the joint


def split_wings(dyn):
    """Each wing's aerowing2 cut at the joint: stations with |y| <= SPLIT_Y to a new aerowing on the fuselage, the rest
    (the console) stays on the wing body under its old name (the stabilators' downwash reads it); the station at the
    joint goes into both. Station order (right to left) and each station's flap / slat inputs are kept."""
    for side in ('Left', 'Right'):
        wing = next(o for o in dyn.children if o.name == side + 'WingAero')
        assert wing.type == 'aerowing2' and wing.get('Body') == side + 'Wing', wing.name
        inner = wing.clone()
        inner.name = side + 'WingInnerAero'
        inner.set('Body', 'Fuselage', 'string8')
        for w, keep in ((wing, lambda y: abs(y) >= SPLIT_Y - 1e-6), (inner, lambda y: abs(y) <= SPLIT_Y + 1e-6)):
            st = w.find('Stations')
            st.children = [c for c in st.children if keep(float(c.get('Y')))]
            assert len(st.children) >= 2, (w.name, len(st.children))
            w.set('AspectRatioMultiplier', '4.0', 'float64')
        dyn.children.insert(dyn.children.index(wing), inner)


def apply(ns):
    tmd, dyn = ns['tmd'], ns['dyn']
    joint = lambda name: next(o for o in dyn.children if o.name == name)
    if TEST != 'nosplit':                   # nosplit: the donor's whole-wing aerodynamics, for the A/B handling check
        split_wings(dyn)
    for side in ('Left', 'Right'):            # the side views ride on the wing bodies (donor): they fell with a torn wing
        cam = joint('Camera%sFuselageView' % side)
        assert cam.get('Body') == side + 'Wing', cam.name
        cam.set('Body', 'Fuselage', 'string8')
    left = {'wingbreak': WINGBREAK_TORQUE_MAX, 'consolebreak': CONSOLEBREAK_TORQUE_MAX}.get(TEST, WING_TORQUE_MAX)
    breakable(tmd, joint('JointFuselageLeftWing'), left, WING_FORCE_MAX)
    breakable(tmd, joint('JointFuselageRightWing'), WING_TORQUE_MAX, WING_FORCE_MAX)
    # the wings' collision hulls. A torn-off wing glides down by itself and ended the flight when IT touched the ground,
    # the aircraft still in the air (in-game 2026-11-10) - with the donor's InstantCrash true, then with it false, then
    # also with CrashOnContact false (SDK wiki; set by no stock aircraft): every time. So any hard ground contact of an
    # aircraft body counts as the crash. The hulls go onto the fuselage body (same geometry, same place while the wing
    # is on): the attached wing still meets the ground (a scrape; a hard hit crashes, as the fuselage's own hull), the
    # torn one falls without a hull - it is not drawn apart yet anyway (block 3) - and the flight ends on the
    # aircraft's own impact
    for side in ('Left', 'Right'):
        hull = joint('Collision%sWing' % side)
        assert hull.type == 'collisionhull' and hull.get('Body') == side + 'Wing', hull.name
        hull.set('Body', 'Fuselage', 'string8')
        flag = hull.find('InstantCrash')
        assert flag is not None and flag.value.strip() == 'true', hull.name
        flag.value = 'false'
    print('wings break at %.0f / %.0f kN m (%.1f g at %.0f kN m per g)%s' % (
        left / 1e3, WING_TORQUE_MAX / 1e3, ULTIMATE_G, TORQUE_PER_G / 1e3, ' - TEST ' + TEST if TEST else ''))
    # fins: breakable, soft, flutter under COND. A yaw-away seen on 2026-11-10 stayed with the donor's fins too and went
    # with a game restart (configs had been copied with the game running); the soft fins with flutter then flew as
    # before at low speed, shook from ~760 kt and lost a fin past ~820 kt (in-game 2026-11-10)
    fins(ns, joint)
    tyre_hubs(ns, joint)
    gear_shear(ns, joint)
    tank_release(ns, joint)
    fuel_wing_loss(ns, joint)
    if TEST not in ('', 'wingbreak', 'consolebreak', 'nosplit', 'finbreak', 'fins', 'flutter'):
        raise SystemExit('F22_TEST=%s: no such test (wingbreak, consolebreak, nosplit, finbreak, fins, flutter)' % TEST)


# burst tyres sit down on their rims (block 3, 2026-11-11). The game's wheel has no input for its pressure or radius,
# so each wheel hull moves onto a small hub body on a locked sliding joint (kinematic, as the donor's wheel-tilt joint):
# a burst raises the hull against its strut by the tyre's height (Radius - RimRadius: main 0.185 m, nose 0.132 m), so
# the strut - and with it the drawn rim - comes down to the rim radius over the ground; the drawn wheel swaps for its
# squashed copy (ac_f22._burst_tyres, breakage graphics). The hub's mass is taken from the body it hangs on
TYRE_HUBS = {'L': ('LeftGearWheelAssembly', ('LeftWheelHull',), 20.0),
             'R': ('RightGearWheelAssembly', ('RightWheelHull',), 20.0),
             'N': ('NoseGearLower', ('LeftFrontWheelHull', 'RightFrontWheelHull'), 15.0)}
TYRE_DROP_RATE = 2.0                 # m/s: flat in 0.09 s, a sheared leg's wheel out of the way in 0.5 s (5.0 jolted on RST)


def tyre_hubs(ns, joint):
    obj, dyn = ns['obj'], ns['dyn']
    for key, (parent, hulls, mass) in TYRE_HUBS.items():
        pb = joint(parent)
        assert pb.type == 'rigidbody', parent
        hn = [joint(h) for h in hulls]
        assert all(h.type == 'wheel' and h.get('Body') == parent for h in hn), hulls
        drop = float(hn[0].get('Radius')) - float(hn[0].get('RimRadius'))
        r0 = [sum(float(h.get('R0').split()[i]) for h in hn) / len(hn) for i in range(3)]
        # (its mass from the fuselage, not from the gear body it hangs on: lightened gear bodies on the oleo's 1.9e7 N/m
        # limit spring ring far past what the game's step holds - a 1710 ft/min touchdown read 236 g and bounced 45 ft,
        # in-game 2026-11-13)
        fus = joint('Fuselage')
        fus.set('Mass', '%g' % (float(fus.get('Mass')) - mass), 'float64')
        hub = 'F22WheelHub' + key
        # body, joint and wheels in a row, as the donor lists its gear (inserted before the first wheel)
        at = hn[0]
        obj(dyn, 'product', 'F22TyreBurstDrop' + key, at, Inputs=' F22TyreBurst%s.Output %.4f ' % (key, drop))
        obj(dyn, 'mixlinear', 'F22TyreDropCmd' + key, at, Input0='F22TyreBurstDrop%s.Output' % key,
            Input1='F22Shear%s.Output' % key, Weight0=1.0, Weight1=SHEAR_LIFT)      # (gear_shear: the wheel goes up)
        obj(dyn, 'servoclassic', 'F22TyreDrop' + key, at, Input='F22TyreDropCmd%s.Output' % key, Speed=TYRE_DROP_RATE,
            P1=1.0)
        obj(dyn, 'rigidbody', hub, at, Mass=mass, InertiaLength=('tmvector3d', ' 0.3 0.3 0.3 '),
            R0=('tmvector3d', ' %.4f %.4f %.4f ' % tuple(r0)), B0=('tmmatrix3d', pb.get('B0')))
        # Type 1 slides along X0 (the nose strut's): the position is Body1's travel along +X0, up
        obj(dyn, 'multibody_joint', 'JointF22WheelHub' + key, at, Body0=parent, Body1=hub,
            R0=('tmvector3d', ' %.4f %.4f %.4f ' % tuple(r0)), X0=('tmvector3d', ' 0.0 0.0 1.0 '), Kp=0.0, Kd=0.0,
            InputPosition='F22TyreDrop%s.Output' % key, InputLock='1.0', Type=('uint32', '1'))
        for h in hn:
            h.set('Body', hub, 'string8')
    print('tyres: hubs %s (a burst tyre sits down on its rim)' % ', '.join(sorted(TYRE_HUBS)))


# sheared struts (block 3, 2026-11-11; failures_f22: over 20 ft/s at touchdown, nose under 4 x its load). The lower
# strut and the wheel are a debris body hanging from the wheel's parent (main: wheel assembly, nose: lower strut) on a
# chain of joints - three slides, yaw, pitch - locked while the leg holds (rigid: no spring in the load path) and all
# unlocked at the shear; stock aircraft drive InputLock the same way (F-15E gear locks, Concorde retract lock). Test
# 2026-11-11 (left wheel, the tyre burst as trigger): unlocked, the chain let it go as a free body (slid 1.2 m, turned
# over and over). It flew high and bounced higher: the 40 kg body had the aircraft's tyre (K 3.8e6: ~48 Hz on that
# mass, far past the ~13 Hz the game's step holds - each bounce added energy) and the tyre's compression under the
# aircraft (~1.8 kJ) at the release. So the debris rolls on a tyre of its own, soft for its mass (8 Hz, half damped),
# 2 cm under the real radius - it carries a few hundred newtons while the leg holds - and the aircraft's own wheel
# lifts 1 m into the airframe at the shear: nothing is left under the broken leg, the aircraft sits down on it.
# While locked the debris rides the burst-tyre drop (its tyre stays clear of the ground on a flat). Its mass comes out
# of the lower strut bodies: the unsprung mass stays as it was
SHEAR_GEAR = {'L': ('LeftGearWheelAssembly', ('LeftWheelHull',), 'LeftGearLower', 80.0),
              'R': ('RightGearWheelAssembly', ('RightWheelHull',), 'RightGearLower', 80.0),
              'N': ('NoseGearLower', ('LeftFrontWheelHull', 'RightFrontWheelHull'), 'NoseGearMiddle', 40.0)}
SHEAR_LIFT = 1.0                     # m the aircraft's wheel rises into the airframe at the shear
DEBRIS_HZ, DEBRIS_ZETA = 8.0, 0.5
SHEAR_CHAIN = [('X', 1, ' 1.0 0.0 0.0 '), ('Y', 1, ' 0.0 1.0 0.0 '), ('Z', 1, ' 0.0 0.0 1.0 '),
               ('Yaw', 0, ' 0.0 0.0 1.0 '), ('Pitch', 0, ' 0.0 1.0 0.0 ')]
LINK_MASS = 10.0                     # kg per chain link (2 and 5 kg: light bodies on the game's stiff joint springs blew up)
DEBRIS_BRAKE = 1.0                   # the debris wheel's brake, always full: locked (no spin, no gyroscope)


def gear_shear(ns, joint):
    obj, dyn = ns['obj'], ns['dyn']
    for key, (root, hulls, take_from, mass) in SHEAR_GEAR.items():
        hn = [joint(h) for h in hulls]
        hub = 'F22WheelHub' + key
        assert all(h.get('Body') == hub for h in hn), hulls
        assert joint('JointF22WheelHub' + key).get('Body0') == root, root
        r0 = ' %.4f %.4f %.4f ' % tuple(sum(float(h.get('R0').split()[i]) for h in hn) / len(hn) for i in range(3))
        # the debris and link masses come out of the fuselage (see tyre_hubs): the gear bodies keep theirs
        fus = joint('Fuselage')
        take = mass + LINK_MASS * (len(SHEAR_CHAIN) - 1)
        fus.set('Mass', '%g' % (float(fus.get('Mass')) - take), 'float64')
        at = hn[0]
        # the tyre's compression: its load over its stiffness (a wheel's 'Deformation' is a graphics ID only - read in
        # the dynamics it stopped the aircraft from loading: "property 'LeftWheelHull.Deformation' not found", STOP,
        # 2026-11-13)
        squash = []
        for h in hn:
            # (a weight field, not a constant in an Inputs list: '2.6e-07' there is read as object '2' - STOP again)
            obj(dyn, 'mixlinear', 'F22TyreSquash%s%s' % (key, h.name), at, Input0='%s.Load' % h.name,
                Input1='%s.Load' % h.name, Weight0=1.0 / float(h.get('K')), Weight1=0.0)
            squash.append('F22TyreSquash%s%s.Output' % (key, h.name))
        obj(dyn, 'maximum', 'F22TyreSquash' + key, at, Inputs=' %s 0.0 ' % ' '.join(squash))
        obj(dyn, 'mixlinear', 'F22DebrisHold' + key, at, Input0='F22TyreBurstDrop%s.Output' % key,
            Input1='F22TyreSquash%s.Output' % key, Weight0=1.0, Weight1=1.0)
        # the debris hangs in the aircraft's joint tree on a chain of joints - three slides, yaw, pitch - locked while
        # the leg holds, free at the shear; the Z slide follows the burst-tyre drop plus the aircraft tyre's
        # compression, so the debris tyre (2 cm smaller) carries next to nothing while the leg holds (held at the
        # tyre's own centre a hard touchdown pressed it into the ground and fired it metres up, 2026-11-13). Its wheel
        # is braked locked (DebrisWheel below): a sheared wheel and strut drag and tumble, and a wheel spinning at
        # landing speed is a gyroscope - every yaw of the debris made a large roll torque. History, 2026-11-15: with
        # roll locked to the aircraft (this chain) that torque reached the aircraft - it jerked, and the debris turned
        # with it about its old fixing; set free on a broken jointlinear (as the tanks) a wheel gets no ground contact
        # - they fell through the runway; with a third, free roll axis (a ball joint on a telescopic rod with 5 kg
        # links, then this chain with a soft roll) the spinning wheel precessed into the yaw-pitch-roll singularity
        # and the physics blew up - the aircraft vanished, three times. This chain, 10 kg links, is the one that held
        vec = lambda v: ('tmvector3d', ' %.4f %.4f %.4f ' % tuple(v))
        eye = ('tmmatrix3d', ' 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0 ')
        o = lambda type_, name, **f: obj(dyn, type_, name, at, **f)
        held = o('logic_greater', 'F22GearHeld' + key, Input0='0.5', Input1='F22Shear%s.Output' % key) and \
            'F22GearHeld%s.Output' % key
        # no roll axis: any roll of the debris against the aircraft blew the physics up, four times (2026-11-15) -
        # free (ball joint on a rod; a soft spring, roll last) and sprung in the middle with the wheel locked (no
        # gyroscope): the game does not stand a wheel tilting sideways against the aircraft's frame, it seems
        prev = root
        for n, (name, typ, axis) in enumerate(SHEAR_CHAIN):
            last = n == len(SHEAR_CHAIN) - 1
            body = 'F22GearDebris' + key if last else 'F22GearLink%s%s' % (name, key)
            o('rigidbody', body, Mass=mass if last else LINK_MASS, R0=('tmvector3d', r0), B0=eye,
              InertiaLength=vec([0.6, 0.6, 0.6] if last else [0.3, 0.3, 0.3]))
            o('multibody_joint', 'JointF22GearShear%s%s' % (name, key), Body0=prev, Body1=body, R0=('tmvector3d', r0),
              X0=('tmvector3d', axis), Kp=0.0, Kd=0.0, InputPosition='F22DebrisHold%s.Output' % key if name == 'Z' else '0.0',
              InputLock=held, Type=('uint32', str(typ)))
            prev = body
        h0 = hn[0]
        k = mass * (2 * math.pi * DEBRIS_HZ) ** 2
        obj(dyn, 'wheel', 'F22DebrisWheel' + key, at, Body='F22GearDebris' + key, R0=('tmvector3d', r0),
            Radius=float(h0.get('Radius')) - 0.02, Width=float(h0.get('Width')) * len(hn),
            RimRadius=float(h0.get('RimRadius')), Inflation=float(h0.get('Inflation')), K=k,
            D=2 * DEBRIS_ZETA * math.sqrt(k * mass), InputBrake='1.0', BrakeStrength=DEBRIS_BRAKE)
    print('gear shear: debris %s on joint chains (slides, yaw, pitch), wheel locked, free at the shear' % ', '.join(sorted(SHEAR_GEAR)))


# ferry tank jettison (2026-11-13, user: "check dropping the tanks - there is another way now, as with the surfaces").
# In October an unlocked tank slid along its joint and pulled the aircraft over: a joint never lets a body go, and a
# body's mass and drag cannot be switched off. A broken jointlinear does let go - a torn console falls on by itself
# with its mass and aerodynamics, through the ground without a hull, and the aircraft flies on (in-game 2026-11-10).
# A jointlinear breaks only on load (ForceMax is a number, not an input), so the tank is kicked off as a real pylon's
# ejector does it: tank -> jointlinear -> ejector rack -> locked slide on the fuselage. The rack follows its
# InputPosition kinematically (as the tyre hubs, in-game 2026-11-11); at the release it strokes EJECT_STROKE down at
# EJECT_SPEED - the tank's inertia stretches the jointlinear past TANK_FORCE_MAX within milliseconds, it breaks, the
# tank and its pylon (the F-22 drops both) fly free. (First build, 2026-11-13: worked in game - both tanks dropped,
# but straight down and alike: the fall below.) (A chain of free joints, as the sheared strut's, would not do: its links stay rigid in
# the aircraft's rotation, hundreds of metres out once the tank falls away.) The tank's hull rides a body of its own on
# a locked slide, lifted into the wing at the release: a falling hull would end the flight where it meets the ground.
# The release: EMER JETT (the cockpit button, Controls.EmergencyJettision), airborne and with DC essential power; also
# when the console under the pylon tears off. Latched - a jettisoned tank stays gone (as a torn console: a new flight
# from the menu brings it back; the game does not mend a broken joint)
# The fall (2026-11-13, user: the tanks dropped straight down, both alike - "as it must be by the laws of physics").
# What a dropped finless tank does: the ejector's stronger forward piston pitches it nose down (it must not pitch up
# into the wing); a body of revolution without fins is unstable in pitch and yaw (the Munk moment: the nose's
# cross-flow lift is ahead of the centre of gravity) - it turns away from the flow, goes broadside and tumbles end
# over end, the cross-flow drag damping the tumble to a steady rate while the drag slows it and gravity takes it.
# An empty tank (236 kg) does all of this quickly; a full one (2050 kg) falls heavier and turns slower. So:
#  - the tank body is the shell (tank and pylon, empty): its fuel hangs beside it on the aircraft as TANK_SLUGS
#    invisible slugs, each on its own rack, kicked off as the ferry fuel burns down past its share (and all that are
#    left at the jettison). A body's mass cannot change - the aircraft's mass now follows the ferry fuel in steps
#    of 453 kg a tank, and the shell falls as an empty tank. (A jettison with fuel in the tanks falls as empty too;
#    usual practice drops them empty - they feed first.) Slugs fall forever through the ground with drag of their own
#  - the shell hangs on its rack at the forward lug (TANK_LUG_AHEAD ahead of its centre of gravity): the kick there
#    pitches it nose down (~0.8 rad/s)
#  - make_f22.py: the shell's aerodynamics as a slender body - lift on the nose stations (TANK_NOSE_CL), drag along
#    and across the whole length (the wiki: the moment comes from the stations' place against the centre of gravity;
#    Cm 0.5 on the whole-length aerofuselage did not turn it, in-game 2026-11-13)
#  - ripple: the right tank 0.1 s after the left (fighters fire their stations in a sequence: one jolt at a time;
#    the F-22's interval is not public) and its cartridge 10 % weaker (cartridges spread): no mirror-image twins
TANK_SHELL = 236.0 - 10.0            # kg: the tank and pylon, empty, less the rack and the hull body (they stay)
TANK_SLUGS = 4
TANK_LUG_AHEAD = 0.6                 # m
# cross-flow lift of the nose (aerofuselage over the nose stations, to the full diameter): slender-body theory gives a
# normal force of ~2 alpha on the cross-section (0.57 m2) there; per the stations' planform (~1.6 m2): ~0.7. Its centre
# ~2 m ahead of the centre of gravity: at 300 kt ~27 kN m per radian on the shell's ~870 kg m2 - unstable at ~5.6 /s,
# it turns broadside within half a second and tumbles, the cross-flow drag of the whole length holding the rate
TANK_NOSE_CL = 0.7
# the shell's lugs hold what they were built for - the full tank at 13.5 g (2050 kg: 270 kN), as the pylon of a real
# tank: the empty shell does not come off in a tumble. (80 kN, a margin for the kick only, tore the intact side's
# tank off in the violent roll after a console loss - 226 kg 3 m out at ~10 rad/s, in-game 2026-11-13.) The kick's
# snap stretches the joint 0.3 m at once: 600 kN
TANK_FORCE_MAX = 2.7e5               # N
TANK_TORQUE_MAX = 2.0e5              # N m
TANK_KF, TANK_DF = 2.0e6, 4.0e3      # 211 kg: 15 Hz (stock Swift: its 77 kg wing on 1e6 - 18 Hz); 9 g: 1 cm
# about the lug: Ixx ~ 95, Iyy / Izz ~ 900-1000 kg m2 (a thin shell: InertiaLength 6.7 / 1.04 / 1.04) -> ~10-11 Hz
TANK_KT = {'x': 4.0e5, 'y': 5.0e6, 'z': 5.0e6}
TANK_DT = {'x': 1.2e3, 'y': 1.4e4, 'z': 1.4e4}
SLUG_KF, SLUG_DF = 2.5e6, 7.0e3      # 453 kg: 12 Hz
SLUG_KT, SLUG_DT = 3.0e5, 1.0e3      # its ~50-110 kg m2: ~8-12 Hz
SLUG_FORCE_MAX, SLUG_TORQUE_MAX = 7.0e4, 3.0e4      # 13.5 g x 453 kg = 60 kN
SLUG_DUE_S = 2.0                     # a share burnt for 2 s: its slug goes (not on a frame of the fuel count at the load)
# the kick, in two phases. Push: the rack strokes EJECT_STROKE at EJECT_SPEED (8 m/s, a cartridge's piston) - the tank
# is shoved through its joint at the forward lug, gains the separation speed and its nose-down pitch (~5 m/s,
# ~0.8 rad/s by the joint's strength over ~15 ms); a hard push breaks the joint on its own. Snap: EJECT_SNAP_S into
# the stroke the rack jumps EJECT_SNAP further at once (0.3 m x 2e6 = 600 kN) - the joint gives for certain, the tank
# leaving at the rack's speed. History (in-game 2026-11-13): the push alone (8 m/s) sometimes left the tanks hanging
# under the pylons - the rack's servo eases in, the light shell simply followed; a jump alone (50 m/s) broke the joint
# in its first step without passing any impulse: the tank left with no speed or pitch of its own, kept the aircraft's
# angle of attack, nose a little above the flow, and the finless shell's instability pitched it nose up and tail
# first. And a kick that did not break it is repeated (EJECT_PERIOD: down, up - the pull up loads it as well - and
# down) for EJECT_TRY_S, the shell's until it is seen apart (F22TankApart), a slug's (unseen) for the whole time; then
# the rack stays down
EJECT_STROKE, EJECT_SPEED = 0.25, 8.0
EJECT_SNAP, EJECT_SNAP_S = 0.30, 0.02
EJECT_SPREAD = {'L': 1.0, 'R': 0.9}  # cartridge
EJECT_PERIOD, EJECT_TRY_S = 0.6, 3.0
JETT_RIPPLE_S = 0.10                 # right after left
TANK_WING_DV, TANK_WING_SEP_S = 15.0, 0.15   # m/s, s: a console seen flying away - its tank goes with it
RACK_MASS, TANK_HULL_MASS = 5.0, 5.0       # kg (kinematic: its mass sets only its kick's jolt on the aircraft)
SLUG_RACK_MASS = 2.0
TANK_HULL_LIFT, TANK_HULL_RATE = 0.85, 2.0  # m up into the wing, m/s
TANK_APART_MPS, TANK_APART_S = 5.0, 0.2    # tank and rack this far apart in speed: off (the drawing, after a rewind)


def tank_release(ns, joint):
    """The base aircraft's part: the release latch per side (F22TankGone*) - the add-on's racks fire on it, the ferry
    fuel goes out of the count on it (fuel_wing_loss)."""
    obj, dyn, D = ns['obj'], ns['dyn'], ns['D']
    at = joint('F22TanksAttached')
    o = lambda type_, name, **f: obj(dyn, type_, name, at, **f) and name + '.Output'
    o('variable', 'F22JettReq', Value='0.0')
    air = o('logic_greater', 'F22JettAirborne', Input0='0.5', Input1='OnGroundSensor.Output')
    armed = o('product', 'F22JettArmed', Inputs=' %s DCBusEssentialOn.Output F22FerryTanks.Output ' % air)
    keep = o('maximum', 'F22JettKeep', Inputs=' F22JettReq.Output %s ' % armed)        # never back to 0
    o('event_value', 'F22JettPress', Input=keep, Events=' F22JettReq.Set ')
    btn = D['EmergencyJettisionButton']
    assert btn.type == 'input_button', btn.type
    btn.set('Events', ' %s F22JettPress.Trigger ' % btn.get('Events').strip(), 'string8')
    o('logic_confirm_delay', 'F22JettRight', Input='F22JettReq.Output', TimeUp=JETT_RIPPLE_S, TimeDown=0.0001,
      Threshold=0.5)
    for side, req in (('Left', 'F22JettReq.Output'), ('Right', 'F22JettRight.Output')):
        # its console flying away: the console and its reference body (fcs_status) apart in speed by over TANK_WING_DV
        # for TANK_WING_SEP_S. A torn console leaves at hundreds of m/s2 (15 m/s in well under 0.1 s); the intact one flexes in the violent roll
        # after the other's loss, a few m/s. Twice both tanks dropped with one console off (in-game 2026-11-13):
        # first the latch took any pulse of F22SepWing (4 m/s for 0.05 s), then F22SepWing held 0.3 s - its pulses
        # are held 0.2 s each and come in a row in that roll
        far = o('logic_greater', 'F22TankWingFar' + side, Input0='F22DvWing%s.Output' % side, Input1='%.1f' % TANK_WING_DV)
        lost = o('logic_confirm_delay', 'F22TankWingOff' + side, Input=far, TimeUp=TANK_WING_SEP_S, TimeDown=0.0001,
                 Threshold=0.5)
        now = o('logic_or', 'F22TankGoneNow' + side, Inputs=' %s %s ' % (req, lost))
        rate = o('product', 'F22TankGoneRate' + side, Inputs=' %s 50.0 ' % now)
        held = o('integral_clamped', 'F22TankGoneHeld' + side, Input=rate, Range=' 0.0 1.0 ', Value=0.0)
        o('logic_greater', 'F22TankGone' + side, Input0=held, Input1='0.5')
        o('logic_greater', 'F22TankOn' + side, Input0='0.5', Input1='F22TankGone%s.Output' % side)
        # the kick: EMER JETT only. The rack hangs on the console (tank_addon): a torn console takes its tank along
        # at once, as a real pylon's tank - kicked off the flying console it hung in the air first and went ~0.3 s
        # after the console (in-game 2026-11-13). F22TankGone (with the console's loss) still clears the fuel, the
        # slugs and the hull - unseen, its delay does not show
        krate = o('product', 'F22TankKickRate' + side, Inputs=' %s 50.0 ' % req)
        kheld = o('integral_clamped', 'F22TankKickHeld' + side, Input=krate, Range=' 0.0 1.0 ', Value=0.0)
        o('logic_greater', 'F22TankKick' + side, Input0=kheld, Input1='0.5')
    print('ferry tanks: EMER JETT kicks each off its rack on the console (%.2f m at %.0f m/s, then a snap; the joint gives at %.0f kN), '
          'right %.2f s after left; fuel in %d slugs a tank' % (EJECT_STROKE, EJECT_SPEED, TANK_FORCE_MAX / 1e3,
                                                                JETT_RIPPLE_S, TANK_SLUGS))


def eject_stroke(o, name, signal, speed, apart=None):
    """An ejector rack's position (m, negative = along -axis) for `signal`: the push at `speed`, the snap
    EJECT_SNAP_S into it, repeated every EJECT_PERIOD for EJECT_TRY_S (until `apart`, if given), then held. `o` makes
    an object (type, name, **fields) and returns it. Returns (objects, position signal)."""
    age = name + 'Age'
    nodes = [o('integral_clamped', age, Input=signal, Range=' 0.0 %.1f ' % (EJECT_TRY_S + 1.0), Value=0.0),
             o('product', name + 'Cycles', Inputs=' %s.Output %.4f ' % (age, 1.0 / EJECT_PERIOD)),
             o('clamp_cyclic', name + 'Phase', Input=name + 'Cycles.Output', Range=('string8', ' 0.0 1.0 ')),
             o('logic_greater', name + 'Down', Input0='0.5', Input1=name + 'Phase.Output'),
             o('logic_greater', name + 'Done', Input0=age + '.Output', Input1='%.1f' % EJECT_TRY_S),
             o('logic_or', name + 'Hold', Inputs=' %s.Output %s.Output %s' % (name + 'Down', name + 'Done',
                                                                          apart + ' ' if apart else '')),
             o('logic_and', name + 'Cmd', Inputs=' %s %s.Output ' % (signal, name + 'Hold')),
             o('servoclassic', name, Input=name + 'Cmd.Output', Speed=speed / EJECT_STROKE, P1=1.0),
             # the snap: EJECT_SNAP_S into each down phase (the age's phase), at once
             o('logic_greater', name + 'Late', Input0=name + 'Phase.Output', Input1='%.4f' % (EJECT_SNAP_S / EJECT_PERIOD)),
             o('logic_or', name + 'LateOrDone', Inputs=' %s.Output %s.Output %s' % (name + 'Late', name + 'Done',
                                                                                    apart + ' ' if apart else '')),
             o('logic_and', name + 'Snap', Inputs=' %s.Output %s.Output ' % (name + 'Cmd', name + 'LateOrDone')),
             o('mixlinear', name + 'Pos', Input0=name + '.Output', Input1=name + 'Snap.Output', Weight0=-EJECT_STROKE,
               Weight1=-EJECT_SNAP)]
    return nodes, name + 'Pos.Output'


def _kicked(o, name, base, body, r0, pos, kf, df, kt, dt, fmax, tmax, rack_mass):
    """A kinematic rack (locked slide on base, follows pos) and a breakable jointlinear from it to body."""
    vec = lambda v: ('tmvector3d', ' %.4f %.4f %.4f ' % tuple(v))
    rack = name + 'Rack'
    kt = kt if isinstance(kt, dict) else {a: kt for a in 'xyz'}
    dt = dt if isinstance(dt, dict) else {a: dt for a in 'xyz'}
    return rack, [
        o('rigidbody', rack, Mass=rack_mass, InertiaLength=vec([0.3, 0.3, 0.3]), R0=vec(r0),
          B0=('tmmatrix3d', ' 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0 ')),
        o('multibody_joint', 'Joint' + rack, Body0=base, Body1=rack, R0=vec(r0), X0=vec([0.0, 0.0, 1.0]), Kp=0.0,
          Kd=0.0, InputPosition=pos, InputLock='1.0', Type=('uint32', '1')),
        o('jointlinear', 'Joint' + name, Body0=rack, Body1=body, R0=vec(r0),
          Kfx=kf, Kfy=kf, Kfz=kf, Dfx=df, Dfy=df, Dfz=df, Ktx=kt['x'], Kty=kt['y'], Ktz=kt['z'],
          Dtx=dt['x'], Dty=dt['y'], Dtz=dt['z'], ForceMax=fmax, TorqueMax=tmax)]


def tank_addon(obj, holder, side, body, cg, fuel, x_span, zc, hull_geometry):
    """The ferry add-on's part of one tank (make_f22.py, stage 6): the shell's ejector rack (on its console) and
    breakable joint at the forward lug, the fuel slugs on their own racks, the lifting hull body, the separation check (IRS of the tank
    against its rack) and the graphics swap - drawn on the fuselage while it holds (a sprung body moves centimetres
    against the wing: gaps, as the consoles), on its own body once off. Returns (dynamics, graphics)."""
    full = {'L': 'Left', 'R': 'Right'}[side]
    gone = 'F22TankGone%s.Output' % full
    vec = lambda v: ('tmvector3d', ' %.4f %.4f %.4f ' % tuple(v))
    eye = ('tmmatrix3d', ' 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0 ')
    o = lambda type_, name, **f: obj(holder, type_, name, **f)
    speed = EJECT_SPEED * EJECT_SPREAD[side]
    y = cg[1]
    lug = [cg[0] + TANK_LUG_AHEAD, y, cg[2] + 0.55]          # the pylon's lug line, over the shell's centre of gravity
    hull = 'F22TankHull' + side

    stroke = lambda name, signal, apart=None: eject_stroke(o, name, signal, speed, apart)

    dyn, pos = stroke('F22EjectStroke' + side, 'F22TankKick%s.Output' % full, 'F22TankApart%s.Output' % side)
    rack, nodes = _kicked(o, 'F22Tank' + side, full + 'Wing', body, lug, pos, TANK_KF, TANK_DF, TANK_KT, TANK_DT,
                          TANK_FORCE_MAX, TANK_TORQUE_MAX, RACK_MASS)
    dyn += nodes
    # the fuel slugs, nose to tail inside the tank; slug k holds the k-th share from the bottom, goes when it is burnt
    share = fuel / TANK_SLUGS
    x0, x1 = x_span
    for k in range(TANK_SLUGS):
        name = 'F22TankSlug%s%d' % (side, k)
        r0 = [x0 + (x1 - x0) * (k + 0.5) / TANK_SLUGS, y, zc]
        dyn += [o('logic_greater', name + 'Burnt', Input0='%.1f' % (k * share + 1.0),
                  Input1='F22FerryFuel%s.Output' % full),
                o('logic_confirm_delay', name + 'Due', Input=name + 'Burnt.Output', TimeUp=SLUG_DUE_S, TimeDown=0.0001,
                  Threshold=0.5),
                o('logic_or', name + 'Go', Inputs=' %s.Output %s ' % (name + 'Due', gone))]
        nodes, spos = stroke(name + 'Stroke', name + 'Go.Output')
        dyn += nodes
        dyn += [o('rigidbody', name, Mass=share - SLUG_RACK_MASS, InertiaLength=vec([6.7 / TANK_SLUGS, 0.8, 0.8]),
                  R0=vec(r0), B0=eye),
                # (no drag, a slug would fall faster without end: ~150 m/s, as a falling lump)
                o('aerofuselage', name + 'Aero', Body=name, StationX=('float64', '[ %.4f %.4f ]' % (r0[0] + 0.4, r0[0] - 0.4)),
                  StationY=('float64', '[ %.4f %.4f ]' % (y, y)), StationZ=('float64', '[ %.4f %.4f ]' % (zc, zc)),
                  StationWidth=('float64', '[ 0.6 0.6 ]'), StationHeight=('float64', '[ 0.6 0.6 ]'),
                  StationShape=('uint32', '[ 0 0 ]'), Cdx=1.0, Cdy=1.0, Cdz=1.0, Cly=0.0, Clz=0.0, Cm=0.0)]
        _, nodes = _kicked(o, name, 'Fuselage', name, r0, spos, SLUG_KF, SLUG_DF, SLUG_KT, SLUG_DT, SLUG_FORCE_MAX,
                           SLUG_TORQUE_MAX, SLUG_RACK_MASS)
        # (the slug body itself comes before its joint: rigidbody first, as the donor lists them)
        dyn += nodes
    dyn += [
        o('servoclassic', 'F22TankHullUp' + side, Input=gone, Speed=TANK_HULL_RATE / TANK_HULL_LIFT, P1=1.0),
        o('mixlinear', 'F22TankHullPos' + side, Input0='F22TankHullUp%s.Output' % side, Input1='F22TankHullUp%s.Output' % side,
          Weight0=TANK_HULL_LIFT, Weight1=0.0),
        o('rigidbody', hull, Mass=TANK_HULL_MASS, InertiaLength=vec([0.3, 0.3, 0.3]), R0=vec(lug), B0=eye),
        o('multibody_joint', 'JointF22TankHull' + side, Body0='Fuselage', Body1=hull, R0=vec(lug),
          X0=vec([0.0, 0.0, 1.0]), Kp=0.0, Kd=0.0, InputPosition='F22TankHullPos%s.Output' % side, InputLock='1.0',
          Type=('uint32', '1')),
        o('collisionhull', 'CollisionF22Tank' + side, Body=hull, Geometry=hull_geometry, K=1.0e7, D=1.0e4),
        o('inertial_reference_system', 'F22IrsTank' + side, Body=body),
        o('inertial_reference_system', 'F22IrsRack' + side, Body=rack)]
    diffs = []
    for q in ('GroundSpeed', 'VerticalVelocity'):
        d, n, a = ('F22TankDv%s%s' % (side, q), 'F22TankDvNeg%s%s' % (side, q), 'F22TankDvAbs%s%s' % (side, q))
        dyn += [o('mixlinear', d, Input0='F22IrsTank%s.Output%s' % (side, q), Input1='F22IrsRack%s.Output%s' % (side, q),
                  Weight0=1.0, Weight1=-1.0),
                o('linear', n, Input=d + '.Output', Scaling=-1.0),
                o('maximum', a, Inputs=' %s.Output %s.Output ' % (d, n))]
        diffs.append(a + '.Output')
    dyn += [o('sum', 'F22TankDv' + side, Inputs=' %s ' % ' '.join(diffs)),
            o('logic_greater', 'F22TankFar' + side, Input0='F22TankDv%s.Output' % side, Input1='%.1f' % TANK_APART_MPS),
            o('logic_confirm_delay', 'F22TankApart' + side, Input='F22TankFar%s.Output' % side, TimeUp=TANK_APART_S,
              TimeDown=1.0, Threshold=0.5),
            # (with the console: its own separation, as the console's drawing swaps - the tank rides it)
            o('logic_or', 'F22TankOff' + side, Inputs=' %s F22TankApart%s.Output F22SepWing%s.Output ' % (gone, side, full)),
            o('logic_greater', 'F22TankHolds' + side, Input0='0.5', Input1='F22TankOff%s.Output' % side),
            o('output', 'GfxOutF22TankOff' + side, Input='F22TankOff%s.Output' % side),
            o('output', 'GfxOutF22TankHolds' + side, Input='F22TankHolds%s.Output' % side)]
    gfx = [o('graphics_input', 'GfxF22TankOff' + side, InputID=('uint32', 'GfxOutF22TankOff%s.Output' % side)),
           o('graphics_input', 'GfxF22TankHolds' + side, InputID=('uint32', 'GfxOutF22TankHolds%s.Output' % side)),
           o('bendingbodygraphics', 'Stores_TankK' + side, PositionID=('uint32', full + 'Wing.R'),
             OrientationID=('uint32', full + 'Wing.Q'), PositionID1=('uint32', 'Fuselage.R'),
             OrientationID1=('uint32', 'Fuselage.Q'), GeometryList=' Stores_TankK%s ' % side,
             Range0=(1.0 if side == 'L' else -1.0) * WING_TIP_Y, Range1=(1.0 if side == 'L' else -1.0) * SPLIT_Y,
             InputHide='GfxF22TankOff%s.Output' % side),     # bends with its console (WING_TIP_Y)
           o('rigidbodygraphics', 'Stores_Tank' + side, PositionID=('uint32', body + '.R'),
             OrientationID=('uint32', body + '.Q'), GeometryList=' Stores_Tank%s ' % side,
             InputHide='GfxF22TankHolds%s.Output' % side),
           o('rigidbodygraphics', 'HullF22Tank' + side, PositionID=('uint32', hull + '.R'),
             OrientationID=('uint32', hull + '.Q'), GeometryList=' %s ' % hull_geometry, InputHide='1.0')]
    return dyn, gfx


# fuel with a lost wing (2026-11-11, user: "less fuel - is there a system that shuts the tanks, or should it leak beyond
# the burn?"). The wing tank spans root (y 1.1, 0.189 m2 section) to console (y 4.0, 0.048 m2): split at the break
# (y 2.6) about a third of it goes with the console at once; the root part is torn open along the break - no valve
# closes a ruptured tank, it drains (WING_LEAK, estimate: ~20 s for a full root part). The fuselage tanks lose
# nothing beyond the burn: the wing transfer lines feed through check valves (wing -> fuselage only) and the refuel and
# vent valves are shut outside refuelling (usual fighter practice; the F-22's plumbing is not public). The engines then
# draw on what is left - the other wing, then the feed tanks. A ferry tank (on the console's pylon) goes with it.
# The burn accounting (make_f22.py 'fuel burn': closed forms of the fuel used, transfer -> wing -> feed) gave the lost
# wing's share back as free fuel: the wing and feed stages are integrals of what each tank gives now
WING_LEAK = 15.0                     # kg/s out of a torn wing root tank


def fuel_wing_loss(ns, joint):
    obj, dyn = ns['obj'], ns['dyn']
    at = joint('LeftWingTank')                  # the tank values everything reads (FUEL page, totals, cautions)
    o = lambda type_, name, **f: obj(dyn, type_, name, at, **f) and name + '.Output'
    share = {}
    for side in ('Left', 'Right'):
        st = joint(side + 'WingFuelTank').find('Stations').children
        (y0, a0), (y1, a1) = [(abs(float(x.get('R0').split()[1])),
                               float(x.get('Dimensions').split()[0]) * float(x.get('Dimensions').split()[1])) for x in st]
        area = lambda y: a0 + (a1 - a0) * (y - y0) / (y1 - y0)
        vol = lambda ya, yb: (yb - ya) * (area(ya) + area(yb)) / 2
        share[side] = vol(SPLIT_Y, y1) / vol(y0, y1)
    # the ferry tanks: one per console pylon, shared burn (make_f22.py); the lost one's fuel out of the count - lost
    # with its console or jettisoned (F22TankGone*, tank_release)
    for side in ('Left', 'Right'):
        sep = 'F22SepWing%s.Output' % side
        gone = 'F22TankGone%s.Output' % side
        o('logic_greater', 'F22FuelWingOn' + side, Input0='0.5', Input1=sep)
        # (the side's tank as shown - after a first loss the other side holds all that is left; held from the frame
        # before the separation)
        o('state_frozen', 'F22FerryHeld' + side, Input='F22FerryFuel%s.Output' % side, InputEnable='F22TankOn%s.Output' % side,
          Value=0.0)
        o('product', 'F22FerryLost' + side, Inputs=' F22FerryHeld%s.Output %s ' % (side, gone))
    o('sum', 'F22FerryLost', Inputs=' F22FerryLostLeft.Output F22FerryLostRight.Output ')
    burnt = joint('F22TanksBurnt')
    full = burnt.get('Inputs').split()[1]
    o('mixlinear', 'F22FerryCap', Input0=full, Input1='F22FerryLost.Output', Weight0=1.0, Weight1=-1.0)
    burnt.set('Inputs', ' F22TanksBurntRaw.Output F22FerryCap.Output ', 'string8')
    o('mixlinear', 'F22FerryLeft0', Input0='F22TanksLeft.Output', Input1='F22FerryLost.Output', Weight0=1.0, Weight1=-1.0)
    o('maximum', 'F22FerryLeft', Inputs=' F22FerryLeft0.Output 0.0 ')
    for side, other in (('Left', 'Right'), ('Right', 'Left')):
        o('linear', 'F22FerryShare' + side, Input='F22TankGone%s.Output' % other, Scaling=0.5, Offset=0.5)
        o('product', 'F22FerryFuel' + side, Inputs=' F22FerryLeft.Output F22TanksAttached.Output F22FerryShare%s.Output '
          'F22TankOn%s.Output ' % (side, side))
        joint(side + 'OuterExternalTankFuel').set('Input', 'F22FerryFuel%s.Output' % side, 'string8')
    o('logic_greater', 'F22FerryHasFuel', Input0='F22FerryCap.Output', Input1='F22TanksBurntRaw.Output')
    o('product', 'F22FerryGiving', Inputs=' F22FerryHasFuel.Output F22TanksAttached.Output ')
    o('logic_greater', 'F22FerryNotGiving', Input0='0.5', Input1='F22FerryGiving.Output')
    # what the internal tanks give now, once the fuselage transfer tanks are empty (their closed form stays)
    o('logic_greater', 'F22TransferEmpty', Input0='FuelUsedAfterTransfer.Output', Input1='0.001')
    o('product', 'F22WingStageFlow', Inputs=' FuelFlowTotal.Output F22FerryNotGiving.Output F22TransferEmpty.Output ')
    for side in ('Left', 'Right'):
        sep, keep = 'F22SepWing%s.Output' % side, 'F22FuelWingOn%s.Output' % side
        o('mixlinear', 'F22WingLeft0' + side, Input0='%sWingFuelTank.Output' % side, Input1='F22WingDrawn%s.Output' % side,
          Weight0=1.0, Weight1=-1.0)
        o('maximum', 'F22WingLeft' + side, Inputs=' F22WingLeft0%s.Output 0.0 ' % side)
        # the root part left at the break, draining
        o('product', 'F22WingRoot0' + side, Inputs=' F22WingLeft%s.Output %.4f ' % (side, 1.0 - share[side]))
        o('state_frozen', 'F22WingRoot' + side, Input='F22WingRoot0%s.Output' % side, InputEnable=keep, Value=0.0)
        o('product', 'F22WingLeakFlow' + side, Inputs=' %s %.1f ' % (sep, WING_LEAK))
        o('integral_clamped', 'F22WingLeaked' + side, Input='F22WingLeakFlow%s.Output' % side, Range=' 0.0 100000.0 ',
          Value=0.0)
        o('mixlinear', 'F22WingTorn0' + side, Input0='F22WingRoot%s.Output' % side, Input1='F22WingLeaked%s.Output' % side,
          Weight0=1.0, Weight1=-1.0)
        o('maximum', 'F22WingTorn' + side, Inputs=' F22WingTorn0%s.Output 0.0 ' % side)
        o('product', 'F22WingShownIntact' + side, Inputs=' F22WingLeft%s.Output %s ' % (side, keep))
        o('product', 'F22WingShownTorn' + side, Inputs=' F22WingTorn%s.Output %s ' % (side, sep))
        o('sum', 'F22WingFuel' + side, Inputs=' F22WingShownIntact%s.Output F22WingShownTorn%s.Output ' % (side, side))
        o('logic_greater', 'F22WingHas' + side, Input0='F22WingLeft%s.Output' % side, Input1='0.5')
        o('logic_and', 'F22WingGives' + side, Inputs=' F22WingHas%s.Output %s ' % (side, keep))
        o('logic_greater', 'F22WingDry' + side, Input0='0.5', Input1='F22WingGives%s.Output' % side)
    # split between the wings that still give (both: half each, one: all), then the feed tanks (half each)
    o('product', 'F22WingBoth', Inputs=' F22WingGivesLeft.Output F22WingGivesRight.Output ')
    for side in ('Left', 'Right'):
        o('mixlinear', 'F22WingPart' + side, Input0='F22WingGives%s.Output' % side, Input1='F22WingBoth.Output',
          Weight0=1.0, Weight1=-0.5)
        o('product', 'F22WingDraw' + side, Inputs=' F22WingStageFlow.Output F22WingPart%s.Output ' % side)
        o('integral_clamped', 'F22WingDrawn' + side, Input='F22WingDraw%s.Output' % side, Range=' 0.0 100000.0 ', Value=0.0)
    o('product', 'F22FeedDraw', Inputs=' F22WingStageFlow.Output F22WingDryLeft.Output F22WingDryRight.Output ')
    o('integral_clamped', 'F22FeedDrawn', Input='F22FeedDraw.Output', Range=' 0.0 100000.0 ', Value=0.0)
    for side in ('Left', 'Right'):
        o('mixlinear', 'F22FeedLeft0' + side, Input0='%sFeedFuelTank.Output' % side, Input1='F22FeedDrawn.Output',
          Weight0=1.0, Weight1=-0.5)
        o('maximum', 'F22FeedLeft' + side, Inputs=' F22FeedLeft0%s.Output 0.0 ' % side)
        joint(side + 'WingTank').set('Input', 'F22WingFuel%s.Output' % side, 'string8')
        joint(side + 'FeedTank').set('Input', 'F22FeedLeft%s.Output' % side, 'string8')
    rst = joint('FuelLoadChangedReset')
    rst.set('Events', ' %s F22WingDrawnLeft.Reset F22WingDrawnRight.Reset F22FeedDrawn.Reset ' % rst.get('Events').strip(),
            'string8')
    print('fuel: wing tanks lose %.0f / %.0f %% with the console, the root part drains at %.0f kg/s; fuselage tanks '
          'isolated' % (100 * share['Left'], 100 * share['Right'], WING_LEAK))


def fins(ns, joint):
    tmd, dyn, obj, add_inputs = ns['tmd'], ns['dyn'], ns['obj'], ns['add_inputs']
    # the donor flies the right fin's aerodynamics on the fuselage (the left one's on its fin): both on their fins
    aero = joint('RightVerticalStabilizerAero')
    assert aero.get('Body') == 'Fuselage', aero.get('Body')
    aero.set('Body', 'RightVerticalStabilizer', 'string8')
    o = lambda type_, name, **f: obj(dyn, type_, name, **f) and name + '.Output'
    flutter = TEST not in ('fins', 'finbreak')     # the joints alone: F22_TEST=fins
    if flutter:
        over = o('linear_interpolation', 'F22FlutterOver', Input='AirspeedIndicator.IndicatedAirspeed',
                 Map=' (%.1f 0.0) (%.1f 1.0) ' % tuple(v * 0.514444 for v in FLUTTER_KCAS))
        on = o('product', 'F22FlutterOn', Inputs=' %s F22FailCond.Output ' % over)
        rate = o('mixlinear', 'F22FlutterRate', Input0=on, Input1='1.0', Weight0=0.7, Weight1=-0.3)
        amp = o('integral_clamped', 'F22Flutter', Input=rate, Range=' 0.0 1.0 ', Value=0.0)
        add_inputs('F22BuffetAny', amp)
        # the stabilators shake too: well into the flutter (about 1.5 s over the full flutter speed) one actuator jams -
        # the STAB failure, its side by the sim time's fine digits (failures_f22 RAND's dice). Estimate, as the speeds
        hard = o('logic_greater', 'F22FlutterHard', Input0=amp, Input1='0.6')
        o('logic_greater', 'F22FlutterStabSide', Input0='F22RandU1.Output', Input1='0.5')
        o('event_demultiplexer', 'F22FlutterStabPick', InputSelect='F22FlutterStabSide.Output',
          Events=' F22FailSetStab1.Trigger F22FailSetStab2.Trigger ')
        o('event_edge_rising', 'F22FlutterStabJam', Input=hard, Events=' F22FlutterStabPick.Trigger ', Value=1.0,
          Threshold=0.5)
    torque = FINBREAK_TORQUE_MAX if TEST == 'finbreak' else FIN_TORQUE_MAX
    for side, hz in (('Left', 6.0), ('Right', 6.4)):
        breakable(tmd, joint('Joint%sVerticalStabilizer' % side), torque, 5.0e6, FIN_KF, FIN_DF, FIN_KT, FIN_DT)
        hull = joint('Collision%sVerticalStabilizer' % side)      # as the wings': a torn fin must not end the flight
        assert hull.get('Body') == side + 'VerticalStabilizer', hull.name
        hull.set('Body', 'Fuselage', 'string8')                    # (a fin on the ground is still a crash: InstantCrash)
        if not flutter:
            continue
        phase = o('product', 'F22FlutterPhase' + side, Inputs=' F22SimTime.Output %.2f ' % hz)
        cyc = o('clamp_cyclic', 'F22FlutterCyc' + side, Input=phase, Range=('string8', ' 0.0 1.0 '))
        tri = o('linear_interpolation', 'F22FlutterTri' + side, Input=cyc,
                Map=' (0.0 0.0) (0.25 1.0) (0.75 -1.0) (1.0 0.0) ')
        swing = o('product', 'F22FlutterSwing' + side, Inputs=' %s %s %.3f ' % (tri, amp, FLUTTER_RAD))
        st0 = joint(side + 'VerticalStabilizerAero').find('Stations').children[0]
        servo = st0.get('InputFlapAngle').strip()
        assert servo == 'Servo%sRudder.Output' % side, servo
        o('mixlinear', 'F22RudderAero' + side, Input0=servo, Input1=swing, Weight0=1.0, Weight1=1.0)
        st0.set('InputFlapAngle', 'F22RudderAero%s.Output' % side, 'string8')
    print('fins break at %.0f kN m%s%s' % (torque / 1e3, ' - TEST ' + TEST if TEST else '',
                                                  '; flutter over %.0f KCAS (COND)' % FLUTTER_KCAS[0] if flutter else ''))


# FCS page status (2026-11-10, the user: "full freedom, easy to read"): the donor's FCS page (display_f18_flight_controls)
# takes only surface positions, angle of attack and the g limit - its SV / channel grids are always empty. Beside it, in
# the free space under G-LIM, our table: each surface L / R - OK, DEGD (one hydraulic system out: one servo valve of
# each actuator), HYD (no pressure: the surfaces trail), LOST (torn off with its wing console or fin), JAM (a
# stabilator's actuator stuck, the STAB failure); and the two
# hydraulic systems. Page units as the FAIL page (0..1000 across the screen); placed from the user's straight shot of
# the centre MFD
PARTS_LOST = {'Wing': 'Wing', 'Fin': 'VerticalStabilizer'}
REF_MASS = {'Wing': 5.0, 'Fin': 5.0}       # kg of the reference bodies, taken from the part (50 / 25 kg changed nothing:
REF_INERTIA_LENGTH = {'Wing': '0.3 0.3 0.3', 'Fin': '0.3 0.3 0.3'}     # the stabilators still left, in-game 2026-11-11)
SEP_MPS, SEP_S = 4.0, 0.05           # 'separated' (F22Sep*): faster than LOST; the snapshot froze 1 s late on LOST


def fcs_status(ns):
    """Called from make_f22.py in the graphics part (after the FAIL page): built later, the page object was lost - the
    graphics list is closed and de-duplicated into a new one before breakage's apply (2026-11-10: 'F22FcsPage not
    found', the aircraft did not load)."""
    obj, dyn = ns['obj'], ns['dyn']
    joint = lambda name: next(x for x in dyn.children if x.name == name)
    o = lambda type_, name, **f: obj(dyn, type_, name, **f) and name + '.Output'
    not_ = lambda name, src: o('logic_greater', name, Input0='0.5', Input1=src)
    # lost parts: an inertial reference on the part's body against the fuselage's. The IRS gives no X / Y / Z (only a
    # vector position; "cannot link OutputX" stopped the aircraft from loading, 2026-11-10), so by speeds: attached,
    # the part moves with the airframe - its ground speed and vertical speed differ only by the rotation (4 rad/s roll
    # x 5-7 m: up to ~25 m/s); torn off, it drops and decelerates - over 35 m/s apart (ground speed + vertical speed
    # differences) for 1 s: LOST (RST clears it, it comes back at once if the part is gone). The jointlinear has no
    # 'broken' output
    for part, body_tail in PARTS_LOST.items():
        for side in ('Left', 'Right'):
            body = side + body_tail
            irs = 'F22Irs' + part + side
            obj(dyn, 'inertial_reference_system', irs, Body=body)
            # compared with an IRS on a small body at the part's place and attitude, locked to the fuselage as the
            # donor locks the fins: attached, only the spring's give separates them (~1-2 m/s at most). The fins'
            # canted bodies against the fuselage's own IRS read LOST at 445 kt / 28 deg/s with both fins in place
            # (in-game 2026-11-10); the wings had the fuselage IRS until 2026-11-11 (rotation x span: up to ~25 m/s)
            fb = joint(body)
            fj = joint('Joint%sVerticalStabilizer' % side if part == 'Fin' else 'JointFuselage%sWing' % side)
            assert fj.type == 'multibody_joint', fj.type
            # (mass: suspected and cleared, 2026-11-11 - see damage_graphics, stabilators)
            rbody = 'F22%sRef%s' % (part, side)
            rmass = REF_MASS[part]
            m0 = float(fb.get('Mass'))
            fb.set('Mass', '%g' % (m0 - rmass), 'float64')
            obj(dyn, 'rigidbody', rbody, Mass=rmass, InertiaLength=('tmvector3d', ' %s ' % REF_INERTIA_LENGTH[part]),
                R0=('tmvector3d', fb.get('R0')), B0=('tmmatrix3d', fb.get('B0')))
            obj(dyn, 'multibody_joint', 'JointF22%sRef%s' % (part, side), Body0='Fuselage', Body1=rbody,
                R0=('tmvector3d', fj.get('R0')), X0=('tmvector3d', fj.get('X0')), Kp=1.0e7, Kd=5.0e4,
                Type=('uint32', '0'), InputLock='1')
            ref = 'F22Irs%sRef%s' % (part, side)
            obj(dyn, 'inertial_reference_system', ref, Body=rbody)
            diffs = []
            for q in ('GroundSpeed', 'VerticalVelocity'):
                d = o('mixlinear', 'F22Dv%s%s%s' % (part, side, q), Input0='%s.Output%s' % (irs, q),
                      Input1='%s.Output%s' % (ref, q), Weight0=1.0, Weight1=-1.0)
                n = o('linear', 'F22DvNeg%s%s%s' % (part, side, q), Input=d, Scaling=-1.0)
                diffs.append(o('maximum', 'F22DvAbs%s%s%s' % (part, side, q), Inputs=' %s %s ' % (d, n)))
            dv = o('sum', 'F22Dv%s%s' % (part, side), Inputs=' %s ' % ' '.join(diffs))
            far = o('logic_greater', 'F22Away%s%s' % (part, side), Input0=dv, Input1='35.0')
            o('logic_confirm_delay', 'F22Lost%s%s' % (part, side), Input=far, TimeUp=1.0, TimeDown=1.0, Threshold=0.5)
            # separated, at once (graphics swap, first-loss snapshot): 4 m/s apart for 0.05 s - a torn console leaps
            # away under its own lift (hundreds of m/s2), a torn fin brakes (~100 m/s2); then LOST holds it
            apart = o('logic_greater', 'F22Apart%s%s' % (part, side), Input0=dv, Input1='%.1f' % SEP_MPS)
            now = o('logic_confirm_delay', 'F22SepNow%s%s' % (part, side), Input=apart, TimeUp=SEP_S, TimeDown=0.2,
                    Threshold=0.5)
            o('logic_or', 'F22Sep%s%s' % (part, side), Inputs=' %s F22Lost%s%s.Output ' % (now, part, side))
    # hydraulics per actuator: both systems drive every surface
    for k in (1, 2):
        o('logic_greater', 'F22HydOk%d' % k, Input0='F22HydSystem%d.Output' % k, Input1='0.5')
    not_('F22HydOut1', 'F22HydOk1.Output')
    not_('F22HydOut2', 'F22HydOk2.Output')
    o('sum', 'F22HydOutCount', Inputs=' F22HydOut1.Output F22HydOut2.Output ')   # 0 ok, 1 DEGD, 2 HYD
    rows = [('LEF', 'Wing'), ('TEF', 'Wing'), ('AIL', 'Wing'), ('RUD', 'Fin'), ('STAB', None)]
    o('constant_text', 'F22FcsBlank', Input='    ')
    for t in ('OK', 'DEGD', 'HYD', 'LOST', 'JAM'):
        o('constant_text', 'F22FcsText' + t, Input=t)
    for k in (1, 2):
        o('constant_text', 'F22FcsTextOut%d' % k, Input='OUT')
    lost_any = []
    # F22FcsState<surface><L|R>: 0 OK, 1 DEGD, 2 HYD, 3 LOST, 4 JAM - shown by the FCS page (mfd_f22.fcs_page)
    for name, part in rows:
        for side in ('Left', 'Right'):
            key = name + side[0]
            if part:
                lost = '%s.Output' % ('F22Lost%s%s' % (part, side))
                lost_any.append(lost)
                o('product', 'F22FcsLost3' + key, Inputs=' %s 3.0 ' % lost)
                o('maximum', 'F22FcsState' + key, Inputs=' F22HydOutCount.Output F22FcsLost3%s.Output ' % key)
            else:       # the stabilators are not torn off (their joint is the actuator): JAM, the STAB failure
                k = 1 if side == 'Left' else 2
                o('product', 'F22FcsJam4' + key, Inputs=' F22FailStab%d.Output 4.0 ' % k)
                o('maximum', 'F22FcsState' + key, Inputs=' F22HydOutCount.Output F22FcsJam4%s.Output ' % key)
    # (the first-loss snapshot under the grid - what went first, KT / G / AOA / sideslip - was a test aid of block 2,
    # out with the Hornet page 2026-11-17: user, "telemetry left over from the tests")
    # ICAWS FCS DEGD (failures_f22.ICAWS): a surface lost or a stabilator jammed
    o('logic_or', 'F22FcsDegd', Inputs=' %s F22FailStab1.Output F22FailStab2.Output ' % ' '.join(sorted(set(lost_any))))


# ---- block 3, visible breakage (2026-11-11): the DCS model's damage layers (ac_f22.py BREAK_BODIES). Export makes two
# copies of each console / fin piece: '<part>__K<body>' on the fuselage while the part holds (drawn on its sprung body,
# it opened centimetre gaps at the roots and fin bases under load, in-game 2026-11-11), '<part>__B<body>' on the body
# once separated (F22Sep*, fcs_status: ~0.05 s after the break). At that moment the stubs show on the fuselage and the
# intact fin bases hide. A torn part has no collision hull (any hard ground contact of any body ends the flight,
# 2026-11-10), so it would sink through the ground: it hides when its own radar altimeter reads under 2 m (latched until
# the part is back, RST / new flight) and in any case 30 s after the separation
# the console bends (user 2026-11-15): drawn on the fuselage while it holds (the K copies), each vertex now follows a
# blend of the fuselage and the console body by its span - the fuselage's at the joint (SPLIT_Y), the console's at the
# tip (WING_TIP_Y), smoothly between: the root stays put (no gap at the fuselage - rigid on the sprung body it opened
# one, 2026-11-11), the console bends as its body flexes on the jointlinear (~2 deg at 9 g, K_TORQUE x: the tip ~15 cm
# up). The stock way (bendingbodygraphics, the gliders' and airliners' wings, flap parts with their own transforms in
# the A320). Everything on the console bends with it - flaps, ailerons, leading-edge flaps (their hinge transforms
# stay), the formation strip, the ferry tank copy (tank_addon) - and the tip lights move to the console body
WING_TIP_Y = 6.78                    # m, half the span (13.56 m)


def bend_on_console(n, body):
    """Make rigidbodygraphics `n` (drawn on the fuselage) a bendingbodygraphics between `body` (a wing console) and
    the fuselage, blended along the span from the joint to the tip. Keeps its geometry, transform, hide and lighting."""
    sign = 1.0 if body.startswith('Left') else -1.0
    n.type = 'bendingbodygraphics'
    n.set('PositionID', '%s.R' % body, 'uint32')
    n.set('OrientationID', '%s.Q' % body, 'uint32')
    n.set('PositionID1', 'Fuselage.R', 'uint32')
    n.set('OrientationID1', 'Fuselage.Q', 'uint32')
    n.set('Range0', '%.4f' % (sign * WING_TIP_Y), 'float64')
    n.set('Range1', '%.4f' % (sign * SPLIT_Y), 'float64')


BREAK_PARTS = {'LeftWing': ('Wing', 'Left'), 'RightWing': ('Wing', 'Right'),
               'LeftVerticalStabilizer': ('Fin', 'Left'), 'RightVerticalStabilizer': ('Fin', 'Right')}
GROUND_HIDE_M = 2.0
GONE_AFTER_S = 30.0


def damage_graphics(ns):
    obj, dyn, g, G, parts, published = ns['obj'], ns['dyn'], ns['g'], ns['G'], ns['parts'], ns['published']
    o = lambda type_, name, **f: obj(dyn, type_, name, **f) and name + '.Output'
    gfx = {}

    def gfx_input(sig):
        if sig not in gfx:
            g('graphics_input', 'Gfx' + sig, InputID=('uint32', published(sig)))
            gfx[sig] = 'Gfx%s.Output' % sig
        return gfx[sig]

    for body, (part, side) in BREAK_PARTS.items():
        key = part + side
        sep = 'F22Sep%s.Output' % key
        o('logic_greater', 'F22Holds' + key, Input0='0.5', Input1=sep)
        # at the body's centre (R0 in aircraft coordinates, as the joints')
        r0 = next(x for x in dyn.children if x.type == 'rigidbody' and x.name == body).get('R0')
        alt = o('radar_altimeter', 'F22RadAlt' + key, Body=body, R0=('tmvector3d', r0), Calibration=('float64', '0.0'))
        low = o('logic_greater', 'F22Low' + key, Input0='%.1f' % GROUND_HIDE_M, Input1=alt)
        hit = o('logic_and', 'F22Hit' + key, Inputs=' %s %s ' % (sep, low))
        # latched without events: rises on a hit, holds while the part is off, drops when it is back
        back = o('mixlinear', 'F22SepLess1' + key, Input0=sep, Input1='1.0', Weight0=1.0, Weight1=-1.0)   # 0 / -1
        rate = o('mixlinear', 'F22GroundRate' + key, Input0=hit, Input1=back, Weight0=20.0, Weight1=20.0)
        held = o('integral_clamped', 'F22Grounded' + key, Input=rate, Range=' 0.0 1.0 ', Value=0.0)
        age_rate = o('mixlinear', 'F22SepAgeRate' + key, Input0=sep, Input1='1.0', Weight0=101.0, Weight1=-100.0)
        age = o('integral_clamped', 'F22SepAge' + key, Input=age_rate, Range=' 0.0 %.1f ' % (GONE_AFTER_S + 5.0), Value=0.0)
        old = o('logic_greater', 'F22SepOld' + key, Input0=age, Input1='%.1f' % GONE_AFTER_S)
        grounded = o('logic_greater', 'F22GroundedNow' + key, Input0=held, Input1='0.5')
        # the flying copy: hidden while the part holds, and once it is gone
        o('logic_or', 'F22HideFlying' + key, Inputs=' F22Holds%s.Output %s %s ' % (key, grounded, old))
    # the plain skin of a console / fin ('Fuselage__K<body>', 'Fuselage__B<body>'): no other loop of make_f22.py draws it
    for pname in sorted(parts):
        if pname.startswith(('Fuselage__K', 'Fuselage__B')):
            g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, PositionID=('uint32', 'Fuselage.R'),
              OrientationID=('uint32', 'Fuselage.Q'))
    n_body = {}
    for n in G:
        if n.type != 'rigidbodygraphics' or not re.search('__[KB]', n.name):
            continue
        tag, body = re.search(r'__([KB])(\w+)$', n.name).groups()
        assert body in BREAK_PARTS, n.name
        assert n.find('InputHide') is None, n.name
        key = ''.join(BREAK_PARTS[body])
        if tag == 'K':
            assert n.get('PositionID') == 'Fuselage.R', n.name
            n.set('InputHide', gfx_input('F22Sep' + key))
            if BREAK_PARTS[body][0] == 'Wing':
                bend_on_console(n, body)
        else:
            n.set('PositionID', '%s.R' % body, 'uint32')
            n.set('OrientationID', '%s.Q' % body, 'uint32')
            n.set('InputHide', gfx_input('F22HideFlying' + key))
        n_body[(tag, body)] = n_body.get((tag, body), 0) + 1
    # the wingtip lights (nav and anti-collision, point and cone lights on the fuselage body at y +-6.2) go dark when
    # their console separates - the wiring is torn (they hung blinking in the air, in-game 2026-11-13); the formation
    # strips on a flying console / fin are dark too
    tip_lights = {'Left': ('LightNavRed', 'LightNavRedCone', 'LightAntiCollisionLeft', 'LightAntiCollisionLeftCone'),
                  'Right': ('LightNavGreen', 'LightNavGreenCone', 'LightAntiCollisionRight', 'LightAntiCollisionRightCone')}
    for side, names in tip_lights.items():
        for name in names:
            n = next(x for x in G if x.name == name)
            assert abs(float(n.get('R0').split()[1])) > 6.0, name
            # on the console body: they ride the tip as it bends (dark once it separates, below)
            assert n.get('PositionID') == 'Fuselage.R', name
            n.set('PositionID', '%sWing.R' % side, 'uint32')
            n.set('OrientationID', '%sWing.Q' % side, 'uint32')
            mod = n.get('InputModulation').strip()
            g('graphics_product', 'F22Wired' + name, Input0=mod, Input1=gfx_input('F22HoldsWing' + side))
            n.set('InputModulation', 'F22Wired%s.Output' % name, 'string8')
    for n in G:
        if n.type == 'rigidbodygraphics' and n.name.startswith('L_Formation__B'):
            n.children = [c for c in n.children if c.name != 'InputLuminance']
    for side in ('Left', 'Right'):
        for part in ('Wing', 'Fin'):
            stub = 'D_%s%sStub' % (part, side)
            assert stub in parts, stub
            g('rigidbodygraphics', stub, GeometryList=' %s ' % stub, PositionID=('uint32', 'Fuselage.R'),
              OrientationID=('uint32', 'Fuselage.Q'), InputHide=gfx_input('F22Holds%s%s' % (part, side)))
        base = next(n for n in G if n.type == 'rigidbodygraphics' and n.name == 'D_Fin%sBase' % side)
        base.set('InputHide', gfx_input('F22SepFin' + side))
    # stabilators drawn on the fuselage, turned about their hinge by the actuator: in a full break-up (both consoles off
    # at ~800 kt, the fuselage tumbling) both stabilators left their hinges by a metre and came back, also with heavy
    # reference bodies (in-game 2026-11-11). The hinge is a stiff spring in the game's physics (Kp 1e7); 300 kg six
    # metres from the centre of a fuselage spinning at tens of rad/s pull meganewtons. A real stabilator either holds
    # on its spindle or tears off - it does not wander and come back - so the drawing follows the actuator (+ trailing
    # edge down, right-handed about the joint's axis, as the physics) and stays on the hinge; in flight the stiff
    # actuator keeps the physical one within a fraction of a degree of it
    for side in ('Left', 'Right'):
        gs = next(n for n in G if n.type == 'rigidbodygraphics' and n.name == 'Body_%sStabilator' % side)
        assert gs.get('PositionID') == '%sStabilator.R' % side and gs.find('InputTransform') is None, gs.name
        jn = next(x for x in dyn.children if x.name == 'JointFuselage%sStabilator' % side)
        rot = g('graphics_rotation', 'F22StabHinge' + side, Input=gfx_input('Servo%sStabilator' % side),
                Axis=('tmvector3d', ' %s ' % jn.get('X0').strip()), Pivot=('tmvector3d', ' %s ' % jn.get('R0').strip()))
        gs.set('PositionID', 'Fuselage.R', 'uint32')
        gs.set('OrientationID', 'Fuselage.Q', 'uint32')
        gs.set('InputTransform', 'F22StabHinge%s.Output' % side, 'string8')
    # burst tyres: each wheel and its squashed copy '<part>__FLAT' (ac_f22._burst_tyres), swapped on F22TyreBurst*
    spin_key = {101: 'N', 102: 'L', 103: 'R'}
    o('logic_greater', 'F22TyreOkN', Input0='0.5', Input1='F22TyreBurstN.Output')
    n_tyre = 0
    for pname in sorted(parts):
        if not pname.endswith('__FLAT'):
            continue
        base = pname[:-len('__FLAT')]
        key = next(spin_key[a] for a in parts[pname]['args'] if a in spin_key)
        gb = next(n for n in G if n.type == 'rigidbodygraphics' and n.name == base)
        gf = next(n for n in G if n.type == 'rigidbodygraphics' and n.name == pname)
        assert gb.find('InputHide') is None and gf.find('InputHide') is None, pname
        gb.set('InputHide', gfx_input('F22TyreBurst' + key))
        gf.set('InputHide', gfx_input('F22TyreOk' + key))
        n_tyre += 1
    assert n_tyre == 3, 'burst tyre copies: %d of 3 (export the parts: ./build.sh export)' % n_tyre
    # sheared struts (gear_shear): the lower strut and the wheel hide on the aircraft at the shear, their copies show on
    # the debris body (ac_f22.GEAR_DEBRIS) - the wheel turning with the debris tyre, intact or burst as it was. The
    # copies are in the export pose; moved by the gap between the drawn wheel centre there and the physics wheel
    # centre (the debris body's), so the debris wheel stands on its tyre
    anim = ns['anim']
    import ac_f22 as AC
    hide = lambda name, sig: next(n for n in G if n.type == 'rigidbodygraphics' and n.name == name).set('InputHide', sig)
    n_gear = 0
    for key, (lower, wheel) in AC.GEAR_DEBRIS.items():
        lower_p, wheel_p = 'A_' + lower.replace(',', '_'), 'A_' + wheel.replace(',', '_')
        shear = 'F22Shear%s.Output' % key
        o('logic_or', 'F22HideWheel' + key, Inputs=' F22TyreBurst%s.Output %s ' % (key, shear))
        o('logic_or', 'F22HideFlat' + key, Inputs=' F22TyreOk%s.Output %s ' % (key, shear))
        o('logic_greater', 'F22Unsheared' + key, Input0='0.5', Input1=shear)
        o('logic_or', 'F22HideDebrisWheel' + key, Inputs=' F22Unsheared%s.Output F22TyreBurst%s.Output ' % (key, key))
        o('logic_or', 'F22HideDebrisFlat' + key, Inputs=' F22Unsheared%s.Output F22TyreOk%s.Output ' % (key, key))
        hide(lower_p, gfx_input('F22Shear' + key))
        hide(wheel_p, gfx_input('F22HideWheel' + key))
        hide(wheel_p + '__FLAT', gfx_input('F22HideFlat' + key))
        spin = anim[wheel_p]['links'][0]
        assert spin['kind'] == 'spin', wheel_p
        debris = 'F22GearDebris' + key
        # the debris body's R0 (gear_shear, built later with the physics): the centre of that gear's wheel hulls
        hulls = [next(x for x in dyn.children if x.name == h) for h in SHEAR_GEAR[key][1]]
        r0 = [sum(float(h.get('R0').split()[i]) for h in hulls) / len(hulls) for i in range(3)]
        gap = [r0[i] - spin['pivot'][i] for i in range(3)]
        length = math.sqrt(sum(v * v for v in gap))
        if length < 1e-4:
            gap, length = [0.0, 0.0, 1.0], 0.0
        g('graphics_input', 'GfxDebrisSpin' + key, InputID=('uint32', 'F22DebrisWheel%s.RotationAngle' % key))
        g('graphics_rotation', 'F22DebrisSpin' + key, Input='GfxDebrisSpin%s.Output' % key, Axis=spin['axis'],
          Pivot=spin['pivot'])
        unit = [v / (length or 1.0) for v in gap]
        g('graphics_translation', 'F22DebrisGap' + key, Input='%.4f' % length, Axis=unit)
        g('graphics_translation', 'F22DebrisGapSpun' + key, Input='%.4f' % length, Axis=unit,
          InputTransform='F22DebrisSpin%s.Output' % key)
        on_debris = dict(PositionID=('uint32', debris + '.R'), OrientationID=('uint32', debris + '.Q'))
        g('rigidbodygraphics', 'D_GearDebris' + key, GeometryList=' D_GearDebris%s ' % key, **on_debris,
          InputTransform='F22DebrisGap%s.Output' % key, InputHide=gfx_input('F22Unsheared' + key))
        for part, sig in (('D_GearDebrisWheel' + key, 'F22HideDebrisWheel' + key),
                          ('D_GearDebrisWheel%sFlat' % key, 'F22HideDebrisFlat' + key)):
            g('rigidbodygraphics', part, GeometryList=' %s ' % part, **on_debris,
              InputTransform='F22DebrisGapSpun%s.Output' % key, InputHide=gfx_input(sig))
        n_gear += 1
        print('gear debris %s: drawn wheel centre %.3f m from the physics one' % (key, length))
    drawn = {n.name for n in G if n.type in ('rigidbodygraphics', 'bendingbodygraphics')}
    undrawn = sorted(p for p in parts if (re.search('__[KB]', p) or p.startswith('D_') or p.endswith('__FLAT'))
                     and p not in drawn)
    assert not undrawn, 'breakage parts not drawn: %s' % undrawn
    for body in BREAK_PARTS:
        if not n_body.get(('K', body)) or n_body.get(('K', body)) != n_body.get(('B', body)):
            raise SystemExit('damage_graphics: %s kept %s / flying %s graphics (export the parts: ./build.sh export)' % (
                body, n_body.get(('K', body)), n_body.get(('B', body))))
    print('breakage drawn: %s (kept = flying); stubs on the fuselage' % ', '.join(
        '%s %d' % (b, n_body[('B', b)]) for b in sorted(BREAK_PARTS)))
