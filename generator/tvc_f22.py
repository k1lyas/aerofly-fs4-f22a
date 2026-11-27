"""F-22 pitch thrust vectoring on the F/A-18 dynamics: the F119 thrust really turns with the nozzle.

    python3 tvc_f22.py <f22.tmd> <out.tmd>      apply to a finished .tmd (test variants; needs no regeneration)
make_f22.py calls apply() on the aircraft it generates.

jet_engine has no vector inputs (the game refuses to load VectorZControl on it, test 2026-10-30) but its force follows
the orientation of its Body: each engine gets a nozzle body on an actuated multibody_joint, like a stabilator. Thrust,
afterburner and Mach / altitude behaviour stay the engine's own. The native turbine class vectors too, but it has no
afterburner and no thrust lapse (same test, TEST VEC-C).

flight_controller_f18 knows nothing of the nozzles, so they follow what it asks of the stabilators, which is how the real
pilot has no separate nozzle control either. The real F-22 laws are not public: gains here are estimates.
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import tmd
import burner_f22

MAX_ANGLE = math.radians(20.0)      # F119, and the DCS model's full travel (args 622/623)
GROUND_ANGLE = math.radians(10.0)   # full stick on the ground: 20 deg rotated at 88 kt and held the tail on the runway
# on the ground the vector comes in with speed: full stick and afterburner at 10 deg from standstill still put the tail
# on the runway at ~90 kt (flight 2026-10-30, 10 deg pitch at 94 kt); a smooth rotation at 130 kt was right
GROUND_SPEED_MAP = ' (48.9 0.0) (64.3 1.0) '       # calibrated airspeed, m/s: 95 .. 125 kt
GROUND_PITCH_MAP = ' (0.105 1.0) (0.175 0.0) '     # pitch, rad: gone by 10 deg, the tail touches at ~12-14 deg
# Pitch loop gain by calibrated airspeed, m/s (our schedule, as real flight controls lower their gains with dynamic
# pressure). Flight 2026-11-20 (calm air, telemetry logs/test_091_2026-11-20.jsonl): with the altitude hold the
# Hornet's laws on this airframe fell into a pitch limit cycle at 1.1-1.5 Hz, +-5..6 deg, set off near M 0.97 and
# then kept up down to 563 kt at 600 ft - a high-q loop-gain problem, not a Mach one (the lift-slope and stabilator
# sweep fixes did not change it, nor TVC off). This airframe makes ~1.7x the Hornet's g per degree, so the laws' loop
# runs ~2x hot at high q: full gain to 430 kt, 0.7 at 525, 0.55 from about 600 kt. The g law still holds the
# commanded g (it gets the stabilators it needs), only softer; DIRECT is not touched (the pilot's own loop)
PITCH_Q_GAIN = ' (220.0 1.0) (270.0 0.7) (310.0 0.55) (400.0 0.5) '
NOZZLE_RATE = 0.7                   # rad/s, the stabilators' own (not public for the F119)
DIRECT_NOZZLE_RATE = 1.2            # rad/s in DIRECT (2026-11-21, a sharper flip; the F119's slew rate is not public either)
NOZZLE_MASS = 300.0                 # out of the engine body, whose centre moves so that the common centre stays put
# Stabilator (rad, + nose down) -> nozzle (rad, + nose up). Small signals at half gain: the nozzle moment does not fall
# with speed as the tail's does, at 100 kt on full dry thrust it already adds ~1.1x the tail's own gain to the
# controller's loop; large ones reach the full travel when the tail runs out.
TAIL_MAP = ' (-0.42 %.4f) (-0.1 0.05) (0.0 0.0) (0.1 -0.05) (0.42 %.4f) ' % (MAX_ANGLE, -MAX_ANGLE)
# calibrated airspeed (m/s): full up to ~290 kt, a quarter from ~505 kt, where the tail's moment is far the larger
SPEED_MAP = ' (0.0 1.0) (150.0 1.0) (260.0 0.25) '
# Direct mode (in the spirit of the Su-27 family's "hard link"; the F-22 has nothing like it): airborne,
# with DIR on (SYS page), the stick asks for a pitch rate of its own, past the Hornet's laws. Plain stick to surface
# tumbled the aircraft (test 2026-10-30: ~160 deg/s at 10-70 kt, no damping), so stabilators and nozzles close on the rate.
# Limits (radians, m/s), second try: 50 deg/s and 9 g / 3 g felt heavy and slow in the game. Third: 80 deg/s at any speed looked
# like magic when slow (flight 2026-10-30: nose up to 77 deg/s below 40 kt, while the path stayed within thrust + lift, 1.2 g at
# 40-70 kt). Now the pull rises from ~26 deg/s near standstill, as fast as the mod's full-stick loops, to 62 deg/s at ~195 kt,
# then what 16 g allows at that speed (11 g until 2026-11-09: DIRECT was made the unprotected mode, as a
# hard link in DCS - full stick fast and low overstresses the airframe, the wings break at 13.5 g, breakage_f22.py; the
# peak 62 deg/s stays). Push: the same near standstill, then 5 g. No more pull past 60-70 deg angle of attack, the
# F-22's published trimmed alpha. Roll and yaw stay with the flight controller.
# 2026-11-21 (a sharper flip at the top of a vertical climb, more vector in DIR): the nozzles' +-20 deg stays (the
# F119's and the drawn travel); what held the flip was the law - 26-31 deg/s asked when slow, no pull past 60-70 deg
# alpha. Slow now 52-57 deg/s pull and push (the thrust's +-20 deg at full burner, ~600 kN m, has the authority), the
# pull goes on to ~100 deg alpha (through the stall: a flip, unprotected as DIRECT is meant to be)
DIRECT_PULL_MAP = ' (0.0 0.9) (50.0 1.0) (100.0 1.08) (150.0 1.046) (200.0 0.785) (300.0 0.523) (400.0 0.392) '
DIRECT_PUSH_MAP = ' (0.0 0.9) (50.0 0.8) (100.0 0.55) (150.0 0.33) (200.0 0.25) (300.0 0.16) (400.0 0.12) '
DIRECT_ALPHA_MAP = ' (1.6 1.0) (1.85 0.0) '
# rate error (rad/s) -> surface (rad), by calibrated airspeed: a ~6 rad/s loop on the estimated moments; simulated in 1 DOF
# with the servo rates, 40-600 kt, idle to afterburner. Inverse with dynamic pressure, nozzles only when slow
DIRECT_TAIL_GAIN = ' (0.0 1.2) (77.0 1.2) (110.0 0.6) (150.0 0.32) (200.0 0.18) (260.0 0.108) (350.0 0.06) '
DIRECT_NOZZLE_GAIN = ' (0.0 0.8) (100.0 0.8) (150.0 0.4) (260.0 0.1) '
# the hard part of DIRECT (2026-11-09: as the hard link in DCS): the rate loop alone could not move the
# stabilators more than ~4 deg fast (its gain falls with dynamic pressure), 10.3 g at 450-500 kt in the game, so the
# 13.5 g wing limit (breakage_f22.py) was out of reach. Now the stick also moves them directly, the same at any speed,
# as a mechanical link: 0.10 rad (5.7 deg) at full stick on top of the loop. Fast and low a full pull goes far past the
# wings' strength; slow, the loop's high gain still holds the rate down
DIRECT_HARD = 0.10                  # rad of stabilator per full stick
# DIRECT on / off fade (was 0.5 s): DIR off in a 10 g pull handed the stabilators back to the F/A-18 laws at once -
# their command, far nose down (they had held 9 g against our 10), slammed the load from +10 g down through zero, the
# wing joints rang and broke in the air with the peak still 10.3 g (in-game 2026-11-09, twice). Over 2 s the load
# changes slower than the wings' ~8 Hz, they follow it without ringing
DIRECT_FADE_RATE = 0.5              # 1 / s
# The stabilator command alone hardly moved the nozzles in steady flight ('static'), and not at all on the ground below
# 95 kt: the stick also feeds them directly. It adds no loop gain, the controller closes around it.
STICK_FEED = math.radians(8.0)
# on the ground with the throttles back the nozzles follow the stick at any speed (the F-22's control check): no thrust to speak
# of. With thrust they wait for GROUND_SPEED_MAP, as the tail hit the runway at ~90 kt
GROUND_IDLE_MAP = ' (0.15 1.0) (0.35 0.0) '


def _node(type_, name, **fields):
    n = tmd.Node(type_, name, leaf=False)
    for k, v in fields.items():
        t, v = v if isinstance(v, tuple) else ('float64' if isinstance(v, float) else 'string8', v)
        n.children.append(tmd.Node(t, k, v if isinstance(v, str) else '%.6g' % v))
    return n


def _vec3(v):
    return ('tmvector3d', ' %s ' % ' '.join('%.4f' % x for x in v))


def _after(lst, name, new):
    lst.children.insert([c.name for c in lst.children].index(name) + 1, new)


def apply(dyn):
    for eng in ('Engine1', 'Engine2'):
        body, engine = dyn.find(eng + 'Body'), dyn.find(eng)
        r_eng = [float(x) for x in body.get('R0').split()]
        r_noz = [float(x) for x in engine.get('R0').split()]
        m = float(body.get('Mass'))
        body.set('Mass', '%.6g' % (m - NOZZLE_MASS))
        body.set('R0', _vec3([(m * e - NOZZLE_MASS * n) / (m - NOZZLE_MASS) for e, n in zip(r_eng, r_noz)])[1])
        noz = eng + 'Nozzle'
        _after(dyn, eng + 'Body', _node('rigidbody', noz, Mass=NOZZLE_MASS, InertiaLength=_vec3([1.5, 1.5, 1.5]),
                                        R0=_vec3(r_noz), B0=('tmmatrix3d', ' 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0 ')))
        # right hand rule about X0 (as the arresting hook: +1.05 rad about -y swings its tip down): +y takes the
        # thrust forward and down, the tail goes down. Proven by the 2026-10-30 test: 20 deg lifted the nose at 88 kt
        _after(dyn, 'Joint%sBody' % eng, _node('multibody_joint', 'Joint' + noz, Body0='Fuselage', Body1=noz,
                                               R0=_vec3(r_noz), X0=_vec3([0.0, 1.0, 0.0]), Kp=3000000.0, Kd=30000.0,
                                               Type=('uint32', '0'), InputPosition='NozzleAngle.Output', InputLock='1.0'))
        engine.set('Body', noz)
    old = dyn.find('VectorPitch')
    if old is not None:
        dyn.children.remove(old)
    # on the ground the stick, not the stabilators: they carry the automatic take-off trim, which would lift the nose
    # with the stick neutral
    for o in (
        _node('mixlinear', 'VectorTailMean', Input0='FlightController.OutputLeftTaileron',
              Input1='FlightController.OutputRightTaileron', Weight0=0.5, Weight1=0.5),
        _node('linear_interpolation', 'VectorFromTailMap', Input='VectorTailMean.Output', Map=('tmvector2d', TAIL_MAP)),
        _node('product', 'VectorFromTailKept', Inputs=' VectorFromTailMap.Output F22DirectKeep.Output '),
        _node('linear_interpolation', 'F22DirectNozzleGain', Input='AirDataComputer.OutputCalibratedAirspeed',
              Map=('tmvector2d', DIRECT_NOZZLE_GAIN)),
        _node('product', 'VectorFromStickDirectBlended',
              Inputs=' F22DirectRateError.Output F22DirectNozzleGain.Output F22DirectBlend.Output -1.0 '),
        _node('mixlinear', 'VectorFromTail', Input0='VectorFromTailKept.Output', Input1='VectorFromStickDirectBlended.Output',
              Weight0=1.0, Weight1=1.0),
        _node('linear_interpolation', 'VectorSpeedFade', Input='AirDataComputer.OutputCalibratedAirspeed',
              Map=('tmvector2d', SPEED_MAP)),
        _node('linear', 'VectorInAir', Input='OnGroundSensor.Output', Scaling=-1.0, Offset=1.0),
        _node('linear', 'VectorStickFeed', Input='ServoElevatorStick.Output', Scaling=-STICK_FEED),
        _node('mixlinear', 'VectorFromLaw', Input0='VectorFromTail.Output', Input1='VectorStickFeed.Output',
              Weight0=1.0, Weight1=1.0),
        _node('clamp', 'VectorFromLawClamped', Input='VectorFromLaw.Output',
              Range=('tmvector2d', ' %.4f %.4f ' % (-MAX_ANGLE, MAX_ANGLE))),
        _node('linear_interpolation', 'F22PitchQGainSpeed', Input='AirDataComputer.OutputCalibratedAirspeed',
              Map=('tmvector2d', PITCH_Q_GAIN)),
        # full gain while Auto-GCAS flies the recovery (the autopilot is off then): its fly-up must be crisp
        _node('maximum', 'F22PitchQGain', Inputs=' F22PitchQGainSpeed.Output F22GcasActive.Output '),
        _node('product', 'VectorAirCommand',
              Inputs=' VectorFromLawClamped.Output VectorSpeedFade.Output VectorInAir.Output F22PitchQGain.Output '),
        _node('linear', 'VectorFromStick', Input='ServoElevatorStick.Output', Scaling=-GROUND_ANGLE),
        _node('linear_interpolation', 'VectorGroundSpeedFade', Input='AirDataComputer.OutputCalibratedAirspeed',
              Map=('tmvector2d', GROUND_SPEED_MAP)),
        _node('linear_interpolation', 'VectorGroundPitchFade', Input='PhysicalAttitudeIndicator.PitchAngle',
              Map=('tmvector2d', GROUND_PITCH_MAP)),
        _node('maximum', 'VectorThrottleMax', Inputs=' LeftThrottleCommand.Output RightThrottleCommand.Output '),
        _node('linear_interpolation', 'VectorGroundIdle', Input='VectorThrottleMax.Output', Map=('tmvector2d', GROUND_IDLE_MAP)),
        _node('maximum', 'VectorGroundAllow', Inputs=' VectorGroundSpeedFade.Output VectorGroundIdle.Output '),
        _node('product', 'VectorGroundCommand', Inputs=' VectorFromStick.Output VectorGroundAllow.Output '
                                                       'VectorGroundPitchFade.Output OnGroundSensor.Output '),
        _node('mixlinear', 'VectorCommand', Input0='VectorAirCommand.Output', Input1='VectorGroundCommand.Output',
              Weight0=1.0, Weight1=1.0),
        # the nozzles' slew: the stabilators' rate (through F22NozzleSlow), faster in DIRECT (the command straight to
        # NozzleAngle, which stays the servo the failure / power gates of make_f22 and failures_f22 hook into)
        _node('servoclassic', 'F22NozzleSlow', Input='F22VectorCommandGated.Output', Speed=NOZZLE_RATE, P1=1.0),
        _node('product', 'F22NozzleSlowKept', Inputs=' F22NozzleSlow.Output F22DirectKeep.Output '),
        _node('product', 'F22NozzleDirect', Inputs=' F22VectorCommandGated.Output F22DirectBlend.Output '),
        _node('mixlinear', 'F22NozzleTarget', Input0='F22NozzleSlowKept.Output', Input1='F22NozzleDirect.Output',
              Weight0=1.0, Weight1=1.0),
        _node('servoclassic', 'NozzleAngle', Input='F22NozzleTarget.Output', Speed=DIRECT_NOZZLE_RATE, P1=1.0),
        # DCS args 622/623: no longer drives the drawn nozzles (ac_f22.py NOZZLE_PLATES read NozzleAngle), the table parts still need the signal
        _node('linear', 'VectorPitch', Input='NozzleAngle.Output', Scaling=-1.0 / MAX_ANGLE),
        # the mode from the DIR key of the SYS page only (2026-11-05: the MASTER ARM switch flipped it too - a weapons
        # switch has nothing to do with the flight controls; the switch stays a plain ARM/SAFE toggle)
        _node('variable', 'F22DirectFlipped', Value='0.0'),
        _node('logic_invert', 'F22DirectFlippedNot', Input='F22DirectFlipped.Output'),
        _node('event_value', 'F22DirectToggle', Input='F22DirectFlippedNot.Output', Events=' F22DirectFlipped.Set '),
        _node('linear_interpolation', 'F22DirectMode', Input='F22DirectFlipped.Output', Map=('tmvector2d', ' (0.0 0.0) (1.0 1.0) ')),
        _node('product', 'F22DirectActive', Inputs=' F22DirectMode.Output VectorInAir.Output '),
        # the vector can be switched off on the TVC page: the nozzles go back to neutral at their own rate
        _node('variable', 'F22VectorOn', Value='1.0'),
        _node('logic_invert', 'F22VectorOnNot', Input='F22VectorOn.Output'),
        _node('event_value', 'F22VectorToggle', Input='F22VectorOnNot.Output', Events=' F22VectorOn.Set '),
        _node('product', 'F22VectorCommandGated', Inputs=' VectorCommand.Output F22VectorOn.Output '),
        _node('servoclassic', 'F22DirectBlend', Input='F22DirectActive.Output', Speed=DIRECT_FADE_RATE, P1=1.0),
        _node('linear', 'F22DirectKeep', Input='F22DirectBlend.Output', Scaling=-1.0, Offset=1.0),
        # OutputQRate: + nose down, as the stick's + push (stock Concorde: AngleOfAttackSoon = -0.6 Q + alpha)
        _node('minimum', 'F22DirectStickPull', Inputs=' ServoElevatorStick.Output 0.0 '),
        _node('maximum', 'F22DirectStickPush', Inputs=' ServoElevatorStick.Output 0.0 '),
        _node('linear_interpolation', 'F22DirectPullRate', Input='AirDataComputer.OutputTrueAirspeed',
              Map=('tmvector2d', DIRECT_PULL_MAP)),
        _node('linear_interpolation', 'F22DirectPushRate', Input='AirDataComputer.OutputTrueAirspeed',
              Map=('tmvector2d', DIRECT_PUSH_MAP)),
        _node('linear_interpolation', 'F22DirectAlphaLimit', Input='PitotTube.AngleOfAttack',
              Map=('tmvector2d', DIRECT_ALPHA_MAP)),
        _node('product', 'F22DirectPullCommand',
              Inputs=' F22DirectStickPull.Output F22DirectPullRate.Output F22DirectAlphaLimit.Output '),
        _node('product', 'F22DirectPushCommand', Inputs=' F22DirectStickPush.Output F22DirectPushRate.Output '),
        _node('mixlinear', 'F22DirectRateCommand', Input0='F22DirectPullCommand.Output',
              Input1='F22DirectPushCommand.Output', Weight0=1.0, Weight1=1.0),
        _node('mixlinear', 'F22DirectRateError', Input0='F22DirectRateCommand.Output',
              Input1='InertialReferenceSystem.OutputQRate', Weight0=1.0, Weight1=-1.0),
        _node('linear_interpolation', 'F22DirectTailGain', Input='AirDataComputer.OutputCalibratedAirspeed',
              Map=('tmvector2d', DIRECT_TAIL_GAIN)),
        _node('product', 'F22DirectLoop', Inputs=' F22DirectRateError.Output F22DirectTailGain.Output '),
        _node('linear', 'F22DirectHard', Input='ServoElevatorStick.Output', Scaling=DIRECT_HARD),
        _node('mixlinear', 'F22DirectTail', Input0='F22DirectLoop.Output', Input1='F22DirectHard.Output',
              Weight0=1.0, Weight1=1.0),
        _node('product', 'F22DirectTailBlended', Inputs=' F22DirectTail.Output F22DirectBlend.Output '),
        _node('product', 'F22ControllerTailKept', Inputs=' VectorTailMean.Output F22DirectKeep.Output F22PitchQGain.Output '),
        _node('mixlinear', 'F22TailPitch', Input0='F22ControllerTailKept.Output', Input1='F22DirectTailBlended.Output',
              Weight0=1.0, Weight1=1.0),
        _node('mixlinear', 'F22TailRoll', Input0='FlightController.OutputLeftTaileron',
              Input1='FlightController.OutputRightTaileron', Weight0=0.5, Weight1=-0.5),
        _node('mixlinear', 'F22LeftTailCommand', Input0='F22TailPitch.Output', Input1='F22TailRoll.Output',
              Weight0=1.0, Weight1=1.0),
        _node('mixlinear', 'F22RightTailCommand', Input0='F22TailPitch.Output', Input1='F22TailRoll.Output',
              Weight0=1.0, Weight1=-1.0),
    ):
        dyn.children.insert([c.name for c in dyn.children].index('GfxOutVectorPitch'), o)
    # (the ICAWS FCS line also lights in DIRECT: make_f22.py F22FcsIcaws)
    dyn.find('ServoLeftStabilator').set('Input', 'F22LeftTailCommand.Output')
    dyn.find('ServoRightStabilator').set('Input', 'F22RightTailCommand.Output')
    # MASTER ARM: the Hornet's jump of the MFDs to STORES / RADAR on arming goes (no stores page to jump to)
    dyn.find('MasterArmSafeSwitch_SetToArm').set('Events', ' SimulationMode.Reset ')
    # the vector replaces the Hornet's rudder toe-in on the take-off rotation
    dyn.find('FlightController').set('MaximumRudderToeIn', '0', 'float64')


if __name__ == '__main__':
    root = tmd.load(sys.argv[1])
    apply(root.children[0].children[0].find('DynamicObjects'))
    gfx = root.children[0].children[0].find('GraphicObjects')
    burner_f22.apply(gfx, root.children[0].children[0].find('DynamicObjects'))
    tmd.save(root, sys.argv[2])
