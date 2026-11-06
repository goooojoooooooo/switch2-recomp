# SPDX-License-Identifier: GPL-3.0-or-later
"""Fill the dump block of game.toml from the player's own Legends: Z-A dump (decrypted exefs/).

    python -I recomp/games/plza/fill_manifest.py --exefs <dump>/exefs [--version 2.0.0] [--display-version 2.0.0] [--dry-run]

Reads main.npdm (program id, checked against [game] title_id) and every NSO (main, sdk, subsdk*, rtld): build id, sha256, .text size.
Rewrites what lies between the `# --- BEGIN DUMP` and `# --- END DUMP ---` lines: [dump], one [[dump.file]] per exefs file, and one
[[module]] per NSO in pkp's order (main 0, sdk 1, subsdk0.., rtld last as the entry module), with pkp's load addresses and
translation units at about 45k instructions each (docs/S1b.md). --version also sets [game] version. Only ids and hashes are written:
no game code or data goes into the file.
"""
import argparse
import hashlib
import os
import re
import struct
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, 'game.toml')
BEGIN = '# --- BEGIN DUMP'
END = '# --- END DUMP ---'
INSNS_PER_UNIT = 45000
BASES = {'main': 0x7100000000, 'sdk': 0x7500000000, 'subsdk0': 0x7600000000, 'rtld': 0x7700000000}


def base_of(name):
    if name in BASES:
        return BASES[name]
    return 0x7800000000 + (int(name[6:]) - 1) * 0x100000000      # subsdk1.. past rtld's slot


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def nso_info(path):
    """NSO header: 'NSO0', .text segment {file off, mem off, size} at 0x10, ModuleId (build id) at 0x40."""
    with open(path, 'rb') as f:
        head = f.read(0x100)
    if len(head) < 0x60 or head[:4] != b'NSO0':
        raise SystemExit('%s is not a decrypted NSO (no NSO0 magic)' % path)
    return {'build_id': head[0x40:0x54].hex(), 'text_size': struct.unpack_from('<I', head, 0x18)[0]}


def npdm_program_id(path):
    """main.npdm: 'META', ACI0 offset at 0x70, ProgramId at ACI0 + 0x10."""
    with open(path, 'rb') as f:
        data = f.read()
    if data[:4] != b'META':
        raise SystemExit('main.npdm does not start with META: is the exefs decrypted?')
    aci = struct.unpack_from('<I', data, 0x70)[0]
    if data[aci:aci + 4] != b'ACI0':
        raise SystemExit('main.npdm: no ACI0 section')
    return struct.unpack_from('<Q', data, aci + 0x10)[0]


def scan(exefs):
    names = [n for n in ('main', 'sdk') if os.path.isfile(os.path.join(exefs, n))]
    subs = sorted((n for n in os.listdir(exefs) if re.fullmatch(r'subsdk\d+', n)), key=lambda n: int(n[6:]))
    names += subs + (['rtld'] if os.path.isfile(os.path.join(exefs, 'rtld')) else [])
    for need in ('main', 'rtld', 'main.npdm'):
        if not os.path.isfile(os.path.join(exefs, need)):
            raise SystemExit('missing %s in %s' % (need, exefs))
    mods = []
    for i, n in enumerate(names):
        p = os.path.join(exefs, n)
        info = nso_info(p)
        mods.append(dict(info, name=n, index=i, base=base_of(n), sha256=sha256(p),
                         units=max(1, -(-info['text_size'] // 4 // INSNS_PER_UNIT))))
    return mods


def block(mods, npdm_sha, version, display_version):
    out = [BEGIN + ' (written by fill_manifest.py; edits inside are replaced) ---', '[dump]',
           'version = "%s"' % version, 'display_version = "%s"' % display_version,
           'main_build_id = "%s"' % next(m['build_id'] for m in mods if m['name'] == 'main'),
           'example_folder = "LegendsZA_dump"', '']
    for m in mods:
        out += ['[[dump.file]]', 'name = "%s"' % m['name'], 'sha256 = "%s"' % m['sha256']]
    out += ['[[dump.file]]', 'name = "main.npdm"', 'sha256 = "%s"' % npdm_sha, '']
    for m in mods:
        out += ['[[module]]', 'name = "%s"' % m['name'], 'file = "%s"' % m['name'], 'base = 0x%x' % m['base'],
                'index = %d' % m['index'], 'units = %d' % m['units']]
        if m['name'] == 'main':
            out.append('sites = "main.sites"')
        if m['name'] == 'rtld':
            out.append('entry = true')
    out.append(END)
    return '\n'.join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--exefs', required=True, help='decrypted exefs/ of your dump (the update\'s, if you have one)')
    ap.add_argument('--version', help='game version of this dump, e.g. 2.0.0 (control.nacp; not in exefs)')
    ap.add_argument('--display-version', help='version name players know (default: --version)')
    ap.add_argument('--dry-run', action='store_true', help='print the new block, do not write game.toml')
    a = ap.parse_args(argv)

    text = open(MANIFEST, encoding='utf-8').read()
    game = tomllib.loads(text)['game']
    pid = npdm_program_id(os.path.join(a.exefs, 'main.npdm'))
    want = int(game['title_id'], 16)
    if pid & ~0xFFF != want & ~0xFFF:
        raise SystemExit('main.npdm program id %016X is not %s (%s)' % (pid, game['title_id'], game['title']))
    mods = scan(a.exefs)
    version = a.version or 'unknown'
    new = block(mods, sha256(os.path.join(a.exefs, 'main.npdm')), version, a.display_version or version)

    start, end = text.find(BEGIN), text.find(END)
    if start < 0 or end < start:
        raise SystemExit('game.toml has no BEGIN/END DUMP markers')
    text = text[:start] + new + text[end + len(END):]
    if a.version:
        text = re.sub(r'(?m)^version = "[^"]*"(?=\nplatform)', 'version = "%s"' % a.version, text, count=1)
    tomllib.loads(text)                                  # never write a manifest that does not parse

    for m in mods:
        print('%-8s index %d  base 0x%x  units %4d  build %s' % (m['name'], m['index'], m['base'], m['units'], m['build_id']))
    if a.dry_run:
        print(new)
        return 0
    with open(MANIFEST, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('written: %s' % MANIFEST)
    return 0


if __name__ == '__main__':
    sys.exit(main())
