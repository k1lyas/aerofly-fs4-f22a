"""The cockpit controls that have no function yet, prepared for later logic (2026-11-16, user: every switch, knob,
button and wheel of the cockpit ready before publication, so that helpers can give it a function with the scripts
alone - no model work, no converter).

Each control here has four things:
  1. a part of its own in the model (cut out of the static DCS objects: tools/export_parts.py extract_knobs),
  2. a click zone (controls.tmd) that sends the control's message,
  3. a dynamics object that holds its state (input_discrete / input_default / input_button: `F22<Name>.Output`) and a
     default movement of the part with that state,
  4. a row in release/COCKPIT_CONTROLS.md, a file of the release package (written by this file: python3
     cockpit_controls.py).
Nothing in the aircraft listens to these states yet: to give a control a function, read `F22<Name>.Output` in
make_f22.py (or one of its system modules) - see release/COCKPIT_CONTROLS.md.

Directions and end positions follow the lettering around each control (user: check on the labels which way it
moves and where it starts and ends). Geometry numbers: cockpit_fit.py (measured, work/controls/fit.py); the look-alikes
of controls that already work (K_VoxVolume, K_CNI, K_FlcsBit + K_FlcsGuard) take over their accepted pivots and cuts
by the rigid transform between the two meshes.

Angles: degrees about the part's axis. Console rotaries turn about the panel normal (+ = anticlockwise seen from
above); pointer directions below are 0 = to starboard, 90 = forward. Toggles turn about the panel's lateral axis
(+ = top forward) unless noted."""
import math
from cockpit_fit import FIT

NL, NR = (-0.0752, -0.1742, 0.9818), (-0.0760, 0.1855, 0.9797)          # left / right console normals (ac_f22)
LAT_L, LAT_R = (0.0, 0.98460, 0.17480), (0.0, 0.98254, -0.18606)        # their lateral axes
SW, ACC2, MFD = r'^F22_SWITCH$', r'^F22_ACC2$', r'^F22_MFD$'
FWD = (1.0, 0.0, 0.0)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _add(a, b, k=1.0):
    return tuple(round(x + y * k, 5) for x, y in zip(a, b))


def _neg(a):
    return tuple(-x for x in a)


def _mul(R, v):
    return tuple(_dot(row, v) for row in R)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a))
    return tuple(x / n for x in a)


def _side(i):
    return (NL, LAT_L, 'Left') if FIT[i]['box'][0][1] > 0 else (NR, LAT_R, 'Right')


