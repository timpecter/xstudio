// SPDX-License-Identifier: Apache-2.0
#include "input.hpp"

#include <windows.h>
#include <Xinput.h>
#include <system_error>

using namespace xstudio::controller_input;

State xstudio::controller_input::read_xinput() {
    XINPUT_STATE state{};
    const auto result = XInputGetState(0, &state);
    if (result == ERROR_DEVICE_NOT_CONNECTED)
        return {};
    if (result != ERROR_SUCCESS)
        throw std::system_error(result, std::system_category(), "XInputGetState slot 0");
    return {true, static_cast<uint16_t>(state.Gamepad.wButtons & 0xF3FF)};
}

std::optional<std::vector<Event>> Edges::accept(const Sample &sample) {
    if (sample.sequence <= sample_sequence_ || sample.generation < generation_ ||
        (sample.state.connected && !state_.connected && sample.generation <= generation_) ||
        (!sample.state.connected && sample.generation != generation_))
        return std::nullopt;

    sample_sequence_ = sample.sequence;
    std::vector<Event> events;
    auto emit = [&](Edge edge, uint16_t button) {
        events.push_back(
            {sample.generation, ++event_sequence_, edge, button, sample.state.buttons});
    };

    if (sample.state.connected && sample.generation > generation_) {
        generation_ = sample.generation;
        // The connection snapshot is a baseline, not a set of synthetic presses.
        emit(Edge::Connected, 0);
    } else if (state_.connected && !sample.state.connected) {
        emit(Edge::Disconnected, 0);
    } else if (state_.connected && sample.state.connected) {
        const auto changed = state_.buttons ^ sample.state.buttons;
        for (unsigned bit = 0; bit != 16; ++bit) {
            const auto button = static_cast<uint16_t>(1u << bit);
            if (changed & button)
                emit(sample.state.buttons & button ? Edge::Down : Edge::Up, button);
        }
    }
    state_ = sample.state;
    return events;
}

Poller::Poller(
    Read read, Deliver deliver, ReportError report_error, std::chrono::milliseconds interval)
    : thread_([this, read, deliver, report_error, interval]() {
          uint64_t generation = 0;
          uint64_t sequence   = 0;
          State previous;
          try {
              std::unique_lock lock(mutex_);
              while (!stopped_) {
                  lock.unlock();
                  const auto state = read();
                  lock.lock();
                  if (stopped_)
                      break;
                  if (state.connected && !previous.connected)
                      ++generation;
                  if (state.connected != previous.connected ||
                      (state.connected && state.buttons != previous.buttons)) {
                      deliver({generation, ++sequence, state});
                  }
                  previous = state;
                  wake_.wait_for(lock, interval, [this]() { return stopped_; });
              }
          } catch (const std::exception &error) {
              report_error(error.what());
          }
      }) {}

Poller::~Poller() { stop(); }

void Poller::stop() {
    {
        std::lock_guard lock(mutex_);
        stopped_ = true;
    }
    wake_.notify_all();
    if (thread_.joinable())
        thread_.join();
}
