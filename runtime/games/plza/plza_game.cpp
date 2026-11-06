// SPDX-License-Identifier: GPL-3.0-or-later
// Pokémon Legends: Z-A: the whole game module as one nxrt::game::Info (plza_game.h). Play-mode hooks come here as they are found.
#include "plza_game.h"

#include "play_game.h"
#include "play_types.h"

namespace nxrt::games::plza {

namespace {

// The frame boundary. nnMain (0x7101b2e880) hands the application object to 0x7101b290e0, whose main loop is
//     7101b291e4: x8 = app->vtable[0x18]; r = x8(app); if (r & 1) goto 7101b291e4;   then app->vtable[0x28](app)
// (update v393216). The frame is a virtual call, so the loop head is the one address that runs once per iteration on the main thread:
// a mid-function site (`midhook 0x7101b291e4` in recomp/games/plza/main.sites, GamePlay::frame_update_mid).
constexpr uint64_t kFrameUpdate = 0x1b291e4;

// Factory keyboard and mouse bindings (play_types.h settings file), from Pokopia's (runtime/games/pkp/pkp_game.cpp): keys to the console
// buttons, pads keep the console layout. The roles of Z-A's buttons (A confirm/talk, B back, X menu, ...) are still to be checked in game.
constexpr const char* kSettingsText = R"INI(
[meta]
defaults_rev = 1

[bindings.all]
W = move_forward
S = move_back
A = move_left
D = move_right
Up = look_up
Down = look_down
Left = look_left
Right = look_right
E = btn_a
Return = btn_a
Keypad Enter = btn_a
Mouse1 = btn_zr
Mouse3 = btn_zl
Space = btn_b
Left Shift = btn_b
Backspace = btn_b
Tab = btn_x
F = btn_y
Q = btn_l
R = btn_r
Left Ctrl = btn_lstick
V = btn_rstick
Escape = btn_plus
C = btn_minus
1 = dpad_up
2 = dpad_down
3 = dpad_left
4 = dpad_right

[bindings.menu]
Mouse3 = btn_b
WheelUp = dpad_up
WheelDown = dpad_down
)INI";

const play::GameDefaults& game_defaults() {
    static const play::GameDefaults d = [] {
        play::GameDefaults g;
        g.settings_text = kSettingsText;
        g.defaults_rev = 1;
        return g;
    }();
    return d;
}

const play::GamePlay& game_play() {
    static const play::GamePlay t = [] {
        play::GamePlay p;
        p.frame_update = kFrameUpdate;
        p.frame_update_mid = true;
        return p;
    }();
    return t;
}

}  // namespace

const game::Info& full_info() {
    static const game::Info info = [] {
        game::Info g = core_info();
        g.play = &game_play();
        g.play_defaults = &game_defaults();
        return g;
    }();
    return info;
}

}  // namespace nxrt::games::plza

void nxrt_register_game_plza() { nxrt::game::set_current(&nxrt::games::plza::full_info()); }