# ------------------------------------------------------------------------------------------------ the table
# (inventory number, name, panel, lettering, kind, message, positions [(value, label)], default)
#   kind: toggle / guarded (a toggle under a red guard that lifts by itself) / selector (rotary with detents) /
#         knob (rotary 0 .. 1) / button / wheel / rocker
CONTROLS = [
    # left console
    (8, 'AuxGen', 'ELECTRIC', 'AUX GEN', 'guarded', 'Electrical.F22AuxGen', [(0, 'ON'), (1, 'OFF/RESET')], 0),
    (9, 'FuelTanks', 'FUEL', 'TANKS', 'toggle', 'Fuel.F22Tanks', [(0, 'ALL'), (1, 'EXT')], 0),
    (16, 'FlcsSwitch2', 'FLCS', '(no lettering, forward of BIT)', 'guarded', 'FCS.F22Switch2',
     [(0, 'guarded'), (1, 'actuated')], 0),
    # (19: lettered AAR beside it, AUTO outboard and OFF inboard of it past the rail - read on the exported model, a
    # plate of the DCS scene hides it in the plain renders)
    (19, 'FlcsAar', 'FLCS', 'AAR', 'toggle', 'FCS.F22Aar', [(0, 'AUTO'), (1, 'OFF')], 0),
    # right console
    (23, 'CabinTemp', 'ECS CABIN', 'TEMP', 'knob', 'ECS.F22CabinTemp', [(0, 'COLD'), (1, 'HOT')], 0.5),
    (24, 'AntiFog', 'ECS CABIN', 'ANTIFOG', 'knob', 'ECS.F22AntiFog', [(0, 'COLD'), (1, 'HOT')], 0.5),
    (25, 'AirSource', 'ECS CABIN', 'AIR SOURCE', 'selector', 'ECS.F22AirSource',
     [(0, 'OFF'), (1, 'R'), (2, 'BOTH'), (3, 'L'), (4, 'DUMP')], 2),
    (26, 'EcsMode', 'ECS CABIN', 'MODE', 'toggle', 'ECS.F22Mode', [(0, 'AUTO'), (1, 'MAN')], 0),
    (28, 'VolumeICS', 'RADIO VOL', 'ICS', 'knob', 'Communication.F22VolumeICS', [(0, 'OFF'), (1, 'INC')], 0.5),
    (29, 'VolumeRWR', 'RADIO VOL', 'RWR', 'knob', 'Communication.F22VolumeRWR', [(0, 'OFF'), (1, 'INC')], 0.5),
    (30, 'VolumeMDS', 'RADIO VOL', 'MDS', 'knob', 'Communication.F22VolumeMDS', [(0, 'OFF'), (1, 'INC')], 0.5),
    (31, 'VolumeRCN', 'RADIO VOL', 'RCN', 'knob', 'Communication.F22VolumeRCN', [(0, 'OFF'), (1, 'INC')], 0.5),
    (32, 'VolumeAUX', 'RADIO VOL', 'AUX', 'knob', 'Communication.F22VolumeAUX', [(0, 'OFF'), (1, 'INC')], 0.5),
    (33, 'AuxCommBrightness', 'AUX COMM', 'BRT', 'knob', 'Communication.F22AuxBrightness', [(0, 'OFF'), (1, 'bright')], 0.5),
    (35, 'AuxCommFreqLeft', 'AUX COMM', 'FREQ (left knob)', 'knob', 'Communication.F22AuxFreqLeft', [(0, ''), (1, '')], 0.0),
    (34, 'AuxCommFreqRight', 'AUX COMM', 'FREQ (right knob)', 'knob', 'Communication.F22AuxFreqRight', [(0, ''), (1, '')], 0.0),
    (36, 'Zeroize', 'AUX COMM', 'ZEROIZE', 'guarded', 'Communication.F22Zeroize', [(0, 'guarded'), (1, 'ZEROIZE')], 0),
    (37, 'AuxCommMode', 'AUX COMM', 'MODE', 'selector', 'Communication.F22AuxMode',
     [(0, 'KP'), (1, 'MAN'), (2, 'PRESET'), (3, 'GUARD')], 1),
    (38, 'OxygenTest', 'OXYGEN', 'TEST', 'button', 'Oxygen.F22Test', [(1, 'pressed')], 0),
    (41, 'OxygenMixture', 'OXYGEN', 'MIXTURE', 'toggle', 'Oxygen.F22Mixture', [(0, 'AUTO'), (1, 'FULL')], 0),
    (42, 'OxygenFlow', 'OXYGEN', 'FLOW', 'toggle', 'Oxygen.F22Flow', [(0, 'BYPASS'), (1, 'NORMAL')], 1),
    (43, 'Obogs', 'OXYGEN', 'OBOGS', 'toggle', 'Oxygen.F22Obogs', [(0, 'OFF'), (1, 'ON')], 1),
    (45, 'AftRightGuarded', 'right console, far aft', '(no lettering)', 'guarded', 'Controls.F22AftRightGuarded',
     [(0, 'guarded'), (1, 'actuated')], 0),
    # the two knobs of each screen (no lettering; value rises clockwise)
    (113, 'LeftUfdKnobLeft', 'left UFD', 'lower left knob', 'knob', 'UFD.F22LeftKnobLeft', [(0, ''), (1, '')], 0.5),
    (114, 'LeftUfdKnobRight', 'left UFD', 'lower right knob', 'knob', 'UFD.F22LeftKnobRight', [(0, ''), (1, '')], 0.5),
    (115, 'RightUfdKnobLeft', 'right UFD', 'lower left knob', 'knob', 'UFD.F22RightKnobLeft', [(0, ''), (1, '')], 0.5),
    (116, 'RightUfdKnobRight', 'right UFD', 'lower right knob', 'knob', 'UFD.F22RightKnobRight', [(0, ''), (1, '')], 0.5),
    (121, 'LeftMfdKnobLeft', 'left MFD', 'upper left knob', 'knob', 'LeftMFD.F22KnobLeft', [(0, ''), (1, '')], 0.5),
    (122, 'LeftMfdKnobRight', 'left MFD', 'upper right knob', 'knob', 'LeftMFD.F22KnobRight', [(0, ''), (1, '')], 0.5),
    (117, 'PmfdKnobLeft', 'PMFD (centre)', 'upper left knob', 'knob', 'MPCD.F22KnobLeft', [(0, ''), (1, '')], 0.5),
    (118, 'PmfdKnobRight', 'PMFD (centre)', 'upper right knob', 'knob', 'MPCD.F22KnobRight', [(0, ''), (1, '')], 0.5),
    (123, 'RightMfdKnobLeft', 'right MFD', 'upper left knob', 'knob', 'RightMFD.F22KnobLeft', [(0, ''), (1, '')], 0.5),
    (124, 'RightMfdKnobRight', 'right MFD', 'upper right knob', 'knob', 'RightMFD.F22KnobRight', [(0, ''), (1, '')], 0.5),
    (140, 'LowerMfdKnobLeft', 'lower MFD', 'upper left knob', 'knob', 'LowerMFD.F22KnobLeft', [(0, ''), (1, '')], 0.5),
    (141, 'LowerMfdKnobRight', 'lower MFD', 'upper right knob', 'knob', 'LowerMFD.F22KnobRight', [(0, ''), (1, '')], 0.5),
    # ICP
    (301, 'IcpWheelLowerLeft', 'ICP', 'lower left thumbwheel', 'wheel', 'ICP.F22WheelLowerLeft', [(0, ''), (1, '')], 0.5),
    (302, 'IcpWheelLowerRight', 'ICP', 'lower right thumbwheel', 'wheel', 'ICP.F22WheelLowerRight', [(0, ''), (1, '')], 0.5),
    (303, 'IcpRockerLeft', 'ICP', 'upper left rocker', 'rocker', 'ICP.F22RockerLeft', [(-1, 'lower half held'), (1, 'upper half held')], 0),
    (304, 'IcpDvr', 'ICP', 'DVR key', 'button', 'ICP.F22Dvr', [(1, 'pressed')], 0),
]
SIGNAL = {c[0]: 'F22' + c[1] for c in CONTROLS}
MESSAGE = {c[0]: c[5] for c in CONTROLS}
PART = {c[0]: ('P_' if c[4] == 'button' else 'K_') + c[1] for c in CONTROLS}

