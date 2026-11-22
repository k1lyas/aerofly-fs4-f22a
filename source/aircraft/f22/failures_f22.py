"""F-22 failures (block 1 of docs/reference/FAILURES.md, user 2026-11-09): an instructor page FAIL on the MFDs, hidden
until a code is entered on the ICP, with failures chosen by hand, at random, or caused by how the aircraft is flown.

make_f22.py calls dynamics() before its ICAWS list, after_tvc() after the nozzle law and graphics() in the MFD pages.
Everything acts through this mod's own systems (emergency power, hydraulics, engine run / start, fuel burn, air data):
no new physics. What the real F-22 does is not public (T.O. 1F-22A-1 is not released); the procedures follow general
fighter practice and the accident reports in FAILURES.md, the numbers marked 'estimate' are ours.

FAIL page (in place of the Hornet's UFC BU page, which is out of the menu): two columns of failures, OK / FAIL.
  left keys:  up / down move the cursor, SEL fails the selected item now (or clears it again)
  right keys: RAND arms one failure at random 1 - 15 min later (common ones three times as likely as rare ones),
              COND switches on the failures caused by flying (below; on from the start), RST clears everything
Code: FAIL_CODE on the ICP scratchpad, ENTR on the empty ICP page: the right MFD shows FAIL, the link stays on every MFD
menu.

What the pilot does about each (and what clears it), see FAILURES.md section 2 / 3:
  GEN       generator trips off: cycle its GEN switch (OFF, ON) - it comes back
  GEN ARC   (Tyndall 2012) the left generator trips and the left hydraulics leak slowly: a chafed feeder arcing.
            Cycling the GEN switch now lights a fire in the left bay. GEN and HYD together: leave the switch alone
  HYD       the system leaks down in about a minute. Both fly every surface; the right (utility) one also moves the
            gear, wheel brakes and nose-wheel steering, the left one the bay doors (estimate, usual fighter layout):
            R lost - the gear stays down (free-falls when selected down), brakes on the accumulator, no steering
  BLEED     hot air leak: below 70 % N2 it is harmless, above it heats the bay, at full power a fire in ~1 min;
            EGT up to +35 deg at full power (the FADEC holds thrust on less compressor air)
            (Alaska 2010 report: the pilot pulled the throttles to idle and descended)
  OBOGS     oxygen concentrator off: the backup bottle (BOS) lasts 10 min above 10 000 ft (estimate), then OXY LOW
  OIL       pressure 0: the engine seizes after ~60 s at full power (~90 s at idle) unless shut down (FADEC). On
            the way VIB climbs (page ENG), then EGT. A seized engine (L / R SEIZED) does not turn, does not
            windmill: no pump, no generator on that side, no restart
  AB        no afterburner on that engine (full throttle gives MIL)
  NOZZLE    the nozzles stay where they are: no thrust vectoring
  FUEL LK   0.3 kg/s (~2400 lb/h, estimate) more out of the tanks: no caution, only the fuel going too fast
  L MFD / PMFD  screen dark
  ANTISKD   antiskid off (wheels lock under hard braking)
  FLAME     flameout: shut the engine down (FADEC off or throttle to cut-off), then relight as a ground start (APU
            air, FADEC NORM, throttle out of cut-off; MOTOR if needed)
  FIRE      FIRE warning and voice; the engine itself runs on as before. Fire switch on the ENG page (L FIRE left
            column, R FIRE right column - the DCS cockpit has no fire buttons), the usual fighter sequence: 1st press
            shuts that engine's fuel off (engine stops, box), 2nd press (DSCH) discharges the bottle - the fire goes
            out. One bottle for both sides. With the bottle gone the key reads FUEL: a press gives the fuel back
            (restart as after a flameout). Burning: the side's hydraulics go after 40 s, the engine seizes after
            80 s, the fire reaches the other hydraulic system after 150 s (half as fast with the fuel off; estimates).
            Both sides on fire: one bottle - the second side cannot be put out (eject). From 50 s VIB climbs
  PITOT     the pitot is blocked: total pressure frozen, the airspeed reads like an altimeter (Eglin 2020: a taped
            air data port); AIR DATA on the ICAWS 8 s later. The standby airspeed is on another channel
  DUAL ENG  both engines flame out
  STAB      one stabilator's actuator jams where it stands (its command frozen after the hydraulics: no pressure loss
            moves it either). The flight controller flies on with the other stabilator, the ailerons and the nozzles
            (the vector follows the tail command, so the nozzles take over pitch); FCS DEGD, STAB JAM on the FCS page.
            Nothing in the cockpit clears it (RST on this page does)
Felt, not only read: a damaged engine hunts (thrust +-, its sound and a slight yaw) and grumbles; a seized rotor stops
in 1.5 s with a grind; the gear in a fast airflow rumbles (buffet sound); a generator dropping off blinks its side's
MFD (bus changeover). The bang and the grind sound in the engine, not at the pilot's head. No smoke: Controls.Smoke
sent while an engine burned drew nothing on the F-22 (in-game 2026-11-09).
Flown (COND on): over 300 kt with the gear down for 3 s - the gear is damaged and stays down; under -0.5 g for 30 s -
fuel and oil starve, both engines flame out (estimate); a stall at more than 60 deg AoA under 60 kt in afterburner for
3 s - one engine flames out; hard braking heats the brakes: BRK HOT and they fade (cools in ~10 min); touchdown sink
over 10 ft/s - HARD LDG, over 15 ft/s - the harder-hit main strut folds (GEAR), over 20 ft/s it breaks off below the
leg, its wheel rolling away (the nose strut too: folds past 5 x its static load, breaks past 6.5 x); a wheel locked with the antiskid off
for 1 s, or braking with the brakes far past BRK HOT, bursts that tyre: a bang, the jet pulls to it, no brake there;
rolling over 225 kt (the tyres' rating, estimate) bursts the nose tyre. A burst wheel sits down on its rim (block 3). Flutter past the speed limit (breakage_f22: fins shaking
from 800 KCAS) jams one stabilator, the side by the sim time's fine digits (estimate: what the real tail does is not
public).
"""
import math
import os

# the instructor's code (user 2026-11-15: 9900, opens the page at once). ENTR acts on the open ICP page - on the
# empty one only this code is read (A/T, ALOW, radio entries have pages of their own): no clash with other entries
FAIL_CODE = 9900

# key, page text, weight in RAND (3 = common, 1 = rare)
ITEMS = [('Gen1', 'L GEN', 3), ('Gen2', 'R GEN', 3), ('Hyd1', 'L HYD', 3), ('Hyd2', 'R HYD', 3),
         ('Bleed1', 'L BLEED', 3), ('Bleed2', 'R BLEED', 3), ('Obogs', 'OBOGS', 3), ('Oil1', 'L OIL', 3),
         ('Oil2', 'R OIL', 3), ('Ab1', 'L AB', 3), ('Ab2', 'R AB', 3), ('Nozzle', 'NOZZLE', 3),
         ('FuelLeak', 'FUEL LK', 3), ('Mfd1', 'L MFD', 3), ('Pmfd', 'PMFD', 3), ('Antiskid', 'ANTISKD', 3),
         ('Flame1', 'L FLAME', 1), ('Flame2', 'R FLAME', 1), ('Fire1', 'L FIRE', 1), ('Fire2', 'R FIRE', 1),
         ('GenArc', 'GEN ARC', 1), ('Pitot', 'PITOT', 1), ('Dual', 'DUAL ENG', 1),
         ('Stab1', 'L STAB', 1), ('Stab2', 'R STAB', 1),
         # page 2: landing gear (block 3, 2026-11-11)
         ('GearUpL', 'L GR UP', 1), ('GearUpR', 'R GR UP', 1), ('GearUpN', 'N GR UP', 1),
         ('DnlkL', 'L DNLK', 1), ('DnlkR', 'R DNLK', 1), ('DnlkN', 'N DNLK', 1),
         ('Nws', 'NWS', 3), ('BrakeL', 'L BRAKE', 3), ('BrakeR', 'R BRAKE', 3),
         ('SeizeL', 'L WHL SZ', 1), ('SeizeR', 'R WHL SZ', 1),
         ('TyreL', 'L TIRE', 1), ('TyreR', 'R TIRE', 1), ('TyreN', 'N TIRE', 1)]
PAGE_SIZE = 25          # items per FAIL page (13 rows x 2, the last right row TD FPM / TD SIDE)
ROWS = 13
NOSE_TYRE_KT = 225.0    # nose tyre speed rating (estimate), COND
FOLD_STOP = {'L': 0.754, 'R': 0.754, 'N': 0.909}   # cylinder command at 80 % of the leg's travel (cylinder geometry)
FOLD_RATE, FOLD_BACK = 3.0, 0.4                     # command / s: the fold in ~0.25 s, back down on RST in ~2 s
GEAR_CTL_RATE = 1.5     # gear cylinder command, full stroke / s (a fold or a release in ~0.7 s; the handle's 0.75 / s passes)
SHEAR_SINK_FPS = 20.0   # touchdown sink that breaks a main strut (2 x the design limit, estimate), COND
# nose wheel load that breaks the nose strut (log 'nose 37929 N' static), COND. Its design: braking with the dynamic
# factor 2 on the load moved forward (m a h / wheelbase: 27 900 kg x 0.8 g x 1.9 m / 6.44 m ~ 64 kN) - limit ~166 kN,
# ultimate x 1.5 ~ 250 kN: ~6.5 x static (estimate by the usual rules; the F-22's figures are not public). 4 x and
# the fold at 2.5 x were met by a hard stop (0.7 g: ~2.4 x, more with the oleo's jolt) and by the throttles against
# the brakes (MIL ~2.8 x, AB ~3.4 x) - the nose leg folded holding the brakes (in-game 2026-11-15)
NOSE_SHEAR_N = 6.5 * 37929.0
ROW_DY = 52             # page units between rows (56 with 12 rows; the 13th row must stay above RAND / COND at 160)

# ICAWS lines (text <= 8 letters, the left UFD's packing), and which of them are warnings
ICAWS = [('L FIRE', 'F22FireWarn1'), ('R FIRE', 'F22FireWarn2'), ('L ENG', 'F22EngOut1'), ('R ENG', 'F22EngOut2'),
         ('L SEIZED', 'F22SeizedWarn1'), ('R SEIZED', 'F22SeizedWarn2'),
         ('L OIL', 'F22OilLow1'), ('R OIL', 'F22OilLow2'), ('L BLEED', 'F22BleedWarn1'), ('R BLEED', 'F22BleedWarn2'),
         ('OBOGS', 'F22ObogsWarn'), ('OXY LOW', 'F22OxyLow'), ('L AB', 'F22AbWarn1'), ('R AB', 'F22AbWarn2'),
         ('NOZZLE', 'F22NozzleWarn'), ('AIR DATA', 'F22AirDataWarn'), ('GEAR', 'F22GearWarn'),
         ('BRK HOT', 'F22BrakeHot'), ('HARD LDG', 'F22HardLanding'), ('FCS DEGD', 'F22FcsDegd'),
         ('NWS', 'F22FailNws'), ('L BRAKE', 'F22FailBrakeL'), ('R BRAKE', 'F22FailBrakeR')]
ICAWS_WARN = ('F22FireWarn1', 'F22FireWarn2', 'F22EngOut1', 'F22EngOut2')

MENU_PREFIXES = ('LeftMFD', 'RightMFD', 'MPCD', 'LowerMFD')
HERE = os.path.dirname(os.path.abspath(__file__))


def _have_sound(name):
    """A new cockpit sound is used only once the converter has made it (./build.sh convert): a configs-only build
    must not point at a missing .tsb."""
    dirs = (os.path.join(HERE, 'converted', 'aircraft', 'f22'),
            os.path.expanduser('~/Library/Application Support/Aerofly FS 4/aircraft/f22'))
    if os.environ.get('F22_SOUND_DIR'):      # release installer (release/install.py): the package's own sounds only
        dirs = (os.environ['F22_SOUND_DIR'],)
    return any(os.path.exists(os.path.join(d, name + '.tsb')) for d in dirs)


