"""Generate the F-22A Aerofly FS 4 configuration from the stock F/A-18.

    python3 make_f22.py <f18 dir> <parts.json> <geometry.json> <anim.json> <anim_pivots.json> <out dir>

Physics and systems come from the F/A-18 (twin afterburning turbofans, its flight controller, stabilators as rigid
bodies, the clickable avionics for the cockpit stage) re-dimensioned with the measured F-22 geometry; the CG sits at
the same fraction of the mean aerodynamic chord as on the F/A-18. Graphics are written from scratch from the
sampled DCS animation tables (anim.json). Same structure as make_su35.py (F-15E donor).
"""
import sys, os, re, json, math, shutil
import tmd
import tvc_f22
import burner_f22
import failures_f22
import breakage_f22

DONOR, PARTS, GEOM, ANIM, PIVOTS, OUT = sys.argv[1:7]
NAME = 'f22'
parts = json.load(open(PARTS, encoding='utf-8'))['parts']
CONNECTORS = json.load(open(PARTS, encoding='utf-8')).get('connectors', {})     # DCS cockpit connectors (merge_cockpit.py)
geo = json.load(open(GEOM, encoding='utf-8'))
anim = json.load(open(ANIM, encoding='utf-8'))
pivots = json.load(open(PIVOTS, encoding='utf-8'))


# ---------------------------------------------------------------------------------------------- helpers
def vec(s):
    return [float(x) for x in s.replace('(', ' ').replace(')', ' ').split()]


def fmt(v):
    return ' '.join('%.4f' % x for x in v)


def arr(vals):
    return ' ' + ' '.join('%.4f' % v for v in vals) + ' '


def setv(node, name, value):
    c = node.find(name)
    if c is None:
        raise KeyError('%s.%s' % (node.name, name))
    if isinstance(value, str):
        c.value = value
    elif isinstance(value, (list, tuple)):
        c.value = ' ' + fmt(value) + ' '
    else:
        c.value = '%.6g' % value


def scale(node, names, k):
    for n in names:
        c = node.find(n)
        if c is not None:
            c.value = '%.6g' % (float(c.value) * k)


def move(node, delta, fields=('R0', 'R1')):
    for c in node.children:
        if c.name in fields and len(vec(c.value)) == 3:
            c.value = ' ' + fmt([a + b for a, b in zip(vec(c.value), delta)]) + ' '


def lerp_rows(rows, key, x, field):
    rows = sorted(rows, key=lambda r: r[key])
    if x <= rows[0][key]:
        a, b = rows[0], rows[1]
    elif x >= rows[-1][key]:
        a, b = rows[-2], rows[-1]
    else:
        a, b = next((a, b) for a, b in zip(rows, rows[1:]) if a[key] <= x <= b[key])
    u = (x - a[key]) / (b[key] - a[key])
    return a[field] + u * (b[field] - a[field])


def mac(ys, les, tes):
    """Mean aerodynamic chord length and its leading-edge x for a piecewise linear half wing."""
    area = c2 = xle = 0.0
    for i in range(len(ys) - 1):
        n = 20
        for k in range(n):
            t = (k + 0.5) / n
            y0 = ys[i] + t * (ys[i + 1] - ys[i])
            dy = abs(ys[i + 1] - ys[i]) / n
            le = les[i] + t * (les[i + 1] - les[i])
            c = le - (tes[i] + t * (tes[i + 1] - tes[i]))
            area += c * dy
            c2 += c * c * dy
            xle += le * c * dy
    return c2 / area, xle / area, area


def obj(lst, type_, name, before=None, **fields):
    n = tmd.Node(type_, name, leaf=False)
    for k, v in fields.items():
        if isinstance(v, tuple):
            t, v = v
        else:
            t = 'tmvector2d' if k in ('Map', 'Range') else ('float64' if isinstance(v, float) else 'string8')
        n.children.append(tmd.Node(t, k, v if isinstance(v, str) else '%.6g' % v))
    if before is None:
        lst.children.append(n)
    else:
        lst.children.insert(lst.children.index(before), n)
    return n



# ---------------------------------------------------------------------------------------------- load donor
root = tmd.load(os.path.join(DONOR, 'f18.tmd'))
mm = root.children[0].children[0]
dyn, gfx, snd = mm.find('DynamicObjects'), mm.find('GraphicObjects'), mm.find('SoundObjects')
D = {o.name: o for o in dyn.children}
DONOR_R0 = {o.name: o.get('R0') for o in dyn.children if o.find('R0') is not None}


def stations(o):
    """aerowing2 stations as dicts (floats where numeric)."""
    out = []
    for st in o.find('Stations').children:
        d = {}
        for c in st.children:
            try:
                d[c.name] = float(c.value)
            except ValueError:
                d[c.name] = c.value.strip()
        out.append(d)
    return out


def set_stations(o, rows):
    lst = o.find('Stations')
    lst.children = []
    for r in rows:
        st = tmd.Node('aerowing_station', '', leaf=False)
        for k in ('Airfoil', 'InputFlapAngle', 'InputSlatAngle'):
            if r.get(k):
                st.children.append(tmd.Node('string8', k, r[k]))
        for k in ('LE', 'TE', 'Y', 'Z', 'Incidence', 'FlapFraction'):
            st.children.append(tmd.Node('float64', k, '%.4f' % r[k]))
        lst.children.append(st)


# donor CG position as a fraction of its MAC (main wing only - the F/A-18 rows also hold the LEX strakes)
fw = [r for r in stations(D['LeftWingAero']) if r['Airfoil'] != 'AirfoilStrake']
f_mac, f_xle, _ = mac([r['Y'] for r in fw], [r['LE'] for r in fw], [r['TE'] for r in fw])
masses = [(float(o.get('Mass')), vec(o.get('R0'))[0]) for o in dyn.children if o.type == 'rigidbody']
DONOR_MASS = sum(m for m, _ in masses)
f_cg = sum(m * x for m, x in masses) / DONOR_MASS
CG_FRACTION = (f_xle - f_cg) / f_mac
print('F/A-18: mass %.0f kg, MAC %.2f m, LEMAC x=%.2f, CG x=%.2f -> %.1f%% MAC'
      % (DONOR_MASS, f_mac, f_xle, f_cg, 100 * CG_FRACTION))

# ---------------------------------------------------------------------------------------------- geometry
wing = geo['wing']
WING_ROOT, WING_TIP = wing[0]['y'], wing[-1]['y'] + 0.2
FLAPERON_END = 4.507                     # DCS: flaperons 2.0 .. 4.51, ailerons 4.51 .. 5.84
AILERON_END = 5.836
# Aero stations: the DCS wing rows start at the body side (y 2.6), which left 34 m2 of lifting surface for a jet whose
# 78 m2 reference area includes the blended body - with the donor's fuel on top the wing loading was 2-3x the F/A-18's
# (test flight 5: late lift-off, sluggish at low speed). The wing is continued inboard as a glove to y 1.0 (planform
# extrapolated from the DCS rows) and, like the donor's LEX strakes, a chine strake from y 0.6.
STRAKE_Y, GLOVE_Y = 0.6, 1.0
wy = [WING_ROOT, FLAPERON_END, FLAPERON_END + 0.05, AILERON_END, WING_TIP]
ay = [STRAKE_Y, GLOVE_Y] + wy
wle = [lerp_rows(wing, 'y', y, 'le') for y in ay]
wte = [lerp_rows(wing, 'y', y, 'te') for y in ay]
wz = [lerp_rows(wing, 'y', y, 'z') for y in ay]
# CG at the donor's fraction of the main-wing MAC (glove included, strake excluded - as measured on the F/A-18)
s_mac, s_xle, s_area = mac(ay[1:], wle[1:], wte[1:])
_, _, strake_area = mac(ay[:2], wle[:2], wte[:2])
# + 4 % MAC aft of the donor's fraction (test 6 at 17.9 %: x 0.88, 1.34 m ahead of the main wheels - the weight moment
# about the wheels was ~4x the Hornet's with only ~2x its stabilator power: the nose did not lift before ~200 kt and
# even pitched down with speed). The F-22 is a relaxed-stability jet; the Hornet's control laws keep it flying.
# + another 4 % (test 9, 2026-10-20): rough neutral points (lift slopes 3.5 / 4 per rad, downwash factor 0.6, no
# fuselage) give the Hornet ~4 % MAC static margin, this F-22 ~13 %: the Hornet's control laws hunted with it - pitch
# bobbing on the take-off run at 200-228 kt, trim running to -50 % / +100 % holding low altitude, the nose dropping on
# the landing. Half of the difference first, telemetry to follow.
CG_AFT = 0.08
X_CG = s_xle - (CG_FRACTION + CG_AFT) * s_mac
print('F-22: wing area (outboard of y=%.1f) %.1f m2 + strake %.1f m2 per side, MAC %.2f, LEMAC %.2f -> CG x=%.2f'
      % (GLOVE_Y, s_area, strake_area, s_mac, s_xle, X_CG))
wle, wte, wz = wle[2:], wte[2:], wz[2:]           # the wing body / joint geometry below uses the DCS wing rows
ale = [lerp_rows(wing, 'y', y, 'le') for y in ay]
ate = [lerp_rows(wing, 'y', y, 'te') for y in ay]
az = [lerp_rows(wing, 'y', y, 'z') for y in ay]

stab = [r for r in geo['stab'] if r['te'] < r['le'] - 1.0]
fin = geo['fin']
EYE = geo['eye']
wheels = {w['which']: w for w in geo['wheels']}


def pivot_of(arg):
    n = next(a for a in pivots if any(r['arg'] == arg for r in a['rot']))
    r = next(r for r in n['rot'] if r['arg'] == arg)
    return n['pivot'], r['axis']


# ---------------------------------------------------------------------------------------------- masses, bodies
# Rigid bodies = empty mass: the donor's fuel tanks add the fuel on top (scaled to the F-22's 8.2 t below). The first
# version put 26 t (half fuel) into the bodies and the F/A-18 tanks added up to 4.9 t more: ~31 t with full tanks.
TOTAL = 19700.0       # F-22A operating empty mass
FUEL = 8200.0         # internal fuel
GEAR_SCALE = 1.4
ENGINE_X, ENGINE_Y, ENGINE_Z = -2.9, 0.66, 0.27      # F119 centre; nozzle exits at x -5.4
# Wings: 2 x 2.5 t (a quarter of the empty mass, typical is 10-12 %) on the mid-span of the exposed wing (y 4.7 of
# 6.8 m; the F/A-18's at 44 % of its half span) gave 2.2x the Hornet's roll inertia per unit mass - sluggish roll the
# Hornet's control laws (sized on its own inertia) chased on the approach. Now 1.5 t each at 30 % of the exposed span
# (the structure sits towards the root), the rest goes to the fuselage.
WING_MASS, WING_BODY_SPAN = 1500.0, 0.3
for side, s in (('Left', 1), ('Right', -1)):
    setv(D[side + 'Wing'], 'Mass', WING_MASS)
    setv(D[side + 'Stabilator'], 'Mass', 300.0)
    setv(D[side + 'VerticalStabilizer'], 'Mass', 250.0)
    setv(D['Engine%dBody' % (1 if s > 0 else 2)], 'Mass', 1800.0)
for o in dyn.children:
    if o.type == 'rigidbody' and 'Gear' in o.name:
        scale(o, ('Mass',), GEAR_SCALE)