KNOBS, CLICKS, PRESSES, CLICK_KEYS = [], [], [], []      # ac_f22: KNOB_PARTS, CLICK_SWITCHES, PRESS_PARTS, CLICK_ICP
GUARDS = []                                              # (name, switch signal, R, t): make_f22 (servo), ac_f22 (bushing)

# ---- RADIO VOL knobs and the two ECS temperature knobs: K_VoxVolume's mesh, moved (no rotation). Its pointer as
# modelled looks 45 deg below starboard: angle = direction + 45. Volumes as the VOX knob (user 2026-11-07: OFF to the
# left, loudest to the right, clockwise over the top); TEMP / ANTIFOG from COLD at lower left clockwise over the top to
# HOT at lower right, where the pointer stands in the model
_VOX_BOX, _VOX_PIVOT, _VOX_BASE = ((7.45989, -0.44449, 0.63606), (7.48303, -0.42009, 0.66069)), (7.47019, -0.43153, 0.64998), -0.04987
for i in (23, 24, 28, 29, 30, 31, 32):
    t = FIT[i]['t']
    piv = _add(_VOX_PIVOT, t)
    KNOBS.append(dict(part=PART[i], material=SW, box=(_add(_VOX_BOX[0], t), _add(_VOX_BOX[1], t)),
                      above=(NR, _VOX_BASE + _dot(NR, t), -1.0), pivot=piv, axis=NR, source=SIGNAL[i],
                      angles=[(0.0, 270.0), (1.0, 0.0)] if i in (23, 24) else [(0.0, 225.0), (1.0, 45.0)]))
    CLICKS.append(('CommICSVolumeKnob', _add(piv, NR, 0.004), _neg(NR), None, MESSAGE[i], (0.012, 0.022)))

