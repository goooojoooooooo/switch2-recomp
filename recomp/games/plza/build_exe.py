# SPDX-License-Identifier: GPL-3.0-or-later
"""Build plza.exe from a repository checkout the way the player-side build does (release model b), without the release package.

    python -I recomp/games/plza/build_exe.py --exefs <dump>/updates/<v>/exefs --rt <runtime DLL build dir> --zig <zig.exe>
                                             --work <work dir> --game <game dir> [--jobs N] [--relift]

  1. verifies the dump against recomp/games/plza/game.toml (game_build.verify),
  2. lifts every module with the repository's lifter (recomp/nxrecomp) into <work>/lift/<module> (skipped when already lifted;
     --relift forces it, e.g. after a lifter or main.sites change),
  3. compiles the C++ with zig (game_build.compile_all: only objects that are missing; a changed translation unit needs its .o deleted),
  4. links <game>/plza.exe against plza_rt.lib (game_build.write_gen + link) and copies plza_rt.dll, the ASTC decoder DLLs and fonts/.

--rt is the build folder of the runtime DLL: cmake game-build with -DGAME_BUILD_RT_DLL=ON -DGAME_MANIFEST=<repo>/recomp/games/plza/game.toml,
target game_rt (README.md, "Run"). --zig: the zig.exe of a release package (Pokopia Recomp's tools/build/zig) or any zig 0.17.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RECOMP = os.path.join(REPO, 'recomp')
sys.path.insert(0, os.path.join(REPO, 'game-build', 'release_b'))
import game_build as gb  # noqa: E402


def lift(exefs, gen, jobs, relift):
    for name, nso, base, index, units, sites in gb.MODULES:
        out = os.path.join(gen, name)
        if not relift and os.path.isfile(os.path.join(out, 'module_%s.cpp' % name)):
            print('lift %s: already there (--relift to redo)' % name)
            continue
        os.makedirs(out, exist_ok=True)
        args = ['lift', os.path.join(exefs, nso), out, '--game', 'plza', '--name', name, '--base', hex(base), '--index', str(index),
                '--shards', str(units), '--jobs', str(jobs)]
        if sites:
            args += ['--sites', os.path.join(HERE, sites)]
        t = time.time()
        code = 'import sys; sys.path.insert(0, %r); from nxrecomp.__main__ import main; sys.exit(main(%r))' % (RECOMP, args)
        rc = subprocess.call([sys.executable, '-I', '-c', code], cwd=RECOMP)
        if rc != 0:
            raise SystemExit('lift %s failed (exit %d)' % (name, rc))
        print('lift %s: %.0f s' % (name, time.time() - t))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--exefs', required=True)
    ap.add_argument('--rt', required=True, help='runtime DLL build folder (plza_rt.dll, plza_rt.lib)')
    ap.add_argument('--zig', required=True)
    ap.add_argument('--work', required=True, help='lift/ and obj/ go here')
    ap.add_argument('--game', required=True, help='plza.exe and the runtime files go here')
    ap.add_argument('--jobs', type=int, default=4, help='compile processes (a big unit takes up to 2 GB)')
    ap.add_argument('--relift', action='store_true')
    a = ap.parse_args(argv)
    work, game, rt = (os.path.abspath(x) for x in (a.work, a.game, a.rt))
    gen, obj = os.path.join(work, 'lift'), os.path.join(work, 'obj')
    if len(game) > 150:   # the save data's working files pass 260 characters below such a folder (plza.ini.example)
        print('WARNING: the game folder path is %d characters long. With Windows long paths off (the default) the game aborts at boot '
              '(nn::fs::IsSaveDataExisting); use a shorter folder, e.g. C:\\Games\\plza.' % len(game))

    gb.RECOMP = RECOMP
    gb.ZIG = os.path.abspath(a.zig)
    gb.SDK = sdk = os.path.join(obj, 'sdk')
    gb.load_manifest(os.path.join(HERE, 'game.toml'))
    gb.verify(os.path.abspath(a.exefs))
    lift(os.path.abspath(a.exefs), gen, os.cpu_count() or 4, a.relift)

    os.makedirs(sdk, exist_ok=True)
    for src in ('game-build/src/stub.cpp', 'game-build/src/rt_api.h', 'game-build/res/game.rc', 'game-build/res/game.manifest.in'):
        shutil.copyfile(os.path.join(REPO, src), os.path.join(sdk, os.path.basename(src)))
    shutil.copyfile(os.path.join(rt, gb.RT_LIB), os.path.join(sdk, gb.RT_LIB))
    env = dict(os.environ)
    env['ZIG_GLOBAL_CACHE_DIR'] = env['ZIG_LOCAL_CACHE_DIR'] = os.path.join(obj, 'zig-cache')
    runner = gb.Runner(os.path.join(obj, 'cancel'))
    t = time.time()
    try:
        gb.compile_all(runner, gen, obj, a.jobs, env)
        print('compile: %.0f s' % (time.time() - t))
        os.makedirs(game, exist_ok=True)
        exe = gb.link(runner, obj, game, env, gb.write_gen(obj))
    except gb.Fail as e:
        raise SystemExit(str(e))
    for name in os.listdir(rt):
        if name.lower().endswith('.dll'):
            shutil.copyfile(os.path.join(rt, name), os.path.join(game, name))
    if os.path.isdir(os.path.join(rt, 'fonts')):
        shutil.copytree(os.path.join(rt, 'fonts'), os.path.join(game, 'fonts'), dirs_exist_ok=True)
    print('built %s' % exe)
    return 0


if __name__ == '__main__':
    sys.exit(main())
