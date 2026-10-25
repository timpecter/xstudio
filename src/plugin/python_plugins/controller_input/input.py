# SPDX-License-Identifier: Apache-2.0
import ctypes
from dataclasses import dataclass
from enum import Enum


DPAD_UP = 0x0001
DPAD_DOWN = 0x0002
DPAD_LEFT = 0x0004
DPAD_RIGHT = 0x0008
MENU = 0x0010
VIEW = 0x0020
RB = 0x0200
A = 0x1000
B = 0x2000
X = 0x4000
Y = 0x8000


class Gamepad(ctypes.Structure):
    _fields_ = [
        ("buttons", ctypes.c_uint16),
        ("left_trigger", ctypes.c_uint8),
        ("right_trigger", ctypes.c_uint8),
        ("left_x", ctypes.c_int16),
        ("left_y", ctypes.c_int16),
        ("right_x", ctypes.c_int16),
        ("right_y", ctypes.c_int16),
    ]


class XInputState(ctypes.Structure):
    _fields_ = [("packet", ctypes.c_uint32), ("gamepad", Gamepad)]


class XInputReader:
    def __init__(self):
        self._library = ctypes.WinDLL("xinput1_4.dll")
        self._get_state = self._library.XInputGetState
        self._get_state.argtypes = [ctypes.c_uint32, ctypes.POINTER(XInputState)]
        self._get_state.restype = ctypes.c_uint32

    def __call__(self):
        state = XInputState()
        result = self._get_state(0, ctypes.byref(state))
        if result == 1167:  # ERROR_DEVICE_NOT_CONNECTED
            return State()
        if result:
            raise ctypes.WinError(result)
        return State(True, state.gamepad.buttons & 0xF3FF)


@dataclass(frozen=True)
class State:
    connected: bool = False
    buttons: int = 0


@dataclass(frozen=True)
class Sample:
    generation: int
    sequence: int
    state: State


class Edge(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DOWN = "down"
    UP = "up"


@dataclass(frozen=True)
class Event:
    generation: int
    sequence: int
    edge: Edge
    button: int
    buttons: int


class Edges:
    def __init__(self):
        self.state = State()
        self.generation = 0
        self.sample_sequence = 0
        self.event_sequence = 0

    def accept(self, sample):
        state = sample.state
        if (sample.sequence <= self.sample_sequence
                or sample.generation < self.generation
                or (state.connected and not self.state.connected
                    and sample.generation <= self.generation)
                or (not state.connected and sample.generation != self.generation)):
            return None

        self.sample_sequence = sample.sequence
        events = []

        def emit(edge, button=0):
            self.event_sequence += 1
            events.append(Event(
                sample.generation, self.event_sequence, edge, button, state.buttons))

        if state.connected and sample.generation > self.generation:
            self.generation = sample.generation
            emit(Edge.CONNECTED)
        elif self.state.connected and not state.connected:
            emit(Edge.DISCONNECTED)
        elif self.state.connected and state.connected:
            changed = self.state.buttons ^ state.buttons
            for bit in range(16):
                button = 1 << bit
                if changed & button:
                    emit(Edge.DOWN if state.buttons & button else Edge.UP, button)
        self.state = state
        return events
