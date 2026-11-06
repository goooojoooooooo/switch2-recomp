# Pokémon Legends: Z-A (plza) — skeleton

Second game in this tree, added the way `runtime/docs/GAME_BOUNDARY.md` ("Adding a game") describes. Nothing from the game is in
the repository: every id and hash comes from the player's own dump.

| File | What |
|---|---|
| `game.toml` | manifest; the dump block holds placeholders until `fill_manifest.py` runs |
| `fill_manifest.py` | writes the dump block (build id, sha256 of every exefs file, modules, units) from a decrypted `exefs/`; refuses a dump whose `main.npdm` program id is not Z-A's |
| `config.py` | lifter config, read from `game.toml` (as pkp's) |
| `main.sites` | hook sites of main: none yet |
| `CMakeLists.txt` | per-module libraries `plza_<module>` (pkp's, without the link check that points at the missing `../mpr`) |
| `runtime/games/plza/` | game module: identity from the manifest, title facts with pkp's placeholder values, no play mode yet |

## Use

```
python -I recomp/games/plza/fill_manifest.py --exefs <dump>\exefs --version <x.y.z>
recomp\scripts\build_game.cmd plza
```

Runtime with this game: `-DNXRT_GAMES=plza`. The game exe: `-DGAME_MANIFEST=<repo>/recomp/games/plza/game.toml` (with two manifests
in `recomp/games/`, `game-build/CMakeLists.txt` stops and asks for it).

## Checked (no dump)

- `config.py` loads through `nxrecomp.config.load_game('plza')`.
- `fill_manifest.py` on a synthetic exefs (5 NSOs) writes a manifest that parses; a wrong program id is refused.
- `recomp/cmake/GameManifest.cmake` reads the manifest and writes `game_manifest.h` (`GAME_REGISTER nxrt_register_game_plza`).
- `plza_data.cpp`, `plza_core.cpp`, `plza_game.cpp` compile (zig c++, x86_64-windows-gnu).

## Open

1. Fill the manifest from a dump; confirm `platform` (NVN2?) and the version.
2. Title facts in `plza_core.cpp` from `main.npdm` / `control.nacp` / the boot log.
3. Lift, build, boot; then the frame update hook (`entryhook` in `main.sites`) and play mode in `plza_game.cpp`.
4. Not covered: the launcher (Rust, reads `game.toml` at run time), the setup tool and release packaging for a second game.
