// SPDX-License-Identifier: Apache-2.0
#include <atomic>
#include <caf/actor_registry.hpp>
#include <gtest/gtest.h>
#include <map>

#include "controller_plugin.hpp"
#include "xstudio/ui/keyboard.hpp"
#include "xstudio/ui/viewport/mask.hpp"
#include "xstudio/utility/serialise_headers.hpp"

using namespace xstudio;
using namespace xstudio::controller_input;
using namespace std::chrono_literals;

ACTOR_TEST_MINIMAL()

TEST(ControllerInput, NormalizedEdgesAndIdentity) {
    Edges edges;
    auto connected = edges.accept({1, 1, {true, 0}});
    ASSERT_TRUE(connected);
    ASSERT_EQ(connected->size(), 1);
    EXPECT_EQ(connected->front().edge, Edge::Connected);
    EXPECT_EQ(connected->front().generation, 1);
    EXPECT_EQ(connected->front().sequence, 1);

    auto down = edges.accept({1, 2, {true, 0x1001}});
    ASSERT_TRUE(down);
    ASSERT_EQ(down->size(), 2);
    EXPECT_EQ(down->at(0).button, 0x0001);
    EXPECT_EQ(down->at(1).button, 0x1000);
    EXPECT_EQ(down->at(0).edge, Edge::Down);
    EXPECT_EQ(down->at(1).sequence, 3);
    auto repeated = edges.accept({1, 3, {true, 0x1001}});
    ASSERT_TRUE(repeated);
    EXPECT_TRUE(repeated->empty());
    auto up = edges.accept({1, 4, {true, 0}});
    ASSERT_TRUE(up);
    ASSERT_EQ(up->size(), 2);
    EXPECT_EQ(up->at(0).edge, Edge::Up);
    EXPECT_EQ(up->at(0).button, 0x0001);
    EXPECT_EQ(up->at(1).button, 0x1000);
}

TEST(ControllerInput, ConnectionGenerationsRejectStaleSamples) {
    Edges edges;
    ASSERT_TRUE(edges.accept({1, 1, {true, 0x1000}}));
    auto disconnected = edges.accept({1, 2, {false, 0}});
    ASSERT_TRUE(disconnected);
    ASSERT_EQ(disconnected->size(), 1);
    EXPECT_EQ(disconnected->front().edge, Edge::Disconnected);
    EXPECT_FALSE(edges.accept({1, 3, {true, 0x1000}}));
    auto reconnected = edges.accept({2, 4, {true, 0x1000}});
    ASSERT_TRUE(reconnected);
    ASSERT_EQ(reconnected->size(), 1);
    EXPECT_EQ(reconnected->front().edge, Edge::Connected);
    EXPECT_EQ(reconnected->front().buttons, 0x1000);
    EXPECT_FALSE(edges.accept({1, 100, {true, 0}}));
    EXPECT_FALSE(edges.accept({1, 101, {false, 0}}));
    EXPECT_FALSE(edges.accept({2, 4, {true, 0}}));
    auto released = edges.accept({2, 5, {true, 0}});
    ASSERT_TRUE(released);
    ASSERT_EQ(released->size(), 1);
    EXPECT_EQ(released->front().edge, Edge::Up);
    EXPECT_EQ(released->front().generation, 2);
}

TEST(ControllerInput, PollerCancelsScheduledReadAndReportsErrors) {
    std::mutex mutex;
    std::condition_variable wake;
    bool delivered = false;
    std::atomic<int> reads{0};
    Poller poller(
        [&]() {
            ++reads;
            return State{true, 0};
        },
        [&](const Sample &) {
            std::lock_guard lock(mutex);
            delivered = true;
            wake.notify_all();
        },
        [](const std::string &error) { ADD_FAILURE() << error; },
        10s);
    {
        std::unique_lock lock(mutex);
        ASSERT_TRUE(wake.wait_for(lock, 1s, [&]() { return delivered; }));
    }
    const auto start = std::chrono::steady_clock::now();
    poller.stop();
    EXPECT_LT(std::chrono::steady_clock::now() - start, 500ms);
    const auto stopped_reads = reads.load();
    std::this_thread::sleep_for(40ms);
    EXPECT_EQ(reads.load(), stopped_reads);
    poller.stop();

    std::string reported;
    Poller failing(
        []() -> State { throw std::runtime_error("synthetic read failure"); },
        [](const Sample &) { ADD_FAILURE() << "Unexpected delivery"; },
        [&](const std::string &error) {
            std::lock_guard lock(mutex);
            reported = error;
            wake.notify_all();
        });
    {
        std::unique_lock lock(mutex);
        ASSERT_TRUE(wake.wait_for(lock, 1s, [&]() { return !reported.empty(); }));
        EXPECT_EQ(reported, "synthetic read failure");
    }
    failing.stop();
}

