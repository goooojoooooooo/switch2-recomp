# SPDX-License-Identifier: GPL-3.0-or-later
"""Check game manifests (recomp/games/<id>/game.toml) against what their readers need.

    python -I recomp/scripts/check_manifest.py              every game under recomp/games
    python -I recomp/scripts/check_manifest.py plza         one game (or a path to a game.toml)
    python -I recomp/scripts/check_manifest.py --strict ... placeholders (all-zero ids and hashes) count as errors

Readers and what they need:
  - recomp/cmake/GameManifest.cmake: only [table], [[array]], key = "string" | integer | 0xHEX | true | false lines, no backslash
    or quote inside a string (it stops the configure on anything else, and tomllib would accept more).
  - game-build/release_b/game_build.py and the launcher (launcher/src-tauri/src/manifest.rs): the keys they read.
  - the runtime: module indices 0..n-1 in lifter order, one entry module, distinct load addresses, a module named main.
Across games: distinct id, save folder and launcher identifier, so two ports never share saves or launcher settings.
Exit code 0 when no errors (warnings allowed), 1 otherwise.
"""
import argparse
import os
import re
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
RECOMP = os.path.dirname(HERE)
REPO = os.path.dirname(RECOMP)
GAMES = os.path.join(RECOMP, 'games')

# the line shapes GameManifest.cmake accepts (its game_manifest_load regexes)
LINE_OK = [re.compile(p) for p in (
    r'^\s*#', r'^\s*$',
    r'^\s*\[\[[A-Za-z0-9_.]+\]\]',
    r'^\s*\[[A-Za-z0-9_.]+\]',
    r'^\s*[A-Za-z0-9_]+\s*=\s*"[^"\\]*"',
    r'^\s*[A-Za-z0-9_]+\s*=\s*(0x[0-9a-fA-F]+|[0-9]+|true|false)(\s|$)',
)]
REQUIRED = {
    'game': ['id', 'title', 'short_title', 'product', 'title_id', 'version', 'platform', 'languages'],
    'files': ['exe', 'runtime_dll', 'ini', 'log', 'setup_exe', 'launcher_ini', 'shader_pack', 'save_folder'],
    'dump': ['version', 'display_version', 'main_build_id', 'example_folder', 'file'],
    'launcher': ['name', 'window_title', 'product_name', 'identifier', 'package_name'],
}
HEX = re.compile(r'^[0-9a-fA-F]+$')


class Report:
    def __init__(self, name):
        self.name, self.errors, self.warnings = name, [], []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def is_hex(s, n):
    return isinstance(s, str) and len(s) == n and bool(HEX.match(s))


def placeholder(s):
    return isinstance(s, str) and s != '' and not s.strip('0')


