# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-game configuration of Pokémon Legends: Z-A (Nintendo Switch 2 Edition).

Same shape as recomp/games/pkp/config.py: identity, build id and the module list come from game.toml in this folder (filled from the
player's dump by fill_manifest.py). What stays here is lifter knowledge that is not manifest data: the extra function entries.
"""
import os
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nxrecomp.config import GameConfig, ModuleSpec          # noqa: E402

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game.toml'), 'rb') as _f:
    MANIFEST = tomllib.load(_f)
_GAME = MANIFEST['game']
_BUILD_ID = MANIFEST['dump']['main_build_id'].upper()      # of main (first 20 bytes of the NSO's 32-byte build id field)

# all zeros = the manifest still holds the skeleton's placeholders (fill_manifest.py not run yet): no build is supported
BUILDS = {} if not _BUILD_ID.strip('0') else {_BUILD_ID: _GAME['version']}


class Config(GameConfig):
    name = _GAME['id']
    title_id = _GAME['title_id']
    version = _GAME['version']
    build_id = _BUILD_ID
    modules = [ModuleSpec(m['name'], m['base'], m['file']) for m in MANIFEST['module']]
    overrides = {}
    # rtld's process entry (0x0) has no FDE, symbol or direct branch, so discovery never roots it (as in pkp; runtime/docs/S6.md)
    extra_entries = {'rtld': [0x0]}
    patches = None