def dynamics(ns):
    obj, dyn, D = ns['obj'], ns['dyn'], ns['D']
    setv, dyn_node, add_inputs = ns['setv'], ns['dyn_node'], ns['add_inputs']
    menu_el, keep = ns['_menu_el'], ns['_keep']

    def o(type_, name, **f):
        D[name] = obj(dyn, type_, name, **f)
        return name + '.Output'

    def not_(name, src):
        return o('logic_greater', name, Input0='0.5', Input1=src)

    # ---- failure states: one latch per item (DUAL drives both flameouts)
    keys = [k for k, _, _ in ITEMS if k != 'Dual']
    for k in keys:
        o('variable', 'F22Fail' + k, Value='0.0')
        not_('F22FailNot' + k, 'F22Fail%s.Output' % k)
        o('event_value', 'F22FailSet' + k, Input='1.0', Events=' F22Fail%s.Set ' % k)
        o('event_value', 'F22FailClear' + k, Input='0.0', Events=' F22Fail%s.Set ' % k)
        o('event_value', 'F22FailToggle' + k, Input='F22FailNot%s.Output' % k, Events=' F22Fail%s.Set ' % k)
    o('logic_and', 'F22FailDual', Inputs=' F22FailFlame1.Output F22FailFlame2.Output ')
    o('event_value', 'F22FailSetDual', Input='1.0', Events=' F22FailFlame1.Set F22FailFlame2.Set ')
    o('event_value', 'F22FailClearDual', Input='0.0', Events=' F22FailFlame1.Set F22FailFlame2.Set ')
    o('event_demultiplexer', 'F22FailToggleDual', InputSelect='F22FailDual.Output',
      Events=' F22FailSetDual.Trigger F22FailClearDual.Trigger ')
    o('integral', 'F22SimTime', Input='1.0', Value=0.0)

    # ---- engines
    for k in (1, 2):
        # what the pilot commands: throttle out of cut-off and FADEC on. Shutting it down clears a flameout
        # the fire switch (ENG page) shuts the fuel off like the FADEC does
        o('variable', 'F22FireHandle%d' % k, Value='0.0')
        not_('F22FireHandleIn%d' % k, 'F22FireHandle%d.Output' % k)
        o('logic_and', 'F22EngCmd%d' % k, Inputs=' ThrustLever%dRun.Output F22Fadec%dOn.Output F22FireHandleIn%d.Output '
          % (k, k, k))
        o('event_edge_falling', 'F22EngShutdown%d' % k, Input='F22EngCmd%d.Output' % k,
          Events=' F22FailClearFlame%d.Trigger ' % k, Threshold=0.5)
        o('variable', 'F22Seized%d' % k, Value='0.0')
        not_('F22NotSeized%d' % k, 'F22Seized%d.Output' % k)
        o('event_value', 'F22Seize%d' % k, Input='1.0', Events=' F22Seized%d.Set ' % k)
        o('logic_and', 'F22EngOk%d' % k, Inputs=' F22FailNotFlame%d.Output F22NotSeized%d.Output F22FireHandleIn%d.Output '
          % (k, k, k))
        add_inputs('Engine%dRunWithFuel' % k, 'F22EngOk%d.Output' % k)
        # a seized engine: no starter turns it, no airflow windmills it (its pumps and generator stop)
        o('product', 'F22StartUnlessSeized%d' % k, Inputs=' Engine%dStartRequest.Output F22NotSeized%d.Output ' % (k, k))
        setv(dyn_node('Engine%dStarterSetOn' % k), 'Input0', 'F22StartUnlessSeized%d.Output' % k)
        o('product', 'F22Windmill%d' % k, Inputs=' F22WindmillN2.Output F22NotSeized%d.Output ' % k)
        setv(dyn_node('F22Eng%dGearboxN2' % k), 'Inputs', ' Engine%dN2.Output F22Windmill%d.Output ' % (k, k))
        # oil: pressure gone at once; turning without oil wears it out - 60 s at full N2, ~90 s at idle
        o('product', 'F22OilN2%d' % k, Inputs=' Engine%dN2.Output F22FailNotOil%d.Output ' % (k, k))
        setv(dyn_node('Engine%dOilPressure' % k), 'Input', 'F22OilN2%d.Output' % k)
        o('product', 'F22OilWear%d' % k, Inputs=' F22FailOil%d.Output Engine%dN2.Output %.6f ' % (k, k, 1 / 60.0))
        o('integral_clamped', 'F22OilDamage%d' % k, Input='F22OilWear%d.Output' % k, Range=' 0.0 1.0 ', Value=0.0)
        o('logic_greater', 'F22OilSeizing%d' % k, Input0='F22OilDamage%d.Output' % k, Input1='0.999')
        o('event_edge_rising', 'F22OilSeize%d' % k, Input='F22OilSeizing%d.Output' % k, Events=' F22Seize%d.Trigger ' % k,
          Value=1.0, Threshold=0.5)
        o('logic_and', 'F22OilLow%d' % k, Inputs=' F22FailOil%d.Output DCBusEssentialOn.Output ' % k)
        # afterburner: the lever (and the A/T's) held at full dry thrust; the ram boost at full dry stays
        o('mixlinear', 'F22AbCap%d' % k, Input0='F22FailAb%d.Output' % k, Input1='1.0', Weight0=-0.205, Weight1=1.0)
        o('minimum', 'F22AbLever%d' % k, Inputs=' Engine%dLeverEffective.Output F22AbCap%d.Output ' % (k, k))
        setv(dyn_node('Engine%dLeverShaped' % k), 'Input', 'F22AbLever%d.Output' % k)
        ab_on = dyn_node('Engine%dAfterburnerSetOn' % k)
        o('minimum', 'F22AbLeverRaw%d' % k, Inputs=' %s F22AbCap%d.Output ' % (ab_on.get('Input0').strip(), k))
        o('logic_greater', 'F22AbAsked%d' % k, Input0=ab_on.get('Input0').strip(), Input1='0.799')
        setv(ab_on, 'Input0', 'F22AbLeverRaw%d.Output' % k)
        o('logic_and', 'F22AbWarn%d' % k, Inputs=' F22FailAb%d.Output F22AbAsked%d.Output ' % (k, k))
        # ICAWS L / R ENG: airborne, commanded to run, not running (flameout, seizure, no fuel)
        o('logic_and', 'F22EngOut%d' % k, Inputs=' F22AtAirborne.Output F22EngCmd%d.Output Engine%dNotRunning.Output ' % (k, k))
        # generator: a trip (cleared by cycling its switch); GEN ARC keeps the left one off
        gen_ok = ' F22FailNotGen%d.Output ' % k + ('F22FailNotGenArc.Output ' if k == 1 else '')
        o('logic_and', 'F22GenOk%d' % k, Inputs=gen_ok)
        add_inputs('Engine%dGeneratorDesired' % k, 'F22GenOk%d.Output' % k)
        o('event_edge_rising', 'F22GenSwitchOn%d' % k, Input='Engine%dGeneratorSwitch.Output' % k,
          Events=' F22FailClearGen%d.Trigger ' % k + ('F22GenArcIgnite.Trigger ' if k == 1 else ''),
          Value=1.0, Threshold=0.5)
    o('event_demultiplexer', 'F22GenArcIgnite', InputSelect='F22FailGenArc.Output',
      Events=' DEV0.Trigger F22FailSetFire1.Trigger ')

    # ---- fire, bleed air
    o('variable', 'F22ExtBottle', Value='1.0')
    o('event_value', 'F22ExtUse', Input='0.0', Events=' F22ExtBottle.Set ')
    for k in (1, 2):
        other = 3 - k
        not_('F22EngFuelCut%d' % k, 'F22EngCmd%d.Output' % k)
        o('mixlinear', 'F22FireRate%d' % k, Input0='F22EngCmd%d.Output' % k, Input1='1.0', Weight0=0.5, Weight1=0.5)
        o('product', 'F22FireHeat%d' % k, Inputs=' F22FailFire%d.Output F22FireRate%d.Output ' % (k, k))
        o('integral_clamped', 'F22FireBurn%d' % k, Input='F22FireHeat%d.Output' % k, Range=' 0.0 1000.0 ', Value=0.0)
        o('logic_greater', 'F22FireHydLost%d' % k, Input0='F22FireBurn%d.Output' % k, Input1='40.0')
        o('logic_greater', 'F22FireEngLost%d' % k, Input0='F22FireBurn%d.Output' % k, Input1='80.0')
        o('event_edge_rising', 'F22FireSeize%d' % k, Input='F22FireEngLost%d.Output' % k, Events=' F22Seize%d.Trigger ' % k,
          Value=1.0, Threshold=0.5)
        o('logic_greater', 'F22FireSpread%d' % k, Input0='F22FireBurn%d.Output' % k, Input1='150.0')
        o('logic_and', 'F22FireWarn%d' % k, Inputs=' F22FailFire%d.Output DCBusEssentialOn.Output ' % k)
        # fire switch: state 0 in -> press shuts the fuel off; 2 out with the bottle -> press discharges it (the fire
        # goes out: the fuel is off); 1 out, bottle gone -> press gives the fuel back. One bottle for both sides
        o('product', 'F22ExtArmed%d' % k, Inputs=' F22FireHandle%d.Output F22ExtBottle.Output ' % k)
        o('mixlinear', 'F22FireSwitch%d' % k, Input0='F22FireHandle%d.Output' % k, Input1='F22ExtArmed%d.Output' % k,
          Weight0=1.0, Weight1=1.0)
        o('event_value', 'F22FireHandlePull%d' % k, Input='1.0', Events=' F22FireHandle%d.Set ' % k)
        o('event_value', 'F22FireHandlePush%d' % k, Input='0.0', Events=' F22FireHandle%d.Set ' % k)
        o('event_value', 'F22ExtFire%d' % k, Input='0.0', Events=' F22FailClearFire%d.Trigger F22ExtUse.Trigger ' % k)
        o('event_demultiplexer', 'F22FireSwitchPress%d' % k, InputSelect='F22FireSwitch%d.Output' % k,
          Events=' F22FireHandlePull%d.Trigger F22FireHandlePush%d.Trigger F22ExtFire%d.Trigger ' % (k, k, k))
        # bleed leak: heats the bay above 70 % N2, a fire when it reaches 1 (a minute at full power)
        o('linear_interpolation', 'F22BleedHot%d' % k, Input='Engine%dN2.Output' % k, Map=' (0.70 0.0) (1.0 %.6f) ' % (1 / 60.0))
        o('product', 'F22BleedRate%d' % k, Inputs=' F22FailBleed%d.Output F22BleedHot%d.Output ' % (k, k))
        o('integral_clamped', 'F22BleedHeat%d' % k, Input='F22BleedRate%d.Output' % k, Range=' 0.0 1.0 ', Value=0.0)
        o('logic_greater', 'F22BleedOverheat%d' % k, Input0='F22BleedHeat%d.Output' % k, Input1='0.999')
        o('event_edge_rising', 'F22BleedFire%d' % k, Input='F22BleedOverheat%d.Output' % k,
          Events=' F22FailSetFire%d.Trigger ' % k, Value=1.0, Threshold=0.5)
        o('logic_and', 'F22BleedWarn%d' % k, Inputs=' F22FailBleed%d.Output DCBusEssentialOn.Output ' % k)
        # hydraulics: a leak empties the system in 60 s (GEN ARC's burnt line: 180 s), fire burns its pump
        arc = ('F22FailGenArc.Output', 1 / 180.0) if k == 1 else ('0.0', 0.0)
        o('mixlinear', 'F22HydLeakRate%d' % k, Input0='F22FailHyd%d.Output' % k, Weight0=1 / 60.0, Input1=arc[0], Weight1=arc[1])
        o('integral_clamped', 'F22HydLeak%d' % k, Input='F22HydLeakRate%d.Output' % k, Range=' 0.0 1.0 ', Value=0.0)
        o('mixlinear', 'F22HydLeft%d' % k, Input0='F22HydLeak%d.Output' % k, Input1='1.0', Weight0=-1.0, Weight1=1.0)
        not_('F22HydNotBurnt%d' % k, 'F22FireHydLost%d.Output' % k)
        not_('F22HydNotReached%d' % k, 'F22FireSpread%d.Output' % other)
        sysn = dyn_node('F22HydSystem%d' % k)
        o('maximum', 'F22HydSupply%d' % k, Inputs=sysn.get('Inputs'))
        sysn.type = 'product'
        sysn.set('Inputs', ' F22HydSupply%d.Output F22HydLeft%d.Output F22HydNotBurnt%d.Output F22HydNotReached%d.Output '
                 % (k, k, k, k))

    # ---- what the engine page shows before it goes (user 2026-11-09: the seizure came with no warning but a clock).
    # A dry bearing shakes, then drags: VIB on the ENG page climbs, then EGT; a fire reaching the casing from 50 s
    # shakes it too; a bleed leak loses compressor air, the FADEC holds thrust with a hotter turbine. All estimates
    # (no F119 figures). VIB on the page = value x 100 (the Hornet's 0.015 at full power reads 1.5)
    for k in (1, 2):
        o('linear_interpolation', 'F22FireCasing%d' % k, Input='F22FireBurn%d.Output' % k, Map=' (50.0 0.0) (80.0 1.0) ')
        o('maximum', 'F22EngDamage%d' % k, Inputs=' F22OilDamage%d.Output F22FireCasing%d.Output ' % (k, k))
        o('linear_interpolation', 'F22VibDamage%d' % k, Input='F22EngDamage%d.Output' % k,
          Map=' (0.0 0.0) (0.3 0.003) (0.7 0.015) (1.0 0.05) ')
        o('product', 'F22VibExtra%d' % k, Inputs=' F22VibDamage%d.Output Engine%dN2.Output ' % (k, k))
        vib = dyn_node('Engine%dVibration' % k)
        vib.name = 'F22Vib%dBase' % k
        o('sum', 'Engine%dVibration' % k, Inputs=' F22Vib%dBase.Output F22VibExtra%d.Output ' % (k, k))
        o('linear_interpolation', 'F22EgtOil%d' % k, Input='F22OilDamage%d.Output' % k,
          Map=' (0.0 0.0) (0.5 5.0) (0.8 30.0) (1.0 90.0) ')
        o('linear_interpolation', 'F22EgtBleedN2%d' % k, Input='Engine%dN2.Output' % k, Map=' (0.70 0.0) (1.0 35.0) ')
        o('product', 'F22EgtBleed%d' % k, Inputs=' F22FailBleed%d.Output F22EgtBleedN2%d.Output ' % (k, k))
        o('product', 'F22EgtOilHot%d' % k, Inputs=' F22EgtOil%d.Output Engine%dN2.Output ' % (k, k))
        egt = dyn_node('Engine%dExhaustGasTemperature' % k)
        egt.name = 'F22Egt%dBase' % k
        o('sum', 'Engine%dExhaustGasTemperature' % k,
          Inputs=' F22Egt%dBase.Output F22EgtOilHot%d.Output F22EgtBleed%d.Output ' % (k, k, k))
        # seized: the computers see a stopped engine in the airflow - no relight
        o('logic_and', 'F22SeizedWarn%d' % k, Inputs=' F22Seized%d.Output DCBusEssentialOn.Output ' % k)
        # rough running (the feel block, user 2026-11-09): a damaged engine hunts - the thrust swings a few per cent,
        # two beats against each other so it is not a metronome (each engine its own); heard in its sound, felt as yaw
        for ab, (f, w) in zip('AB', ((0.83 + 0.08 * k, 0.6), (2.3 - 0.2 * k, 0.4))):
            o('product', 'F22RoughPhase%s%d' % (ab, k), Inputs=' F22SimTime.Output %.3f ' % f)
            o('clamp_cyclic', 'F22RoughCyc%s%d' % (ab, k), Input='F22RoughPhase%s%d.Output' % (ab, k),
              Range=('string8', ' 0.0 1.0 '))
            o('linear_interpolation', 'F22RoughTri%s%d' % (ab, k), Input='F22RoughCyc%s%d.Output' % (ab, k),
              Map=' (0.0 0.0) (0.5 %.2f) (1.0 0.0) ' % w)
        o('sum', 'F22RoughWave%d' % k, Inputs=' F22RoughTriA%d.Output F22RoughTriB%d.Output ' % (k, k))
        o('linear_interpolation', 'F22RoughDepth%d' % k, Input='F22EngDamage%d.Output' % k,
          Map=' (0.3 0.0) (0.7 0.04) (1.0 0.10) ')
        o('product', 'F22RoughDip%d' % k, Inputs=' F22RoughDepth%d.Output F22RoughWave%d.Output ' % (k, k))
        o('mixlinear', 'F22RoughFactor%d' % k, Input0='F22RoughDip%d.Output' % k, Input1='1.0', Weight0=-1.0, Weight1=1.0)
        o('product', 'F22RoughLever%d' % k, Inputs=' F22AbLever%d.Output F22RoughFactor%d.Output ' % (k, k))
        setv(dyn_node('Engine%dLeverShaped' % k), 'Input', 'F22RoughLever%d.Output' % k)
        # a seized rotor stops in ~1.5 s, not as a shut-down engine runs down (the game's spool keeps turning, with no
        # fuel and no thrust): N1 / N2 - the pages, the engine sound, the pumps and generator - follow the rotor
        o('mixlinear', 'F22SeizeStopRate%d' % k, Input0='F22Seized%d.Output' % k, Input1='F22NotSeized%d.Output' % k,
          Weight0=1 / 1.5, Weight1=-10.0)
        o('integral_clamped', 'F22SeizeStop%d' % k, Input='F22SeizeStopRate%d.Output' % k, Range=' 0.0 1.0 ', Value=0.0)
        o('mixlinear', 'F22SeizeSpin%d' % k, Input0='F22SeizeStop%d.Output' % k, Input1='1.0', Weight0=-1.0, Weight1=1.0)
        for n in ('N1', 'N2'):
            node = dyn_node('Engine%d%s' % (k, n))
            node.name = 'F22%sRaw%d' % (n, k)
            o('product', 'Engine%d%s' % (k, n), Inputs=' F22%sRaw%d.Output F22SeizeSpin%d.Output ' % (n, k, k))

    # ---- the hydraulic users split between the systems, the usual fighter layout (F-22's is not public, estimate):
    # both systems fly every surface (one lost changes nothing in the air); the right (utility) one also moves the
    # gear, the wheel brakes and nose-wheel steering, the left one the weapon bay doors. R HYD lost: the gear does not
    # retract (selected down it falls free), the brakes have the accumulator only (~8 s), no steering. L HYD lost: the
    # bay doors stay where they are
    setv(dyn_node('F22GearHydOK'), 'Input0', 'F22HydSystem2.Output')
    brake = dyn_node('F22BrakeSupply')
    assert brake.get('Inputs').split() == ['F22HydAuthority.Output', 'F22BrakeAccCharged.Output'], brake.get('Inputs')
    setv(brake, 'Inputs', ' F22HydSystem2.Output F22BrakeAccCharged.Output ')
    steer = dyn_node('F22HydCmdServoSteering')      # (the command; F22HydServoSteering is its flow-limited follower)
    st = steer.get('Inputs').split()
    assert st[-1] == 'F22HydAuthority.Output', st
    setv(steer, 'Inputs', ' %s F22HydSystem2.Output ' % ' '.join(st[:-1]))
    o('logic_greater', 'F22BayHydOK', Input0='F22HydSystem1.Output', Input1='0.5')
    for bay in ('Center', 'Left', 'Right'):
        door = dyn_node('F22Bay' + bay)
        o('state_frozen', 'F22BayHeld' + bay, Input=door.get('Input').strip(), InputEnable='F22BayHydOK.Output', Value=0.0)
        setv(door, 'Input', 'F22BayHeld%s.Output' % bay)

    # ---- fuel leak, screens, antiskid, air data, oxygen
    o('product', 'F22FuelLeakFlow', Inputs=' F22FailFuelLeak.Output 0.3 ')
    add_inputs('FuelFlowTotal', 'F22FuelLeakFlow.Output')
    for name, key in (('DDILeftOn', 'Mfd1'), ('MPCDOn', 'Pmfd')):
        n = dyn_node(name)
        o('product', 'F22Screen' + name, Inputs=' %s F22FailNot%s.Output ' % (n.get('Input0').strip(), key))
        setv(n, 'Input0', 'F22Screen%s.Output' % name)
    sk = dyn_node('AntiSkidOn')
    o('logic_and', 'F22AntiskidEnable', Inputs=' %s F22FailNotAntiskid.Output ' % sk.get('InputEnable').strip())
    setv(sk, 'InputEnable', 'F22AntiskidEnable.Output')
    # a generator dropping off: its bus changes over, the display on it blinks for 0.3 s (left gen - left MFD,
    # right gen - right MFD)
    for k in (1, 2):
        o('variable', 'F22BusBlink%d' % k, Value='0.0')
        o('event_value', 'F22BusBlinkOn%d' % k, Input='1.0', Events=' F22BusBlink%d.Set ' % k)
        o('event_value', 'F22BusBlinkOff%d' % k, Input='0.0', Events=' F22BusBlink%d.Set ' % k)
        o('event_edge_rising', 'F22GenDrop%d' % k, Input='Engine%dGeneratorCaution.Output' % k,
          Events=' F22BusBlinkOn%d.Trigger ' % k, Value=1.0, Threshold=0.5)
        o('logic_confirm_delay', 'F22BusBlinkLong%d' % k, Input='F22BusBlink%d.Output' % k, TimeUp=0.3, TimeDown=0.0001,
          Threshold=0.5)
        o('event_edge_rising', 'F22BusBlinkEnd%d' % k, Input='F22BusBlinkLong%d.Output' % k,
          Events=' F22BusBlinkOff%d.Trigger ' % k, Value=1.0, Threshold=0.5)
        not_('F22BusSteady%d' % k, 'F22BusBlink%d.Output' % k)
    add_inputs('F22ScreenDDILeftOn', 'F22BusSteady1.Output')
    ddr = dyn_node('DDIRightOn')
    o('product', 'F22ScreenDDIRightOn', Inputs=' %s F22BusSteady2.Output ' % ddr.get('Input0').strip())
    setv(ddr, 'Input0', 'F22ScreenDDIRightOn.Output')
    o('state_frozen', 'F22PitotTotal', Input='PitotTube.TotalPressure', InputEnable='F22FailNotPitot.Output', Value=101325.0)
    setv(D['AirDataComputer'], 'InputTotalPressure0', 'F22PitotTotal.Output')
    o('logic_confirm_delay', 'F22AirDataWarn', Input='F22FailPitot.Output', TimeUp=8.0, TimeDown=0.0001, Threshold=0.5)
    # what the air really does (windmill, buffet, wind noise, the COND triggers) reads the raw probe, not the
    # blocked one: only the computers and the displays are fooled (in-game 2026-11-09: IAS fell to 0 in a descent)
    for name in ('F22WindmillN2', 'F22BuffetSpeed', 'F22SoundCas'):
        n = dyn_node(name)
        assert n.get('Input').strip() == 'AirDataComputer.OutputCalibratedAirspeed', name
        setv(n, 'Input', 'AirspeedIndicator.IndicatedAirspeed')
    o('logic_greater', 'F22Above10k', Input0='AirDataComputer.OutputAltitude', Input1='3048.0')
    o('product', 'F22BosUse', Inputs=' F22FailObogs.Output F22Above10k.Output %.6f ' % (1 / 600.0))
    o('integral_clamped', 'F22Bos', Input='F22BosUse.Output', Range=' 0.0 1.0 ', Value=0.0)
    o('logic_greater', 'F22BosEmpty', Input0='F22Bos.Output', Input1='0.999')
    o('logic_and', 'F22OxyLow', Inputs=' F22BosEmpty.Output F22Above10k.Output F22FailObogs.Output ')
    o('logic_and', 'F22ObogsWarn', Inputs=' F22FailObogs.Output DCBusEssentialOn.Output ')
    o('logic_and', 'F22NozzleWarn', Inputs=' F22FailNozzle.Output ')

    # ---- caused by flying (COND)
    # on from the start (user 2026-11-15: the aircraft breaks by how it is flown without first opening the page)
    o('variable', 'F22FailCond', Value='1.0')
    not_('F22FailCondOff', 'F22FailCond.Output')
    o('event_value', 'F22FailCondToggle', Input='F22FailCondOff.Output', Events=' F22FailCond.Set ')
    # gear: extended (or moving) above 300 kt for 3 s - damaged, it stays down (our limit: the F-22's is not public)
    o('variable', 'F22GearDamaged', Value='0.0')
    o('logic_greater', 'F22GearNotUp', Input0='GearSequence.Output', Input1='0.05')
    # the gear out in a fast airflow rumbles before anything breaks (the buffet sound, raw airspeed)
    o('linear_interpolation', 'F22GearAirLoad', Input='AirspeedIndicator.IndicatedAirspeed',
      Map=' (128.6 0.0) (154.3 0.5) (180.0 1.0) ')
    o('product', 'F22GearBuffet', Inputs=' F22GearAirLoad.Output F22GearNotUp.Output ')
    add_inputs('F22BuffetAny', 'F22GearBuffet.Output')
    o('logic_greater', 'F22GearTooFast', Input0='AirspeedIndicator.IndicatedAirspeed', Input1='154.3')
    o('logic_and', 'F22GearOverspeedNow', Inputs=' F22FailCond.Output F22GearNotUp.Output F22GearTooFast.Output ')
    o('logic_confirm_delay', 'F22GearOverspeed', Input='F22GearOverspeedNow.Output', TimeUp=3.0, TimeDown=0.0001,
      Threshold=0.5)
    o('event_value', 'F22GearBreak', Input='1.0', Events=' F22GearDamaged.Set ')
    o('event_edge_rising', 'F22GearOverspeedHit', Input='F22GearOverspeed.Output', Events=' F22GearBreak.Trigger ',
      Value=1.0, Threshold=0.5)
    o('logic_and', 'F22GearStuckDown', Inputs=' F22GearDamaged.Output F22GearIsDown.Output ')
    add_inputs('F22GearTarget', 'F22GearStuckDown.Output')
    # hard landing (2026-11-10): the sink rate at touchdown (the inertial vertical speed, held from the last moment in
    # the air). Over 10 ft/s, the USAF design limit sink rate for land-based aircraft (MIL-A-8863): HARD LDG, an
    # inspection. Over 15 ft/s (x 1.5, the ultimate factor): the main strut that takes the harder hit folds - its own
    # retraction cylinder pulls it up under the load (no breakable joint: a torn-off body ends the flight on contact)
    o('linear', 'F22SinkLive', Input='InertialReferenceSystem.OutputVerticalVelocity', Scaling=-1.0)
    o('state_frozen', 'F22TdSink', Input='F22SinkLive.Output', InputEnable='F22AtAirborne.Output', Value=0.0)
    o('logic_greater', 'F22TdHard', Input0='F22TdSink.Output', Input1='3.048')
    o('logic_greater', 'F22TdSevere', Input0='F22TdSink.Output', Input1='4.572')
    o('logic_and', 'F22TdHardCond', Inputs=' F22TdHard.Output F22FailCond.Output ')
    o('logic_and', 'F22TdSevereCond', Inputs=' F22TdSevere.Output F22FailCond.Output ')
    o('variable', 'F22HardLanding', Value='0.0')
    o('event_value', 'F22HardLandingSet', Input='1.0', Events=' F22HardLanding.Set ')
    for side in ('L', 'R'):
        o('variable', 'F22Collapse' + side, Value='0.0')
        o('event_value', 'F22CollapseSet' + side, Input='1.0', Events=' F22Collapse%s.Set ' % side)
    o('logic_greater', 'F22TdLeftHarder', Input0='LeftWheelHull.Load', Input1='RightWheelHull.Load')
    o('event_demultiplexer', 'F22CollapsePick', InputSelect='F22TdLeftHarder.Output',
      Events=' F22CollapseSetR.Trigger F22CollapseSetL.Trigger ')
    o('event_demultiplexer', 'F22TdHardHit', InputSelect='F22TdHardCond.Output', Events=' DEV0.Trigger F22HardLandingSet.Trigger ')
    # sheared strut (block 3, 2026-11-11): over 20 ft/s (twice the design limit, estimate) the harder-hit main strut does
    # not fold - it breaks below the leg: the lower strut and the wheel come off and roll away (breakage_f22.gear_shear),
    # the aircraft sits down on the broken leg. 15 - 20 ft/s still folds it. The nose strut breaks under a load on its
    # wheel past NOSE_SHEAR_N (6.5 x the static one) for 0.05 s (a nose-first touchdown or a slam-down; estimate)
    o('logic_greater', 'F22TdShear', Input0='F22TdSink.Output', Input1='%.3f' % (SHEAR_SINK_FPS * 0.3048))
    o('logic_and', 'F22TdShearCond', Inputs=' F22TdShear.Output F22FailCond.Output ')
    not_('F22TdNoShear', 'F22TdShear.Output')
    o('logic_and', 'F22TdFoldCond', Inputs=' F22TdSevereCond.Output F22TdNoShear.Output ')
    for side in ('L', 'R', 'N'):
        o('variable', 'F22Shear' + side, Value='0.0')
        o('event_value', 'F22ShearSet' + side, Input='1.0', Events=' F22Shear%s.Set ' % side)
    o('event_demultiplexer', 'F22ShearPick', InputSelect='F22TdLeftHarder.Output',
      Events=' F22ShearSetR.Trigger F22ShearSetL.Trigger ')
    o('event_demultiplexer', 'F22TdSevereHit', InputSelect='F22TdFoldCond.Output', Events=' DEV0.Trigger F22CollapsePick.Trigger ')
    o('event_demultiplexer', 'F22TdShearHit', InputSelect='F22TdShearCond.Output', Events=' DEV0.Trigger F22ShearPick.Trigger ')
    o('logic_greater', 'F22NoseOverload', Input0='NoseWheelLoad.Output', Input1='%.0f' % NOSE_SHEAR_N)
    o('logic_and', 'F22NoseOverloadCond', Inputs=' F22NoseOverload.Output F22FailCond.Output ')
    o('logic_confirm_delay', 'F22NoseOverloadHeld', Input='F22NoseOverloadCond.Output', TimeUp=0.05, TimeDown=0.0001,
      Threshold=0.5)
    o('event_edge_rising', 'F22NoseShearHit', Input='F22NoseOverloadHeld.Output', Events=' F22ShearSetN.Trigger ',
      Value=1.0, Threshold=0.5)
    # 0.15 s after the first wheel touches: the strut loads have built, the harder side decides
    o('logic_confirm_delay', 'F22TdSettled', Input='OnGroundSensor.Output', TimeUp=0.15, TimeDown=0.0001, Threshold=0.5)
    # the shown value: kept from the touch (F22TdSink itself follows the live sink while in the air - the FAIL page
    # read -1614 in a climb, in-game 2026-11-10)
    o('variable', 'F22TdSinkLast', Value='0.0')
    o('event_value', 'F22TdSinkKeep', Input='F22TdSink.Output', Events=' F22TdSinkLast.Set ')
    o('event_edge_rising', 'F22Touchdown', Input='F22TdSettled.Output',
      Events=' F22TdHardHit.Trigger F22TdSevereHit.Trigger F22TdShearHit.Trigger F22TdSinkKeep.Trigger ', Value=1.0,
      Threshold=0.5)
    # (the cylinder command through a rate limit, GEAR_CTL_RATE: a fold, a jam or RST stepped it a whole stroke in a
    # frame - K 5e7 N/m x 0.67 m: ~33 MN into the airframe, and RST tore the left wing off, in-game 2026-11-11 / 12.
    # The handle's own sequence moves it at 0.75 / s: through the limit unchanged)
    # A fold is a failure, not a retraction (user 2026-11-13: "they just go in as if all were well"): the side brace /
    # down-lock lets go and the leg swings back under the aircraft's weight in a fraction of a second, stopping where it
    # jams - the airframe on the runway, the leg wedged under it, not stowed. Its own travel F22FoldFrac: up to 80 % of
    # the leg's travel (FOLD_STOP, the cylinder command for it from the cylinder geometry: the wheel rises 0.76 m main /
    # 1.04 m nose - the aircraft sits down on the belly) at FOLD_RATE; back down slowly on RST. Drawn broken: gear_graphics
    for side, name in (('L', 'Left'), ('R', 'Right')):
        cyl = dyn_node(name + 'GearCyclinder')
        assert cyl.get('Control').strip() == 'MapMainGear.Output', cyl.get('Control')
        o('maximum', 'F22MainGear%s' % side, Inputs=' MapMainGear.Output ')
        o('servoclassic', 'F22MainGearCtl%s' % side, Input='F22MainGear%s.Output' % side, Speed=GEAR_CTL_RATE, P1=1.0)
        fold_travel(o, side)
        o('maximum', 'F22MainGearCyl%s' % side, Inputs=' F22MainGearCtl%s.Output F22FoldFrac%s.Output ' % (side, side))
        setv(cyl, 'Control', 'F22MainGearCyl%s.Output' % side)
    o('logic_or', 'F22GearWarn', Inputs=' F22GearDamaged.Output F22CollapseL.Output F22CollapseR.Output '
                                        'F22ShearL.Output F22ShearR.Output F22ShearN.Output ')
    # negative g held 30 s: fuel and oil starve (estimate), both engines flame out
    o('logic_greater', 'F22NegG', Input0='-4.9', Input1='Accelerometer.Acceleration')
    o('logic_and', 'F22NegGNow', Inputs=' F22FailCond.Output F22NegG.Output F22AtAirborne.Output ')
    o('logic_confirm_delay', 'F22NegGLong', Input='F22NegGNow.Output', TimeUp=30.0, TimeDown=0.0001, Threshold=0.5)
    o('event_edge_rising', 'F22NegGStarve', Input='F22NegGLong.Output', Events=' F22FailSetDual.Trigger ',
      Value=1.0, Threshold=0.5)
    # deep stall in afterburner: the inlet flow breaks down, one engine stalls out. The F119 and its inlets are built
    # for high-AoA flight with the nozzles vectoring - the F-22's display flying does it in afterburner - so only past
    # that envelope: > 60 deg AoA, < 60 kt, 3 s (was 50 deg / 100 kt / 2 s, a fighter's usual limit; softened at the
    # user's wish 2026-11-15)
    o('logic_greater', 'F22StallAoa', Input0='PitotTube.AngleOfAttack', Input1='1.0472')
    o('logic_greater', 'F22StallSlow', Input0='30.9', Input1='AirspeedIndicator.IndicatedAirspeed')
    o('logic_or', 'F22StallAb', Inputs=' Engine1AfterburnerSetOn.Output Engine2AfterburnerSetOn.Output ')
    o('logic_and', 'F22StallNow', Inputs=' F22FailCond.Output F22StallAoa.Output F22StallSlow.Output F22StallAb.Output '
                                         'F22AtAirborne.Output ')
    o('logic_confirm_delay', 'F22StallHeld', Input='F22StallNow.Output', TimeUp=3.0, TimeDown=0.0001, Threshold=0.5)
    o('product', 'F22StallSideRaw', Inputs=' F22SimTime.Output 7.77 ')
    o('clamp_cyclic', 'F22StallSideCyc', Input='F22StallSideRaw.Output', Range=('string8', ' 0.0 1.0 '))
    # (event_select casts its value to an integer itself: 0.5 .. 1.48 is 0 or 1 whether it truncates or rounds;
    # no stock aircraft uses the floor class)
    o('mixlinear', 'F22StallSide', Input0='F22StallSideCyc.Output', Input1='1.0', Weight0=0.98, Weight1=0.5)
    o('event_select', 'F22StallSelect', Events=' F22FailSetFlame1.Trigger F22FailSetFlame2.Trigger ')
    o('event_value', 'F22StallPick', Input='F22StallSide.Output', Events=' F22StallSelect.Trigger ')
    o('event_edge_rising', 'F22StallHit', Input='F22StallHeld.Output', Events=' F22StallPick.Trigger ', Value=1.0,
      Threshold=0.5)
    # brakes: heat from braking work (pedal x ground speed), cooling in ~10 min; hot from 1.0, then they fade.
    # Checked offline (scratchpad simfail.py): a full stop from 130 kt ~0.5, a rejected takeoff at 150 kt ~0.7, so two
    # hard stops close together make them hot (estimates); cooling takes 1.0 off in 10 min
    o('product', 'F22BrakeWork', Inputs=' F22FailCond.Output F22BrakeDemand.Output InertialReferenceSystem.OutputGroundSpeed ')
    o('mixlinear', 'F22BrakeHeatRate', Input0='F22BrakeWork.Output', Input1='1.0', Weight0=1 / 800.0, Weight1=-1 / 600.0)
    o('integral_clamped', 'F22BrakeHeat', Input='F22BrakeHeatRate.Output', Range=' 0.0 2.0 ', Value=0.0)
    o('logic_greater', 'F22BrakeHot', Input0='F22BrakeHeat.Output', Input1='1.0')
    o('linear_interpolation', 'F22BrakeFade', Input='F22BrakeHeat.Output', Map=' (1.0 1.0) (2.0 0.3) ')
    for side in ('Left', 'Right'):
        add_inputs('F22%sBrakePowered' % side, 'F22BrakeFade.Output')
    # tyre burst (2026-11-10), two real ways: a wheel locked under hard braking with the antiskid off (or failed) -
    # the skid wears through the tyre in a second; or braking on with the brakes far past BRK HOT (heat 1.8 of 2) - the
    # tyre overheats (the fusible plugs that let a tyre down slowly after a hot stop are not modelled). The side with
    # the harder pedal goes. A burst wheel runs on its rim: its brake does next to nothing, the rim drags (as 35 % of
    # that brake, estimate) - the jet pulls towards it; a bang at the wheel. RST restores
    not_('F22AntiskidOff', 'AntiSkidOn.Output')
    o('logic_greater', 'F22BrakeHard', Input0='F22BrakeDemand.Output', Input1='0.8')
    o('logic_greater', 'F22BrakeOn', Input0='F22BrakeDemand.Output', Input1='0.3')
    o('logic_greater', 'F22RollFast', Input0='InertialReferenceSystem.OutputGroundSpeed', Input1='30.0')
    o('logic_greater', 'F22RollSome', Input0='InertialReferenceSystem.OutputGroundSpeed', Input1='15.0')
    o('logic_greater', 'F22BrakeCooked', Input0='F22BrakeHeat.Output', Input1='1.8')
    o('logic_and', 'F22SkidNow', Inputs=' F22FailCond.Output OnGroundSensor.Output F22AntiskidOff.Output F22BrakeHard.Output '
                                        'F22RollFast.Output ')
    o('logic_and', 'F22CookNow', Inputs=' F22FailCond.Output OnGroundSensor.Output F22BrakeCooked.Output F22BrakeOn.Output '
                                        'F22RollSome.Output ')
    o('logic_confirm_delay', 'F22SkidLong', Input='F22SkidNow.Output', TimeUp=1.0, TimeDown=0.0001, Threshold=0.5)
    o('logic_confirm_delay', 'F22CookLong', Input='F22CookNow.Output', TimeUp=2.0, TimeDown=0.0001, Threshold=0.5)
    o('logic_or', 'F22TyreKill', Inputs=' F22SkidLong.Output F22CookLong.Output ')
    o('logic_greater', 'F22TyreLeftHarder', Input0='LeftBrakePedal.Output', Input1='RightBrakePedal.Output')
    for side in ('L', 'R'):
        o('variable', 'F22TyreBurst' + side, Value='0.0')
        o('event_value', 'F22TyreBurstSet' + side, Input='1.0', Events=' F22TyreBurst%s.Set ' % side)
    o('event_demultiplexer', 'F22TyrePick', InputSelect='F22TyreLeftHarder.Output',
      Events=' F22TyreBurstSetR.Trigger F22TyreBurstSetL.Trigger ')
    o('event_edge_rising', 'F22TyreBurstNow', Input='F22TyreKill.Output', Events=' F22TyrePick.Trigger ', Value=1.0,
      Threshold=0.5)
    for side, name in (('L', 'Left'), ('R', 'Right')):
        not_('F22TyreOk' + side, 'F22TyreBurst%s.Output' % side)
        o('product', 'F22%sBrakeTyre' % name, Inputs=' F22%sBrakePowered.Output F22TyreOk%s.Output ' % (name, side))
        o('product', 'F22RimDrag' + side, Inputs=' F22TyreBurst%s.Output 0.35 ' % side)
        mix = dyn_node(name + 'BrakeMix')
        assert mix.get('Inputs').split() == ['F22%sBrakePowered.Output' % name, 'ParkingBrake.Output'], mix.get('Inputs')
        setv(mix, 'Inputs', ' F22%sBrakeTyre.Output ParkingBrake.Output F22RimDrag%s.Output ' % (name, side))
    # nose tyre (2026-11-11): rolling faster than its rating - 225 kt ground speed with weight on the nose wheel for 1 s
    # (estimate: fighter tyres are rated about 200-250 kt; the F-22's is not public; the nose tyre, smallest and fastest
    # turning, goes first). On its rim (breakage_f22.tyre_hubs lowers it), the rim drags; no brake there to lose
    o('logic_greater', 'F22NoseLoaded', Input0='NoseWheelLoad.Output', Input1='2000.0')
    o('logic_greater', 'F22TyreOverspeed', Input0='InertialReferenceSystem.OutputGroundSpeed', Input1='%.2f' % (
      NOSE_TYRE_KT * 0.514444))
    o('logic_and', 'F22NoseTyreOverNow', Inputs=' F22FailCond.Output F22NoseLoaded.Output F22TyreOverspeed.Output ')
    o('logic_confirm_delay', 'F22NoseTyreOver', Input='F22NoseTyreOverNow.Output', TimeUp=1.0, TimeDown=0.0001,
      Threshold=0.5)
    o('variable', 'F22TyreBurstN', Value='0.0')
    o('event_value', 'F22TyreBurstSetN', Input='1.0', Events=' F22TyreBurstN.Set ')
    o('event_edge_rising', 'F22NoseTyreGo', Input='F22NoseTyreOver.Output', Events=' F22TyreBurstSetN.Trigger ',
      Value=1.0, Threshold=0.5)
    o('product', 'F22RimDragN', Inputs=' F22TyreBurstN.Output 0.35 ')
    for hull in ('LeftFrontWheelHull', 'RightFrontWheelHull'):
        n = dyn_node(hull)
        assert n.find('InputBrake') is None, hull
        n.set('InputBrake', 'F22RimDragN.Output', 'string8')      # (new fields: setv only changes existing ones)
        n.set('BrakeStrength', '0.5', 'float64')

    gear_dynamics(o, not_, add_inputs, dyn_node, setv)

    # ---- random: one failure 1 - 15 min after RAND, common ones three times as likely. The sim time's fine digits at
    # the press are the dice (no random generator in the configs)
    pool = [k for k, _, w in ITEMS for _ in range(w)]
    o('product', 'F22RandU1Raw', Inputs=' F22SimTime.Output 7919.37 ')
    o('clamp_cyclic', 'F22RandU1', Input='F22RandU1Raw.Output', Range=('string8', ' 0.0 1.0 '))
    # pool index for event_select (it casts to an integer): 0.5 .. P - 0.5 stays in range truncated or rounded
    o('mixlinear', 'F22RandPoolPick', Input0='F22RandU1.Output', Input1='1.0', Weight0=len(pool) - 1.0, Weight1=0.5)
    o('product', 'F22RandU2Raw', Inputs=' F22SimTime.Output 104729.71 ')
    o('clamp_cyclic', 'F22RandU2', Input='F22RandU2Raw.Output', Range=('string8', ' 0.0 1.0 '))
    o('mixlinear', 'F22RandDueNew', Input0='F22RandU2.Output', Input1='F22SimTime.Output', Weight0=840.0, Weight1=1.0,
      Offset=60.0)
    for name in ('F22RandArmed', 'F22RandIdx', 'F22RandDue'):
        o('variable', name, Value='0.0')
    o('event_value', 'F22RandIdxSet', Input='F22RandPoolPick.Output', Events=' F22RandIdx.Set ')
    o('event_value', 'F22RandDueSet', Input='F22RandDueNew.Output', Events=' F22RandDue.Set ')
    o('event_value', 'F22RandStart', Input='1.0', Events=' F22RandIdxSet.Trigger F22RandDueSet.Trigger F22RandArmed.Set ')
    o('event_value', 'F22RandStop', Input='0.0', Events=' F22RandArmed.Set ')
    o('event_demultiplexer', 'F22RandPress', InputSelect='F22RandArmed.Output',
      Events=' F22RandStart.Trigger F22RandStop.Trigger ')
    o('logic_greater', 'F22RandTimeUp', Input0='F22SimTime.Output', Input1='F22RandDue.Output')
    o('logic_and', 'F22RandDueNow', Inputs=' F22RandArmed.Output F22RandTimeUp.Output ')
    o('event_select', 'F22RandSelect', Events=' %s ' % ' '.join('F22FailSet%s.Trigger' % k for k in pool))
    o('event_value', 'F22RandFire', Input='F22RandIdx.Output', Events=' F22RandSelect.Trigger ')
    o('event_edge_rising', 'F22RandHit', Input='F22RandDueNow.Output', Events=' F22RandFire.Trigger F22RandStop.Trigger ',
      Value=1.0, Threshold=0.5)

    # ---- page keys: cursor, SEL, reset
    n_items = len(ITEMS)
    o('variable', 'F22FailCursor', Value='0.0')
    for name, step in (('Next', 1.0), ('Prev', -1.0)):
        o('mixlinear', 'F22FailCursor%sRaw' % name, Input0='F22FailCursor.Output', Input1='1.0', Weight0=1.0, Weight1=step)
        o('clamp_cyclic', 'F22FailCursor' + name, Input='F22FailCursor%sRaw.Output' % name,
          Range=('string8', ' -0.5 %.1f ' % (n_items - 0.5)))
    o('event_value', 'F22FailCursorDown', Input='F22FailCursorNext.Output', Events=' F22FailCursor.Set ')
    o('event_value', 'F22FailCursorUp', Input='F22FailCursorPrev.Output', Events=' F22FailCursor.Set ')
    o('event_select', 'F22FailSelect', Events=' %s ' % ' '.join('F22FailToggle%s.Trigger' % k for k, _, _ in ITEMS))
    o('event_value', 'F22FailSel', Input='F22FailCursor.Output', Events=' F22FailSelect.Trigger ')
    zero = ['F22Fail%s.Set' % k for k in keys] + ['F22Seized1.Set', 'F22Seized2.Set', 'F22GearDamaged.Set',
                                                   'F22RandArmed.Set', 'F22FireHandle1.Set', 'F22FireHandle2.Set',
                                                   'F22HardLanding.Set', 'F22CollapseL.Set', 'F22CollapseR.Set',
                                                   'F22TyreBurstL.Set', 'F22TyreBurstR.Set', 'F22TyreBurstN.Set',
                                                   'F22CollapseN.Set', 'F22AltGear.Set']
    # (not the sheared struts: a broken leg stays broken, as a torn-off wing - RST relocked the debris chain and snapped
    # the wheel, metres away by then, back in one frame: the jolt tore the left wing off, in-game 2026-11-11)
    o('event_value', 'F22FailResetZero', Input='0.0', Events=' %s ' % ' '.join(zero))
    o('event_value', 'F22FailResetOne', Input='1.0', Events=' F22ExtBottle.Set ')
    resets = ['F22%s%d.Reset' % (n, k) for n in ('OilDamage', 'FireBurn', 'BleedHeat', 'HydLeak') for k in (1, 2)] + \
        ['F22UpHeld%s.Reset' % k for k in 'LRN']
    o('event_value', 'F22FailReset', Input='0.0', Events=' F22FailResetZero.Trigger F22FailResetOne.Trigger %s '
      'F22Bos.Reset F22BrakeHeat.Reset Accelerometer.Reset ' % ' '.join(resets))

    # ---- hidden link: FAIL_CODE on the scratchpad, ENTR on the empty ICP page (page 0 cleared the pad before): the
    # link shows on every MFD menu and the right MFD goes to the page at once (user 2026-11-15; it toggled the link
    # before - the page then took the menu, FAIL, on an MFD)
    o('variable', 'F22FailUnlocked', Value='0.0')
    o('event_value', 'F22FailOpen', Input='1.0', Events=' F22FailUnlocked.Set SetRightMFDUFCBU.Trigger ScratchPad.Clear ')
    o('logic_equal', 'F22FailCodeMatch', Input0='ScratchPadValue.Output', Input1='%d.0' % FAIL_CODE)
    o('logic_and', 'F22FailCodeOk', Inputs=' ScratchPadValue.OutputValid F22FailCodeMatch.Output ')
    o('event_demultiplexer', 'F22FailCodeEnter', InputSelect='F22FailCodeOk.Output',
      Events=' ScratchPad.Clear F22FailOpen.Trigger ')
    ent = D['UpFrontEnterEvent']
    ev = ent.get('Events').split()
    assert ev[0] == 'ScratchPad.Clear', ev[0]
    ev[0] = 'F22FailCodeEnter.Trigger'
    setv(ent, 'Events', ' %s ' % ' '.join(ev))

    # ---- menus: the link on every MFD menu (top row, beside SYS), the FAIL page keys, the ENG page's fire switches
    # (left engine top left key, right engine top right key: side by side the vertical labels ran together)
    # two pages: the cursor runs over all items, the page shown is the cursor's; PAGE jumps to the other page's first
    o('logic_greater', 'F22FailPage2', Input0='F22FailCursor.Output', Input1='%.1f' % (PAGE_SIZE - 0.5))
    o('multiplexer', 'F22FailPageTarget', InputSelect='F22FailPage2.Output', Inputs=' %d.0 0.0 ' % PAGE_SIZE)
    o('event_value', 'F22FailPageFlip', Input='F22FailPageTarget.Output', Events=' F22FailCursor.Set ')
    o('constant_text', 'F22AltGearMenuLabel', Input='ALT GR')
    for name, text in (('Fail', 'FAIL'), ('FailSel', 'SEL'), ('FailRand', 'RAND'), ('FailCond', 'COND'), ('FailPage', 'PAGE'),
                       ('FailRst', 'RST'), ('ExtLFire', 'L FIRE'), ('ExtLFuel', 'L FUEL'), ('ExtLDsch', 'L DSCH'),
                       ('ExtRFire', 'R FIRE'), ('ExtRFuel', 'R FUEL'), ('ExtRDsch', 'R DSCH')):
        o('constant_text', 'F22%sMenuLabel' % name, Input=text)
    o('multiplexer_text', 'F22FailLinkLabel', InputSelect='F22FailUnlocked.Output',
      Inputs=' BlankLabel.Output F22FailMenuLabel.Output ')
    for side, k in (('L', 1), ('R', 2)):
        o('multiplexer_text', 'F22Ext%sLabel' % side, InputSelect='F22FireSwitch%d.Output' % k,
          Inputs=' F22Ext{0}FireMenuLabel.Output F22Ext{0}FuelMenuLabel.Output F22Ext{0}DschMenuLabel.Output '.format(side))
    for prefix in MENU_PREFIXES:
        o('event_demultiplexer', 'F22FailLink' + prefix, InputSelect='F22FailUnlocked.Output',
          Events=' DEV0.Trigger Set%sUFCBU.Trigger ' % prefix)
        for page in (D[prefix + 'TacticalMenuPage'], D[prefix + 'SupportMenuPage']):
            els = page.find('Elements').children
            assert els[3].name == 'Blank', (prefix, els[3].name)
            els[3] = menu_el('F22FailPageLink', 'F22FailLinkLabel.Output', 'F22FailLink%s.Trigger' % prefix)
        keep(D[prefix + 'UFCBUMenuPage'], {2}, {
            5: menu_el('F22FailUpButton', 'ArrowUpSmall.Output', 'F22FailCursorUp.Trigger'),
            6: menu_el('F22FailDownButton', 'ArrowDownSmall.Output', 'F22FailCursorDown.Trigger'),
            7: menu_el('F22FailSelButton', 'F22FailSelMenuLabel.Output', 'F22FailSel.Trigger'),
            10: menu_el('F22FailRandButton', 'F22FailRandMenuLabel.Output', 'F22RandPress.Trigger', 'F22RandArmed.Output'),
            11: menu_el('F22FailCondButton', 'F22FailCondMenuLabel.Output', 'F22FailCondToggle.Trigger', 'F22FailCond.Output'),
            12: menu_el('F22FailRstButton', 'F22FailRstMenuLabel.Output', 'F22FailReset.Trigger'),
            13: menu_el('F22FailPageButton', 'F22FailPageMenuLabel.Output', 'F22FailPageFlip.Trigger', 'F22FailPage2.Output')})
        keep(D[prefix + 'EngineMenuPage'], {2}, {
            5: menu_el('F22ExtLButton', 'F22ExtLLabel.Output', 'F22FireSwitchPress1.Trigger', 'F22FireHandle1.Output'),
            10: menu_el('F22ExtRButton', 'F22ExtRLabel.Output', 'F22FireSwitchPress2.Trigger', 'F22FireHandle2.Output')})

    # ---- voices and the stall bang (only once converted, see _have_sound)
    voice, published = ns['voice'], ns['published']
    sounds = []
    for k, side in ((1, 'left'), (2, 'right')):
        # ENGINE OUT 1.5 s after the engine stops (the warning confirms first): it no longer talks over the seizure
        o('logic_confirm_delay', 'F22EngOutVoice%d' % k, Input='F22EngOut%d.Output' % k, TimeUp=1.5, TimeDown=0.0001,
          Threshold=0.5)
        for what, src in (('fire', 'F22FireWarn%d' % k), ('engine', 'F22EngOutVoice%d' % k)):
            wav = 'voice_%s_%s' % (what, side)
            if _have_sound(wav):
                o('product', 'F22Voice%s%d' % (what.title(), k), Inputs=' %s.Output F22VoiceOn.Output ' % src)
                voice('F22Voice%s%dIn' % (what.title(), k), published('F22Voice%s%d' % (what.title(), k)), wav + '.wav', 3.0)
                sounds.append(wav)
    snd, cockpit_loop = ns['snd'], ns['cockpit_loop']

    def engine_once(name, src, wav, volume, k, r0=None):
        """A one-shot sound in the engine (as the stock internal engine loops: at the engine, heard in the cockpit),
        not at the pilot's head - there it sounded like the intercom (in-game 2026-11-09)."""
        r0 = r0 or dyn_node('Engine%d' % k).get('R0')
        obj(snd, 'soundinput', name, InputID=('uint32', src))
        obj(snd, 'soundmultiply', name + 'Volume', Input0=name + '.Output', Input1='%g' % volume)
        obj(snd, 'soundsingle', name + 'Sound', PositionID=('uint32', 'Fuselage.R'), OrientationID=('uint32', 'Fuselage.Q'),
            VelocityID=('uint32', 'Fuselage.V'), InputTrigger=name + '.Output', InputVolume=name + 'Volume.Output',
            InputPitch='1.0', SoundFile=wav, Threshold=0.9, Direction=('uint32', '1'), R0=('tmvector3d', r0),
            Radius=2.0, Range=('float64', '500.0'), External=('bool', 'false'))

    if _have_sound('engine_rough'):
        o('sum', 'F22RoughLevel', Inputs=' F22VibExtra1.Output F22VibExtra2.Output ')
        obj(snd, 'soundinput', 'F22RoughIn', InputID=('uint32', published('F22RoughLevel')))
        obj(snd, 'soundmapping', 'F22RoughVolume0', Input='F22RoughIn.Output',
            Map=' (0.0 0.0) (0.004 0.03) (0.02 0.25) (0.05 0.5) ')
        obj(snd, 'soundmultiply', 'F22RoughVolume', Input0='F22RoughVolume0.Output', Input1='1.0')
        cockpit_loop('F22RoughSound', 'F22RoughVolume.Output', '1.0', 'engine_rough.wav')
        sounds.append('engine_rough')
    if _have_sound('seize_grind'):
        for k in (1, 2):
            engine_once('F22SeizeGrind%dIn' % k, published('F22Seized%d' % k), 'seize_grind.wav', 8.0, k)
        sounds.append('seize_grind')
    if _have_sound('stall_bang'):
        for k in (1, 2):
            engine_once('F22StallBang%dIn' % k, published('F22FailFlame%d' % k), 'stall_bang.wav', 14.0, k)
        # the tyre's bang, at the wheel: its own sound from real recordings (make_damage_sounds.py) - the stall bang it
        # shared until 2026-11-21 had nothing above 1 kHz and was lost under the touchdown (user: 'almost not heard')
        tyre = 'tyre_burst.wav' if _have_sound('tyre_burst') else 'stall_bang.wav'
        for side, name in (('L', 'Left'), ('R', 'Right')):
            engine_once('F22TyreBang%sIn' % side, published('F22TyreBurst' + side), tyre, 10.0, None,
                        dyn_node(name + 'WheelHull').get('R0'))
        engine_once('F22TyreBangNIn', published('F22TyreBurstN'), tyre, 10.0, None,
                    dyn_node('LeftFrontWheelHull').get('R0'))
        sounds.append('stall_bang')
    # gear legs breaking (the shear's bang too: gear_crunch) (fold / shear) and the airframe then sliding on the runway (make_damage_sounds.py)
    if _have_sound('gear_crunch'):
        for side, hull in (('L', 'LeftWheelHull'), ('R', 'RightWheelHull'), ('N', 'LeftFrontWheelHull')):
            o('logic_or', 'F22GearBreaks' + side, Inputs=' F22Collapse%s.Output F22Shear%s.Output ' % (side, side))
            engine_once('F22GearCrunch%sIn' % side, published('F22GearBreaks' + side), 'gear_crunch.wav', 14.0, None,
                        dyn_node(hull).get('R0'))
        sounds.append('gear_crunch')
    if _have_sound('belly_scrape'):
        o('logic_or', 'F22GearBroken', Inputs=' F22CollapseL.Output F22CollapseR.Output F22CollapseN.Output '
                                              'F22ShearL.Output F22ShearR.Output F22ShearN.Output ')
        o('product', 'F22ScrapeLevel0', Inputs=' F22GearBroken.Output OnGroundSensor.Output '
                                               'InertialReferenceSystem.OutputGroundSpeed ')
        # the slide swells in over ~1 s: at full level at once it buried the leg breaking (2026-11-21 recording: the
        # crunch's crack lasted 0.1 s above the scrape, its weight none)
        o('first_order_low_pass', 'F22ScrapeLevel', Input='F22ScrapeLevel0.Output', TimeConstant='0.5')
        obj(snd, 'soundinput', 'F22ScrapeIn', InputID=('uint32', published('F22ScrapeLevel')))
        obj(snd, 'soundmapping', 'F22ScrapeVolume', Input='F22ScrapeIn.Output',
            Map=' (0.0 0.0) (1.0 0.05) (5.0 0.35) (20.0 0.7) (60.0 1.0) ')
        obj(snd, 'soundmapping', 'F22ScrapePitch', Input='F22ScrapeIn.Output', Map=' (0.0 0.6) (10.0 0.8) (60.0 1.2) ')
        cockpit_loop('F22ScrapeSound', 'F22ScrapeVolume.Output', 'F22ScrapePitch.Output', 'belly_scrape.wav')
        sounds.append('belly_scrape')
    print('failures: %d items, RAND pool %d, sounds %s' % (n_items, len(pool), ', '.join(sounds) or 'none yet (convert)'))