# ---- bat toggles of K_CNI's mesh in its pose (aft as modelled, 39.4 deg to the forward position): ECS MODE (AUTO aft /
# MAN forward), OBOGS (OFF aft / ON forward)
_CNI_BOX, _CNI_PIVOT, _CNI_BASE = ((7.2411, -0.3099, 0.59787), (7.25404, -0.30104, 0.61826)), (7.25063, -0.30707, 0.60122), -0.0285
for i in (26, 43):
    t = FIT[i]['t']
    piv = _add(_CNI_PIVOT, t)
    KNOBS.append(dict(part=PART[i], material=SW, box=(_add(_CNI_BOX[0], t), _add(_CNI_BOX[1], t)),
                      above=(NR, _CNI_BASE + _dot(NR, t), 0.0072), island_top=0.012, pivot=piv, axis=LAT_R,
                      source=SIGNAL[i], angles=[(0.0, 0.0), (1.0, 39.4)]))
    CLICKS.append(('APUMaster', _add(piv, NR, 0.010), NR, FWD, MESSAGE[i], (0.007, 0.022)))

# ---- toggles standing differently (cockpit_fit: the pieces reaching 9 mm above the cluster's lowest point move - bat or
# paddle - the nut stays; tilt and its direction measured on the bat):
#   19  FLCS AAR, bat tilted 28.4 deg outboard = AUTO: turns about the forward axis to the same tilt inboard = OFF
#   41 / 42  paddles (MIXTURE, FLOW) 20.5 deg aft = AUTO / BYPASS: forward = FULL / NORMAL
#   9   FUEL TANKS, a bat under a triangular cap, 20 deg forward = ALL (lettered forward of it): aft = EXT
for i, axis, swing, drag, size in ((19, None, 56.8, (0.0, -1.0, 0.0), (0.007, 0.022)), (41, LAT_R, 41.0, FWD, (0.008, 0.016)),
                                   (42, LAT_R, 41.0, FWD, (0.008, 0.016)), (9, LAT_L, -40.0, _neg(FWD), (0.013, 0.032))):
    f = FIT[i]
    n = _side(i)[0]
    if axis is None:
        axis = _unit(_add(FWD, n, -_dot(FWD, n)))             # forward in the panel: + = top to starboard (inboard)
    KNOBS.append(dict(part=PART[i], material=SW, box=tuple(map(tuple, f['box'])), above=(n, f['base'], 0.0),
                      island_top=0.009, pivot=tuple(f['pivot']), axis=axis, source=SIGNAL[i],
                      angles=[(0.0, 0.0), (1.0, swing)]))
    CLICKS.append(('APUMaster', _add(f['pivot'], n, 0.010), n, drag, MESSAGE[i], size))

# ---- guarded toggles: the FLCS BIT switch's mesh (bat between rails under a red lid hinged at its far end), turned
# and moved (cockpit_fit R, t: residual under 0.2 mm). The bat stands at the open end of the lid in the model and
# goes 44 deg under it; the lid lifts 105 deg by itself as the switch leaves that position (make_f22: a servo, as
# F22FlcsGuard). Cuts as ac_f22 K_FlcsBit / _guard_part, in this switch's frame
_BIT_BOX, _BIT_PIVOT, _BIT_BASE, _BIT_ORIGIN = ((7.1703, 0.3738, 0.6049), (7.18386, 0.38246, 0.62509)), (7.18064, 0.37971, 0.60839), -0.01181, (7.17904, 0.37914, 0.6113)


