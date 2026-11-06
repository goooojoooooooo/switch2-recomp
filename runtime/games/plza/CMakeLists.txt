# SPDX-License-Identifier: GPL-3.0-or-later
# The Pokémon Legends: Z-A game module (docs/GAME_BOUNDARY.md, plza_game.h), in the shape of games/pkp. Libraries, each a superset of
# the one before:
#   nxrt_game_plza_data   identity, branding (pure data; the launcher links it)
#   nxrt_game_plza_core   + title facts (links nxrt)
#   nxrt_game_plza        + play-mode hooks (links nxrt_gfx; only with NXRT_BUILD_GFX). plza.exe links this one.
# Build it with -DNXRT_GAMES=plza (or "pkp;plza").
set(_plza "${CMAKE_CURRENT_SOURCE_DIR}")
set(_rt "${PROJECT_SOURCE_DIR}")
get_filename_component(_plza_recomp "${_rt}/../recomp" ABSOLUTE)
include("${_plza_recomp}/cmake/GameManifest.cmake")
game_manifest_load("${_plza_recomp}/games/plza/game.toml")
set(_plza_gen "${CMAKE_CURRENT_BINARY_DIR}/gen")
game_manifest_header("${_plza_gen}/game_manifest.h")
set(NXRT_GAME_PLZA_INCLUDES "${_rt}/include" "${_rt}/games" "${_plza}" "${_rt}/src/gfx" "${_rt}/src/gfx/play" "${_rt}/src/testtools")

add_library(nxrt_game_plza_data STATIC "${_plza}/plza_data.cpp")
target_include_directories(nxrt_game_plza_data PUBLIC ${NXRT_GAME_PLZA_INCLUDES})
target_include_directories(nxrt_game_plza_data PRIVATE "${_plza_gen}")
target_compile_features(nxrt_game_plza_data PUBLIC cxx_std_20)

add_library(nxrt_game_plza_core STATIC "${_plza}/plza_core.cpp")
target_link_libraries(nxrt_game_plza_core PUBLIC nxrt_game_plza_data nxrt)

if(TARGET nxrt_gfx)
    add_library(nxrt_game_plza STATIC "${_plza}/plza_game.cpp")
    target_link_libraries(nxrt_game_plza PUBLIC nxrt_game_plza_core nxrt_gfx)
endif()