# ---- landing gear (block 3, 2026-11-11, user: "quality, with models and conversions if needed")
# Where each leg really is: its retraction joint's angle over the angle at which its cylinder holds it up (solved from
# the cylinder geometry, tools in FAILURES.md: main 1.590 rad, nose 1.696 rad; magnitude, the legs only move one way
# from down). The legs' drawing (gear_graphics) and the gear lamps follow it - before, all three followed the handle's
# sequence, so a folded leg was drawn down. Main joint: free, held by its cylinder; nose joint: locked when down.
GEAR_LEGS = {'L': ('JointLeftGear', 1.5903), 'R': ('JointRightGear', 1.5903), 'N': ('JointNoseGearUpper', 1.6961)}
GEAR_STATIC = {'L': 117885.0, 'R': 117885.0, 'N': 37929.0}        # N per leg at 27 900 kg (make_f22 'gear at ...')
GEAR_LOAD = {'L': 'LeftWheelHull.Load', 'R': 'RightWheelHull.Load', 'N': 'NoseWheelLoad.Output'}
NOSE_FOLD_X = 5.0        # nose wheel load (x static) that folds the nose leg (COND; past NOSE_SHEAR_N it breaks): past limit
NWS_CASTER_KP, NWS_CASTER_KD = 300.0, 60.0    # N m / rad, N m s / rad: castoring nose wheel (NWS off); the damper
                                               # on the ~0.7 kg m2 strut body: ~80 /s (400 gave ~550 /s - too close to
                                               # what the game's step holds, 2026-11-15)
