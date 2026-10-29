# SPDX-License-Identifier: Apache-2.0
"""Layered button/trigger mappings with Common inheritance."""
from dataclasses import dataclass

from .input import A, B, X, Y, VIEW, LB, RB, LT, RT


MODES = ("playlists", "media", "timeline")
SCOPES = ("common",) + MODES
DISABLED = "disabled"
LAYERS = ("normal", "shifted")
BUTTONS = {"a": A, "b": B, "x": X, "y": Y, "view": VIEW,
           "lb": LB, "rb": RB, "lt": LT, "rt": RT}
SHIFT_BUTTONS = tuple(button for button in BUTTONS if button != "a")
FUNCTIONS = {
    "toggle_playback": ("Play / Pause", MODES),
    "toggle_guide": ("Controller Guide", MODES),
    "toggle_mask": ("Toggle Mask", MODES),
    "cycle_loop": ("Cycle Playback Behavior", MODES),
    "cycle_compare": ("Cycle Compare Layout", MODES),
    "exposure_down": ("Exposure Down", MODES),
    "exposure_up": ("Exposure Up", MODES),
    "clear_selection": ("Clear Checked Media", ("media",)),
}
CATEGORIES = {
    "toggle_playback": "Transport",
    "toggle_guide": "Controller",
    "toggle_mask": "Image/display",
    "cycle_loop": "Playback behavior",
    "cycle_compare": "Compare",
    "exposure_down": "Image/display",
    "exposure_up": "Image/display",
    "clear_selection": "Browsing",
}


@dataclass(frozen=True)
class ButtonBinding:
    mode: str
    button: str
    action: str
    layer: str = "normal"


@dataclass(frozen=True)
class ButtonConfiguration:
    bindings: tuple[ButtonBinding, ...]
    shift: str = "lt"

    def __post_init__(self):
        if not isinstance(self.bindings, tuple):
            raise ValueError("Button bindings must be an immutable tuple")
        if self.shift not in SHIFT_BUTTONS:
            raise ValueError("Unsupported Shift input: " + str(self.shift))
        inputs, actions = set(), set()
        for binding in self.bindings:
            if not isinstance(binding, ButtonBinding) or binding.action is None:
                raise ValueError("Invalid button binding")
            self.validate_target(binding.mode, binding.button, binding.action, binding.layer)
            if binding.layer not in LAYERS:
                raise ValueError("Unsupported mapping layer: " + str(binding.layer))
            if binding.button == self.shift:
                raise ValueError("The dedicated Shift input cannot have a mapping")
            input_key = (binding.mode, binding.layer, binding.button)
            action_key = (binding.mode, binding.action)
            if input_key in inputs or (binding.action != DISABLED and action_key in actions):
                raise ValueError("Each button and function may be assigned only once per mode")
            inputs.add(input_key)
            actions.add(action_key)

    @staticmethod
    def validate_target(mode, button, action, layer="normal"):
        if mode not in SCOPES:
            raise ValueError("Unsupported controller mode: " + str(mode))
        if not isinstance(button, str) or button not in BUTTONS:
            raise ValueError("Unsupported editable button: " + str(button))
        if action == DISABLED:
            if mode == "common" and layer == "normal":
                raise ValueError("Common bindings must be assigned or unassigned")
            return
        if action is not None and (
                not isinstance(action, str) or action not in FUNCTIONS
                or (mode == "common" and FUNCTIONS[action][1] != MODES)
                or (mode != "common" and mode not in FUNCTIONS[action][1])):
            raise ValueError("Unsupported function in " + mode + ": " + str(action))

    @classmethod
    def defaults(cls):
        bindings = [
            ButtonBinding("common", button, action, layer)
            for button, action, layer in (
                ("x", "toggle_playback", "normal"), ("view", "toggle_guide", "normal"),
                ("a", "toggle_mask", "normal"), ("y", "cycle_loop", "normal"),
                ("y", "cycle_compare", "shifted"))
        ]
        return cls(tuple(sorted(bindings, key=lambda b: (b.mode, b.button, b.layer))))

    def explicit_action(self, mode, button, layer="normal"):
        return next((b.action for b in self.bindings
                     if b.mode == mode and b.button == button and b.layer == layer), None)

    def _scope_action(self, mode, button, layer):
        explicit = self.explicit_action(mode, button, layer)
        if explicit is None and layer == "shifted":
            explicit = self.explicit_action(mode, button)
        return explicit

    def effective(self, mode, button, layer="normal"):
        if button == self.shift:
            return None, "shift"
        explicit = self._scope_action(mode, button, layer)
        if explicit == DISABLED:
            return None, "disabled"
        if explicit is not None:
            return explicit, mode
        if mode == "common":
            return None, "unassigned"
        inherited = self._scope_action("common", button, layer)
        if inherited == DISABLED:
            return None, "disabled"
        if inherited is None:
            return None, "unassigned"
        if any(b.mode == mode and b.action == inherited for b in self.bindings):
            return None, "suppressed"
        return inherited, "common"

    def action(self, mode, button, layer="normal"):
        return self.effective(mode, button, layer)[0]

    def assign(self, mode, button, action, layer="normal"):
        self.validate_target(mode, button, action, layer)
        if layer not in LAYERS:
            raise ValueError("Unsupported mapping layer: " + str(layer))
        if button == self.shift:
            raise ValueError("The dedicated Shift input cannot have a mapping")
        bindings = [b for b in self.bindings if not (
            b.mode == mode and ((b.button == button and b.layer == layer) or (
                action != DISABLED and b.action == action)))]
        if action is not None:
            bindings.append(ButtonBinding(mode, button, action, layer))
        return ButtonConfiguration(tuple(sorted(
            bindings, key=lambda b: (b.mode, b.button, b.layer))), self.shift)

    def with_shift(self, button):
        return ButtonConfiguration(tuple(
            b for b in self.bindings if b.button != button), button)