for side, s in (('Left', 1), ('Right', -1)):
    w = D[side + 'Wing']
    yc = WING_ROOT + WING_BODY_SPAN * (WING_TIP - WING_ROOT)
    setv(w, 'R0', [lerp_rows(wing, 'y', yc, 'le') * 0.6 + lerp_rows(wing, 'y', yc, 'te') * 0.4, s * yc,
                   lerp_rows(wing, 'y', yc, 'z')])
    setv(w, 'InertiaLength', [4.0, 4.0, 0.2])
    setv(D['JointFuselage%sWing' % side], 'R0', [(wle[0] + wte[0]) / 2, s * WING_ROOT, wz[0]])
    # stabilator: body at the stab centre, hinge on the DCS pivot (DCS arg 16 = left)
    piv, axis = pivot_of(16)
    e = D[side + 'Stabilator']
    sm = stab[len(stab) // 2]
    setv(e, 'R0', [(sm['le'] + sm['te']) / 2, s * sm['y'], sm['z']])
    setv(e, 'InertiaLength', [2.6, 2.4, 0.1])
    setv(D['JointFuselage%sStabilator' % side], 'R0', [piv[0], s * abs(piv[1]), piv[2]])
    # canted fins: body at the fin centre, joint at the fin root
    fm = fin[len(fin) // 2]
    setv(D[side + 'VerticalStabilizer'], 'R0', [(fm['le'] + fm['te']) / 2, s * fm['y'], fm['z']])
    f0 = fin[0]
    setv(D['Joint%sVerticalStabilizer' % side], 'R0', [(f0['le'] + f0['te']) / 2, s * f0['y'], f0['z'] - 0.3])
    eb = D['Engine%dBody' % (1 if s > 0 else 2)]
    setv(eb, 'R0', [ENGINE_X, s * ENGINE_Y, ENGINE_Z])
    setv(D['JointEngine%dBody' % (1 if s > 0 else 2)], 'R0', [ENGINE_X, s * ENGINE_Y, ENGINE_Z])
# Stiffer airframe joints than the donor's: the F/A-18 fins hang on free springs (Kp 1e6, unlocked) and its wing
# joint is sized for a 1.5 t wing on a 1.5 m arm. The F-22 fins are twice as large and its wings heavier on a longer
# arm; the first test diverged (NaN) during the take-off run. Fins locked as on the F-15E (the Su-35 donor), wing
# joint stiffness scaled to keep the donor's wing frequency (Kp ~ m r^2).
for side in ('Left', 'Right'):
    j = D['Joint%sVerticalStabilizer' % side]
    setv(j, 'Kp', 1.0e7); setv(j, 'Kd', 5.0e4); setv(j, 'InputLock', 1.0)
    jw, w = D['JointFuselage%sWing' % side], D[side + 'Wing']
    r2 = sum((a - b) ** 2 for a, b in zip(vec(jw.get('R0')), vec(w.get('R0'))))
    k = float(w.get('Mass')) * r2 / (1500.0 * 1.53 ** 2)
    scale(jw, ('Kp', 'Kd'), k)
print('wing joint stiffness x%.2f' % k)
f = D['Fuselage']
setv(f, 'InertiaLength', [12.0, 3.0, 1.6])
others = [(float(o.get('Mass')), vec(o.get('R0'))[0]) for o in dyn.children if o.type == 'rigidbody' and o.name != 'Fuselage']
f_mass = TOTAL - sum(m for m, _ in others)
setv(f, 'Mass', f_mass)
# fuel tanks: the donor's sequence (MassMap: total fuel -> tank content) scaled to 8.2 t
k_fuel = FUEL / sum(float(o.get('Mass')) for o in dyn.children if o.type == 'fuel_tank')
for o in dyn.children:
    if o.type == 'fuel_tank':
        scale(o, ('Mass', 'Capacity'), k_fuel)
        o.find('MassMap').value = ' ' + ' '.join('(%.2f %.2f)' % (a * k_fuel, b * k_fuel) for a, b in
                                                 zip(vec(o.get('MassMap'))[0::2], vec(o.get('MassMap'))[1::2])) + ' '
tanks = [(float(o.get('Mass')), o.get('Body').strip()) for o in dyn.children if o.type == 'fuel_tank']
wing_fuel = [(m, vec(D[b].get('R0'))[0]) for m, b in tanks if b != 'Fuselage']
# empty CG on X_CG, as before: where the game applies the tank masses is not documented (on the body origin they move
# the CG forward with fuel - the stable direction; at the aircraft origin a few cm aft)
x_f = (X_CG * TOTAL - sum(m * x for m, x in others)) / f_mass
setv(f, 'R0', [x_f, 0.0, 0.1])
print('mass %.0f kg empty + %.0f kg fuel (x%.2f of the donor tanks), fuselage %.0f kg at x=%.2f'
      % (TOTAL, FUEL, k_fuel, f_mass, x_f))
# weight and balance bookkeeping of the donor (fuel page, approach speed)
setv(D['EmptyMass'], 'Value', TOTAL)
setv(D['LEMAC'], 'Value', s_xle)
setv(D['MAC'], 'Value', s_mac)
for n in ('CGxLeftTransferFuelTank', 'CGxLeftFeedFuelTank', 'CGxRightFeedFuelTank', 'CGxRightTransferFuelTank'):
    setv(D[n], 'Input', X_CG)
setv(D['CGxWingTanks'], 'Input', wing_fuel[0][1])
fp = D['FuelPrediction']
for n, v in (('LEMAC', s_xle), ('MAC', s_mac), ('EmptyMass', TOTAL), ('ZeroFuelMass', TOTAL)):
    setv(fp, n, v)
setv(D['ApproachAirspeed'], 'WingArea', 2 * (s_area + strake_area))

# ---------------------------------------------------------------------------------------------- landing gear
def strut_extension(damper):
    v = [a - b for a, b in zip(vec(damper.get('R0')), vec(damper.get('R1')))]
    lmax = float(damper.get('LimitLengthMax'))
    return math.sqrt(max(lmax ** 2 - v[0] ** 2 - v[1] ** 2, 0.0)) - abs(v[2])


def rotate(p, origin, axis, angle):
    """Rotate point p about the axis through origin (Rodrigues)."""
    k = [a / math.sqrt(sum(x * x for x in axis)) for a in axis]
    v = [a - b for a, b in zip(p, origin)]
    c, s_ = math.cos(angle), math.sin(angle)
    kxv = [k[1] * v[2] - k[2] * v[1], k[2] * v[0] - k[0] * v[2], k[0] * v[1] - k[1] * v[0]]
    kv = sum(a * b for a, b in zip(k, v))
    return [origin[i] + v[i] * c + kxv[i] * s_ + k[i] * kv * (1 - c) for i in range(3)]


# Gear travel and static compression from the DCS mod (F-22A.lua, the original block kept as a comment there): main
# legs stroke 0.099 m, 0.050 m compressed at the nominal mass (27.9 t); nose leg 0.317 m, 0.199 m. The animated
# strokes agree (main 0.100, nose 0.324 m) - the physical travel is the drawn one, nothing beyond. Version 1 already
# had the main travel but kept the donor's carrier-gear forces (sized for 0.39 m of wheel travel) on it: ~7 MN/m at
# the wheel, the leg hardly compressed under the weight and the touchdown came through hard.
main_stroke = max(math.sqrt(sum(x * x for x in l['translation'][-1])) for p in anim.values() for l in p['links']
                  if l['kind'] == 'table' and l['arg'] in (4, 6))
nose_stroke = max(math.sqrt(sum(x * x for x in l['translation'][-1])) for p in anim.values() for l in p['links']
                  if l['kind'] == 'table' and l['arg'] == 1)
M_NOMINAL = 27900.0
MAIN_STATIC, NOSE_STATIC = 0.050 / 0.099, 0.199 / 0.317       # static compression, fraction of the stroke
MAIN_GEO = {}
for side in ('Left', 'Right'):
    j, dmp, hull = D['Joint%sGearLower' % side], D['%sGearDamper' % side], D['%sWheelHull' % side]
    o, ax = vec(j.get('R0')), vec(j.get('X0'))
    r0, r1, w = vec(dmp.get('R0')), vec(dmp.get('R1')), vec(hull.get('R0'))
    grid = [i * 0.0005 for i in range(-1600, 1601)]
    z_of = lambda a: rotate(w, o, ax, a)[2]
    l_of = lambda a: math.dist(r0, rotate(r1, o, ax, a))
    at_z = lambda z: min(grid, key=lambda a: abs(z_of(a) - z))
    a_c = min(grid, key=lambda a: abs(l_of(a) - float(dmp.get('LimitLengthMin'))))      # compressed
    a_e = at_z(z_of(a_c) - main_stroke)                                                 # extended
    a_s = at_z(z_of(a_e) + MAIN_STATIC * main_stroke)                                   # static
    ratio = lambda a: abs((z_of(a + 0.002) - z_of(a - 0.002)) / (l_of(a + 0.002) - l_of(a - 0.002)))
    setv(dmp, 'LimitLengthMax', round(l_of(a_e), 4))
    MAIN_GEO[side] = dict(l_ext=l_of(a_e), l_cmp=l_of(a_c), l_s=l_of(a_s), r_ext=ratio(a_e), r_cmp=ratio(a_c),
                          r_s=ratio(a_s), arm=(a_e, a_c, w[2] - z_of(a_e)))
fd = D['FrontGearDamper']
setv(fd, 'LimitLengthMin', round(float(fd.get('LimitLengthMax')) - nose_stroke, 4))
NOSE_EXT = strut_extension(fd)
ARM = {side: MAIN_GEO[side]['arm'] for side in ('Left', 'Right')}
print('main gear: stroke %.3f m, damper %.3f .. %.3f m (lever %.1f .. %.1f); nose stroke %.3f m'
      % (main_stroke, MAIN_GEO['Left']['l_cmp'], MAIN_GEO['Left']['l_ext'], MAIN_GEO['Left']['r_ext'],
         MAIN_GEO['Left']['r_cmp'], nose_stroke))
MAIN_EXT = ARM['Left'][2]
LOAD = TOTAL / DONOR_MASS
nw, lw = wheels['nose'], wheels['left']
f_nose = vec(D['LeftFrontWheelHull'].get('R0'))
d_nose = [nw['center'][0] - f_nose[0], 0.0, nw['center'][2] + NOSE_EXT - f_nose[2]]
for o in dyn.children:
    # everything hanging on the nose leg moves with it (incl. the retraction cylinder - IPACS spells it
    # 'Cyclinder' - and the catapult launch bar; left behind they tore the gear apart: NaN in the first test)
    if re.match(r'(Joint)?NoseGear(Upper|Middle|Lower|Airbrake)$|FrontGear(Damper|Cyclinder)$|(Left|Right)FrontWheelHull$|'
                r'(Joint)?LaunchBar$|(LaunchBar|Holdback)AttachmentPoint$', o.name):
        move(o, d_nose)
# one nose wheel on the F-22: the donor's twin hulls side by side, half the width each
for side, s in (('Left', 1), ('Right', -1)):
    h = D['%sFrontWheelHull' % side]
    r = vec(h.get('R0'))
    setv(h, 'R0', [r[0], s * nw['width'] / 4, r[2]])
    setv(h, 'Radius', nw['radius']); setv(h, 'Width', nw['width'] / 2); setv(h, 'RimRadius', 0.55 * nw['radius'])
f_main = vec(D['LeftWheelHull'].get('R0'))
for side, s in (('Left', 1), ('Right', -1)):
    d = [lw['center'][0] - f_main[0], s * (abs(lw['center'][1]) - abs(f_main[1])), lw['center'][2] + MAIN_EXT - f_main[2]]
    for o in dyn.children:
        if re.match(r'(Joint)?%sGear(Lower|WheelAssembly|Airbrake)?$|%sGear(Damper|Cyclinder)$|%sWheelHull$' % ((side,) * 3), o.name):
            move(o, d)
    h = D['%sWheelHull' % side]
    setv(h, 'Radius', lw['radius']); setv(h, 'Width', lw['width']); setv(h, 'RimRadius', 0.55 * lw['radius'])
moved_bodies = {n for n in D if D[n].type == 'rigidbody' and re.search(r'Gear|LaunchBar', n)}
for o in dyn.children:
    att = {o.get(k, '').strip() for k in ('Body', 'Body0', 'Body1')} & moved_bodies
    if att and o.find('R0') is not None and o.type != 'rigidbody' and vec(o.get('R0')) == vec(DONOR_R0.get(o.name, '0 0 0')):
        raise SystemExit('not moved with its gear body: %s %s' % (o.type, o.name))
for o in dyn.children:
    if o.type == 'wheel':
        scale(o, ('K', 'D'), LOAD)
    if o.type == 'oleo_pneumatic_damper':
        scale(o, ('LimitSpring', 'LimitDamping', 'ForceCompressed', 'DampingCompressed', 'ForceExtended',
                  'DampingExtended'), LOAD)
    # (the gear retraction cylinders carry no aircraft weight: scaled x2.5 with gear bodies only x1.4 heavier, they
    # blew the physics up (NaN) when the retraction ended against the stop - telemetry: smooth climb, then NaN)
# Oleo forces from the static point: the leg's share of the weight at the nominal mass sits at the DCS mod's static
# compression. Wheel spring linear from a gas preload (OLEO_PRELOAD x the static load, fully extended) through the
# static point; damping OLEO_DAMPING of critical over the whole stroke (0.5 shook the aircraft on the runway: on the
# 210 kg main leg the damping/mass came to ~700 1/s, the donor's stable value at its static point ~380 1/s). Force and
# damping are taken linear in the damper length between the two ends (the game's oleo law is not documented) and
# converted through the leg geometry (wheel rise per damper shortening: trailing arm on the mains, 1 on the nose).
OLEO_PRELOAD, OLEO_DAMPING = 0.2, 0.25


def oleo(dmp, load, stroke, static, l_ext, l_cmp, l_s, r_ext=1.0, r_cmp=1.0, r_s=1.0):
    k_w = (1 - OLEO_PRELOAD) * load / (static * stroke)
    f_cmp = OLEO_PRELOAD * load + k_w * stroke
    u = (l_ext - l_s) / (l_ext - l_cmp)                   # static point along the damper travel
    f_ext = (load * r_s - u * f_cmp * r_cmp) / (1 - u)
    c_w = OLEO_DAMPING * 2 * math.sqrt(k_w * load / 9.81)
    setv(dmp, 'ForceCompressed', f_cmp * r_cmp)
    setv(dmp, 'ForceExtended', max(f_ext, 0.05 * load * r_ext))
    setv(dmp, 'DampingCompressed', c_w * r_cmp ** 2)
    setv(dmp, 'DampingExtended', c_w * r_ext ** 2)
    return k_w


x_n, x_m = nw['center'][0], lw['center'][0]
W_MAIN = M_NOMINAL * 9.81 * (X_CG - x_n) / (x_m - x_n) / 2
W_NOSE = M_NOMINAL * 9.81 - 2 * W_MAIN
for side in ('Left', 'Right'):
    gm = MAIN_GEO[side]
    k_main = oleo(D['%sGearDamper' % side], W_MAIN, main_stroke, MAIN_STATIC, gm['l_ext'], gm['l_cmp'], gm['l_s'],
                  gm['r_ext'], gm['r_cmp'], gm['r_s'])
l_max = float(fd.get('LimitLengthMax'))
k_nose = oleo(fd, W_NOSE, nose_stroke, NOSE_STATIC, l_max, l_max - nose_stroke, l_max - NOSE_STATIC * nose_stroke)
print('gear at %.0f kg: main %.0f N per wheel, %.2f MN/m (%.1f Hz); nose %.0f N, %.2f MN/m (%.1f Hz)'
      % (M_NOMINAL, W_MAIN, k_main / 1e6, math.sqrt(k_main * 9.81 / W_MAIN) / (2 * math.pi), W_NOSE, k_nose / 1e6,
         math.sqrt(k_nose * 9.81 / W_NOSE) / (2 * math.pi)))
# (tyres keep the donor's damping: 1.6 % of the stiffness on the 70 kg wheel assemblies - D/m ~860 1/s - shook the
# aircraft on the runway and the tyres lost their grip, it slid sideways standing still)

# ---------------------------------------------------------------------------------------------- aerodynamics
# aerowing2: InputFlapAngle on station i deflects the segment i -> i+1 (radians). F-22: flaperons (flap + roll)
# inboard, ailerons outboard; the donor's leading-edge flaps (InputSlatAngle) on the whole span.
anchor = D['GearInput']
for side, s in (('Left', 1), ('Right', -1)):
    # flaperon = flap + the roll part of the aileron command only: the Hornet droops its ailerons with the flaps
    # (FCS page: TEF 30 / AIL 30 on the ground), the plain sum put the flaperons ~60 deg down - far past the flap stall
    # (ClFlapStall), a roll input changed drag instead of lift: the nose yawed and rose instead of banking
    o_ = 'Right' if side == 'Left' else 'Left'
    obj(dyn, 'mixlinear', 'AileronRoll' + side, D[side + 'WingAero'], Input0='Servo%sAileron.Output' % side,
        Input1='Servo%sAileron.Output' % o_, Weight0=0.5, Weight1=-0.5)
    obj(dyn, 'sum', 'Flaperon' + side, D[side + 'WingAero'], Inputs=' Servo%sFlap.Output AileronRoll%s.Output ' % (side, side))
    # stations run from -y to +y: the right wing is the left one reversed, and a station's flap / slat input drives
    # the segment towards the next station (so on the right wing it comes from the outboard neighbour)
    seg = []
    for i in range(len(ay) - 1):
        mid = (ay[i] + ay[i + 1]) / 2
        flap = None
        if WING_ROOT < mid < FLAPERON_END:
            flap = 'Flaperon%s.Output' % side
        elif FLAPERON_END + 0.05 < mid < AILERON_END:
            flap = 'Servo%sAileron.Output' % side
        seg.append((flap, 'Servo%sSlat.Output' % side if mid > WING_ROOT else None))
    rows = []
    for i, y in enumerate(ay):
        rows.append({'Airfoil': 'AirfoilStrake' if y == STRAKE_Y else 'NACA65A005',
                     'LE': ale[i], 'TE': ate[i], 'Y': s * y, 'Z': az[i], 'Incidence': 0.0, 'FlapFraction': 0.25})
    if s > 0:
        for i in range(len(ay) - 1):
            rows[i]['InputFlapAngle'], rows[i]['InputSlatAngle'] = seg[i]
    else:
        rows = list(reversed(rows))
        n_ = len(ay)
        for j in range(n_ - 1):          # reversed station j starts the segment of left-wing segment n_-2-j
            rows[j]['InputFlapAngle'], rows[j]['InputSlatAngle'] = seg[n_ - 2 - j]
    set_stations(D[side + 'WingAero'], rows)
    pick = [stab[0], stab[len(stab) // 3], stab[2 * len(stab) // 3], stab[-1]]
    pick.append({'y': stab[-1]['y'] + 0.2, 'le': stab[-1]['le'] - 0.15, 'te': stab[-1]['te'] + 0.2, 'z': stab[-1]['z']})
    rows = [{'Airfoil': 'AirfoilHorizontalStabilizer', 'LE': r['le'], 'TE': r['te'], 'Y': s * r['y'], 'Z': r['z'],
             'Incidence': 0.0, 'FlapFraction': 0.0} for r in pick]
    set_stations(D[side + 'StabilatorAero'], rows if s > 0 else list(reversed(rows)))
    # rudder (segment 0) over the lower three quarters of the fin as on the F-22 (was half: rudder power per yaw
    # inertia ~0.55x the Hornet's, the control laws could not keep the sideslip out of banked turns)
    pick = [fin[0], fin[3 * len(fin) // 4], fin[-1]]
    rows = [{'Airfoil': 'AirfoilVerticalStabilizer', 'InputFlapAngle': 'Servo%sRudder.Output' % side if k == 0 else None,
             'LE': r['le'], 'TE': r['te'], 'Y': s * r['y'], 'Z': r['z'], 'Incidence': 0.0, 'FlapFraction': 0.25}
            for k, r in enumerate(pick)]
    set_stations(D[side + 'VerticalStabilizerAero'], rows)
fa = D['FuselageAero']
rows = [r for r in geo['fuselage'] if r['width'] > 0.3][::3]
rows.sort(key=lambda r: -r['x'])
rows.insert(0, {'x': geo['bounds'][1][0] - 0.05, 'width': 0.05, 'z_min': rows[0]['z_min'], 'z_max': rows[0]['z_min'] + 0.05})
for k, f_ in (('StationX', lambda r: r['x']), ('StationY', lambda r: 0.0), ('StationZ', lambda r: (r['z_min'] + r['z_max']) / 2),
              ('StationWidth', lambda r: r['width']), ('StationHeight', lambda r: r['z_max'] - r['z_min'])):
    setv(fa, k, arr(f_(r) for r in rows))
setv(fa, 'StationShape', ' ' + ' '.join('0' for _ in rows) + ' ')

# ---------------------------------------------------------------------------------------------- engines, collision, cameras
for e, s in (('Engine1', 1), ('Engine2', -1)):   # Engine1 = left (+y), as on the F/A-18
    o = D[e]
    setv(o, 'R0', [-5.3, s * ENGINE_Y, ENGINE_Z])
    setv(o, 'MilitaryThrust', 116000.0)          # F119-PW-100
    setv(o, 'AfterburnerThrust', 156000.0)
# wave drag. The jet_engine military thrust falls with air density and gains nothing with Mach (only the afterburner
# does), so with the Hornet's wave drag (CdA 4 m2 x 0.29 at M1.2 .. 0.51 at M1.8) the F-22 held M1.21 on dry thrust
# at 34000 ft and reached M2.1 with afterburner. F-22 wave drag as CdA (m2) at 34000 ft: low through the transonic
# rise and supercruise (dry thrust ~74 kN there balances M1.5), a wall above M2.0 for the M2.25 limit; scaled up
# towards the ground like the stock F-15E (static pressure stands in for altitude), where it keeps the Hornet's ~M1.6.
# The airbrake control stays within 0..1 as on the stock jets: both maps are normalised (Mach map / 10, altitude
# factor / 5) and the scale goes into Area x Cd = 50 m2.
WAVE_CDA = [(0.80, 0.00), (0.90, 0.05), (1.00, 0.25), (1.10, 0.35), (1.20, 0.33), (1.50, 0.22), (1.70, 0.35),
            (1.90, 0.75), (2.10, 1.40), (2.25, 2.10), (2.50, 4.00), (4.00, 10.0)]
# above 34000 ft the afterburner gains with altitude (60000 ft reached M2.72 with the factor falling there): rising
# again holds ~M2.25 up to 65000 ft (estimate with T = AB x sigma x (1 + 0.54 M + 1.07e-4 h), dry thrust ~M1.5)
WAVE_ALT = [(5000, 1.65), (7170, 1.52), (11600, 1.33), (18750, 1.17), (24540, 1.0), (30090, 1.5), (46560, 3.0),
            (69680, 4.5), (101325, 5.0)]
wave = D['MachDragIncrease']
wave.name = 'MachDragIncreaseMach'
setv(wave, 'Map', ' ' + ' '.join('(%.2f %.3f)' % (m, c / 10.0) for m, c in WAVE_CDA) + ' ')
obj(dyn, 'linear_interpolation', 'MachDragAltitudeFactor', D['WaveDrag'], Input='PitotTube.StaticPressure',
    Map=' ' + ' '.join('(%d %.2f)' % (p_, f_ / 5.0) for p_, f_ in WAVE_ALT) + ' ')
obj(dyn, 'product', 'MachDragIncrease', D['WaveDrag'],
    Inputs=' MachDragIncreaseMach.Output MachDragAltitudeFactor.Output ')
setv(D['WaveDrag'], 'Area', 25.0)
setv(D['WaveDrag'], 'Cd', 2.0)
setv(D['AirBrake'], 'R0', [-3.4, 0.0, 0.3])      # the speed brake is the split flaperons, ailerons and rudders
setv(D['AirBrake'], 'Area', 1.2)
col = {'CollisionFuselage': 'ColFuselage', 'CollisionLeftVerticalStabilizer': 'ColFinLeft',
       'CollisionRightVerticalStabilizer': 'ColFinRight', 'CollisionLeftWing': 'ColWingLeft',
       'CollisionRightWing': 'ColWingRight', 'CollisionLeftStabilator': 'ColStabLeft',
       'CollisionRightStabilator': 'ColStabRight'}
# Hull contact: the F/A-18's 5e6 N/m (D 1e4) is the softest of the stock aircraft (~330 N/m per kg); on the 20-28 t
# F-22 (~180 N/m per kg) a ground impact pushed the hull deep enough to fall through the terrain, and the light damping
# threw it back up. Stock jets and airliners: ~1000-3700 N/m per kg, damping ~0.8 % of K (737, Concorde, Learjet).
HULL_K = 1800.0 * (TOTAL + FUEL)
for o in list(dyn.children):
    if o.type == 'collisionhull':
        if o.name in col:
            setv(o, 'Geometry', col[o.name])
            k_h = HULL_K * (0.1 if 'Stabilator' in o.name else 1.0)     # the donor's stabilator ratio
            setv(o, 'K', k_h)
            setv(o, 'D', 0.008 * k_h)
        else:
            dyn.children.remove(o)
cams = {'CameraFollow': ([-24.0, 0.0, 3.6], [1.0, 0.0, 0.0]),
        'CameraPilot': (EYE, [1.0, 0.0, -0.05]),
        'CameraPilotSideView': ([EYE[0] + 0.7, -0.45, EYE[2] + 0.2], [-1.0, 0.5, -0.4]),
        'CameraCockpitOutside': ([2.0, 4.0, 2.0], [0.6, -0.8, -0.2]),
        'CameraGearView': ([-5.0, 0.0, -1.0], [1.0, 0.0, 0.0]),
        'CameraStabilizer': ([-5.0, 0.0, 3.6], [0.95, 0.0, -0.25]),
        'CameraLeftFuselageView': ([-1.5, 6.5, 0.6], [0.9, -1.0, -0.1]),
        'CameraRightFuselageView': ([-1.5, -6.5, 0.6], [0.9, 1.0, -0.1])}
for n, (r0, d) in cams.items():
    setv(D[n], 'R0', r0)
    if D[n].find('Direction') is not None:
        setv(D[n], 'Direction', d)
setv(D['Telemetry'], 'LookAtPosition', [2.0, 0.0, 0.6])
for o in dyn.children:
    if o.type in ('pitot_tube', 'static_pressure_sensor', 'angle_of_attack_sensor', 'temperature_sensor') and o.find('R0'):
        setv(o, 'R0', [10.8, 0.0, 0.0])

# ---------------------------------------------------------------------------------------------- new dynamic signals
# nozzles (F119 2D nozzle): open at idle, closing towards full dry thrust, opening again with afterburner
for side, eng in (('Left', 'Engine1'), ('Right', 'Engine2')):
    obj(dyn, 'linear_interpolation', 'Nozzle%sDry' % side, anchor, Input='%sN2.Output' % eng,
        Map=' (0.0 0.3) (0.65 0.3) (1.0 0.0) ')      # 0.75 at idle (Su-35 schedule) gaped open: see-through gaps
    obj(dyn, 'mixlinear', 'Nozzle%sMix' % side, anchor, Input0='Nozzle%sDry.Output' % side,
        Input1='%sAfterburner.Output' % eng, Weight0=1.0, Weight1=0.5, Offset=0.0)
    obj(dyn, 'linear_interpolation', 'Nozzle%sTarget' % side, anchor, Input='Nozzle%sMix.Output' % side,
        Map=' (0.0 0.0) (1.0 1.0) ')
    obj(dyn, 'servoclassic', 'Nozzle%s' % side, anchor, Input='Nozzle%sTarget.Output' % side, Speed=0.6, P1=1.0)
# F/A-18 habits the F-22 does not have / cannot meet:
# - rudder toe-in on the ground: replaced by the real thrust vectoring (tvc_f22.py; without either, test 6, the rotation
#   came at ~200 kt)
# - 7.5 g limit of the Hornet's control laws: the F-22 pulls 9 g
setv(D['FlightController'], 'MaximumAcceleration', 9.0 * 9.81)
# - flap moment and drag: the Hornet's airfoil values. Tests 9/10 (nose drop on the approach, adverse yaw when banking)
#   had been met with CmFlap1 / 2.4 and CdFlap2 / 2 - both came from the flaperons summing the drooped aileron on top
#   of the flap (~60 deg), fixed at the source above
# - fins: from the model's exposed outline 5.2 m2 each against ~8.3 m2 on the real F-22 (vertical tail volume ~30 %
#   below the Hornet's relative to the wing) - fin lift slope x 1.5
setv(D['AirfoilVerticalStabilizer'], 'ClAlpha1', 6.28 * 1.5)
# - throttle floor at the Hornet's supersonic limit: above about M1.2 its logic holds the engines at full dry thrust (0.78) until back
#   below it, the throttle at 0% did nothing at M2.04 (user, 2026-10-30): the F/A-18's engine limit, nothing known of the kind on the F119
setv(D['MinimumThrustInput'], 'Weight0', 0.0)
# ... and M1.5-1.6 on dry thrust had been flown on that floor: 0.78 + the flight idle 0.03 = 0.81 (flight8, M1.48 at 10.25 km and still gaining), just over the
# engine's 0.8, above which jet_engine gives the Mach gain (AfterburnerMachIncrease). Below 0.8 its thrust has none, and at the MIL detent on its own the F-22 fell
# below M1.2 at 34000 ft (user, 2026-11-01). A real engine does gain with ram: at full dry the command rises to the same 0.81 through the transonic. What is lit and heard goes
# by the lever, so that this is not shown as afterburner
for lever in ('Engine1ThrustLever', 'Engine2ThrustLever'):
    det = D[lever].find('Map').children[2]
    assert det.get('NominalX').strip() == '0.65', lever
    # the top of dry power, just under the afterburner's 0.8: the lever leaves the detent into minimum afterburner. The Hornet's detent held from 0.6 to 0.75 of the travel, a
    # dead zone a key could move in with nothing happening, then a jump to 0.84 (user, 2026-11-01); 0.63 .. 0.655 lost the feel of the stop altogether (same day)
    # A zone 0.645 .. 0.73 above the stop, as the A380's, with the drawn lever kept continuous, was tried and rejected the same day: it spoilt the way into afterburner the user had accepted
    setv(det, 'Value', 0.799)
    setv(det, 'SnapMinimumX', 0.61)
    setv(det, 'SnapMaximumX', 0.66)
# RPM and thrust readings (the F/A-18's maps, 2026-11-01). jet_engine turns faster with afterburner: N2 92 % at full dry, 101 % in full afterburner. On a real engine the
# afterburner burns behind the turbine and does not speed the spool up: top rpm at full dry, the same with afterburner (rotation speed 0.91 at the detent). F119 numbers
# are not public: 100 % at full dry and N1 40 % at idle as low bypass engines of its class. THRUST on the ENG page: the value is a share, the page prints whole numbers (0)
for eng in ('Engine1', 'Engine2'):
    setv(D[eng + 'N2'], 'Map', ' (0.0 0.0) (0.65 0.65) (0.91 1.0) (1.0 1.01) ')
    setv(D[eng + 'N1'], 'Map', ' (0.0 0.0) (0.65 0.40) (0.91 1.0) (1.0 1.01) ')
    setv(D[eng + 'Thrust'], 'Map', ' (0.0 0.0) (0.65 0.0) (1.0 100.0) ')
# the game's Power gauge keeps the old curve: below 100 % at full dry, 100 % in full afterburner
obj(dyn, 'linear_interpolation', 'F22PowerGauge', D['SenderPower'], Input='Engine1.OutputRotationSpeed', Map=' (0.0 0.0) (0.65 0.54) (1.0 1.0) ')
setv(D['SenderPower'], 'Input', 'F22PowerGauge.Output')
obj(dyn, 'linear_interpolation', 'F22RamMach', D['LeftThrottleCommand'], Input='AirDataComputer.OutputMachNumber', Map=' (0.90 0.0) (1.05 0.011) ')
for eng, side in (('Engine1', 'Left'), ('Engine2', 'Right')):
    cmd = D[side + 'ThrottleCommand']
    # jet_engine is at full dry already at a command of ~0.70 (N2 readings: 0.576 -> rotation speed 0.865, 0.696 and 0.75 and 0.78 -> 0.91): nothing more happens from there to
    # 0.8. The lever is spread so that rpm and thrust go on rising all the way up to the detent, and only there reach the top
    obj(dyn, 'linear_interpolation', eng + 'LeverShaped', cmd, Input=eng + 'LeverEffective.Output', Map=' (0.0 0.0) (0.795 0.70) (0.799 0.799) (1.0 1.0) ')
    obj(dyn, 'linear_interpolation', eng + 'RamAtFullDry', cmd, Input=eng + 'LeverEffective.Output', Map=' (0.795 0.0) (0.799 1.0) ')
    obj(dyn, 'product', eng + 'Ram', cmd, Inputs=' F22RamMach.Output %sRamAtFullDry.Output ' % eng)
    obj(dyn, 'mixlinear', eng + 'LeverWithRam', cmd, Input0=eng + 'LeverShaped.Output', Input1=eng + 'Ram.Output', Weight0=1.0, Weight1=1.0)
    obj(dyn, 'minimum', eng + 'LeverLimited', cmd, Inputs=' %sLeverWithRam.Output 1.0 ' % eng)
    setv(cmd, 'Inputs', ' %sLeverLimited.Output MinimumThrustInput.Output ' % eng)
    # ... and its fuel. At 0.81 the engine bills that bit of thrust at the afterburner's rate: 26800 pph each at M1.54, 34570 ft (user's FPAS, 2026-11-01), 53600 pph on an estimated
    # 85 kN = TSFC ~2.8 by the engine's own numbers. This is meant as dry thrust: TSFC ~1.1 (dry engines burn more with Mach; the F119's figure is not public) = 10450 pph each
    obj(dyn, 'linear', eng + 'NotLit', D[eng + 'FuelFlow'], Input=eng + 'AfterburnerSetOn.Output', Scaling=-1.0, Offset=1.0)
    obj(dyn, 'product', eng + 'RamUnlit', D[eng + 'FuelFlow'], Inputs=' %sRam.Output %sNotLit.Output ' % (eng, eng))
    obj(dyn, 'linear', eng + 'FlowFactor', D[eng + 'FuelFlow'], Input=eng + 'RamUnlit.Output', Scaling=-0.61 / 0.011, Offset=1.0)
    setv(D[eng + 'FuelFlow'], 'Inputs', ' %sBurningFade.Output %s.OutputFuelFlow %sFlowFactor.Output ' % (eng, eng, eng))
    obj(dyn, 'product', eng + 'AfterburnerLit', D[eng + 'Afterburner'], Inputs=' %s.OutputAfterburner %sAfterburnerSetOn.Output ' % (eng, eng))
    setv(D[eng + 'Afterburner'], 'Input', eng + 'AfterburnerLit.Output')
# Autothrottle (our own: the Hornet's AutoThrottleButton only sends a message, what it does is not in the configs; F-22 figures are not public). While it is on the engines follow its virtual lever
# in place of the pilot's, up to full dry thrust: afterburner stays the pilot's. Moving the real lever takes it off, the engines go back to where the lever is. Gear up it holds the speed caught when
# switched on: Mach from M0.7, else calibrated airspeed, the arrows of the SYS page step them, the ICP keypad enters them. Gear down it holds angle of attack 8.5 deg, our choice (the Hornet's approach mode is 8.1).
# The law works on acceleration, InertialReferenceSystem.OutputAccelerationV (the Hornet's excess energy cue reads it the same way): speed error -> acceleration wanted, at most 1.5 m/s2, and
# the integral closes on that. On a 1-axis model of the F-22 at sea level and 11 km the overshoot was < 3 m/s for a 15-25 m/s step; a plain PI on the speed error overshot by 17 m/s (windup)
at_anchor = D['LeftThrottleCommand']
for key, src in (('Cas', 'AirDataComputer.OutputCalibratedAirspeed'), ('Mach', 'AirDataComputer.OutputMachNumber')):
    obj(dyn, 'variable', 'F22At%sTarget' % key, at_anchor, Value='0.0')
    obj(dyn, 'event_value', 'F22AtCapture' + key, at_anchor, Input=src, Events=' F22At%sTarget.Set ' % key)
# the arrows' step (user 2026-11-06: a fixed 10 kt / M0.05 was too coarse or the keypad was needed): the STEP key of
# the SYS page cycles 1 / 5 / 10 / 50 kt and M0.01 / 0.05 / 0.10 / 0.20, from 10 kt / M0.10 (the first fixed step was
# 10 kt / M0.05; one press of 5 kt and M0.01 was too slow then, user 2026-11-01). Exact values: the ICP keypad.
obj(dyn, 'variable', 'F22AtStepIndex', at_anchor, Value='2.0')
obj(dyn, 'linear_interpolation', 'F22AtStepNext', at_anchor, Input='F22AtStepIndex.Output', Map=' (0.0 1.0) (1.0 2.0) (2.0 3.0) (2.5 3.0) (3.0 0.0) ')
obj(dyn, 'event_value', 'F22AtStepCycle', at_anchor, Input='F22AtStepNext.Output', Events=' F22AtStepIndex.Set ')
obj(dyn, 'linear_interpolation', 'F22AtStepCas', at_anchor, Input='F22AtStepIndex.Output', Map=' (0.0 0.5144) (1.0 2.572) (2.0 5.144) (3.0 25.72) ')
obj(dyn, 'linear_interpolation', 'F22AtStepMach', at_anchor, Input='F22AtStepIndex.Output', Map=' (0.0 0.01) (1.0 0.05) (2.0 0.10) (3.0 0.20) ')
for key in ('Cas', 'Mach'):
    for way, sign in (('Up', 1.0), ('Down', -1.0)):
        obj(dyn, 'mixlinear', 'F22At%s%sValue' % (key, way), at_anchor, Input0='F22At%sTarget.Output' % key, Input1='F22AtStep%s.Output' % key,
            Weight0=1.0, Weight1=sign)
        obj(dyn, 'event_value', 'F22At%s%s' % (key, way), at_anchor, Input='F22At%s%sValue.Output' % (key, way), Events=' F22At%sTarget.Set ' % key)
    # (both step, only the one in use counts)
for way in ('Up', 'Down'):
    obj(dyn, 'event_value', 'F22AtStep' + way, at_anchor, Input='1.0', Events=' F22AtCas%s.Trigger F22AtMach%s.Trigger ' % (way, way))
obj(dyn, 'logic_greater', 'F22AtMachNow', at_anchor, Input0='AirDataComputer.OutputMachNumber', Input1='0.7')
obj(dyn, 'variable', 'F22AtUseMach', at_anchor, Value='0.0')
obj(dyn, 'event_value', 'F22AtCaptureUseMach', at_anchor, Input='F22AtMachNow.Output', Events=' F22AtUseMach.Set ')
obj(dyn, 'maximum', 'F22AtLeverMax', at_anchor, Inputs=' Engine1ThrustLever.Output Engine2ThrustLever.Output ')
obj(dyn, 'clamp', 'F22AtLeverDry', at_anchor, Input='F22AtLeverMax.Output', Range=('tmvector2d', ' 0.0 0.799 '))
obj(dyn, 'integral_clamped', 'F22AtIntegral', at_anchor, Input='F22AtToIntegral.Output', Range=' 0.0 0.799 ', Value=0.0)
obj(dyn, 'event_value', 'F22AtCaptureIntegral', at_anchor, Input='F22AtLeverDry.Output', Events=' F22AtIntegral.Set ')
capture = ['F22AtCaptureCas', 'F22AtCaptureMach', 'F22AtCaptureUseMach', 'F22AtCaptureIntegral']
for k in (1, 2):
    obj(dyn, 'variable', 'F22AtLever%dCaught' % k, at_anchor, Value='0.0')
    obj(dyn, 'event_value', 'F22AtCaptureLever%d' % k, at_anchor, Input='Engine%dThrustLever.Output' % k, Events=' F22AtLever%dCaught.Set ' % k)
    capture.append('F22AtCaptureLever%d' % k)
    obj(dyn, 'mixlinear', 'F22AtLever%dMoved' % k, at_anchor, Input0='Engine%dThrustLever.Output' % k, Input1='F22AtLever%dCaught.Output' % k, Weight0=1.0, Weight1=-1.0)
    obj(dyn, 'linear_interpolation', 'F22AtLever%dAway' % k, at_anchor, Input='F22AtLever%dMoved.Output' % k, Map=' (-0.03 1.0) (-0.0299 0.0) (0.0299 0.0) (0.03 1.0) ')
obj(dyn, 'variable', 'F22AtOn', at_anchor, Value='0.0')
obj(dyn, 'logic_invert', 'F22AtOnNot', at_anchor, Input='F22AtOn.Output')
obj(dyn, 'event_value', 'F22AtToggle', at_anchor, Input='F22AtOnNot.Output', Events=' F22AtOn.Set ')
obj(dyn, 'event_value', 'F22AtPress', at_anchor, Input='1.0', Events=' %s F22AtToggle.Trigger ' % ' '.join(c + '.Trigger' for c in capture))
obj(dyn, 'event_value', 'F22AtOff', at_anchor, Input='0.0', Events=' F22AtOn.Set ')
setv(D['AutoThrottleButton'], 'Events', D['AutoThrottleButton'].get('Events') + 'F22AtPress.Trigger ')
obj(dyn, 'logic_or', 'F22AtAfterburner', at_anchor, Inputs=' Engine1AfterburnerSetOn.Output Engine2AfterburnerSetOn.Output ')
obj(dyn, 'logic_or', 'F22AtCancel', at_anchor, Inputs=' F22AtLever1Away.Output F22AtLever2Away.Output F22AtAfterburner.Output OnGroundSensor.Output ')
obj(dyn, 'event_edge_rising', 'F22AtCancelled', at_anchor, Input='F22AtCancel.Output', Events=' F22AtOff.Trigger ', Value=1.0, Threshold=0.5)
obj(dyn, 'logic_invert', 'F22AtNoAfterburner', at_anchor, Input='F22AtAfterburner.Output')
obj(dyn, 'logic_invert', 'F22AtAirborne', at_anchor, Input='OnGroundSensor.Output')
obj(dyn, 'logic_and', 'F22AtActive', at_anchor, Inputs=' F22AtOn.Output F22AtNoAfterburner.Output F22AtAirborne.Output ')
# 0 calibrated airspeed, 1 Mach, 2 angle of attack
obj(dyn, 'multiplexer', 'F22AtMode', at_anchor, InputSelect='AnyGearDown.Output', Inputs=' F22AtUseMach.Output 2.0 ')
obj(dyn, 'mixlinear', 'F22AtCasError', at_anchor, Input0='F22AtCasTarget.Output', Input1='AirDataComputer.OutputCalibratedAirspeed', Weight0=1.0, Weight1=-1.0)
obj(dyn, 'mixlinear', 'F22AtMachError', at_anchor, Input0='F22AtMachTarget.Output', Input1='AirDataComputer.OutputMachNumber', Weight0=295.0, Weight1=-295.0)
# 1 deg of angle of attack ~ 4 m/s at the approach speed (lift: dV / V = -dAoA / (2 AoA))
obj(dyn, 'linear', 'F22AtAoaError', at_anchor, Input='PitotTube.AngleOfAttack', Scaling=229.0, Offset=-229.0 * 0.1484)
obj(dyn, 'multiplexer', 'F22AtError', at_anchor, InputSelect='F22AtMode.Output', Inputs=' F22AtCasError.Output F22AtMachError.Output F22AtAoaError.Output ')
obj(dyn, 'linear', 'F22AtAccelRaw', at_anchor, Input='F22AtError.Output', Scaling=0.15)
obj(dyn, 'clamp', 'F22AtAccelWanted', at_anchor, Input='F22AtAccelRaw.Output', Range=('tmvector2d', ' -1.5 1.5 '))
obj(dyn, 'mixlinear', 'F22AtToIntegral', at_anchor, Input0='F22AtAccelWanted.Output', Input1='InertialReferenceSystem.OutputAccelerationV', Weight0=0.05, Weight1=-0.05)
obj(dyn, 'mixlinear', 'F22AtProportional', at_anchor, Input0='F22AtAccelWanted.Output', Input1='InertialReferenceSystem.OutputAccelerationV', Weight0=0.1, Weight1=-0.1)
obj(dyn, 'mixlinear', 'F22AtRaw', at_anchor, Input0='F22AtIntegral.Output', Input1='F22AtProportional.Output', Weight0=1.0, Weight1=1.0)
obj(dyn, 'clamp', 'F22AtRawDry', at_anchor, Input='F22AtRaw.Output', Range=('tmvector2d', ' 0.0 0.799 '))
obj(dyn, 'multiplexer', 'F22AtDemand', at_anchor, InputSelect='F22AtActive.Output', Inputs=' F22AtLeverDry.Output F22AtRawDry.Output ')
obj(dyn, 'servoclassic', 'F22AtLever', at_anchor, Input='F22AtDemand.Output', Speed=0.5, P0=0.0, P1=1.0, P2=0.0, P3=0.0, Position=0.0)
# the drawn levers go with it: 0.799 is the stop, 0.65 of the travel
obj(dyn, 'linear_interpolation', 'F22AtLeverDrawn', at_anchor, Input='F22AtLever.Output', Map=' (0.0 0.0) (0.799 0.65) ')
for eng in ('Engine1', 'Engine2'):
    obj(dyn, 'multiplexer', eng + 'LeverEffective', at_anchor, InputSelect='F22AtActive.Output', Inputs=' %sThrustLever.Output F22AtLever.Output ' % eng)
    obj(dyn, 'multiplexer', eng + 'LeverDrawn', D[eng + 'ThrustLeverPosition'], InputSelect='F22AtActive.Output', Inputs=' %sThrustLever.OutputLever F22AtLeverDrawn.Output ' % eng)
    setv(D[eng + 'ThrustLeverPosition'], 'Input', eng + 'LeverDrawn.Output')
# - nose wheel steering only with the nose strut compressed (joint > -0.05 m); the lightly loaded F-22 nose leg
#   stays almost fully extended (-NOSE_EXT) on the ground, so steering never engaged
setv(D['NoseGearCompressed'], 'Input1', -(NOSE_EXT - 0.02))
# - nose wheel steering + the aircraft's bank angle (clamped 0.14 rad, added after the steering range): on a runway
#   with ~1 deg of cross slope the nose wheel steered downhill all the way - flight 11: rest bank -1.5 deg / +0.8 deg on
#   the two runway directions, heading drifting left 1.5 deg/s / right 0.9 deg/s on the roll with the pedals neutral.
#   Unseen while the stiff nose leg never compressed (steering off); the F-22 has no such coupling
setv(D['SteeringEnabledWithStabilization'], 'Weight1', 0.0)
# - rudder trim: with the wheel brakes on Shift+Space the rudder keys Q/E become Shift+Q/E (the game's rudder trim) on
#   the roll-out - the fins stayed deflected left and the aircraft pulled aside. So the controller takes the trim from
#   the cockpit's YAW TRIM knob only (left console, ac K_YawTrim), its own message, not the game's rudder trim keys
#   (user 2026-11-05: the knob turned but did nothing - the input was zeroed). As the Hornet's: the trim offsets the
#   rudder command inside the flight controller - both rudders move, the pedals stay. 41 positions: 20 clicks a side.
obj(dyn, 'input_default', 'F22YawTrim', D['FlightController'], Message='Controls.F22YawTrim', Positions=('uint', '41'),
    Range=' -1.0 1.0 ', Speed=0.1)
setv(D['FlightController'], 'InputRudderTrim', 'F22YawTrim.Output')
# - AC bus tie only with the parking brake released: the Hornet's left bus takes ground power while parked, the F-22
#   cockpit has no ground power panel - on a cold start the left DDI and the PMFD (left bus) stayed dark until the brake
#   was released or the left generator came on
setv(D['ACBusTieDesired'], 'Inputs', ' BusTieSwitch.Output BatterySwitchOn.Output ACBusTieDesired0.Output ')
# - BATT: two positions, ON / OFF, as the F-22's switch. The Hornet's is ON (1) / OFF (0) / ORIDE (-1, the battery forced
#   onto the essential bus); its click volume steps, and the F-22 switch draws 0 and -1 alike as OFF - two steps down put
#   it in ORIDE and the UFDs, gear lamps and ICAWS stayed lit with BATT "off" after a shutdown (user 2026-11-15)
setv(D['BatteryOverrideSwitch'], 'Range', ' 0.0 1.0 ')

# ---------------------------------------------------------------------------------------------- Hornet carrier gear out
# The F-22 is land based: no catapult launch bar, no wing fold, no refuelling probe (a boom receptacle). Their
# F/A-18 dynamics go; where the wing fold gated the controls ("wings locked" for the ailerons, outer slats and the
# full-thrust check) it now always reads locked - with the Hornet's logic an unlocked wing switched the ailerons
# off. (The arresting hook stays: the F-22 has one for runway cables.) The launch bar's 20 kg go to the fuselage.
NO_F22 = re.compile(r'^(Joint|Sender)?(LaunchBar|Holdback|WingFold|FuelProbe)|^GearRetractedResetLaunchBar$|'
                    r'^CASCautionWingsUnlocked$')
gone = [o for o in dyn.children if NO_F22.search(o.name)]
for o in gone:
    if o.type == 'rigidbody':
        setv(D['Fuselage'], 'Mass', float(D['Fuselage'].get('Mass')) + float(o.get('Mass')))
dyn.children = [o for o in dyn.children if not NO_F22.search(o.name)]
for o in gone:
    D.pop(o.name, None)
setv(D['CAS'], 'Messages', ' ' + ' '.join(m for m in D['CAS'].get('Messages').split() if not NO_F22.search(m)) + ' ')
for o in dyn.children:
    for c in o.walk():
        if c.leaf and c is not o and c.value and 'WingFold' in c.value:
            c.value = c.value.replace('WingFoldLocked.Output', '1.0').replace('WingFoldUnlocked.Output', '0.0')
gone_names = {o.name for o in gone}
left = [o.name for o in dyn.children for c in o.walk() if c.leaf and c is not o and c.value and
        gone_names & {t.split('.')[0] for t in re.findall(r'[A-Za-z_][A-Za-z0-9_.]*', c.value)}]
assert not left, left
print('removed %d F/A-18 carrier / wing fold / probe objects' % len(gone))

# ---------------------------------------------------------------------------------------------- F-22 screens: dynamics
# Lower SMFD: a fourth F/A-18 DDI - the right DDI's dynamics (page, menu, bezel buttons, brightness) cloned under
# LowerMFD / DDILower, without the 'same page as the left DDI' resets of the right one
LOWER = [('RightMFD', 'LowerMFD'), ('DDIRight', 'DDILower'), ('RightDDI', 'LowerDDI')]
LOWER_PAT = re.compile('|'.join(a for a, _ in LOWER))


def lower_name(s):
    for a, b in LOWER:
        s = s.replace(a, b)
    return s


def clone_lower(o):
    c = o.clone()
    c.name = lower_name(c.name)
    for x in c.walk():
        if x.leaf and x is not c and x.value:
            x.value = lower_name(x.value)
    return c


right_chain = [o for o in dyn.children if LOWER_PAT.search(o.name)]
lower_chain = [clone_lower(o) for o in right_chain]
i_ = dyn.children.index(right_chain[-1]) + 1
dyn.children[i_:i_] = lower_chain
D.update({o.name: o for o in lower_chain})
setv(D['LeftAndLowerMFDPageAreTheSame'], 'Input0', '-1.0')
setv(D['SetLowerMFDPageAndResetLeftIfNeeded'], 'Events', ' LowerMFDPage.Set ')
print('lower SMFD: %d F/A-18 right DDI dynamics objects cloned (%s)'
      % (len(lower_chain), ', '.join(sorted({o.type for o in lower_chain}))[:200]))

# One menu on every MFD (the Hornet's TAC / SUPT pair, combat pages out): FUEL, FPAS, UFC backup, HSI, ADI, CHECKLIST,
# ENG, FCS, HUD repeater, SA map - built from each display's own menu elements (their events select that display's
# pages); the menu label no longer flips to the tactical menu
for prefix in ('LeftMFD', 'RightMFD', 'MPCD', 'LowerMFD'):
    tac, sup = D[prefix + 'TacticalMenuPage'], D[prefix + 'SupportMenuPage']
    tac_el = {e.name: e for e in tac.find('Elements').children}
    els = [e.clone() for e in sup.find('Elements').children]
    assert [e.name for e in els][17:20:2] == ['BuiltInTestLabel', 'MissionInitializationLabel'], prefix
    els[17], els[19] = tac_el['HUDPageLink'].clone(), tac_el['SituationAwarenessPageLink'].clone()
    next(e for e in els if e.name == 'SupportMenuLabel').set('Events', ' DEV0.Trigger ')
    for page in (tac, sup):
        page.find('Elements').children = [e.clone() for e in els]
setv(D['SupportMenuLabel'], 'Input', 'MENU')
# BAY (stage 6): a menu link on every MFD's menu (left side, top) to page 10, the Hornet's stores page, which becomes
# the F-22 BAY page: its left buttons toggle the bays (boxed while commanded open), MENU and HUD / SA stay
D['F22BayMenuLabel'] = obj(dyn, 'constant_text', 'F22BayMenuLabel', D[prefix + 'SupportMenuPage'], Input='BAY')


def _menu_el(name, text, events, inp=None):
    e = tmd.Node('text_menu_basic_page_element', name, leaf=False)
    e.children.append(tmd.Node('string8', 'InputText', text))
    if inp:
        e.children.append(tmd.Node('string8', 'Input', inp))
    e.children.append(tmd.Node('string8', 'Events', ' %s ' % events))
    return e


for bay, short in (('Left', 'LFT'), ('Center', 'CTR'), ('Right', 'RGT'), ('All', 'ALL')):
    D['F22Bay%sMenuLabel' % bay] = obj(dyn, 'constant_text', 'F22Bay%sMenuLabel' % bay, D['F22BayMenuLabel'],
                                       Input=short)
for prefix in ('LeftMFD', 'RightMFD', 'MPCD', 'LowerMFD'):
    # MENU of the BAY page: the Hornet stores page's own MENU button (back to the menu). Copied from the support menu
    # page, it was that page's MENU label, whose events are emptied above (the label must not flip menus) - the BAY
    # page could not be left
    stores_menu = D[prefix + 'StoresMenuPage'].find('Elements').children[2].clone()
    assert stores_menu.name == 'MenuLabel', (prefix, stores_menu.name)
    link = _menu_el('F22BayPageLink', 'F22BayMenuLabel.Output', 'Set%sStores.Trigger' % prefix)
    for page in (D[prefix + 'TacticalMenuPage'], D[prefix + 'SupportMenuPage']):
        els = page.find('Elements').children
        assert els[5].name == 'Blank', (prefix, els[5].name)
        els[5] = link.clone()
    els = [e.clone() for e in D[prefix + 'SupportMenuPage'].find('Elements').children]
    for k, bay in enumerate(('Left', 'Center', 'Right')):
        els[5 + k] = _menu_el('F22Bay%sButton' % bay, 'F22Bay%sMenuLabel.Output' % bay, 'F22Bay%sToggle.Trigger' % bay,
                              'F22Bay%sCommand.Output' % bay)
    els[8] = _menu_el('F22BayAllButton', 'F22BayAllMenuLabel.Output', 'F22BayAllToggle.Trigger')
    for k in range(len(els)):                         # a page of its own: the bay buttons and MENU (2) only
        if k != 2 and not 5 <= k <= 8:
            els[k] = tmd.Node('text_menu_basic_page_element', 'Blank', leaf=False)
    els[2] = stores_menu
    D[prefix + 'StoresMenuPage'].find('Elements').children = els
# Page buttons. The Hornet's own events on these are its dummy DEV0 (the stock aircraft does nothing with them either), so a label with no function goes
# (2026-11-01, user's list; real meaning in brackets): ADI INS / STBY (attitude source: the game has no INS failure to switch away from), FUEL FLBIT (built in
# test), FCS BLIN / AOA (BIT logic inspection, AOA cross check), ENG RECORD (data recorder), most of HSI and SA (sensors, ACLS, waypoint sequencing, datalink).
# FPAS and UFC BU: empty display_f18 stubs in the stock aircraft as well (the Hornet's fuel advisory and backup up-front panel were never built). UFC BU is out of
# the menu; FPAS is built here, F22PerfPage in the graphics section.
# In return: BINGO can be set from the FUEL page (the Hornet's IFEI buttons are not in this cockpit), ADI, HSI and SA link to each other.
def _keep(page, keep, extra=None):
    els = page.find('Elements').children
    for k in range(len(els)):
        if k not in keep:
            els[k] = tmd.Node('text_menu_basic_page_element', 'Blank', leaf=False)
    for k, e in (extra or {}).items():
        while len(els) <= k:        # short lists on the pages with few buttons
            els.append(tmd.Node('text_menu_basic_page_element', 'Blank', leaf=False))
        els[k] = e


for name, step in (('F22BingoUp', 45.359237), ('F22BingoDown', -45.359237)):  # 100 lb a press (user 2026-11-06: 250 kg = 551 lb was too coarse; the step is in kg)
    obj(dyn, 'event_value', name, D['F22BayMenuLabel'], Input='%.1f' % step, Events=' BingoFuel.Step ')
for prefix in ('LeftMFD', 'RightMFD', 'MPCD', 'LowerMFD'):
    menu_els = {e.name: e for e in D[prefix + 'SupportMenuPage'].find('Elements').children}
    hsi, sa = menu_els['HorizontalSituationPageLink'], menu_els['SituationAwarenessPageLink']
    _keep(D[prefix + 'ADIMenuPage'], {2}, {1: hsi.clone()})
    _keep(D[prefix + 'FuelMenuPage'], {2}, {11: _menu_el('F22BingoUpButton', 'ArrowUpLarge.Output', 'F22BingoUp.Trigger'),
                                            12: _menu_el('F22BingoDownButton', 'ArrowDownLarge.Output', 'F22BingoDown.Trigger')})
    _keep(D[prefix + 'FlightControlMenuPage'], {2})
    _keep(D[prefix + 'EngineMenuPage'], {2})
    _keep(D[prefix + 'HSIMenuPage'], {2, 5, 6, 13, 17}, {1: sa.clone()})
    _keep(D[prefix + 'SituationAwarenessMenuPage'], {2, 17}, {1: hsi.clone()})
    for page in (D[prefix + 'TacticalMenuPage'], D[prefix + 'SupportMenuPage']):
        els = page.find('Elements').children
        assert els[4].name == 'UFCBUPageLink', prefix
        els[4] = tmd.Node('text_menu_basic_page_element', 'Blank', leaf=False)
    _keep(D[prefix + 'FlightPerformanceAdvisorySystemMenuPage'], {2})
# SYS: the empty BIT page becomes the page of the vector, the FCS mode and the automatics (F22TvcPage in the graphics section), with the Hornet's BIT buttons gone. (The Hornet's RADAR page,
# tried in the menu on 2026-11-01, is out again: no targets are drawn, a picture only with the FLIR on)
D['F22TvcMenuLabel'] = obj(dyn, 'constant_text', 'F22TvcMenuLabel', D['F22BayMenuLabel'], Input='SYS')
# the A/T step key's text is the step itself: 1 / 5 / 10 / 50 kt, or .01 .. .20 when the A/T holds Mach
obj(dyn, 'mixlinear', 'F22AtStepTextIndex', D['F22BayMenuLabel'], Input0='F22AtStepIndex.Output', Input1='F22AtUseMach.Output', Weight0=1.0, Weight1=4.0)
for k_, t_ in enumerate(('1', '5', '10', '50', '.01', '.05', '.10', '.20')):
    obj(dyn, 'constant_text', 'F22AtStepLabel%d' % k_, D['F22BayMenuLabel'], Input=t_)
D['F22AtStepText'] = obj(dyn, 'multiplexer_text', 'F22AtStepText', D['F22BayMenuLabel'], InputSelect='F22AtStepTextIndex.Output',
                         Inputs=' %s ' % ' '.join('F22AtStepLabel%d.Output' % k_ for k_ in range(8)))
for key, text in (('Direct', 'DIR'), ('Vector', 'VEC'), ('Gcas', 'GCS'), ('At', 'A/T')):
    D['F22%sMenuLabel' % key] = obj(dyn, 'constant_text', 'F22%sMenuLabel' % key, D['F22BayMenuLabel'], Input=text)
for prefix in ('LeftMFD', 'RightMFD', 'MPCD', 'LowerMFD'):
    bit_event = {'MPCD': 'SetMPCDMFDBuiltInTest'}.get(prefix, 'Set%sBuiltInTest' % prefix)
    for page in (D[prefix + 'TacticalMenuPage'], D[prefix + 'SupportMenuPage']):
        els = page.find('Elements').children
        els[4] = _menu_el('F22TvcPageLink', 'F22TvcMenuLabel.Output', bit_event + '.Trigger')
    _keep(D[prefix + 'BuiltInTestMenuPage'], {2}, {5: _menu_el('F22DirectButton', 'F22DirectMenuLabel.Output', 'F22DirectToggle.Trigger', 'F22DirectMode.Output'),
                                                   6: _menu_el('F22VectorButton', 'F22VectorMenuLabel.Output', 'F22VectorToggle.Trigger', 'F22VectorOn.Output'),
                                                   # (7, VOX: gone - the RADIO VOL knob's OFF mutes the voice, user
                                                   # 2026-11-07: one control, not three)
                                                   8: _menu_el('F22GcasButton', 'F22GcasMenuLabel.Output', 'F22GcasToggle.Trigger', 'F22GcasArmed.Output'),
                                                   # ALT GR: the alternate gear extension (failures_f22 gear_dynamics;
                                                   # the DCS cockpit has no handle for it) - lit once pulled, until RST
                                                   9: _menu_el('F22AltGearButton', 'F22AltGearMenuLabel.Output', 'F22AltGearPull.Trigger', 'F22AltGear.Output'),
                                                   # the A/T on the right column (user 2026-11-06): on / off, up, the
                                                   # step (drawn across on the page, F22TvcPage: a side key's label
                                                   # reads downwards), down
                                                   # (A/T and the step are drawn on the page, across, level with
                                                   # their keys - F22TvcPage; the arrows are the menu's own symbols
                                                   # as on the Hornet's radar page: display_text printed 'arrow_up'
                                                   # as 'a', user 2026-11-07)
                                                   10: _menu_el('F22AtButton', 'BlankLabel.Output', 'F22AtPress.Trigger'),
                                                   11: _menu_el('F22AtUpButton', 'ArrowUpSmall.Output', 'F22AtStepUp.Trigger'),
                                                   12: _menu_el('F22AtStepButton', 'BlankLabel.Output', 'F22AtStepCycle.Trigger'),
                                                   13: _menu_el('F22AtDownButton', 'ArrowDownSmall.Output', 'F22AtStepDown.Trigger')})
# CHECKLIST (user 2026-11-04): the Hornet's checklist is a drawn display class (display_f18_checklist, its takeoff /
# landing checks of the Hornet) - replaced by this mod's own procedures, four lists picked by the left bezel buttons
D['F22ChecklistIndex'] = obj(dyn, 'variable', 'F22ChecklistIndex', D['F22BayMenuLabel'], Value='0.0')
CHECKLIST_NAMES = ('START', 'T/O', 'LAND', 'SHUT')
for k, text in enumerate(CHECKLIST_NAMES):
    obj(dyn, 'event_value', 'F22ChecklistSet%d' % k, D['F22BayMenuLabel'], Input='%.1f' % k, Events=' F22ChecklistIndex.Set ')
    obj(dyn, 'logic_equal', 'F22ChecklistIs%d' % k, D['F22BayMenuLabel'], Input0='F22ChecklistIndex.Output', Input1='%.1f' % k)
    D['F22Checklist%dMenuLabel' % k] = obj(dyn, 'constant_text', 'F22Checklist%dMenuLabel' % k, D['F22BayMenuLabel'], Input=text)
for prefix in ('LeftMFD', 'RightMFD', 'MPCD', 'LowerMFD'):
    _keep(D[prefix + 'ChecklistMenuPage'], {2}, {5 + k: _menu_el('F22Checklist%dButton' % k, 'F22Checklist%dMenuLabel.Output' % k,
                                                                 'F22ChecklistSet%d.Trigger' % k, 'F22ChecklistIs%d.Output' % k)
                                                 for k in range(len(CHECKLIST_NAMES))})
# (moving map on the other MFDs: tried 2026-10-22, removed - the game draws one map instance only (every stock aircraft
# has exactly one texture_animation_map_display; our copies drew nothing, MODE only darkened the page), and the one
# map is sized for the PMFD (432 px): on the 390 px MFDs it would spill over and stand 10 % off the HSI symbols)
# start pages: engines left, fuel right, the map on the PMFD, flight controls below
for prefix, page in (('LeftMFD', 8), ('RightMFD', 4), ('MPCD', 2), ('LowerMFD', 9)):
    setv(D[prefix + 'Page'], 'Value', '%.1f' % page)

# ICP = the F/A-18 up-front controller: its five option lines and scratchpad on the ICP windows, its keypad on the ICP
# keys. The F-22 function keys open UFC pages - the Hornet's own (COM1 / COM2, A/P, STPT = waypoint) or F-22 pages
# added to the UFC menu (NAV: ILS, TACAN, ADF, course, heading; ALT: altitude holds; HUD: declutter, baro / radar
# altitude; OTHR: ADF2, time - not the Hornet's carrier beacon / data link; IFF has its own key). Hornet page
# numbers: 1 A/P, 2 IFF, 3 TACAN, 4 ILS, 5 D/L, 6 BCN, 9 heading, 10 course, 11 HSI time, 12 waypoint, 15 / 16 ADF1 / 2.
ufc = D['UpFrontController']
anchor = ufc


def ufc_page_event(page):
    name = 'UpFrontControllerPageTo%d' % page
    if name not in D:
        D[name] = obj(dyn, 'event_value', name, anchor, Input='%.1f' % page,
                      Events=' SetUpFrontControllerPageAndStartAutoReset.Trigger ')
    return name + '.Trigger'


def ufc_label(text):
    name = 'F22Label' + re.sub(r'[^A-Za-z0-9]', '', text) + ('Option' if text.startswith(' ') else '')
    if name not in D:
        D[name] = obj(dyn, 'constant_text', name, anchor, Input=text)
    return name + '.Output'


def ufc_page(name, options):
    """F-22 UFC page: up to five (label, events) option lines; returns the page number."""
    page = tmd.Node('text_menu_basic_page', name, leaf=False)
    els = tmd.Node('text_menu_basic_page_elements', 'Elements', leaf=False)
    for k in range(5):
        e = tmd.Node('text_menu_basic_page_element', 'Blank', leaf=False)
        if k < len(options) and options[k]:
            text, events = options[k]
            if not text.endswith('.Output'):
                text = ' ' + text            # column 0 is the Hornet's selection colon (bare 'ILS' lost its I)
            e.name = 'F22Option%d' % k
            e.children = [tmd.Node('string8', 'InputText', text if text.endswith('.Output') else ufc_label(text)),
                          tmd.Node('string8', 'Events', ' %s ' % events)]
        els.children.append(e)
    page.children.append(els)
    dyn.children.insert(dyn.children.index(ufc), page)
    D[name] = page
    pages = ufc.get('Pages').split()
    ufc.set('Pages', ' ' + ' '.join(pages + [name]) + ' ')
    return len(pages)


def hud_set(switch, value):
    name = 'F22%sTo%d' % (switch, value)
    D[name] = obj(dyn, 'event_value', name, anchor, Input='%.1f' % value, Events=' %s.Set ' % switch)
    return name + '.Trigger'


# A/T target by the keypad, as the HSEL page: OTHR, then MACH or KCAS, the digits (139 = M1.39, 450 = 450 kt), MRK. It also picks what is held, and switches the A/T on
for key, text in (('Mach', ':MACH'), ('Cas', ':KCAS')):
    obj(dyn, 'constant_text', 'F22At%sEntryLabel' % key, anchor, Input=text)
obj(dyn, 'binary_to_text', 'F22AtLineLabel', anchor, Input='F22AtActive.Output', Text0=' A/T', Text1=':A/T')
AT_MACH_PAGE = ufc_page('F22UFCPageAtMach', [('F22AtMachEntryLabel.Output', 'DEV0.Trigger')])
AT_CAS_PAGE = ufc_page('F22UFCPageAtCas', [('F22AtCasEntryLabel.Output', 'DEV0.Trigger')])
obj(dyn, 'constant_text', 'F22AltFloorEntryLabel', anchor, Input=':ALOW')
ALT_FLOOR_PAGE = ufc_page('F22UFCPageAltFloor', [('F22AltFloorEntryLabel.Output', 'DEV0.Trigger')])
assert AT_CAS_PAGE == AT_MACH_PAGE + 1 and ALT_FLOOR_PAGE == AT_CAS_PAGE + 1
enter_events = D['UpFrontEnterEvent'].get('Events').split()
enter_events += ['ScratchPad.Clear'] * (AT_MACH_PAGE - len(enter_events))
setv(D['UpFrontEnterEvent'], 'Events', ' %s F22AtEnterMach.Trigger F22AtEnterCas.Trigger F22AltFloorEnter.Trigger ' % ' '.join(enter_events))
obj(dyn, 'event_demultiplexer', 'F22AltFloorEnter', anchor, InputSelect='ScratchPadValue.OutputValid', Events=' DEV0.Trigger F22AltFloorSet.Trigger ')
obj(dyn, 'event_linear', 'F22AltFloorSetValue', anchor, Scaling=0.3048, Offset=0.0, Events=' F22AltFloor.Set ')       # feet
obj(dyn, 'event_value', 'F22AltFloorSet', anchor, Input='ScratchPadValue.Output', Events=' F22AltFloorSetValue.Trigger ScratchPad.Clear ')
for key, scale, use in (('Mach', 0.01, '1.0'), ('Cas', 0.514444, '0.0')):
    obj(dyn, 'event_demultiplexer', 'F22AtEnter' + key, anchor, InputSelect='ScratchPadValue.OutputValid', Events=' DEV0.Trigger F22AtSet%s.Trigger ' % key)
    obj(dyn, 'event_linear', 'F22AtSet%sValue' % key, anchor, Scaling=scale, Offset=0.0, Events=' F22At%sTarget.Set ' % key)
    obj(dyn, 'event_value', 'F22AtSelect' + key, anchor, Input=use, Events=' F22AtUseMach.Set ')
    obj(dyn, 'event_value', 'F22AtSet' + key, anchor, Input='ScratchPadValue.Output',
        Events=' F22AtSet%sValue.Trigger F22AtSelect%s.Trigger F22AtEngageIfOff.Trigger ScratchPad.Clear ' % (key, key))
obj(dyn, 'event_demultiplexer', 'F22AtEngageIfOff', anchor, InputSelect='F22AtOn.Output', Events=' F22AtEngage.Trigger DEV0.Trigger ')
obj(dyn, 'event_value', 'F22AtEngage', anchor, Input='1.0', Events=' F22AtCaptureIntegral.Trigger F22AtCaptureLever1.Trigger F22AtCaptureLever2.Trigger F22AtOn.Set ')
ICP_PAGES = {
    'Nav': ufc_page('F22UFCPageNav', [('ILS', ufc_page_event(4)), ('TCN', ufc_page_event(3)), ('ADF', ufc_page_event(15)),
                                      ('CRS', 'UpFrontControllerPageToSelectedCourse.Trigger'),
                                      ('HDG', 'UpFrontControllerPageToSelectedHeading.Trigger')]),
    'Altitude': ufc_page('F22UFCPageAltitude', [('UFCAutopilotBaroLabel.Output', 'FlightController.SetBaroAltitudeHold'),
                                                ('UFCAutopilotRadarLabel.Output', 'FlightController.SetRadarAltitudeHold'),
                                                ('ALOW', ufc_page_event(ALT_FLOOR_PAGE))]),
    'HUD': ufc_page('F22UFCPageHUD', [('NORM', hud_set('HUDRejectSwitch', 0)), ('REJ1', hud_set('HUDRejectSwitch', 1)),
                                      ('REJ2', hud_set('HUDRejectSwitch', 2)), ('BARO', hud_set('HUDBaroRadarSelectSwitch', 0)),
                                      ('RALT', hud_set('HUDBaroRadarSelectSwitch', 1))]),
    'Other': ufc_page('F22UFCPageOther', [('ADF2', ufc_page_event(16)), ('TIME', ufc_page_event(11)), ('F22AtLineLabel.Output', 'F22AtPress.Trigger'),
                                          ('MACH', ufc_page_event(AT_MACH_PAGE)), ('KCAS', ufc_page_event(AT_CAS_PAGE))]),
    'Steerpoint': 12,
}
for key, page in ICP_PAGES.items():
    obj(dyn, 'input_event', 'ICPKey' + key, anchor, Message='ICP.' + key, Events=' %s ' % ufc_page_event(page))
# UFD / ICP brightness: on with the right AC bus (as the right DDI), dimmed with the wheel left of the ICP (DCS
# ICP_WHEELUP / ICP_WHEELDWN), 0.5 at start as before
obj(dyn, 'input_default', 'UFDBrightnessWheel', anchor, Message='UFD.Brightness', Range=' 0.0 1.0 ',
    Positions=('uint', '21'), Value=0.5)
# (2026-11-05, user: after the fuel ran out the whole cockpit went dark at once) the two UFDs - ICAWS and the standby
# flight group - are the displays left on the battery (DC essential bus); the ICP, MFDs and HUD need AC (generators /
# APU), as the Hornet's. The F-22's exact battery loads are not public; standby + warnings on the battery is the rule
obj(dyn, 'product', 'UFDBrightnessValue', anchor, Inputs=' DCBusEssentialOn.Output UFDBrightnessWheel.Output ')
obj(dyn, 'product', 'ICPBrightnessValue', anchor, Inputs=' DDIRightOn.Output UFDBrightnessWheel.Output ')
# (HUD brightness: a full wheel of 1.6 instead of the Hornet's 1.0 changed nothing in the game (2026-10-22): the HUD
# renderer clamps at 1 - the HUD is drawn twice instead, graphics section)

# ---------------------------------------------------------------------------------------------- fuel burn
# Aerofly keeps the loaded fuel for the whole flight (the stock F/A-18 too: no burn, flies on with 0 kg). The fuel
# used is integrated from the engines' fuel flow (kg/s) and taken out of the tank values everything reads (FUEL page,
# total / internal, fuel low and bingo cautions, FPAS, UFD): fuselage transfer tanks first, then the wing tanks, the
# feed tanks last; an engine runs only while its feed tank holds fuel. The aircraft mass stays the loaded one (set by
# the simulator).
anchor = D['LeftTransferTank']
obj(dyn, 'sum', 'FuelFlowTotal', anchor, Inputs=' Engine1FuelFlow.Output Engine2FuelFlow.Output ')
obj(dyn, 'integral_clamped', 'FuelUsed', anchor, Input='FuelFlowTotal.Output', Range=' 0.0 100000.0 ', Value=0.0)
use = 'FuelUsed.Output'
for group in ('Transfer', 'Wing', 'Feed'):
    raw = {side: '%s%sFuelTank.Output' % (side, group) for side in ('Left', 'Right')}
    for side in ('Left', 'Right'):
        obj(dyn, 'mixlinear', 'FuelLeft%s%s' % (side, group), anchor, Input0=raw[side], Input1=use, Weight0=1.0,
            Weight1=-0.5)
        obj(dyn, 'maximum', 'FuelRemaining%s%s' % (side, group), anchor,
            Inputs=' FuelLeft%s%s.Output 0.0 ' % (side, group))
        setv(D['%s%sTank' % (side, group)], 'Input', 'FuelRemaining%s%s.Output' % (side, group))
    obj(dyn, 'sum', 'FuelLoaded%s' % group, anchor, Inputs=' %s %s ' % (raw['Left'], raw['Right']))
    obj(dyn, 'mixlinear', 'FuelUsedBeyond%s' % group, anchor, Input0=use, Input1='FuelLoaded%s.Output' % group,
        Weight0=1.0, Weight1=-1.0)
    obj(dyn, 'maximum', 'FuelUsedAfter%s' % group, anchor, Inputs=' FuelUsedBeyond%s.Output 0.0 ' % group)
    use = 'FuelUsedAfter%s.Output' % group
# a new fuel load set in the menu during the flight (the simulator's tank contents jump) starts the count again - the
# first test took the fuel burnt before out of a fresh 500 kg load and both engines flamed out at once
obj(dyn, 'sum', 'FuelLoaded', anchor, Inputs=' FuelLoadedTransfer.Output FuelLoadedWing.Output FuelLoadedFeed.Output ')
obj(dyn, 'servoclassic', 'FuelLoadedFollow', anchor, Input='FuelLoaded.Output', Speed=2000.0, P0=0.0, P1=1.0, P2=0.0,
    P3=0.0)
obj(dyn, 'mixlinear', 'FuelLoadStep', anchor, Input0='FuelLoaded.Output', Input1='FuelLoadedFollow.Output',
    Weight0=1.0, Weight1=-1.0)
obj(dyn, 'mixlinear', 'FuelLoadStepNegative', anchor, Input0='FuelLoadStep.Output', Input1='0.0', Weight0=-1.0,
    Weight1=0.0)
obj(dyn, 'maximum', 'FuelLoadStepSize', anchor, Inputs=' FuelLoadStep.Output FuelLoadStepNegative.Output ')
obj(dyn, 'logic_greater', 'FuelLoadChanged', anchor, Input0='FuelLoadStepSize.Output', Input1='5.0')
obj(dyn, 'event_edge_rising', 'FuelLoadChangedReset', anchor, Input='FuelLoadChanged.Output',
    Events=' FuelUsed.Reset ', Value=1.0, Threshold=0.5)
for k, side in ((1, 'Left'), (2, 'Right')):
    obj(dyn, 'logic_greater', 'Engine%dFuelFed' % k, anchor, Input0='%sFeedTank.Output' % side, Input1='0.5')
    obj(dyn, 'logic_and', 'Engine%dRunWithFuel' % k, anchor,
        Inputs=' %s Engine%dFuelFed.Output ' % (D['Engine%d' % k].get('InputRun').strip(), k))
    setv(D['Engine%d' % k], 'InputRun', 'Engine%dRunWithFuel.Output' % k)
anchor = ufc

# ---------------------------------------------------------------------------------------------- engine start, APU power
# As the F-22 (and the DCS mod's Engine_System.lua / Avionics.lua): the APU's generator powers the aircraft once it
# runs (displays up before the engine start - with the Hornet's APU, air only, they stayed dark until an engine
# generator came on), and an engine starts by itself when its throttle leaves cut-off with starter air (APU) - no
# crank switch (the F/A-18 Engines.Crank stays for keyboard use). The Hornet's ground power path becomes the APU
# generator: connected while the APU is available, cut off by the left engine generator as before.
setv(D['ExternalPowerConnected'], 'Inputs', ' APUAvailable.Output ')
setv(D['ExternalPowerModeSelectNormal'], 'Input0', '1.0')
anchor = D['Engine1StarterSetOn']
crank = {1: dict(Input0='EngineCrankSwitch.Output', Input1='0.5'), 2: dict(Input0='-0.5', Input1='EngineCrankSwitch.Output')}
for k in (1, 2):
    obj(dyn, 'logic_greater', 'Engine%dCrankSelected' % k, anchor, **crank[k])
    obj(dyn, 'logic_invert', 'Engine%dNotRunning' % k, anchor, Input='Engine%dRunning.Output' % k)
    obj(dyn, 'logic_and', 'Engine%dThrottleStart' % k, anchor,
        Inputs=' ThrustLever%dRun.Output Engine%dNotRunning.Output ' % (k, k))
    obj(dyn, 'logic_or', 'Engine%dStartRequest' % k, anchor,
        Inputs=' Engine%dCrankSelected.Output Engine%dThrottleStart.Output ' % (k, k))
    setv(D['Engine%dStarterSetOn' % k], 'Input0', 'Engine%dStartRequest.Output' % k)
    setv(D['Engine%dStarterSetOn' % k], 'Input1', '0.5')
    # generator at rated speed (400) before it is switched onto the bus at N2 0.55 (Engine%dRunning), as a generator
    # control unit closes the contactor only with voltage and frequency in limits (the Hornet's map reached rated
    # speed only at N2 0.57)
    setv(D['Engine%dGeneratorDriveRotationSpeed0' % k], 'Map', ' (0.40 0.0) (0.50 600.0) ')
# displays blink for ~0.5 s as each engine generator comes online, accepted as is (2026-10-21). Measured with the
# recorder below (DIAG_POWER): once a generator is a bus's only feed (the APU contactor or the bus tie opening) the bus
# stays below the displays' 100 V for 0.5 - 0.63 s while the generator side holds 116 V across the closed contactor -
# Aerofly's network settling, not the wiring. Tried and reverted: the APU held on 0.5 s longer (only moved the dip),
# a 1 s ride-through on the display power-on signals (still blinked, shorter).

# ---------------------------------------------------------------------------------------------- automatic flaps, trim
# The F-22 has no flap lever: the flight control system sets the flaps. With the gear handle down the takeoff /
# landing setting (the Hornet's HALF - the F-22's trailing edge goes down less than the Hornet's FULL), with it up
# the Hornet's AUTO, where the flight controller schedules leading and trailing edges with angle of attack and Mach
# itself (slow flight clean keeps them). Every Hornet consumer read FlapsSelector, now the gear handle; the pilot's
# lever (Controls.Flaps, the F key) and its clicks are gone, and with them the CHK FLAPS caution (cannot happen).
FLAP_LEVER = re.compile(r'^FlapsSelector(_Sound\d)?$')
dyn.children = [o for o in dyn.children if not FLAP_LEVER.search(o.name)]
# (the gear down by ALT GR counts as down - the alternate extension leaves the handle where it was: with it up after
# ALT GR the flaps went AUTO with the gear hanging down, user 2026-11-15)
obj(dyn, 'maximum', 'F22FlapsGearDown', D['FlapsMapping'], Inputs=' GearLever.Output F22AltGear.Output ')
D['FlapsSelector'] = obj(dyn, 'linear_interpolation', 'FlapsSelector', D['FlapsMapping'], Input='F22FlapsGearDown.Output',
                         Map=' (0.0 0.0) (1.0 0.5) ')
# Pitch trim: none - 0 always (user 2026-11-15). The F-22 has no takeoff trim (its flight control system works the
# stabilators at rotation) and needs no trimming in flight: neutral stick is 1 g. History: the Hornet's CHK TRIM wants
# 40-60 % nose up before takeoff, so the mod sent its T/O TRIM message on the ground (SenderF22AutoTakeoffTrim) - at
# any speed it also fired at the touchdown and pitched the nose up on the landing roll and at a bounce; left at takeoff
# trim after liftoff the Hornet's laws pitched up the whole flight (its trim offsets the commanded g). Without it the
# test is whether the nose still lifts at a normal speed with the aft CG (in October, with less aft CG, it did not
# before ~200 kt; make_f22 CG_AFT): if not, a rotation aid comes back in another form. User's test 2026-11-15 with the
# trim at 0 by hand: lift-off 135-140 kt clean at MIL, 122-127 in afterburner, 170 with full ferry tanks - normal, no
# aid needed. The trim starts at 0 in every flight state (the ground states had none: the Hornet's controller began at
# 50 % nose up) and the game's spawn takeoff trim is 0 (copilot.tmc); the trim keys still work if wanted. (Holding it
# at 0 by a sender of Controls.Trim, absolute, did nothing - the spawn still read 50 %: removed.)
D['FlightController'].set('PitchTrim', '0.0', 'float64')
# ... and the spawn still read 50 %, with the game's automatic trim assistance off (user 2026-11-15): the Hornet's
# flight controller trims by itself - on the ground to its takeoff trim (50 % nose up; its class holds an
# 'AutoTrimGround' state), back to 0 when the gear goes up in the air; the pilot can move it by hand meanwhile. Its own
# code, not a file setting: senders of Controls.Trim did nothing - absolute (normalized) and as trim-key steps (a
# ground trim-to-zero, removed). On the ground at 50 % it holds the stabilators ~3 deg nose up (FCS page STAB at rest)
NO_CHECK = ('CASCautionCheckFlaps', 'CASCautionCheckTrim')
setv(D['CAS'], 'Messages', ' ' + ' '.join(m for m in D['CAS'].get('Messages').split() if m not in NO_CHECK) + ' ')
# ICP rocker -> map range, the way the MFD buttons step it (StepMapRange: an event into MapRange.Step; the rocker's
# first build sent NavigationDisplayPilot.Range with a step qualifier from a push button - nothing happened)
for key, step in (('Up', 1.0), ('Down', -1.0)):
    obj(dyn, 'event_value', 'F22MapRange' + key, anchor, Input='%.1f' % step, Events=' MapRange.Step ')
    obj(dyn, 'input_event', 'ICPMapRange' + key, anchor, Message='ICP.MapRange' + key,
        Events=' F22MapRange%s.Trigger ' % key)

# ---------------------------------------------------------------------------------------------- stores, bays, tanks
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stores_f22 as S          # layout constants (numpy-free at import)
# Stage 6. Load variants (livery selector, add-ons written below): F22CombatLoad (6 AIM-120C + 2 AIM-9X in the bays)
# and F22FerryTanks (two 600 gal tanks on their wing pylons) are 0 here, 1 in their add-on's parameters.tmd - as the
# F/A-18's external tank add-ons.
obj(dyn, 'linear', 'F22CombatLoad', anchor, Input='0.0')
obj(dyn, 'linear', 'F22FerryTanks', anchor, Input='0.0')
obj(dyn, 'logic_invert', 'F22CombatHidden', anchor, Input='F22CombatLoad.Output')
# weapon bays: the BAY page of the MFDs (or a Weapons.Bay* message) toggles each bay's door command; ALL opens every
# bay if all are shut, else shuts them. Door servos 0 shut .. 1 open (the side bays swing the AIM-9 trapeze out with
# the doors, DCS arguments 600 - 602); ~1 s, on hydraulics with the battery on
BAYS = ('Center', 'Left', 'Right')
for bay in BAYS:
    obj(dyn, 'variable', 'F22Bay%sCommand' % bay, anchor, Value='0.0')
    obj(dyn, 'logic_invert', 'F22Bay%sCommandNot' % bay, anchor, Input='F22Bay%sCommand.Output' % bay)
    obj(dyn, 'event_value', 'F22Bay%sToggle' % bay, anchor, Input='F22Bay%sCommandNot.Output' % bay,
        Events=' F22Bay%sCommand.Set ' % bay)
    obj(dyn, 'input_event', 'F22Bay%sMessage' % bay, anchor, Message='Weapons.Bay%s' % bay,
        Events=' F22Bay%sToggle.Trigger ' % bay)
    obj(dyn, 'product', 'F22Bay%sDemand' % bay, anchor, Inputs=' F22Bay%sCommand.Output DCBusEssentialOn.Output ' % bay)
    obj(dyn, 'servoclassic', 'F22Bay' + bay, anchor, Input='F22Bay%sDemand.Output' % bay, Speed=1.0, P0=0.0, P1=1.0,
        P2=0.0, P3=0.0, Position=0.0)
    # page status: 0 CLSD, 1 MOVE, 2 OPEN
    obj(dyn, 'logic_greater', 'F22Bay%sUnlocked' % bay, anchor, Input0='F22Bay%s.Output' % bay, Input1='0.02')
    obj(dyn, 'logic_greater', 'F22Bay%sFullOpen' % bay, anchor, Input0='F22Bay%s.Output' % bay, Input1='0.98')
    obj(dyn, 'sum', 'F22Bay%sState' % bay, anchor, Inputs=' F22Bay%sUnlocked.Output F22Bay%sFullOpen.Output ' % (bay, bay))
obj(dyn, 'logic_or', 'F22BayAnyCommanded', anchor, Inputs=' %s ' % ' '.join('F22Bay%sCommand.Output' % b for b in BAYS))
obj(dyn, 'logic_invert', 'F22BayAllCommand', anchor, Input='F22BayAnyCommanded.Output')
# ALL: decide once (open all if all are shut, else shut all) into a variable, then set the three commands from it -
# an event chain re-reads its input after every target, so set straight from F22BayAllCommand it flipped back midway
obj(dyn, 'variable', 'F22BayAllTarget', anchor, Value='0.0')
obj(dyn, 'event_value', 'F22BayAllApply', anchor, Input='F22BayAllTarget.Output',
    Events=' %s ' % ' '.join('F22Bay%sCommand.Set' % b for b in BAYS))
obj(dyn, 'event_value', 'F22BayAllToggle', anchor, Input='F22BayAllCommand.Output',
    Events=' F22BayAllTarget.Set F22BayAllApply.Trigger ')
obj(dyn, 'input_event', 'F22BayAllMessage', anchor, Message='Weapons.BayAll', Events=' F22BayAllToggle.Trigger ')
obj(dyn, 'logic_or', 'F22BayOpen', anchor, Inputs=' %s ' % ' '.join('F22Bay%sUnlocked.Output' % b for b in BAYS))
# air refuelling receptacle (AAR panel: door OPEN / CLOSE switch, receptacle light knob) - for the look, Aerofly has
# no refuelling; the door needs hydraulics (battery), the light DC power
obj(dyn, 'input_switch', 'F22AARSwitch', anchor, Message='Fuel.AARDoor', Value=0.0,
    Events=' SwitchSoundLeftConsole.Trigger ', EventsRelease=' SwitchSoundLeftConsole.Trigger ')
obj(dyn, 'product', 'F22AARDoorDemand', anchor, Inputs=' F22AARSwitch.Output DCBusEssentialOn.Output ')
obj(dyn, 'servoclassic', 'F22AARDoor', anchor, Input='F22AARDoorDemand.Output', Speed=0.5, P0=0.0, P1=1.0, P2=0.0,
    P3=0.0, Position=0.0)
obj(dyn, 'input_default', 'F22AARLightKnob', anchor, Message='Fuel.AARLight', Range=' 0.0 1.0 ',
    Positions=('uint', '21'), Value=0.0)
obj(dyn, 'product', 'F22AARLight', anchor, Inputs=' F22AARLightKnob.Output F22AARDoor.Output DCBusEssentialOn.Output ')
# ferry tanks: their fuel is drawn first (the internal fuel waits). Each tank: 1814 kg (600 US gal). The F/A-18 FUEL
# page and total fuel show them as its outer wing tanks. Jettison (2026-11-13): breakage_f22.tank_release / tank_addon
# - an ejector rack breaks the tank's jointlinear and the tank flies free (October: an unlocked joint only slid it)
obj(dyn, 'linear', 'F22TanksAttached', anchor, Input='F22FerryTanks.Output')
obj(dyn, 'product', 'F22TanksFlow', anchor, Inputs=' FuelFlowTotal.Output F22TanksAttached.Output ')
obj(dyn, 'integral_clamped', 'F22TanksBurntRaw', anchor, Input='F22TanksFlow.Output', Range=' 0.0 100000.0 ', Value=0.0)
obj(dyn, 'minimum', 'F22TanksBurnt', anchor, Inputs=' F22TanksBurntRaw.Output %.1f ' % (2 * S.TANK_FUEL))
obj(dyn, 'mixlinear', 'F22TanksLeft', anchor, Input0='F22TanksBurnt.Output', Input1='F22TanksAttached.Output',
    Weight0=-1.0, Weight1=2 * S.TANK_FUEL)
obj(dyn, 'product', 'F22TankFuelEach', anchor, Inputs=' F22TanksLeft.Output F22TanksAttached.Output 0.5 ')
by_name = {o.name: o for o in dyn.children}          # (obj() does not enter D)
setv(by_name['FuelLoadChangedReset'], 'Events', ' FuelUsed.Reset F22TanksBurntRaw.Reset ')
for side in ('Left', 'Right'):
    setv(D['%sOuterExternalTankAttached' % side], 'Input', 'F22TanksAttached.Output')
    setv(D['%sOuterExternalTankFuel' % side], 'Input', 'F22TankFuelEach.Output')
# the internal tanks give only what the ferry tanks did not (the fuel burn section's FuelUsed counts all of it)
obj(dyn, 'mixlinear', 'F22InternalUsed', by_name['FuelLeftLeftTransfer'], Input0='FuelUsed.Output',
    Input1='F22TanksBurnt.Output', Weight0=1.0, Weight1=-1.0)
for o in dyn.children:
    if o.name.startswith('FuelLeft') and o.get('Input1') == 'FuelUsed.Output':
        o.set('Input1', 'F22InternalUsed.Output')
    if o.name == 'FuelUsedBeyondTransfer':
        o.set('Input0', 'F22InternalUsed.Output')
anchor = ufc

# ---------------------------------------------------------------------------------------------- landing / taxi lights
# The F-22 switch is LDG / OFF / TAXI (DCS arg 709: +1 forward = LDG, 0 OFF, -1 aft = TAXI). The F/A-18 switch
# (Controls.Lighting.Landing, 0 .. 2) lit both lamps at > 0.5: now 2 = LDG (landing lamp), 1 = OFF (start value),
# 0 = TAXI (taxi lamp); each lamp only with the nose gear down and locked and DC power, as the Hornet's
setv(D['LandingLightSwitch'], 'Value', 1.0)
setv(D['LandingLightSelectedOn'], 'Input1', '1.5')
anchor = D['LandingLight']
obj(dyn, 'logic_greater', 'F22TaxiLightSelected', anchor, Input0='0.5', Input1='LandingLightSwitch.Output')
obj(dyn, 'logic_and', 'F22TaxiLightOn', anchor,
    Inputs=' NoseGearDownAndLocked.Output F22TaxiLightSelected.Output DCBusEssentialOn.Output ')
D['F22TaxiLight'] = obj(dyn, 'servoclassic', 'F22TaxiLight', anchor, Input='F22TaxiLightOn.Output', Speed=8.0, P0=0.0,
                        P1=1.0, P2=0.0, P3=0.0, Position=0.0)
anchor = ufc

# ---------------------------------------------------------------------------------------------- graphics
G = []


def g(type_, name, **fields):
    n = tmd.Node(type_, name, leaf=False)
    for k, v in fields.items():
        if isinstance(v, tuple):
            t, v = v
        elif isinstance(v, list):
            t, v = 'tmvector3d', ' ' + fmt(v) + ' '
        else:
            t = 'tmvector2d' if k == 'Map' else ('float64' if isinstance(v, float) else 'string8')
        n.children.append(tmd.Node(t, k, v if isinstance(v, str) else '%.6g' % v))
    G.append(n)
    return n


def body(b):
    return {'PositionID': ('uint32', '%s.R' % b), 'OrientationID': ('uint32', '%s.Q' % b)}


# collision hull meshes: the game loads only geometry a graphics object draws - the hulls (ColFuselage ...) were
# missing ('unable to compute bounding sphere for ''' x7 in tm.log), no ground contact, no crash: the aircraft fell
# through the terrain. Drawn hidden (as the King Air's door ropes); every stock hull is a drawn object.
for o in dyn.children:
    if o.type == 'collisionhull':
        g('rigidbodygraphics', 'Hull' + o.name[len('Collision'):], GeometryList=' %s ' % o.get('Geometry').strip(),
          InputHide='1.0', **body(o.get('Body').strip()))


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
C = importlib.import_module(os.environ.get('AC', 'ac_f22'))

# strut stroke per leg from the sampled DCS compression (wheel travel at arg = 1)
COMP_ARG = {1: 'Nose', 6: 'Left', 4: 'Right'}
dcs_stroke = {}
for p in anim.values():
    for l in p['links']:
        if l['kind'] == 'table' and l['arg'] in COMP_ARG:
            t = l['translation'][-1]
            dcs_stroke[COMP_ARG[l['arg']]] = max(dcs_stroke.get(COMP_ARG[l['arg']], 0.0), math.sqrt(sum(x * x for x in t)))

sources = sorted({d['source'] for d in C.DRIVERS.values() if d['kind'] == 'table'})
# gear legs follow the physical retraction joints (angle 0 = down, about -1.7 rad = up)
DYN_OUT = {}
# graphics read dynamic values through explicit `output` objects, as the stock F-15E does (reading servos or
# joints directly returned 0 in the game: gear never moved, nose wheel never steered)
out_anchor = D['GearInput']


def published(dyn_name):
    # an `output` object is terminal: graphics read it directly, dynamics objects cannot take it as an input
    # input_button: the graphics read it directly as the stock F/A-18 does; an `output` object taking it as its
    # input stopped the dynamics from loading ("property 'EmergencyJettisionButton.Output' not found": STOP sign)
    if dyn_name in D and D[dyn_name].type in ('output', 'input_button'):
        return dyn_name + '.Output'
    # `output_free` objects did not reach the graphics in the game (stick stayed still while the throttles and
    # pedals, read through `output` objects, moved): publish the value it forwards instead
    if dyn_name in D and D[dyn_name].type == 'output_free':
        src = D[dyn_name].get('Input').strip()
        if src.endswith('.Output'):
            return published(src[:-len('.Output')])
    out = 'GfxOut' + dyn_name
    if out not in D:
        D[out] = obj(dyn, 'output', out, out_anchor, Input=dyn_name + '.Output')
    return out + '.Output'


for src in sources:
    if src == 'StrokeNose':
        # nose: prismatic joint (0 = modelled length), DCS compression 0..1 over the DCS stroke
        joint = 'JointNoseGearLower'
        sgn = 1.0 if vec(D[joint].get('X0'))[2] > 0 else -1.0
        g('graphics_input', 'Gfx' + src + 'Raw', InputID=('uint32', published(joint)))
        pts = sorted([(sgn * -NOSE_EXT, 0.0), (sgn * (-NOSE_EXT + dcs_stroke.get('Nose', 0.1)), 1.0)])
        g('graphics_linear_interpolation', 'Gfx' + src, Input='Gfx%sRaw.Output' % src,
          Map=' ' + ' '.join('(%.4f %.4f)' % p for p in pts) + ' ')
    elif src.startswith('Stroke'):
        # mains: the F/A-18 trailing arm angle, fully extended oleo -> 0, fully compressed -> 1
        side = src[6:]
        a_ext, a_cmp, _ = ARM[side]
        g('graphics_input', 'Gfx' + src + 'Raw', InputID=('uint32', published('Joint%sGearLower' % side)))
        g('graphics_linear_interpolation', 'Gfx' + src, Input='Gfx%sRaw.Output' % src,
          Map=' ' + ' '.join('(%.4f %.4f)' % p for p in sorted([(a_ext, 0.0), (a_cmp, 1.0)])) + ' ')
    else:
        g('graphics_input', 'Gfx' + src, InputID=('uint32', published(DYN_OUT.get(src, src))))
mapped = {}


def driver_input(arg):
    d = C.DRIVERS[arg]
    if 'map' not in d:
        return 'Gfx%s.Output' % d['source']
    key = (d['source'], tuple(map(tuple, d['map'])))
    if key not in mapped:
        n = 'Gfx%sToArg%d' % (d['source'], arg)
        g('graphics_linear_interpolation', n, Input='Gfx%s.Output' % d['source'],
          Map=' ' + ' '.join('(%.4f %.4f)' % tuple(p) for p in d['map']) + ' ')
        mapped[key] = n + '.Output'
    return mapped[key]


g('rigidbodygraphics', 'Fuselage', GeometryList=' Fuselage ', **body('Fuselage'))
PART_XFORM = {}          # animated part -> its full graphics transform (cockpit click volumes move with it)
for pname in sorted(parts):
    if pname.startswith('Body_'):
        g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, **body(pname[5:]))
for pname, p in sorted(anim.items()):
    if pname in getattr(C, 'NOZZLE_PLATES', {}):         # one rigid plate: ac_f22.py
        flap, side = C.NOZZLE_PLATES[pname]
        sig = 'F22Flap%s%s' % (flap, side)
        if sig not in D:
            D[sig] = obj(dyn, 'mixlinear', sig, out_anchor, Input0='NozzleAngle.Output', Input1='Nozzle%s.Output' % side, Weight0=1.0,
                         Weight1=C.NOZZLE_OPEN if flap == 'Upper' else -C.NOZZLE_OPEN)
            g('graphics_input', 'Gfx' + sig, InputID=('uint32', published(sig)))
        hx, hz = C.NOZZLE_HINGE[flap]
        g('graphics_rotation', pname + '_Plate', Input='Gfx%s.Output' % sig, Axis=[0.0, 1.0, 0.0], Pivot=[hx, p['pivot'][1], hz])
        PART_XFORM[pname] = pname + '_Plate.Output'
        g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, **body('Fuselage'), InputTransform=pname + '_Plate.Output')
        continue
    chain = []  # outermost first (applied last)
    for l in reversed(p['links']):
        if l['kind'] == 'spin':
            g('graphics_input', pname + '_SpinInput', InputID=('uint32', l['hull'] + '.RotationAngle'))
            chain.append(('graphics_rotation', pname + '_Spin',
                          dict(Input=pname + '_SpinInput.Output', Axis=l['axis'], Pivot=l['pivot'])))
            continue
        src = driver_input(l['arg'])
        if C.DRIVERS.get(l['arg'], {}).get('mirror'):       # -1 .. 0 as the mirror of 0 .. 1 (OFF of a three-way toggle)
            table = lambda vals: ' ' + ' '.join('(%.3f %.6f)' % (a, v) for a, v in
                                                sorted({(-a, -v) for a, v in zip(l['samples'], vals) if a > 0} |
                                                       set(zip(l['samples'], vals)))) + ' '
        else:
            table = lambda vals: ' ' + ' '.join('(%.3f %.6f)' % (a, v) for a, v in zip(l['samples'], vals)) + ' '
        for i in range(3):
            vals = [t[i] for t in l['translation']]
            if max(vals) - min(vals) > 1e-4:
                m = g('graphics_linear_interpolation', '%s_A%d_T%dMap' % (pname, l['arg'], i), Input=src, Map=table(vals))
                chain.append(('graphics_translation', '%s_A%d_T%d' % (pname, l['arg'], i),
                              dict(Input=m.name + '.Output', Axis=[float(i == k) for k in range(3)])))
        for i in (2, 1, 0):
            vals = [e[i] for e in l['euler']]
            if max(vals) - min(vals) > 1e-4:
                m = g('graphics_linear_interpolation', '%s_A%d_R%dMap' % (pname, l['arg'], i), Input=src, Map=table(vals))
                chain.append(('graphics_rotation', '%s_A%d_R%d' % (pname, l['arg'], i),
                              dict(Input=m.name + '.Output', Axis=[float(i == k) for k in range(3)], Pivot=p['pivot'])))
    for k, (t, n, fields) in enumerate(chain):
        if k + 1 < len(chain):
            fields = dict(fields, InputTransform=chain[k + 1][1] + '.Output')
        g(t, n, **fields)
    extra = {'InputTransform': chain[0][1] + '.Output'} if chain else {}
    PART_XFORM[pname] = extra.get('InputTransform')
    g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, **body('Fuselage'), **extra)
# static DCS objects drawn as parts of their own (ac STATIC_PARTS), fixed to the fuselage
for pname in getattr(C, 'STATIC_PARTS', {}):
    if pname in parts:
        g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, **body('Fuselage'))
# ---------------------------------------------------------------------------------------------- console switches (2026-11-04)
# The static console controls made working parts (ac SWITCH_PARTS / CLICK_SWITCHES); each acts on the aircraft, none is
# an empty toggle (user). The F/A-18 systems behind YAW TRIM (rudder trim) and LAMP TEST (annunciator test) are the
# donor's own; the rest is ours below. Donor cockpit volumes, anti-ice, bleed air and cabin temperature feed nothing
# in Aerofly (outputs for the Hornet's knob graphics only): those F-22 knobs stay static.
def dyn_node(name):
    return next(o for o in dyn.children if o.name == name)


def add_inputs(name, *extra):
    n = dyn_node(name)
    n.set('Inputs', ' %s %s ' % (n.get('Inputs').strip(), ' '.join(extra)), 'string8')


SW_SOUND = dict(EventsUp=' SwitchSoundLeftConsole.Trigger ', EventsDown=' SwitchSoundLeftConsole.Trigger ')
# FADEC (ENGINES panel, our choice - the mod's knob has L and R marks): L = left engine FADEC off, R = right off, NORM
# both on. An engine without its FADEC gets no fuel: it runs down and does not light (dry motoring with MOTOR). This is
# the way to shut an engine down - the throttle's own cut-off (below idle) is out of reach of a hardware throttle.
obj(dyn, 'input_discrete', 'F22FadecSelector', anchor, Message='Engines.F22Fadec', Range=' -1.0 1.0 ', Value=0.0, **SW_SOUND)
obj(dyn, 'logic_greater', 'F22Fadec1On', anchor, Input0='F22FadecSelector.Output', Input1='-0.5')
obj(dyn, 'logic_greater', 'F22Fadec2On', anchor, Input0='0.5', Input1='F22FadecSelector.Output')
for k in (1, 2):
    add_inputs('Engine%dRunWithFuel' % k, 'F22Fadec%dOn.Output' % k)
# MOTOR: the starter turns every engine that is not running while the button is held (and 1 s after a click: a
# mouse click is one press event). With FADEC on and the throttle out of cut-off the engine lights as on a normal start;
# with FADEC off it is dry motoring (no fuel). The donor's crank (keyboard Engines.Crank) stays.
def push_button(name, message):
    """A push button as a held state: input_button has no Output (only press / release events - 'property
    F22MotorButton.Output not found' stopped the aircraft from loading, 2026-11-05): its events set a variable 1 / 0."""
    obj(dyn, 'variable', name + 'Pressed', anchor, Value='0.0')
    obj(dyn, 'event_value', name + 'Down', anchor, Input='1.0', Events=' %sPressed.Set ' % name)
    obj(dyn, 'event_value', name + 'Up', anchor, Input='0.0', Events=' %sPressed.Set ' % name)
    obj(dyn, 'input_button', name, anchor, Message=message, InputValue='1.0',
        Events=' %sDown.Trigger ButtonSoundCenterPanel.Trigger ' % name,
        EventsRelease=' %sUp.Trigger ButtonSoundCenterPanel.Trigger ' % name)
    return name + 'Pressed.Output'


obj(dyn, 'logic_confirm_delay', 'F22MotorHeld', anchor, Input=push_button('F22MotorButton', 'Engines.F22Motor'),
    TimeUp=0.0001, TimeDown=1.0)
for k in (1, 2):
    obj(dyn, 'logic_and', 'F22Motor%d' % k, anchor, Inputs=' F22MotorHeld.Output Engine%dNotRunning.Output ' % k)
    add_inputs('Engine%dStartRequest' % k, 'F22Motor%d.Output' % k)
# ALT FLAPS (FLCS panel): EXTEN puts the flaps to the takeoff / landing setting with the gear up as well, below 250 kt
# (our limit, as the F-16's alternate flaps); NORM leaves them to the automatic schedule (gear handle).
obj(dyn, 'input_discrete', 'F22AltFlapsSwitch', anchor, Message='Controls.F22AltFlaps', Range=' 0.0 1.0 ', Value=0.0,
    **SW_SOUND)
obj(dyn, 'logic_greater', 'F22AltFlapsSlow', anchor, Input0='128.6', Input1='AirDataComputer.OutputCalibratedAirspeed')
obj(dyn, 'logic_and', 'F22AltFlapsActive', anchor, Inputs=' F22AltFlapsSwitch.Output F22AltFlapsSlow.Output ')
# (from F22FlapsGearDown - the handle, or the gear down by ALT GR: this line had GearLever and overrode it, so with ALT GR
# the G key still moved the flaps, in-game 2026-11-15)
obj(dyn, 'maximum', 'F22FlapDemand', D['FlapsSelector'], Inputs=' F22FlapsGearDown.Output F22AltFlapsActive.Output ')
setv(D['FlapsSelector'], 'Input', 'F22FlapDemand.Output')
# CNI (right console): power of the navigation receivers and the transponder - off: no ILS, TACAN, ADF, DME, marker
# beacons or transponder (needles, HUD and CPL lose their signal).
obj(dyn, 'input_discrete', 'F22CNISwitch', anchor, Message='Avionics.F22CNI', Range=' 0.0 1.0 ', Value=1.0,
    EventsUp=' SwitchSoundRightConsole.Trigger ', EventsDown=' SwitchSoundRightConsole.Trigger ')
for name in ('TACANOn', 'TACANDMEOn', 'ILSOn', 'ILSDMEOn', 'ADF1Receiver', 'ADF2Receiver', 'TransponderOn'):     # (+ the marker receiver, below)
    node = D.get(name) or dyn_node(name)
    old = node.get('InputEnable')
    if old is None:
        print('WARNING CNI: %s has no InputEnable' % name)
        continue
    obj(dyn, 'logic_and', 'F22CNI' + name, anchor, Inputs=' %s F22CNISwitch.Output ' % old.strip())
    node.set('InputEnable', 'F22CNI%s.Output' % name, 'string8')
# AUX/ACP (right console): the audio control panel - off: no voice warnings, GCAS tone or marker tones in the headset
obj(dyn, 'input_discrete', 'F22ACPSwitch', anchor, Message='Avionics.F22ACP', Range=' 0.0 1.0 ', Value=1.0,
    EventsUp=' SwitchSoundRightConsole.Trigger ', EventsDown=' SwitchSoundRightConsole.Trigger ')
# DN LOCK OVERRIDE (beside the gear handle): on the ground the donor holds the gear down whatever the handle says
# (GearSequence follows 'gear down or on ground'); the button frees the handle for 3 s - the gear then retracts on the
# ground (emergency use, as the real override)
obj(dyn, 'logic_confirm_delay', 'F22DownLockOverride', anchor,
    Input=push_button('F22DownLockOverrideButton', 'Gear.F22DownLockOverride'), TimeUp=0.0001, TimeDown=3.0)
obj(dyn, 'logic_invert', 'F22DownLockNotOverridden', anchor, Input='F22DownLockOverride.Output')
obj(dyn, 'logic_and', 'F22GroundGearLock', anchor, Inputs=' OnGroundSensor.Output F22DownLockNotOverridden.Output ')
node = D.get('GearDownOrOnGround') or dyn_node('GearDownOrOnGround')
assert 'OnGroundSensor.Output' in node.get('Inputs')
node.set('Inputs', node.get('Inputs').replace('OnGroundSensor.Output', 'F22GroundGearLock.Output'), 'string8')
# FLCS BIT (our sequence, no data on the F-22's): START on the ground with DC power and hydraulic pressure (engine or
# APU pumps: the check moves the surfaces) runs a 40 s check, FLCS BIT on
# the ICAWS while it runs, BIT PASS when done; OFF and STOP hold the result, STOP aborts a check still running, loss of
# DC power clears it; each new START (from OFF) clears the last result and runs it again. In the air it does not run.
# The switch rests at STOP (aft, under the notch of its red guard, as modelled); the guard lifts whenever the switch is
# out of STOP (user 2026-11-05: it stayed shut). STOP aborts a running check, a passed one stays (BIT PASS until power
# goes or a new START).
obj(dyn, 'input_discrete', 'F22FlcsBitSwitch', anchor, Message='FCS.F22Bit', Range=' -1.0 1.0 ', Value=-1.0, **SW_SOUND)
obj(dyn, 'logic_greater', 'F22FlcsGuardOpen', anchor, Input0='F22FlcsBitSwitch.Output', Input1='-0.5')
obj(dyn, 'servoclassic', 'F22FlcsGuard', anchor, Input='F22FlcsGuardOpen.Output', Speed=5.0, P1=1.0, Position=0.0)
obj(dyn, 'logic_greater', 'F22BitStart', anchor, Input0='F22FlcsBitSwitch.Output', Input1='0.5')
obj(dyn, 'logic_greater', 'F22BitStopSwitch', anchor, Input0='-0.5', Input1='F22FlcsBitSwitch.Output')
obj(dyn, 'logic_greater', 'F22BitHydOK', anchor, Input0='F22HydAuthority.Output', Input1='0.9')
obj(dyn, 'logic_and', 'F22BitCanRun', anchor,
    Inputs=' F22BitStart.Output OnGroundSensor.Output DCBusEssentialOn.Output F22BitHydOK.Output ')
obj(dyn, 'logic_invert', 'F22BitNoPower', anchor, Input='DCBusEssentialOn.Output')
obj(dyn, 'logic_and', 'F22BitAbort', anchor, Inputs=' F22BitStopSwitch.Output F22BitNotPass.Output ')
# a new START (from OFF) clears the last result and runs the check again: 0.2 s after the switch reaches START
obj(dyn, 'logic_confirm_delay', 'F22BitStartHeld', anchor, Input='F22BitStart.Output', TimeUp=0.2, TimeDown=0.0001)
obj(dyn, 'logic_invert', 'F22BitStartNotHeld', anchor, Input='F22BitStartHeld.Output')
obj(dyn, 'logic_and', 'F22BitRestart', anchor, Inputs=' F22BitStart.Output F22BitStartNotHeld.Output ')
obj(dyn, 'logic_or', 'F22BitStop', anchor, Inputs=' F22BitAbort.Output F22BitNoPower.Output F22BitRestart.Output ')
obj(dyn, 'mixlinear', 'F22BitRate', anchor, Input0='F22BitCanRun.Output', Input1='F22BitStop.Output',
    Weight0=1.0 / 40.0, Weight1=-50.0, Offset=0.0)
obj(dyn, 'integral_clamped', 'F22BitProgress', anchor, Input='F22BitRate.Output', Range=' 0.0 1.0 ', Value=0.0)
obj(dyn, 'logic_greater', 'F22BitPass', anchor, Input0='F22BitProgress.Output', Input1='0.999')
obj(dyn, 'logic_invert', 'F22BitNotPass', anchor, Input='F22BitPass.Output')
# LAMP TEST / off / NVG (one three-way toggle): the donor's annunciator test switch gets the third position; NVG
# dims the annunciators (gear, BATT, the donor's lamps) to a third for night vision goggles
lt = dyn_node('LightTestSwitch')
setv(lt, 'Range', ' -1.0 1.0 ')
obj(dyn, 'linear_interpolation', 'F22NvgDim', anchor, Input='LightTestSwitch.Output',
    Map=' ( -1.0 0.35 ) ( -0.5 1.0 ) ( 1.0 1.0 ) ')
add_inputs('AnnunciatorBrightness', 'F22NvgDim.Output')
obj(dyn, 'logic_and', 'F22BitRunning', anchor, Inputs=' F22BitCanRun.Output F22BitNotPass.Output ')
# BATT lamp (right of the battery switch, the mod's BATT plate): the battery alone feeds the DC bus - no engine
# generator and no APU generator on line
obj(dyn, 'logic_or', 'F22GeneratorOnline', anchor,
    Inputs=' Engine1GeneratorContactor.Output Engine2GeneratorContactor.Output ExternalPowerConnected.Output ')
obj(dyn, 'logic_invert', 'F22NoGenerator', anchor, Input='F22GeneratorOnline.Output')
obj(dyn, 'logic_and', 'F22OnBattery', anchor, Inputs=' DCBusEssentialOn.Output F22NoGenerator.Output ')
# ---------------------------------------------------------------------------------------------- emergency power (2026-11-05)
# APU: the F-22's APU with its stored-energy start gives in-flight emergency power for recovery (globalsecurity, F-22
# flight critical systems). It burns the aircraft's fuel (feed tanks) and needs DC power to start and run; no fuel or
# no DC: it does not start, a running one stops. Its flow is our estimate (the G-250's is not published): 0.02 kg/s,
# about 160 lb/h. (The donor APU spun up from the switch alone, without fuel or power.)
obj(dyn, 'logic_or', 'F22ApuFuel', anchor, Inputs=' Engine1FuelFed.Output Engine2FuelFed.Output ')
obj(dyn, 'logic_and', 'F22ApuCanRun', anchor, Inputs=' F22ApuFuel.Output DCBusEssentialOn.Output ')
# APU switch OFF / ARM / START (user 2026-11-06: the game had only two positions - the donor's APU on / off): START
# starts it, it runs in ARM, OFF stops it; losing fuel or DC power stops it too (a new START is needed)
obj(dyn, 'input_discrete', 'F22ApuSwitch', D['APUN1'], Message='Engines.F22Apu', Range=' -1.0 1.0 ', Value=-1.0,
    EventsUp=' SwitchSoundLeftConsole.Trigger ', EventsDown=' SwitchSoundLeftConsole.Trigger ')
obj(dyn, 'logic_greater', 'F22ApuStartPos', D['APUN1'], Input0='F22ApuSwitch.Output', Input1='0.5')
obj(dyn, 'logic_greater', 'F22ApuOffPos', D['APUN1'], Input0='-0.5', Input1='F22ApuSwitch.Output')
# (the latch is set by event_value objects, as the ICAWS acknowledge: the first build set it from event_edge_rising with
# Value 0 and OFF did not stop the APU in the game, user 2026-11-06)
obj(dyn, 'variable', 'F22ApuRun', D['APUN1'], Value='0.0')
obj(dyn, 'event_value', 'F22ApuRunOn', D['APUN1'], Input='1.0', Events=' F22ApuRun.Set ')
obj(dyn, 'event_value', 'F22ApuRunOff', D['APUN1'], Input='0.0', Events=' F22ApuRun.Set ')
obj(dyn, 'event_edge_rising', 'F22ApuStarted', D['APUN1'], Input='F22ApuStartPos.Output', Events=' F22ApuRunOn.Trigger ', Value=1.0, Threshold=0.5)
obj(dyn, 'event_edge_rising', 'F22ApuStopped', D['APUN1'], Input='F22ApuOffPos.Output', Events=' F22ApuRunOff.Trigger ', Value=1.0, Threshold=0.5)
# Fuel or DC lost for 2 s stops it (the APU controller rides through a short interruption). Without the ride-through
# the APU died ~1 s after it came up (user 2026-11-06): the battery feeds DC ESS only while DC L is below 12 V
# (DCBusEssentialFeedFromUtilityBattery, BatterySwitchOnAndDCBusLeftOff) while DCBusEssentialOn needs 20 V, so as the
# APU generator picks up the network (the ~0.5 s settling measured with DIAG_POWER) DC ESS reads off and the latch reset.
obj(dyn, 'logic_invert', 'F22ApuCannotRunNow', D['APUN1'], Input='F22ApuCanRun.Output')
obj(dyn, 'logic_confirm_delay', 'F22ApuCannotRun', D['APUN1'], Input='F22ApuCannotRunNow.Output', TimeUp=2.0,
    TimeDown=0.0001, Threshold=0.5)
obj(dyn, 'logic_invert', 'F22ApuCanRunHeld', D['APUN1'], Input='F22ApuCannotRun.Output')
obj(dyn, 'event_edge_rising', 'F22ApuDropped', D['APUN1'], Input='F22ApuCannotRun.Output', Events=' F22ApuRunOff.Trigger ', Value=1.0, Threshold=0.5)
# (the OFF position also holds it off directly: nothing can latch it on while the switch is at OFF)
obj(dyn, 'logic_invert', 'F22ApuNotOff', D['APUN1'], Input='F22ApuOffPos.Output')
obj(dyn, 'product', 'F22ApuDemand', D['APUN1'], Inputs=' F22ApuRun.Output F22ApuCanRunHeld.Output F22ApuNotOff.Output ')
setv(D['APUN1'], 'Input', 'F22ApuDemand.Output')
setv(dyn_node('APUMasterSwitchSetOnResetTimeOnGround'), 'Input', 'F22ApuRun.Output')
obj(dyn, 'product', 'F22ApuFuelFlow', anchor, Inputs=' APUAvailable.Output 0.02 ')
add_inputs('FuelFlowTotal', 'F22ApuFuelFlow.Output')
# standby air data: the air data computer's second channel on the DC essential bus (standby sensors), so the standby
# airspeed and altitude on the right UFD stay alive on the battery
setv(D['AirDataComputer'], 'InputEnable1', 'DCBusEssentialOn.Output')
# hydraulics (the donor's two pressures were constants - the surfaces moved with both engines dead): each system's
# pressure from its engine-driven pump by N2 (full from ~55 %, idle is above; a windmilling engine gives part - our
# estimate of the pump curve), the APU drives the emergency pump on system 1 (Eaton: emergency hydraulic pump).
# Every surface is powered by both systems: the actuators get the larger share - no pressure, the commands fade and
# the surfaces trail to neutral, part pressure, part deflection. (The F119's nozzles are fuel-actuated: not here.)
# A stopped engine in Aerofly does not windmill: its N2 falls to 0 (user's test 2026-11-05: RPM 0, the pressure fell
# from 3000 to 0 and stayed). A real one keeps turning in the airflow and its pumps give part of their output: the
# windmill N2 here is our estimate by airspeed (none below 100 kt, ~15 % at 250 kt, ~22 % at 400 kt - typical of
# military turbofans, no F119 figure is public); the gearbox pumps (hydraulic, the nozzles' fuel pressure) turn with
# the larger of the two. The pumps are variable-displacement: the pressure holds down to a low speed (full from 25 %
# N2, half at 10 % - estimate) - what fades is how much the surfaces can do.
obj(dyn, 'linear_interpolation', 'F22WindmillN2', anchor, Input='AirDataComputer.OutputCalibratedAirspeed',
    Map=' (51.4 0.0) (77.2 0.09) (128.6 0.15) (205.8 0.22) (300.0 0.28) ')
for k in (1, 2):
    obj(dyn, 'maximum', 'F22Eng%dGearboxN2' % k, anchor, Inputs=' Engine%dN2.Output F22WindmillN2.Output ' % k)
    obj(dyn, 'linear_interpolation', 'F22HydPump%d' % k, anchor, Input='F22Eng%dGearboxN2.Output' % k,
        Map=' (0.05 0.0) (0.10 0.4) (0.16 0.8) (0.25 1.0) ')
obj(dyn, 'maximum', 'F22HydSystem1', anchor, Inputs=' F22HydPump1.Output APUAvailable.Output ')
obj(dyn, 'maximum', 'F22HydSystem2', anchor, Inputs=' F22HydPump2.Output ')
obj(dyn, 'maximum', 'F22HydAuthority', anchor, Inputs=' F22HydSystem1.Output F22HydSystem2.Output ')
for k in (1, 2):
    obj(dyn, 'product', 'F22HydPressure%d' % k, anchor, Inputs=' F22HydSystem%d.Output 20684280.0 ' % k)
    setv(D['NeedleHydraulicPressure%dMapping' % k], 'Input', 'F22HydPressure%d.Output' % k)
    obj(dyn, 'logic_greater', 'F22HydLow%d' % k, anchor, Input0='0.5', Input1='F22HydSystem%d.Output' % k)
obj(dyn, 'logic_or', 'F22HydLow', anchor, Inputs=' F22HydLow1.Output F22HydLow2.Output ')
# the F119's nozzles are moved by fuel pressure from the engine-driven pump (fueldraulic): with both engines dead and
# no windmill they stay where they are and vector nothing (the first build let dead engines vector - a glide held in
# pitch by the nozzles). The two nozzles share one angle: the larger pump decides.
obj(dyn, 'maximum', 'F22NozzleActuation', anchor, Inputs=' F22HydPump1.Output F22HydPump2.Output ')
# (applied to NozzleAngle after tvc_f22.apply, which builds it)
# ---- what must stop without AC power or hydraulics (audit 2026-11-05, user: "check what keeps working that should not")
# gear: retracting needs hydraulic pressure; without it a lowered gear stays down (down-locks) and a raised one stays up
# (up-locks) until it is selected down - then it falls free (no pressure needed). (GearSequence followed the handle
# with both engines dead.)
obj(dyn, 'logic_greater', 'F22GearHydOK', anchor, Input0='F22HydAuthority.Output', Input1='0.5')
obj(dyn, 'logic_invert', 'F22GearHydLost', anchor, Input='F22GearHydOK.Output')
obj(dyn, 'logic_greater', 'F22GearIsDown', anchor, Input0='GearSequence.Output', Input1='0.5')
obj(dyn, 'logic_and', 'F22GearHeldDown', anchor, Inputs=' F22GearHydLost.Output F22GearIsDown.Output ')
obj(dyn, 'logic_or', 'F22GearTarget', D['GearSequence'], Inputs=' GearDownOrOnGround.Output F22GearHeldDown.Output ')
setv(D['GearSequence'], 'Input', 'F22GearTarget.Output')
# strut travel as drawn (work/anim.json, args 0 / 3 / 5): the nose strut swings evenly over the whole sequence, the
# main struts at 0.5 - 0.9 (doors 0.3 - 0.5). The Hornet maps moved all three at 0.25 - 0.75, so the gear joints and
# the down / up-lock lamps ran together and off the picture (user 2026-11-07: lamps late and all three in step, the
# nose takes longer)
setv(dyn_node('MapNoseGear'), 'Map', ' (0.0 1.0) (1.0 0.0) ')
setv(dyn_node('MapMainGear'), 'Map', ' (0.0 1.0) (0.5 1.0) (0.9 0.0) (1.0 0.0) ')
# wheel brakes: hydraulic, with an accumulator for braking without pressure - our estimate of its size: 8 s of full
# braking (no F-22 figure), recharged by the pumps in about 2 s. The parking brake holds on trapped pressure.
obj(dyn, 'maximum', 'F22BrakeDemand', anchor, Inputs=' LeftBrakePedal.Output RightBrakePedal.Output ')
obj(dyn, 'mixlinear', 'F22BrakeAccRate', anchor, Input0='F22GearHydOK.Output', Input1='F22BrakeDemand.Output',
    Weight0=0.5, Weight1=-0.125, Offset=0.0)
obj(dyn, 'integral_clamped', 'F22BrakeAccumulator', anchor, Input='F22BrakeAccRate.Output', Range=' 0.0 1.0 ', Value=1.0)
obj(dyn, 'logic_greater', 'F22BrakeAccCharged', anchor, Input0='F22BrakeAccumulator.Output', Input1='0.02')
obj(dyn, 'maximum', 'F22BrakeSupply', anchor, Inputs=' F22HydAuthority.Output F22BrakeAccCharged.Output ')
for side in ('Left', 'Right'):
    obj(dyn, 'product', 'F22%sBrakePowered' % side, anchor, Inputs=' %sBrakePedal.Output F22BrakeSupply.Output ' % side)
    setv(D['%sBrakeMix' % side], 'Inputs', ' F22%sBrakePowered.Output ParkingBrake.Output ' % side)
# autopilot: its modes run in the mission computers (AC): it drops out when they lose power and cannot be engaged
obj(dyn, 'logic_invert', 'F22NoMissionComputer', anchor, Input='MissionComputer1On.Output')
obj(dyn, 'logic_and', 'F22ApWithoutPower', anchor, Inputs=' FlightController.OutputAutopilotActive F22NoMissionComputer.Output ')
obj(dyn, 'event_edge_rising', 'F22ApPowerLoss', anchor, Input='F22ApWithoutPower.Output',
    Events=' FlightController.DisconnectAutopilot ', Value=1.0, Threshold=0.5)
# landing and taxi lights: heavy AC loads, off on the battery
add_inputs('LandingLightOn', 'ACBus1AOn.Output')
add_inputs('F22TaxiLightOn', 'ACBus1AOn.Output')
HYD_SERVOS = ('ServoLeftAileron', 'ServoRightAileron', 'ServoLeftRudder', 'ServoRightRudder', 'ServoLeftFlap',
              'ServoRightFlap', 'ServoLeftSlat', 'ServoRightSlat', 'ServoOuterLeftSlat', 'ServoOuterRightSlat',
              'ServoAirBrake', 'ServoSteering')       # the stabilators: after tvc_f22.apply (it sets their inputs)
# FLCS BIT surface program (user 2026-11-05: the check only lit ICAWS lines - as a fly-by-wire ground BIT, the surfaces
# now run through their travel and the stick and pedals do nothing while it runs). Over the 40 s (F22BitProgress 0..1):
# stabilators together (pitch), then against each other (roll), ailerons, rudders, trailing-edge flaps, leading-edge
# flaps, then neutral. Angles (rad) about 80 % of each surface's drawn travel: ailerons / rudders +-30 deg (ac DRIVERS
# 11/12/17/18), LEF 0..20 deg (603); the flaps 20 deg and the stabilators +-20 deg are our choice. The servos' own rates
# limit the motion.
def _bit_map(*pts):
    return ' %s ' % ' '.join('(%.3f %.3f)' % p for p in pts)
_W = lambda p0, p1, a: [(p0, 0.0), (p0 + 0.25 * (p1 - p0), a), (p0 + 0.75 * (p1 - p0), -a), (p1, 0.0)]   # 0 +a -a 0
_D = lambda p0, p1, a: [(p0, 0.0), (p0 + 0.5 * (p1 - p0), a), (p1, 0.0)]                               # 0 a 0
BIT_PROGRAM = {
    'ServoLeftAileron': [(0.0, 0.0)] + _W(0.35, 0.55, 0.40) + [(1.0, 0.0)],
    'ServoRightAileron': [(0.0, 0.0)] + _W(0.35, 0.55, -0.40) + [(1.0, 0.0)],
    'ServoLeftRudder': [(0.0, 0.0)] + _W(0.55, 0.70, 0.40) + [(1.0, 0.0)],
    'ServoRightRudder': [(0.0, 0.0)] + _W(0.55, 0.70, 0.40) + [(1.0, 0.0)],
    'ServoLeftFlap': [(0.0, 0.0)] + _D(0.70, 0.85, 0.35) + [(1.0, 0.0)],
    'ServoRightFlap': [(0.0, 0.0)] + _D(0.70, 0.85, 0.35) + [(1.0, 0.0)],
    'ServoLeftSlat': [(0.0, 0.0)] + _D(0.85, 0.95, 0.30) + [(1.0, 0.0)],
    'ServoRightSlat': [(0.0, 0.0)] + _D(0.85, 0.95, 0.30) + [(1.0, 0.0)],
    'ServoOuterLeftSlat': [(0.0, 0.0)] + _D(0.85, 0.95, 0.30) + [(1.0, 0.0)],
    'ServoOuterRightSlat': [(0.0, 0.0)] + _D(0.85, 0.95, 0.30) + [(1.0, 0.0)],
    'ServoLeftStabilator': [(0.0, 0.0)] + _W(0.0, 0.2, 0.35)[1:] + _W(0.2, 0.35, 0.35)[1:] + [(1.0, 0.0)],
    'ServoRightStabilator': [(0.0, 0.0)] + _W(0.0, 0.2, 0.35)[1:] + _W(0.2, 0.35, -0.35)[1:] + [(1.0, 0.0)],
}


def bit_command(name, old):
    """The servo's command, or the BIT program while the check runs."""
    if name not in BIT_PROGRAM:
        return old
    node = dyn_node(name)
    obj(dyn, 'linear_interpolation', 'F22Bit' + name, node, Input='F22BitProgress.Output',
        Map=_bit_map(*BIT_PROGRAM[name]))
    obj(dyn, 'multiplexer', 'F22BitSel' + name, node, InputSelect='F22BitRunning.Output',
        Inputs=' %s F22Bit%s.Output ' % (old, name))
    return 'F22BitSel%s.Output' % name


for name in HYD_SERVOS:
    node = dyn_node(name)
    old = bit_command(name, node.get('Input').strip())
    obj(dyn, 'product', 'F22Hyd' + name, node, Inputs=' %s F22HydAuthority.Output ' % old)
    node.set('Input', 'F22Hyd%s.Output' % name, 'string8')
# the controls without a function yet (cockpit_controls.py, 2026-11-16): their states - nothing reads them so far
import cockpit_controls
cockpit_controls.dynamics(obj, dyn, anchor)
# static DCS controls made turning parts (ac KNOB_PARTS: the ICP thumbwheels), turned by their dynamics value 0..1
for k in getattr(C, 'KNOB_PARTS', ()):
    if k.get('spin') or k.get('press'):       # the fans, burner_f22.py; push buttons, PRESS_PARTS below
        continue
    h = parts.get(k['part'], {}).get('hinge')
    if h is None:
        print('WARNING knob part %s not exported' % k['part'])
        continue
    g('graphics_input', 'Gfx' + k['part'], InputID=('uint32', published(k['source'])))
    if 'angles' in k:        # switches and pointer knobs (ac SWITCH_PARTS): value -> degrees about the axis
        steps = ['(%.4f %.5f)' % (v, math.radians(a)) for v, a in k['angles']]
    else:
        # ridge-pitch steps: detent i of n -> (i mod phases) / phases of a pitch (the wheel mesh is an open arc)
        n = k['positions'] - 1
        steps = ['(%.4f %.5f)' % (i / n, math.radians(k['pitch']) * (i % k['phases']) / k['phases']) for i in range(n + 1)]
    g('graphics_linear_interpolation', k['part'] + '_Angle', Input='Gfx%s.Output' % k['part'],
      Map=' %s ' % ' '.join(steps))
    g('graphics_rotation', k['part'] + '_Turn', Input=k['part'] + '_Angle.Output', Axis=h['axis'], Pivot=h['pivot'])
    g('rigidbodygraphics', k['part'], GeometryList=' %s ' % k['part'], **body('Fuselage'),
      InputTransform=k['part'] + '_Turn.Output')


# keys of the screens and the ICP (ac PRESS_PARTS, 2026-11-16): objects of their own in the DCS cockpit, static there.
# Each is a part of its own now and goes in while it is held, the stock F/A-18's way (its UFC keys: a graphics_input
# on the key's input_button - the graphics read a button's Output, the dynamics cannot - scaled to 1.5 mm, a
# graphics_translation into the panel). A key whose message has no input_button yet (an input_event acts on it, or
# nothing does: the keys still free) gets a silent one of its own beside it, as the stock pairs a button and an event
# on one message
def press_button(k):
    for o in dyn.children:
        if o.type != 'input_button' or (o.get('Message') or '').strip() != k['message']:
            continue
        iv = o.get('InputValue')
        if k['value'] is None or (iv is not None and abs(float(iv) - k['value']) < 1e-6):
            return o.name
    name = 'F22Press' + re.sub(r'\W', '', k['part'][2:])
    fields = dict(Message=k['message'])
    if k['value'] is not None:
        fields['InputValue'] = '%g' % k['value']
    D[name] = obj(dyn, 'input_button', name, D['UpFrontKey0'], **fields)
    return name


def press_axis(k):
    if k['axis'] == 'x':
        return [1.0, 0.0, 0.0]
    if not isinstance(k['axis'][0], str):        # a cut-out button: its own push direction
        return [float(x) for x in k['axis']]
    c_, dn, rt = (CONNECTORS[q] for q in k['axis'])
    a, b = [x - y for x, y in zip(rt, c_)], [x - y for x, y in zip(c_, dn)]
    n = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    ln = math.sqrt(sum(x * x for x in n))
    n = [x / ln for x in n]
    if sum(x * (e - p) for x, e, p in zip(n, EYE, c_)) > 0:      # into the screen, away from the pilot
        n = [-x for x in n]
    return n


def press_resolve():
    made = 0
    for k, node in press_pending:
        before = len(dyn.children)
        node.set('InputID', press_button(k) + '.Output', 'uint32')
        made += len(dyn.children) - before
    print('key press buttons: %d keys, %d silent buttons of their own' % (len(press_pending), made))


n_press, press_pending = 0, []
for k in getattr(C, 'PRESS_PARTS', ()):
    if k['part'] not in parts:
        print('WARNING key part %s not exported' % k['part'])
        continue
    # (the button is looked up at the end, press_resolve: some keys get their input_button further down, and a silent
    # twin made here stood beside it - UFD.RightPage / RightKey1 / RightKey3 in the first build)
    press_pending.append((k, g('graphics_input', 'Gfx' + k['part'], InputID=('uint32', 'PENDING'),
                               Scaling=float(k.get('depth', C.PRESS_DEPTH)))))
    g('graphics_translation', k['part'] + '_Push', Input='Gfx%s.Output' % k['part'], Axis=press_axis(k))
    g('rigidbodygraphics', k['part'], GeometryList=' %s ' % k['part'], **body('Fuselage'),
      InputTransform=k['part'] + '_Push.Output')
    n_press += 1
print('keys pushed in while held: %d' % n_press)
# stores (stage 6): the bay missiles show with the combat load (the AIM-9X parts '__S' ride their trapeze chains);
# the ferry tanks are drawn by their add-on, on their own bodies
g('graphics_input', 'GfxF22CombatHidden', InputID=('uint32', published('F22CombatHidden')))
if 'Stores_AIM120' in parts:
    g('rigidbodygraphics', 'Stores_AIM120', GeometryList=' Stores_AIM120 ', **body('Fuselage'),
      InputHide='GfxF22CombatHidden.Output')
for n in G:
    if n.type == 'rigidbodygraphics' and n.name.endswith('__S'):
        n.children.append(tmd.Node('string8', 'InputHide', 'GfxF22CombatHidden.Output'))
# the pilot figure (ac PILOT_MATERIAL): drawn from outside and the aircraft's other cameras, not in the pilot's own
# view - as the F/A-18's (graphics_human with ShowInside)
if 'Pilot' in parts:
    g('rigidbodygraphics', 'Pilot', GeometryList=' Pilot ', **body('Fuselage'),
      ShowInside=('uint32', ' %s ' % ' '.join(c for c in cams if c != 'CameraPilot')))  # (as the display caps)

# ---------------------------------------------------------------------------------------------- exterior lights
# Switches of the F/A-18 (left console): position lights (Controls.Lighting.Navigation, brightness knob), formation
# lights (knob), strobe / anti-collision (switch), landing-taxi light (one switch, on only with the nose gear down and
# locked). Positions and colours from the DCS light nodes; lens geometry (parts L_<key> / A_<nodes>__L<key>) glows
# with its switch, point lights are the visible glow sprites, cone lights the light cast on the airframe / ground.
# Brightness values as the accepted Su-35 lights (themselves sized on the stock F/A-18).
g('graphics_input', 'GfxPositionLight', InputID=('uint32', published('PositionLightBrightness')))
g('graphics_input', 'GfxFormationLight', InputID=('uint32', published('FormationLightBrightness')))
g('graphics_input', 'GfxStrobeLight', InputID=('uint32', published('StrobeLight')))
g('graphics_input', 'GfxLandingLight', InputID=('uint32', published('LandingLight')))
g('graphics_input', 'GfxTaxiLight', InputID=('uint32', published('F22TaxiLight')))
g('graphics_input', 'GfxLightTime', InputID=('uint32', published('UniversalTime')))
g('graphics_flasher', 'StrobeFlasher', InputTime='GfxLightTime.Output', Function='DoublePulse', Period=2.0)
g('graphics_product', 'StrobeSwitched', Input0='GfxStrobeLight.Output', Input1='StrobeFlasher.Output')
g('graphics_product', 'FormationLightScaled', Input0='GfxFormationLight.Output', Input1='0.08')
# navigation lights: five positions of the NAV knob (DCS arg 715 has 5 detents; the mod drew no lights from it):
# OFF / DIM / MED / BRT / FLASH, from the F/A-18 position-light knob (0..1, 21 steps) - steady brightness levels and
# a 1 s on/off flash, gated by power and the exterior lights master (the F/A-18 product of the three, > 0)
NAV_STEPS = [0.125, 0.375, 0.625, 0.875]
g('graphics_input', 'GfxNavKnob', InputID=('uint32', published('PositionLightBrightnessKnob')))
steps = lambda levels: ' (0.0 %g) ' % levels[0] + ' '.join('(%.4f %g) (%.4f %g)' % (b_ - 1e-4, levels[i], b_, levels[i + 1])
                                                    for i, b_ in enumerate(NAV_STEPS)) + ' (1.0 %g) ' % levels[-1]
# (a graphics_multiplexer would select by uint32 references - those may point into the dynamics list: sums instead)
g('graphics_linear_interpolation', 'NavSteady', Input='GfxNavKnob.Output', Map=steps([0.0, 0.25, 0.6, 1.0, 0.0]))
g('graphics_linear_interpolation', 'NavFlashSelect', Input='GfxNavKnob.Output', Map=steps([0.0, 0.0, 0.0, 0.0, 1.0]))
g('graphics_flasher', 'NavFlasher', InputTime='GfxLightTime.Output', Function='Rectangle', Period=1.0)
g('graphics_product', 'NavFlash', Input0='NavFlashSelect.Output', Input1='NavFlasher.Output')
g('graphics_mix', 'NavLevel', Input0='NavSteady.Output', Input1='NavFlash.Output', Weight0=1.0, Weight1=1.0)
g('graphics_linear_interpolation', 'NavPowered', Input='GfxPositionLight.Output', Map=' (0.0 0.0) (0.01 1.0) (1.0 1.0) ')
g('graphics_product', 'NavLights', Input0='NavLevel.Output', Input1='NavPowered.Output')
# gear position lights (landing gear panel, user 2026-11-04): NOSE / LEFT / RIGHT green while that gear is down and
# locked (the donor's per-gear signals), on DC power; dark in transit and up
# Brightness as the stock F/A-18's gear annunciators (user: the first build, colour x 1.6, was too dim - the Hornet's are
# (200 900 100) x AnnunciatorBrightness = DC x its day/night dimmer, and light with the annunciator test)
# (2026-11-06, user) yellow while that gear moves (neither down and locked nor up and locked), green once down and
# locked, dark when up. Two bodies of the same lens: the green annunciator (as before, with the lamp test) and an amber
# one, the green hidden while the gear moves, the amber hidden otherwise (the first try, graphics_multi_color with
# red / green parts, lit red: it picks a colour, it does not mix)
for gear in ('Nose', 'Left', 'Right'):
    obj(dyn, 'product', 'F22Gear%sLamp' % gear, anchor,
        Inputs=' %sGearDownAndLocked.Output DCBusEssentialOn.Output ' % gear)
    obj(dyn, 'logic_or', 'F22Gear%sLocked' % gear, anchor, Inputs=' %sGearDownAndLocked.Output %sGearUpAndLocked.Output ' % (gear, gear))
    obj(dyn, 'logic_invert', 'F22Gear%sMoving' % gear, anchor, Input='F22Gear%sLocked.Output' % gear)
    obj(dyn, 'logic_invert', 'F22Gear%sNotMoving' % gear, anchor, Input='F22Gear%sMoving.Output' % gear)
    obj(dyn, 'product', 'F22Gear%sAmber' % gear, anchor, Inputs=' F22Gear%sMoving.Output DCBusEssentialOn.Output ' % gear)
    for sig in ('Amber', 'Moving', 'NotMoving'):
        g('graphics_input', 'GfxGear%s%s' % (gear, sig), InputID=('uint32', published('F22Gear%s%s' % (gear, sig))))
    g('graphics_input', 'GfxGear%sLamp' % gear, InputID=('uint32', published('F22Gear%sLamp' % gear)))
# the gear handle's wheel glows red while any leg is in transit (user 2026-11-16, as the F/A-18's handle light): a lamp
# copy of the wheel on the handle (ac _gear_handle_light), hidden while dark; on the DC essential bus as the plates
obj(dyn, 'maximum', 'F22GearAnyMoving', anchor, Inputs=' F22GearNoseMoving.Output F22GearLeftMoving.Output F22GearRightMoving.Output ')
obj(dyn, 'product', 'F22GearHandleLight', anchor, Inputs=' F22GearAnyMoving.Output DCBusEssentialOn.Output ')
obj(dyn, 'logic_invert', 'F22GearHandleDark', anchor, Input='F22GearHandleLight.Output')
for sig in ('Light', 'Dark'):
    g('graphics_input', 'GfxGearHandle' + sig, InputID=('uint32', published('F22GearHandle' + sig)))
g('graphics_input_color', 'F22GearIndicatorColor', InputID=('uint32', published('AnnunciatorBrightness')),
  Color=('tmvector3d', ' 200.0 900.0 100.0 '))
g('graphics_input', 'GfxF22AnnunciatorTest', InputID=('uint32', published('AnnunciatorTestOn')))
# BATT: amber (a caution, the Hornet's yellow annunciators are 900 600 0 class), the same dimmer and test
g('graphics_input_color', 'F22CautionIndicatorColor', InputID=('uint32', published('AnnunciatorBrightness')),
  Color=('tmvector3d', ' 900.0 520.0 40.0 '))
g('graphics_input', 'GfxBattLampLamp', InputID=('uint32', published('F22OnBattery')))
GEAR_LAMPS = {'GearNose': 'F22GearIndicatorColor', 'GearLeft': 'F22GearIndicatorColor',
              'GearRight': 'F22GearIndicatorColor', 'BattLamp': 'F22CautionIndicatorColor'}
LAMP_SWITCH = {'Formation': 'FormationLightScaled', 'Landing': 'GfxLandingLight', 'Taxi': 'GfxTaxiLight',
               'GearHandle': 'GfxGearHandleLight'}
# (GearHandle: 900, the annunciators' scale, burnt the wheel out to a pink blob - user 2026-11-17: far too bright)
LAMP_GAIN = {'Formation': 1.0, 'Landing': 6.0, 'Taxi': 6.0, 'GearHandle': 1.5}
# ('__K<body>' / '__B<body>': a lamp on a breakable part, kept on the fuselage / flying with the body - the swap is
# breakage_f22.damage_graphics')
lamp_keys = sorted({re.split('__[KB]', p.split('__L')[-1] if '__L' in p else p[2:])[0] for p in list(parts) + list(anim)
                    if p.startswith('L_') or '__L' in p})
for key in lamp_keys:
    if key in ('GearNoseAmber', 'GearLeftAmber', 'GearRightAmber'):        # their own copies of the plates
        g('graphics_annunciator_color', 'Lamp%sColor' % key, Input='Gfx%s.Output' % key,
          InputColor=('tmvector3d', 'F22CautionIndicatorColor.Output'))
        continue
    if key in GEAR_LAMPS:
        # (the donor writes InputColor with the tmvector3d tag although it names an output)
        g('graphics_annunciator_color', 'Lamp%sColor' % key, Input='Gfx%sLamp.Output' % key,
          InputColor=('tmvector3d', GEAR_LAMPS[key] + '.Output'), InputTest='GfxF22AnnunciatorTest.Output')
        continue
    g('graphics_color', 'Lamp%sColor' % key, Input=LAMP_SWITCH[key] + '.Output',
      Color=('tmvector3d', ' %s ' % fmt([c * LAMP_GAIN[key] for c in C.LAMP_COLOURS[key]])))
for pname in sorted(parts):
    if pname.startswith('L_'):
        key = re.split('__[KB]', pname[2:])[0]
        if key in ('GearNose', 'GearLeft', 'GearRight'):
            g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, **body('Fuselage'),
              InputLuminance='Lamp%sColor.Output' % key, InputHide='Gfx%sMoving.Output' % key)
            continue
        if key in ('GearNoseAmber', 'GearLeftAmber', 'GearRightAmber'):
            g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, **body('Fuselage'),
              InputLuminance='Lamp%sColor.Output' % key, InputHide='Gfx%sNotMoving.Output' % key[:-5])
            continue
        g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, **body('Fuselage'),
          InputLuminance='Lamp%sColor.Output' % key)