def _guarded(i):
    R, t = FIT[i]['R'], FIT[i]['t']
    Rt = [[R[r][c] for r in range(3)] for c in range(3)]
    xf = lambda p: _add(_mul(R, p), t)
    back = lambda v: _mul(Rt, (v[0] - t[0], v[1] - t[1], v[2] - t[2]))
    n, lat = _mul(R, NL), _mul(R, LAT_L)
    fwd = _cross(lat, n)
    base = _BIT_BASE + _dot(n, t)
    box = tuple(map(tuple, FIT[i]['box']))
    in_bat = lambda vs: all(all(_BIT_BOX[0][k] <= p[k] <= _BIT_BOX[1][k] for k in range(3)) for p in map(back, vs))
    piv = xf(_BIT_ORIGIN)
    hp = _dot(piv, n) - base

    def local(v):
        d = (v[0] - piv[0], v[1] - piv[1], v[2] - piv[2])
        return _dot(d, fwd), _dot(d, lat), _dot(v, n) - base

    def lid(verts):
        L = [local(v) for v in verts]
        if not all(abs(l) <= 0.0063 and -0.0046 <= f <= 0.0202 for f, l, _ in L):
            return False
        if min(h for _, _, h in L) < 0.0014:
            return False
        return not all(0.0019 <= abs(l) <= 0.0041 and -0.0006 <= f <= 0.0052 and h <= 0.0047 for f, l, h in L)
    hinge = tuple(round(piv[k] + fwd[k] * 0.0161 + n[k] * (0.0038 - hp), 5) for k in range(3))
    KNOBS.append(dict(part=PART[i], material=SW, box=box, above=(n, base, 0.0075), island_top=0.012, select=in_bat,
                      pivot=xf(_BIT_PIVOT), axis=lat, source=SIGNAL[i], angles=[(0.0, 0.0), (1.0, 44.0)]))
    KNOBS.append(dict(part=PART[i] + 'Guard', material=SW, box=box, select=lid, pivot=hinge, axis=lat,
                      source=SIGNAL[i] + 'Guard', angles=[(0.0, 0.0), (1.0, 105.0)]))
    CLICKS.append(('APUMaster', _add(piv, n, 0.010), n, _mul(R, FWD), MESSAGE[i], (0.007, 0.022)))
    GUARDS.append((PART[i][2:], SIGNAL[i], R, t))


for _i in (8, 16, 36, 45):
    _guarded(_i)

# ---- rotaries of their own shape (right console): the whole cluster turns about the panel normal through its centre
#   25  AIR SOURCE: five detents; the knob's flat side stands at lower starboard in the model (as the pointers of the
#       volume knobs beside it: angle = direction + 45). Lettering: OFF aft (270), R starboard (0), BOTH forward (90),
#       L port (180), DUMP between L and OFF (215)
#   37  AUX COMM MODE: a bar knob, fore-aft in the model (its forward end taken as the pointer: angle = direction - 90;
#       the bar looks the same turned half round). Lettering: KP 160, MAN 185, PRESET 210, GUARD 320
#   33  BRT: plain knob, OFF lettered to port: 270 deg clockwise from there
#   34 / 35  the two FREQ knobs: plain, one full turn over the range
for i, angles in ((25, [(0.0, -45.0), (1.0, 45.0), (2.0, 135.0), (3.0, 225.0), (4.0, 260.0)]),
                  (37, [(0.0, 70.0), (1.0, 95.0), (2.0, 120.0), (3.0, 230.0)]),
                  (33, [(0.0, 0.0), (1.0, -270.0)]), (34, [(0.0, 0.0), (1.0, -360.0)]), (35, [(0.0, 0.0), (1.0, -360.0)])):
    f = FIT[i]
    KNOBS.append(dict(part=PART[i], material=SW, box=tuple(map(tuple, f['box'])), above=(NR, f['base'], -1.0),
                      pivot=tuple(f['centre']), axis=NR, source=SIGNAL[i], angles=angles))
    top = _add(f['centre'], NR, 0.004)
    CLICKS.append(('CommICSVolumeKnob', top, _neg(NR), None, MESSAGE[i], (0.007, 0.014) if i in (34, 35) else (0.011, 0.022)))

# ---- push buttons cut out of the static object: pushed in while held (make_f22: as the screen keys)
#   13  ENGINES MOTOR (works already: Engines.F22Motor): the red button inside its guard ring - the pieces within
#       5.6 mm of the axis
#   38  OXYGEN TEST: the whole flat button
f = FIT[13]
PRESSES.append(dict(part='P_Motor', message='Engines.F22Motor', value=1.0, axis=_neg(NL), depth=0.0025, cut=True))
KNOBS.append(dict(part='P_Motor', material=SW, box=tuple(map(tuple, f['box'])), cylinder=(tuple(f['centre']), NL, 0.0056),
                  whole=True, axis=NL, pivot=tuple(f['centre']), press=True))
f = FIT[38]
PRESSES.append(dict(part=PART[38], message=MESSAGE[38], value=1.0, axis=_neg(NR), depth=0.0015, cut=True))
KNOBS.append(dict(part=PART[38], material=SW, box=tuple(map(tuple, f['box'])), axis=NR, pivot=tuple(f['centre']), press=True))
CLICKS.append(('TakeoffTrim', _add(f['centre'], NR, 0.004), _neg(NR), None, MESSAGE[38], (0.006, 0.008)))