NOSE_FOLD_S = 0.1        # held this long (a slam-down's peak; not a frame's spike of the wheel's contact)
# m/s sideways at touchdown (COND, estimates). A tyre scrubbed sideways faster than ~15 kt bursts; the side load a leg
# can get is limited by the tyres' grip, i.e. by the vertical load - a leg folds / breaks sideways only in a hard
# touchdown (over 10 ft/s) as well. (First: 4 / 6 / 8 m/s on drift alone - two ordinary landings with ~8 kt of
# leftover crab burst a tyre, in-game 2026-11-12)
SIDE_BURST, SIDE_FOLD, SIDE_SHEAR = 8.0, 8.0, 11.0



def fold_travel(o, k):
    """The leg's fold travel (cylinder command 0 .. FOLD_STOP[k]): fast while F22Collapse<k> is set, slowly back without.
    A sheared leg does not fold: its stub stays down (both came at a -1700 ft/min nose-first touchdown - the nose and the
    right main, DNLK failed, sheared and folded: the stubs went most of the way into their bays, in-game 2026-11-15)"""
    o('logic_greater', 'F22Unsheared' + k + 'Fold', Input0='0.5', Input1='F22Shear%s.Output' % k)
    o('logic_and', 'F22FoldNow' + k, Inputs=' F22Collapse%s.Output F22Unsheared%sFold.Output ' % (k, k))
    o('mixlinear', 'F22FoldRate' + k, Input0='F22FoldNow%s.Output' % k, Input1='1.0', Weight0=FOLD_RATE + FOLD_BACK,
      Weight1=-FOLD_BACK)
    o('integral_clamped', 'F22FoldFrac' + k, Input='F22FoldRate%s.Output' % k, Range=' 0.0 %.3f ' % FOLD_STOP[k], Value=0.0)

