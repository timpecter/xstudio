# SPDX-License-Identifier: Apache-2.0
"""Tests for the compatibility-first live button mapping slice."""
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "plugin" / "python_plugins"))
from controller_input.bindings import Bindings
from controller_input.input import A, B, MENU, RB, LT, RT, X, Edge, Edges, Event, Sample, State
from controller_input.mapping import BUTTONS, ButtonBinding, ButtonConfiguration, DISABLED, FUNCTIONS, MODES


class ConfigurationTests(unittest.TestCase):
    def test_layer_precedence_disable_and_normal_fallback(self):
        config = ButtonConfiguration(()).assign("common", "b", "toggle_playback")
        config = config.assign("common", "b", "toggle_mask", "shifted")
        self.assertEqual(config.action("media", "b", "shifted"), "toggle_mask")
        config = config.assign("media", "b", "exposure_up")
        self.assertEqual(config.action("media", "b", "shifted"), "exposure_up")
        config = config.assign("media", "b", DISABLED)
        self.assertIsNone(config.action("media", "b", "shifted"))
        config = config.assign("media", "b", "exposure_down", "shifted")
        self.assertEqual(config.action("media", "b", "shifted"), "exposure_down")
        self.assertIsNone(config.action("media", "b"))
        config = config.assign("common", "x", "toggle_guide")
        config = config.assign("common", "x", DISABLED, "shifted")
        self.assertIsNone(config.action("common", "x", "shifted"))
        self.assertEqual(config.action("common", "x"), "toggle_guide")

    def test_displacement_across_layers_preserves_other_scopes(self):
        config = ButtonConfiguration.defaults()
        changed = config.assign("common", "b", "toggle_playback", "shifted")
        self.assertIsNone(changed.action("common", "x"))
        self.assertEqual(changed.action("timeline", "b", "shifted"), "toggle_playback")
        changed = changed.assign("timeline", "x", "toggle_playback", "shifted")
        self.assertEqual(changed.effective("timeline", "b", "shifted"), (None, "suppressed"))
        self.assertEqual(changed.action("media", "b", "shifted"), "toggle_playback")
        with self.assertRaises(ValueError):
            ButtonConfiguration((ButtonBinding("media", "a", "toggle_mask"),
                                 ButtonBinding("media", "b", "toggle_mask", "shifted")))
        for layer in ("invalid", None):
            with self.assertRaises(ValueError):
                config.assign("media", "b", "toggle_mask", layer)

    def test_shift_exclusion_and_reassignment(self):
        config = ButtonConfiguration.defaults().assign("media", "b", "toggle_mask", "shifted")
        shifted = config.with_shift("b")
        self.assertEqual(shifted.shift, "b")
        self.assertEqual(shifted.effective("media", "b"), (None, "shift"))
        self.assertIsNone(shifted.action("common", "lt"))
        self.assertFalse(any(b.button == "b" for b in shifted.bindings))
        for button in ("a", "menu", "dpad", None):
            with self.assertRaises(ValueError):
                config.with_shift(button)
        with self.assertRaises(ValueError):
            shifted.assign("media", "b", "toggle_mask")

    def test_defaults_and_mode_local_displacement(self):
        config = ButtonConfiguration.defaults()
        changed = config.assign("common", "a", "toggle_playback")
        self.assertEqual(changed.action("common", "a"), "toggle_playback")
        self.assertIsNone(changed.action("common", "x"))
        self.assertIsNone(next(
            (b for b in changed.bindings
             if b.mode == "common" and b.action == "toggle_mask"), None))
        self.assertEqual(changed.action("media", "a"), "toggle_playback")
        self.assertIsNone(changed.action("media", "x"))
        self.assertEqual(config.action("common", "a"), "toggle_mask")

    def test_disconnect_and_round_trip(self):
        config = ButtonConfiguration.defaults().assign("media", "x", DISABLED)
        self.assertIsNone(config.action("media", "x"))
        self.assertEqual(config.action("common", "x"), "toggle_playback")
        self.assertEqual(ButtonConfiguration(config.bindings), config)

    def test_factory_default_mode_includes_viewer_functions_and_compare(self):
        config = ButtonConfiguration.defaults()
        self.assertEqual(config.action("common", "a"), "toggle_mask")
        self.assertEqual(config.action("common", "y"), "cycle_loop")
        self.assertEqual(config.action("common", "y", "shifted"), "cycle_compare")
        self.assertNotIn("viewer", [b.mode for b in config.bindings])

    def test_rejects_invalid_bindings(self):
        for bindings in (
                (ButtonBinding("grading", "a", "toggle_mask"),),
                (ButtonBinding("common", "menu", "toggle_playback"),),
                (ButtonBinding("common", "lt", "toggle_playback"),),
                (ButtonBinding("common", "dpad", "toggle_playback"),),
                (ButtonBinding("common", "a", "unknown"),),
                (ButtonBinding("common", "a", "toggle_mask"),
                 ButtonBinding("common", "a", "toggle_playback")),
                (ButtonBinding("common", "a", "toggle_playback"),
                 ButtonBinding("common", "b", "toggle_playback"))):
            with self.subTest(bindings=bindings), self.assertRaises(ValueError):
                ButtonConfiguration(bindings)

    def test_rejects_invalid_disconnect_target(self):
        config = ButtonConfiguration.defaults()
        for mode, button in (("bad", "x"), ("common", "menu")):
            with self.assertRaises(ValueError):
                config.assign(mode, button, None)

    def test_common_override_disable_and_restore(self):
        config = ButtonConfiguration.defaults()
        self.assertEqual(config.effective("media", "x"), ("toggle_playback", "common"))
        changed = config.assign("media", "x", "toggle_mask")
        self.assertEqual(changed.effective("media", "x"), ("toggle_mask", "media"))
        self.assertEqual(changed.action("timeline", "x"), "toggle_playback")
        disabled = changed.assign("media", "x", DISABLED).assign("media", "view", DISABLED)
        self.assertIsNone(disabled.action("media", "x"))
        self.assertIsNone(disabled.action("media", "view"))
        restored = disabled.assign("media", "x", None)
        self.assertEqual(restored.effective("media", "x"), ("toggle_playback", "common"))
        with self.assertRaises(ValueError):
            config.assign("common", "x", DISABLED)

    def test_local_duplicate_suppresses_without_mutating_common(self):
        config = ButtonConfiguration.defaults()
        changed = config.assign("media", "b", "toggle_playback")
        self.assertEqual(changed.effective("media", "x"), (None, "suppressed"))
        self.assertEqual(changed.action("media", "b"), "toggle_playback")
        self.assertEqual(changed.action("common", "x"), "toggle_playback")
        self.assertEqual(changed.action("common", "x"), "toggle_playback")
        self.assertEqual(changed.assign("media", "b", None), config)

    def test_common_edits_preserve_local_and_disabled_bindings(self):
        config = ButtonConfiguration.defaults().assign("media", "x", DISABLED)
        changed = config.assign("common", "x", "exposure_up")
        self.assertIsNone(changed.action("media", "x"))
        self.assertEqual(changed.action("timeline", "x"), "exposure_up")
        self.assertEqual(changed.action("common", "a"), "toggle_mask")
        for action, (_, modes) in FUNCTIONS.items():
            for mode in (("common", *modes) if modes == MODES else modes):
                self.assertEqual(config.assign(mode, "b", action).action(mode, "b"), action)


