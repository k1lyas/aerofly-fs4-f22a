#!/usr/bin/env python3
"""Installer of the F-22A Raptor add-on for Aerofly FS 4 (desktop: Windows, macOS, Linux).

    python3 install.py                 install or update (finds the game and your Aerofly user folder)
    python3 install.py --uninstall     move the installed F-22 out of the game (into the backup folder)
    python3 install.py --game DIR      game folder, when it is not found (the one that holds aircraft/f18)
    python3 install.py --user DIR      Aerofly user folder, when it is not found (the one that holds aircraft/)
    python3 install.py --no-update-check

Why an installer: the flight model, systems, displays and engine sounds of this add-on are built on the stock
F/A-18C. Those files belong to IPACS and are not in this package. The installer reads the F/A-18 of YOUR OWN game
and writes the F-22's configuration files from it on your machine; it also copies the F/A-18's sounds and the stock
F-15E's engine sounds. Nothing in the game folder is changed - only <user folder>/aircraft/f22 is written.

Needs Python 3.8 or newer, no extra packages. This file is part of the F-22A add-on, GPL-3 (see LICENSE).
"""
import argparse, hashlib, json, os, platform, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, 'generator')
PKG_AC = os.path.join(HERE, 'aircraft', 'f22')
NAME = 'f22'
GAME_FOLDER = 'Aerofly FS 4 Flight Simulator'      # Steam folder name
USER_FOLDER = 'Aerofly FS 4'
STEAM_APP = '1995890'
KEEP_BACKUPS = 2


def say(msg=''):
    print(msg, flush=True)


# (2026-11-18, found under Wine) printed into a pipe or file on Windows, Python writes the ANSI code page (cp1252):
# a folder name in Cyrillic stopped the installer with UnicodeEncodeError inside its own message. Unprintable
# characters become '?' instead; the console itself and the log file are UTF-8 anyway
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass


def stop(msg):
    say('\nSTOPPED: ' + msg)
    sys.exit(1)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------ where things are
