// SPDX-License-Identifier: Apache-2.0
#include "controller_plugin.hpp"
#include "xstudio/plugin_manager/plugin_factory.hpp"

using namespace xstudio;
using namespace xstudio::controller_input;

namespace {
const char *edge_name(Edge edge) {
    switch (edge) {
    case Edge::Connected:
        return "connected";
    case Edge::Disconnected:
        return "disconnected";
    case Edge::Down:
        return "down";
    case Edge::Up:
        return "up";
    }
    throw std::logic_error("Unknown controller edge");
}
} // namespace

ControllerPlugin::ControllerPlugin(
    caf::actor_config &cfg,
    const utility::JsonStore &settings,
    Poller::Read read,
    Observe observe)
    : StandardPlugin(cfg, "Controller Input", settings), observe_(std::move(observe)) {
    const auto actor = caf::actor_cast<caf::actor>(this);
    poller_          = std::make_unique<Poller>(
        std::move(read),
        [actor](const Sample &sample) {
            utility::JsonStore json;
            json["generation"] = sample.generation;
            json["sequence"]   = sample.sequence;
            json["connected"]  = sample.state.connected;
            json["buttons"]    = sample.state.buttons;
            caf::anon_mail(utility::event_atom_v, std::string("controller_sample"), json)
                .send(actor);
        },
        [actor](const std::string &error) {
            caf::anon_mail(std::string("controller_input_error"), error).send(actor);
        });
}

caf::message_handler ControllerPlugin::message_handler_extensions() {
    return {
        [this](utility::event_atom, const std::string &kind, const utility::JsonStore &json) {
            if (kind != "controller_sample") {
                spdlog::warn("Controller Input: unexpected event {}", kind);
                return;
            }
            const Sample sample{
                json.at("generation").get<uint64_t>(),
                json.at("sequence").get<uint64_t>(),
                {json.at("connected").get<bool>(), json.at("buttons").get<uint16_t>()}};
            const auto events = edges_.accept(sample);
            if (!events) {
                spdlog::debug(
                    "Controller Input: rejected stale sample generation={} sequence={}",
                    sample.generation,
                    sample.sequence);
                return;
            }
            for (const auto &event : *events) {
                utility::JsonStore normalized;
                normalized["backend"]    = "xinput1_4";
                normalized["slot"]       = 0;
                normalized["generation"] = event.generation;
                normalized["sequence"]   = event.sequence;
                normalized["edge"]       = edge_name(event.edge);
                normalized["button"]     = event.button;
                normalized["buttons"]    = event.buttons;
                spdlog::info("Controller Input: {}", normalized.dump());
                mail(utility::event_atom_v, std::string("controller_input"), normalized)
                    .send(plugin_events_group());
                if (observe_)
                    observe_(normalized);
            }
        },
        [this](const std::string &kind, const std::string &error) {
            spdlog::error("Controller Input: {}: {}; acquisition stopped", kind, error);
            // An acquisition failure must not terminate the linked plugin manager.
            quit(caf::exit_reason::normal);
        }};
}

void ControllerPlugin::on_exit() {
    poller_->stop();
    StandardPlugin::on_exit();
}

extern "C" {
plugin_manager::PluginFactoryCollection *plugin_factory_collection_ptr() {
    return new plugin_manager::PluginFactoryCollection(
        std::vector<std::shared_ptr<plugin_manager::PluginFactory>>{
            std::make_shared<plugin_manager::PluginFactoryTemplate<ControllerPlugin>>(
                utility::Uuid("6d11e948-b80d-4409-9c11-d6b4eb30ad13"),
                "Controller Input",
                plugin_manager::PluginFlags::PF_UTILITY,
                true,
                "xSTUDIO",
                "Windows XInput 1.4 slot 0 connection and button input (no action bindings)")});
}
}