class LiveMappingTests(unittest.TestCase):
    def setUp(self):
        self.bindings = Bindings()
        self.sequence = 0
        self.held = 0

    def event(self, button=0, edge=Edge.DOWN):
        self.sequence += 1
        if edge == Edge.DOWN:
            self.held |= button
        elif edge == Edge.UP:
            self.held &= ~button
        return self.bindings.accept(Event(1, self.sequence, edge, button, self.held))

    def test_live_assignment_undo_redo_and_dirty(self):
        self.bindings.edit("assign", 0, "common", "a", "toggle_playback")
        self.assertTrue(self.bindings.dirty)
        self.assertEqual(self.event(A).action, "toggle_playback")
        self.assertIsNone(self.event(X))
        self.event(A, Edge.UP)
        self.event(X, Edge.UP)
        self.bindings.edit("undo", 1)
        self.assertFalse(self.bindings.dirty)
        self.assertEqual(self.event(A).action, "toggle_mask")
        self.assertEqual(self.event(X).action, "toggle_playback")
        self.bindings.edit("redo", 2)
        self.assertTrue(self.bindings.dirty)
        self.assertEqual(self.bindings.revision, 3)

    def test_stale_and_invalid_edits_leave_history_untouched(self):
        self.bindings.edit("assign", 0, "common", "b", "toggle_playback")
        before = self.bindings.configuration
        for operation, revision, mode, button, action in (
                ("assign", 0, "common", "a", "toggle_playback"),
                ("assign", 1, "common", "menu", "toggle_playback"),
                ("assign", 1, "media", "a", "unknown"),
                ("invalid", 1, None, None, None)):
            with self.assertRaises(ValueError):
                self.bindings.edit(operation, revision, mode, button, action)
            self.assertEqual(self.bindings.configuration, before)
            self.assertEqual(self.bindings.revision, 1)
        self.bindings.edit("undo", 1)
        self.assertFalse(self.bindings.dirty)

    def test_noop_preserves_revision_and_new_edit_clears_redo(self):
        self.bindings.edit("assign", 0, "common", "x", "toggle_playback")
        self.assertEqual(self.bindings.revision, 0)
        with self.assertRaises(ValueError):
            self.bindings.edit("undo", 0)
        self.bindings.edit("assign", 0, "common", "b", "toggle_playback")
        self.bindings.edit("undo", 1)
        self.bindings.edit("assign", 2, "common", "b", "toggle_guide")
        with self.assertRaises(ValueError):
            self.bindings.edit("redo", 3)

    def test_qml_numeric_revision_is_accepted_but_boolean_is_not(self):
        with self.assertRaises(ValueError):
            self.bindings.edit("assign", False, "common", "b", "toggle_playback")
        self.bindings.edit("assign", 0.0, "common", "b", "toggle_playback")
        self.assertEqual(self.bindings.revision, 1)

    def test_remapping_held_input_waits_for_release(self):
        self.assertIsNone(self.event(B))
        self.bindings.edit("assign", 0, "common", "b", "toggle_playback")
        self.assertIsNone(self.event(B))
        self.event(B, Edge.UP)
        self.assertEqual(self.event(B).action, "toggle_playback")

    def test_reconnect_baseline_blocks_held_input(self):
        self.held = X
        self.event(edge=Edge.CONNECTED)
        self.assertIsNone(self.event(X))
        self.event(X, Edge.UP)
        self.assertEqual(self.event(X).action, "toggle_playback")

    def test_specialised_mode_bindings_apply_only_while_menu_is_open(self):
        self.bindings.edit("assign", 0, "media", "b", "exposure_up")
        self.bindings.mode = "media"
        self.event(MENU)
        self.event(MENU, Edge.UP)
        self.assertEqual(self.event(B).action, "exposure_up")
        self.event(B, Edge.UP)
        self.assertEqual(self.event(A).action, "confirm")
        self.event(A, Edge.UP)
        self.event(MENU)
        self.event(MENU, Edge.UP)
        self.assertEqual(self.bindings.mode, "common")
        self.assertIsNone(self.event(B))
        self.event(B, Edge.UP)
        self.assertEqual(self.event(A).action, "toggle_mask")

    def test_legacy_chords_survive_ordinary_button_remapping(self):
        self.bindings.edit("assign", 0, "media", "a", "toggle_playback")
        self.event(MENU)
        self.event(MENU, Edge.UP)
        self.bindings.mode = "media"
        self.event(RB)
        self.assertEqual(self.event(RT).action, "toggle_select")
        self.assertEqual(self.event(A).action, "confirm")
        self.event(A, Edge.UP)
        self.event(MENU)
        self.event(MENU, Edge.UP)
        self.assertEqual(self.event(A).action, "toggle_mask")

    def test_common_live_history_disable_and_held_protection(self):
        self.assertEqual(self.event(X).action, "toggle_playback")
        self.bindings.edit("assign", 0, "common", "x", "toggle_mask")
        self.assertIsNone(self.event(X))
        self.event(X, Edge.UP)
        self.bindings.mode = "timeline"
        self.assertEqual(self.event(X).action, "toggle_mask")
        self.bindings.edit("assign", 1, "timeline", "x", DISABLED)
        self.event(X, Edge.UP)
        self.assertIsNone(self.event(X))
        self.bindings.edit("undo", 2)
        self.event(X, Edge.UP)
        self.assertEqual(self.event(X).action, "toggle_mask")
        self.bindings.edit("undo", 3)
        self.assertFalse(self.bindings.dirty)
        self.event(X, Edge.UP)
        self.assertEqual(self.event(X).action, "toggle_playback")

    def test_shift_both_release_orders_and_fresh_presses(self):
        self.bindings.mode = "timeline"
        self.bindings.edit("assign", 0, "common", "b", "toggle_mask", "shifted")
        self.assertIsNone(self.event(B))
        self.event(LT)
        self.assertEqual(self.bindings.layer, "shifted")
        self.assertIsNone(self.event(B))
        self.event(B, Edge.UP)
        self.assertEqual(self.event(B).action, "toggle_mask")
        self.event(LT, Edge.UP)
        self.assertEqual(self.bindings.layer, "normal")
        self.assertIsNone(self.event(B))
        self.event(B, Edge.UP)
        self.assertIsNone(self.event(B))
        self.event(B, Edge.UP)
        self.event(LT)
        self.assertEqual(self.event(B).action, "toggle_mask")
        self.event(B, Edge.UP)
        self.event(LT, Edge.UP)
        self.assertIsNone(self.event(B))

    def test_shift_change_undo_load_and_reconnect_held_safety(self):
        self.bindings.edit("assign", 0, "common", "b", "toggle_mask", "shifted")
        self.event(LT)
        self.bindings.edit("shift", 1, button="rb")
        self.assertEqual(self.bindings.configuration.shift, "rb")
        self.assertEqual(self.bindings.layer, "normal")
        self.bindings.edit("undo", 2)
        self.assertEqual(self.bindings.configuration.shift, "lt")
        self.assertEqual(self.bindings.layer, "normal")
        self.event(LT, Edge.UP)
        self.event(LT)
        self.assertEqual(self.bindings.layer, "shifted")
        self.bindings.load_configuration(self.bindings.configuration)
        self.assertEqual(self.bindings.layer, "normal")
        self.held = LT | RT
        self.event(edge=Edge.CONNECTED)
        self.assertEqual(self.bindings.layer, "normal")
        self.assertIsNone(self.event(RT))
        self.event(LT, Edge.UP)
        self.event(LT)
        self.assertEqual(self.bindings.layer, "shifted")

    def test_reserved_selection_controls_work_if_chosen_as_shift(self):
        for shift in ("rt", "y"):
            with self.subTest(shift=shift):
                resolver = Bindings()
                resolver.configuration = resolver.configuration.with_shift(shift)
                resolver.mode = "media"
                resolver.menu_open = True
                button = BUTTONS[shift]
                command = resolver.accept(Event(1, 1, Edge.DOWN, button, button))
                self.assertEqual(command.action, "toggle_select" if shift == "rt" else "clear_selection")

    def test_digital_shift_and_action_in_same_sample_uses_new_layer(self):
        self.bindings.configuration = self.bindings.configuration.with_shift("rb").assign(
            "common", "b", "exposure_up", "shifted")
        edges = Edges()
        commands = []
        for sequence, state in enumerate((State(True), State(True, B | RB)), 1):
            for event in edges.accept(Sample(1, sequence, state)):
                command = self.bindings.accept(event)
                if command:
                    commands.append(command.action)
        self.assertEqual(commands, ["exposure_up"])


if __name__ == "__main__":
    unittest.main()