def steam_roots():
    home = os.path.expanduser('~')
    roots = []
    if os.name == 'nt':
        try:
            import winreg
            for hive, key, val in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
                                   (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath'),
                                   (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam', 'InstallPath')):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        # (Steam writes it with forward slashes: c:/program files (x86)/steam)
                        roots.append(os.path.normpath(winreg.QueryValueEx(k, val)[0]))
                except OSError:
                    pass
        except ImportError:
            pass
        for env in ('ProgramFiles(x86)', 'ProgramFiles'):
            if os.environ.get(env):
                roots.append(os.path.join(os.environ[env], 'Steam'))
    elif sys.platform == 'darwin':
        roots.append(os.path.join(home, 'Library/Application Support/Steam'))
    else:
        roots += [os.path.join(home, p) for p in ('.steam/steam', '.steam/root', '.local/share/Steam',
                                                  '.var/app/com.valvesoftware.Steam/.local/share/Steam')]
    return roots


def steam_libraries():
    """Every Steam library folder: the Steam folder itself + the ones listed in steamapps/libraryfolders.vdf."""
    libs = []
    for root in steam_roots():
        if not os.path.isdir(root):
            continue
        libs.append(root)
        vdf = os.path.join(root, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            with open(vdf, encoding='utf-8', errors='replace') as fh:
                for m in re.finditer(r'"path"\s+"([^"]+)"', fh.read()):
                    libs.append(m.group(1).replace('\\\\', '\\'))
    seen, out = set(), []
    for lib in libs:
        key = os.path.normcase(os.path.realpath(lib))
        if key not in seen:
            seen.add(key)
            out.append(lib)
    return out


# how the player starts the installer again with options (install.bat passes them on)
RERUN = 'install.bat' if os.name == 'nt' else 'python3 install.py'


def is_game(folder):
    return os.path.isfile(os.path.join(folder, 'aircraft', 'f18', 'f18.tmd'))


def find_game(arg):
    if arg:
        arg = os.path.abspath(os.path.expanduser(arg))
        for cand in (arg, os.path.dirname(arg), os.path.dirname(os.path.dirname(arg))):   # .../aircraft/f18 is fine too
            if is_game(cand):
                return cand
        stop('no aircraft/f18/f18.tmd under "%s" - give the folder of the game that holds "aircraft"' % arg)
    for lib in steam_libraries():
        cand = os.path.join(lib, 'steamapps', 'common', GAME_FOLDER)
        if is_game(cand):
            return cand
    stop('Aerofly FS 4 was not found in your Steam libraries.\n'
         '  Start again with the game folder:   %s --game "<...>%ssteamapps%scommon%s%s"\n'
         '  (Steam: right click the game > Manage > Browse local files shows it)' % (RERUN, os.sep, os.sep, os.sep, GAME_FOLDER))


def windows_documents():
    """The Documents folder as Windows knows it (it may be moved, e.g. into OneDrive)."""
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [('a', wintypes.DWORD), ('b', wintypes.WORD), ('c', wintypes.WORD), ('d', ctypes.c_ubyte * 8)]
        fid = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
        buf = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(buf)) == 0:
            path = buf.value
            ctypes.windll.ole32.CoTaskMemFree(buf)
            return path
    except Exception:
        pass
    return os.path.join(os.path.expanduser('~'), 'Documents')


def find_user(arg, game):
    if arg:
        arg = os.path.abspath(os.path.expanduser(arg))
        if os.path.basename(arg).lower() == 'aircraft':
            arg = os.path.dirname(arg)
        if not os.path.isdir(arg):
            stop('the user folder "%s" does not exist' % arg)
        return arg
    home = os.path.expanduser('~')
    if os.name == 'nt':
        cands = [os.path.join(windows_documents(), USER_FOLDER), os.path.join(home, 'Documents', USER_FOLDER)]
    elif sys.platform == 'darwin':
        cands = [os.path.join(home, 'Library/Application Support', USER_FOLDER)]
    else:
        # native, or the Windows game under Proton: its Documents sit in the library's compatdata
        lib = os.path.dirname(os.path.dirname(os.path.dirname(game)))
        cands = [os.path.join(home, '.config', USER_FOLDER),
                 os.path.join(lib, 'steamapps', 'compatdata', STEAM_APP, 'pfx', 'drive_c', 'users', 'steamuser',
                              'Documents', USER_FOLDER)]
    for c in cands:
        if os.path.isdir(c):
            return c
    stop('your Aerofly user folder was not found (looked for: %s).\n'
         '  Start the game once so that it creates the folder, or start again with:   %s --user "<folder>"\n'
         '  (it is the folder that holds main.mcf)' % (', '.join(dict.fromkeys(cands)), RERUN))


def game_running():
    try:
        if os.name == 'nt':
            out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, timeout=20).stdout
            return any('aerofly_fs_4' in l.lower() and 'converter' not in l.lower() for l in out.splitlines())
        out = subprocess.run(['ps', '-A', '-o', 'args='], capture_output=True, text=True, timeout=20).stdout
        return any(re.search(r'aerofly[ _]fs[ _]4', l, re.I) and 'converter' not in l.lower() and
                   'install.py' not in l for l in out.splitlines())
    except Exception:
        return False


# ------------------------------------------------------------------------------------------ the work
def donor_state(donor, manifest):
    """'tested' when every stock file the add-on reads or copies is one of the files a release was tested with: the
    F/A-18's and the other stock aircraft's (stock_copy: the F-15E's engine sounds, paths under the game's aircraft/)."""
    missing = [f for f in manifest['donor_read'] + manifest['donor_copy'] if not os.path.isfile(os.path.join(donor, f))]
    if missing:
        stop('your F/A-18 folder lacks: %s\n  (%s) - verify the game files in Steam and try again' %
             (', '.join(missing), donor))
    stock = os.path.dirname(donor)
    missing = [f for f in manifest.get('stock_copy', {}).values() if not os.path.isfile(os.path.join(stock, f))]
    if missing:
        stop('your game lacks: %s\n  (under %s) - verify the game files in Steam and try again' %
             (', '.join(missing), stock))
    for build in manifest['tested_games']:
        if all(sha(os.path.join(donor, f)) == h for f, h in build['donor'].items()) and \
                all(sha(os.path.join(stock, f)) == h for f, h in build.get('stock', {}).items()):
            return build
    return None


def generate(donor, stage, version, log_path):
    env = dict(os.environ, F22_SOUND_DIR=stage, F22_VERSION=version, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    for k in ('F22_TEST', 'AC', 'PYTHONPATH'):
        env.pop(k, None)
    data = [os.path.join(GEN, 'data', f) for f in ('parts.json', 'geometry.json', 'anim.json', 'anim_pivots.json')]
    runs = [[os.path.join(GEN, 'make_f22.py'), donor] + data + [stage],
            [os.path.join(GEN, 'make_f22_meta.py'), donor, data[1], data[0], stage]]
    with open(log_path, 'w', encoding='utf-8') as log:
        log.write('Python %s (%s)\n' % (sys.version.split()[0], sys.executable))
        for argv in runs:
            # the script run with generator/ first on its path: the Windows embeddable Python of the package does not
            # put a script's own folder there (its ._pth file decides the path) and ignores PYTHONPATH
            boot = ('import runpy, sys; sys.path.insert(0, %r); sys.argv = %r; runpy.run_path(%r, run_name="__main__")'
                    % (GEN, argv, argv[0]))
            cmd = [sys.executable, '-X', 'utf8', '-B', '-c', boot]
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=GEN)
            text = r.stdout.decode('utf-8', 'replace')
            log.write('$ ' + ' '.join(argv) + '\n' + text + '\n')
            if r.returncode != 0:
                say('\n'.join(text.strip().splitlines()[-12:]))
                stop('the configuration generator failed (full output: %s).\n'
                     '  Most likely your F/A-18 files differ from the game versions this release was tested with.\n'
                     '  Please report it with that file.' % log_path)
    model = os.path.join(stage, 'model.tmc')        # converter input, not for the game
    if os.path.exists(model):
        os.remove(model)


def backup(target, backups):
    os.makedirs(backups, exist_ok=True)
    dest = os.path.join(backups, '%s_%s' % (NAME, time.strftime('%Y%m%d-%H%M%S')))
    while os.path.exists(dest):            # two runs within a second
        time.sleep(1)
        dest = os.path.join(backups, '%s_%s' % (NAME, time.strftime('%Y%m%d-%H%M%S')))
    shutil.move(target, dest)
    old = sorted(d for d in os.listdir(backups) if re.fullmatch(NAME + r'_\d{8}-\d{6}', d))
    for d in old[:-KEEP_BACKUPS]:
        shutil.rmtree(os.path.join(backups, d), ignore_errors=True)
    return dest


def update_notice(manifest, version):
    repo = manifest.get('repository', '')
    if not repo:
        return
    try:
        import urllib.request
        req = urllib.request.Request('https://api.github.com/repos/%s/releases/latest' % repo,
                                     headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'f22-installer'})
        with urllib.request.urlopen(req, timeout=6) as r:
            latest = json.load(r).get('tag_name', '').lstrip('v')
        key = lambda v: [int(x) if x.isdigit() else x for x in re.split(r'[.\-+]', v)]
        if latest and latest != version and key(latest) > key(version):
            say('\nA newer version is out: %s (this is %s)  ->  https://github.com/%s/releases/latest' %
                (latest, version, repo))
    except Exception:
        pass            # offline or rate-limited: never a reason to fail


