"""Loads chosen in the cockpit (0.9.2; 2026-11-26: one livery entry per paint, the load picked on the ground, the
aircraft spawning clean). Built on three things tested in game the same day:

1. the add-on folder `stores` is of Type default: the game loads it with every livery;
2. mass in flight: a fuel_tank at each station holds the store's mass. A fuel_engine with a negative fuel flow is a
   source (ApfelFlieger, forum #76): source -> fuel_rail -> fuel_valve -> tank fills it; a fuel_engine straight on the
   tank empties it. Both flows are set by the tank's own mass (OutputFuelMass): a fast fixed flow overran the tank's
   capacity (6968 kg), and the first step after loading is a long one (4832 kg) - so GAIN x the difference to the
   wanted mass, either way, up to FLOW, the fill only after START_S. The engines do not draw on these tanks;
3. light bodies: each missile and each ferry tank shell is a body of PUPPET kg with every force on it (thrust, the
   hold, aerodynamics) and its mount's stiffness and strength scaled by the same ratio - the same accelerations, so the
   same flight (two missiles side by side, light and full, flew alike). The rest of the store's mass is the station
   tank's: emptied at once at the release.

The bodies always hang (hidden while not loaded); a released one does not come back - rearming after a launch or a
jettison is choosing the livery again (the game reloads the aircraft where it is), as before.
"""

PUPPET = {'120': 5.0, '9x': 5.0, 'shell': 10.0}     # kg
DENSITY = 812.0          # kg/m3 of the game's fuel (0.25 m3 took 203 kg)
FLOW = 10000.0           # kg/s at most: a 2 t ferry tank goes in ~0.2 s
GAIN = 20.0              # 1/s: the flow per kg still to go (x dt = 0.33 a frame at 60 frames/s - no overshoot)
START_S = 0.5            # s after the load before a tank fills
# loads on SMS key 12 (LOAD), round: CLEAN, COMBAT (6 AIM-120C + 2 AIM-9X), FERRY (two 600 gal tanks), FULL
PRESETS = (('CLEAN', 0, 0), ('COMBAT', 1, 0), ('FERRY', 0, 1), ('FULL', 1, 1))


def light_total():
    """kg of the bodies that always hang now (light missiles and shells, their racks, the tanks' hull bodies): taken off
    the fuselage, so the clean aircraft weighs what it did before 0.9.2."""
    import weapons_f22 as W, breakage_f22 as B
    missiles = sum(PUPPET[m['kind']] + W.RACK_MASS for m in W.missiles())
    return missiles + 2 * (PUPPET['shell'] + B.RACK_MASS + B.TANK_HULL_MASS)


def ratio(kind, mass):
    """A light body's share of its store's mass."""
    return PUPPET[kind] / mass


def base(obj, dyn, anchor, label):
    """f22.tmd: the load as two switches (F22CombatLoad, F22FerryTanks - the names of the stage 6 add-ons, now set
    here), from F22LoadPreset that SMS LOAD cycles - only as the ground crew would load: on the ground, the parking
    brake set; the engines may run (2026-11-26: the first rule, APU on and engines stopped, left no quick start
    with a load; hot loading with the engines running is done in the real Air Force too). Otherwise the key gives the
    same preset back. The ICP LOAD page (OTHR -> LOAD, make_f22.py) sets a preset anywhere, in the air too
    (2026-11-26/27: a quick start on the runway or in the air needs its load; it replaced the codes 9901-9904)."""
    o = lambda type_, name, **f: obj(dyn, type_, name, anchor, **f)
    n = len(PRESETS)
    o('variable', 'F22LoadPreset', Value='0.0')
    o('linear_interpolation', 'F22LoadNextRaw', Input='F22LoadPreset.Output',
      Map=' %s ' % ' '.join('(%.1f %.1f)' % (k, (k + 1) % n) for k in range(n)))
    o('logic_and', 'F22LoadAllowed', Inputs=' OnGroundSensor.Output ParkingBrakeSet.Output ')
    o('multiplexer', 'F22LoadNext', InputSelect='F22LoadAllowed.Output',
      Inputs=' F22LoadPreset.Output F22LoadNextRaw.Output ')
    # tanks hung where none hung come full (2026-11-27 video: taken off by a code and hung again, they came back with
    # what they held - the burn count F22TanksBurntRaw kept running); tanks that stay keep what they hold
    o('logic_greater', 'F22LoadTanksOff', Input0='0.5', Input1='F22FerryTanks.Output')
    o('linear_interpolation', 'F22LoadNextTanks', Input='F22LoadNextRaw.Output',
      Map=' %s ' % ' '.join('(%.1f %.1f)' % (k, p[2]) for k, p in enumerate(PRESETS)))
    o('product', 'F22LoadCycleHangs', Inputs=' F22LoadAllowed.Output F22LoadNextTanks.Output F22LoadTanksOff.Output ')
    o('event_value', 'F22LoadCycle', Input='F22LoadNext.Output', Events=' F22LoadPreset.Set ')
    o('event_value', 'F22LoadCycleFill', Input='F22LoadNext.Output', Events=' F22LoadPreset.Set F22TanksBurntRaw.Reset ')
    o('event_demultiplexer', 'F22LoadKey', InputSelect='F22LoadCycleHangs.Output',
      Events=' F22LoadCycle.Trigger F22LoadCycleFill.Trigger ')
    for name, col in (('F22CombatLoad', 1), ('F22FerryTanks', 2)):
        o('linear_interpolation', name, Input='F22LoadPreset.Output',
          Map=' %s ' % ' '.join('(%.1f %.1f)' % (k, p[col]) for k, p in enumerate(PRESETS)))
    for k in range(n):
        if not PRESETS[k][2]:
            o('event_value', 'F22LoadSet%d' % k, Input='%.1f' % k, Events=' F22LoadPreset.Set ScratchPad.Clear ')
            continue
        o('event_value', 'F22LoadSet%dKeep' % k, Input='%.1f' % k, Events=' F22LoadPreset.Set ScratchPad.Clear ')
        o('event_value', 'F22LoadSet%dFill' % k, Input='%.1f' % k,
          Events=' F22LoadPreset.Set ScratchPad.Clear F22TanksBurntRaw.Reset ')
        o('event_demultiplexer', 'F22LoadSet%d' % k, InputSelect='F22LoadTanksOff.Output',
          Events=' F22LoadSet%dKeep.Trigger F22LoadSet%dFill.Trigger ' % (k, k))
    o('multiplexer_text', 'F22LoadText', InputSelect='F22LoadPreset.Output',
      Inputs=' %s ' % ' '.join(label(p[0]) for p in PRESETS))