for n in G:
    if n.type == 'rigidbodygraphics' and '__L' in n.name:
        n.children.append(tmd.Node('string8', 'InputLuminance', 'Lamp%sColor.Output' % re.split('__[KB]', n.name.split('__L')[1])[0]))
        if n.name.endswith('__LGearHandle'):
            n.children.append(tmd.Node('string8', 'InputHide', 'GfxGearHandleDark.Output'))
# ---- cockpit night lighting: the F-22 INTERIOR LIGHTS panel (left console). Every interior material has a lighting
# map (export_parts.py, ac_f22.py LABEL_ILLUMINATION): red = flood (FLOOD knob, F/A-18 FloodLightBrightness), green =
# side-console lettering (CONSOLE, ConsoleBrightness), blue = instrument panel and ICP key lettering (INST PNL,
# PanelLightBrightness); each on DC power as the Hornet's. NVIS green lettering, dim greenish flood on the panels only
# (the first build's (0.8 1.0 0.85) on every texture lit the cockpit as by day). The game's own
# cockpit-lighting command (Controls.Lighting.*) sets the same knobs. Flood since 2026-10-22: baked lamp light on the
# side consoles only (ac BAKE_FLOOD) at the F/A-18's strength - its flood colours are 2.9 / 2.3 / 1.4 (orange) and
# 0 / 1.4 / 1.4 (blue); ours (0.28 0.38 0.3) lit nearly nothing at full FLOOD (user test)
for src, name, col in (('FloodLightBrightness', 'CockpitFlood', (1.9, 2.5, 2.0)),
                       ('ConsoleBrightness', 'ConsoleLettering', (0.5, 1.6, 0.6)),
                       ('PanelLightBrightness', 'PanelLettering', (0.5, 1.6, 0.6))):
    g('graphics_input', 'Gfx' + name, InputID=('uint32', published(src)))
    g('graphics_color', name + 'Color', Input='Gfx%s.Output' % name, Color=('tmvector3d', ' %s ' % fmt(col)))
