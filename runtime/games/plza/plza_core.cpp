// SPDX-License-Identifier: GPL-3.0-or-later
// Pokémon Legends: Z-A, the core part of the game module (plza_game.h): the data part plus the title facts. Needs the runtime library,
// not the graphics one.
//
// Main thread and system resource size: main.npdm of update v393216 (META: priority 44, core 0, stack 0x100000, SystemResourceSize
// 0x1000000; ThreadInfo cores 0..2, a Switch 1 application). Save sizes are still placeholders: the dump has no control.nacp, so they
// come from the boot log (what the game asks for). No test probes and no poll sleeps yet: both need addresses found in Z-A's own main.
#include "plza_game.h"

#include "nxrt/game.h"

#include "nxrt/services.h"

namespace nxrt::games::plza {

namespace {

void title_defaults(services::TitleProfile& p) {
    p.program_id = data_info().program_id;
    p.name = data_info().title;
    p.display_version = data_info().version;
    p.supported_languages = data_info().languages;
    p.account_save_size = 0x4000000;           // placeholder (pkp's); control.nacp / boot log
    p.account_save_journal = 0x4000000;
    p.device_save_size = 0x4000000;
    p.device_save_journal = 0x4000000;
    p.main_thread_stack = 0x100000;            // main.npdm
    p.main_thread_priority = 44;
    p.main_thread_core = 0;
    p.system_resource_size = 0x1000000;        // main.npdm META SystemResourceSize (GetInfo 16)
    p.firmware = "19.0.1";                     // sdk is NintendoSDK 19.3.11: the last 19.x firmware
    p.user_nickname = "Player";
    p.user_uid_hi = 0x0000000000000001ull;
    p.user_uid_lo = 0x41435a4152656370ull;     // "PZARecmp"
}

}  // namespace

const game::Info& core_info() {
    static const game::Info info = [] {
        game::Info g = data_info();
        g.title_defaults = &title_defaults;
        return g;
    }();
    return info;
}

}  // namespace nxrt::games::plza

void nxrt_register_game_plza_core() { nxrt::game::set_current(&nxrt::games::plza::core_info()); }
