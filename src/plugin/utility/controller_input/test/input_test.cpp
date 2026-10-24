// SPDX-License-Identifier: Apache-2.0
#include <atomic>
#include <gtest/gtest.h>

#include "controller_plugin.hpp"
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