# ---- the two knobs of each screen: knurled cylinders along the screen's normal in the frames' object (F22_MFD), each
# the whole pieces within 6.8 mm of its axis (body radius 6.2 mm; the mount plate under it, 16 mm, stays). No marks:
# 270 deg over the range, clockwise (seen by the pilot) for a rising value
for i in (113, 114, 115, 116, 117, 118, 121, 122, 123, 124, 140, 141):
    c, n = tuple(FIT[i]['centre']), _unit(FIT[i]['normal'])              # normal: towards the pilot
    KNOBS.append(dict(part=PART[i], material=MFD, box=(_add(c, (1, 1, 1), -0.013), _add(c, (1, 1, 1), 0.013)),
                      cylinder=(c, n, 0.0068), whole=True, pivot=c, axis=n, source=SIGNAL[i],
                      angles=[(0.0, 135.0), (1.0, -135.0)]))
    CLICKS.append(('CommICSVolumeKnob', _add(c, n, 0.004), _neg(n), None, MESSAGE[i], (0.007, 0.014)))

# ---- ICP. Lower thumbwheels: the meshes of the upper ones (ac_f22 K_WheelUFD / K_WheelHUD: an open arc, turned
# within one ridge pitch), 14.5 mm forward and 45.15 mm below them
for i, y in ((301, 1.0), (302, -1.0)):
    KNOBS.append(dict(part=PART[i], material=ACC2, box=((7.6455, min(y * 0.090, y * 0.106), 1.05785), (7.6785, max(y * 0.090, y * 0.106), 1.10685)),
                      axis=(0.0, 1.0, 0.0), source=SIGNAL[i], pitch=7.7, phases=4, positions=21))
    CLICK_KEYS.append(([7.6491, y * 0.0975, 1.0816], 'LeftMFDBrightnessKnob', MESSAGE[i], 1.0, 'step', 0.010, 0.004))
# rockers: upper left (an object of its own, CP__4.001; no function yet) and lower right (map range, ICP.MapRangeUp /
# Down: pieces of the ICP's key object). Each tips 6 deg about its lateral axis towards the half that is held
ROCKERS = [dict(part=PART[303], signal=SIGNAL[303], up=MESSAGE[303] + 'Up', down=MESSAGE[303] + 'Down',
                box=((7.6248, 0.0848, 1.1481), (7.6299, 0.0961, 1.1688)), new=True),
           dict(part='K_IcpRockerRight', signal='F22IcpRockerRight', up='ICP.MapRangeUp', down='ICP.MapRangeDown',
                box=((7.6249, -0.0794, 1.0776), (7.6299, -0.0681, 1.0983)), new=False)]
for r in ROCKERS:
    lo, hi = r['box']
    c = tuple(round((a + b) / 2, 5) for a, b in zip(lo, hi))
    # (material: the lower right rocker's arrows are pieces of the ICP's lettering object, F22_SCREEN - they go with it)
    KNOBS.append(dict(part=r['part'], material=r'^F22_(ACC2|SCREEN)$', box=r['box'], whole=True, legend=True, axis=(0.0, 1.0, 0.0), pivot=c,
                      source=r['signal'], angles=[(-1.0, -6.0), (0.0, 0.0), (1.0, 6.0)]))
    if r['new']:
        for msg, dz in ((r['up'], 0.005), (r['down'], -0.005)):
            CLICK_KEYS.append(([lo[0], c[1], round(c[2] + dz, 5)], 'MenuKeyAP', msg, 1.0, 'event', 0.005, 0.005))
# IFF and DVR keys: pieces of the ICP's key object, their lettering pieces of its lettering object (F22_SCREEN); the
# other keys are objects of their own, ac_f22 PRESS_PARTS
for part, y, msg, value in (('P_ICP_IFF', -0.0089, 'UpFront.Page', 2.0), (PART[304], -0.0880, MESSAGE[304], None)):
    KNOBS.append(dict(part=part, material=r'^F22_(ACC2|SCREEN)$', box=((7.6252, y - 0.0081, 1.1577), (7.6295, y + 0.0081, 1.1736)), whole=True,
                      axis=FWD, pivot=(7.6277, y, 1.1657), press=True))
    PRESSES.append(dict(part=part, message=msg, value=value, axis=FWD, cut=True))