for n in G:
    if n.type == 'rigidbodygraphics' and (n.name == 'Fuselage' or n.name.startswith(('A_', 'K_', 'P_'))) and '__L' not in n.name:
        for k, name in enumerate(('CockpitFlood', 'ConsoleLettering', 'PanelLettering')):
            n.children.append(tmd.Node('string8', 'InputIllumination%d' % k, name + 'Color.Output'))
# the panel's MFD knob dims all the MFDs (the Hornet's DDIs and MPCD each had their own; their bezel knobs are not
# clickable on the F-22)
for name, own in (('DDIRightBrightness', 'RightMFDBrightness'), ('DDILowerBrightness', 'LowerMFDBrightness'),
                  ('MPCDBrightness', 'MPCDBrightnessSetting')):
    assert own + '.Output' in D[name].get('Inputs'), name
    setv(D[name], 'Inputs', D[name].get('Inputs').replace(own + '.Output', 'LeftMFDBrightness.Output'))
# air refuelling receptacle light (AAR LIGHT knob, door open, DC power): a soft white glow in the receptacle
g('graphics_input', 'GfxAARLight', InputID=('uint32', published('F22AARLight')))
g('graphics_pointlight', 'LightAARReceptacle', **body('Fuselage'), R0=[1.307, 0.0, 0.84], X0=[0.0, 0.0, 1.0],
  Color=('tmvector3d', ' 1.0 0.97 0.9 '), Brightness=2.0, Size=0.06, ConeCenter=0.0, ConeCutoff=-0.5,
  InputModulation='GfxAARLight.Output')
