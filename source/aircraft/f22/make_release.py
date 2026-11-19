#!/usr/bin/env python3
"""Build the public release package of the F-22A (see docs/PUBLISHING.md).

    python3 make_release.py [--allow-diagnostic] [--no-selftest]

Result: dist/F-22A-Raptor-<version>/ and dist/F-22A-Raptor-<version>.zip (+ .sha256). Version: the VERSION file.

The package holds no IPACS file: the converter output (model, textures, own sounds), the configuration generator
(make_f22.py and its modules) and release/install.py, which builds the configs on the user's machine from the user's
own stock F/A-18 and copies the F/A-18's sounds. Steps here:
  1. checks: the conversion finished, no diagnostic state in the generator sources, VERSION is x.y.z
  2. package tree: converted/aircraft/f22 without text configs and without sounds no config uses (the voices are
     Kokoro's, make_voices_kokoro.py - freely licensed); generator/ ; installer, documents, licence
  3. reference build with the packaged generator from this machine's F/A-18 -> generator/manifest.json (hashes of the
     F/A-18 files and of every built file: the installer tells the user whether the result equals the tested build)
  4. tools/clean_check.py on the tree: any IPACS file or stock text in it stops the release
  5. zip (launchers keep their execute bit), then a trial install from the package into a temporary user folder
"""
import argparse, glob, hashlib, importlib.util, json, os, re, shutil, subprocess, sys, tempfile, time, zipfile

A = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(A))
TOOLS = os.path.join(REPO, 'tools')
REL = os.path.join(A, 'release')
CONVERTED = os.path.join(A, 'converted', 'aircraft', 'f22')
BUILD = os.path.join(A, 'build', 'f22')
STEAM = os.path.expanduser('~/Library/Application Support/Steam/steamapps')
GAME = os.path.join(STEAM, 'common', 'Aerofly FS 4 Flight Simulator')
DONOR = os.path.join(GAME, 'aircraft', 'f18')
GENERATOR = ['make_f22.py', 'make_f22_meta.py', 'ac_f22.py', 'breakage_f22.py', 'burner_f22.py', 'failures_f22.py',
             'stores_f22.py', 'tvc_f22.py', 'cockpit_controls.py', 'cockpit_fit.py', 'mfd_f22.py']
DATA = {'parts.json': os.path.join(BUILD, 'parts.json'), 'geometry.json': os.path.join(A, 'work', 'geometry.json'),
        'anim.json': os.path.join(A, 'work', 'anim.json'), 'anim_pivots.json': os.path.join(A, 'work', 'anim_pivots.json')}
DOCS = ['README.md', 'GUIDE.md', 'CREDITS.md', 'CHANGELOG.md', 'COCKPIT_CONTROLS.md']     # (the last: written by cockpit_controls.py)
# never in a release: text configs (built on the user's machine). The voices are in: Kokoro-82M, Apache 2.0
# (make_voices_kokoro.py)
EXCLUDE = re.compile(r'\.(tmc|tmd)$')
DONOR_COPY_EXTRA = ['display_source_light.ttx']       # build.sh DONOR_FILES: the F/A-18 LCD digits
# the official Windows embeddable Python (python.org, PSF licence, unchanged) in the package's python\ folder: on
# Windows install.bat runs it, so a player needs no Python of his own (user 2026-11-18). Not in git: downloaded once
# into work/vendor, checked against the SHA-256 python.org publishes. x64 (Windows on ARM runs it emulated)
EMBED_PY = ('python-3.14.10-embed-amd64.zip', '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159',
            'https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip')
BINARY = ('.ttx', '.tmb', '.tsb', '.exe', '.dll', '.pyd', '.zip', '.cat', '.jpg', '.png')


