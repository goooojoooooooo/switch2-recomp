# Pokémon Legends: Z-A (plza)

Second game in this tree, added the way `runtime/docs/GAME_BOUNDARY.md` ("Adding a game") describes. Nothing from the game is in
the repository: every id and hash comes from the player's own dump.

| File | What |
|---|---|
| `game.toml` | manifest, dump block filled from update v393216 |
| `fill_manifest.py` | writes the dump block (build id, sha256 of every exefs file, modules, units) from a decrypted `exefs/`; refuses a dump whose `main.npdm` program id is not Z-A's |
| `config.py` | lifter config, read from `game.toml` (as pkp's) |
| `main.sites` | hook sites of main: none yet |
| `CMakeLists.txt` | per-module libraries `plza_<module>` (pkp's, without the link check that points at the missing `../mpr`) |
| `runtime/games/plza/` | game module: identity from the manifest, title facts from main.npdm (save sizes still placeholders), no play mode yet |

## Use

```
python -I recomp/games/plza/fill_manifest.py --exefs <dump>\exefs --version <x.y.z>
python -I recomp/scripts/check_manifest.py --strict plza
recomp\scripts\build_game.cmd plza
```

Full step-by-step (dump, coverage, first boot, shaders, play mode, release): [BRINGUP.md](BRINGUP.md).
`recomp/scripts/check_manifest.py` checks every `recomp/games/*/game.toml` against what CMake, `game_build.py`, the launcher and the
runtime read, and that no two games share an id, save folder or launcher identifier.

Runtime with this game: `-DNXRT_GAMES=plza`. The game exe: `-DGAME_MANIFEST=<repo>/recomp/games/plza/game.toml` (with two manifests
in `recomp/games/`, `game-build/CMakeLists.txt` stops and asks for it).

## What the dump says (update v393216, the code that runs)

- A **Switch 1** program, also in the "Switch 2 Edition" package: NintendoSDK 19.3.11, NVN (not NVN2: `NintendoSDK_NVN-19_3_11`),
  main.npdm ThreadInfo cores 0..2. Hence `platform = "switch1"`: the runtime's Switch 1 paths (3 cores, Switch 1 tick and memory,
  the NVN1 proc table) apply, not Pokopia's Switch 2 ones.
- Modules: `main` (12,947,420 instruction words, 288 units), `sdk` (1,652,876, 37 units), `rtld`. No subsdk. Plain LZ4 NSOs (no ZBIC).
- main.npdm: main thread priority 44, core 0, stack 0x100000, SystemResourceSize 0x1000000 (in `plza_core.cpp`).
- Engine: Game Freak's Trinity (`romfs/arc/data.trpfd`, `data.trpfs`, `system/config/data/trinity_config.trowc`), audio Wwise.
- Not in the dump: `control.nacp`, so the display version, languages and save sizes are still unknown.

## Checked

- `check_manifest.py --strict`: pkp and plza pass.
- `nxrecomp cover`: **100 % of instruction words translate** in all three modules (main, sdk, rtld), with no lifter change.
- `GameManifest.cmake` reads the manifest (`GAME_PLATFORM Switch1`, modules rtld/main/sdk); the three runtime sources compile
  (zig c++, x86_64-windows-gnu); `config.py` loads with the real build id.

## Boot status (2026-11-06, update v393216, RTX 5070, headless)

Built the player's way (game_build.py verify + compile with zig, `plza_rt.dll` from game-build with `GAME_BUILD_RT_DLL=ON`, link with
zig) and booted: **the game reaches its main loop and runs** (60 s run: 24,540 presents, 17.9 M command lists, audio at 48 kHz, 4.25 GB).
Nothing is drawn yet: no shader cache, so every draw is skipped. Fixes it took, in boot order:

1. `runtime/include/nxrt/memory.h`: alias region 8 GiB -> 64 GiB (39-bit layout). nninitStartup asks
   `StandardAllocator::Initialize(nullptr, 12 GiB)`, which nn::os's virtual address memory reserves in the alias region.
2. `runtime/src/kernel/svc_memory.cpp`: MapMemory accepts MapPhysicalMemory pages as the source (thread stacks allocated from that heap).
3. `recomp/nxrecomp/jumptables.py`: computed-goto label tables (`ldr xT, [table, wI, uxtw #3]; br xT`), the Lua 5.4 VM's dispatch:
   a switch over the table's labels instead of an indirect call (main: one unit changed, c_138).
4. `runtime/src/kernel/svc_thread.cpp`: SetThreadCoreMask with IdealCoreUseProcessValue (-2) ignores the mask, as mesosphere does.

**Shader cache, and the first picture.** A run with `[nvn] dump_missing = shader_dump` wrote every block the game made (8,489:
1,435 vertex, 7,028 fragment, 26 compute; Maxwell, NVN1) in the corpus layout; `spirv_harness --batch shader_dump --out
shader_cache/spirv --no-val` translated all 8,489 ok in 19 s. With that cache a 90 s run draws 2.6 M draws (107 skipped), 2,154
pipelines, ~260 fps, and the presented frames (`[nvn] shot_frames`, the `shot_dir` folder must exist) show the game's first-boot
**language selection screen**, complete (UI, fonts incl. CJK, animated background). It waits there for input.
Notes: the harness used is Pokopia 0.6.2's prebuilt one, which has no `--serve` (no on-demand translation); `--no-val` because no
Vulkan SDK `spirv-val` was installed. One unsupported operation: sampler reduction (min/max filtering) not enabled on the device.

**Input.** The frame boundary is the head of the main loop (`midhook 0x7101b291e4`; nnMain's run function calls the frame as
`app->vtable[0x18]` and loops while it returns true), installed through the new `GamePlay::frame_update_mid` (play mode adds a mid-site
hook instead of an entry hook). With it play mode is pumped (frame limiter: ~57 fps), and test scripts drive the game: the keyboard path
(`key Return` -> controls.ini `Return = btn_a`) picks the language, and the left stick moves the cursor on the appearance screen.

**Text (fixed).** Glyphs that were not on the first screen drew as nothing. Z-A's glyph caches are two R8 2048x2048 textures in a
CPU_UNCACHED (coherent) pool in MapPhysicalMemory pages; the CPU rasterizes new glyphs into them after their first upload. The texture
write watch only covered the heap, and VirtualProtect cannot span two reservations, which MapPhysicalMemory makes one per 64 KiB granule.
Now: `write_watch.cpp` accepts regions in the alias region and protects range by range (`protect_range`), `nvn_gpu_texture.cpp` keeps a
second region for MapPhysicalMemory storage (`tex_ww_for`), and `svc_memory.cpp` tells the tracker about physical mapping changes. The
appearance screen reads "Choose an option below to get started.", "Use the Left Stick", "Back". Debug log tag `nvn.texdbg` (level debug)
shows each texture's storage and pool flags and every watch.

## Open

1. Cube maps (`BPTC_SFLOAT` 6-layer textures get the dummy view) and the 5 NVN procs that are only logging stubs
   (`nvnCommandBufferBindSeparateTexturesDeferred`, `...SamplersDeferred`, `SetProvokingVertexMode`, ...).
2. Memory: `[memory] limit_gb = 12` for Z-A (the Switch 1 default of 8 GB stops the run; 6.1 GB on the appearance screen).
3. Shaders: validate the cache with `spirv-val`; a harness with `--serve` (built from tools/shaders) for on-demand translation.
3. Save sizes and languages (no control.nacp in the dump), poll sleeps on the boot path.
4. Release packaging (the launcher reads `game.toml`; branding in `runtime/games/plza/launcher.rc`).
