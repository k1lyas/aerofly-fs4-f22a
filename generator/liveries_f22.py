"""Community liveries (0.9.2): skins painted by DCS players for the mod on its own layout (Grinnelli Designs' paint
kit - the model's UVs, its normal map), so derivatives of the GPL-3 model; carried over under the GPL, free, with their
authors named in release/CREDITS.md (2026-11-26: all the skins he downloaded; an author with a claim writes to
him and they agree on what to do).

One entry each: the load is picked in the cockpit (loads_f22, 0.9.2) - for a few hours of 2026-11-26 each came clean
and with the full set (a repaint naming the add-ons it needs), before the load system. Of the six Texac USAF skins - one paint, one weathering,
only the fin markings differ - kept ED 005 and AK 193 (FF 169 / 191, AK 118, AK 195 left out).
Only the skin's colour is taken: relief, gloss, metal and AO stay the base livery's (a skin's RoughMet marks most of the airframe metal - the
aircraft looked oiled, test 2026-11-25) - except where the finish is the livery (the mirror coating: its own RoughMet,
'roughmet'); the formation strips are painted over as on the base (ac_f22.paint_out_strips), the skin's own decor
stays. Not taken: the authors' other textures (canopy, visor: ours).

The archives sit in work/livery_sources (not in the repository); the maps are written to build/f22/<folder>/, then
the previews (./build.sh previews) and ./build.sh convert:

    uv run --with pillow python3 liveries_f22.py          (decodes the DDS, then runs Blender for the maps)
"""
import os, sys, shutil, subprocess, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(HERE, 'work', 'livery_sources')
OUT = os.path.join(HERE, 'build', 'f22')
BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
REQUIREMENTS = 'load_combat load_ferry'

TEXAC = 'https://www.digitalcombatsimulator.com/en/files/filter/user-is-Texac/apply/'
LIVERIES = [
    dict(folder='usaf_ed005', description='USAF ED 005',
         archive='31st_TES_(ED_005)_Clean.ZIP', member='31st TES (ED 005) Clean/F-22_CleanScheme_ED.dds',
         name='31st TES (ED 005) Clean', author='Texac', page=TEXAC),
    # the mirror coating test (Nellis, 2021): here the skin's own gloss and metal are the point - its RoughMet is taken
    dict(folder='usaf_ot_mirror', description='USAF Mirror',
         archive='F-22A_Raptor_422nd_TES_(OT_04-4065)_Mirror.ZIP', member='422nd TES (OT 04-4065) Mirror/F-22_Mirror.dds',
         roughmet='422nd TES (OT 04-4065) Mirror/F-22_Mirror_RoughMet.dds',
         name='F-22A Raptor 422nd TES (OT 04-4065) Mirror', author='Texac', page=TEXAC),
    # 193, one of the last two Raptors built (JBER, 2012): the 3rd Wing's flagship
    dict(folder='usaf_ak193', description='USAF AK 193',
         archive='Raptor_Liveries.7z', member='Raptor Liveries/525th FS (AK 193)/F-22_AK_193.dds',
         name='F-22A 193 and 195 - 3rd Wing and 525 FS', author='Texac (commissioned; uploaded by Aggressor11)',
         page='https://www.digitalcombatsimulator.com/en/files/3340372/'),
    dict(folder='tuaf_kaan', description='TuAF KAAN',
         archive='THK_F22A_MMU_Kaan.zip', member='F-22_Diffuse.dds', name='TuAF F22 Raptor | MMU KAAN',
         author='AsilTurq', page='https://www.digitalcombatsimulator.com/en/files/3348437/'),
    dict(folder='isaf_mobius_one', description='Mobius One',
         archive='Ace_Combat_-_ISAF_Air_Force_-_Mobius_One.zip',
         member='Ace Combat - ISAF Air Force - Mobius One/f-22a_default.dds',
         name='Ace Combat - ISAF Air Force - 118th Tactical Fighter Wing "Mobius 1" F-22A Raptor', author='_BillyTheKid_',
         page='https://www.digitalcombatsimulator.com/en/files/filter/user-is-_BillyTheKid_/apply/'),
    # Danksley's LICENSE.txt: redistribute with credit and a link to the file page
    dict(folder='crimson_squadron', description='Crimson',
         archive='F-22A-PW-Crimson-Squad-Highvis.zip', member='F-22A/Crimson 2nd Appearance/F-22_Diffuse.dds',
         name='Federation Peacekeeper Squadron Crimson (2nd)', author='Danksley',
         page='https://www.digitalcombatsimulator.com/en/files/filter/user-is-Danksley/apply/'),
]
# The paint changed in flight was tried (a test build, 2026-11-26) and dropped: texture_animation on the skin colour
# draws only mip level 0 - the skin stayed the clear colour from a distance (docs/reference/ENGINE_CATALOG.md).