TEST(ControllerInput, PollerProducesConnectionGenerationsWithoutDuplicateSamples) {
    std::mutex mutex;
    std::condition_variable wake;
    const std::vector<State> states{
        {true, 0}, {true, 0x1000}, {true, 0x1000}, {false, 0}, {false, 0}, {true, 0}};
    size_t index = 0;
    std::vector<Sample> samples;
    Poller poller(
        [&]() { return states[std::min(index++, states.size() - 1)]; },
        [&](const Sample &sample) {
            std::lock_guard lock(mutex);
            samples.push_back(sample);
            wake.notify_all();
        },
        [](const std::string &error) { ADD_FAILURE() << error; });
    bool arrived;
    {
        std::unique_lock lock(mutex);
        arrived = wake.wait_for(lock, 1s, [&]() { return samples.size() >= 4; });
    }
    poller.stop();
    ASSERT_TRUE(arrived);
    ASSERT_EQ(samples.size(), 4);
    EXPECT_EQ(samples[0].generation, 1);
    EXPECT_EQ(samples[1].generation, 1);
    EXPECT_EQ(samples[2].generation, 1);
    EXPECT_FALSE(samples[2].state.connected);
    EXPECT_EQ(samples[3].generation, 2);
    for (size_t i = 0; i != samples.size(); ++i)
        EXPECT_EQ(samples[i].sequence, i + 1);
}

TEST(ControllerInput, SyntheticInputReachesPluginOnceAndShutdownStopsWork) {
    ACTOR_INIT_GLOBAL_META()
    fixture f;
    std::mutex mutex;
    std::condition_variable wake;
    std::vector<utility::JsonStore> received;
    std::atomic<int> reads{0};
    auto actor = f.system.spawn<ControllerPlugin>(
        utility::JsonStore(),
        [&]() {
            const auto count = ++reads;
            wake.notify_all();
            return State{true, static_cast<uint16_t>(count >= 2 ? 0x1000 : 0)};
        },
        [&](const utility::JsonStore &event) {
            std::lock_guard lock(mutex);
            received.push_back(event);
            wake.notify_all();
        });
    f.self->monitor(actor);
    bool arrived;
    {
        std::unique_lock lock(mutex);
        arrived = wake.wait_for(
            lock, 1s, [&]() { return received.size() >= 2 && reads.load() >= 6; });
    }
    EXPECT_TRUE(arrived);
    f.self->send_exit(actor, caf::exit_reason::user_shutdown);
    bool exited = false;
    f.self->receive(
        [&](const caf::down_msg &) { exited = true; },
        caf::after(1s) >> [&]() { ADD_FAILURE() << "Plugin failed to exit"; });
    EXPECT_TRUE(exited);
    const auto stopped_reads = reads.load();
    std::this_thread::sleep_for(50ms);
    EXPECT_EQ(reads.load(), stopped_reads);
    std::lock_guard lock(mutex);
    ASSERT_EQ(received.size(), 2);
    EXPECT_EQ(received[0].at("edge"), "connected");
    EXPECT_EQ(received[0].at("sequence"), 1);
    EXPECT_EQ(received[1].at("backend"), "xinput1_4");
    EXPECT_EQ(received[1].at("slot"), 0);
    EXPECT_EQ(received[1].at("edge"), "down");
    EXPECT_EQ(received[1].at("generation"), 1);
    EXPECT_EQ(received[1].at("sequence"), 2);
    EXPECT_EQ(received[1].at("button"), 0x1000);
}

