"""Write the F-22A aircraft card (.tmc), copilot hints, option.tmc and the converter model.tmc.

    python3 make_f22_meta.py <f18 dir> <geometry.json> <parts.json> <out dir>
Based on the F/A-18 files; performance data of the F-22A.
"""
import sys, os, re, json, glob

DONOR, GEOM, PARTS, OUT = sys.argv[1:5]
geo = json.load(open(GEOM, encoding='utf-8'))
pj = json.load(open(PARTS, encoding='utf-8'))
# release version (release/install.py sets F22_VERSION from the package's VERSION file); empty in a development build
VERSION = os.environ.get('F22_VERSION', '')
w = {x['which']: x for x in geo['wheels']}
n, l = w['nose'], w['left']
ground = min(x['lowest_z'] for x in geo['wheels'])

DESCRIPTION = (
    "The Lockheed Martin F-22A Raptor is a single-seat, twin-engine stealth air superiority fighter. Two Pratt & "
    "Whitney F119 turbofans with two-dimensional thrust vectoring nozzles give 156 kN of thrust each with "
    "afterburner and allow supercruise without afterburner. Unofficial fan-made add-on%s, free under GPL-3: 3D model "
    "from the Grinnelli Designs DCS World mod, flight model and systems built on the F/A-18."
    % (' v' + VERSION if VERSION else ''))
LANGS = ['en', 'br', 'cn', 'de', 'es', 'fr', 'id', 'it', 'jp', 'kr', 'pl', 'sv', 'th', 'tr']

t = open(os.path.join(DONOR, 'f18.tmc'), encoding='utf-8').read()
descs = '\n'.join("""            <[localized_text][element][{i}]
                <[string8u][Language][{l}]>
                <[string8][Text][{t}]>
            >""".format(i=i, l=lang, t=DESCRIPTION) for i, lang in enumerate(LANGS))
t = re.sub(r'(<\[list_localized_text\]\[Descriptions\]\[\]\n).*?(\n        >\n)', lambda m: m.group(1) + descs + m.group(2), t,
           flags=re.S)
values = {
    'ContactSpheres': ' (%.3f 0.0 %.3f %.3f) (%.3f %.3f %.3f %.3f) (%.3f -%.3f %.3f %.3f) ' % (
        n['center'][0], n['center'][2], n['radius'], l['center'][0], abs(l['center'][1]), l['center'][2], l['radius'],
        l['center'][0], abs(l['center'][1]), l['center'][2], l['radius']),
    'ICAO': 'F22', 'DisplayName': 'F-22A', 'DisplayNameFull': 'Lockheed Martin F-22A Raptor',
    'MaximumTaxiMass': '38000.0', 'MaximumTakeoffMass': '38000.0', 'MaximumLandingMass': '29000.0',
    'MaximumZeroFuelMass': '28000.0', 'OperatingEmptyMass': '19700.0', 'MaximumFuelMass': '8200.0',
    'MaximumPersonsOnBoard': '1', 'WingSpan': '13.56', 'WingArea': '78.0', 'Length': '18.9', 'Height': '5.08',
    'NoseWheelPosition': '%.4f' % n['center'][0], 'Year': '2005', 'UnitsBuilt': '195', 'EngineThrust': '156000.0',
    'MinimumAirspeed': '60.0', 'ApproachAirspeed': '75.0', 'MaximumMachNumber': '2.25', 'MaximumAltitude': '19800.0',
    'MaximumRange': '2960000.0', 'MaximumLoadRange': '2500000.0', 'MaximumFuelRange': '2960000.0',
    'MaximumFerryRange': '3200000.0',
}
for k, v in values.items():
    t = re.sub(r'(<\[[^\]]+\]\s*\[%s\]\s*\[)[^\]]*(\])' % k, lambda m: m.group(1) + v + m.group(2), t)
# land based: no catapult start, no wing fold (the arresting hook stays - the F-22 has one)
t = re.sub(r'(\[Tags\]\[[^\]]*)', lambda m: m.group(1).replace(' catapult_hook', '').replace(' wingfold', ''), t)
open(os.path.join(OUT, 'f22.tmc'), 'w', encoding='utf-8', newline='\n').write(t)

