// SPDX-License-Identifier: Apache-2.0
#pragma once

#include "bindings.hpp"
#include "input.hpp"
#include "xstudio/playhead/enums.hpp"
#include "xstudio/plugin_manager/plugin_base.hpp"

namespace xstudio::controller_input {

// Exposure step in stops per press, and the OCIO exposure attribute limits.
constexpr float exposure_step = 0.25f;
constexpr float exposure_min  = -10.0f;
constexpr float exposure_max  = 10.0f;

// Loop -> Play Once -> Ping-Pong -> Loop.
playhead::LoopMode next_loop_mode(playhead::LoopMode current);
const char *loop_mode_name(playhead::LoopMode mode);

struct ExposureFanOut;

class ControllerPlugin : public plugin::StandardPlugin {
  public:
    using Observe = std::function<void(const utility::JsonStore &)>;
    ControllerPlugin(
        caf::actor_config &cfg,
        const utility::JsonStore &settings,
        Poller::Read read       = read_xinput,
        Observe observe         = {},
        Observe observe_command = {});

  protected:
    void on_exit() override;
    caf::message_handler message_handler_extensions() override;

  private:
    void execute(const Command &command);
    void toggle_playback();
    void cycle_loop();
    void toggle_mask();
    void adjust_exposure(float delta);
    void start_exposure();
    void read_exposure(std::shared_ptr<ExposureFanOut> state);
    void write_exposure(std::shared_ptr<ExposureFanOut> state);
    void finish_exposure();
    caf::actor registry_actor(const std::string &name, const char *action);

    Edges edges_;
    Bindings bindings_;
    Observe observe_;
    Observe observe_command_;
    float pending_exposure_{0.0f};
    bool exposure_busy_{false};
    std::unique_ptr<Poller> poller_;
};

} // namespace xstudio::controller_input