TEST(ControllerInput, AcquisitionFailureStopsActorNormally) {
    ACTOR_INIT_GLOBAL_META()
    fixture f;
    std::atomic<int> reads{0};
    auto actor = f.system.spawn<ControllerPlugin>(utility::JsonStore(), [&]() -> State {
        ++reads;
        throw std::runtime_error("synthetic plugin acquisition failure");
    });
    f.self->monitor(actor);
    bool exited = false;
    f.self->receive(
        [&](const caf::down_msg &down) {
            exited = true;
            EXPECT_EQ(down.reason, caf::exit_reason::normal);
        },
        caf::after(1s) >>
            [&]() {
                ADD_FAILURE() << "Acquisition failure did not stop plugin";
                f.self->send_exit(actor, caf::exit_reason::user_shutdown);
            });
    EXPECT_TRUE(exited);
    EXPECT_EQ(reads.load(), 1);
    std::this_thread::sleep_for(40ms);
    EXPECT_EQ(reads.load(), 1);
}

namespace {
Event down(uint16_t pressed, uint64_t sequence, uint64_t generation = 1) {
    return {generation, sequence, Edge::Down, pressed, pressed};
}
Event up(uint16_t released, uint64_t sequence, uint64_t generation = 1) {
    return {generation, sequence, Edge::Up, released, 0};
}
} // namespace

TEST(ControllerInput, BindingsResolveApprovedLayout) {
    Bindings bindings;
    EXPECT_EQ(bindings.mode(), Mode::Viewer);
    EXPECT_FALSE(bindings.accept({1, 1, Edge::Connected, 0, 0}));

    auto play = bindings.accept(down(button::X, 2));
    ASSERT_TRUE(play);
    EXPECT_EQ(play->action, Action::TogglePlayback);
    EXPECT_EQ(play->sequence, 2);
    EXPECT_FALSE(bindings.accept(up(button::X, 3)));
    EXPECT_EQ(bindings.accept(down(button::DpadUp, 4))->action, Action::ExposureUp);
    EXPECT_EQ(bindings.accept(down(button::DpadDown, 5))->action, Action::ExposureDown);
    EXPECT_EQ(bindings.accept(down(button::Y, 6))->action, Action::CycleLoop);
    EXPECT_EQ(bindings.accept(down(button::Menu, 7))->action, Action::ToggleGuide);
    EXPECT_EQ(bindings.accept(down(button::A, 8))->action, Action::ToggleMask);

    // View is a dedicated modifier: no action alone, and it suppresses other buttons.
    EXPECT_FALSE(bindings.accept(down(button::View, 9)));
    EXPECT_FALSE(bindings.accept(down(button::X, 10)));
    uint64_t sequence = 11;
    EXPECT_FALSE(bindings.accept(down(button::DpadLeft, sequence++)));
    EXPECT_FALSE(bindings.accept(down(button::DpadRight, sequence++)));
    EXPECT_EQ(bindings.mode(), Mode::Viewer);

    // Down steps forward and Up steps back, wrapping at both ends.
    const std::vector<std::pair<uint16_t, Mode>> modes{
        {button::DpadDown, Mode::Playlists},
        {button::DpadDown, Mode::Media},
        {button::DpadDown, Mode::Timeline},
        {button::DpadDown, Mode::Grading},
        {button::DpadDown, Mode::Viewer},
        {button::DpadUp, Mode::Grading},
        {button::DpadUp, Mode::Timeline},
        {button::DpadDown, Mode::Grading},
        {button::DpadDown, Mode::Viewer}};
    for (const auto &[pressed, mode] : modes) {
        auto selected = bindings.accept(down(pressed, sequence++));
        ASSERT_TRUE(selected);
        EXPECT_EQ(selected->action, Action::SelectMode);
        EXPECT_EQ(selected->mode, mode);
        EXPECT_EQ(bindings.mode(), mode);
    }
    EXPECT_FALSE(bindings.accept(up(button::View, sequence++)));
    EXPECT_EQ(bindings.accept(down(button::DpadUp, sequence++))->action, Action::ExposureUp);

    const auto select = [&](Mode mode) {
        EXPECT_FALSE(bindings.accept(down(button::View, sequence++)));
        while (bindings.mode() != mode)
            bindings.accept(down(button::DpadDown, sequence++));
        EXPECT_FALSE(bindings.accept(up(button::View, sequence++)));
    };

    for (const auto mode : {Mode::Timeline, Mode::Grading}) {
        select(mode);
        for (const auto pressed :
             {button::Y,
              button::A,
              button::B,
              button::DpadUp,
              button::DpadDown,
              button::DpadLeft,
              button::DpadRight})
            EXPECT_FALSE(bindings.accept(down(pressed, sequence++)));
        EXPECT_EQ(bindings.accept(down(button::X, sequence++))->action, Action::TogglePlayback);
    }

    for (const auto mode : {Mode::Playlists, Mode::Media}) {
        select(mode);
        EXPECT_EQ(
            bindings.accept(down(button::DpadUp, sequence++))->action, Action::BrowsePrevious);
        EXPECT_EQ(
            bindings.accept(down(button::DpadDown, sequence++))->action, Action::BrowseNext);
        EXPECT_EQ(bindings.accept(down(button::A, sequence++))->action, Action::Confirm);
        EXPECT_EQ(bindings.accept(down(button::B, sequence++))->action, Action::Back);
        EXPECT_FALSE(bindings.accept(down(button::Y, sequence++)));
    }
}