def main():
    ap = argparse.ArgumentParser(description='Install the F-22A Raptor add-on into Aerofly FS 4')
    ap.add_argument('--game', help='game folder (holds aircraft/f18)')
    ap.add_argument('--user', help='Aerofly user folder (holds aircraft/)')
    ap.add_argument('--uninstall', action='store_true')
    ap.add_argument('--no-update-check', action='store_true')
    ap.add_argument('--no-running-check', action='store_true', help=argparse.SUPPRESS)
    a = ap.parse_args()

    if sys.version_info < (3, 8):
        stop('Python 3.8 or newer is needed (this is %s)' % platform.python_version())
    with open(os.path.join(GEN, 'manifest.json'), encoding='utf-8') as fh:
        manifest = json.load(fh)
    version = manifest['version']
    say('F-22A Raptor for Aerofly FS 4 - version %s' % version)

    game = find_game(a.game)
    user = find_user(a.user, game)
    target = os.path.join(user, 'aircraft', NAME)
    backups = os.path.join(user, 'aircraft_backup')
    say('game folder:  %s\nuser folder:  %s' % (game, user))
    if not a.no_running_check and game_running():
        stop('Aerofly FS 4 is running - close it and start the installer again')

    if a.uninstall:
        if not os.path.isdir(target):
            say('the F-22 is not installed - nothing to do')
            return
        say('moved to %s\nuninstalled (delete that folder to free the space)' % backup(target, backups))
        return

    donor = os.path.join(game, 'aircraft', 'f18')
    build = donor_state(donor, manifest)
    if build:
        say('stock files:   known (%s)' % build['label'])
    else:
        say('stock files:   NOT one of the tested game versions - the F-22 is built from them all the same;\n'
            '               if it misbehaves, look for a newer release and report your game version')

    stage = os.path.join(user, '%s-installing' % NAME)       # beside aircraft/: the same disk, moved in at the end
    if os.path.exists(stage):
        shutil.rmtree(stage)
    say('copying model, textures and sounds ...')
    shutil.copytree(PKG_AC, stage)
    say('building the configuration from your F/A-18 ...')
    log_path = os.path.join(user, 'f22_install.log')
    generate(donor, stage, version, log_path)
    for f in manifest['donor_copy']:
        shutil.copy2(os.path.join(donor, f), os.path.join(stage, f))
    for f, src in manifest.get('stock_copy', {}).items():        # e.g. f15e_jet_00.tsb <- aircraft/f15e/jet_00.tsb
        shutil.copy2(os.path.join(os.path.dirname(donor), src), os.path.join(stage, f))
    with open(os.path.join(stage, 'f22_version.txt'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('F-22A Raptor add-on %s\ninstalled %s\n' % (version, time.strftime('%Y-%m-%d %H:%M')))

    # the built files against the tested builds (they can match although the F/A-18 files differ, e.g. in line ends)
    def differing(b):
        return [f for f, h in b['output'].items() if not os.path.isfile(os.path.join(stage, f)) or
                sha(os.path.join(stage, f)) != h]
    if any(not differing(b) for b in manifest['tested_games']):
        say('verified: every built file is identical to the tested build')
    elif build:
        bad = differing(build)
        say('WARNING: %d built file(s) differ from the tested build: %s\n'
            '         please report this with %s' % (len(bad), ', '.join(bad[:6]), log_path))
    else:
        say('note: the built files differ from the tested build (as expected with other F/A-18 files)')

    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.isdir(target):
        say('previous F-22 moved to %s' % backup(target, backups))
    os.replace(stage, target)
    say('\nINSTALLED: %s\nStart Aerofly FS 4 - the aircraft is listed as "F-22A" (Lockheed Martin F-22A Raptor).' % target)
    if not a.no_update_check:
        update_notice(manifest, version)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        say('\ninterrupted - nothing was installed')
        sys.exit(1)