def check(path, strict):
    folder = os.path.dirname(path)
    r = Report(os.path.basename(folder))
    text = open(path, encoding='utf-8').read()
    for n, line in enumerate(text.splitlines(), 1):
        if not any(p.match(line) for p in LINE_OK):
            r.err('line %d: GameManifest.cmake cannot read it: %s' % (n, line.strip()))
    try:
        m = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        r.err('not valid TOML: %s' % e)
        return r, None

    if m.get('schema') != 1:
        r.err('schema must be 1')
    missing = 0                     # stop only when keys are missing: every later check reads them
    for table, keys in REQUIRED.items():
        t = m.get(table)
        if not isinstance(t, dict):
            r.err('missing [%s]' % table)
            missing += 1
            continue
        for k in keys:
            if k not in t:
                r.err('[%s] has no %s' % (table, k))
                missing += 1
    if missing:
        return r, m
    g, f, d = m['game'], m['files'], m['dump']

    if g['id'] != r.name:
        r.err('[game] id "%s" is not the folder name "%s"' % (g['id'], r.name))
    if not is_hex(g['title_id'], 16):
        r.err('[game] title_id must be 16 hex digits')
    if g['platform'] not in ('switch1', 'switch2'):
        r.err('[game] platform must be switch1 or switch2')
    if not isinstance(g['languages'], int) or g['languages'] <= 0:
        r.err('[game] languages must be a positive bit mask')
    for k in REQUIRED['files']:
        if not f[k]:
            r.err('[files] %s is empty' % k)
    for k, ext in (('exe', '.exe'), ('runtime_dll', '.dll'), ('setup_exe', '.exe')):
        if not f[k].lower().endswith(ext):
            r.err('[files] %s should end in %s' % (k, ext))

    if not is_hex(d['main_build_id'], 40):
        r.err('[dump] main_build_id must be 40 hex digits (the first 20 bytes of main\'s build id)')
    elif placeholder(d['main_build_id']):
        (r.err if strict else r.warn)('[dump] main_build_id is a placeholder: run the game\'s fill tool on a dump')
    files = d['file'] if isinstance(d['file'], list) else []
    names = [x.get('name') for x in files]
    if len(set(names)) != len(names):
        r.err('[[dump.file]] names repeat')
    if 'main.npdm' not in names:
        r.err('[[dump.file]] lacks main.npdm')
    zero = 0
    for x in files:
        if not is_hex(x.get('sha256', ''), 64):
            r.err('[[dump.file]] %s: sha256 must be 64 hex digits' % x.get('name'))
        elif placeholder(x['sha256']):
            zero += 1
    if zero:
        (r.err if strict else r.warn)('%d of %d [[dump.file]] hashes are placeholders' % (zero, len(files)))

    mods = m.get('module')
    if not isinstance(mods, list) or not mods:
        r.err('no [[module]]')
        return r, m
    lacking = 0
    for i, mod in enumerate(mods):
        for k in ('name', 'file', 'base', 'index', 'units'):
            if k not in mod:
                r.err('[[module]] #%d has no %s' % (i, k))
                lacking += 1
    if lacking:
        return r, m
    mnames = [x['name'] for x in mods]
    if len(set(mnames)) != len(mnames):
        r.err('[[module]] names repeat')
    if 'main' not in mnames:
        r.err('no [[module]] named main (GAME_MAIN_BASE comes from it)')
    if [x['index'] for x in mods] != list(range(len(mods))):
        r.err('[[module]] index must be 0..%d in the listed (lifter) order' % (len(mods) - 1))
    entries = [x['name'] for x in mods if x.get('entry') is True]
    if len(entries) != 1:
        r.err('exactly one [[module]] needs entry = true (has %d)' % len(entries))
    bases = [x['base'] for x in mods]
    if len(set(bases)) != len(bases):
        r.err('[[module]] load addresses repeat')
    for x in mods:
        if x['base'] % 0x1000:
            r.err('[[module]] %s: base 0x%x is not page aligned' % (x['name'], x['base']))
        if not isinstance(x['units'], int) or x['units'] < 1:
            r.err('[[module]] %s: units must be at least 1' % x['name'])
        if x['file'] not in names:
            r.err('[[module]] %s: file "%s" has no [[dump.file]] hash' % (x['name'], x['file']))
        if 'sites' in x and not os.path.isfile(os.path.join(folder, x['sites'])):
            r.err('[[module]] %s: sites file %s not found' % (x['name'], x['sites']))
    for n in names:
        if n != 'main.npdm' and n not in [x['file'] for x in mods]:
            r.warn('[[dump.file]] %s is hashed but no [[module]] lifts it' % n)

    sh = m.get('shaders', {})
    if sh.get('extractor') not in (None, 'generic', 'ktgl'):
        r.err('[shaders] extractor must be generic or ktgl')
    script = sh.get('extractor_script')
    if script and not os.path.isfile(os.path.join(REPO, script)):
        r.err('[shaders] extractor_script %s not found in the repository' % script)
    if not os.path.isfile(os.path.join(folder, 'config.py')):
        r.err('no config.py next to the manifest (the lifter\'s --game %s)' % r.name)
    if not os.path.isfile(os.path.join(REPO, 'runtime', 'games', r.name, '%s_game.h' % r.name)):
        r.err('no runtime/games/%s/%s_game.h (game_manifest.h GAME_HEADER)' % (r.name, r.name))
    return r, m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('games', nargs='*', help='game ids or game.toml paths (default: every recomp/games/*/game.toml)')
    ap.add_argument('--strict', action='store_true', help='placeholders are errors (for a release)')
    a = ap.parse_args(argv)
    paths = []
    for x in a.games or sorted(os.listdir(GAMES)):
        p = x if x.endswith('.toml') else os.path.join(GAMES, x, 'game.toml')
        if os.path.isfile(p):
            paths.append(os.path.abspath(p))
        elif a.games:
            print('%s: no game.toml' % x)
            return 1

    bad, seen = 0, {}
    for p in paths:
        r, m = check(p, a.strict)
        if m and 'files' in m and 'launcher' in m:
            for what, val in (('id', m.get('game', {}).get('id')), ('save_folder', m['files'].get('save_folder')),
                              ('launcher identifier', m['launcher'].get('identifier'))):
                if val in seen.get(what, {}):
                    r.err('%s "%s" is also used by %s' % (what, val, seen[what][val]))
                seen.setdefault(what, {})[val] = r.name
        status = 'FAIL' if r.errors else ('ok, %d warning(s)' % len(r.warnings) if r.warnings else 'ok')
        print('%s: %s' % (r.name, status))
        for e in r.errors:
            print('  error: ' + e)
        for w in r.warnings:
            print('  warning: ' + w)
        bad += bool(r.errors)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