def gear_dynamics(o, not_, add_inputs, dyn_node, setv):
    o('logic_greater', 'F22GearLoadsArmed', Input0='F22SimTime.Output', Input1='5.0')
    add_inputs('F22NoseOverloadCond', 'F22GearLoadsArmed.Output')
    for k, (joint, up) in GEAR_LEGS.items():
        o('absolute', 'F22LegAngle' + k, Input=joint + '.Output')
        o('linear_interpolation', 'F22LegU' + k, Input='F22LegAngle%s.Output' % k, Map=' (0.0 0.0) (%.4f 1.0) ' % up)
        o('logic_greater', 'F22LegNearDown' + k, Input0='0.03', Input1='F22LegU%s.Output' % k)
        # up and locked, as the up-lock hook: caught at 97 % of the travel, let go only once the leg really comes down
        # (under 80 %). On the angle alone the stowed nose leg sagged out of the top 3 % in a pull (its cylinder holds
        # it springily) and NOSE lit amber through the manoeuvre (in-game 2026-11-13)
        o('logic_greater', 'F22LegAtUp' + k, Input0='F22LegU%s.Output' % k, Input1='0.97')
        o('logic_greater', 'F22LegOffUp' + k, Input0='0.80', Input1='F22LegU%s.Output' % k)
        o('mixlinear', 'F22LegUpRate' + k, Input0='F22LegAtUp%s.Output' % k, Input1='F22LegOffUp%s.Output' % k,
          Weight0=20.0, Weight1=-20.0)
        o('integral_clamped', 'F22LegUpHeld' + k, Input='F22LegUpRate%s.Output' % k, Range=' 0.0 1.0 ', Value=0.0)
        o('logic_greater', 'F22LegUp' + k, Input0='F22LegUpHeld%s.Output' % k, Input1='0.5')
    # nose leg fold (the mains have F22CollapseL / R): its cylinder pulls it up, its down-lock lets go
    o('variable', 'F22CollapseN', Value='0.0')
    o('event_value', 'F22CollapseSetN', Input='1.0', Events=' F22CollapseN.Set ')
    not_('F22NoseNotCollapsed', 'F22CollapseN.Output')
    add_inputs('NoseGearLocked', 'F22NoseNotCollapsed.Output')

    # GEAR UP (L / R / N GR UP): the leg's up-lock does not let go - selected down, it stays in its bay (the failure
    # shows at the next extension: it holds a leg that is up). ALT GR (SYS page) - the alternate extension: releases
    # the up-locks, the gear falls and locks down; it stays down (the handle no longer raises it) until RST.
    o('variable', 'F22AltGear', Value='0.0')
    o('event_value', 'F22AltGearPull', Input='1.0', Events=' F22AltGear.Set ')
    add_inputs('F22GearTarget', 'F22AltGear.Output')
    for k in 'LRN':
        o('logic_and', 'F22UpJam' + k, Inputs=' F22FailGearUp%s.Output F22LegUp%s.Output ' % (k, k))
        o('logic_or', 'F22UpFree' + k, Inputs=' F22FailNotGearUp%s.Output F22AltGear.Output ' % k)
        # (the release wins: with jam and release both true the first version summed to 0 and ALT GR did nothing,
        # in-game 2026-11-12)
        not_('F22UpNotFree' + k, 'F22UpFree%s.Output' % k)
        o('logic_and', 'F22UpJamOnly' + k, Inputs=' F22UpJam%s.Output F22UpNotFree%s.Output ' % (k, k))
        o('mixlinear', 'F22UpHoldRate' + k, Input0='F22UpJamOnly%s.Output' % k, Input1='F22UpFree%s.Output' % k,
          Weight0=20.0, Weight1=-20.0)
        o('integral_clamped', 'F22UpHeld' + k, Input='F22UpHoldRate%s.Output' % k, Range=' 0.0 1.0 ', Value=0.0)
        o('logic_greater', 'F22UpHold' + k, Input0='F22UpHeld%s.Output' % k, Input1='0.5')
    add_inputs('F22MainGearL', 'F22UpHoldL.Output')
    add_inputs('F22MainGearR', 'F22UpHoldR.Output')
    cyl = dyn_node('FrontGearCyclinder')
    assert cyl.get('Control').strip() == 'MapNoseGear.Output', cyl.get('Control')
    o('maximum', 'F22NoseGearCtl', Inputs=' MapNoseGear.Output F22UpHoldN.Output ')
    o('servoclassic', 'F22NoseGearSmooth', Input='F22NoseGearCtl.Output', Speed=GEAR_CTL_RATE, P1=1.0)
    fold_travel(o, 'N')
    o('maximum', 'F22NoseGearCyl', Inputs=' F22NoseGearSmooth.Output F22FoldFracN.Output ')
    setv(cyl, 'Control', 'F22NoseGearCyl.Output')

    # DNLK (L / R / N DNLK): the down-lock does not hold (Eglin 2022: a mis-rigged main strut) - the lamp stays amber,
    # and once the leg carries weight (30 % of its static load for 0.3 s) it folds. COND: a nose wheel load past 5 x
    # static for 0.1 s (a hard nose-first touch or slam-down) folds the nose leg; past 6.5 x it breaks off (F22ShearN)
    for k in 'LRN':
        o('logic_greater', 'F22DnlkLoaded' + k, Input0=GEAR_LOAD[k], Input1='%.0f' % (0.3 * GEAR_STATIC[k]))
        o('logic_and', 'F22DnlkGo' + k, Inputs=' F22FailDnlk%s.Output F22DnlkLoaded%s.Output F22GearLoadsArmed.Output '
          % (k, k))
        o('logic_confirm_delay', 'F22DnlkFold' + k, Input='F22DnlkGo%s.Output' % k, TimeUp=0.3, TimeDown=0.0001,
          Threshold=0.5)
        o('event_edge_rising', 'F22DnlkHit' + k, Input='F22DnlkFold%s.Output' % k, Events=' F22CollapseSet%s.Trigger ' % k,
          Value=1.0, Threshold=0.5)
    o('logic_greater', 'F22NoseFoldLoad', Input0='NoseWheelLoad.Output', Input1='%.0f' % (NOSE_FOLD_X * GEAR_STATIC['N']))
    o('logic_and', 'F22NoseFoldNow', Inputs=' F22NoseFoldLoad.Output F22FailCond.Output F22GearLoadsArmed.Output ')
    o('logic_confirm_delay', 'F22NoseFoldHeld', Input='F22NoseFoldNow.Output', TimeUp=NOSE_FOLD_S, TimeDown=0.0001,
      Threshold=0.5)
    o('event_edge_rising', 'F22NoseFoldHit', Input='F22NoseFoldHeld.Output', Events=' F22CollapseSetN.Trigger ',
      Value=1.0, Threshold=0.5)

    # gear lamps from the legs themselves: green down and locked (near down, its lock not failed, not folding), amber
    # moving or unsafe (a failed down-lock reads unsafe), dark up and locked. Locked counts only where the handle wants
    # the leg: a leg left in its bay with the handle down (GR UP), or stuck down with it up, reads amber (in-game
    # 2026-11-11: the jammed leg showed nothing)
    o('logic_greater', 'F22GearHandleDown', Input0='F22GearTarget.Output', Input1='0.5')
    not_('F22GearHandleUp', 'F22GearHandleDown.Output')
    for k, gear in (('L', 'Left'), ('R', 'Right'), ('N', 'Nose')):
        o('logic_and', 'F22Leg%sDownLocked' % k, Inputs=' F22LegNearDown%s.Output F22FailNotDnlk%s.Output ' % (k, k))
        lamp, locked = dyn_node('F22Gear%sLamp' % gear), dyn_node('F22Gear%sLocked' % gear)
        assert lamp.get('Inputs').split()[0] == '%sGearDownAndLocked.Output' % gear, lamp.get('Inputs')
        setv(lamp, 'Inputs', ' F22Leg%sDownLocked.Output DCBusEssentialOn.Output ' % k)
        o('logic_and', 'F22Leg%sUpWanted' % k, Inputs=' F22LegUp%s.Output F22GearHandleUp.Output ' % k)
        o('logic_and', 'F22Leg%sDownWanted' % k, Inputs=' F22Leg%sDownLocked.Output F22GearHandleDown.Output ' % k)
        setv(locked, 'Inputs', ' F22Leg%sDownWanted.Output F22Leg%sUpWanted.Output ' % (k, k))
    add_inputs('F22GearWarn', 'F22UpHoldL.Output', 'F22UpHoldR.Output', 'F22UpHoldN.Output', 'F22CollapseN.Output',
               'F22FailDnlkL.Output', 'F22FailDnlkR.Output', 'F22FailDnlkN.Output')

    # NWS: nose-wheel steering gone (failed, or no utility pressure) - the steering joint lets go and the wheel
    # castors, on a weak centring spring and its shimmy damper: steer with the brakes and, fast enough, the rudder
    # (ICAWS NWS). (First build: the joint stayed locked at 0 - a wheel held straight, user 2026-11-15: 'the strut no
    # longer turns but the jet still turns'.) The donor joint was always locked, its Kp / Kd unused; now they are the
    # castoring wheel's spring and damper (estimates)
    sv = dyn_node('ServoSteering')
    o('product', 'F22NwsCmd', Inputs=' %s F22FailNotNws.Output ' % sv.get('Input').strip())
    setv(sv, 'Input', 'F22NwsCmd.Output')
    o('logic_greater', 'F22NwsPressure', Input0='F22HydSystem2.Output', Input1='0.5')
    o('logic_and', 'F22NwsWorks', Inputs=' F22FailNotNws.Output F22NwsPressure.Output ')
    nj = dyn_node('JointNoseGearMiddle')
    assert nj.get('InputPosition').strip() == 'ServoSteering.Output' and nj.get('InputLock').strip() == '1.0', nj.name
    setv(nj, 'InputLock', 'F22NwsWorks.Output')
    setv(nj, 'Kp', '%g' % NWS_CASTER_KP)
    setv(nj, 'Kd', '%g' % NWS_CASTER_KD)
    # BRAKE (L / R): that wheel's brake gone, the parking brake on that side too (one brake line); WHL SZ: a wheel
    # seized (brake stuck on / bearing) - it drags locked, and skidding on it bursts its tyre (1.5 s over 15 m/s)
    for k, name in (('L', 'Left'), ('R', 'Right')):
        add_inputs('F22%sBrakeTyre' % name, 'F22FailNotBrake%s.Output' % k)
        o('product', 'F22ParkBrake' + k, Inputs=' ParkingBrake.Output F22FailNotBrake%s.Output ' % k)
        mix = dyn_node(name + 'BrakeMix')
        ins = mix.get('Inputs').split()
        assert 'ParkingBrake.Output' in ins, ins
        setv(mix, 'Inputs', ' %s F22FailSeize%s.Output ' % (' '.join('F22ParkBrake%s.Output' % k if x == 'ParkingBrake.Output'
                                                                    else x for x in ins), k))
        o('logic_and', 'F22SeizeSkid' + k, Inputs=' F22FailSeize%s.Output OnGroundSensor.Output F22RollSome.Output ' % k)
        o('logic_confirm_delay', 'F22SeizeSkidLong' + k, Input='F22SeizeSkid%s.Output' % k, TimeUp=1.5,
          TimeDown=0.0001, Threshold=0.5)
        o('event_edge_rising', 'F22SeizeBurst' + k, Input='F22SeizeSkidLong%s.Output' % k,
          Events=' F22TyreBurstSet%s.Trigger ' % k, Value=1.0, Threshold=0.5)
    # TIRE (L / R / N): the tyre goes now (an instructor's burst; the flown ways are COND)
    for k in 'LRN':
        o('event_edge_rising', 'F22FailTyreGo' + k, Input='F22FailTyre%s.Output' % k,
          Events=' F22TyreBurstSet%s.Trigger ' % k, Value=1.0, Threshold=0.5)

    # touching down sideways (COND): the sideways speed over the ground at the touch - ground speed x sin(drift angle),
    # + = moving to the right of the nose. Aerofly's OutputDriftAngle: radians, and + with the track LEFT of the heading
    # (in-game 2026-11-12, two landings: the HUD's flight path marker 2.6 / 3.3 deg left of the waterline at 133 / 134 kt
    # - 6 / 8 kt to the left - read +9 kt here before the sign was turned). The tyres' friction below the centre of
    # gravity rolls the aircraft towards the drift: the leg on that side takes it - over SIDE_BURST its tyre bursts, in a
    # hard touchdown (over 10 ft/s) over SIDE_FOLD the leg folds, over SIDE_SHEAR it breaks off
    sin_map = ' %s ' % ' '.join('(%.4f %.5f)' % (a, math.sin(a)) for a in [i * math.pi / 24 for i in range(-12, 13)])
    o('linear_interpolation', 'F22DriftSin', Input='InertialReferenceSystem.OutputDriftAngle', Map=sin_map)
    o('product', 'F22SideLive', Inputs=' F22DriftSin.Output InertialReferenceSystem.OutputGroundSpeed -1.0 ')
    o('state_frozen', 'F22TdSide', Input='F22SideLive.Output', InputEnable='F22AtAirborne.Output', Value=0.0)
    o('absolute', 'F22TdSideAbs', Input='F22TdSide.Output')
    o('logic_greater', 'F22TdSideRight', Input0='F22TdSide.Output', Input1='0.0')
    for what, limit, target in (('Burst', SIDE_BURST, 'F22TyreBurstSet%s'), ('Fold', SIDE_FOLD, 'F22CollapseSet%s'),
                                ('Shear', SIDE_SHEAR, 'F22ShearSet%s')):
        o('logic_greater', 'F22Side%sOver' % what, Input0='F22TdSideAbs.Output', Input1='%.1f' % limit)
        hard = '' if what == 'Burst' else ' F22TdHard.Output'
        o('logic_and', 'F22Side%sCond' % what, Inputs=' F22Side%sOver.Output F22FailCond.Output%s ' % (what, hard))
        o('event_demultiplexer', 'F22Side%sPick' % what, InputSelect='F22TdSideRight.Output',
          Events=' %s.Trigger %s.Trigger ' % (target % 'L', target % 'R'))
        o('event_demultiplexer', 'F22Side%sHit' % what, InputSelect='F22Side%sCond.Output' % what,
          Events=' DEV0.Trigger F22Side%sPick.Trigger ' % what)
    # the legs' drawing (DCS args, gear_graphics): main legs and their doors share an argument - doors 0.3 - 0.5,
    # leg 0.5 (up) - 0.9 (down), locks to 1.0. From the leg's own travel u (0 down, 1 up): the doors follow the handle's
    # sequence while the leg is stowed, the leg is drawn where it is (0.9 - 0.4 u, plus the last tenth of the sequence
    # as it comes down) - a normal cycle draws as before, a folded or jammed leg where it really is, doors open. The
    # nose leg 1 - u (its own argument also moves the doors: they stay on the sequence, gear_graphics)
    o('minimum', 'F22GearDoorArg', Inputs=' GearSequence.Output 0.5 ')
    o('mixlinear', 'F22GearSeqTail0', Input0='GearSequence.Output', Input1='1.0', Weight0=1.0, Weight1=-0.9)
    o('maximum', 'F22GearSeqTail', Inputs=' F22GearSeqTail0.Output 0.0 ')
    for k in 'LR':
        o('linear', 'F22LegDownFrac' + k, Input='F22LegU%s.Output' % k, Scaling=-1.0, Offset=1.0)
        o('product', 'F22GearTail' + k, Inputs=' F22GearSeqTail.Output F22LegDownFrac%s.Output ' % k)
        o('mixlinear', 'F22GearMoveArg' + k, Input0='F22LegU%s.Output' % k, Input1='F22GearTail%s.Output' % k,
          Weight0=-0.4, Weight1=1.0, Offset=0.9)
        o('logic_greater', 'F22LegStowed' + k, Input0='F22LegU%s.Output' % k, Input1='0.99')
        o('multiplexer', 'F22GearArg' + k, InputSelect='F22LegStowed%s.Output' % k,
          Inputs=' F22GearMoveArg%s.Output F22GearDoorArg.Output ' % k)
    o('linear', 'F22GearArgN', Input='F22LegUN.Output', Scaling=-1.0, Offset=1.0)
    o('variable', 'F22TdSideLast', Value='0.0')
    o('event_value', 'F22TdSideKeep', Input='F22TdSide.Output', Events=' F22TdSideLast.Set ')
    td = dyn_node('F22Touchdown')
    setv(td, 'Events', ' %s F22SideBurstHit.Trigger F22SideFoldHit.Trigger F22SideShearHit.Trigger '
                       'F22TdSideKeep.Trigger ' % td.get('Events').strip())


