# SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass

from .input import A, B, X, Y, MENU, VIEW, DPAD_DOWN, DPAD_UP, Edge


MODES = ("viewer", "playlists", "media", "timeline")


@dataclass(frozen=True)
class Command:
    action: str
    mode: str
    generation: int
    sequence: int


class Bindings:
    def __init__(self):
        self.mode = "viewer"
        self.menu_held = False

    def accept(self, event):
        if event.edge in (Edge.CONNECTED, Edge.DISCONNECTED):
            self.menu_held = False
            return None
        if event.edge == Edge.UP:
            if event.button == MENU:
                self.menu_held = False
            return None
        if event.button == MENU:
            self.menu_held = True
            return None
        if self.menu_held:
            if event.button not in (DPAD_DOWN, DPAD_UP):
                return None
            step = 1 if event.button == DPAD_DOWN else -1
            self.mode = MODES[(MODES.index(self.mode) + step) % len(MODES)]
            action = "select_mode"
        else:
            action = {X: "toggle_playback", VIEW: "toggle_guide"}.get(event.button)
            if action is None and self.mode == "viewer":
                action = {
                    DPAD_UP: "exposure_up", DPAD_DOWN: "exposure_down",
                    A: "toggle_mask", Y: "cycle_loop",
                }.get(event.button)
            elif action is None and self.mode in ("playlists", "media"):
                action = {
                    DPAD_UP: "browse_previous", DPAD_DOWN: "browse_next",
                    A: "confirm", B: "back",
                }.get(event.button)
        if action is not None:
            return Command(action, self.mode, event.generation, event.sequence)
        return None
