# SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass

from .input import A, X, Y, MENU, RB, VIEW, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT, DPAD_UP, Edge


MODES = ("viewer", "playlists", "media", "timeline")


@dataclass(frozen=True)
class Command:
    action: str
    mode: str
    generation: int
    sequence: int


BROWSE_MODES = ("playlists", "media")


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
            # Menu is the gate for mode changes and for browsing playlists/media.
            if event.button in (DPAD_LEFT, DPAD_RIGHT):
                step = 1 if event.button == DPAD_RIGHT else -1
                self.mode = MODES[(MODES.index(self.mode) + step) % len(MODES)]
                action = "select_mode"
            elif self.mode in BROWSE_MODES:
                action = {
                    DPAD_UP: "browse_previous", DPAD_DOWN: "browse_next", A: "confirm",
                }.get(event.button)
                # RB acts as a shift modifier for multi-selecting media.
                if action == "confirm" and self.mode == "media" and event.buttons & RB:
                    action = "toggle_select"
            else:
                action = None
        else:
            action = {X: "toggle_playback", VIEW: "toggle_guide"}.get(event.button)
            if action is None and self.mode == "viewer":
                action = {
                    DPAD_LEFT: "exposure_down", DPAD_RIGHT: "exposure_up",
                    DPAD_UP: "previous_media", DPAD_DOWN: "next_media",
                    A: "toggle_mask", Y: "cycle_loop",
                }.get(event.button)
        if action is not None:
            return Command(action, self.mode, event.generation, event.sequence)
        return None
