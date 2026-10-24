// SPDX-License-Identifier: Apache-2.0
#pragma once

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

namespace xstudio::controller_input {

struct State {
    bool connected{false};
    uint16_t buttons{0};
};

struct Sample {
    uint64_t generation{0};
    uint64_t sequence{0};
    State state;
};

enum class Edge { Connected, Disconnected, Down, Up };

struct Event {
    uint64_t generation;
    uint64_t sequence;
    Edge edge;
    uint16_t button;
    uint16_t buttons;
};

class Edges {
  public:
    std::optional<std::vector<Event>> accept(const Sample &sample);

  private:
    uint64_t generation_{0};
    uint64_t sample_sequence_{0};
    uint64_t event_sequence_{0};
    State state_;
};

// A single XInput slot, not a device selection or binding layer.
State read_xinput();

class Poller {
  public:
    using Read        = std::function<State()>;
    using Deliver     = std::function<void(const Sample &)>;
    using ReportError = std::function<void(const std::string &)>;

    Poller(
        Read read,
        Deliver deliver,
        ReportError report_error,
        std::chrono::milliseconds interval = std::chrono::milliseconds(16));
    ~Poller();
    Poller(const Poller &)            = delete;
    Poller &operator=(const Poller &) = delete;
    void stop();

  private:
    std::mutex mutex_;
    std::condition_variable wake_;
    bool stopped_{false};
    std::thread thread_;
};

} // namespace xstudio::controller_input