CLICK_KEYS.append(([7.6277, -0.0880, 1.1657], 'MenuKeyAP', MESSAGE[304], 1.0, 'event'))


# ---- the armrest over the right console (user 2026-11-17: good to have, but it hides the OXYGEN and CNI panels under
# it): a pad 10 x 19 cm, 5 cm thick, standing out from the cockpit wall 6-10 cm above the console (pieces of the
# F22_ACC2 and F22_EXTRA objects; its wall bracket, F22_TUB, stays). A click folds it up against the wall about its
# outer upper edge - down is closed by the console under it - and a second click lowers it again. This one works: it
# is not in the table of free controls
ARMREST = dict(part='K_Armrest', signal='F22Armrest', message='Controls.F22Armrest', pivot=(7.19, -0.500, 0.753))
KNOBS.append(dict(part=ARMREST['part'], material=r'^F22_(ACC2|EXTRA)$', box=((7.135, -0.512, 0.696), (7.245, -0.314, 0.758)),
                  whole=True, axis=FWD, pivot=ARMREST['pivot'], source=ARMREST['signal'] + 'Servo',
                  angles=[(0.0, 0.0), (1.0, 90.0)]))
# its click zone: along the hinge line, on the pad in both positions (drag up = fold)
CLICKS.append(('APUMaster', (7.19, -0.478, 0.755), FWD, (0.0, 0.0, 1.0), ARMREST['message'], (0.03, 0.10)))


# ------------------------------------------------------------------------------------------------ dynamics
def dynamics(obj, dyn, anchor):
    """The state objects (make_f22.py). Toggles and selectors: input_discrete (one click = one position); knobs and
    wheels: input_default (0 .. 1 in equal clicks); buttons: an input_button made by make_f22 with the key press."""
    for i, name, panel, label, kind, message, positions, default in CONTROLS:
        sound = 'SwitchSound%sConsole.Trigger' % ('Left' if i in FIT and 'box' in FIT[i] and _side(i)[2] == 'Left' else 'Right')
        if kind in ('toggle', 'guarded', 'selector'):
            obj(dyn, 'input_discrete', SIGNAL[i], anchor, Message=message,
                Range=' %.1f %.1f ' % (positions[0][0], positions[-1][0]), Value=float(default),
                EventsUp=' %s ' % sound, EventsDown=' %s ' % sound)
        elif kind in ('knob', 'wheel'):
            n = 37 if i in (34, 35) else 21
            obj(dyn, 'input_default', SIGNAL[i], anchor, Message=message, Range=' 0.0 1.0 ', Positions=('uint', str(n)),
                Value=float(default))
    for name, signal, R, t in GUARDS:           # the lid follows its switch
        obj(dyn, 'logic_greater', signal + 'GuardOpen', anchor, Input0=signal + '.Output', Input1='0.5')
        obj(dyn, 'servoclassic', signal + 'Guard', anchor, Input=signal + 'GuardOpen.Output', Speed=5.0, P1=1.0, Position=0.0)
    # the armrest: 0 down / 1 folded up, about a second on its way
    obj(dyn, 'input_discrete', ARMREST['signal'], anchor, Message=ARMREST['message'], Range=' 0.0 1.0 ', Value=0.0,
        EventsUp=' SwitchSoundRightConsole.Trigger ', EventsDown=' SwitchSoundRightConsole.Trigger ')
    obj(dyn, 'servoclassic', ARMREST['signal'] + 'Servo', anchor, Input=ARMREST['signal'] + '.Output', Speed=1.2, P1=1.0,
        Position=0.0)
    for r in ROCKERS:                            # +1 / -1 while a half is held (a button has no output the dynamics can read)
        s = r['signal']
        obj(dyn, 'variable', s, anchor, Value='0.0')
        obj(dyn, 'event_value', s + 'Rest', anchor, Input='0.0', Events=' %s.Set ' % s)
        for half, v, msg in (('Up', '1.0', r['up']), ('Down', '-1.0', r['down'])):
            obj(dyn, 'event_value', s + half + 'Held', anchor, Input=v, Events=' %s.Set ' % s)
            obj(dyn, 'input_button', s + half, anchor, Message=msg, InputValue='1.0',
                Events=' %s%sHeld.Trigger ' % (s, half), EventsRelease=' %sRest.Trigger ' % s)