# (name, switch, colour, position, direction, sprite size, sprite brightness, cone brightness, cone centre, cutoff)
RED, GREEN, HEAD = (1.0, 0.3, 0.1, 1.0), (0.1, 1.0, 0.3, 1.0), (1.0, 0.92, 0.8, 1.0)
LIGHTS = [
    ('NavRed', 'NavLights', RED, [-1.985, 6.223, 0.275], [0.55, 0.83, 0.0], 0.03, 6.0, 0.1, 0.72, 0.23),
    ('NavGreen', 'NavLights', GREEN, [-1.985, -6.223, 0.275], [0.55, -0.83, 0.0], 0.03, 6.0, 0.1, 0.72, 0.23),
    ('AntiCollisionLeft', 'StrobeSwitched', RED, [-1.985, 6.243, 0.285], [0.0, 1.0, 0.0], 0.04, 25.0, 0.3, 0.5, -0.3),
    ('AntiCollisionRight', 'StrobeSwitched', RED, [-1.985, -6.243, 0.285], [0.0, -1.0, 0.0], 0.04, 25.0, 0.3, 0.5, -0.3),
    ('Landing', 'GfxLandingLight', HEAD, [5.88, -0.105, -0.805], [0.982, 0.0, -0.19], 0.12, 1.5, 45.0, 0.999, 0.95),
    ('Taxi', 'GfxTaxiLight', HEAD, [5.90, 0.09, -0.78], [0.9998, 0.0, -0.02], 0.12, 1.5, 20.0, 0.995, 0.93),
]
for name, sw, col, r0, x0, size, sprite, cone, centre, cutoff in LIGHTS:
    g('graphics_pointlight', 'Light' + name, **body('Fuselage'), R0=r0, X0=x0, Color=('tmvector3d', ' %s ' % fmt(col)),
      Brightness=float(sprite), Size=size, ConeCenter=centre, ConeCutoff=cutoff, InputModulation=sw + '.Output')
    if cone:
        g('graphics_conelight', 'Light%sCone' % name, **body('Fuselage'), R0=r0, X0=x0,
          Color=('tmvector3d', ' %s ' % fmt(col)), Brightness=float(cone), ConeCenter=centre, ConeCutoff=cutoff,
          InputModulation=sw + '.Output')

# ---------------------------------------------------------------------------------------------- displays and HUD
# the stock F/A-18 display objects (they draw into the render targets display_light / hud_light, the textures of our
# display quads and HUD projection), copied with every graphics object they read (as make_su35.py with the F-15E)
f18_gfx = {o.name: o for o in gfx.children}
display_parts = {n: p['display'] for n, p in parts.items() if p.get('display')}
H = getattr(C, 'HUD_DONOR', None)
# donor display windows (the F-22's own windows are built below) + the up-front controller (ICP text), the IFEI
# (digit templates, clock) and the F/A-18 DDI pages the UFDs draw
roots = ['DisplayTexture', 'UFC', 'IFEI'] + [d['donor'] for d in display_parts.values()] + \
        [d['brightness'] for d in display_parts.values()]
if H and 'HudProjection' in parts:
    roots += [H['texture'], H['centre'], H['hud']]
NOT_GFX = ('PositionID', 'OrientationID', 'InputID', 'GeometryList')


def gfx_refs(node):
    for c in node.walk():
        if c is node or c.name in NOT_GFX or not c.leaf:
            continue
        for tok in re.findall(r'[A-Za-z_][A-Za-z0-9_]*', c.value or ''):
            yield tok


copied, todo = {}, list(roots)
f18_gfx['DisplayTexture'].set('RenderList', ' DisplayBackground ' + ' '.join(
    d['donor'] for d in display_parts.values() if d.get('texture', 'display') == 'display') + ' ')
while todo:
    n = todo.pop()
    if n in copied or n not in f18_gfx:
        continue
    copied[n] = f18_gfx[n].clone()
    todo.extend(t for t in gfx_refs(f18_gfx[n]) if t in f18_gfx and t not in copied)
clash = [n for n in copied if any(o.name == n for o in G)]
assert not clash, 'display objects clash with our graphics: %s' % clash
order = [o.name for o in gfx.children]
for n in sorted(copied, key=order.index):
    o = copied[n]
    for c in list(o.children):
        if c.name.startswith('InputIllumination'):        # F/A-18 flood light colours (not copied)
            o.children.remove(c)
    if o.find('GeometryList') is not None and o.type != 'graphics_hud':
        print('WARNING copied display object %s draws F/A-18 geometry %s' % (n, o.get('GeometryList')))
    G.append(o)
if H and 'HudProjection' in parts:
    copied[H['hud']].set('GeometryList', ' HudProjection ')
    # the F/A-18 HUD symbology window (graphics_animation_display) is drawn only while its R0 is in view: at the
    # F/A-18's HUD (x 5.96, behind the F-22 seat) the HUD stayed empty
    hud = parts['HudProjection']['hud']
    # smaller symbology (scaled about the render target centre, the boresight stays) so all of it fits the F-22
    # combiner: at the F/A-18 scale the side boxes and the pitch ladder ran past the glass (first test)
    k = getattr(C, 'HUD_SCALE', 1.0)
    if k != 1.0:
        tp, ts = vec(copied[H['centre']].get('TargetPosition')), vec(copied[H['centre']].get('TargetSize'))
        sc = vec(copied[H['centre']].get('TargetScale'))[0] / 2.0
        copied[H['centre']].set('TargetPosition', ' %d %d ' % tuple(round(sc - (sc - p_) * k) for p_ in tp), 'tmvector2d')
        copied[H['centre']].set('TargetSize', ' %d %d ' % tuple(round(t * k) for t in ts), 'tmvector2d')
    copied[H['centre']].set('R0', ' ' + fmt(hud['centre']) + ' ', 'tmvector3d')
    copied[H['centre']].set('Radius', '%.4f' % hud['radius'], 'float64')
    g('rigidbodygraphics', 'HudCombiner', GeometryList=' HudCombiner ', **body('Fuselage'))
    # the HUD at full brightness looked about half as bright as the stock F/A-18's by day (user, 2026-10-22; a
    # brightness above 1 is clamped): the collimated projection drawn twice - the HUD light adds up on the scene
    # (one geometry in two graphics objects stops the model from loading: each layer has its own, ac HUD_LAYERS)
    for k in range(2, getattr(C, 'HUD_LAYERS', 1) + 1):
        hud_k = copied[H['hud']].clone()
        hud_k.name = H['hud'] + str(k)
        hud_k.set('GeometryList', ' HudProjection%d ' % k)
        G.append(hud_k)
# ---- F-22 screens: graphics (second render target display2_light, atlas units 1024 = 2048 px, y up)
# lower SMFD: the right DDI's graphics cloned (its pages are shared), drawn at the left DDI's place of the new atlas
lower_gfx = [clone_lower(copied[n]) for n in sorted(copied, key=order.index) if LOWER_PAT.search(n)]
G.extend(lower_gfx)
copied.update({o.name: o for o in lower_gfx})
copied['DDILower'].set('TargetPosition', ' 18 614 ', 'tmvector2d')
for n in ('UFDBrightness', 'ICPBrightness'):
    b_ = copied['DDIRightBrightness'].clone()
    b_.name = n
    # through an `output` object: read directly, the product gave the graphics 0 - UFDs and ICP stayed black
    b_.set('InputID', published('UFDBrightnessValue' if n == 'UFDBrightness' else 'ICPBrightnessValue'), 'uint32')
    G.append(b_)


def window(name, d, render, pos=(0, 0), size=(1024, 1024)):
    """Display window drawing into the atlas (pos / size in atlas units); d = the display quad it shows (the window
    renders only while that screen is in view). A window draws one item (first test: only the first label of each
    UFD showed) - several go into a render list, as the F/A-18's UFC and IFEI."""
    if len(render) > 1:
        g('graphics_animation_render_list', name + 'Items', RenderList=' %s ' % ' '.join(render))
        render = [name + 'Items']
    return g('graphics_animation_display', name, **body('Fuselage'), R0=list(d['centre']), Radius=float(d['radius']),
             TargetPosition=('tmvector2d', ' %d %d ' % pos), TargetSize=('tmvector2d', ' %d %d ' % size),
             TargetScale=('tmvector2d', ' 1024 1024 '), InputDisplay='0.0', RenderList=' %s ' % ' '.join(render))


def place_copy(src, name, **fields):
    o = copied[src].clone()
    o.name = name
    for k, v in fields.items():
        t = {'Position': 'tmvector2f', 'TargetPosition': 'tmvector2d', 'Scaling': 'float64', 'FontSize': 'float64',
             'Stride': 'float64', 'Digits': 'int32', 'Length': 'uint', 'FontID': 'uint',
             'LeftJustified': 'bool', 'Color': 'tmvector4f'}.get(k, 'string8')
        o.set(k, v, t)
    G.append(o)
    return name


# the DDI font (fontdisplay; 2 = the UFC's segments); character stride 0.8 x size (0.625 let the letters overlap)
UFD_FONT = dict(FontID='0', FontSize=20.0, Stride=16.0)


def text_out(name, src):
    """dynamics text value -> output_text -> graphics_input_text; returns the graphics input name."""
    out = 'F22Text' + name
    if out not in D:
        D[out] = obj(dyn, 'output_text', out, anchor, Input=src)
        g('graphics_input_text', out, InputID=('uint32', out + '.Output'))
    return out + '.Output'


def label(text, pos, size=20.0, color=None):
    """Static text in the DDI font (green, or the given RGBA)."""
    key = re.sub(r'[^A-Za-z0-9]', '', text)
    extra = {'Color': ' %g %g %g %g ' % color} if color else {}
    return place_copy('UpFrontControllerLine0', 'F22Label%s_%d_%d' % (key, pos[0], pos[1]),
                      Input=text_out(key, ufc_label(text)), Position=' %d %d ' % pos, Length=str(len(text)),
                      **dict(UFD_FONT, FontSize=size, Stride=size * 0.9), **extra)


def dyn_value(gname):
    """The dynamics value an F/A-18 graphics input shows: (dynamics output, scale, offset)."""
    o = copied[gname]
    if o.type == 'graphics_mapping_linear':
        src, k, off = dyn_value(o.get('Input').split('.')[0])
        k2, off2 = float(o.get('Scaling', '1')), float(o.get('Offset', '0'))
        return src, k * k2, off * k2 + off2
    d_ = o.get('InputID').split('.')[0]
    if D[d_].type == 'output':                       # terminal: dynamics read what it forwards
        return D[d_].get('Input').strip(), 1.0, 0.0
    return d_ + '.Output', 1.0, 0.0


def number(gname, key, pos, scale=1.0, n=5):
    """Live number, right-aligned in an n-character field ending at pos x + n x stride."""
    src, k, off = dyn_value(gname)
    return number_of(src, key, pos, k * scale, off * scale, n)


def number_of(src, key, pos, scale=1.0, offset=0.0, n=5, font=UFD_FONT):
    """number() of a dynamics output: src x scale + offset."""
    obj(dyn, 'mixlinear', 'UFDValue' + key, anchor, Input0=src, Input1='1.0', Weight0=scale, Weight1=offset)
    obj(dyn, 'int_to_text', 'UFDNumber' + key, anchor, Input='UFDValue%s.Output' % key)
    return place_copy('UpFrontControllerLine0', 'UFDNumber' + key, Input=text_out(key, 'UFDNumber%s.Output' % key),
                      Position=' %d %d ' % pos, Length=str(n), LeftJustified='false', **font)


screens = {n: d for n, d in display_parts.items() if d.get('texture') == 'display2'}
icp = [d for n, d in sorted(screens.items()) if n.startswith('DisplayICP') and n != 'DisplayICPScratch']
icp_c = [sum(d['centre'][k] for d in icp) / len(icp) for k in range(3)]
# (the window's radius is also its zoom-click area: the five windows only, the option buttons beside them stay
# clickable)
icp_d = dict(centre=icp_c, radius=max(math.dist(icp_c, d['centre']) + d['radius'] for d in icp))
# ICP: the UFC option lines in the five windows (line k at atlas y 244 - 56 k, 215 x 40 units each), the scratchpad
# Measured on screenshots (2026-11-01): every line had no gap under the glyphs. The glyph runs from ~0.22 x size under Position to ~0.96 x size over it (screens 40 units high, top gap 6.25 at 30 / 249):
# at size 30 from 249 it went under the window's 244 and lost its bottom. Size 29 from 253: 246.6 .. 280.8
icp_lines = [place_copy('UpFrontControllerLine%d' % k, 'ICPLine%d' % k, Position=' 22 %d ' % (253 - 56 * k), FontSize=29.0)
             for k in range(5)]
window('ICPLines', icp_d, icp_lines)
window('ICPScratch', screens['DisplayICPScratch'], [
    # (size 26 on the stock stride 22 made the digits run into each other: a glyph is ~0.84 x size wide). A glyph is centred on its cell: measured on screenshots, the overlay at 34 starts
    # at 22.8, so at 21 its first letter was cut by the window's 15 (ON, user 2026-11-01); digits at 34 with size 26 end 3.5 units short of the window's 245
    place_copy('UpFrontControllerScratchPad', 'ICPScratchPad', Position=' 24 306 ', FontSize=22.0, Stride=23.0),
    place_copy('UpFrontControllerScratchPadOverlay', 'ICPScratchPadOverlay', Position=' 30 304 ')])
# left UFD (atlas 430..800 x 630..915): engines left / right (RPM %, EGT degC, fuel flow 100 lb/h, nozzle %, oil psi
# - the F/A-18 IFEI's values, as text: its LCD digits drew blue cells and cut the third digit) above the cautions
# header: each engine's state in place of the plain L / R (2026-11-05, user: on the battery the UFDs are all that is
# left, and the engines' state could not be told) - RUN, OFF, MOT (starter, no fuel), STRT (starting), WMIL
# (windmilling: stopped, turned by the airflow), FADC (stopped by its FADEC); F22Eng<n>StageW, ENG page section
for k in (1, 2):
    obj(dyn, 'multiplexer_text', 'F22Eng%dShortText' % k, anchor, InputSelect='F22Eng%dStageW.Output' % k,
        Inputs=' %s ' % ' '.join(ufc_label(('L ' if k == 1 else 'R ') + t) for t in ('OFF', 'MOT', 'STRT', 'RUN', 'FADC', 'WMIL')))
ufd_l = [label('ENG', (440, 890))] + [
    place_copy('UpFrontControllerLine0', 'F22Eng%dShortItem' % k, Input=text_out('Eng%dShort' % k, 'F22Eng%dShortText.Output' % k),
               Position=' %d 890 ' % x, Length='6', LeftJustified='false', **UFD_FONT) for k, x in ((1, 544), (2, 649))]
for row, (text, src, scale) in enumerate([('RPM', 'N2', 100.0), ('EGT', 'TemperatureInCentigrade', 1.0),
                                          ('FF', 'FuelFlow', 7936.641438), ('NOZ', 'NozzlePosition', 100.0),
                                          ('OIL', 'OilPressure', 0.000145037681)]):
    y = 866 - 23 * row
    ufd_l.append(label(text, (440, y)))
    for side, x in ((1, 560), (2, 665)):
        if src == 'N2':       # RPM of the gearbox: the engine's N2 or, stopped, the windmill estimate the pumps run on
            ufd_l.append(number_of('F22Eng%dGearboxN2.Output' % side, 'Engine%d%s' % (side, text), (x, y), scale, 0.0, 5))
        else:
            ufd_l.append(number('Engine%d%s' % (side, src), 'Engine%d%s' % (side, text), (x, y), scale, 5))
# ICAWS (F-22 integrated caution / advisory / warning): the F/A-18 CAS conditions with F-22 texts, amber, each in its
# own slot, shown while active (the F/A-18 CAS renderer drew nothing outside its DDI - not even FUEL LO at 0 kg)
AMBER = (1.0, 0.75, 0.0, 1.0)
# (+ the F-22 / DCS mod UFD advisories the Hornet's CAS lacks: speed brake out, flaps down, parking brake set at
# any thrust - the Hornet's PARK BRK only came with takeoff thrust)
obj(dyn, 'logic_greater', 'F22SpeedBrakeOut', anchor, Input0='ServoAirBrake.Output', Input1='0.05')
obj(dyn, 'logic_greater', 'F22FlapsDown', anchor, Input0='FlapsSelector.Output', Input1='0.25')
# the ICAWS FLAPS line: flaps down with the gear up - ALT FLAPS (gear down, the flaps follow the gear handle and the
# line only repeated the gear lamps, user 2026-11-06: clutter)
obj(dyn, 'logic_invert', 'F22GearNotDown', anchor, Input='AnyGearDown.Output')
obj(dyn, 'logic_and', 'F22FlapsAlt', anchor, Inputs=' F22FlapsDown.Output F22GearNotDown.Output ')
# Voice (our choice, nothing is published of the F-22's). The airliners' terrain_warning was tried first (2026-11-01) and rejected: its civil envelope spoke as soon as the nose went down, out of
# step with the HUD's arrow. PULL UP now comes from what the arrow reads, TerrainRadar.OutputPullUpCue: 0 / 1 from the closing speed against the room to turn at this speed (game code).
# Spoken from the first moment of the cue and repeated while it lasts, the words on the ICAWS (none on the HUD: the arrow is enough, user 2026-11-01). Voices: make_cockpit_sounds.py, macOS Samantha,
# personal use, to be replaced before any publication. The VOX knob's OFF mutes them. (Heights called out with the gear down, as the airliners', tried and taken out: fighters do not have it)
# Volume: the RADIO VOL panel's VOX knob only (user 2026-11-07: the ICP thumbwheel, this knob and the SYS VOX key did
# the same thing; the ICP wheel and the key are gone). 0 .. 1 in 20 clicks of 5 %, OFF at 0 mutes the voice and the
# tones. Audio taper: equal clicks sound equally far apart - the gain falls 30 dB from the top to the first click
# (1.5 x 10^(-1.5 (1 - p)); the linear 0 .. 1.5 of the first build changed little over its upper half, user: "only on /
# off"); 0.9 at start = gain 1.06, the level accepted by ear (1.0 before). Each click plays a short 1 kHz tone at the
# new level, so the level can be set by ear without waiting for a warning.
obj(dyn, 'input_default', 'F22VoiceVolume', anchor, Message='Voice.Volume', Range=' 0.0 1.0 ', Positions=('uint', '21'), Value=0.9)
obj(dyn, 'logic_greater', 'F22VoiceOn', anchor, Input0='F22VoiceVolume.Output', Input1='0.01')
obj(dyn, 'linear_interpolation', 'F22VoiceGain', anchor, Input='F22VoiceVolume.Output',
    Map=' (0.0 0.0) ' + ' '.join('(%.2f %.4f)' % (k / 20.0, 1.5 * 10 ** (-1.5 * (1 - k / 20.0))) for k in range(1, 21)) + ' ')
obj(dyn, 'product', 'F22AudioLevel', anchor, Inputs=' F22VoiceGain.Output F22ACPSwitch.Output ICSOn.Output ')    # AUX/ACP off or no intercom power (AC): silent
obj(snd, 'soundinput', 'F22VoiceLevel', InputID=('uint32', published('F22AudioLevel')))
obj(dyn, 'servolinear', 'F22VoiceVolumeLag', anchor, Input='F22VoiceVolume.Output', OutputSpeed=0.5,
    InputPosition=('float64array', ' 0.0 1.0 '), OutputPosition=('float64array', ' 0.0 1.0 '), Position=0.9)