def after_tvc(ns):
    """NOZZLE: the vector law's command frozen where it was (after tvc_f22 and the nozzle power gate); STAB the same for
    one stabilator."""
    obj, dyn, D = ns['obj'], ns['dyn'], ns['D']
    nz = next(n for n in dyn.children if n.name == 'NozzleAngle')
    D['F22NozzleFrozen'] = obj(dyn, 'state_frozen', 'F22NozzleFrozen', nz, Input=nz.get('Input').strip(),
                               InputEnable='F22FailNotNozzle.Output', Value=0.0)
    nz.set('Input', 'F22NozzleFrozen.Output', 'string8')
    # STAB: the stabilator's servo command frozen last, after the hydraulic gate and the BIT program (make_f22.py), so
    # a jammed actuator stays put whatever the pressure does. Not a joint change: the joint stays the actuator
    for k, side in ((1, 'Left'), (2, 'Right')):
        sv = next(n for n in dyn.children if n.name == 'Servo%sStabilator' % side)
        src = sv.get('Input').strip()
        assert src == 'F22HydServo%sStabilator.Output' % side, src
        D['F22StabFrozen%d' % k] = obj(dyn, 'state_frozen', 'F22StabFrozen%d' % k, sv, Input=src,
                                       InputEnable='F22FailNotStab%d.Output' % k, Value=0.0)
        sv.set('Input', 'F22StabFrozen%d.Output' % k, 'string8')


