// SPDX-License-Identifier: Apache-2.0
#pragma once

#include "input.hpp"
#include "xstudio/plugin_manager/plugin_base.hpp"

namespace xstudio::controller_input {

class ControllerPlugin : public plugin::StandardPlugin {
  public:
    using Observe = std::function<void(const utility::JsonStore &)>;
    ControllerPlugin(
        caf::actor_config &cfg,
        const utility::JsonStore &settings,
        Poller::Read read = read_xinput,
        Observe observe   = {});

  protected:
    void on_exit() override;
    caf::message_handler message_handler_extensions() override;

  private:
    Edges edges_;
    Observe observe_;
    std::unique_ptr<Poller> poller_;
};

} // namespace xstudio::controller_input
