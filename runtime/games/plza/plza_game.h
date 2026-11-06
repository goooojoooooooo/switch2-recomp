// SPDX-License-Identifier: GPL-3.0-or-later
// The Pokémon Legends: Z-A game module (docs/GAME_BOUNDARY.md): what the game-independent base needs to run this title, as one
// nxrt::game::Info. Libraries (games/plza/CMakeLists.txt), each a superset of the one before:
//   nxrt_game_plza_data   identity, branding (pure data)          the launcher           nxrt_register_game_plza_data()
//   nxrt_game_plza_core   + title facts (needs nxrt)              the service tests      nxrt_register_game_plza_core()
//   nxrt_game_plza        + play-mode hooks (needs nxrt_gfx)      plza.exe               nxrt_register_game_plza()
// The game exe (game-build/src/game_main.cpp, GAME_REGISTER) calls nxrt_register_game_plza() before nxrt::init().
#pragma once

#include "nxrt/game.h"

void nxrt_register_game_plza();
void nxrt_register_game_plza_core();
void nxrt_register_game_plza_data();

namespace nxrt::games::plza {
const game::Info& data_info();     // plza_data.cpp
const game::Info& core_info();     // plza_core.cpp
const game::Info& full_info();     // plza_game.cpp
}  // namespace nxrt::games::plza