obj(dyn, 'mixlinear', 'F22VoiceVolumeStep', anchor, Input0='F22VoiceVolume.Output', Input1='F22VoiceVolumeLag.Output', Weight0=1.0, Weight1=-1.0)
obj(dyn, 'logic_greater', 'F22VoiceVolumeUp', anchor, Input0='F22VoiceVolumeStep.Output', Input1='0.01')
obj(dyn, 'logic_greater', 'F22VoiceVolumeDown', anchor, Input0='-0.01', Input1='F22VoiceVolumeStep.Output')
obj(dyn, 'logic_or', 'F22VoiceVolumeClick', anchor, Inputs=' F22VoiceVolumeUp.Output F22VoiceVolumeDown.Output ')
IRS = 'InertialReferenceSystem.Output'
obj(dyn, 'logic_greater', 'F22PullUp', anchor, Input0='TerrainRadar.OutputPullUpCue', Input1='0.5')
obj(dyn, 'integral_clamped', 'F22PullUpTime', anchor, Input='F22PullUp.Output', Range=' 0.0 100000.0 ', Value=0.0)
obj(dyn, 'event_edge_falling', 'F22PullUpEnd', anchor, Input='F22PullUp.Output', Events=' F22PullUpTime.Reset ', Threshold=0.5)
obj(dyn, 'clamp_cyclic', 'F22PullUpPhase', anchor, Input='F22PullUpTime.Output', Range=('string8', ' 0.0 1.6 '))     # the phrase takes about 1.3 s
obj(dyn, 'logic_greater', 'F22PullUpGate', anchor, Input0='0.8', Input1='F22PullUpPhase.Output')
obj(dyn, 'logic_and', 'F22VoicePullUp', anchor, Inputs=' F22PullUp.Output F22PullUpGate.Output F22VoiceOn.Output ')

def voice(name, src, wav, volume, pitch='1.0'):
    """Cockpit voice as in the stock aircraft: fires on the rising edge of src, spoken at the pilot's head."""
    if not failures_f22._have_sound(wav[:-4]):       # a release without the voices (make_release.py): no sound object
        return
    obj(snd, 'soundinput', name, InputID=('uint32', src))
    obj(snd, 'soundmultiply', name + 'Volume0', Input0=name + '.Output', Input1='%g' % volume)
    obj(snd, 'soundmultiply', name + 'Volume', Input0=name + 'Volume0.Output', Input1='F22VoiceLevel.Output')
    obj(snd, 'soundsingle', name + 'Sound', PositionID=('uint32', 'Fuselage.R'), OrientationID=('uint32', 'Fuselage.Q'), VelocityID=('uint32', 'Fuselage.V'),
        InputTrigger=name + '.Output', InputVolume=name + 'Volume.Output', InputPitch=pitch, SoundFile=wav, Threshold=0.9, Direction=('uint32', '1'),
        R0=('tmvector3d', ' 7.15 0.0 1.35 '), Radius=0.5, Range=('float64', '4.0'), External=('bool', 'false'))


voice('F22VoicePullUpIn', published('F22VoicePullUp'), 'voice_pullup.wav', 3.0)
voice('F22VoiceVolumeToneIn', published('F22VoiceVolumeClick'), 'vox_tone.wav', 1.5)     # the VOX knob's click tone
# ALTITUDE once when going down through a floor set on the ICP (ALT, ALOW), as the Hornet's and the F-16's low altitude voice; not with the gear down, or it would speak at every landing. The floor is
# our choice, 200 ft at start. The 5 s hold keeps it from repeating over rough ground. OVER G and BINGO on their ICAWS conditions
obj(dyn, 'variable', 'F22AltFloor', anchor, Value='60.96')
obj(dyn, 'logic_greater', 'F22AltBelowFloor', anchor, Input0='F22AltFloor.Output', Input1='RadarAltimeter.Output')
obj(dyn, 'logic_invert', 'F22VoiceNoPullUp', anchor, Input='F22PullUp.Output')
obj(dyn, 'logic_and', 'F22AltWarning', anchor, Inputs=' F22AltBelowFloor.Output F22GcasSinking.Output NoGearDown.Output F22AtAirborne.Output F22VoiceNoPullUp.Output ')
obj(dyn, 'logic_confirm_delay', 'F22AltWarningHeld', anchor, Input='F22AltWarning.Output', TimeUp=0.1, TimeDown=5.0, Threshold=0.5)
obj(dyn, 'product', 'F22VoiceAltitude', anchor, Inputs=' F22AltWarningHeld.Output F22VoiceOn.Output ')
voice('F22VoiceAltitudeIn', published('F22VoiceAltitude'), 'voice_altitude.wav', 3.0)
obj(dyn, 'logic_and', 'F22VoiceBingo', anchor, Inputs=' BingoFuelReached.Output F22AtAirborne.Output F22VoiceOn.Output ')
voice('F22VoiceBingoIn', published('F22VoiceBingo'), 'voice_bingo.wav', 3.0)
obj(dyn, 'logic_confirm_delay', 'F22OverGHeld', anchor, Input='F22OverG.Output', TimeUp=0.01, TimeDown=4.0, Threshold=0.5)
obj(dyn, 'product', 'F22VoiceOverG', anchor, Inputs=' F22OverGHeld.Output F22VoiceOn.Output ')
voice('F22VoiceOverGIn', published('F22VoiceOverG'), 'voice_overg.wav', 3.0)
# A tone when Auto-GCAS takes the stick, once (user, 2026-11-01): the outer marker's dashes at twice the pitch, 800 Hz, four in a second, so that no new file is needed
obj(dyn, 'product', 'F22VoiceGcas', anchor, Inputs=' F22GcasActive.Output F22VoiceOn.Output ')
voice('F22VoiceGcasIn', published('F22VoiceGcas'), 'marker_outer.wav', 1.0, pitch='2.0')
# Marker beacons on the approach: the tone over each one (marker_receiver of the stock aircraft, which only light lamps with it; our tones). The receiver is real (game code: it looks for fixes
# named OM, MM, IM at the airports nearby), but no such beacon was met in Haugesund, Bergen or San Francisco (user, 2026-11-01). Tones made up from the radio height were tried and taken out:
# a beacon tells the place on the approach, the height is on the HUD anyway (user), so where the game has no beacon there is no tone
obj(dyn, 'logic_and', 'F22CNIMarker', anchor, Inputs=' ACBus2AOn.Output F22CNISwitch.Output ')         # CNI, on AC as the ILS
obj(dyn, 'marker_receiver', 'F22MarkerReceiver', anchor, Body='Fuselage', InputEnable='F22CNIMarker.Output')


def cockpit_loop(name, volume_src, pitch, wav):
    obj(snd, 'soundloop', name, PositionID=('uint32', 'Fuselage.R'), OrientationID=('uint32', 'Fuselage.Q'), VelocityID=('uint32', 'Fuselage.V'), InputVolume=volume_src, InputPitch=pitch,
        SoundFile=wav, R0=('tmvector3d', ' 7.15 0.0 1.35 '), Radius=0.5, Range=('float64', '4.0'), External=('bool', 'false'))


for key, wav in (('Outer', 'marker_outer'), ('Middle', 'marker_middle'), ('Inner', 'marker_inner')):
    obj(dyn, 'product', 'F22Marker' + key, anchor, Inputs=' F22MarkerReceiver.Output%s F22VoiceOn.Output ' % key)
    obj(snd, 'soundinput', 'F22Marker%sIn' % key, InputID=('uint32', published('F22Marker' + key)))
    obj(snd, 'soundmultiply', 'F22Marker%sVolume0' % key, Input0='F22Marker%sIn.Output' % key, Input1='0.5')
    obj(snd, 'soundmultiply', 'F22Marker%sVolume' % key, Input0='F22Marker%sVolume0.Output' % key, Input1='F22VoiceLevel.Output')
    cockpit_loop('F22Marker%sSound' % key, 'F22Marker%sVolume.Output' % key, '1.0', wav + '.wav')
# Air along the canopy, the user's idea, as the Concorde's wind loop but for a strong pressurised canopy: a quiet hiss by calibrated airspeed, so quieter high up at the same Mach, no whistle.
# Buffet near the limits: low rumble from angle of attack and g, fading out at low speed. Levels are in the configs, to be set by ear
obj(dyn, 'output', 'F22SoundCas', out_anchor, Input='AirDataComputer.OutputCalibratedAirspeed')
obj(dyn, 'linear_interpolation', 'F22BuffetAoa', anchor, Input='PitotTube.AngleOfAttack', Map=' (0.26 0.0) (0.44 0.5) (0.70 1.0) ')
obj(dyn, 'linear_interpolation', 'F22BuffetLoad', anchor, Input='Accelerometer.Acceleration', Map=' (58.9 0.0) (88.3 0.6) (107.9 1.0) ')
obj(dyn, 'maximum', 'F22BuffetAny', anchor, Inputs=' F22BuffetAoa.Output F22BuffetLoad.Output ')
obj(dyn, 'linear_interpolation', 'F22BuffetSpeed', anchor, Input='AirDataComputer.OutputCalibratedAirspeed', Map=' (30.0 0.0) (80.0 1.0) ')
obj(dyn, 'product', 'F22Buffet', anchor, Inputs=' F22BuffetAny.Output F22BuffetSpeed.Output ')
obj(snd, 'soundinput', 'F22FlowCas', InputID=('uint32', 'F22SoundCas.Output'))
obj(snd, 'soundmapping', 'F22FlowVolume', Input='F22FlowCas.Output', Map=' (0.0 0.0) (40.0 0.006) (100.0 0.025) (200.0 0.06) (350.0 0.105) (600.0 0.135) ')    # 0.3 x the first try: at 300-500 kt it was as loud as the engines (user)
obj(snd, 'soundmapping', 'F22FlowPitch', Input='F22FlowCas.Output', Map=' (0.0 0.7) (100.0 0.8) (300.0 1.1) (600.0 1.3) ')
cockpit_loop('F22FlowSound', 'F22FlowVolume.Output', 'F22FlowPitch.Output', 'flow_noise.wav')
obj(snd, 'soundinput', 'F22BuffetIn', InputID=('uint32', published('F22Buffet')))
obj(snd, 'soundmultiply', 'F22BuffetVolume', Input0='F22BuffetIn.Output', Input1='0.6')
# pitch 2.5: the file's 22-90 Hz could not be heard in the first test (small speakers do not reach that low, not confirmed), now about 55-225 Hz
cockpit_loop('F22BuffetSound', 'F22BuffetVolume.Output', '2.5', 'buffet.wav')
# Auto-GCAS (our choice, as on the F-16 and F-35; nothing is known of one on the F-22). The HUD arrow alone is too late for it: the game's cue gives one second before the point where a pilot
# with wings level must pull (terrain_radar, game code), and a second of delay on top lost the aircraft nearly every time, inverted always (user, 2026-11-01). So it works out the room it needs:
# from its own path (TerrainRadar.OutputDistance along the velocity, 0 = no ground within 20 s, x sine of the path = height) against the sink during the reaction and the roll to level, the sink
# gained while rolling (the laws keep +1 g, inverted that pushes down), the height lost in the pull V^2 / a x (1 - cos path), and 40 m. Times and speeds are estimates: roll ~150 deg/s (Hornet laws
# did ~250 deg/s), g onset 0.4 s. On a model at 90-300 m/s, path -3 .. -85 deg, bank 0 .. 180 deg the lowest point stayed over 40 m, and with a roll of 90 deg/s over 30 m; the terrain ahead in level flight is left to the arrow, which
# starts it at once. It rolls towards wings level and pulls by moving the stick inputs themselves, so that both the normal laws and DIRECT obey and the stick is seen to move. It ends when the
# danger has gone and the path points up, or at 15 deg up, or with a stick deflection over half, or the GCS button.
# Signs: x forward, y left, z up, a positive roll is the right wing down (InertialReferenceSystem QRate is + nose down, seen on the DIRECT loop); Controls.Roll.Input + is right, Pitch.Input - is a pull
PI = 3.14159265
obj(dyn, 'variable', 'F22GcasArmed', anchor, Value='1.0')
obj(dyn, 'logic_invert', 'F22GcasArmedNot', anchor, Input='F22GcasArmed.Output')
obj(dyn, 'event_value', 'F22GcasToggle', anchor, Input='F22GcasArmedNot.Output', Events=' F22GcasArmed.Set ')
obj(dyn, 'linear_interpolation', 'F22GcasPilotPitch', anchor, Input='ElevatorInput.Output', Map=' (-0.5 1.0) (-0.49 0.0) (0.49 0.0) (0.5 1.0) ')
obj(dyn, 'linear_interpolation', 'F22GcasPilotRoll', anchor, Input='AileronInput.Output', Map=' (-0.5 1.0) (-0.49 0.0) (0.49 0.0) (0.5 1.0) ')
obj(dyn, 'logic_or', 'F22GcasPilot', anchor, Inputs=' F22GcasPilotPitch.Output F22GcasPilotRoll.Output ')
obj(dyn, 'logic_invert', 'F22GcasPilotNot', anchor, Input='F22GcasPilot.Output')
obj(dyn, 'clamp_cyclic', 'F22GcasBank', anchor, Input='PhysicalAttitudeIndicator.BankAngle', Range=('string8', ' %.6f %.6f ' % (-PI, PI)))
obj(dyn, 'maximum', 'F22GcasSpeed', anchor, Inputs=' AirDataComputer.OutputTrueAirspeed 30.0 ')
obj(dyn, 'inverse', 'F22GcasPerSpeed', anchor, Input='F22GcasSpeed.Output')
obj(dyn, 'linear', 'F22GcasSink', anchor, Input=IRS + 'VerticalVelocity', Scaling=-1.0)
obj(dyn, 'product', 'F22GcasPathSine', anchor, Inputs=' F22GcasSink.Output F22GcasPerSpeed.Output ')
obj(dyn, 'product', 'F22GcasHeight', anchor, Inputs=' TerrainRadar.OutputDistance F22GcasPathSine.Output ')
obj(dyn, 'linear_interpolation', 'F22GcasTimeToPull', anchor, Input='F22GcasBank.Output', Map=' (-3.1416 2.1) (-2.09 1.7) (-1.05 1.2) (0.0 0.8) (1.05 1.2) (2.09 1.7) (3.1416 2.1) ')
obj(dyn, 'linear_interpolation', 'F22GcasRollSink', anchor, Input='F22GcasBank.Output', Map=' (-3.1416 30.0) (-1.57 9.0) (0.0 0.0) (1.57 9.0) (3.1416 30.0) ')
obj(dyn, 'linear_interpolation', 'F22GcasRollDrop', anchor, Input='F22GcasBank.Output', Map=' (-3.1416 28.0) (-1.57 8.0) (0.0 0.0) (1.57 8.0) (3.1416 28.0) ')
obj(dyn, 'product', 'F22GcasReactDrop', anchor, Inputs=' F22GcasSink.Output F22GcasTimeToPull.Output ')
obj(dyn, 'mixlinear', 'F22GcasSinkAtPull', anchor, Input0='F22GcasSink.Output', Input1='F22GcasRollSink.Output', Weight0=1.0, Weight1=1.0)
obj(dyn, 'product', 'F22GcasSineAtPull', anchor, Inputs=' F22GcasSinkAtPull.Output F22GcasPerSpeed.Output ')
obj(dyn, 'linear_interpolation', 'F22GcasCosLoss', anchor, Input='F22GcasSineAtPull.Output', Map=' (0.0 0.0) (0.2 0.0202) (0.4 0.0835) (0.6 0.2) (0.8 0.4) (1.0 1.0) ')
# V^2 / a, a = what the wing gives (1 g speed ~70 m/s) up to about 7 g on the stick
obj(dyn, 'linear_interpolation', 'F22GcasRadius', anchor, Input='F22GcasSpeed.Output', Map=' (50.0 833.0) (70.0 980.0) (100.0 833.0) (140.0 653.0) (170.0 602.0) (200.0 667.0) (250.0 1042.0) (300.0 1500.0) (400.0 2667.0) (600.0 6000.0) (800.0 10667.0) ')
obj(dyn, 'product', 'F22GcasPullDrop', anchor, Inputs=' F22GcasRadius.Output F22GcasCosLoss.Output ')
obj(dyn, 'sum', 'F22GcasRoomNeeded', anchor, Inputs=' F22GcasReactDrop.Output F22GcasRollDrop.Output F22GcasPullDrop.Output 40.0 ')
obj(dyn, 'logic_greater', 'F22GcasNoRoom', anchor, Input0='F22GcasRoomNeeded.Output', Input1='F22GcasHeight.Output')
obj(dyn, 'logic_greater', 'F22GcasGroundAhead', anchor, Input0='TerrainRadar.OutputDistance', Input1='1.0')
obj(dyn, 'logic_greater', 'F22GcasSinking', anchor, Input0='F22GcasSink.Output', Input1='3.0')
obj(dyn, 'logic_and', 'F22GcasPredicted', anchor, Inputs=' F22GcasNoRoom.Output F22GcasGroundAhead.Output F22GcasSinking.Output ')
obj(dyn, 'logic_greater', 'F22GcasGoingDown', anchor, Input0='0.0', Input1=IRS + 'FlightPathAngle')
obj(dyn, 'logic_and', 'F22GcasArrowDown', anchor, Inputs=' F22PullUp.Output F22GcasGoingDown.Output ')
obj(dyn, 'logic_or', 'F22GcasDanger', anchor, Inputs=' F22GcasPredicted.Output F22GcasArrowDown.Output ')
obj(dyn, 'logic_and', 'F22GcasStart', anchor, Inputs=' F22GcasDanger.Output F22GcasArmed.Output F22GcasPilotNot.Output NoGearDown.Output F22AtAirborne.Output INSOn.Output ')   # (INS on AC)
obj(dyn, 'variable', 'F22GcasActive', anchor, Value='0.0')
obj(dyn, 'event_value', 'F22GcasOn', anchor, Input='1.0', Events=' F22GcasActive.Set FlightController.DisconnectAutopilot ')
obj(dyn, 'event_value', 'F22GcasOff', anchor, Input='0.0', Events=' F22GcasActive.Set ')
obj(dyn, 'event_edge_rising', 'F22GcasStarted', anchor, Input='F22GcasStart.Output', Events=' F22GcasOn.Trigger ', Value=1.0, Threshold=0.5)
obj(dyn, 'logic_invert', 'F22GcasDangerNot', anchor, Input='F22GcasDanger.Output')
obj(dyn, 'logic_greater', 'F22GcasPathUp', anchor, Input0=IRS + 'FlightPathAngle', Input1='0.03')
obj(dyn, 'logic_greater', 'F22GcasPathWellUp', anchor, Input0=IRS + 'FlightPathAngle', Input1='0.26')
obj(dyn, 'logic_and', 'F22GcasClear', anchor, Inputs=' F22GcasDangerNot.Output F22GcasPathUp.Output ')
obj(dyn, 'logic_or', 'F22GcasEnd', anchor, Inputs=' F22GcasClear.Output F22GcasPathWellUp.Output F22GcasPilot.Output F22GcasArmedNot.Output AnyGearDown.Output OnGroundSensor.Output ')
obj(dyn, 'event_edge_rising', 'F22GcasEnded', anchor, Input='F22GcasEnd.Output', Events=' F22GcasOff.Trigger ', Value=1.0, Threshold=0.5)
obj(dyn, 'linear_interpolation', 'F22GcasRollCommand', anchor, Input='F22GcasBank.Output', Map=' (-1.2 1.0) (1.2 -1.0) ')
# ~7 g on the stick's scale of 9 g. No pull until the wings are within 60 deg of level: inverted, a pull goes down
obj(dyn, 'linear_interpolation', 'F22GcasPitchCommand', anchor, Input='F22GcasBank.Output', Map=' (-2.1 0.0) (-1.57 -0.4) (-1.05 -0.85) (1.05 -0.85) (1.57 -0.4) (2.1 0.0) ')
obj(dyn, 'servoclassic', 'F22GcasBlend', anchor, Input='F22GcasActive.Output', Speed=2.5, P0=0.0, P1=1.0, P2=0.0, P3=0.0, Position=0.0)
obj(dyn, 'linear', 'F22GcasKeep', anchor, Input='F22GcasBlend.Output', Scaling=-1.0, Offset=1.0)
for axis, stick, servo, cmd_ in (('Pitch', 'ElevatorInput', 'ServoElevatorStick', 'F22GcasPitchCommand'), ('Roll', 'AileronInput', 'ServoAileronStick', 'F22GcasRollCommand')):
    obj(dyn, 'product', 'F22Gcas%sPilotKept' % axis, anchor, Inputs=' %s.Output F22GcasKeep.Output ' % stick)
    obj(dyn, 'product', 'F22Gcas%sAuto' % axis, anchor, Inputs=' %s.Output F22GcasBlend.Output ' % cmd_)
    obj(dyn, 'mixlinear', 'F22Stick' + axis, anchor, Input0='F22Gcas%sPilotKept.Output' % axis, Input1='F22Gcas%sAuto.Output' % axis, Weight0=1.0, Weight1=1.0)
    setv(D[servo], 'Input', 'F22Stick%s.Output' % axis)
setv(D['FlightController'], 'InputElevator', 'F22StickPitch.Output')
setv(D['FlightController'], 'InputAileron', 'F22StickRoll.Output')
# Warnings. OVER G from 9.3 g or -3.3 g held 0.3 s (the laws limit at 9 g and peak a little over it; DIRECT goes to 16 g, the wings break at 13.5 g). AOA: over 40 deg in flight, our choice
obj(dyn, 'logic_greater', 'F22OverPositive', anchor, Input0='Accelerometer.Acceleration', Input1='%.2f' % (9.3 * 9.81))
obj(dyn, 'logic_greater', 'F22OverNegative', anchor, Input0='%.2f' % (-3.3 * 9.81), Input1='Accelerometer.Acceleration')
obj(dyn, 'logic_or', 'F22OverAny', anchor, Inputs=' F22OverPositive.Output F22OverNegative.Output ')
obj(dyn, 'logic_confirm_delay', 'F22OverG', anchor, Input='F22OverAny.Output', TimeUp=0.3, TimeDown=1.0, Threshold=0.5)
obj(dyn, 'logic_greater', 'F22AoaOver', anchor, Input0='PitotTube.AngleOfAttack', Input1='0.698')
obj(dyn, 'logic_greater', 'F22AoaFlying', anchor, Input0='AirDataComputer.OutputCalibratedAirspeed', Input1='25.0')
obj(dyn, 'logic_and', 'F22AoaHigh', anchor, Inputs=' F22AoaOver.Output F22AoaFlying.Output F22AtAirborne.Output ')
ICAWS = [('FUEL LOW', 'CautionFuelLow'), ('BINGO', 'BingoFuelReached'), ('L GEN', 'Engine1GeneratorCaution'),
         ('R GEN', 'Engine2GeneratorCaution'), ('PARK BRK', 'ParkingBrakeSet'), ('CANOPY', 'CanopyOpen'),
         ('SPD BRK', 'F22SpeedBrakeOut'), ('FLAPS', 'F22FlapsAlt'), ('AP OFF', 'CautionAutopilot'),
         ('ANTISKID', 'AntiSkidOff'), ('BAY OPEN', 'F22BayOpen'),
         ('BRK ACC', 'BrakePressureLow'), ('FCS', 'F22FcsIcaws'), ('PULL UP', 'F22PullUp'), ('OVER G', 'F22OverG'), ('AOA', 'F22AoaHigh'),
         ('GCAS', 'F22GcasActive'), ('A/T', 'F22AtActive'), ('FLCS BIT', 'F22BitRunning'), ('BIT PASS', 'F22BitPassShow'),
         ('HYD', 'F22HydLow')]     # (one slot for either system: an eighth row would fall below the left UFD, y 630)
# failures (FAIL page, failures_f22.py, 2026-11-09): their logic, and their ICAWS lines
failures_f22.dynamics(globals())
ICAWS += failures_f22.ICAWS
# master caution: the F-22 cockpit has no Hornet MASTER CAUTION lamp (the reset button seemed to do nothing), so an
# unacknowledged caution flashes on the ICAWS (the CAS flasher, 1 s) until the reset (left button under the left UFD,
# CAS.MasterCaution); the advisories (speed brake, flaps, parking brake) stay steady. The generators join the CAS
# cautions (the Hornet's CAS had no GEN message: switching a generator off raised nothing)
ADVISORIES = ('F22SpeedBrakeOut', 'F22FlapsAlt', 'ParkingBrakeSet', 'F22BayOpen', 'F22PullUp', 'F22AoaHigh', 'F22GcasActive', 'F22AtActive',
              'F22BitRunning', 'F22BitPassShow')
# BIT PASS on the ground only (in the air it stayed lit the whole flight, user 2026-11-06: clutter); FCS: the Hornet's
# aileron-off caution or the direct mode (tvc_f22: the laws are bypassed)
# ... and until the ICAWS reset (left button under the left UFD, as a caution's acknowledge; user 2026-11-07: it stayed
# up to the takeoff and nothing cleared it). A new pass shows it again.
obj(dyn, 'variable', 'F22BitPassAcked', anchor, Value='0.0')
obj(dyn, 'event_value', 'F22BitPassAck', anchor, Input='1.0', Events=' F22BitPassAcked.Set ')
obj(dyn, 'event_value', 'F22BitPassFresh', anchor, Input='0.0', Events=' F22BitPassAcked.Set ')
obj(dyn, 'event_edge_rising', 'F22BitPassNew', anchor, Input='F22BitPass.Output', Events=' F22BitPassFresh.Trigger ', Value=1.0, Threshold=0.5)
obj(dyn, 'logic_greater', 'F22BitPassNotAcked', anchor, Input0='0.5', Input1='F22BitPassAcked.Output')
obj(dyn, 'logic_and', 'F22BitPassShow', anchor, Inputs=' F22BitPass.Output OnGroundSensor.Output F22BitPassNotAcked.Output ')
obj(dyn, 'logic_or', 'F22FcsIcaws', anchor, Inputs=' CautionAileronOff.Output F22DirectActive.Output ')
for k in (1, 2):
    obj(dyn, 'warning_system_message', 'CASCautionEngine%dGenerator' % k, D['CAS'], Severity=('int', '2'),
        Input='Engine%dGeneratorCaution.Output' % k)
setv(D['CAS'], 'Messages', D['CAS'].get('Messages') + 'CASCautionEngine1Generator CASCautionEngine2Generator ')
# (own latch: CAS.OutputMasterCaution flashed the ICAWS but the reset never cleared it) - set by each caution
# coming on, cleared by the reset button
obj(dyn, 'variable', 'ICAWSUnacked', anchor, Value='0.0')
for text, cond in ICAWS:
    if cond not in ADVISORIES:
        obj(dyn, 'event_edge_rising', 'ICAWSNew' + cond, anchor, Input=cond + '.Output', Events=' ICAWSUnacked.Set ',
            Value=1.0, Threshold=0.5)
obj(dyn, 'event_value', 'ICAWSAcknowledge', anchor, Input='0.0', Events=' ICAWSUnacked.Set ')
setv(D['MasterCautionButton_Pressed'], 'Events', D['MasterCautionButton_Pressed'].get('Events') + 'ICAWSAcknowledge.Trigger F22BitPassAck.Trigger ')
obj(dyn, 'logic_greater', 'ICAWSUnacknowledged', anchor, Input0='ICAWSUnacked.Output', Input1='0.5')
obj(dyn, 'logic_invert', 'ICAWSFlashDark', anchor, Input='CASFlasher.Output')
obj(dyn, 'logic_and', 'ICAWSBlank', anchor, Inputs=' ICAWSUnacknowledged.Output ICAWSFlashDark.Output ')
obj(dyn, 'logic_invert', 'ICAWSLit', anchor, Input='ICAWSBlank.Output')
g('graphics_animation_render_list', 'F22Nothing', RenderList='  ')
# ICAWS as a list (2026-11-06, user: the 3 x 7 grid of fixed places, one per message, read as scattered words; colours:
# red = a problem, yellow = only the aircraft's state). The lit messages in order of importance - the warnings (PULL UP,
# OVER G, HYD, FCS), the cautions, both red, then the state (speed brake, parking brake, A/T...) yellow and steady -
# packed into 4 rows of 3 under the engine table, MORE and the number when more are lit. An unacknowledged caution
# flashes in its place (the list does not jump). 16 at a stride of 14: any message can land in the third column (8
# letters at 15.3 ran out of the screen). The packing was checked offline on 20000 random sets.
UFD_RED = (1.0, 0.2, 0.15, 1.0)
ICAWS_WARN = ('F22PullUp', 'F22OverG', 'F22HydLow', 'F22FcsIcaws') + failures_f22.ICAWS_WARN
ICAWS_STATE = ('ParkingBrakeSet', 'F22SpeedBrakeOut', 'F22FlapsAlt', 'F22BayOpen', 'F22GcasActive', 'F22AtActive',
               'F22BitRunning', 'F22BitPassShow')
icaws_text = dict((c, t) for t, c in ICAWS)
icaws_order = list(ICAWS_WARN) + [c for _, c in ICAWS if c not in ICAWS_WARN and c not in ICAWS_STATE] + list(ICAWS_STATE)
assert sorted(icaws_order) == sorted(c for _, c in ICAWS)
ICAWS_SLOTS = 12
for k, cond in enumerate(icaws_order):
    obj(dyn, 'logic_greater', 'F22IcawsOn%d' % k, anchor, Input0=cond + '.Output', Input1='0.5')
    obj(dyn, 'sum', 'F22IcawsCount%d' % k, anchor,
        Inputs=(' F22IcawsOn0.Output ' if k == 0 else ' F22IcawsCount%d.Output F22IcawsOn%d.Output ' % (k - 1, k)))
    obj(dyn, 'product', 'F22IcawsVal%d' % k, anchor,
        Inputs=' F22IcawsOn%d.Output %s %d.0 ' % (k, '1.0' if cond in ADVISORIES else 'ICAWSLit.Output', k + 1))
