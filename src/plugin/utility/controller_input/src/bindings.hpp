// SPDX-License-Identifier: Apache-2.0
#pragma once

#include <cstdint>
#include <optional>

#include "input.hpp"

namespace xstudio::controller_input {

// XInput button masks used by the approved temporary layout.
namespace button {
    constexpr uint16_t DpadUp    = 0x0001;
    constexpr uint16_t DpadDown  = 0x0002;
    constexpr uint16_t DpadLeft  = 0x0004;
    constexpr uint16_t DpadRight = 0x0008;
    constexpr uint16_t Menu      = 0x0010;
    constexpr uint16_t View      = 0x0020;
    constexpr uint16_t A         = 0x1000;
    constexpr uint16_t B         = 0x2000;
    constexpr uint16_t X         = 0x4000;
    constexpr uint16_t Y         = 0x8000;
} // namespace button

enum class Mode { Viewer, Playlists, Media, Timeline, Grading };

enum class Action {
    SelectMode,
    TogglePlayback,
    ToggleGuide,
    ExposureUp,
    ExposureDown,
    ToggleMask,
    CycleLoop,
    BrowsePrevious,
    BrowseNext,
    Confirm,
    Back
};

struct Command {
    Action action;
    Mode mode;
    uint64_t generation;
    uint64_t sequence;
};

const char *mode_name(Mode mode);
const char *action_name(Action action);

// Fixed Stage 1 layout. View is a dedicated modifier: while held, only
// View + D-pad Down/Up (next/previous mode, wrapping) is active. Commands
// dispatch on button down.
class Bindings {
  public:
    std::optional<Command> accept(const Event &event);
    [[nodiscard]] Mode mode() const { return mode_; }

  private:
    std::optional<Action> resolve(uint16_t button);

    Mode mode_{Mode::Viewer};
    bool view_held_{false};
};

} // namespace xstudio::controller_input