SOURCE_README = """# Sources of the F-22A add-on (GPL-3)

The part we wrote, as the GPL asks for with every copy: the scripts that turn the original model into the files in
`../aircraft/f22`, the configuration generator, the sound scripts and the release tooling. Only what the build uses.

- `aircraft/f22/build.sh`, `tools/build_lib.sh` - the build: import of the DCS model into Blender, export of parts and
  textures (`ac_f22.py`, `tools/export_parts.py`, ...), the IPACS Aircraft Converter, installation. Written for macOS
  with Blender and the converter under CrossOver; paths are at the top of the two scripts. The converter also wants a
  `build/config.tmc` naming your output folder (see the IPACS aircraft SDK).
- `aircraft/f22/make_f22.py` and the modules it imports - the configuration generator (the copy the installer runs is
  in `../generator/`).
- `aircraft/f22/make_cockpit_sounds.py`, `make_voices_kokoro.py`, `mfd_pages.py` - cockpit sounds, voice warnings,
  the still pictures of the screens.
- `aircraft/f22/make_release.py`, `tools/clean_check.py` - release packaging and the check that no IPACS file is in a
  package. The installer and the documents it packs are the files at the top of this package.

Not here: the original model (EDM files and textures of the Grinnelli Designs F-22A mod, GPL-3): %(upstream_model)s ;
the Blender importer io_EDM (MIT): https://github.com/ndevenish/Blender_ioEDM and its forks; Blender; the IPACS
Aircraft Converter; the game.
"""


def source_files():
    """Repo-relative paths of the pipeline sources a release carries: the import closure of what the build starts."""
    t, a = 'tools', 'aircraft/f22'
    sh = ''.join(open(os.path.join(REPO, f), encoding='utf-8').read() for f in (a + '/build.sh', t + '/build_lib.sh'))
    start = [t + '/' + m for m in re.findall(r'\$T/([\w/]+\.(?:py|sh))', sh)] + [t + '/build_lib.sh', t + '/clean_check.py'] + \
            [a + '/' + f for f in ('build.sh', 'make_f22.py', 'make_f22_meta.py', 'ac_f22.py', 'mfd_pages.py',
                                   'make_cockpit_sounds.py', 'make_voices_kokoro.py', 'make_release.py', 'VERSION',
                                   'release/release.json')]
    mods = {}
    for d in (t, t + '/diag', a):
        for f in glob.glob(os.path.join(REPO, d, '*.py')):
            mods.setdefault(os.path.basename(f)[:-3], d + '/' + os.path.basename(f))
    keep, todo = set(), list(start)
    while todo:
        rel = todo.pop()
        if rel in keep:
            continue
        if not os.path.isfile(os.path.join(REPO, rel)):
            stop('source file %s named by the build is missing' % rel)
        keep.add(rel)
        if rel.endswith('.py'):
            text = open(os.path.join(REPO, rel), encoding='utf-8').read()
            names = set(re.findall(r'^\s*(?:import|from)\s+(\w+)', text, re.M))
            for line in re.findall(r'^\s*import\s+([\w, ]+)', text, re.M):
                names |= set(re.split(r'[,\s]+', line))
            names |= set(re.findall(r"import_module\(.*?'(\w+)'\)", text))
            todo += [mods[n] for n in names if n in mods]
    return sorted(keep)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def stop(msg):
    print('RELEASE STOPPED: ' + msg)
    sys.exit(1)