icaws_inputs = ' BlankLabel.Output %s ' % ' '.join(ufc_label(icaws_text[c]) for c in icaws_order)
icaws_font = dict(UFD_FONT, FontSize=16.0, Stride=14.0)
for s_ in range(ICAWS_SLOTS):
    x, y = 437 + 122 * (s_ % 3), 742 - 20 * (s_ // 3)
    terms = {'R': [], 'Y': []}
    for k, cond in enumerate(icaws_order):
        obj(dyn, 'linear_interpolation', 'F22IcawsAt%d_%d' % (s_, k), anchor, Input='F22IcawsCount%d.Output' % k,
            Map=' (%.1f 0.0) (%.1f 1.0) (%.1f 0.0) ' % (s_ + 0.5, s_ + 1.0, s_ + 1.5))
        obj(dyn, 'product', 'F22IcawsPick%d_%d' % (s_, k), anchor, Inputs=' F22IcawsAt%d_%d.Output F22IcawsVal%d.Output ' % (s_, k, k))
        terms['Y' if cond in ICAWS_STATE else 'R'].append('F22IcawsPick%d_%d.Output' % (s_, k))
    for cls, color in (('R', UFD_RED), ('Y', AMBER)):
        obj(dyn, 'sum', 'F22IcawsSlot%d%s' % (s_, cls), anchor, Inputs=' %s ' % ' '.join(terms[cls]))
        obj(dyn, 'multiplexer_text', 'F22IcawsSlotText%d%s' % (s_, cls), anchor, InputSelect='F22IcawsSlot%d%s.Output' % (s_, cls),
            Inputs=icaws_inputs)
        ufd_l.append(place_copy('UpFrontControllerLine0', 'UFDIcaws%d%s' % (s_, cls),
                                Input=text_out('Icaws%d%s' % (s_, cls), 'F22IcawsSlotText%d%s.Output' % (s_, cls)),
                                Position=' %d %d ' % (x, y), Length='8', **dict(icaws_font, Color=' %g %g %g %g ' % color)))
obj(dyn, 'mixlinear', 'F22IcawsMoreRaw', anchor, Input0='F22IcawsCount%d.Output' % (len(icaws_order) - 1), Input1='1.0',
    Weight0=1.0, Weight1=-float(ICAWS_SLOTS))
obj(dyn, 'maximum', 'F22IcawsMore', anchor, Inputs=' F22IcawsMoreRaw.Output 0.0 ')
obj(dyn, 'logic_greater', 'F22IcawsOverflow', anchor, Input0='F22IcawsMore.Output', Input1='0.5')
g('graphics_input', 'GfxF22IcawsOverflow', InputID=('uint32', published('F22IcawsOverflow')))
g('graphics_animation_render_list', 'F22IcawsMoreList', RenderList=' %s %s ' % (
    label('MORE', (690, 650), 15.0, UFD_RED),
    number_of('F22IcawsMore.Output', 'IcawsMore', (750, 650), 1.0, n=2, font=dict(icaws_font, Color=' %g %g %g %g ' % UFD_RED))))
g('graphics_animation_render_switch', 'F22IcawsMoreShow', Input='GfxF22IcawsOverflow.Output', RenderList=' F22Nothing F22IcawsMoreList ')
ufd_l.append('F22IcawsMoreShow')
window('UFDLeft', screens['DisplayLeftUFD'], ufd_l)
# right UFD (atlas 430..800 x 320..605): standby attitude (the F/A-18 ADI page: attitude, airspeed, altitude,
# vertical speed; the four squares under it are its sideslip indicator - the lower one is the ball) beside total fuel
# (lb) with the time / range to BINGO and the local time
# (2026-11-07, user) two pages again, the top button (R_SMFD_1) flips them: SFI (this page) and TIME - kept from the
# rejected UFD pages of 2026-11-06 (scratchpad make_f22_ufd_v2.py), the rest of those stays out. Back to SFI by itself
# when the standby instruments are what is left: the battery alone on the bus, or no engine running in the air.


def ufd_button(name, message, events):
    """A UFD push button: its click sends message, the button fires events (+ the click sound)."""
    obj(dyn, 'input_button', name, anchor, Message=message, InputValue='1.0',
        Events=' %s ButtonSoundCenterPanel.Trigger ' % events, EventsRelease=' ButtonSoundCenterPanel.Trigger ')


def ufd_text(key, src, pos, n, font=UFD_FONT):
    return place_copy('UpFrontControllerLine0', 'UFD' + key, Input=text_out(key, src), Position=' %d %d ' % pos,
                      Length=str(n), **font)


obj(dyn, 'variable', 'F22UfdRPage', anchor, Value='0.0')
obj(dyn, 'logic_invert', 'F22UfdRPageOther', anchor, Input='F22UfdRPage.Output')
obj(dyn, 'event_value', 'F22UfdRPageNext', anchor, Input='F22UfdRPageOther.Output', Events=' F22UfdRPage.Set ')
ufd_button('F22UfdRPageButton', 'UFD.RightPage', 'F22UfdRPageNext.Trigger')
g('graphics_input', 'GfxF22UfdRPage', InputID=('uint32', published('F22UfdRPage')))
obj(dyn, 'logic_and', 'F22BothEnginesOut', anchor, Inputs=' Engine1NotRunning.Output Engine2NotRunning.Output F22AtAirborne.Output ')
obj(dyn, 'logic_or', 'F22StandbyNeeded', anchor, Inputs=' F22OnBattery.Output F22BothEnginesOut.Output ')
obj(dyn, 'event_value', 'F22UfdRToSfiSet', anchor, Input='0.0', Events=' F22UfdRPage.Set ')
obj(dyn, 'event_edge_rising', 'F22UfdRToSfi', anchor, Input='F22StandbyNeeded.Output', Events=' F22UfdRToSfiSet.Trigger ',
    Value=1.0, Threshold=0.5)
g('graphics_animation_render_switch', 'F22UfdAdiSwitch', Input='GfxF22UfdRPage.Output', RenderList=' ADIPage F22Nothing ')
window('UFDRightADI', screens['DisplayRightUFD'], ['F22UfdAdiSwitch'], pos=(432, 345), size=(255, 255))
clock_src, _, _ = dyn_value('LocalTime')
obj(dyn, 'time_to_text', 'UFDClockText', anchor, Input=clock_src, Hours=('bool', 'true'), Seconds=('bool', 'true'))
# (2026-11-06, user) COM1 / COM2 out: they showed the Hornet's channel numbers ('1' / '2'), no channel has a frequency -
# they meant nothing. FUEL with T (minutes) and R (nautical miles) to BINGO at the present flow and ground speed, the
# FPAS page's own figures (F22PerfTime / F22PerfRange), held at 999 min / 9999 NM with the engines off
obj(dyn, 'clamp', 'F22UfdFuelTime', anchor, Input='F22PerfTime.Output', Range=('tmvector2d', ' 0.0 59940.0 '))
obj(dyn, 'clamp', 'F22UfdFuelRange', anchor, Input='F22PerfRange.Output', Range=('tmvector2d', ' 0.0 18518000.0 '))
ufd_r = [label('FUEL', (694, 575)), number('TotalFuel', 'FuelTotal', (694, 549), 2.204622621849, 6),
         label('T', (694, 515)), number_of('F22UfdFuelTime.Output', 'UfdFuelTime', (720, 515), 1 / 60.0, n=4),
         label('R', (694, 490)), number_of('F22UfdFuelRange.Output', 'UfdFuelRange', (720, 490), 1 / 1852.0, n=4),
         place_copy('UpFrontControllerLine0', 'UFDClock', Input=text_out('Clock', 'UFDClockText.Output'),
                    Position=' 692 445 ', Length='8', **dict(UFD_FONT, FontSize=17.0, Stride=13.5))]
# (2026-11-05) the APU (OFF / STRT / ON) and both hydraulic pressures (psi), for an engine failure on the battery
obj(dyn, 'logic_greater', 'F22ApuTurning', anchor, Input0='APUN1.Output', Input1='0.05')
obj(dyn, 'multiplexer', 'F22ApuStage0', anchor, InputSelect='F22ApuTurning.Output', Inputs=' 0.0 1.0 ')
obj(dyn, 'multiplexer', 'F22ApuStage', anchor, InputSelect='APUAvailable.Output', Inputs=' F22ApuStage0.Output 2.0 ')
obj(dyn, 'multiplexer_text', 'F22ApuText', anchor, InputSelect='F22ApuStage.Output',
    Inputs=' %s ' % ' '.join(ufc_label(t) for t in ('OFF', 'STRT', 'ON')))
small = dict(UFD_FONT, FontSize=17.0, Stride=13.5)
# shown only when it matters (user 2026-11-05: in normal flight these lines were clutter): the APU turning, a
# hydraulic system low, the battery alone on the bus or an engine not running (on the ground before the start too)
obj(dyn, 'logic_or', 'F22UfdSysShow', anchor, Inputs=' F22ApuTurning.Output F22HydLow.Output F22OnBattery.Output '
    'Engine1NotRunning.Output Engine2NotRunning.Output ')
g('graphics_input', 'GfxF22UfdSysShow', InputID=('uint32', published('F22UfdSysShow')))
ufd_sys = [label('APU', (694, 380), 17.0),          # (size 20 ran into the state: 'APUOFF', user 2026-11-05)
          place_copy('UpFrontControllerLine0', 'UFDApu', Input=text_out('Apu', 'F22ApuText.Output'),
                     Position=' 746 380 ', Length='4', **small),
          label('HYD', (694, 357), 17.0),               # ('HYD L/R' at 20 ran out of the window)
          # (two 4-digit fields at 13.5 touched: '24072407', user 2026-11-05 - smaller digits with a gap, L then R)
          number_of('F22HydSystem1.Output', 'Hyd1', (692, 334), 3000.0, n=4, font=dict(small, FontSize=15.0, Stride=12.0)),
          number_of('F22HydSystem2.Output', 'Hyd2', (750, 334), 3000.0, n=4, font=dict(small, FontSize=15.0, Stride=12.0))]
g('graphics_animation_render_list', 'F22UfdSysList', RenderList=' %s ' % ' '.join(ufd_sys))
g('graphics_animation_render_switch', 'F22UfdSys', Input='GfxF22UfdSysShow.Output', RenderList=' F22Nothing F22UfdSysList ')
ufd_r.append('F22UfdSys')
# TIME: the local time, the flight time (counts while airborne, held on the ground) and a stopwatch for the approach,
# a hold or a check, as the A380's: an integral of its running flag. The three lower buttons, left to right R_SMFD_2 /
# 3 / 4: ST/SP starts and stops it, the middle one is free, RST zeroes it - on this page only. (In the rejected build
# RST sat on the middle button and the legends stood off their buttons, user 2026-11-07: legends now centred over
# them - the user's screenshot: 1.331 px per page unit, buttons at page x 556 / 627 / 698 by the legends' centres)
obj(dyn, 'integral', 'F22FlightTime', anchor, Input='F22AtAirborne.Output')
obj(dyn, 'variable', 'F22StopwatchRunning', anchor, Value='0.0')
obj(dyn, 'logic_invert', 'F22StopwatchOther', anchor, Input='F22StopwatchRunning.Output')
obj(dyn, 'event_value', 'F22StopwatchToggle', anchor, Input='F22StopwatchOther.Output', Events=' F22StopwatchRunning.Set ')
obj(dyn, 'integral', 'F22Stopwatch', anchor, Input='F22StopwatchRunning.Output')
obj(dyn, 'event_demultiplexer', 'F22UfdR1Event', anchor, InputSelect='F22UfdRPage.Output', Events=' DEV0.Trigger F22StopwatchToggle.Trigger ')
obj(dyn, 'event_demultiplexer', 'F22UfdR3Event', anchor, InputSelect='F22UfdRPage.Output', Events=' DEV0.Trigger F22Stopwatch.Reset ')
ufd_button('F22UfdR1Button', 'UFD.RightKey1', 'F22UfdR1Event.Trigger')
ufd_button('F22UfdR3Button', 'UFD.RightKey3', 'F22UfdR3Event.Trigger')
for n_, src in (('F22FlightTimeText', 'F22FlightTime.Output'), ('F22StopwatchText', 'F22Stopwatch.Output')):
    obj(dyn, 'time_to_text', n_, anchor, Input=src, Hours=('bool', 'true'), Seconds=('bool', 'true'))
obj(dyn, 'binary_to_text', 'F22StopwatchState', anchor, Input='F22StopwatchRunning.Output', Text0='STOP', Text1='RUN')
time_page = [label('TIME', (585, 585), 17.0),
             label('LOCAL', (445, 540)), ufd_text('TimeLocal', 'UFDClockText.Output', (590, 540), 8),
             label('FLIGHT', (445, 500)), ufd_text('TimeFlight', 'F22FlightTimeText.Output', (590, 500), 8),
             label('TIMER', (445, 455)), ufd_text('TimeState', 'F22StopwatchState.Output', (590, 455), 4),
             ufd_text('TimeWatch', 'F22StopwatchText.Output', (470, 400), 8, dict(UFD_FONT, FontSize=34.0, Stride=28.0)),
             label('ST/SP', (522, 328), 15.0), label('RST', (678, 328), 15.0)]
# (2026-11-07, user) the stopwatch also on the SFI page, under the clock - once started (running, or stopped with a
# time on it); the flight time stays on TIME only
obj(dyn, 'logic_greater', 'F22StopwatchUsed', anchor, Input0='F22Stopwatch.Output', Input1='0.5')
g('graphics_input', 'GfxF22StopwatchUsed', InputID=('uint32', published('F22StopwatchUsed')))
g('graphics_animation_render_switch', 'F22UfdSfiWatch', Input='GfxF22StopwatchUsed.Output',
  RenderList=' F22Nothing %s ' % ufd_text('SfiWatch', 'F22StopwatchText.Output', (692, 421), 8, dict(UFD_FONT, FontSize=17.0, Stride=13.5)))
ufd_r.append('F22UfdSfiWatch')
g('graphics_animation_render_list', 'F22UfdSfiList', RenderList=' %s ' % ' '.join(ufd_r))
g('graphics_animation_render_list', 'F22UfdTimeList', RenderList=' %s ' % ' '.join(time_page))
g('graphics_animation_render_switch', 'F22UfdRPages', Input='GfxF22UfdRPage.Output', RenderList=' F22UfdSfiList F22UfdTimeList ')
window('UFDRight', screens['DisplayRightUFD'], ['F22UfdRPages'])
# BAY page (stage 6) on the MFDs in place of the Hornet's stores page (page 10): the left buttons L BAY / C BAY /
# R BAY / ALL (boxed = commanded open), centre: each bay's load and door state, the ferry tanks. DDI page units
# 0 .. 1024 (y up), the DDI font
BAY_FONT = 34.0
for name, texts in (('F22BayStateText', ('CLSD', 'MOVE', 'OPEN')), ('F22TanksText', ('NONE', '1 X 600 GAL', '2 X 600 GAL'))):
    for t in texts:
        ufc_label(t)
for bay in BAYS:
    obj(dyn, 'multiplexer_text', 'F22Bay%sStateText' % bay, anchor, InputSelect='F22Bay%sState.Output' % bay,
        Inputs=' %s ' % ' '.join(ufc_label(t) for t in ('CLSD', 'MOVE', 'OPEN')))
for bay, load in (('Center', '6 AIM-120C'), ('Left', 'AIM-9X'), ('Right', 'AIM-9X')):
    obj(dyn, 'multiplexer_text', 'F22Bay%sLoadText' % bay, anchor, InputSelect='F22CombatLoad.Output',
        Inputs=' %s %s ' % (ufc_label('EMPTY'), ufc_label(load)))
# tanks still on: the load's two less the jettisoned / lost ones (breakage_f22.tank_release)
obj(dyn, 'sum', 'F22TanksOnCount', anchor, Inputs=' F22TankOnLeft.Output F22TankOnRight.Output ')
obj(dyn, 'product', 'F22TanksHanging', anchor, Inputs=' F22TanksOnCount.Output F22FerryTanks.Output ')
obj(dyn, 'multiplexer_text', 'F22TanksText', anchor, InputSelect='F22TanksHanging.Output',
    Inputs=' %s ' % ' '.join(ufc_label(t) for t in ('NONE', '1 X 600 GAL', '2 X 600 GAL')))
bay_font = dict(UFD_FONT, FontSize=BAY_FONT, Stride=BAY_FONT * 0.85)
bay_items = [label('WEAPON BAYS', (300, 860), BAY_FONT)]
for row, (bay, short) in enumerate((('Left', 'LFT'), ('Center', 'CTR'), ('Right', 'RGT'))):
    y = 740 - 70 * row
    bay_items += [label(short, (150, y), BAY_FONT),
                  place_copy('UpFrontControllerLine0', 'F22BayPage%sLoad' % bay,
                             Input=text_out('Bay%sLoad' % bay, 'F22Bay%sLoadText.Output' % bay), Position=' 330 %d ' % y,
                             Length='10', **bay_font),
                  place_copy('UpFrontControllerLine0', 'F22BayPage%sState' % bay,
                             Input=text_out('Bay%sState' % bay, 'F22Bay%sStateText.Output' % bay),
                             Position=' 720 %d ' % y, Length='4', **bay_font)]
bay_items += [label('TANKS', (150, 480), BAY_FONT),
              place_copy('UpFrontControllerLine0', 'F22BayPageTanks', Input=text_out('Tanks', 'F22TanksText.Output'),
                         Position=' 330 480 ', Length='11', **bay_font)]
g('graphics_animation_render_list', 'F22BayPage', RenderList=' %s ' % ' '.join(bay_items))
n_bay = 0
for o in G:
    if o.type == 'graphics_animation_render_switch' and o.find('RenderList') is not None and \
            'StoresPage' in o.get('RenderList').split():
        o.set('RenderList', ' ' + ' '.join('F22BayPage' if t == 'StoresPage' else t
                                           for t in o.get('RenderList').split()) + ' ')
        n_bay += 1
print('BAY page in %d MFD page switches' % n_bay)
# FUEL page: the Hornet page counts the ferry tanks in TOTAL but draws no box for them here - EXT L / EXT R (lb) below
# the wing tanks while the tanks hang
fuel_items = []
# (each side's own tank, gone once it is jettisoned or lost with its console: breakage_f22.tank_release - the lines
# showed full tanks after a jettison, in-game 2026-11-13)
for side, x in (('L', 110), ('R', 790)):
    full = {'L': 'Left', 'R': 'Right'}[side]
    obj(dyn, 'product', 'F22FuelExt%sShown' % side, anchor, Inputs=' F22TanksAttached.Output F22TankOn%s.Output ' % full)
    obj(dyn, 'mixlinear', 'UFDValueExt' + side, anchor, Input0='F22FerryFuel%s.Output' % full, Input1='1.0',
        Weight0=2.20462, Weight1=0.0)
    obj(dyn, 'int_to_text', 'UFDNumberExt' + side, anchor, Input='UFDValueExt%s.Output' % side)
    obj(dyn, 'multiplexer_text', 'F22FuelExt%sValue' % side, anchor, InputSelect='F22FuelExt%sShown.Output' % side,
        Inputs=' BlankLabel.Output UFDNumberExt%s.Output ' % side)
    obj(dyn, 'multiplexer_text', 'F22FuelExt%sName' % side, anchor, InputSelect='F22FuelExt%sShown.Output' % side,
        Inputs=' BlankLabel.Output %s ' % ufc_label('EXT ' + side))
    fuel_items += [place_copy('UpFrontControllerLine0', 'F22FuelPageExt%sName' % side,
                              Input=text_out('FuelExt%sName' % side, 'F22FuelExt%sName.Output' % side),
                              Position=' %d 470 ' % (x + 15), Length='5', **dict(UFD_FONT, FontSize=30.0, Stride=27.0)),
                   place_copy('UpFrontControllerLine0', 'F22FuelPageExt%sValue' % side,
                              Input=text_out('FuelExt%sValue' % side, 'F22FuelExt%sValue.Output' % side),
                              Position=' %d 415 ' % x, Length='5', LeftJustified='false', **bay_font)]
g('graphics_animation_render_list', 'F22FuelPage', RenderList=' FuelPage %s ' % ' '.join(fuel_items))
n_fuel = 0
for o in G:
    if o.type == 'graphics_animation_render_switch' and o.find('RenderList') is not None and \
            'FuelPage' in o.get('RenderList').split():
        o.set('RenderList', ' ' + ' '.join('F22FuelPage' if t == 'FuelPage' else t
                                           for t in o.get('RenderList').split()) + ' ')
        n_fuel += 1
print('FUEL page EXT L / R in %d MFD page switches' % n_fuel)
# FPAS page (empty in the stock Hornet, user's wish 2026-11-01): what the fuel means now, at the present flow and ground speed. Units are the game's SI (kg, kg/s,
# m/s, m, s). All to BINGO, the reserve the pilot set on the FUEL page. Flow in afterburner is honest: minutes shrink at once
LB, NM = 2.204622621849, 1 / 1852.0
obj(dyn, 'sum', 'F22PerfFlow', anchor, Inputs=' Engine1FuelFlow.Output Engine2FuelFlow.Output ')
obj(dyn, 'inverse', 'F22PerfPerFlow', anchor, Input='F22PerfFlow.Output')
obj(dyn, 'mixlinear', 'F22PerfMarginRaw', anchor, Input0='TotalFuel.Output', Input1='BingoFuel.Output', Weight0=1.0, Weight1=-1.0)
obj(dyn, 'maximum', 'F22PerfMargin', anchor, Inputs=' F22PerfMarginRaw.Output 0.0 ')
obj(dyn, 'product', 'F22PerfTime', anchor, Inputs=' F22PerfMargin.Output F22PerfPerFlow.Output ')
obj(dyn, 'product', 'F22PerfRange', anchor, Inputs=' F22PerfTime.Output InertialReferenceSystem.OutputGroundSpeed ')
obj(dyn, 'product', 'F22PerfSpecific', anchor, Inputs=' InertialReferenceSystem.OutputGroundSpeed F22PerfPerFlow.Output ')
obj(dyn, 'product', 'F22PerfFuelToWaypoint', anchor, Inputs=' F22PerfFlow.Output GPSNavigationSystem.OutputNextWaypointTime ')
obj(dyn, 'mixlinear', 'F22PerfFuelAtWaypointRaw', anchor, Input0='TotalFuel.Output', Input1='F22PerfFuelToWaypoint.Output', Weight0=1.0, Weight1=-1.0)
obj(dyn, 'maximum', 'F22PerfFuelAtWaypoint', anchor, Inputs=' F22PerfFuelAtWaypointRaw.Output 0.0 ')
perf_font = dict(UFD_FONT, FontSize=BAY_FONT, Stride=BAY_FONT * 0.85)
perf_items = [label('FUEL PERFORMANCE', (250, 905), BAY_FONT)]
perf_rows = [('FUEL LB', 'TotalFuel.Output', LB), ('BINGO LB', 'BingoFuel.Output', LB), ('TO BINGO LB', 'F22PerfMargin.Output', LB),
             ('FLOW PPH', 'F22PerfFlow.Output', LB * 3600.0), ('TIME MIN', 'F22PerfTime.Output', 1 / 60.0), ('RANGE NM', 'F22PerfRange.Output', NM),
             ('NM/1000 LB', 'F22PerfSpecific.Output', NM * 1000 / LB)]
for row, (text, src, k) in enumerate(perf_rows):
    y = 835 - 56 * row
    perf_items += [label(text, (120, y), BAY_FONT), number_of(src, 'Perf%d' % row, (600, y), k, n=7, font=perf_font)]
perf_items += [label('NEXT', (120, 430), BAY_FONT),
               place_copy('UpFrontControllerLine0', 'F22PerfNext', Input=text_out('PerfNext', 'GPSNavigationSystem.OutputNextWaypointIdentifier'),
                          Position=' 600 430 ', Length='7', LeftJustified='false', **perf_font)]
for row, (text, src, k) in enumerate([('DIST NM', 'GPSNavigationSystem.OutputNextWaypointDistance', NM),
                                      ('TIME MIN', 'GPSNavigationSystem.OutputNextWaypointTime', 1 / 60.0),
                                      ('FUEL THERE LB', 'F22PerfFuelAtWaypoint.Output', LB)]):
    y = 374 - 56 * row
    perf_items += [label(text, (120, y), BAY_FONT), number_of(src, 'PerfNext%d' % row, (600, y), k, n=7, font=perf_font)]
# the wind, for the fuel it costs: wind_vector of the stock airliners, in the F/A-18's own air data
obj(dyn, 'wind_vector', 'WindVector', anchor, InputTrueAirspeed='AirDataComputer.OutputTrueAirspeed', InputAngleOfAttack='PitotTube.AngleOfAttack', InputX=IRS + 'X', InputY=IRS + 'Y',
    InputZ=IRS + 'Z', InputPosition=IRS + 'Position', InputVelocity=IRS + 'Velocity')
obj(dyn, 'clamp_cyclic', 'F22WindFrom', anchor, Input='WindVector.OutputDirection', Range=('string8', ' 0.0 6.283185 '))
perf_items += [label('WIND DEG', (120, 206), BAY_FONT), number_of('F22WindFrom.Output', 'PerfWindDir', (600, 206), 180.0 / math.pi, n=7, font=perf_font),
               label('WIND KT', (120, 150), BAY_FONT), number_of('WindVector.OutputSpeed', 'PerfWindSpeed', (600, 150), 1.94384, n=7, font=perf_font)]
g('graphics_animation_render_list', 'F22PerfPage', RenderList=' %s ' % ' '.join(perf_items))
n_perf = 0
for o in G:
    if o.type == 'graphics_animation_render_switch' and o.find('RenderList') is not None and \
            'FlightPerformanceAdvisorySystemPage' in o.get('RenderList').split():
        o.set('RenderList', ' ' + ' '.join('F22PerfPage' if t == 'FlightPerformanceAdvisorySystemPage' else t
                                           for t in o.get('RenderList').split()) + ' ')
        n_perf += 1
print('FPAS page in %d MFD page switches' % n_perf)
# CHECKLIST pages: this mod's procedures with its own switches (what the cockpit does, not an F-22 manual - none is
# public). 13 lines of up to 26 characters, the line's text picked by F22ChecklistIndex
CHECKLISTS = [
    ('COLD START', ['BATT .............. ON', 'APU ............ START', 'CANOPY .......... CLOSE', 'CNI / ACP ........... ON',
                    'FADEC ............ NORM', 'THROTTLES ......... IDLE', '  (STARTS ON APU AIR)', 'L / R GEN ........... ON',
                    'BATT LIGHT ........ OUT', 'APU ............... OFF', 'FLCS BIT ....... START', '  40 S, BIT PASS -> STOP',
                    'LAMP TEST ...... CHECK']),
    ('BEFORE TAKEOFF', ['CANOPY ......... CLOSED', 'BIT PASS ...... ON ICAWS', 'MASTER ARM ....... SAFE', 'ALT FLAPS ........ NORM',
                        'FLAPS ...... T/O (AUTO)', 'TRIM ............. ZERO', 'LDG/TAXI LIGHT .... LDG', 'NAV / FORM LIGHTS .. ON',
                        'PARK BRAKE .... RELEASE', 'ICAWS ........... CLEAR', '', 'GEAR UP NEEDS AIRBORNE', 'OR DN LOCK OVERRIDE']),
    ('LANDING', ['SPEED ....... BELOW 250', 'GEAR ............. DOWN', '3 GREEN ...... NOSE L R', 'FLAPS ...... LDG (AUTO)',
                 'ALT FLAPS ........ NORM', '  (EXTEN: FLAPS GEAR UP)', 'A/T ... AOA 8.5 IF WANT', 'LDG LIGHT .......... ON',
                 'SPEED BRAKE ...... AS RQ', '', 'AFTER LANDING:', 'LIGHT ............ TAXI', 'FLAPS ........... AUTO']),
    ('SHUTDOWN', ['PARK BRAKE ......... SET', 'THROTTLES ......... IDLE', 'APU ............... OFF', 'FADEC ............. L',
                  '  (LEFT ENGINE STOPS)', 'FADEC ............. R', '  (RIGHT ENGINE STOPS)', 'FADEC ............ NORM',
                  'LIGHTS ............ OFF', 'CNI / ACP .......... OFF', 'BATT .............. OFF', 'CANOPY ........... OPEN', '']),
]
chk_items = []
obj(dyn, 'multiplexer_text', 'F22ChecklistTitle', anchor, InputSelect='F22ChecklistIndex.Output',
    Inputs=' %s ' % ' '.join(ufc_label(t) for t, _ in CHECKLISTS))
chk_items.append(place_copy('UpFrontControllerLine0', 'F22ChecklistTitleText', Input=text_out('ChecklistTitle', 'F22ChecklistTitle.Output'),
                            Position=' 300 905 ', Length='16', **dict(UFD_FONT, FontSize=BAY_FONT, Stride=BAY_FONT * 0.85)))
for row in range(13):
    texts = [lines[row] if row < len(lines) and lines[row] else ' ' for _, lines in CHECKLISTS]
    obj(dyn, 'multiplexer_text', 'F22ChecklistLine%d' % row, anchor, InputSelect='F22ChecklistIndex.Output',
        Inputs=' %s ' % ' '.join(ufc_label(t) if t.strip() else 'BlankLabel.Output' for t in texts))
    chk_items.append(place_copy('UpFrontControllerLine0', 'F22ChecklistLine%dText' % row,
                                Input=text_out('ChecklistLine%d' % row, 'F22ChecklistLine%d.Output' % row),
                                Position=' 170 %d ' % (835 - 56 * row), Length='26', **dict(UFD_FONT, FontSize=30.0, Stride=25.5)))
g('graphics_animation_render_list', 'F22ChecklistPage', RenderList=' %s ' % ' '.join(chk_items))
n_chk = 0
for o in G:
    if o.type == 'graphics_animation_render_switch' and o.find('RenderList') is not None and \
            'ChecklistPage' in o.get('RenderList').split():
        o.set('RenderList', ' ' + ' '.join('F22ChecklistPage' if t == 'ChecklistPage' else t
                                           for t in o.get('RenderList').split()) + ' ')
        n_chk += 1
print('CHECKLIST page in %d MFD page switches' % n_chk)
# ENG page: each engine's start stage under the Hornet's engine table - OFF, MOTOR (starter, no fuel: FADEC off or
# throttle in cut-off), START (starter with fuel), RUN, FADEC OFF (stopped by its FADEC), WINDMILL (stopped, turning)
for k, side in ((1, 'L'), (2, 'R')):
    obj(dyn, 'multiplexer', 'F22Eng%dStageCrank' % k, anchor, InputSelect='Engine%dRunWithFuel.Output' % k, Inputs=' 1.0 2.0 ')
    # (the starter turns only with air on it: Engine<n>StarterPressureSufficient, the jet_engine's InputStart - a start
    # request without the APU showed MOT at 0 RPM, user 2026-11-05)
    obj(dyn, 'multiplexer', 'F22Eng%dStageStart' % k, anchor, InputSelect='Engine%dStarterPressureSufficient.Output' % k,
        Inputs=' 0.0 F22Eng%dStageCrank.Output ' % k)
    obj(dyn, 'multiplexer', 'F22Eng%dStageRun' % k, anchor, InputSelect='Engine%dRunning.Output' % k,
        Inputs=' F22Eng%dStageStart.Output 3.0 ' % k)
    obj(dyn, 'logic_invert', 'F22Fadec%dOff' % k, anchor, Input='F22Fadec%dOn.Output' % k)
    obj(dyn, 'logic_invert', 'F22Eng%dNoStart' % k, anchor, Input='Engine%dStarterPressureSufficient.Output' % k)
    obj(dyn, 'logic_and', 'F22Eng%dFadecStopped' % k, anchor,
        Inputs=' F22Fadec%dOff.Output F22Eng%dNoStart.Output Engine%dNotRunning.Output ' % (k, k, k))
    obj(dyn, 'multiplexer', 'F22Eng%dStage' % k, anchor, InputSelect='F22Eng%dFadecStopped.Output' % k,
        Inputs=' F22Eng%dStageRun.Output 4.0 ' % k)
    # windmilling: stopped with fuel on or off, no starter, but turning above 8 % N2 (the airflow, F22WindmillN2)
    obj(dyn, 'logic_greater', 'F22Eng%dTurning' % k, anchor, Input0='F22Eng%dGearboxN2.Output' % k, Input1='0.08')
    obj(dyn, 'logic_equal', 'F22Eng%dStageOff' % k, anchor, Input0='F22Eng%dStage.Output' % k, Input1='0.0')
    obj(dyn, 'logic_and', 'F22Eng%dWindmill' % k, anchor, Inputs=' F22Eng%dStageOff.Output F22Eng%dTurning.Output ' % (k, k))
    obj(dyn, 'multiplexer', 'F22Eng%dStageW' % k, anchor, InputSelect='F22Eng%dWindmill.Output' % k,
        Inputs=' F22Eng%dStage.Output 5.0 ' % k)
    obj(dyn, 'multiplexer_text', 'F22Eng%dStageText' % k, anchor, InputSelect='F22Eng%dStageW.Output' % k,
        Inputs=' %s ' % ' '.join(ufc_label(t) for t in ('%s OFF' % side, '%s MOTOR' % side, '%s START' % side,
                                                         '%s RUN' % side, '%s FADEC OFF' % side, '%s WINDMILL' % side)))
eng_items = [place_copy('UpFrontControllerLine0', 'F22Eng%dStageItem' % k, Input=text_out('Eng%dStage' % k, 'F22Eng%dStageText.Output' % k),
                        Position=' %d 100 ' % x, Length='12', **dict(UFD_FONT, FontSize=28.0, Stride=24.0))
             for k, x in ((1, 130), (2, 590))]
g('graphics_animation_render_list', 'F22EnginesPage', RenderList=' EnginesPage %s ' % ' '.join(eng_items))
n_eng = 0
for o in G:
    if o.type == 'graphics_animation_render_switch' and o.find('RenderList') is not None and \
            'EnginesPage' in o.get('RenderList').split():
        o.set('RenderList', ' ' + ' '.join('F22EnginesPage' if t == 'EnginesPage' else t
                                           for t in o.get('RenderList').split()) + ' ')
        n_eng += 1
print('ENG page start stages in %d MFD page switches' % n_eng)
# TVC page in place of the Hornet's empty BIT page. Nozzle + = nose up. Pitch rate: InertialReferenceSystem's is + nose down
obj(dyn, 'binary_to_text', 'F22TvcModeText', anchor, Input='F22DirectMode.Output', Text0='AUTO', Text1='DIRECT')
obj(dyn, 'binary_to_text', 'F22TvcVectorText', anchor, Input='F22VectorOn.Output', Text0='OFF', Text1='ON')
# the VOICE row: the VOX knob in % (OFF at 0)
obj(dyn, 'linear', 'F22VoicePct', anchor, Input='F22VoiceVolume.Output', Scaling=100.0, Offset=0.5)
obj(dyn, 'int_to_text', 'F22VoicePctText', anchor, Input='F22VoicePct.Output')
obj(dyn, 'constant_text', 'F22VoiceOffText', anchor, Input='OFF')
obj(dyn, 'multiplexer_text', 'F22TvcVoiceText', anchor, InputSelect='F22VoiceOn.Output', Inputs=' F22VoiceOffText.Output F22VoicePctText.Output ')
DEG = 180.0 / math.pi
obj(dyn, 'binary_to_text', 'F22TvcGcasText', anchor, Input='F22GcasArmed.Output', Text0='OFF', Text1='ON')
obj(dyn, 'linear', 'F22AtModeShown', anchor, Input='F22AtMode.Output', Scaling=1.0, Offset=1.0)
obj(dyn, 'product', 'F22AtModeOrOff', anchor, Inputs=' F22AtActive.Output F22AtModeShown.Output ')
obj(dyn, 'multiplexer_text', 'F22TvcAtText', anchor, InputSelect='F22AtModeOrOff.Output', Inputs=' %s ' % ' '.join(ufc_label(t) for t in ('OFF', 'SPD KT', 'MACH', 'AOA')))
obj(dyn, 'linear', 'F22AtCasShown', anchor, Input='F22AtCasTarget.Output', Scaling=1.94384)
obj(dyn, 'int_to_text', 'F22AtCasText', anchor, Input='F22AtCasShown.Output')
obj(dyn, 'float_to_text', 'F22AtMachText', anchor, Input='F22AtMachTarget.Output', Decimals=('uint32', '2'))
obj(dyn, 'constant_text', 'F22AtAoaText', anchor, Input='8.5')
obj(dyn, 'multiplexer_text', 'F22AtTargetText', anchor, InputSelect='F22AtMode.Output', Inputs=' F22AtCasText.Output F22AtMachText.Output F22AtAoaText.Output ')
tvc_items = [label('SYSTEMS', (390, 905), BAY_FONT),
             label('FCS MODE', (120, 835), BAY_FONT),
             place_copy('UpFrontControllerLine0', 'F22TvcMode', Input=text_out('TvcMode', 'F22TvcModeText.Output'),
                        Position=' 600 835 ', Length='7', LeftJustified='false', **perf_font),
             label('VECTOR', (120, 779), BAY_FONT),
             place_copy('UpFrontControllerLine0', 'F22TvcVector', Input=text_out('TvcVector', 'F22TvcVectorText.Output'),
                        Position=' 600 779 ', Length='7', LeftJustified='false', **perf_font),
             label('VOICE %', (120, 723), BAY_FONT),
             place_copy('UpFrontControllerLine0', 'F22TvcVoice', Input=text_out('TvcVoice', 'F22TvcVoiceText.Output'),
                        Position=' 600 723 ', Length='7', LeftJustified='false', **perf_font),
             label('AUTO GCAS', (120, 667), BAY_FONT),
             place_copy('UpFrontControllerLine0', 'F22TvcGcas', Input=text_out('TvcGcas', 'F22TvcGcasText.Output'),
                        Position=' 600 667 ', Length='7', LeftJustified='false', **perf_font),
             label('A/T', (120, 611), BAY_FONT),
             place_copy('UpFrontControllerLine0', 'F22TvcAt', Input=text_out('TvcAt', 'F22TvcAtText.Output'),
                        Position=' 600 611 ', Length='7', LeftJustified='false', **perf_font),
             label('A/T TARGET', (120, 555), BAY_FONT),
             place_copy('UpFrontControllerLine0', 'F22TvcAtTarget', Input=text_out('TvcAtTarget', 'F22AtTargetText.Output'),
                        Position=' 600 555 ', Length='7', LeftJustified='false', **perf_font)]
tvc_rows = [('NOZZLE DEG', 'NozzleAngle.Output', DEG), ('ALOW FT', 'F22AltFloor.Output', 3.28084), ('AUTHORITY %', 'VectorSpeedFade.Output', 100.0),
            ('PITCH RATE D/S', 'InertialReferenceSystem.OutputQRate', -DEG), ('AOA DEG', 'PitotTube.AngleOfAttack', DEG), ('LOAD G', 'Accelerometer.Acceleration', 1 / 9.81),
            ('PEAK G', 'Accelerometer.MaximumPositiveAcceleration', 1 / 9.81), ('CAS KT', 'AirDataComputer.OutputCalibratedAirspeed', 1.94384)]
for row, (text, src, k) in enumerate(tvc_rows):
    y = 499 - 56 * row
    tvc_items += [label(text, (120, y), BAY_FONT), number_of(src, 'Tvc%d' % row, (600, y), k, n=7, font=perf_font)]
# the A/T keys' legends, across, level with keys 1 and 3 of the right column (user 2026-11-06: the menu's own labels sat
# between the keys and read downwards). Calibrated on the user's SYS screenshot of 2026-11-07: the page rows (SYSTEMS
# 905 ... CAS KT 107) sit at screenshot y = 1264.5 - 0.9107 * page y (text centres, within 3 px); the right keys at 548 /
# 695 / 840 / 985 px -> page y 786 / 625 / 465 / 307. (The first placement, 710 / 557 / 425 / 288, came from a coarser
# reading and stood half a key low.) Keys 2 and 4 carry the menu's arrows.
at_font = dict(perf_font, FontSize=28.0, Stride=24.0)
obj(dyn, 'binary_to_text', 'F22AtKeyText', anchor, Input='F22AtActive.Output', Text0='A/T', Text1='*A/T')
tvc_items += [place_copy('UpFrontControllerLine0', 'F22TvcAtKey', Input=text_out('TvcAtKey', 'F22AtKeyText.Output'),
                         Position=' 894 786 ', Length='4', LeftJustified='false', **at_font),
              place_copy('UpFrontControllerLine0', 'F22TvcAtStep', Input=text_out('TvcAtStep', 'F22AtStepText.Output'),
                         Position=' 918 465 ', Length='3', LeftJustified='false', **at_font)]
g('graphics_animation_render_list', 'F22TvcPage', RenderList=' %s ' % ' '.join(tvc_items))
# HUD: the A/T's target under the airspeed box while the A/T holds (kt, Mach or AoA as on the SYS page; user
# 2026-11-07). Drawn into the HUD's own render list, so it goes through the same HUD_SCALE as the F/A-18 symbology
# (page units 0 .. 1024, centre 512 = boresight). Placed from the user's HUD screenshot: the donor's HUD is conformal
# (Radius 0.16 m about 0.7 m from the eye: ~40 page units per ladder degree), the 5 deg ladder step there is 117 px ->
# 0.59 px per unit; boresight at px (973, 257) (the FPV 58 px under it at 2.5 deg AoA), the speed box 806 .. 861 x 268
# px -> right edge at page x 313, the text's middle 30 px under the box's -> page y 442 (an estimate, to be checked
# in the game)
if H:
    g('graphics_input', 'GfxF22HudAtShow', InputID=('uint32', published('F22AtActive')))
    # Place (2026-11-07, the user's night screenshot with it showing at the first guess, 217 432): the speed box 113 px
    # wide there = ~99 page units (earlier screenshots) -> 1.14 px per unit; the number stood 47 px right of the box's
    # digits and 244 px under where it belongs, just below the box -> 41 units left, 214 up: right edge at page x 272
    # (field of 4 from 176), baseline 646. Next screenshot: right edge right, the number 38 px under the place just below
    # the box (box 92 px = 0.93 px per unit) -> baseline 687.
    # (Two builds showed nothing - drawn 0 1 0, then lit 3000. A test with letters always on found it: the HUD's
    # graphics_animation_display draws only the FIRST item of its RenderList - a letter put before the F/A-18 HUD
    # showed and the whole HUD was gone, those after it never showed. So the HUD and ours go into one render list. The
    # letter drawn white at 0 .. 1 was plainly visible: no lit colour is needed; ours in the HUD's pale green, in five
    # steps with the HUD brightness knob, as the symbology dims)
    at_txt = text_out('HudAtTarget', 'F22AtTargetText.Output')
    steps = []
    for k_ in range(5):
        lum = (k_ + 1) / 5.0
        steps.append(place_copy('UpFrontControllerLine0', 'F22HudAtTarget%d' % k_, Input=at_txt, Position=' 176 687 ',
                                Length='4', LeftJustified='false', FontID='0', FontSize=30.0, Stride=24.0,
                                Color=' %.3f %.3f %.3f 1.0 ' % (0.65 * lum, lum, 0.75 * lum)))
    g('graphics_linear_interpolation', 'F22HudAtLevel', Input='HUDBrightness.Output', Map=('tmvector2d', ' (0.0 0.0) (1.0 4.0) '))
    g('graphics_animation_render_switch', 'F22HudAtLit', Input='F22HudAtLevel.Output', RenderList=' %s ' % ' '.join(steps))
    g('graphics_animation_render_switch', 'F22HudAt', Input='GfxF22HudAtShow.Output', RenderList=' F22Nothing F22HudAtLit ')
    g('graphics_animation_render_list', 'F22HudWithOverlay', RenderList=' %s F22HudAt ' % copied[H['centre']].get('RenderList').strip())
    copied[H['centre']].set('RenderList', ' F22HudWithOverlay ')
n_tvc = 0
for o in G:
    if o.type == 'graphics_animation_render_switch' and o.find('RenderList') is not None and \
            'BuiltInTestPage' in o.get('RenderList').split():
        o.set('RenderList', ' ' + ' '.join('F22TvcPage' if t == 'BuiltInTestPage' else t
                                           for t in o.get('RenderList').split()) + ' ')
        n_tvc += 1
print('TVC page in %d MFD page switches' % n_tvc)
failures_f22.graphics(globals())           # FAIL page in place of the Hornet's UFC BU page
breakage_f22.fcs_status(globals())         # FCS page: surface status table beside the donor's page
breakage_f22.damage_graphics(globals())    # torn consoles / fins fly away on their bodies, stubs on the fuselage
failures_f22.gear_graphics(globals())      # the gear legs drawn where their joints are (folds, jams), not the handle
# No traffic on any cockpit screen: the Hornet's SA and radar pages and the C90's MFD hand their tmtraffic_display to an empty function in this build of the game (game code, arm64), and the
# Learjet's TCAS panel draws only its rings (tried 2026-11-01: an empty scope with traffic all round). Nothing in the configs can reach the traffic.
# TEMPORARY power recorder (the displays blink as each generator comes online), counted from 2 s after the APU is up,
# integrals only (a peak hold reading its own output made Aerofly recurse until its stack overflowed). Lower SMFD:
# - per bus the live voltage and the ms at zero (< 10 V), low (< 100 V, the displays' minimum), high (> 130 V);
#   first test: AC L / R low ~0.5 s per engine start, never zero, the generators and the APU never low;
# - AC L / R low split by whether the bus had a second feed (AC L: APU contactor closed, AC R: bus tie closed);
# - each contactor's live state (%) and the ms it spent between open and closed.
# Off = the FCS page back.
DIAG_POWER = False
lower_items = ['DDILower']
if DIAG_POWER:
    DIAG_FONT = dict(FontID='0', FontSize=18.0, Stride=16.2)
    obj(dyn, 'logic_confirm_delay', 'DiagArmed', anchor, Input='APUAvailable.Output', TimeUp=2.0, TimeDown=0.0001,
        Threshold=0.5)

    def timer(key, inputs):
        """ms during which all inputs (dynamics outputs) are > 0.5, while armed."""
        obj(dyn, 'logic_and', key + 'Armed', anchor, Inputs=' DiagArmed.Output %s ' % ' '.join(inputs))
        obj(dyn, 'integral', key + 'Time', anchor, Input=key + 'Armed.Output', Value=0.0)
        return key + 'Time.Output'

    def greater(key, a, b):
        obj(dyn, 'logic_greater', key, anchor, Input0=a, Input1=b)
        return key + '.Output'

    diag = [label('MS', (30, 970), 18), label('NOW', (110, 970), 18), label('ZERO', (180, 970), 18),
            label('LOW', (260, 970), 18), label('HIGH', (330, 970), 18)]
    for row, (text, bus, arm) in enumerate([('AC L', 'ACBusLeft', []), ('AC R', 'ACBusRight', []),
                                            ('GEN1', 'ACBusEngine1Generator', ['Engine1GeneratorContactor.Output']),
                                            ('GEN2', 'ACBusEngine2Generator', ['Engine2GeneratorContactor.Output']),
                                            ('EXT', 'ACBusExternalPower', [])]):
        y, k = 940 - 30 * row, 'Diag' + bus
        diag += [label(text, (30, y), 18), number_of(bus + '.Output', k + 'Now', (100, y), n=4, font=DIAG_FONT)]
        for col, (cond, a, b) in enumerate([('Zero', '10.0', bus + '.Output'), ('Low', '100.0', bus + '.Output'),
                                            ('High', bus + '.Output', '130.0')]):
            t = timer(k + cond, [greater(k + cond, a, b)] + arm)
            diag.append(number_of(t, k + cond, (180 + 75 * col, y), 1000.0, n=4, font=DIAG_FONT))
    diag += [label('LOW MS', (30, 790), 18), label('2 FEED', (165, 790), 18), label('1 FEED', (285, 790), 18)]
    for row, (text, bus, feed) in enumerate([('AC L', 'ACBusLeft', 'ExternalPowerContactor'),
                                             ('AC R', 'ACBusRight', 'ACBusTie')]):
        y, k = 762 - 28 * row, 'Diag' + bus
        fed = greater(k + 'SecondFeed', feed + '.Output', '0.5')
        alone = greater(k + 'OneFeed', '0.5', feed + '.Output')
        diag += [label(text, (30, y), 18),
                 number_of(timer(k + 'LowTwoFeeds', [k + 'Low.Output', fed]), k + 'LowTwo', (180, y), 1000.0, n=4,
                           font=DIAG_FONT),
                 number_of(timer(k + 'LowOneFeed', [k + 'Low.Output', alone]), k + 'LowOne', (300, y), 1000.0, n=4,
                           font=DIAG_FONT)]
    diag += [label('SW', (30, 706), 18), label('NOW', (75, 706), 18), label('MID', (140, 706), 18),
             label('SW', (215, 706), 18), label('NOW', (260, 706), 18), label('MID', (325, 706), 18)]
    for n_, (text, sw) in enumerate([('G1', 'Engine1GeneratorContactor'), ('G2', 'Engine2GeneratorContactor'),
                                     ('EX', 'ExternalPowerContactor'), ('TI', 'ACBusTie')]):
        x, y, k = 30 + 185 * (n_ % 2), 678 - 28 * (n_ // 2), 'Diag' + sw
        mid = timer(k + 'Mid', [greater(k + 'Above', sw + '.Output', '0.05'), greater(k + 'Below', '0.95', sw + '.Output')])
        diag += [label(text, (x, y), 18), number_of(sw + '.Output', k + 'Now', (x + 40, y), 100.0, n=3, font=DIAG_FONT),
                 number_of(mid, k + 'Mid', (x + 105, y), 1000.0, n=4, font=DIAG_FONT)]
    window('DiagPower', display_parts['DisplayLowerMFD'], diag)
    lower_items = ['DiagPower']
tex2 = copied['DisplayTexture'].clone()
tex2.name = 'DisplayTexture2'
tex2.set('TextureName', 'display2_light')
tex2.set('RenderList', ' %s UFDLeft UFDRightADI UFDRight ICPLines ICPScratch ' % ' '.join(lower_items))
G.insert(G.index(copied['DisplayTexture']) + 1, tex2)
for pname, d in sorted(display_parts.items()):
    if d['donor'] in copied:
        disp = copied[d['donor']]
        disp.set('R0', ' ' + fmt(d['centre']) + ' ', 'tmvector3d')
        disp.set('Radius', '%.4f' % d['radius'], 'float64')
    g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, **body('Fuselage'), InputLuminance=d['brightness'] + '.Output')
# display caps (ac DISPLAY_CAPS): the screen's still picture, lit as the screen, shown outside the pilot's own view
outside_cams = ' %s ' % ' '.join(c for c in cams if c != 'CameraPilot')
for pname, p in sorted(parts.items()):
    if p.get('cap') in display_parts:
        g('rigidbodygraphics', pname, GeometryList=' %s ' % pname, **body('Fuselage'),
          InputLuminance=display_parts[p['cap']]['brightness'] + '.Output', ShowInside=('uint32', outside_cams))
print('display objects copied from the F/A-18: %d' % len(copied))

gfx.children = G

for lst in (dyn, gfx, snd):
    seen, unique = set(), []
    for o in lst.children:
        if o.name not in seen:
            seen.add(o.name)
            unique.append(o)
    if len(unique) != len(lst.children):
        print('removed %d duplicate objects from %s' % (len(lst.children) - len(unique), lst.name))
    lst.children = unique

# ---------------------------------------------------------------------------------------------- cockpit clicks
# The stock F/A-18 click volumes (controls.tmd) moved onto the F-22 cockpit: MFD bezel buttons on the DCS button
# connectors (axis into the screen), switches / knobs / levers on their animated parts. The drag direction of a switch
# or lever is the way its part moves when the dynamics value it shows rises (sampled animation of the part's centre),
# a knob turns about its animation axis pointing into the panel; values are made positive accordingly.
def _rot(e):
    cx, cy, cz = (math.cos(a) for a in e)
    sx, sy, sz = (math.sin(a) for a in e)
    # Blender Euler 'XYZ': R = Rz @ Ry @ Rx
    return [[cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz],
            [cy * sz, sx * sy * sz + cx * cz, cx * sy * sz - sx * cz],
            [-sy, sx * cy, cx * cy]]


def _apply(link, a, p, pivot):
    """Position of point p with the part's link for one argument at value a (table lookup by nearest samples)."""
    xs = link['samples']
    i = min(range(len(xs)), key=lambda k: abs(xs[k] - a))
    R, t = _rot(link['euler'][i]), link['translation'][i]
    q = [p[k] - pivot[k] for k in range(3)]
    return [sum(R[r][k] * q[k] for k in range(3)) + pivot[r] + t[r] for r in range(3)]


def _unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _frame(axis):
    x = _unit(axis)
    ref = [0.0, 1.0, 0.0] if abs(x[1]) < 0.9 else [0.0, 0.0, 1.0]
    d = sum(r * c for r, c in zip(ref, x))
    y = _unit([r - d * c for r, c in zip(ref, x)])
    return x, y, _cross(x, y)


def _arg_values(arg):
    """DCS argument values for the dynamics value going low -> high."""
    d = C.DRIVERS[arg]
    if 'map' in d:
        pts = sorted(d['map'])
        return pts[0][1], pts[-1][1]
    return d['range']


def _lerp(pts, x):
    pts = sorted(pts)
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def _lever_angle(args):
    """Lever angle (rad) as a function of the dynamics value, rotation axis and pivot, summed over the DCS cockpit
    arguments of one part (throttle travel + cut-off detent); the part rests at all arguments 0."""
    links = []
    for arg in args:
        key = C.COCKPIT_ARG_BASE + arg
        pname = next(n for n, p in anim.items() if any(l['arg'] == key for l in p['links']))
        link = next(l for l in anim[pname]['links'] if l['arg'] == key)
        d = C.DRIVERS[key]
        links.append((link, d.get('map'), d['range'], anim[pname]['pivot']))
    de = [abs(e1 - e0) for e0, e1 in zip(links[0][0]['euler'][0], links[0][0]['euler'][-1])]
    i = max(range(3), key=lambda k: de[k])

    def angle(v):
        total = 0.0
        for link, m, rng, _ in links:
            a = _lerp(m, v) if m else min(max(v, rng[0]), rng[1])
            total += _lerp(list(zip(link['samples'], (e[i] for e in link['euler']))), a)
        return total
    return angle, [float(k == i) for k in range(3)], links[0][3]


def make_controls():
    root_c = tmd.load(os.path.join(DONOR, 'controls.tmd'))
    lst = root_c.children[0].children[0].children[0]
    f18c = {c.name: c for c in lst.children}
    eye = C.MEASURE['eye']
    out = []

    def place(c, r0, axis, direction=None, transform=None, positive=True):
        x, y, z = _frame(axis)
        c.set('R0', ' ' + fmt(r0) + ' ', 'tmvector3d')
        c.set('B0', ' %s  %s  %s ' % (fmt(x), fmt(y), fmt(z)), 'tmmatrix3d')
        if direction is not None and c.find('Direction') is not None:
            c.set('Direction', ' ' + fmt(_unit(direction)) + ' ', 'tmvector3d')
        # no InputTransform: click volumes are linked while the dynamics load, before the graphics exist - a
        # graphics transform there ('object A_..._R2 not found') stopped the aircraft from loading (STOP sign)
        it = c.find('InputTransform')
        if it is not None:
            c.children.remove(it)
        if positive:
            for m in c.walk():
                v = m.find('Value') if not m.leaf else None
                if v is not None and v.value.strip().startswith('-'):
                    v.value = v.value.strip()[1:]
        out.append(c)

    # MFD bezel buttons: F/A-18 values 0-4 bottom row (left to right), 5-9 left column and 10-14 right column (top
    # to bottom), 15-19 top row (left to right); DCS points 1-5 top row left to right, 6-10 right column top to
    # bottom, 11-15 bottom row right to left, 16-20 left column bottom to top
    point_of = {}
    for v in range(5):
        point_of[15 + v] = 1 + v
        point_of[10 + v] = 6 + v
        point_of[v] = 15 - v
        point_of[5 + v] = 20 - v
    for d in getattr(C, 'CLICK_MFDS', []):
        c_, dn, rt = (CONNECTORS[k] for k in d['quad'])
        nrm = _unit(_cross([a - b for a, b in zip(rt, c_)], [a - b for a, b in zip(c_, dn)]))
        if sum(n_ * (e - p) for n_, e, p in zip(nrm, eye, c_)) > 0:
            nrm = [-x for x in nrm]                       # into the screen
        for name, c in f18c.items():
            if not name.startswith(d['f18']):
                continue
            m = [x for x in c.walk() if not x.leaf and x.find('Value') is not None][0]
            pt = CONNECTORS.get('%s%d_PNT' % (d['points'], point_of[int(round(float(m.get('Value'))))]))
            if pt is not None:
                c = c.clone()
                if 'rename' in d:
                    c.name = c.name.replace(*d['rename'])
                    for x in c.walk():
                        if x.leaf and x.name == 'Message':
                            x.value = x.value.replace(*d['rename'])
                place(c, pt, nrm, direction=nrm, positive=False)
    # switches, knobs, levers on animated cockpit parts
    for name, arg, kind, *message in getattr(C, 'CLICK_PARTS', []):
        if name not in f18c:
            print('WARNING click template %s missing in the F/A-18 controls' % name)
            continue
        key = C.COCKPIT_ARG_BASE + arg
        pname = next((n for n, p in anim.items() if any(l['arg'] == key for l in p['links'])), None)
        if pname is None or 'bbox' not in parts.get(pname, {}):
            print('WARNING no animated part for cockpit argument %d' % arg)
            continue
        link = next(l for l in anim[pname]['links'] if l['arg'] == key)
        pivot = anim[pname]['pivot']
        lo, hi = parts[pname]['bbox']
        ctr = [(a + b) / 2 for a, b in zip(lo, hi)]
        grip = getattr(C, 'CLICK_GRIPS', {}).get(name)
        if grip:                     # the grip of a lever, not the middle of its whole part (pivot to knob)
            ctr = list(grip[0])
        a0, a1 = _arg_values(key)
        c = f18c[name].clone()
        if message:                  # an F/A-18 control as the template of an F-22 one with its own message
            c.name = '%s_%d' % (name, arg)
            for m in c.walk():
                if not m.leaf and m.find('Message') is not None:
                    m.set('Message', message[0], 'string8')
        if kind == 'knob':
            de = [e1 - e0 for e0, e1 in zip(link['euler'][0], link['euler'][-1])]
            i = max(range(3), key=lambda k: abs(de[k]))
            axis = [float(k == i) * (1 if de[i] > 0 else -1) for k in range(3)]   # +rotation = arg rising
            if (link['samples'][-1] - link['samples'][0]) * (a1 - a0) < 0:
                axis = [-x for x in axis]                                          # value rising = arg falling
            if sum(a * (e - p) for a, e, p in zip(axis, eye, ctr)) > 0:
                axis = [-x for x in axis]
                for m in c.walk():
                    v = m.find('Value') if not m.leaf else None
                    if v is not None:
                        v.value = '%g' % -abs(float(v.value))
                place(c, ctr, axis, direction=axis, transform=PART_XFORM.get(pname), positive=False)
            else:
                place(c, ctr, axis, direction=axis, transform=PART_XFORM.get(pname))
            continue
        p0, p1 = _apply(link, a0, ctr, pivot), _apply(link, a1, ctr, pivot)
        move = [b - a for a, b in zip(p0, p1)]
        lever_axis = [a - b for a, b in zip(ctr, pivot)]
        place(c, ctr, lever_axis if kind == 'toggle' else _cross(move, lever_axis), direction=move,
              transform=PART_XFORM.get(pname))
        if grip:
            c.set('Radius', '%g' % grip[1][0], 'float64')
            c.set('Length', '%g' % grip[1][1], 'float64')
    # console switches, knobs and buttons cut out of the static DCS object (ac CLICK_SWITCHES): an F/A-18 template at
    # the part, its message replaced by the F-22 one (None: the template's own - the F/A-18 system it drives)
    for tpl, point, axis, direction, message, size in getattr(C, 'CLICK_SWITCHES', []):
        c = f18c[tpl].clone()
        c.name = 'F22Sw_' + (re.sub(r'\W', '', message) if message else tpl)
        if message:
            for m in c.walk():
                if not m.leaf and m.find('Message') is not None:
                    m.set('Message', message, 'string8')
        place(c, point, axis, direction=direction if direction is not None else axis, positive=True)
        if size:
            c.set('Radius', '%g' % size[0], 'float64')
            c.set('Length', '%g' % size[1], 'float64')
    for name, point, axis, direction, size in getattr(C, 'CLICK_POINTS', []):
        if isinstance(point, str):
            point = CONNECTORS[point]
        elif isinstance(point[0], str):
            point = [sum(CONNECTORS[k][i] for k in point) / len(point) for i in range(3)]
        c = f18c[name].clone()
        n_same = sum(1 for o_ in out if o_.name.startswith(name))
        if n_same:
            c.name = '%s%d' % (name, n_same + 1)
        place(c, point, axis, direction=direction, positive=False)
        if size:
            c.set('Radius', '%g' % size[0], 'float64')
            c.set('Length', '%g' % size[1], 'float64')
    # ICP keys and UFD buttons: F/A-18 UFC key templates with the F-22 function's message, pushed forward (+x)
    for point, tpl, message, value, qualifier, *size in getattr(C, 'CLICK_ICP', []) + getattr(C, 'CLICK_UFD', []):
        c = f18c[tpl].clone()
        c.name = 'F22Key_' + (point if isinstance(point, str) else re.sub(r'\W', '', message))
        m = next(x for x in c.walk() if not x.leaf and x.find('Message') is not None)
        m.set('Message', message, 'string8')
        m.set('Value', '%g' % value, 'float64')
        m.set('Qualifiers', ' %s ' % qualifier, 'string8')
        # size: key face (square), or (width, height) of a key face; a knob (thumbwheel) gets a cylinder along its
        # axle (y) with the wheel's radius and width - the first build's 18 mm disk facing the pilot was far wider
        # than the 8 mm wheel
        k_ = size[0] if size else getattr(C, 'ICP_KEY_SIZE', 0.015)
        knob = c.find('Dimensions') is None
        axis = [0.0, 1.0, 0.0] if knob else [1.0, 0.0, 0.0]
        place(c, CONNECTORS[point] if isinstance(point, str) else point, axis, direction=axis, positive=False)
        if not knob:
            c.set('Dimensions', ' 0.004 %g %g ' % (k_, size[1] if len(size) > 1 else k_), 'tmvector3d')
        else:
            c.set('Radius', '%g' % (k_ / 2), 'float64')
            if len(size) > 1:
                c.set('Length', '%g' % size[1], 'float64')
    for name, tpl, point, offset, push, dims, message, value, *qual in getattr(C, 'CLICK_BUTTONS', []):
        c = f18c[tpl].clone()
        c.name = name
        place(c, [a + b for a, b in zip(CONNECTORS[point], offset)], push, direction=push, positive=False)
        c.set('Dimensions', ' ' + fmt(dims) + ' ', 'tmvector3d')
        m = next(x for x in c.walk() if not x.leaf and x.find('Message') is not None)
        m.set('Message', message, 'string8')
        m.set('Value', '%g' % value, 'float64')
        if qual:
            m.set('Qualifiers', qual[0], 'string8')
    # volumes turning with their lever: control_input (dynamics output, scaled to the lever angle) -> control_rotation
    transforms = {}
    for c in out:
        if c.name not in getattr(C, 'CLICK_FOLLOW', {}):
            continue
        src, args, *rng = C.CLICK_FOLLOW[c.name]
        lo_, hi_ = rng[0] if rng else (-0.2, 1.0)        # throttles: -0.2 cut-off .. 1 full, linear through both ends
        if src not in transforms:
            angle, axis, pivot = _lever_angle(args)
            ci = f18c['Engine1ThrustLeverPosition'].clone()
            ci.name = 'Click%s' % src
            ci.set('InputID', '%s.Output' % src, 'uint32')
            k = (angle(hi_) - angle(lo_)) / (hi_ - lo_)
            ci.set('Scaling', '%.6f' % k, 'float64')
            ci.set('Offset', '%.6f' % (angle(hi_) - k * hi_), 'float64')
            print('click volumes on %s: %.3f + %.3f x rad about %s (off at 0 by %.3f rad)'
                  % (src, angle(hi_) - k * hi_, k, axis, angle(hi_) - k * hi_ - angle(0.0)))
            cr = f18c['Engine1ThrustLeverTransform'].clone()
            cr.name = 'Click%sTransform' % src
            cr.set('Input', '%s.Output' % ci.name, 'string8')
            cr.set('Axis', ' ' + fmt(axis) + ' ', 'tmvector3d')
            cr.set('Pivot', ' ' + fmt(pivot) + ' ', 'tmvector3d')
            transforms[src] = (ci, cr)
        c.set('InputTransform', 'Click%sTransform.Output' % src, 'string8')
    out[:0] = [n for pair in transforms.values() for n in pair]
    lst.children = out
    print('cockpit click volumes: %d' % len(out))
    return root_c


# ---------------------------------------------------------------------------------------------- write
press_resolve()
tvc_f22.apply(dyn)
# stabilators: hydraulic power and the BIT program on the vector law's tail commands (the first build gated the
# Hornet's taileron outputs, which tvc_f22 no longer feeds to the servos - the stabilators kept moving with no hydraulic
# pressure, found 2026-11-05 tracing the data flow)
for name in ('ServoLeftStabilator', 'ServoRightStabilator'):
    node = dyn_node(name)
    old = bit_command(name, node.get('Input').strip())
    obj(dyn, 'product', 'F22Hyd' + name, node, Inputs=' %s F22HydAuthority.Output ' % old)
    node.set('Input', 'F22Hyd%s.Output' % name, 'string8')
nz = next(o for o in dyn.children if o.name == 'NozzleAngle')      # nozzles: fuel-actuated, F22NozzleActuation
obj(dyn, 'product', 'F22NozzleCommandPowered', nz, Inputs=' %s F22NozzleActuation.Output ' % nz.get('Input').strip())
nz.set('Input', 'F22NozzleCommandPowered.Output', 'string8')
failures_f22.after_tvc(globals())          # NOZZLE failure: the command frozen
breakage_f22.apply(globals())              # wing consoles break at 13.5 g; mechanics tests via F22_TEST=...
burner_f22.apply(gfx, dyn, parts)
os.makedirs(OUT, exist_ok=True)
tmd.save(root, os.path.join(OUT, NAME + '.tmd'))
# flight states of the F/A-18; cold & dark as an F-22 stands on the ramp: canopy open (the lever at 0 holds it
# until the pilot closes it, with power), position and formation lights off (the Hornet's are set to 50 / 40 %)
STATE_EXTRA = {'clean': [('servoclassic', 'F22MainGearCtlL', 'Position', 1.0),   # gear up: the rate-limited
                          ('servoclassic', 'F22MainGearCtlR', 'Position', 1.0),   # cylinder commands start up
                          ('servoclassic', 'F22NoseGearSmooth', 'Position', 1.0),   # (failures_f22, 1 = up)
                          ('integral_clamped', 'F22LegUpHeldL', 'Value', 1.0),    # up-locks caught (no amber blink
                          ('integral_clamped', 'F22LegUpHeldR', 'Value', 1.0),    # at an airborne start)
                          ('integral_clamped', 'F22LegUpHeldN', 'Value', 1.0)],
               'start': [('input_discrete', 'F22ApuSwitch', 'Value', 0.0),      # the donor's start state has the APU
                          ('variable', 'F22ApuRun', 'Value', 1.0)],               # running: ARM, latched on
               'cold': [('servoclassic', 'CanopySequence', 'Position', 1.0),
                        ('input_discrete', 'CanopyLever', 'Value', 0.0),
                        ('input_default', 'PositionLightBrightnessKnob', 'Value', 0.0),
                        ('input_default', 'FormationLightBrightnessKnob', 'Value', 0.0),
                        ('input_discrete', 'StrobeLightSwitch', 'Value', 0.0),
                        # interior lights off (the Hornet's start values 0.4 / 0.4 / 0.6 stood in every state). MFD,
                        # UFD and HUD brightness keep their knob positions: dark without power, readable once it is on
                        ('input_default', 'PanelLightKnob', 'Value', 0.0),
                        ('input_default', 'ConsoleBrightnessKnob', 'Value', 0.0),
                        ('input_default', 'FloodLightKnob', 'Value', 0.0),
                        # (user 2026-11-06: CNI, AUX and the generators stood ON on a cold start) the console
                        # switches as the aircraft is left: CNI / ACP off, generators off, APU OFF, FLCS STOP
                        ('input_discrete', 'F22CNISwitch', 'Value', 0.0),
                        ('input_discrete', 'F22ACPSwitch', 'Value', 0.0),
                        ('input_switch', 'Engine1GeneratorSwitch', 'Value', 0.0),
                        ('input_switch', 'Engine2GeneratorSwitch', 'Value', 0.0),
                        ('input_discrete', 'F22ApuSwitch', 'Value', -1.0),
                        ('input_discrete', 'F22FlcsBitSwitch', 'Value', -1.0)]}
for suffix in ('clean', 'cold', 'flaps', 'gear', 'landing', 'start', 'takeoff'):        # no carrier start
    src = os.path.join(DONOR, 'f18_%s.tmd' % suffix)
    if os.path.exists(src):
        st = tmd.load(src)
        lst_ = st.children[0].children[0].children[0]
        lst_.children = [o for o in lst_.children if not (NO_F22.search(o.name) or FLAP_LEVER.search(o.name))]
        for o in lst_.children:          # Hornet landing light off (0) / on -> F-22 OFF (1) / LDG (2)
            if o.name == 'LandingLightSwitch' and o.find('Value') is not None:
                o.set('Value', '%g' % (1.0 if float(o.get('Value')) < 0.5 else 2.0), 'float64')
        # pitch trim 0 in every state (make_f22 'Pitch trim'): the ground states set none and the Hornet's flight
        # controller started at its takeoff trim, 50 % nose up (user 2026-11-15, after the trim went to 0 for good)
        for type_, name, field, value in STATE_EXTRA.get(suffix, []) + [('flight_controller_f18', 'FlightController',
                                                                         'PitchTrim', 0.0)]:
            node = next((o for o in lst_.children if o.name == name), None)
            if node is None:
                node = tmd.Node(type_, name, leaf=False)
                lst_.children.append(node)
            node.set(field, '%g' % value, 'float64')
        tmd.save(st, os.path.join(OUT, '%s_%s.tmd' % (NAME, suffix)))
tmd.save(make_controls(), os.path.join(OUT, 'controls.tmd'))


# ---- load variants (stage 6): add-ons as the F/A-18's external tank add-ons (option.tmc Type addon, parameters.tmd
# overriding the base's switch, system.tmd adding bodies, aerodynamics and graphics) and repaints of the default livery
# that require them (the livery selector is Aerofly's only load choice: the MB-339's tip-tank liveries)
def addon_file(dyn_nodes, gfx_nodes=()):
    root = tmd.Node('file', '', leaf=False)
    mm = tmd.Node('modelmanager', '', leaf=False)
    dl = tmd.Node('pointer_list_tmuniverse', 'DynamicObjects', leaf=False)
    dl.children = list(dyn_nodes)
    mm.children.append(dl)
    if gfx_nodes:
        gl = tmd.Node('pointer_list_tmgraphics', 'GraphicObjects', leaf=False)
        gl.children = list(gfx_nodes)
        mm.children.append(gl)
    root.children.append(mm)
    doc = tmd.Node('document', '', leaf=False)          # tmd.save writes the children of the node it gets
    doc.children.append(root)
    return doc


def write_option(folder, description, type_, tags=None, requirements=None):
    os.makedirs(folder, exist_ok=True)
    extra = ('    <[string8][Tags][ %s ]>\n' % tags if tags else '') + \
            ('    <[string8][Requirements][ %s ]>\n' % requirements if requirements else '')
    open(os.path.join(folder, 'option.tmc'), 'w', encoding='utf-8', newline='\n').write(
        '<[file][][]\n  <[object][][]\n    <[string8][Description][%s]>\n    <[string8][Type][%s]>\n%s  >\n>\n'
        % (description, type_, extra))


holder = tmd.Node('list', 'x', leaf=False)
vec3 = lambda v: ('tmvector3d', ' %s ' % fmt(v))
farr = lambda xs: ('float64', '[ %s ]' % ' '.join('%.4f' % x for x in xs))     # as the F/A-18's: float64 [ ... ]
# combat load: 6 x AIM-120C (157 kg) + 2 x AIM-9X (85 kg) as one mass in the bays, locked to the fuselage
combat_dyn = [obj(holder, 'linear', 'F22CombatLoad', Input='1.0')]
combat_sys = [obj(holder, 'rigidbody', 'F22CombatLoadBody', Mass=6 * 157.0 + 2 * 85.0, InertiaLength=vec3([3.6, 2.6, 0.4]),
                  R0=vec3([2.45, 0.0, -0.45]), B0=('tmmatrix3d', ' 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0 ')),
              obj(holder, 'multibody_joint', 'JointF22CombatLoad', Body0='Fuselage', Body1='F22CombatLoadBody',
                  R0=vec3([2.45, 0.0, -0.45]), X0=vec3([1.0, 0.0, 0.0]), Kp=0.0, Kd=0.0, Type=('uint32', '1'),
                  InputLock='1.0')]
ad = os.path.join(OUT, 'load_combat')
write_option(ad, 'Combat load: 6 AIM-120C, 2 AIM-9X', 'addon', tags='loads_combat')
tmd.save(addon_file(combat_dyn), os.path.join(ad, 'parameters.tmd'))
tmd.save(addon_file(combat_sys), os.path.join(ad, 'system.tmd'))
# ferry tanks: each tank with its pylon a body of its own (2050 kg: 236 kg tank and pylon, est., + 1814 kg fuel - the
# mass stays the full one, as the internal fuel's), drag of the tank (its profile) and the pylon; on an ejector rack
# through a breakable joint, its hull on a body of its own (breakage_f22.tank_addon: EMER JETT drops tank and pylon)
ferry_dyn = [obj(holder, 'linear', 'F22FerryTanks', Input='1.0')]
ferry_sys, ferry_gfx = [], []
prof = [(0.0, 0.0), (0.04, 0.17), (0.10, 0.40), (0.20, 0.68), (0.30, 0.88), (0.40, 1.0), (0.66, 1.0), (0.80, 0.82),
        (0.94, 0.53), (1.0, 0.47)]
nose = [p for p in prof if p[0] <= 0.40]
for side, st in (('L', 'Pylon2'), ('R', 'Pylon10')):
    y = S.CONN[st][1]
    zc = S.TANK_TOP_Z - 0.425
    body_name = 'F22Tank%sBody' % side
    cg = [S.TANK_NOSE_X - 3.2, y, zc + 0.05]
    t_dyn, t_gfx = breakage_f22.tank_addon(obj, holder, side, body_name, cg, S.TANK_FUEL,
                                           (S.TANK_NOSE_X - 0.6, S.TANK_NOSE_X - 6.1), zc, 'ColStoreTank' + side)
    # the shell (tank and pylon, empty): its fuel hangs beside it as slugs (breakage_f22.tank_addon); a thin shell -
    # InertiaLength 6.7 / 1.04 / 1.04 gives a thin cylinder's m r2 about its axis
    ferry_sys += [
        obj(holder, 'rigidbody', body_name, Mass=breakage_f22.TANK_SHELL, InertiaLength=vec3([6.7, 1.04, 1.04]),
            R0=vec3(cg), B0=('tmmatrix3d', ' 1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0 ')),
        # the shell's aerodynamics as a slender body (breakage_f22: the fall): the whole length gives drag - along
        # (Cdx) and the viscous cross-flow drag of a cylinder (~1.0), which damps a tumble - and no lift; the
        # cross-flow lift sits on the nose, where the section grows (to the full diameter at 40 %): ahead of the
        # centre of gravity, so the finless tank is unstable in pitch and yaw. (Lift along the whole length, Cly / Clz
        # 0.3 as the F/A-18's tanks, put its centre on the centre of gravity: the shell fell without turning, also with
        # Cm 0.5 - in-game 2026-11-13)
        obj(holder, 'aerofuselage', 'F22Tank%sAero' % side, Body=body_name,
            StationX=farr([S.TANK_NOSE_X - f * 6.7 for f, _ in prof]), StationY=farr([y] * len(prof)),
            StationZ=farr([zc] * len(prof)), StationWidth=farr([0.85 * r for _, r in prof]),
            StationHeight=farr([0.85 * r for _, r in prof]), StationShape=('uint32', '[ %s ]' % ' '.join(['0'] * len(prof))),
            Cdx=0.05, Cdy=1.0, Cdz=1.0, Cly=0.0, Clz=0.0, Cm=0.0),
        obj(holder, 'aerofuselage', 'F22Tank%sNoseAero' % side, Body=body_name,
            StationX=farr([S.TANK_NOSE_X - f * 6.7 for f, _ in nose]), StationY=farr([y] * len(nose)),
            StationZ=farr([zc] * len(nose)), StationWidth=farr([0.85 * r for _, r in nose]),
            StationHeight=farr([0.85 * r for _, r in nose]), StationShape=('uint32', '[ %s ]' % ' '.join(['0'] * len(nose))),
            Cdx=0.0, Cdy=0.0, Cdz=0.0, Cly=breakage_f22.TANK_NOSE_CL, Clz=breakage_f22.TANK_NOSE_CL, Cm=0.0),
        obj(holder, 'aerodynamic_drag', 'F22Pylon%sDrag' % side, Body=body_name, X0=vec3([1.0, 0.0, 0.0]),
            R0=vec3([0.2, y, S.TANK_TOP_Z + 0.15]), Area=0.04)] + t_dyn
    ferry_gfx += t_gfx
ad = os.path.join(OUT, 'load_ferry')
write_option(ad, 'Ferry tanks: 2 x 600 US gal', 'addon', tags='loads_ferry')
tmd.save(addon_file(ferry_dyn), os.path.join(ad, 'parameters.tmd'))
tmd.save(addon_file(ferry_sys, ferry_gfx), os.path.join(ad, 'system.tmd'))
# load repaints (listed for the converter in model.tmc by make_f22_meta.py); like every stock repaint each holds a
# texture - an unchanged copy of the smallest one (the 64 px formation light)
for folder, description, load in (('combat', 'US Air Force - combat load', 'load_combat'),
                                  ('ferry', 'US Air Force - ferry tanks', 'load_ferry')):
    write_option(os.path.join(OUT, folder), description, 'repaint', requirements=load)
    if os.path.exists(os.path.join(OUT, 'lamp_formation_color.png')):     # converter input; absent in a release install
        shutil.copy(os.path.join(OUT, 'lamp_formation_color.png'), os.path.join(OUT, folder))
print('variants: load_combat, load_ferry add-ons; repaints combat, ferry')
print('graphics objects %d; strut ext nose %.3f main %.3f (arm %s); DCS stroke %s' % (len(G), NOSE_EXT, MAIN_EXT, {k: tuple(round(x, 3) for x in v) for k, v in ARM.items()}, dcs_stroke))
print('written', OUT)