TEST(ControllerInput, LoopModeCyclesThroughAllModes) {
    EXPECT_EQ(next_loop_mode(playhead::LM_LOOP), playhead::LM_PLAY_ONCE);
    EXPECT_EQ(next_loop_mode(playhead::LM_PLAY_ONCE), playhead::LM_PING_PONG);
    EXPECT_EQ(next_loop_mode(playhead::LM_PING_PONG), playhead::LM_LOOP);
}

TEST(ControllerInput, BindingsClearModifierOnConnectionChange) {
    Bindings bindings;
    bindings.accept({1, 1, Edge::Connected, 0, 0});
    EXPECT_FALSE(bindings.accept(down(button::View, 2)));
    EXPECT_FALSE(bindings.accept({1, 3, Edge::Disconnected, 0, 0}));

    // View held through reconnect is baseline, so D-pad keeps its mode action.
    EXPECT_FALSE(bindings.accept({2, 4, Edge::Connected, 0, button::View}));
    auto exposure = bindings.accept(down(button::DpadUp, 5, 2));
    ASSERT_TRUE(exposure);
    EXPECT_EQ(exposure->action, Action::ExposureUp);
    EXPECT_EQ(exposure->generation, 2);
    EXPECT_EQ(bindings.mode(), Mode::Viewer);
}

namespace {
struct FakeStudio {
    std::mutex mutex;
    std::condition_variable wake;
    bool playing{false};
    playhead::LoopMode loop{playhead::LM_LOOP};
    std::map<int, float> exposure{{0, 0.0f}, {1, 9.9f}};
    std::map<int, int> exposure_writes;
    std::vector<bool> mask_events;
    std::vector<utility::JsonStore> commands;

    template <class F> void update(F f) {
        std::lock_guard lock(mutex);
        f();
        wake.notify_all();
    }
};

caf::actor
fake_pipeline(caf::actor_system &system, std::shared_ptr<FakeStudio> studio, int id) {
    return system.spawn([studio, id](caf::event_based_actor *) -> caf::behavior {
        return {
            [studio, id](module::attribute_value_atom, const std::string &title)
                -> caf::result<utility::JsonStore> {
                if (title != "Exposure (E)")
                    return caf::make_error(caf::sec::unexpected_message);
                std::lock_guard lock(studio->mutex);
                return utility::JsonStore(nlohmann::json(studio->exposure[id]));
            },
            [studio, id](
                module::change_attribute_value_atom,
                const std::string &title,
                const utility::JsonStore &value,
                bool) -> bool {
                studio->update([&]() {
                    if (title == "Exposure (E)") {
                        studio->exposure[id] = value.get<float>();
                        ++studio->exposure_writes[id];
                    }
                });
                return true;
            }};
    });
}

caf::actor fake_viewport(caf::actor_system &system, caf::actor pipeline) {
    return system.spawn([pipeline](caf::event_based_actor *) -> caf::behavior {
        return {[pipeline](colour_pipeline::colour_pipeline_atom) { return pipeline; }};
    });
}
} // namespace

