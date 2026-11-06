# Legends Z-A: guía de arranque (bring-up)

Orden de trabajo para llevar `plza` del esqueleto a un juego que arranca y se juega bien. Cada paso dice qué archivo cambia y cómo
se comprueba. Todo parte de **tu propio volcado** (tu consola, tu cartucho o compra): el repositorio nunca guarda nada del juego.

## 0. Volcado

El launcher ya lo hace solo: en *Set up* eliges tus NSP/XCI y tus claves, y llama a `nx_extract` con el title ID de `game.toml`.
A mano (`tools/extract`):

```
nx_extract --input base.xci --input update.nsp --keys prod.keys --title-id 0100F43008C44000 --out <volcado> --check
nx_extract --input base.xci --input update.nsp --keys prod.keys --title-id 0100F43008C44000 --out <volcado>
```

- `--check` identifica sin escribir: confirma qué programa y qué actualización usa. La *Switch 2 Edition* puede traer su propio
  ejecutable; el que importa es el `exefs` que realmente corre en Switch 2.
- `extract.json` cuenta `zbic_modules`. Si es mayor que 0, el lifter necesita una copia convertida:
  `nx_extract --plain-nso <exefs> <salida>` (`runtime/docs/zbic.md`).

## 1. Manifiesto

```
python -I recomp/games/plza/fill_manifest.py --exefs <volcado>/updates/<v>/exefs --version <x.y.z>
python -I recomp/scripts/check_manifest.py --strict plza
```

`fill_manifest.py` rechaza un volcado que no sea Z-A. Después confirma a mano en `game.toml`:
- `platform`: `switch2` si el `exefs` es el ejecutable de Switch 2 (NVN2), `switch1` si es el de Switch 1. Cambia los núcleos y la
  memoria que el runtime le da al juego (`runtime/src/kernel/svc_info.cpp`).
- `languages`: los bits de `control.nacp` (`SupportedLanguage`).

## 2. Cobertura del lifter (antes de compilar nada)

```
cd recomp
python -m nxrecomp cover <exefs>/main --game plza
```

Lista las palabras de instrucción de `.text` que el lifter no sabe traducir. Cada una sin cubrir es un `guest_unimpl` en tiempo de
ejecución. Se arreglan en `nxrecomp/lift/tier2/x_*.py` y se prueban con los oráculos (`recomp/README.md`: difftest, e2e). Huecos
conocidos: `recomp/docs/GAPS.md`.

## 3. Traducir y compilar

Entorno de desarrollo: el de `README.md` (VS Build Tools, LLVM, CMake, Ninja, Python 3.13, .NET 8, vcpkg, Rust, Node).

```
recomp\scripts\build_game.cmd plza                          (lifter + bibliotecas plza_<módulo> en work\build\plza)
cmake ... -DNXRT_GAMES=plza                                  (runtime con el módulo runtime/games/plza)
cmake ... -DGAME_MANIFEST=<repo>/recomp/games/plza/game.toml (game-build: con dos juegos en recomp/games hay que elegir)
```

El jugador no necesita nada de esto: `game-build/release_b/game_build.py` hace la traducción, compilación y enlace en su PC a
partir de `game.toml` (verifica hashes, traduce, compila con Zig y enlaza contra `plza_rt.dll`).

## 4. Primer arranque

`plza.exe --log plza.log`. El log dice dónde se para. Lo habitual, en orden:

1. **Datos del título** (`runtime/games/plza/plza_core.cpp`, ahora con valores de Pokopia): pila, prioridad y núcleo del hilo
   principal desde `main.npdm`; tamaños de partida guardada desde `control.nacp` o desde lo que el juego pide en el log; `firmware`
   según la versión de SDK de `sdk`.
2. **Servicios y SVC sin implementar**: el log los nombra (por ejemplo `am` avisa de applets que Pokopia nunca lanzó). Se
   implementan en la base (`runtime/src/services/`, `runtime/src/kernel/`) y sirven para cualquier juego.
3. **Esperas lentas en el arranque**: bucles `SleepThread` que solo consultan un estado. Pokopia ahorra ~12 s con la tabla
   `kPollSleeps` de `pkp_core.cpp`; en Z-A van en `plza_core.cpp` (`g.poll_sleeps`).

## 5. Shaders

El launcher arma la caché con `tools/shaders/scripts/extract_generic.py` sobre el romfs (Z-A no usa KTGL, así que el extractor
`ktgl` no aplica). Los shaders que falten en juego se vuelcan con `NXRT_NVN_DUMP_MISSING` y se analizan con
`tools/shaders/scripts/census.py --game plza`.

## 6. Modo de juego (lo que hace que se sienta como un port de PC)

Siguiendo `runtime/games/pkp/pkp_game.cpp` y `runtime/docs/GAME_BOUNDARY.md`:

1. **Hook de frame**: la función que el bucle principal llama una vez por frame en el hilo principal. Va como `entryhook <dir>`
   en `main.sites` y como `frame_update` en `plza_game.cpp` (`GamePlay`). Sin él no hay entrada de teclado/ratón ni límite de FPS.
2. **Controles de fábrica**: `kSettingsText` y revisiones (`GameDefaults`), con el esquema de botones de Z-A.
3. **Menús, cámara y pantalla**: el código de menús de la base (`runtime/src/gfx/play/menu_ktgl.*`) es del motor de Koei Tecmo;
   Z-A (motor de Game Freak) necesita sus propios hooks de menú. Resolución, FOV, calidad y TAA como `pkp_quality.cpp` y
   `pkp_taa.cpp`.
4. **Sondas de prueba** (`plza_tt_probe.cpp`, como `pkp_tt_probe.cpp`): posición del jugador, zona, tiempo de juego, para las
   pruebas automáticas del runtime.

## 7. Publicar

- `check_manifest.py --strict` sin errores.
- Marca del launcher: `runtime/games/plza/launcher.rc` y `launcher.manifest` (copiar la forma de los de pkp, con icono propio).
- Licencias y avisos como en Pokopia; nada del juego en el paquete.
