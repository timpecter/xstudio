# SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass

from .input import A, Y, MENU, RT, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT, DPAD_UP, Edge
from .mapping import BUTTONS, SCOPES, ButtonConfiguration

DEFAULT_MODE = "common"


@dataclass(frozen=True)
class Command:
    action: str
    mode: str
    generation: int
    sequence: int


BROWSE_MODES = ("playlists", "media")


class Bindings:
    def __init__(self):
        self.mode = DEFAULT_MODE
        self.menu_open = False
        self.configuration = ButtonConfiguration.defaults()
        self._baseline = self.configuration
        self.revision = 0
        self._undo = []
        self._redo = []
        self._held = 0
        self._blocked = 0

    @property
    def dirty(self):
        return self.configuration != self._baseline

    @property
    def can_undo(self):
        return bool(self._undo)

    @property
    def can_redo(self):
        return bool(self._redo)

    @property
    def layer(self):
        shift = BUTTONS[self.configuration.shift]
        return "shifted" if self._held & shift and not self._blocked & shift else "normal"

    def check_revision(self, revision):
        if type(revision) not in (int, float) or revision != self.revision:
            raise ValueError("Controller mappings changed; refresh and try again")

    def mark_saved(self):
        self.set_baseline(self.configuration)

    def set_baseline(self, configuration):
        self._baseline = configuration
        self.revision += 1

    def load_configuration(self, configuration):
        if not isinstance(configuration, ButtonConfiguration):
            raise ValueError("Invalid controller button configuration")
        self.configuration = configuration
        self._baseline = configuration
        self._undo.clear()
        self._redo.clear()
        self._blocked |= self._held
        self.revision += 1

    def reset_input(self):
        self.menu_open = False
        self.mode = DEFAULT_MODE
        self._held = 0
        self._blocked = 0

    def edit(self, operation, revision, mode=None, button=None, action=None, layer="normal"):
        self.check_revision(revision)
        if operation in ("assign", "shift"):
            changed = (self.configuration.with_shift(button) if operation == "shift"
                       else self.configuration.assign(mode, button, action, layer))
            if changed == self.configuration:
                return
            self._undo.append(self.configuration)
            self._redo.clear()
        elif operation in ("undo", "redo"):
            source, target = (
                (self._undo, self._redo) if operation == "undo"
                else (self._redo, self._undo))
            if not source:
                raise ValueError("No controller mapping edit to " + operation)
            changed = source.pop()
            target.append(self.configuration)
        else:
            raise ValueError("Unknown controller mapping operation: " + str(operation))
        self.configuration = changed
        self.revision += 1
        self._blocked |= self._held

    def accept(self, event):
        if event.edge in (Edge.CONNECTED, Edge.DISCONNECTED):
            self.menu_open = False
            self.mode = DEFAULT_MODE
            self._held = event.buttons if event.edge == Edge.CONNECTED else 0
            self._blocked = self._held
            return None
        shift = BUTTONS[self.configuration.shift]
        # A sample can change a digital modifier and another button together.
        if bool(event.buttons & shift) != bool(self._held & shift):
            self._blocked |= self._held & ~shift
            self._held = (self._held & ~shift) | (event.buttons & shift)
        if event.edge == Edge.UP:
            self._held &= ~event.button
            self._blocked &= ~event.button
            return None
        was_held = bool(self._held & event.button)
        self._held |= event.button
        if self._blocked & event.button:
            return None
        if event.button == shift and not (
                self.menu_open and self.mode == "media" and event.button in (RT, Y)):
            self._blocked |= self._held & ~event.button
            return None
        if event.button == MENU:
            if not was_held:
                self.menu_open = not self.menu_open
                if not self.menu_open:
                    self.mode = DEFAULT_MODE
            return None
        reserved = {}
        if self.menu_open:
            # Menu is the gate for mode changes and for browsing playlists/media.
            if event.button in (DPAD_LEFT, DPAD_RIGHT):
                step = 1 if event.button == DPAD_RIGHT else -1
                self.mode = SCOPES[(SCOPES.index(self.mode) + step) % len(SCOPES)]
                return Command("select_mode", self.mode, event.generation, event.sequence)
            if self.mode in BROWSE_MODES:
                reserved = {
                    DPAD_UP: "browse_previous", DPAD_DOWN: "browse_next", A: "confirm",
                }
                if self.mode == "media":
                    reserved.update({RT: "toggle_select", Y: "clear_selection"})
                if event.button in reserved:
                    return Command(
                        reserved[event.button], self.mode, event.generation, event.sequence)
                if event.button in (DPAD_UP, DPAD_DOWN):
                    return None
            elif event.button in (DPAD_UP, DPAD_DOWN):
                return None
        button = next((name for name, value in BUTTONS.items()
                       if value == event.button), None)
        action = self.configuration.action(self.mode, button, self.layer)
        if action is None and not self.menu_open:
            action = {
                DPAD_LEFT: "exposure_down", DPAD_RIGHT: "exposure_up",
                DPAD_UP: "previous_media", DPAD_DOWN: "next_media",
            }.get(event.button)
        if action is not None:
            return Command(action, self.mode, event.generation, event.sequence)
        return None