def graphics(ns):
    obj, dyn, D, g, G = ns['obj'], ns['dyn'], ns['D'], ns['g'], ns['G']
    # the nose strut drawn at the steering joint's angle, not the steering servo's: castoring (NWS off) it turns by itself
    so = next(o for o in dyn.children if o.name == 'GfxOutServoSteering')
    assert so.get('Input').strip() == 'ServoSteering.Output', so.get('Input')
    so.set('Input', 'JointNoseGearMiddle.Output', 'string8')
    label, place_copy, text_out = ns['label'], ns['place_copy'], ns['text_out']
    UFD_FONT, AMBER = ns['UFD_FONT'], ns['AMBER']
    # engine state text (UFD, ENG page): a seized engine read WMIL while it ran down (in-game 2026-11-09) - SEIZ
    ufc_label = ns['ufc_label']
    for k, side in ((1, 'L'), (2, 'R')):
        obj(dyn, 'multiplexer', 'F22Eng%dStageS' % k, InputSelect='F22Seized%d.Output' % k,
            Inputs=' F22Eng%dStageW.Output 6.0 ' % k)
        for name, text in (('F22Eng%dShortText' % k, '%s SEIZ' % side), ('F22Eng%dStageText' % k, '%s SEIZED' % side)):
            n = next(o for o in dyn.children if o.name == name)
            assert n.get('InputSelect').strip() == 'F22Eng%dStageW.Output' % k, name
            n.set('InputSelect', 'F22Eng%dStageS.Output' % k, 'string8')
            n.set('Inputs', ' %s %s ' % (n.get('Inputs').strip(), ufc_label(text)), 'string8')
    size = 30.0
    font = dict(UFD_FONT, FontSize=size, Stride=size * 0.9)
    green = (0.3, 1.0, 0.3, 1.0)
    # two pages of slots: each slot shows the item of the page the cursor is on (its text, cursor mark, OK / FAIL),
    # one set of graphics for both pages (texts switched in the dynamics)
    ufc_text = ns['ufc_label']
    o_ = lambda type_, name, **f: obj(dyn, type_, name, **f) and name + '.Output'
    items = [label('FAILURES', (378, 905), 34.0)]       # (centred, as the other pages' titles: mfd_f22)
    blank = {n: o_('constant_text', 'F22FailBlank%d' % n, Input=' ' * n) for n in (1, 2, 4, 8)}
    n_pages = (len(ITEMS) + PAGE_SIZE - 1) // PAGE_SIZE
    assert n_pages == 2, n_pages
    for i, (key, text, _) in enumerate(ITEMS):
        src = 'F22FailDual.Output' if key == 'Dual' else 'F22Fail%s.Output' % key
        obj(dyn, 'logic_equal', 'F22FailAt%d' % i, Input0='F22FailCursor.Output', Input1='%d.0' % i)
        obj(dyn, 'binary_to_text', 'F22FailCurText%d' % i, Input='F22FailAt%d.Output' % i, Text0=' ', Text1='>')
        obj(dyn, 'binary_to_text', 'F22FailOkText%d' % i, Input=src, Text0='OK', Text1='  ')
        obj(dyn, 'binary_to_text', 'F22FailBadText%d' % i, Input=src, Text0='    ', Text1='FAIL')
    for slot in range(PAGE_SIZE):
        col, row = divmod(slot, ROWS)
        x, y = (110, 500)[col], 840 - ROW_DY * row
        per = {'Cur': [], 'Name': [], 'Ok': [], 'Bad': []}
        for pg in range(n_pages):
            i = slot + PAGE_SIZE * pg
            if i < len(ITEMS):
                per['Cur'].append('F22FailCurText%d.Output' % i)
                per['Name'].append(ufc_text(ITEMS[i][1]))
                per['Ok'].append('F22FailOkText%d.Output' % i)
                per['Bad'].append('F22FailBadText%d.Output' % i)
            else:
                per['Cur'].append(blank[1]); per['Name'].append(blank[8]); per['Ok'].append(blank[2]); per['Bad'].append(blank[4])
        for what, lst in per.items():
            o_('multiplexer_text', 'F22FailSlot%s%d' % (what, slot), InputSelect='F22FailPage2.Output',
               Inputs=' %s ' % ' '.join(lst))
        items += [place_copy('UpFrontControllerLine0', 'F22FailCur%d' % slot, Input=text_out('FailSlotCur%d' % slot, 'F22FailSlotCur%d.Output' % slot),
                             Position=' %d %d ' % (x - 26, y), Length='1', **font),
                  place_copy('UpFrontControllerLine0', 'F22FailName%d' % slot, Input=text_out('FailSlotName%d' % slot, 'F22FailSlotName%d.Output' % slot),
                             Position=' %d %d ' % (x, y), Length='8', **font),
                  place_copy('UpFrontControllerLine0', 'F22FailOk%d' % slot, Input=text_out('FailSlotOk%d' % slot, 'F22FailSlotOk%d.Output' % slot),
                             Position=' %d %d ' % (x + 243, y), Length='2', Color=' %g %g %g %g ' % green, **font),
                  place_copy('UpFrontControllerLine0', 'F22FailBad%d' % slot, Input=text_out('FailSlotBad%d' % slot, 'F22FailSlotBad%d.Output' % slot),
                             Position=' %d %d ' % (x + 243, y), Length='4', Color=' %g %g %g %g ' % AMBER, **font)]
    obj(dyn, 'binary_to_text', 'F22FailRandText', Input='F22RandArmed.Output', Text0='OFF', Text1='ARMED')
    obj(dyn, 'binary_to_text', 'F22FailCondText', Input='F22FailCond.Output', Text0='OFF', Text1='ON')
    obj(dyn, 'product', 'F22FailPeakG', Inputs=' Accelerometer.MaximumPositiveAcceleration %.6f ' % (1 / 9.81))
    obj(dyn, 'float_to_text', 'F22FailPeakGText', Input='F22FailPeakG.Output', Decimals=('uint32', '1'))
    obj(dyn, 'binary_to_text', 'F22FailExtText', Input='F22ExtBottle.Output', Text0='USED', Text1='RDY')
    # the last touchdown's sink rate, ft/min as the HUD (2026-11-10: a landing seen at -680 at 170 ft gave no HARD LDG -
    # the flare had taken it off; the pilot needs the number at the touch), in the right column's free last row
    obj(dyn, 'product', 'F22FailTdFpm', Inputs=' F22TdSinkLast.Output 196.85 ')
    obj(dyn, 'float_to_text', 'F22FailTdFpmText', Input='F22FailTdFpm.Output', Decimals=('uint32', '0'))
    # page 2: the last touchdown's sideways speed (kt, + to the right) - what the side-load failures read
    obj(dyn, 'product', 'F22FailTdSideKt', Inputs=' F22TdSideLast.Output 1.94384 ')
    obj(dyn, 'float_to_text', 'F22FailTdSideText', Input='F22FailTdSideKt.Output', Decimals=('uint32', '0'))
    obj(dyn, 'multiplexer_text', 'F22FailTdText', InputSelect='F22FailPage2.Output',
        Inputs=' F22FailTdFpmText.Output F22FailTdSideText.Output ')
    obj(dyn, 'multiplexer_text', 'F22FailTdName', InputSelect='F22FailPage2.Output',
        Inputs=' %s %s ' % (ufc_text('TD FPM'), ufc_text('TD SIDE')))
    ty = 840 - ROW_DY * (ROWS - 1)
    items.append(place_copy('UpFrontControllerLine0', 'F22FailTdNameItem', Input=text_out('FailTdName', 'F22FailTdName.Output'),
                            Position=' %d %d ' % (500, ty), Length='7', **font))
    for text, src, pos, n in (('RAND', 'F22FailRandText', (110, 160), 5), ('COND', 'F22FailCondText', (500, 160), 3),
                              ('PEAK G', 'F22FailPeakGText', (110, 104), 5), ('EXT', 'F22FailExtText', (500, 104), 4),
                              ('', 'F22FailTdText', (500 + int(size * 0.9 * 8), ty), 5)):
        items += ([label(text, pos, size)] if text else []) + [
                  place_copy('UpFrontControllerLine0', src + 'Item', Input=text_out(src[3:], src + '.Output'),
                             Position=' %d %d ' % (pos[0] + int(size * 0.9 * (len(text) + 1)), pos[1]), Length=str(n), **font)]
    g('graphics_animation_render_list', 'F22FailPage', RenderList=' %s ' % ' '.join(items))
    n = 0
    for o in G:
        if o.type == 'graphics_animation_render_switch' and o.find('RenderList') is not None and \
                'UFCBUPage' in o.get('RenderList').split():
            o.set('RenderList', ' ' + ' '.join('F22FailPage' if t == 'UFCBUPage' else t for t in o.get('RenderList').split()) + ' ')
            n += 1
    print('FAIL page in %d MFD page switches' % n)


