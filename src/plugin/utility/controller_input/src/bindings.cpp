// SPDX-License-Identifier: Apache-2.0
#include "bindings.hpp"

#include <stdexcept>

using namespace xstudio::controller_input;

const char *xstudio::controller_input::mode_name(Mode mode) {
    switch (mode) {
    case Mode::Viewer:
        return "viewer";
    case Mode::Timeline:
        return "timeline";
    case Mode::Playlists:
        return "playlists";
    case Mode::Media:
        return "media";
    case Mode::Grading:
        return "grading";
    }
    throw std::logic_error("Unknown controller mode");
}

const char *xstudio::controller_input::action_name(Action action) {
    switch (action) {
    case Action::SelectMode:
        return "select_mode";
    case Action::TogglePlayback:
        return "toggle_playback";
    case Action::ToggleGuide:
        return "toggle_guide";
    case Action::ExposureUp:
        return "exposure_up";
    case Action::ExposureDown:
        return "exposure_down";
    case Action::ToggleMask:
        return "toggle_mask";
    case Action::CycleLoop:
        return "cycle_loop";
    case Action::BrowsePrevious:
        return "browse_previous";
    case Action::BrowseNext:
        return "browse_next";
    case Action::Confirm:
        return "confirm";
    case Action::Back:
        return "back";
    }
    throw std::logic_error("Unknown controller action");
}

std::optional<Command> Bindings::accept(const Event &event) {
    switch (event.edge) {
    case Edge::Connected:
    case Edge::Disconnected:
        // Buttons held at connect are a baseline, so the modifier starts released.
        view_held_ = false;
        return {};
    case Edge::Up:
        if (event.button == button::View)
            view_held_ = false;
        return {};
    case Edge::Down:
        break;
    }

    if (event.button == button::View) {
        view_held_ = true;
        return {};
    }

    if (view_held_) {
        constexpr int mode_count = static_cast<int>(Mode::Grading) + 1;
        int step                 = 0;
        if (event.button == button::DpadDown)
            step = 1;
        else if (event.button == button::DpadUp)
            step = mode_count - 1;
        else
            return {};
        mode_ = static_cast<Mode>((static_cast<int>(mode_) + step) % mode_count);
        return Command{Action::SelectMode, mode_, event.generation, event.sequence};
    }

    if (auto action = resolve(event.button))
        return Command{*action, mode_, event.generation, event.sequence};
    return {};
}

std::optional<Action> Bindings::resolve(uint16_t pressed) {
    switch (pressed) {
    case button::X:
        return Action::TogglePlayback;
    case button::Menu:
        return Action::ToggleGuide;
    default:
        break;
    }

    switch (mode_) {
    case Mode::Viewer:
        if (pressed == button::DpadUp)
            return Action::ExposureUp;
        if (pressed == button::DpadDown)
            return Action::ExposureDown;
        if (pressed == button::Y)
            return Action::CycleLoop;
        if (pressed == button::A)
            return Action::ToggleMask;
        break;
    case Mode::Timeline:
    case Mode::Grading:
        break;
    case Mode::Playlists:
    case Mode::Media:
        if (pressed == button::DpadUp)
            return Action::BrowsePrevious;
        if (pressed == button::DpadDown)
            return Action::BrowseNext;
        if (pressed == button::A)
            return Action::Confirm;
        if (pressed == button::B)
            return Action::Back;
        break;
    }
    return {};
}