def station_tank(obj, holder, key, body, at, target):
    """One station's mass: a flat tank on `body` at `at` (as the test's: one horizontal section - the stock-like upright
    sections with the outlet at the bottom took 3 kg and stopped) kept at `target` (kg, a dynamics value)."""
    import tmd
    o = lambda type_, name, **f: obj(holder, type_, name, **f)
    v3 = lambda v: ('tmvector3d', ' %.3f %.3f %.3f ' % tuple(v))
    p = 'F22Mass' + key
    tank = o('fuel_tank', p + 'Tank', Body=body, Mass=0.0, Capacity=3.0, Outlet0=v3(at),
             MassMap=('tmvector2d', ' ( 0.0 0.0 ) ( 100000.0 0.0 ) '))
    stations = tmd.Node('fuel_tank_stations', 'Stations', leaf=False)
    st = tmd.Node('fuel_tank_station', '', leaf=False)
    for k, v in (('R0', v3(at)), ('X0', v3((1.0, 0.0, 0.0))), ('Y0', v3((0.0, 1.0, 0.0))),
                 ('Dimensions', ('tmvector2d', ' 3.0 0.18 '))):
        st.children.append(tmd.Node(v[0], k, v[1]))
    stations.children.append(st)
    tank.children.append(stations)
    fm = p + 'Tank.OutputFuelMass'
    rate = lambda name, src: o('linear_interpolation', name, Input=src, Map=' (0.0 0.0) (%.1f %.1f) ' % (FLOW / GAIN, FLOW))
    return [tank,
            o('mixlinear', p + 'Short', Input0=target, Input1=fm, Weight0=1.0, Weight1=-1.0),
            rate(p + 'FillRate', p + 'Short.Output'),
            o('product', p + 'FillFlow', Inputs=' %s.Output F22MassStarted.Output -1.0 ' % (p + 'FillRate')),
            o('fuel_engine', p + 'Source', InputPressure=p + 'Rail.OutputPressure', AddFlow=p + 'Rail.AddFlow',
              InputFuelFlow=p + 'FillFlow.Output'),
            o('fuel_rail', p + 'Rail', DesignFlow=FLOW, Pressure=344738.0),
            o('fuel_valve', p + 'Fill', InputPressure0=p + 'Rail.OutputPressure', InputPressure1=p + 'Tank.OutputPressure0',
              AddFlow0=p + 'Rail.AddFlow', AddFlow1=p + 'Tank.AddFlow', MaximumFlow=FLOW, Input='1.0'),
            o('mixlinear', p + 'Over', Input0=fm, Input1=target, Weight0=1.0, Weight1=-1.0),
            rate(p + 'DrainRate', p + 'Over.Output'),
            o('fuel_engine', p + 'Drain', InputPressure=p + 'Tank.OutputPressure0', AddFlow=p + 'Tank.AddFlow',
              InputFuelFlow=p + 'DrainRate.Output')]


def clock(obj, holder):
    """The add-on's start delay (START_S): F22MassStarted."""
    o = lambda type_, name, **f: obj(holder, type_, name, **f)
    return [o('integral_clamped', 'F22MassClock', Input='1.0', Range=' 0.0 10.0 ', Value=0.0),
            o('logic_greater', 'F22MassStarted', Input0='F22MassClock.Output', Input1='%.2f' % START_S)]


def icp_labels(obj, dyn, anchor):
    """The ICP LOAD page's lines: each preset's name, the colon on the one set (F22LoadPreset)."""
    out = []
    for k, p in enumerate(PRESETS):
        obj(dyn, 'logic_equal', 'F22LoadIsPreset%d' % k, anchor, Input0='F22LoadPreset.Output', Input1='%.1f' % k)
        obj(dyn, 'binary_to_text', 'F22LoadLine%d' % k, anchor, Input='F22LoadIsPreset%d.Output' % k,
            Text0=' ' + p[0], Text1=':' + p[0])
        out.append('F22LoadLine%d.Output' % k)
    return out