TEST(ControllerInput, CommandsDriveStudioActionsOncePerPress) {
    ACTOR_INIT_GLOBAL_META()
    fixture f;
    auto studio = std::make_shared<FakeStudio>();

    auto mask = f.system.spawn([studio](caf::event_based_actor *) -> caf::behavior {
        return {[studio](
                    ui::keypress_monitor::hotkey_event_atom,
                    const utility::Uuid &,
                    bool pressed,
                    const std::string &context,
                    const std::string &,
                    bool) {
            EXPECT_EQ(context, "controller_input");
            studio->update([&]() { studio->mask_events.push_back(pressed); });
        }};
    });
    const ui::Hotkey hotkey(
        'M',
        ui::NoModifier,
        "Toggle Mask",
        "Viewport",
        "",
        "",
        false,
        caf::actor_cast<caf::actor_addr>(mask));
    auto keyboard = f.system.spawn([hotkey](caf::event_based_actor *) -> caf::behavior {
        return {
            [hotkey](ui::keypress_monitor::hotkey_atom, const std::string &name)
                -> caf::result<ui::Hotkey> {
                if (name == hotkey.hotkey_name())
                    return hotkey;
                return caf::make_error(caf::sec::unexpected_message);
            }};
    });

    auto playhead_actor = f.system.spawn([studio](caf::event_based_actor *) -> caf::behavior {
        return {
            [studio](playhead::loop_atom) {
                std::lock_guard lock(studio->mutex);
                return studio->loop;
            },
            [studio](playhead::loop_atom, playhead::LoopMode loop) -> caf::unit_t {
                studio->update([&]() { studio->loop = loop; });
                return caf::unit;
            }};
    });

    auto shared_pipeline = fake_pipeline(f.system, studio, 0);
    const std::vector<caf::actor> viewports{
        fake_viewport(f.system, shared_pipeline),
        fake_viewport(f.system, fake_pipeline(f.system, studio, 1)),
        fake_viewport(f.system, shared_pipeline)};
    auto events = f.system.spawn(
        [studio, viewports, playhead_actor](caf::event_based_actor *) -> caf::behavior {
            return {
                [studio](playhead::play_atom) {
                    std::lock_guard lock(studio->mutex);
                    return studio->playing;
                },
                [studio](playhead::play_atom, bool playing) {
                    studio->update([&]() { studio->playing = playing; });
                    return true;
                },
                [viewports](ui::viewport::viewport_atom) { return viewports; },
                [playhead_actor](ui::viewport::viewport_playhead_atom) {
                    return playhead_actor;
                }};
        });
    f.system.registry().put(global_playhead_events_actor, events);
    f.system.registry().put(keyboard_events, keyboard);

    const std::vector<uint16_t> buttons{
        0,
        button::X,
        0,
        button::DpadUp,
        0,
        button::DpadUp,
        0,
        button::A,
        0,
        button::Y,
        0,
        button::View,
        button::View | button::DpadDown,
        button::View,
        0,
        button::Y,
        0,
        button::View,
        button::View | button::DpadUp,
        0};
    std::atomic<size_t> index{0};
    auto actor = f.system.spawn<ControllerPlugin>(
        utility::JsonStore(),
        [&]() {
            const auto i = std::min(index++, buttons.size() - 1);
            return State{true, buttons[i]};
        },
        ControllerPlugin::Observe(),
        [studio](const utility::JsonStore &command) {
            studio->update([&]() { studio->commands.push_back(command); });
        });

    bool done;
    {
        std::unique_lock lock(studio->mutex);
        done = studio->wake.wait_for(lock, 3s, [&]() {
            return studio->commands.size() >= 7 && studio->playing &&
                   studio->loop == playhead::LM_PLAY_ONCE && studio->mask_events.size() >= 2 &&
                   studio->exposure_writes[0] >= 2 && studio->exposure_writes[1] >= 2;
        });
    }
    f.self->send_exit(actor, caf::exit_reason::user_shutdown);
    f.self->wait_for(actor);
    f.system.registry().erase(global_playhead_events_actor);
    f.system.registry().erase(keyboard_events);
    EXPECT_TRUE(done);

    std::lock_guard lock(studio->mutex);
    const std::vector<std::pair<std::string, std::string>> expected{
        {"toggle_playback", "viewer"},
        {"exposure_up", "viewer"},
        {"exposure_up", "viewer"},
        {"toggle_mask", "viewer"},
        {"cycle_loop", "viewer"},
        {"select_mode", "playlists"},
        // Y has no Playlists binding, so the next command is the return to Viewer.
        {"select_mode", "viewer"}};
    ASSERT_EQ(studio->commands.size(), expected.size());
    uint64_t previous = 0;
    for (size_t i = 0; i != expected.size(); ++i) {
        EXPECT_EQ(studio->commands[i].at("action"), expected[i].first);
        EXPECT_EQ(studio->commands[i].at("mode"), expected[i].second);
        EXPECT_EQ(studio->commands[i].at("generation"), 1);
        EXPECT_GT(studio->commands[i].at("sequence").get<uint64_t>(), previous);
        previous = studio->commands[i].at("sequence").get<uint64_t>();
    }
    EXPECT_TRUE(studio->playing);
    EXPECT_EQ(studio->loop, playhead::LM_PLAY_ONCE);
    EXPECT_EQ(studio->mask_events, (std::vector<bool>{true, false}));
    // The shared pipeline is adjusted once per press, not once per viewport.
    EXPECT_EQ(studio->exposure_writes[0], 2);
    EXPECT_FLOAT_EQ(studio->exposure[0], 0.5f);
    EXPECT_EQ(studio->exposure_writes[1], 2);
    EXPECT_FLOAT_EQ(studio->exposure[1], exposure_max);
}