# ------------------------------------------------------------------------------------------------ the helpers' table
def doc():
    kinds = dict(toggle='two-position toggle', guarded='guarded toggle (the red lid lifts by itself)', selector='rotary selector',
                 knob='rotary knob', wheel='thumbwheel', rocker='rocker', button='push button')
    out = ['# F-22A cockpit controls prepared for new functions', '',
           'Every control below is already a moving, clickable part of the cockpit with a state of its own, but nothing in',
           'the aircraft reacts to it yet. Giving one a function needs the Python scripts only - no model work and no',
           'IPACS converter: run the installer again and the aircraft is rebuilt with your logic.', '',
           '## How to use a control', '',
           '1. Find its row. `State` is the name of its dynamics object; read it as `<State>.Output`.',
           '2. In `generator/make_f22.py` (or one of the system modules beside it) feed that output into your logic, the',
           '   same way the working switches do - search for `F22CNISwitch` (a toggle that powers the nav receivers) or',
           '   `F22VoiceVolume` (a knob) for a short worked example.',
           '3. The part already moves with the state (table and angles in `generator/cockpit_controls.py`); change the',
           '   positions, the default or the angles there if your function needs other ones.',
           '4. Run the installer (it will warn that the built files differ from the tested build: expected after a',
           '   change); check `tm.log` in the Aerofly user folder if the aircraft does not load.', '',
           'Values: toggles and selectors hold the whole numbers listed under `Positions`; knobs and wheels run from 0 to 1',
           'in equal clicks (20 clicks; the FREQ knobs 36); a button is an `input_button` - give it `Events` (see',
           '`push_button()` in make_f22.py for a held state). A rocker holds +1 / -1 while a half is pressed, 0 at rest.', '',
           '| Panel | Lettering | Kind | State (`.Output`) | Message of the click | Positions | Default |',
           '|---|---|---|---|---|---|---|']
    for i, name, panel, label, kind, message, positions, default in CONTROLS:
        if kind == 'button':
            state = 'F22Press' + PART[i][2:]
        else:
            state = SIGNAL[i]
        if kind == 'rocker':
            message = message + 'Up / ' + message + 'Down'
        pos = ', '.join(('%g = %s' % (v, l)) if l else '%g' % v for v, l in positions)
        if kind in ('knob', 'wheel'):
            pos = '0 .. 1' + ('' if not positions[0][1] else ' (%s .. %s)' % (positions[0][1], positions[-1][1]))
        out.append('| %s | %s | %s | `%s` | `%s` | %s | %g |' % (panel, label, kinds[kind], state, message, pos, default))
    out += ['', '## Controls that already work', '',
            'These came from the same static geometry and are wired to systems (see GUIDE.md): FLCS BIT and its guard, ALT FLAPS,',
            'YAW TRIM, FADEC, ENGINES MOTOR, LAMP TEST / NVG, CNI, AUX/ACP, RADIO VOL VOX, DN LOCK OVERRIDE, the screen and ICP',
            'keys, the two upper ICP thumbwheels (UFD and HUD brightness), the lower right ICP rocker (map range) and the',
            'armrest over the right console (a click folds it up against the wall: state `F22Armrest`).',
            'The keys of the screens and of the ICP all go in while held; the UFD keys `UFD.LeftPage`, `UFD.LeftKey2`,',
            '`UFD.LeftKey3` and `UFD.RightKey2` are still free (states `F22PressL_SMFD_1`, `F22PressL_SMFD_3`, `F22PressL_SMFD_4`,',
            '`F22PressR_SMFD_3`).', '',
            'Not prepared: the cap at the right sill and the flat round plugs at the lower corners of the MFD frames (not',
            'controls), DN LOCK OVERRIDE and RESET beside the gear handle (painted on the panel: click zone only).', '']
    return '\n'.join(out)


if __name__ == '__main__':
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'release', 'COCKPIT_CONTROLS.md')
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(doc())
    print('wrote', os.path.normpath(path), '-', len(CONTROLS), 'controls')