def gear_graphics(ns):
    """The gear legs drawn from their own joints (gear_dynamics F22GearArg*): every chain table of DCS arg 5 (left main
    leg and doors), 3 (right) and of arg 0 on the nose leg's parts (DCS nodes ending in 6: strut, piston, fork, links,
    wheel, its lamps; the nose doors keep the handle's sequence) reads the leg's argument instead of the sequence."""
    g, G, anim, published = ns['g'], ns['G'], ns['anim'], ns['published']
    src = {}
    for k in 'LRN':
        g('graphics_input', 'GfxF22GearArg' + k, InputID=('uint32', published('F22GearArg' + k)))
        src[k] = 'GfxF22GearArg%s.Output' % k
    by_name = {n.name: n for n in G}
    count = {'L': 0, 'R': 0, 'N': 0}
    for pname, p in anim.items():
        nodes = pname[2:].split('__')[0].split('_')
        for l in p['links']:
            arg = l.get('arg')
            k = {5: 'L', 3: 'R'}.get(arg) or ('N' if arg == 0 and nodes[-1] == '6' else None)
            if not k:
                continue
            maps = [n for name, n in by_name.items() if name.startswith('%s_A%d_' % (pname, arg)) and name.endswith('Map')]
            assert maps, (pname, arg)
            for n in maps:
                n.set('Input', src[k], 'string8')
            count[k] += 1
    assert all(count.values()), count
    print('gear legs drawn from their joints: left %(L)d, right %(R)d, nose %(N)d part chains' % count)
    gear_broken_graphics(ns, by_name)


# A folded leg drawn broken (user 2026-11-13): the lower strut and the wheel kinked out where the piston leaves the
# leg (the wheel splayed out / back), the leg's own door hanging off its hinge, the bay's outer door torn away. Each
# grows with the fold (F22FoldFrac). The kink is a turn in the leg's own frame, inserted in each part's transform chain
# inside the gear tables (after the wheel's spin): it folds with the leg. Pivots and parts from the DCS model (export
# pose: A_51 leg, A_53_51 piston + axle + torque links, A_47 leg door, A_49 outer bay door; right mirrored; nose A_6
# leg, A_14_13_6 fork, A_4 / A_5 side doors)
GEAR_BROKEN = {
    'L': dict(kink=('A_53_51', 'A_54_53_51', 'A_54_53_51__FLAT'), pivot=(-0.35, 1.385, -1.02), axis=(1.0, 0.0, 0.0),
              angle=0.35, bent=(('A_47', -0.5), ('A_49', 0.6))),
    'R': dict(kink=('A_58_56', 'A_59_58_56', 'A_59_58_56__FLAT'), pivot=(-0.35, -1.385, -1.02), axis=(1.0, 0.0, 0.0),
              angle=-0.35, bent=(('A_48', 0.5), ('A_50', -0.6))),
    'N': dict(kink=('A_14_13_6', 'A_15_14_13_6', 'A_15_14_13_6__FLAT'), pivot=(5.93, 0.0, -1.22), axis=(0.0, 1.0, 0.0),
              angle=0.40, bent=(('A_4', 0.6), ('A_5', -0.6))),
}
# doors (bent): turned past open about their own hinge (the DCS open pose is the export pose; closing turns them about x
# by +-1.3 / 0.96 / 1.9 rad - 'bent' goes the other way) with a little twist - hanging bent, not gone (they vanished
# first, in-game 2026-11-13)
DOOR_TWIST = 0.25


def gear_broken_graphics(ns, by_name):
    import failures_f22 as F
    g, G, published = ns['g'], ns['G'], ns['published']
    vec = lambda v: ('tmvector3d', ' %.4f %.4f %.4f ' % tuple(v))

    def innermost_hook(part, rot):
        """Insert graphics transform `rot` innermost in `part`'s chain (after a wheel's spin, which stays innermost)."""
        node = by_name[part]
        prev, cur = node, node.get('InputTransform').split('.')[0]
        while True:
            n = by_name[cur]
            nxt = n.find('InputTransform')
            if nxt is None:
                break
            prev, cur = n, nxt.value.split('.')[0]
        if cur.endswith('_Spin'):          # wheel: the spin innermost, the kink right outside it
            prev.set('InputTransform', rot + '.Output', 'string8')
            by_name[rot].set('InputTransform', cur + '.Output', 'string8')
        else:
            by_name[cur].set('InputTransform', rot + '.Output', 'string8')

    for k, b in GEAR_BROKEN.items():
        stop = F.FOLD_STOP[k]
        g('graphics_input', 'GfxF22FoldFrac' + k, InputID=('uint32', published('F22FoldFrac' + k)))
        g('graphics_input', 'GfxF22Collapse' + k, InputID=('uint32', published('F22Collapse' + k)))
        for part in b['kink']:
            rot = 'F22Kink%s_%s' % (k, part)
            mp = g('graphics_linear_interpolation', rot + 'Map', Input='GfxF22FoldFrac%s.Output' % k,
                   Map=' (0.0 0.0) (%.3f %.4f) ' % (stop, b['angle']))
            by_name[rot + 'Map'] = mp
            by_name[rot] = g('graphics_rotation', rot, Input=rot + 'Map.Output', Axis=vec(b['axis']), Pivot=vec(b['pivot']))
            innermost_hook(part, rot)
        for part, angle in b['bent']:
            link = next(l for l in ns['anim'][part]['links'] if l['kind'] == 'table')
            closing = link['euler'][0][0]
            assert abs(closing) > 0.5 and closing * angle < 0, (part, closing, angle)   # past open: against closing
            pivot = ns['anim'][part]['pivot']
            n_ = (1.0 + DOOR_TWIST ** 2) ** 0.5
            rot = 'F22DoorBent%s_%s' % (k, part)
            by_name[rot + 'Map'] = g('graphics_linear_interpolation', rot + 'Map', Input='GfxF22FoldFrac%s.Output' % k,
                                     Map=' (0.0 0.0) (%.3f %.4f) ' % (stop, angle))
            by_name[rot] = g('graphics_rotation', rot, Input=rot + 'Map.Output', Axis=vec((1.0 / n_, 0.0, DOOR_TWIST / n_)),
                             Pivot=vec(pivot))
            innermost_hook(part, rot)
    print('gear broken drawing: kinked lower strut and wheel, bent doors (L, R, N)')
