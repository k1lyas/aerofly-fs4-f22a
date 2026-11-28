"""List references in an Aerofly .tmd that point to objects which do not exist.

    python3 check_refs.py <aircraft.tmd>

uint32 *ID fields point into the dynamic list; string8 references inside the graphics/sound lists point
into the same list. A missing target makes the input silently read 0 in the game.
"""
import sys, re
import tmd

root = tmd.load(sys.argv[1])
mm = root.children[0].children[0]
lists = {n: mm.find(n) for n in ('DynamicObjects', 'GraphicObjects', 'SoundObjects')}
names = {n: {o.name for o in l.children} for n, l in lists.items()}
REF = re.compile(r'\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b')
missing = {}
for ln, lst in lists.items():
    for o in lst.children:
        for c in o.children:
            if c.type not in ('string8', 'uint32') or not c.value or c.name.endswith('File'):
                continue
            target = 'DynamicObjects' if c.type == 'uint32' or c.name.endswith('ID') else ln
            for obj, _ in REF.findall(c.value):
                if obj in ('Controls', 'Aircraft', 'Autopilot', 'Navigation', 'FlightManagementSystem', 'Yoke',
                           'IceProtection', 'Lights', 'Cockpit', 'Engines', 'Simulation', 'Doors', 'Camera', 'Performance',
                           'Warnings', 'Communication', 'Aircraft'):
                    continue
                if obj not in names[target]:
                    missing.setdefault((ln, obj), []).append('%s.%s' % (o.name, c.name))
# `output` objects are terminal: only graphics/sound may read them; a dynamics object taking one as an input makes
# the whole .tmd fail to load ("property 'X.Output' not found" -> STOP sign in the game)
dyn_types = {o.name: o.type for o in lists['DynamicObjects'].children}
bad_out = []
for o in lists['DynamicObjects'].children:
    for c in o.children:
        if c.type == 'string8' and c.value and not c.name.endswith('File') and not c.name.startswith('Message'):
            for obj, prop in REF.findall(c.value):    # (Message fields hold message paths, not object references)
                if dyn_types.get(obj) in ('output', 'output_free'):
                    bad_out.append('%s.%s -> %s.%s' % (o.name, c.name, obj, prop))
for b in bad_out:
    print('DYNAMICS READS OUTPUT', b)
# a constant in an Inputs list written as 6.6e-05 is read as object '6' (property '6.6e-05' not found -> STOP sign,
# 2026-11-27; 2.6e-07 in 2026-11-13): constants there in plain decimals
ENOT = re.compile(r'(?<![\w.])[-+]?\d+(\.\d+)?[eE][-+]?\d+')
for ln, lst in lists.items():
    for o in lst.children:
        for c in o.children:
            if c.type == 'string8' and c.name == 'Inputs' and c.value and ENOT.search(c.value):
                print('E-NOTATION IN INPUTS %s.%s: %s' % (o.name, c.name, c.value.strip()))
# a RenderList names graphics objects bare (no .Output): a missing one fails the whole .tmd ("object 'X' not found",
# tmd error hint 'RenderList X' -> STOP sign, 2026-11-28: the MSL TEST page appended to G after gfx.children was split
# off it)
for o in lists['GraphicObjects'].children:
    for c in o.children:
        if c.name == 'RenderList' and c.value:
            for tok in c.value.split():
                if tok not in names['GraphicObjects']:
                    print('RENDERLIST MISSING %s.%s -> %s' % (o.name, c.name, tok))
print('dynamics reading output objects:', len(bad_out))
for (ln, obj), users in sorted(missing.items()):
    print('%-15s %-40s <- %s%s' % (ln[:-7], obj, ', '.join(users[:4]), ' ...+%d' % (len(users) - 4) if len(users) > 4 else ''))
print('missing targets:', len(missing))

# every object property must be one the game knows for that type: an unknown one ("property 'X' is not a member of
# type 'Y'") fails the whole .tmd -> STOP sign (graphics_hud.InputLuminance did). Known = used by a stock aircraft.
import glob, os
STOCK = os.path.expanduser('~/Library/Application Support/Steam/steamapps/common/Aerofly FS 4 Flight Simulator/aircraft')
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.stock_properties.txt')
if os.path.exists(CACHE):
    known = {tuple(l.rstrip('\n').split('\t')) for l in open(CACHE) if l.strip()}
else:
    known = set()
    for f in glob.glob(os.path.join(STOCK, '*', '*.tmd')):
        try:
            r = tmd.load(f)
        except Exception:
            continue
        for o in r.walk():
            for c in o.children:
                if c.name and o.type:
                    known.add((o.type, c.name))
    open(CACHE, 'w').write('\n'.join('%s\t%s' % k for k in sorted(known)))
types = {t for t, _ in known}
unknown = sorted({(o.type, c.name, o.name) for l in lists.values() for o in l.children for c in o.children
                  if c.name and o.type in types and (o.type, c.name) not in known})
for t, prop, name in unknown:
    print('UNKNOWN PROPERTY %s.%s (object %s) - not used by any stock aircraft' % (t, prop, name))
print('unknown properties:', len(unknown))
# one geometry drawn by two graphics objects stops the model from loading ("geometry 'X' is used multiple times (2)
# in tmgraphics objects" -> STOP sign; F-22, the HUD projection drawn twice, 2026-10-22)
from collections import Counter
geo_use = Counter(n for o in lists['GraphicObjects'].children if o.find('GeometryList') is not None
                  for n in o.get('GeometryList').split())
for n, k in sorted(geo_use.items()):
    if k > 1:
        print('UNKNOWN GEOMETRY USED %d TIMES: %s' % (k, n))
print('geometries used more than once:', sum(1 for k in geo_use.values() if k > 1))