c = open(os.path.join(DONOR, 'copilot.tmc'), encoding='utf-8').read()
c = re.sub(r'// F/?A-18\S*[^\n]*', '// F-22A Raptor', c)
for k, v in {'MaximumTakeoffMass': '38000.0', 'DefaultGrossMass': '26000.0', 'WingSpan': '13.56',
             'WingArea': '78.0', 'HeightOffset': '%.3f' % ground, 'NoseWheelPositionX': '%.4f' % n['center'][0]}.items():
    c = re.sub(r'(\[%s\]\[)[^\]]*(\])' % k, lambda m: m.group(1) + v + m.group(2), c)
# engine ratings per engine: F119-PW-100 (the Hornet's F404 numbers came along); take-off trim: none (the Hornet's 50 %
# nose up when spawning on the runway; -0.3 until 2026-11-15 - the F-22 has no takeoff trim, make_f22 'Pitch trim')
for rating, thrust in (('RatingAfterburner', '156000.0'), ('RatingMaxMilitary', '116000.0')):
    c = re.sub(r'(\[%s\]\[\]\s*(?:<[^\n]*\n\s*)*?<\[float64\]\[MaximumThrust\]\s*\[)[^\]]*(\])' % rating,
               lambda m: m.group(1) + thrust + m.group(2), c)
c = re.sub(r'(\[PitchTrimTakeoff\]\[)[^\]]*(\])', lambda m: m.group(1) + '0.0' + m.group(2), c)
open(os.path.join(OUT, 'copilot.tmc'), 'w', encoding='utf-8', newline='\n').write(c)

open(os.path.join(OUT, 'option.tmc'), 'w', encoding='utf-8', newline='\n').write("""<[file][][]
  <[object][][]
    <[string8][Description][USAF]>
    <[string8][Type][repaint]>
  >
>
""")

full = set(pj.get('full_res', []))
pngs = [os.path.basename(p)[:-4] for p in glob.glob(os.path.join(OUT, '*.png')) if not p.endswith('_alpha.png')]
big = sorted(p for p in pngs if re.sub(r'_(color|bump)$', '', p) in full and re.search(r'_(color|bump)$', p))
rest = sorted(p for p in pngs if p not in big)
def files(lst): return '\n'.join('                                    ' + x for x in lst)
# repaints: sub-folders whose option.tmc is Type repaint (the load add-ons are not; the converter needs the list for
# their textures and selection previews)
repaints = sorted(d for d in os.listdir(OUT) if os.path.isfile(os.path.join(OUT, d, 'option.tmc')) and
                  '[Type][repaint]' in open(os.path.join(OUT, d, 'option.tmc'), encoding='utf-8').read())
open(os.path.join(OUT, 'model.tmc'), 'w', encoding='utf-8', newline='\n').write("""<[file][][]
    <[convert_model_settings][][]
        <[float64][BumpMapScaling][1]>
        <[list_convert_target_settings][Targets][]
            <[convert_target_settings][element][0]
                <[string8][Target][Desktop]>
                <[list_string8][Repaints][%s]>
                <[list_convert_texture_settings][FileOptions][]
                    <[convert_texture_settings][element][0]
                        <[int32][MaxTextureSize][2048]>
                        <[float64][BumpMapScaling][1.0]>
                        <[list_string8][Files][
%s
                                              ]>
                    >
                    <[convert_texture_settings][element][1]
                        <[int32][MaxTextureSize][4096]>
                        <[float64][BumpMapScaling][1.0]>
                        <[list_string8][Files][
%s
                                              ]>
                    >
                >
            >
        >
    >
>
""" % ((' ' + ' '.join(repaints) + ' ') if repaints else '', files(rest), files(big)))
print('meta written: ground z=%.3f, 4096 textures: %d, 2048: %d, repaints: %s' % (ground, len(big), len(rest), repaints))