def git(*args):
    return subprocess.run(['git', '-C', REPO] + list(args), capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--allow-diagnostic', action='store_true', help='release although a source says DIAGNOSTIC')
    ap.add_argument('--no-selftest', action='store_true')
    a = ap.parse_args()

    version = open(os.path.join(A, 'VERSION')).read().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        stop('VERSION must be x.y.z (numbers only), not %r' % version)
    conf = json.load(open(os.path.join(REL, 'release.json'), encoding='utf-8'))

    # ---- 1 checks
    log = os.path.join(A, 'logs', 'convert.log')
    if not (os.path.isfile(log) and re.search('all done|converting done', open(log, errors='replace').read())):
        stop('the last conversion did not finish (logs/convert.log) - ./build.sh convert first')
    if os.environ.get('F22_TEST'):
        stop('F22_TEST is set - a release is built without test variants')
    diag = [f for f in GENERATOR if re.search(r'\bDIAGNOSTIC\b', open(os.path.join(A, f), encoding='utf-8').read())]
    if diag and not a.allow_diagnostic:
        stop('diagnostic state in %s (a line says DIAGNOSTIC) - finish or revert it, or --allow-diagnostic' % ', '.join(diag))
    for doc in DOCS:
        if not os.path.isfile(os.path.join(REL, doc)):
            stop('release/%s is missing' % doc)
    if 'v%s' % version not in open(os.path.join(REL, 'CHANGELOG.md'), encoding='utf-8').read():
        stop('release/CHANGELOG.md has no entry for v%s' % version)
    dirty = git('status', '--porcelain', '--', 'aircraft/f22', 'tools/tmd.py')
    commit = git('rev-parse', '--short', 'HEAD') + ('+uncommitted' if dirty else '')

    # ---- 2 package tree
    name = 'F-22A-Raptor-%s' % version
    dist = os.path.join(A, 'dist')
    root = os.path.join(dist, name)
    if os.path.exists(root):
        shutil.rmtree(root)
    pkg_ac = os.path.join(root, 'aircraft', 'f22')
    left_out = []
    for d, _, files in os.walk(CONVERTED):
        for f in files:
            src = os.path.join(d, f)
            rel = os.path.relpath(src, CONVERTED)
            if f.startswith('.') or EXCLUDE.search(f):
                left_out.append(rel)
                continue
            os.makedirs(os.path.dirname(os.path.join(pkg_ac, rel)), exist_ok=True)
            shutil.copy2(src, os.path.join(pkg_ac, rel))
    gen = os.path.join(root, 'generator')
    os.makedirs(os.path.join(gen, 'data'))
    for f in GENERATOR:
        shutil.copy2(os.path.join(A, f), gen)
    shutil.copy2(os.path.join(TOOLS, 'tmd.py'), gen)
    for f, src in DATA.items():
        shutil.copy2(src, os.path.join(gen, 'data', f))
    for f in ['install.py', 'install.bat', 'install.command']:
        shutil.copy2(os.path.join(REL, f), root)
    emb = os.path.join(A, 'work', 'vendor', EMBED_PY[0])
    if not os.path.isfile(emb) or sha(emb) != EMBED_PY[1]:
        stop('the Windows embeddable Python is missing or not the published file: download %s into %s (SHA-256 %s)'
             % (EMBED_PY[2], os.path.dirname(emb), EMBED_PY[1]))
    with zipfile.ZipFile(emb) as z:
        z.extractall(os.path.join(root, 'python'))
    # the sources of our part (GPL-3: every package carries them) - only what the build really uses: the scripts the
    # build files start, what those import, the generator, the sound scripts and the release tooling. Debug tools,
    # experiments, working notes and the converter config (it holds a local path) stay out
    src_root = os.path.join(root, 'source')
    for rel in source_files():
        os.makedirs(os.path.dirname(os.path.join(src_root, rel)), exist_ok=True)
        shutil.copy2(os.path.join(REPO, rel), os.path.join(src_root, rel))
    open(os.path.join(src_root, 'README.md'), 'w', encoding='utf-8').write(SOURCE_README % conf)
    shutil.copy2(os.path.join(A, 'source', 'LICENSE'), os.path.join(root, 'LICENSE'))
    open(os.path.join(root, 'VERSION'), 'w').write(version + '\n')
    if not conf.get('repository'):
        print('NOTE: release.json has no "repository" - the documents point at the forum thread for the sources and '
              'the installer does not look for updates. Set it before the public release.')

    # ---- 3 reference build with the packaged generator, exactly as the installer runs it
    spec = importlib.util.spec_from_file_location('f22_install', os.path.join(root, 'install.py'))
    inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inst)
    tmp = tempfile.mkdtemp(prefix='f22_release_')
    ref = os.path.join(tmp, 'ref')
    shutil.copytree(pkg_ac, ref)
    before = {os.path.relpath(os.path.join(d, f), ref) for d, _, fs in os.walk(ref) for f in fs}
    inst.generate(DONOR, ref, version, os.path.join(tmp, 'generate.log'))
    built = sorted({os.path.relpath(os.path.join(d, f), ref) for d, _, fs in os.walk(ref) for f in fs} - before)
    text = ''.join(open(os.path.join(ref, f), encoding='utf-8', errors='replace').read() for f in built)
    donor_tsb = sorted(os.path.basename(p) for p in glob.glob(os.path.join(DONOR, '*.tsb')))
    for f in sorted(os.listdir(pkg_ac)):            # own sounds no config uses (left from earlier builds)
        if f.endswith('.tsb') and not re.search(r'\b%s\b' % re.escape(f[:-4]), text):
            os.remove(os.path.join(pkg_ac, f))
            left_out.append(f + ' (unused)')
    clash = [f for f in donor_tsb + DONOR_COPY_EXTRA if os.path.exists(os.path.join(pkg_ac, f))]
    if clash:
        stop('package files with the names of F/A-18 files the installer copies: %s' % ', '.join(clash))
    donor_read = ['f18.tmd', 'f18.tmc', 'controls.tmd', 'copilot.tmc'] + sorted(
        os.path.basename(p) for p in glob.glob(os.path.join(DONOR, 'f18_*.tmd'))
        if os.path.basename(p)[4:-4] in ('clean', 'cold', 'flaps', 'gear', 'landing', 'start', 'takeoff'))
    acf = os.path.join(STEAM, 'appmanifest_1995890.acf')
    build_id = re.search(r'"buildid"\s+"(\d+)"', open(acf).read()).group(1) if os.path.isfile(acf) else '?'
    manifest = {
        'version': version, 'built': time.strftime('%Y-%m-%d'), 'source_commit': commit,
        'repository': conf.get('repository', ''),
        'donor_read': donor_read, 'donor_copy': donor_tsb + DONOR_COPY_EXTRA,
        'tested_games': [{'label': 'Steam build %s, macOS' % build_id,
                          'donor': {f: sha(os.path.join(DONOR, f)) for f in donor_read + donor_tsb + DONOR_COPY_EXTRA},
                          'output': {f.replace(os.sep, '/'): sha(os.path.join(ref, f)) for f in built}}]
                        + conf.get('extra_tested_games', []),
    }
    json.dump(manifest, open(os.path.join(gen, 'manifest.json'), 'w', encoding='utf-8'), indent=1)
    tokens = {'@VERSION@': version, '@FORUM_URL@': conf['forum'], '@UPSTREAM_URL@': conf['upstream_model'],
              '@SOURCE_URL@': ('https://github.com/' + conf['repository']) if conf.get('repository')
              else 'see the forum thread (the repository address is posted there)',
              '@SUPPORT_URL@': ('https://ko-fi.com/' + conf['ko_fi']) if conf.get('ko_fi') else conf['forum'],
              '@REPO@': conf.get('repository', ''),
              '@TESTED@': '; '.join('Aerofly FS 4 ' + g['label'] for g in manifest['tested_games'])}
    for doc in DOCS:
        t = open(os.path.join(REL, doc), encoding='utf-8').read()
        for k, v in tokens.items():
            t = t.replace(k, v)
        left = re.findall(r'@[A-Z_]+@', t)
        if left:
            stop('release/%s: unknown placeholder %s' % (doc, left[0]))
        open(os.path.join(root, doc), 'w', encoding='utf-8', newline='\n').write(t)
    # the README's pictures (2026-11-19: the user's in-game screenshots, cropped)
    shutil.copytree(os.path.join(REL, 'media'), os.path.join(root, 'media'))
    shutil.rmtree(tmp)
    print('package tree: %d files, %.0f MB; built on install: %d files; left out: %s'
          % (sum(len(fs) for _, _, fs in os.walk(root)),
             sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(root) for f in fs) / 1048576,
             len(built), ', '.join(sorted(left_out))))

    # ---- 4 nothing personal and nothing of IPACS in the tree
    home = os.path.expanduser('~')
    private = [home, home.replace('/', '\\'), os.path.basename(home) + '@']
    mail = git('config', 'user.email')
    if mail:
        private.append(mail)
    for d, _, files in os.walk(root):
        for f in files:
            if f.endswith(BINARY):
                continue
            text = open(os.path.join(d, f), encoding='utf-8', errors='replace').read()
            hit = next((x for x in private if x and x in text), None)
            if hit:
                stop('a personal path or address in %s - not for publication' % os.path.relpath(os.path.join(d, f), root))
    r = subprocess.run([sys.executable, os.path.join(TOOLS, 'clean_check.py'), root, '--src', BUILD],
                       capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if not l.startswith(('note ', 'warn '))]
    print('\n'.join('  ' + l[:200] for l in lines))
    open(os.path.join(dist, name + '.clean_check.txt'), 'w').write(r.stdout)
    if r.returncode != 0:
        stop('clean_check found IPACS content in the package (full report: dist/%s.clean_check.txt)' % name)

    # ---- 5 zip + trial install
    zpath = os.path.join(dist, name + '.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for d, _, files in os.walk(root):
            for f in sorted(files):
                full = os.path.join(d, f)
                arc = os.path.relpath(full, dist).replace(os.sep, '/')
                zi = zipfile.ZipInfo(arc, time.localtime(os.path.getmtime(full))[:6])
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = (0o755 if f in ('install.command', 'install.py') else 0o644) << 16
                with open(full, 'rb') as fh:
                    z.writestr(zi, fh.read(), compresslevel=6)
    digest = sha(zpath)
    open(zpath + '.sha256', 'w').write('%s  %s\n' % (digest, os.path.basename(zpath)))
    print('zip: %s  %.0f MB  sha256 %s' % (zpath, os.path.getsize(zpath) / 1048576, digest[:16]))

    if not a.no_selftest:
        for py in [sys.executable] + [p for p in ('/usr/bin/python3',) if os.path.exists(p) and
                                       os.path.realpath(p) != os.path.realpath(sys.executable)]:
            tmp = tempfile.mkdtemp(prefix='f22_selftest_')
            with zipfile.ZipFile(zpath) as z:
                z.extractall(os.path.join(tmp, 'unzipped'))
            user = os.path.join(tmp, 'user')
            os.makedirs(os.path.join(user, 'aircraft'))
            r = subprocess.run([py, os.path.join(tmp, 'unzipped', name, 'install.py'), '--game', GAME, '--user', user,
                                '--no-running-check', '--no-update-check'], capture_output=True, text=True)
            ver = subprocess.run([py, '--version'], capture_output=True, text=True).stdout.strip()
            ok = r.returncode == 0 and 'verified: every built file' in r.stdout
            inst_dir = os.path.join(user, 'aircraft', 'f22')
            n = sum(len(fs) for _, _, fs in os.walk(inst_dir))
            # every sound a built config names is there (in the aircraft folder or the game's own sound folder)
            named = set()
            for f in glob.glob(os.path.join(inst_dir, '*.tmd')) + glob.glob(os.path.join(inst_dir, '*', '*.tmd')):
                named |= set(re.findall(r'\[SoundFile\]\[\s*([^\]\s]+)\s*\]', open(f, encoding='utf-8', errors='replace').read()))
            lost = sorted(x for x in named if not any(os.path.exists(os.path.join(d, os.path.splitext(os.path.basename(x))[0] + '.tsb'))
                                                      for d in (inst_dir, os.path.join(GAME, 'sound'))))
            if lost:
                ok = False
                print('configs name sounds that are not installed: %s' % ', '.join(lost))
            print('trial install with %s: %s (%d files installed)' % (ver, 'OK, verified' if ok else 'FAILED', n))
            if not ok:
                print(r.stdout[-1500:], r.stderr[-1500:])
                stop('the trial install failed - the folder is kept: %s' % tmp)
            shutil.rmtree(tmp)
    print('RELEASE READY: %s' % zpath)


if __name__ == '__main__':
    main()
