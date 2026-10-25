// SPDX-License-Identifier: Apache-2.0
#include "controller_plugin.hpp"

#include <algorithm>
#include <caf/actor_registry.hpp>

#include "xstudio/plugin_manager/plugin_factory.hpp"
#include "xstudio/ui/keyboard.hpp"

using namespace xstudio;
using namespace xstudio::controller_input;

namespace xstudio::controller_input {
struct ExposureFanOut {
    float delta{0.0f};
    size_t pending{0};
    std::vector<caf::actor> pipelines;
    std::vector<std::optional<float>> values;
};

playhead::LoopMode next_loop_mode(playhead::LoopMode current) {
    switch (current) {
    case playhead::LM_LOOP:
        return playhead::LM_PLAY_ONCE;
    case playhead::LM_PLAY_ONCE:
        return playhead::LM_PING_PONG;
    default:
        return playhead::LM_LOOP;
    }
}

const char *loop_mode_name(playhead::LoopMode mode) {
    switch (mode) {
    case playhead::LM_PLAY_ONCE:
        return "play once";
    case playhead::LM_PING_PONG:
        return "ping-pong";
    default:
        return "loop";
    }
}
} // namespace xstudio::controller_input

namespace {
const auto reply_timeout = std::chrono::seconds(2);
const std::string exposure_attribute{"Exposure (E)"};
const std::string mask_hotkey{"Toggle Mask"};
const std::string hotkey_context{"controller_input"};

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
    Observe observe,
    Observe observe_command)
    : StandardPlugin(cfg, "Controller Input", settings),
      observe_(std::move(observe)),
      observe_command_(std::move(observe_command)) {
    status_ = add_string_attribute("Controller Status", "Status", "Controller disconnected");
    status_->expose_in_ui_attrs_group("controller_input_state");

    guide_enabled_ = add_boolean_attribute("Controller Guide", "Guide", false);
    guide_enabled_->expose_in_ui_attrs_group("controller_input_state");
    connected_ = add_boolean_attribute("Controller Connected", "Connected", false);
    connected_->expose_in_ui_attrs_group("controller_input_state");
    mode_ = add_string_attribute("Controller Mode", "Mode", mode_name(bindings_.mode()));
    mode_->expose_in_ui_attrs_group("controller_input_state");
    qml_viewport_overlay_code(
        R"(
            import QtQuick
            import xStudio 1.0
            import xstudio.qml.models 1.0
            import xstudio.qml.helpers 1.0

            Item {
                anchors.fill: parent
                visible: !view.isQuickview &&
                         (connectedValue.value === true || guideValue.value === true)
                XsModuleData {
                    id: controllerState
                    modelDataName: "controller_input_state"
                }
                XsAttributeValue {
                    id: connectedValue
                    attributeTitle: "Controller Connected"
                    model: controllerState
                }
                XsAttributeValue {
                    id: modeValue
                    attributeTitle: "Controller Mode"
                    model: controllerState
                }
                XsAttributeValue {
                    id: guideValue
                    attributeTitle: "Controller Guide"
                    model: controllerState
                }
                XsAttributeValue {
                    id: statusValue
                    attributeTitle: "Controller Status"
                    model: controllerState
                }
                Rectangle {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 24
                    width: 360
                    height: guideText.implicitHeight + 32
                    radius: 8
                    color: "#dd17191d"
                    border.color: "#8899aabb"

                    Text {
                        id: guideText
                        anchors.fill: parent
                        anchors.margins: 16
                        color: "white"
                        font.pixelSize: 18
                        text: "Controller mode: " +
                              (modeValue.value === undefined ? "" : modeValue.value) +
                              (guideValue.value === true ?
                                  "\n\n" + statusValue.value +
                                  "\n\nMenu + D-pad: change mode" +
                                  "\nX: play / pause; View: guide" +
                                  "\nViewer: D-pad exposure, A mask, Y loop" +
                                  "\nPlaylists / Media: navigation not available yet" : "")
                        wrapMode: Text.WordWrap
                    }
                }
            }
        )");

    const auto actor = caf::actor_cast<caf::actor>(this);
    // Register attributes after StandardPlugin::make_behavior sets the module's actor.
    mail(module::connect_to_ui_atom_v).send(actor);
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
                if (event.edge == Edge::Connected) {
                    connected_->set_value(true);
                    status_->set_value("Controller connected");
                    refresh_overlay();
                } else if (event.edge == Edge::Disconnected) {
                    connected_->set_value(false);
                    status_->set_value("Controller disconnected");
                    refresh_overlay();
                }
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
                if (auto command = bindings_.accept(event))
                    execute(*command);
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

void ControllerPlugin::execute(const Command &command) {
    utility::JsonStore json;
    json["action"]     = action_name(command.action);
    json["mode"]       = mode_name(command.mode);
    json["generation"] = command.generation;
    json["sequence"]   = command.sequence;
    spdlog::info("Controller Command: {}", json.dump());
    mail(utility::event_atom_v, std::string("controller_command"), json)
        .send(plugin_events_group());
    if (observe_command_)
        observe_command_(json);

    switch (command.action) {
    case Action::SelectMode:
        mode_->set_value(mode_name(command.mode));
        status_->set_value(std::string("Mode: ") + mode_name(command.mode));
        refresh_overlay();
        break;
    case Action::ToggleGuide:
        toggle_guide();
        break;
    case Action::TogglePlayback:
        toggle_playback();
        break;
    case Action::ExposureUp:
        adjust_exposure(exposure_step);
        break;
    case Action::ExposureDown:
        adjust_exposure(-exposure_step);
        break;
    case Action::ToggleMask:
        toggle_mask();
        break;
    case Action::CycleLoop:
        cycle_loop();
        break;
    case Action::BrowsePrevious:
    case Action::BrowseNext:
    case Action::Confirm:
    case Action::Back:
        spdlog::warn(
            "Controller Command: {} is not available yet", action_name(command.action));
        break;
    }
}

caf::actor ControllerPlugin::registry_actor(const std::string &name, const char *action) {
    auto actor = system().registry().template get<caf::actor>(name);
    if (!actor)
        spdlog::warn("Controller Command: {} failed: {} is unavailable", action, name);
    return actor;
}

void ControllerPlugin::toggle_guide() {
    const bool enabled = !guide_enabled_->value();
    guide_enabled_->set_value(enabled);
    status_->set_value(enabled ? "Controller guide shown" : "Controller guide hidden");
    refresh_overlay();
}

void ControllerPlugin::refresh_overlay() {
    if (auto events = registry_actor(global_playhead_events_actor, "refresh_overlay"))
        anon_mail(playhead::redraw_viewport_atom_v).send(events);
}

void ControllerPlugin::toggle_playback() {
    auto events = registry_actor(global_playhead_events_actor, "toggle_playback");
    if (!events)
        return;
    mail(playhead::play_atom_v)
        .request(events, reply_timeout)
        .then(
            [this, events](bool playing) {
                mail(playhead::play_atom_v, !playing)
                    .request(events, reply_timeout)
                    .then(
                        [playing](bool) {
                            spdlog::info(
                                "Controller Command: playback {}",
                                playing ? "stopped" : "started");
                        },
                        [](caf::error &err) {
                            spdlog::warn(
                                "Controller Command: toggle_playback failed: {}",
                                to_string(err));
                        });
            },
            [](caf::error &err) {
                spdlog::warn("Controller Command: toggle_playback failed: {}", to_string(err));
            });
}

void ControllerPlugin::cycle_loop() {
    auto events = registry_actor(global_playhead_events_actor, "cycle_loop");
    if (!events)
        return;
    auto fail = [](caf::error &err) {
        spdlog::warn("Controller Command: cycle_loop failed: {}", to_string(err));
    };
    mail(ui::viewport::viewport_playhead_atom_v)
        .request(events, reply_timeout)
        .then(
            [this, fail](caf::actor playhead) {
                if (!playhead) {
                    spdlog::warn("Controller Command: cycle_loop failed: no active playhead");
                    return;
                }
                mail(playhead::loop_atom_v)
                    .request(playhead, reply_timeout)
                    .then(
                        [this, playhead, fail](playhead::LoopMode current) {
                            const auto next = next_loop_mode(current);
                            mail(playhead::loop_atom_v, next)
                                .request(playhead, reply_timeout)
                                .then(
                                    [next]() {
                                        spdlog::info(
                                            "Controller Command: loop mode {}",
                                            loop_mode_name(next));
                                    },
                                    fail);
                        },
                        fail);
            },
            fail);
}

void ControllerPlugin::toggle_mask() {
    auto keyboard = registry_actor(keyboard_events, "toggle_mask");
    if (!keyboard)
        return;
    mail(ui::keypress_monitor::hotkey_atom_v, mask_hotkey)
        .request(keyboard, reply_timeout)
        .then(
            [](const ui::Hotkey &hotkey) {
                size_t notified = 0;
                for (const auto &address : hotkey.watchers()) {
                    auto watcher = caf::actor_cast<caf::actor>(address);
                    if (!watcher)
                        continue;
                    // Same press/release pair that the keyboard hotkey delivers.
                    for (const bool pressed : {true, false})
                        caf::anon_mail(
                            ui::keypress_monitor::hotkey_event_atom_v,
                            hotkey.uuid(),
                            pressed,
                            hotkey_context,
                            std::string(),
                            false)
                            .send(watcher);
                    ++notified;
                }
                if (notified)
                    spdlog::info("Controller Command: mask toggled");
                else
                    spdlog::warn("Controller Command: toggle_mask failed: no mask plugin");
            },
            [](caf::error &err) {
                spdlog::warn("Controller Command: toggle_mask failed: {}", to_string(err));
            });
}

void ControllerPlugin::adjust_exposure(float delta) {
    // Presses are queued so a read-modify-write never overlaps another.
    pending_exposure_ += delta;
    start_exposure();
}

void ControllerPlugin::start_exposure() {
    if (exposure_busy_ || pending_exposure_ == 0.0f)
        return;
    const float delta = pending_exposure_;
    pending_exposure_ = 0.0f;
    auto events       = registry_actor(global_playhead_events_actor, "exposure");
    if (!events)
        return;
    exposure_busy_ = true;
    mail(ui::viewport::viewport_atom_v)
        .request(events, reply_timeout)
        .then(
            [this, delta](const std::vector<caf::actor> &viewports) {
                auto state     = std::make_shared<ExposureFanOut>();
                state->delta   = delta;
                state->pending = viewports.size();
                if (viewports.empty()) {
                    read_exposure(state);
                    return;
                }
                for (const auto &viewport : viewports) {
                    mail(colour_pipeline::colour_pipeline_atom_v)
                        .request(viewport, reply_timeout)
                        .then(
                            [this, state](caf::actor pipeline) {
                                // Shared pipelines are adjusted once.
                                if (pipeline && std::find(
                                                    state->pipelines.begin(),
                                                    state->pipelines.end(),
                                                    pipeline) == state->pipelines.end())
                                    state->pipelines.push_back(pipeline);
                                if (--state->pending == 0)
                                    read_exposure(state);
                            },
                            [this, state](caf::error &err) {
                                spdlog::warn(
                                    "Controller Command: exposure viewer skipped: {}",
                                    to_string(err));
                                if (--state->pending == 0)
                                    read_exposure(state);
                            });
                }
            },
            [this](caf::error &err) {
                spdlog::warn("Controller Command: exposure failed: {}", to_string(err));
                finish_exposure();
            });
}

void ControllerPlugin::read_exposure(std::shared_ptr<ExposureFanOut> state) {
    if (state->pipelines.empty()) {
        spdlog::warn("Controller Command: exposure failed: no viewer colour pipelines");
        finish_exposure();
        return;
    }
    // Read every pipeline before writing any, so synchronised viewers are not
    // stepped twice.
    state->pending = state->pipelines.size();
    state->values.assign(state->pipelines.size(), std::nullopt);
    for (size_t i = 0; i != state->pipelines.size(); ++i) {
        mail(module::attribute_value_atom_v, exposure_attribute)
            .request(state->pipelines[i], reply_timeout)
            .then(
                [this, state, i](const utility::JsonStore &value) {
                    state->values[i] = value.get<float>();
                    if (--state->pending == 0)
                        write_exposure(state);
                },
                [this, state](caf::error &err) {
                    spdlog::warn(
                        "Controller Command: exposure viewer skipped: {}", to_string(err));
                    if (--state->pending == 0)
                        write_exposure(state);
                });
    }
}

void ControllerPlugin::write_exposure(std::shared_ptr<ExposureFanOut> state) {
    state->pending = static_cast<size_t>(
        std::count_if(state->values.begin(), state->values.end(), [](const auto &v) {
            return v.has_value();
        }));
    if (state->pending == 0) {
        spdlog::warn("Controller Command: exposure failed: no readable viewer exposure");
        finish_exposure();
        return;
    }
    const auto total = state->pending;
    for (size_t i = 0; i != state->pipelines.size(); ++i) {
        if (!state->values[i])
            continue;
        const float target =
            std::clamp(*state->values[i] + state->delta, exposure_min, exposure_max);
        mail(
            module::change_attribute_value_atom_v,
            exposure_attribute,
            utility::JsonStore(nlohmann::json(target)),
            true)
            .request(state->pipelines[i], reply_timeout)
            .then(
                [this, state, total](bool) {
                    if (--state->pending == 0) {
                        spdlog::info(
                            "Controller Command: exposure {:+} applied to {} viewer "
                            "pipeline(s)",
                            state->delta,
                            total);
                        finish_exposure();
                    }
                },
                [this, state](caf::error &err) {
                    spdlog::warn(
                        "Controller Command: exposure viewer skipped: {}", to_string(err));
                    if (--state->pending == 0)
                        finish_exposure();
                });
    }
}

void ControllerPlugin::finish_exposure() {
    exposure_busy_ = false;
    start_exposure();
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
                "Windows XInput 1.4 slot 0 controller with a fixed Stage 1 button layout")});
}
}