TEST(ControllerInput, DISABLED_PhysicalXInputButtonEdges) {
    ACTOR_INIT_GLOBAL_META()
    fixture f;
    std::mutex mutex;
    std::condition_variable wake;
    std::vector<utility::JsonStore> received;
    auto actor = f.system.spawn<ControllerPlugin>(
        utility::JsonStore(), Poller::Read(read_xinput), [&](const utility::JsonStore &event) {
            std::lock_guard lock(mutex);
            received.push_back(event);
            wake.notify_all();
        });
    f.self->monitor(actor);
    bool paired = false;
    {
        std::unique_lock lock(mutex);
        paired = wake.wait_for(lock, 30s, [&]() {
            for (const auto &down : received) {
                if (down.at("edge") != "down")
                    continue;
                for (const auto &up : received) {
                    if (up.at("edge") == "up" && up.at("button") == down.at("button") &&
                        up.at("generation") == down.at("generation") &&
                        up.at("sequence") > down.at("sequence"))
                        return true;
                }
            }
            return false;
        });
    }
    f.self->send_exit(actor, caf::exit_reason::user_shutdown);
    bool exited = false;
    f.self->receive(
        [&](const caf::down_msg &) { exited = true; },
        caf::after(1s) >> [&]() { ADD_FAILURE() << "Physical input plugin failed to exit"; });
    EXPECT_TRUE(exited);
    EXPECT_TRUE(paired) << "No physical button down/up pair within 30 seconds";
    std::lock_guard lock(mutex);
    ASSERT_FALSE(received.empty());
    EXPECT_EQ(received.front().at("edge"), "connected");
    for (size_t i = 0; i != received.size(); ++i) {
        EXPECT_EQ(received[i].at("backend"), "xinput1_4");
        EXPECT_EQ(received[i].at("slot"), 0);
        EXPECT_EQ(received[i].at("sequence"), i + 1);
    }
}