def decoded(lv, kind='color'):
    return os.path.join(SOURCES, lv['folder'], kind + '.png')


def _read(archive, member):
    path = os.path.join(SOURCES, archive)
    if archive.lower().endswith('.7z'):          # (bsdtar: macOS's own libarchive reads 7z)
        return subprocess.run(['bsdtar', '-xOf', path, member], capture_output=True, check=True).stdout
    with zipfile.ZipFile(path) as z:
        return z.read(member)


def decode(lv):
    """The skin's colour map (and RoughMet where it is taken) out of its archive, BC7 DDS -> PNG (Pillow; Blender reads
    no BC7)."""
    import io
    from PIL import Image
    os.makedirs(os.path.join(SOURCES, lv['folder']), exist_ok=True)
    for kind in ('color', 'roughmet'):
        if not lv.get(kind if kind != 'color' else 'member') or os.path.exists(decoded(lv, kind)):
            continue
        im = Image.open(io.BytesIO(_read(lv['archive'], lv['member'] if kind == 'color' else lv[kind])))
        print('%s %s: %s %dx%d' % (lv['folder'], kind, im.format, *im.size))
        im.convert('RGBA' if kind == 'color' else 'RGB').save(decoded(lv, kind))


def maps():
    """Inside Blender: the base livery's colour pipeline on the skin (aerofly_tex.write_material_textures with the
    mod's own RoughMet, so the colour is treated as the base's), then the formation strips; only the colour is kept."""
    sys.path[:0] = [os.path.join(HERE, '..', '..', 'tools'), HERE]
    import tempfile
    import aerofly_tex as X
    import ac_f22 as C
    rm = X.load_image(X.find_texture(C.TEXTURES, 'F-22A_Default_RoughMet'))
    for lv in LIVERIES:
        tmp = tempfile.mkdtemp()
        own = lv.get('roughmet')
        X.write_material_textures(tmp, 'f_22a_default', X.load_image(decoded(lv)), None,
                                  X.load_image(decoded(lv, 'roughmet')) if own else rm, size=4096)
        path = os.path.join(tmp, 'f_22a_default_color.png')
        c = X.load_image(path)
        rgb = c[..., :3].copy()
        skipped = C.paint_out_strips(rgb)
        if skipped:
            print('LIVERY %s: formation strips left as painted (index, box filled): %s' % (lv['folder'], skipped))
        X.save_png(path, rgb, limit=c.shape[1])
        d = os.path.join(OUT, lv['folder'])
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            if f.startswith('f_22a_default_'):
                os.remove(os.path.join(d, f))
        # colour; with the skin's own RoughMet also its gloss and metal (specular, reflection) - relief and AO stay ours
        for f in ['color'] + (['specular', 'specular_alpha', 'reflection'] if own else []):
            if os.path.exists(os.path.join(tmp, 'f_22a_default_%s.png' % f)):
                shutil.copy(os.path.join(tmp, 'f_22a_default_%s.png' % f), d)
        shutil.rmtree(tmp)
        print('LIVERY', lv['folder'], 'written')


if __name__ == '__main__':
    if '--' in sys.argv and 'maps' in sys.argv[sys.argv.index('--') + 1:]:
        maps()
    else:
        for lv in LIVERIES:
            decode(lv)
        r = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', os.path.abspath(__file__), '--', 'maps'],
                           cwd=HERE, capture_output=True, text=True)
        print('\n'.join(l for l in (r.stdout + r.stderr).splitlines()
                        if l.startswith('LIVERY') or 'Error' in l or 'Traceback' in l or l.startswith('  ')))
        sys.exit(r.returncode)
