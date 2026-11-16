#!/usr/bin/env python3
"""Publication check: does an aircraft package contain anything copied from IPACS files?

    python3 tools/clean_check.py <package dir> [--ref DIR ...] [--window N] [--strict]

Compared against (default): every stock aircraft folder + sound/ of the installed game, and sdk/dr400 of this repo.
Checks
  1. identical files (SHA-256) - any match is a failure, whatever the name, except tiny converted textures (< 4 KB
     .ttx): a flat colour or flat normal map converts to the same bytes whoever made it - reported as a note; a
     larger .ttx is a note too when --src names the folder of the source PNGs and its source is a single-colour image
     (a black 2048 px render target converts to the same bytes as any stock one);
  2. same file names as a stock file (e.g. jet_00.tsb) - a warning: rename ours, it invites confusion;
  3. text configs (.tmd .tmc .tgi) and the package's scripts and documents (.py .md .txt): windows of N consecutive
     non-trivial lines identical to a stock file
     (whitespace-normalised). Format boilerplate is unavoidable, so a match is reported per file with a percentage;
     a file is a failure when more than LIMIT percent of its lines sit in matching windows (default 25 %).
Exit code 0 = clean, 1 = failures. The package is not modified.
"""
import argparse, hashlib, os, re, struct, sys, zlib, collections

HOME = os.path.expanduser('~')
GAME = os.path.join(HOME, 'Library/Application Support/Steam/steamapps/common/Aerofly FS 4 Flight Simulator')
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_EXT = ('.tmd', '.tmc', '.tgi')
PKG_TEXT_EXT = TEXT_EXT + ('.py', '.md', '.txt')     # generator scripts and documents of a release
LIMIT = 25.0


def walk(root):
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.startswith('.'):
                yield os.path.join(d, f)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def png_uniform(path):
    """True when the PNG is one colour all over (8 bit, not interlaced; anything else: False)."""
    try:
        d = open(path, 'rb').read()
        if d[:8] != b'\x89PNG\r\n\x1a\n':
            return False
        i, idat, head = 8, [], None
        while i < len(d):
            n, kind = struct.unpack('>I4s', d[i:i + 8])
            if kind == b'IHDR':
                head = struct.unpack('>IIBBBBB', d[i + 8:i + 21])
            elif kind == b'IDAT':
                idat.append(d[i + 8:i + 8 + n])
            i += 12 + n
        w, h, depth, ctype, _, _, interlace = head
        if depth != 8 or interlace or ctype not in (0, 2, 4, 6):
            return False
        bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
        raw = zlib.decompress(b''.join(idat))
        stride = w * bpp
        prev, first = bytearray(stride), None
        for y in range(h):
            f = raw[y * (stride + 1)]
            row = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
            if f == 1:
                for x in range(bpp, stride):
                    row[x] = (row[x] + row[x - bpp]) & 255
            elif f == 2:
                row = bytearray((a + b) & 255 for a, b in zip(row, prev))
            elif f == 3:
                for x in range(stride):
                    row[x] = (row[x] + ((row[x - bpp] if x >= bpp else 0) + prev[x]) // 2) & 255
            elif f == 4:
                for x in range(stride):
                    a, b, c = (row[x - bpp] if x >= bpp else 0), prev[x], (prev[x - bpp] if x >= bpp else 0)
                    pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                    row[x] = (row[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
            if first is None:
                first = bytes(row[:bpp]) * w
            if bytes(row) != first:
                return False
            prev = row
        return True
    except Exception:
        return False


def norm_lines(path):
    out = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.split('//')[0]
            line = re.sub(r'\s+', ' ', line).strip()
            if len(line) >= 12:
                out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('package')
    ap.add_argument('--ref', action='append', default=[])
    ap.add_argument('--window', type=int, default=8)
    ap.add_argument('--limit', type=float, default=LIMIT)
    ap.add_argument('--skip', action='append', default=[], help='package sub-folders to ignore (e.g. _source)')
    ap.add_argument('--src', help='folder with the source PNGs of the package textures (uniform images are notes)')
    a = ap.parse_args()

    refs = a.ref or [os.path.join(GAME, 'aircraft'), os.path.join(GAME, 'sound'), os.path.join(REPO, 'sdk/dr400')]
    refs = [r for r in refs if os.path.isdir(r)]
    if not refs:
        print('no reference folders found - nothing to compare against'); return 1
    pkg = [p for p in walk(a.package) if not any(('/' + s + '/') in p for s in a.skip)]
    print('package %s: %d files; references: %s' % (a.package, len(pkg), ', '.join(refs)))

    # --- 1/2: hashes and names, size-prefiltered
    sizes = collections.defaultdict(list)
    for p in pkg:
        sizes[os.path.getsize(p)].append(p)
    ref_names = collections.defaultdict(list)
    ref_text = []
    ref_hash = collections.defaultdict(list)
    for r in refs:
        for f in walk(r):
            ref_names[os.path.basename(f).lower()].append(f)
            sz = os.path.getsize(f)
            if sz in sizes:
                ref_hash[sha(f)].append(f)
            if f.lower().endswith(TEXT_EXT):
                ref_text.append(f)
    fail = 0
    for p in pkg:
        h = sha(p)
        if h in ref_hash:
            if p.lower().endswith('.ttx') and os.path.getsize(p) < 4096:
                print('note flat texture identical to a stock one (uniform image, expected): %s' % os.path.relpath(p, a.package))
                continue
            src_png = os.path.join(a.src, os.path.basename(p)[:-4] + '.png') if a.src else ''
            if p.lower().endswith('.ttx') and src_png and os.path.isfile(src_png) and png_uniform(src_png):
                print('note texture identical to a stock one, its source %s is a single-colour image: %s'
                      % (os.path.basename(src_png), os.path.relpath(p, a.package)))
                continue
            fail += 1
            print('FAIL identical file: %s == %s' % (os.path.relpath(p, a.package), ref_hash[h][0]))
    pkg_name = os.path.basename(os.path.normpath(a.package)).lower()
    for p in pkg:
        b = os.path.basename(p).lower()
        if b in ref_names and not b.startswith(pkg_name) and b not in ('option.tmc', 'controls.tmd', 'copilot.tmc'):
            print('warn same name as a stock file: %s (%s)' % (os.path.relpath(p, a.package), ref_names[b][0]))

    # --- 3: line windows
    W = a.window
    index = {}
    for f in ref_text:
        ls = norm_lines(f)
        for i in range(len(ls) - W + 1):
            index.setdefault(hash(tuple(ls[i:i + W])), f)
    for p in pkg:
        if not p.lower().endswith(PKG_TEXT_EXT):
            continue
        ls = norm_lines(p)
        if len(ls) < W:
            continue
        covered = [False] * len(ls)
        src = collections.Counter()
        for i in range(len(ls) - W + 1):
            f = index.get(hash(tuple(ls[i:i + W])))
            if f:
                for k in range(i, i + W):
                    covered[k] = True
                src[os.path.relpath(f, GAME) if f.startswith(GAME) else f] += 1
        pct = 100.0 * sum(covered) / len(ls)
        status = 'FAIL' if pct > a.limit else 'ok  '
        if pct > a.limit:
            fail += 1
        print('%s %-34s %6d lines, %5.1f %% in %d-line windows identical to stock%s'
              % (status, os.path.relpath(p, a.package), len(ls), pct, W,
                 ('  (' + ', '.join('%s x%d' % kv for kv in src.most_common(2)) + ')') if src else ''))
    print('RESULT:', 'CLEAN' if not fail else '%d failure(s)' % fail)
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
