// SPDX-License-Identifier: GPL-3.0-or-later
// Pokémon Legends: Z-A: the whole game module as one nxrt::game::Info (plza_game.h).
//
// STATUS: skeleton. No play-mode table yet (Info::play and play_defaults stay null, which the base handles: play::game_play() and
// play::game_defaults() return null and the hooks that need a game are skipped). Play mode comes here as Z-A's hooks are found, in the
// shape of runtime/games/pkp/pkp_game.cpp: the frame update function on the main thread (with `entryhook` in
// recomp/games/plza/main.sites), factory keyboard bindings, then camera, menu and display hooks.
#include "plza_game.h"

namespace nxrt::games::plza {

const game::Info& full_info() {
    static const game::Info info = core_info();
    return info;
}

}  // namespace nxrt::games::plza

void nxrt_register_game_plza() { nxrt::game::set_current(&nxrt::games::plza::full_info()); }
