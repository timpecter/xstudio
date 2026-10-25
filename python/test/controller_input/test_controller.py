# SPDX-License-Identifier: Apache-2.0
import ctypes
import importlib
import json
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "plugin" / "python_plugins"))
from controller_input.bindings import Bindings, Command, MODES
from controller_input.input import (
    A, B, X, Y, MENU, VIEW, DPAD_DOWN, DPAD_UP,
    Edge, Edges, Event, Gamepad, Sample, State, XInputReader, XInputState,
)


class InputTests(unittest.TestCase):
    def test_xinput_abi_and_disconnected(self):
        self.assertEqual(ctypes.sizeof(Gamepad), 12)
        self.assertEqual(ctypes.sizeof(XInputState), 16)
        reader = XInputReader.__new__(XInputReader)
        reader._get_state = Mock(return_value=1167)
        self.assertEqual(reader(), State())

    def test_xinput_masks_reserved_bits_and_uses_slot_zero(self):
        reader = XInputReader.__new__(XInputReader)

        def get_state(slot, pointer):
            self.assertEqual(slot, 0)
            pointer._obj.gamepad.buttons = 0xFFFF
            return 0

        reader._get_state = get_state
        self.assertEqual(reader(), State(True, 0xF3FF))

    @unittest.skipUnless(sys.platform == "win32", "Windows error conversion")
    def test_xinput_failure_is_not_disconnect(self):
        reader = XInputReader.__new__(XInputReader)
        reader._get_state = Mock(return_value=5)
        with self.assertRaises(OSError):
            reader()

    def test_baseline_edges_holds_release_and_disconnect(self):
        edges = Edges()
        self.assertEqual(edges.accept(Sample(0, 1, State())), [])
        self.assertEqual(
            [e.edge for e in edges.accept(Sample(1, 2, State(True, X)))],
            [Edge.CONNECTED])
        self.assertEqual(edges.accept(Sample(1, 3, State(True, X))), [])
        self.assertEqual(
            [e.edge for e in edges.accept(Sample(1, 4, State(True)))], [Edge.UP])
        self.assertEqual(
            [e.edge for e in edges.accept(Sample(1, 5, State(True, X)))], [Edge.DOWN])
        self.assertEqual(
            [e.edge for e in edges.accept(Sample(1, 6, State()))], [Edge.DISCONNECTED])

    def test_stale_and_previous_connection_samples_are_rejected(self):
        edges = Edges()
        edges.accept(Sample(1, 1, State(True)))
        edges.accept(Sample(1, 2, State()))
        self.assertIsNone(edges.accept(Sample(1, 3, State(True, X))))
        self.assertIsNone(edges.accept(Sample(2, 2, State(True, X))))
        self.assertEqual(
            [e.edge for e in edges.accept(Sample(2, 4, State(True, MENU)))],
            [Edge.CONNECTED])
        self.assertIsNone(edges.accept(Sample(1, 5, State(True, X))))
        self.assertIsNone(edges.accept(Sample(1, 6, State())))


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.bindings = Bindings()
        self.sequence = 0

    def event(self, button, edge=Edge.DOWN):
        self.sequence += 1
        return self.bindings.accept(Event(1, self.sequence, edge, button, button))

    def test_viewer_layout(self):
        for button, action in (
                (X, "toggle_playback"), (VIEW, "toggle_guide"),
                (A, "toggle_mask"), (Y, "cycle_loop"),
                (DPAD_UP, "exposure_up"), (DPAD_DOWN, "exposure_down")):
            self.assertEqual(self.event(button).action, action)
            self.assertIsNone(self.event(button, Edge.UP))
        self.assertIsNone(self.event(B))

    def test_menu_is_dedicated_modifier_and_four_modes_wrap(self):
        self.assertIsNone(self.event(MENU))
        for button in (X, VIEW, A, Y, B, 0x0004, 0x0008):
            self.assertIsNone(self.event(button))
        for mode in ("playlists", "media", "timeline", "viewer"):
            command = self.event(DPAD_DOWN)
            self.assertEqual((command.action, command.mode), ("select_mode", mode))
        self.assertEqual(self.event(DPAD_UP).mode, "timeline")
        self.event(MENU, Edge.UP)
        self.assertEqual(self.event(X).action, "toggle_playback")

    def test_browse_modes_and_timeline(self):
        for mode in MODES[1:3]:
            self.bindings.mode = mode
            for button, action in (
                    (DPAD_UP, "browse_previous"), (DPAD_DOWN, "browse_next"),
                    (A, "confirm"), (B, "back")):
                self.assertEqual(self.event(button).action, action)
        self.bindings.mode = "timeline"
        for button in (A, B, Y, DPAD_UP, DPAD_DOWN):
            self.assertIsNone(self.event(button))
        self.assertEqual(self.event(VIEW).action, "toggle_guide")

    def test_connection_changes_clear_modifier(self):
        for edge in (Edge.CONNECTED, Edge.DISCONNECTED):
            self.event(MENU)
            self.assertIsNone(self.event(MENU, edge))
            self.assertEqual(self.event(DPAD_UP).action, "exposure_up")


class Attribute:
    def __init__(self, name, value, roles):
        self.name, self.current, self.roles = name, value, roles

    def set_value(self, value):
        self.current = value

    def set_role_data(self, role, value):
        self.roles[role] = value


class FakePluginBase:
    def __init__(self, connection, name):
        self.connection, self.name = connection, name
        self.attrs = {}
        self.ui_connected = False

    def add_attribute(self, name, value, roles):
        if "qml_code" in roles:
            # Module::add_attribute selects QmlCodeAttribute before testing value type.
            value = None
        attr = Attribute(name, value, roles)
        self.attrs[name] = attr
        return attr

    def connect_to_ui(self):
        self.ui_connected = True

    def current_playhead(self):
        return self.connection.playhead

    def cleanup_message_handler(self):
        self.cleaned = True


def controller_module():
    core = types.ModuleType("xstudio.core")
    for name in (
            "attribute_value_atom", "change_attribute_value_atom",
            "colour_pipeline_atom", "log_atom", "play_atom", "redraw_viewport_atom", "viewport_atom"):
        setattr(core, name, type(name, (), {}))
    core.JsonStore = lambda value: types.SimpleNamespace(get=lambda: value)
    core.LoopMode = types.SimpleNamespace(LM_LOOP=1, LM_PLAY_ONCE=0, LM_PING_PONG=2)
    core.LogLevel = types.SimpleNamespace(
        SPDLOG_LEVEL_INFO=2, SPDLOG_LEVEL_WARN=3, SPDLOG_LEVEL_ERROR=4)
    plugin = types.ModuleType("xstudio.plugin")
    plugin.PluginBase = FakePluginBase
    with patch.dict(sys.modules, {"xstudio.core": core, "xstudio.plugin": plugin}):
        spec = importlib.util.spec_from_file_location(
            "controller_input._test_controller",
            ROOT / "src" / "plugin" / "python_plugins" / "controller_input" / "controller.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


CONTROLLER = controller_module()


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        self.connection.api.plugin_manager.plugin_detail = []
        self.connection.api.app.global_playhead_events.remote = "events"
        self.connection.playhead = types.SimpleNamespace(looping=1)
        self.media = [
            types.SimpleNamespace(uuid="m1", name="First media"),
            types.SimpleNamespace(uuid="m2", name="Second media")]
        self.playlist = types.SimpleNamespace(
            uuid="p1", name="Review", containers=[], media=self.media,
            playhead_selection=types.SimpleNamespace(selected_sources=[self.media[0]]))
        self.session = types.SimpleNamespace(
            uuid="s1", playlists=[self.playlist], viewed_container=self.playlist,
            inspected_container=None)
        self.connection.api.session = self.session
        self.plugin = CONTROLLER.ControllerPlugin(
            self.connection, reader=lambda: State(), start=False)

    def tearDown(self):
        self.plugin.cleanup()

    def command(self, action, mode="viewer"):
        self.plugin.execute(Command(action, mode, 1, 1))

    def test_ui_registration_badge_independent_of_guide(self):
        self.assertTrue(self.plugin.ui_connected)
        for name in ("Controller Status", "Controller Connected",
                     "Controller Mode", "Controller Guide"):
            self.assertEqual(self.plugin.attrs[name].roles["groups"], ["controller_input_state"])
        overlay = self.plugin.attrs["Controller Input Overlay"]
        self.assertIs(overlay.current, True)
        self.assertEqual(overlay.roles["groups"], ["viewport_overlay_plugins"])
        self.assertIn("!view.isQuickview", overlay.roles["qml_code"])
        self.plugin.accept(Sample(1, 1, State(True)))
        self.assertTrue(self.plugin.connected.current)
        self.assertFalse(self.plugin.guide.current)
        self.command("select_mode", "playlists")
        self.assertEqual(self.plugin.mode.current, "playlists")
        for expected in (True, False):
            self.command("toggle_guide")
            self.assertEqual(self.plugin.guide.current, expected)
            self.assertEqual(self.plugin.mode.current, "playlists")
        self.plugin.accept(Sample(1, 2, State()))
        self.assertFalse(self.plugin.connected.current)
        redraws = [
            call for call in self.connection.send.call_args_list
            if isinstance(call.args[1], CONTROLLER.redraw_viewport_atom)]
        self.assertEqual(len(redraws), 5)

    def test_input_and_commands_reach_studio_log_at_info_level(self):
        for sequence, state in enumerate(
                (State(True), State(True, VIEW), State(True, VIEW), State(True)), 1):
            self.plugin.accept(Sample(1, sequence, state))
        logs = [
            call.args for call in self.connection.send.call_args_list
            if isinstance(call.args[1], CONTROLLER.log_atom)]
        self.assertEqual(len(logs), 4)  # connect, down, command, up; no held repeat
        self.assertTrue(all(args[0] == self.connection.remote() for args in logs))
        self.assertTrue(all(args[2] == CONTROLLER.LogLevel.SPDLOG_LEVEL_INFO for args in logs))
        inputs = [json.loads(args[3].split(": ", 1)[1])
                  for args in logs if args[3].startswith("Controller Input: ")]
        self.assertEqual([entry["edge"] for entry in inputs], ["connected", "down", "up"])
        self.assertEqual(inputs[1], {
            "backend": "xinput1_4", "slot": 0, "generation": 1,
            "sequence": 2, "edge": "down", "button": VIEW, "buttons": VIEW,
        })
        command = json.loads(logs[2][3].split(": ", 1)[1])
        self.assertEqual(command["action"], "toggle_guide")
        records = self.plugin.take_log_records()
        self.assertEqual(len(records), 4)
        self.assertTrue(all(record[0] > 0 and record[1] == 2 for record in records))
        self.assertEqual([record[2] for record in records], [args[3] for args in logs])
        self.assertEqual(self.plugin.take_log_records(), [])
        bridge = self.plugin.attrs["Controller Log Bridge"]
        self.assertEqual(bridge.roles["groups"], ["dynamic qml items"])
        self.assertTrue(bridge.roles["attr_enabled"])
        self.assertIn("take_log_records", bridge.roles["qml_code"])

    def test_menu_visibility_tracks_press_release_and_disconnect(self):
        for sequence, (state, expected) in enumerate((
                (State(True), False), (State(True, MENU), True),
                (State(True, MENU | DPAD_DOWN), True),
                (State(True, DPAD_DOWN), False),
                (State(True, MENU), True), (State(), False)), 1):
            self.plugin.accept(Sample(1, sequence, state))
            self.assertIs(self.plugin.menu_held.current, expected)
        self.plugin.accept(Sample(2, 7, State(True, MENU)))
        self.assertFalse(self.plugin.menu_held.current)
        self.assertFalse(self.plugin.browse_visible.current)

    def test_browse_highlights_without_selection_source_or_transport_writes(self):
        second = types.SimpleNamespace(uuid="p2", name="Dailies", containers=[])
        child = types.SimpleNamespace(uuid="t1", name="Sequence")
        self.playlist.containers = [child]
        self.session.playlists.append(second)
        self.command("select_mode", "playlists")
        self.assertEqual(self.plugin.browse_rows.current,
                         ["Review", "Review / Sequence", "Dailies"])
        self.assertEqual(self.plugin.browse_index.current, 0)
        self.command("browse_next", "playlists")
        self.assertEqual(self.plugin.browse_index.current, 1)
        self.command("browse_next", "playlists")
        self.assertEqual(self.plugin.browse_index.current, 2)
        self.command("browse_next", "playlists")
        self.assertEqual(self.plugin.browse_index.current, 2)
        self.command("browse_previous", "playlists")
        self.assertEqual(self.plugin.browse_index.current, 1)
        self.assertIs(self.session.viewed_container, self.playlist)
        self.assertEqual(self.playlist.playhead_selection.selected_sources, [self.media[0]])
        self.connection.request_receive_timeout.assert_not_called()
        self.connection.get_named_python_plugin_instance.assert_not_called()
        self.command("back", "playlists")
        self.assertFalse(self.plugin.browse_visible.current)
        with self.assertLogs(CONTROLLER.LOGGER, level="WARNING"):
            self.command("confirm", "playlists")
        self.assertIn("preview only", self.plugin.status.current)
        self.assertIs(self.session.viewed_container, self.playlist)

    def test_media_preview_is_scoped_to_viewed_container(self):
        self.command("select_mode", "media")
        self.command("browse_next", "media")
        self.assertEqual(self.plugin.browse_index.current, 1)
        self.assertEqual(self.plugin.browse_rows.current, ["First media", "Second media"])
        self.playlist.media.reverse()
        self.command("select_mode", "media")
        self.assertEqual(self.plugin.browse_index.current, 0)
        other_media = types.SimpleNamespace(uuid="m3", name="Other media")
        other = types.SimpleNamespace(
            uuid="p2", name="Other", media=[other_media],
            playhead_selection=types.SimpleNamespace(selected_sources=[]))
        self.session.viewed_container = other
        self.command("select_mode", "media")
        self.assertEqual(self.plugin.browse_rows.current, ["Other media"])
        self.assertEqual(self.plugin.browse_index.current, 0)
        self.assertEqual(self.plugin.browse_title.current, "Media preview: Other")
        self.connection.request_receive_timeout.assert_not_called()

    def test_removed_candidates_empty_lists_and_session_replacement(self):
        self.command("select_mode", "media")
        self.command("browse_next", "media")
        self.playlist.media.pop()
        with self.assertLogs(CONTROLLER.LOGGER, level="WARNING"):
            self.command("browse_next", "media")
        self.assertEqual(self.plugin.browse_rows.current, ["First media"])
        self.playlist.media.clear()
        with self.assertLogs(CONTROLLER.LOGGER, level="WARNING"):
            self.command("browse_next", "media")
        self.assertEqual(self.plugin.browse_rows.current, [])
        self.assertEqual(self.plugin.browse_index.current, -1)
        self.assertIn("No items", self.plugin.status.current)
        self.session.uuid = "s2"
        self.command("select_mode", "playlists")
        self.assertEqual(self.plugin.browse_index.current, 0)
        self.assertEqual(list(self.plugin._browse_selection), [("playlists", "s2")])
        self.session.viewed_container = None
        self.session.inspected_container = self.playlist
        self.command("select_mode", "media")
        self.assertEqual(self.plugin.browse_title.current, "Media preview: Review")
        self.assertEqual(self.plugin.browse_rows.current, [])
        self.session.inspected_container = None
        with self.assertLogs(CONTROLLER.LOGGER, level="WARNING"):
            self.command("select_mode", "media")
        self.assertTrue(self.plugin.browse_visible.current)
        self.assertEqual(self.plugin.browse_title.current, "Media preview: no playlist open")
        self.assertEqual(self.plugin.browse_rows.current, [])
        self.assertIn("source unchanged", self.plugin.status.current)

    def test_browse_window_keeps_selection_in_seven_visible_rows(self):
        self.session.playlists = [
            types.SimpleNamespace(uuid=str(i), name="Playlist %s" % i, containers=[])
            for i in range(20)]
        self.command("select_mode", "playlists")
        for _ in range(15):
            self.command("browse_next", "playlists")
        self.assertEqual(len(self.plugin.browse_rows.current), 7)
        self.assertEqual(self.plugin.browse_rows.current[self.plugin.browse_index.current],
                         "Playlist 15")

    def test_warnings_errors_and_tracebacks_reach_studio_log(self):
        self.command("confirm")
        self.plugin._samples.put(Sample(1, 1, State(True)))
        self.plugin._samples.put(Sample(1, 2, State(True, X)))
        self.plugin._samples.put(None)
        self.connection.request_receive_timeout.side_effect = RuntimeError("request failed")
        self.plugin._dispatch()
        logs = [
            call.args for call in self.connection.send.call_args_list
            if isinstance(call.args[1], CONTROLLER.log_atom)]
        self.assertEqual(logs[0][2], CONTROLLER.LogLevel.SPDLOG_LEVEL_WARN)
        self.assertEqual(logs[-1][2], CONTROLLER.LogLevel.SPDLOG_LEVEL_ERROR)
        self.assertIn("Traceback", logs[-1][3])
        self.assertIn("request failed", logs[-1][3])

    def test_cleanup_unregisters_only_this_plugins_log_handler(self):
        other = CONTROLLER.ControllerPlugin(
            self.connection, reader=lambda: State(), start=False)
        try:
            self.plugin.cleanup()
            self.assertNotIn(self.plugin._log_handler, self.plugin._logger.handlers)
            self.assertIn(other._log_handler, other._logger.handlers)
        finally:
            other.cleanup()

    def test_gui_log_consumers_drain_bounded_batches_without_duplicates(self):
        for index in range(300):
            self.plugin._logger.info("Controller test record %s", index)
        first = self.plugin.take_log_records()
        second = self.plugin.take_log_records()
        self.assertEqual((len(first), len(second)), (256, 44))
        self.assertEqual(
            [record[2] for record in first + second],
            ["Controller test record %s" % index for index in range(300)])
        self.assertEqual(self.plugin.take_log_records(), [])

    def test_one_playback_toggle_per_press_and_disconnect_is_safe(self):
        self.connection.request_receive_timeout.return_value = (False,)
        for sequence, state in enumerate(
                (State(True), State(True, X), State(True, X), State()), 1):
            self.plugin.accept(Sample(1, sequence, state))
        calls = self.connection.request_receive_timeout.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args[:2], (2000, "events"))
        self.assertTrue(calls[1].args[-1])

    def test_all_loop_modes_cycle(self):
        for expected in (0, 2, 1, 0):
            self.command("cycle_loop")
            self.assertEqual(self.connection.playhead.looping, expected)

    def test_mask_uses_existing_plugin_callback(self):
        self.command("toggle_mask")
        self.connection.get_named_python_plugin_instance.assert_called_once_with("Mask")
        self.connection.get_named_python_plugin_instance.return_value.toggle_mask_cb.assert_called_once_with(
            True, "controller_input")

    def test_exposure_reads_before_writes_deduplicates_and_clamps(self):
        operations = []

        class Actor:
            def __init__(self, address):
                self.address = address

            def __str__(self):
                return self.address

        def request(timeout, actor, atom, *args):
            operations.append((actor, type(atom).__name__, args))
            if isinstance(atom, CONTROLLER.viewport_atom):
                return (["v1", "v2", "v3"],)
            if isinstance(atom, CONTROLLER.colour_pipeline_atom):
                return (Actor("p1" if actor in ("v1", "v2") else "p2"),)
            if isinstance(atom, CONTROLLER.attribute_value_atom):
                return (types.SimpleNamespace(get=lambda: 9.9 if str(actor) == "p1" else -1.0),)
            return (True,)

        self.connection.request_receive_timeout.side_effect = request
        self.command("exposure_up")
        self.assertEqual([op[1] for op in operations[-4:]], [
            "attribute_value_atom", "attribute_value_atom",
            "change_attribute_value_atom", "change_attribute_value_atom"])
        self.assertEqual([op[2][1].get() for op in operations[-2:]], [10.0, -0.75])
        self.assertEqual([str(op[0]) for op in operations[-2:]], ["p1", "p2"])

    def test_exposure_failure_does_not_write_success_shaped_values(self):
        self.connection.request_receive_timeout.return_value = ([],)
        with self.assertRaisesRegex(RuntimeError, "no viewer"):
            self.command("exposure_down")
        self.connection.request_receive_timeout.assert_called_once()

    def test_unknown_and_unavailable_actions_are_explicit(self):
        with self.assertRaises(ValueError):
            self.command("invalid")
        with self.assertLogs(CONTROLLER.LOGGER, level="WARNING") as logs:
            self.command("confirm", "media")
        self.assertIn("not available yet", logs.output[0])

    def test_legacy_plugin_prevents_dual_dispatch(self):
        detail = Mock()
        detail.uuid.return_value = CONTROLLER.LEGACY_UUID
        self.connection.api.plugin_manager.plugin_detail = [detail]
        with self.assertRaisesRegex(RuntimeError, "dual input"):
            CONTROLLER.ControllerPlugin(self.connection, reader=lambda: State())

    def test_polling_failure_is_reported_and_stops_dispatch(self):
        self.plugin.reader = Mock(side_effect=OSError("device failure"))
        with self.assertLogs(CONTROLLER.LOGGER, level="ERROR"):
            self.plugin._poll()
        self.plugin._dispatch()
        self.assertFalse(self.plugin.connected.current)
        self.assertIn("device failure", self.plugin.status.current)

    def test_worker_command_failure_is_logged(self):
        self.plugin._samples.put(Sample(1, 1, State(True)))
        self.plugin._samples.put(Sample(1, 2, State(True, X)))
        self.plugin._samples.put(None)
        self.connection.request_receive_timeout.side_effect = RuntimeError("request failed")
        with self.assertLogs(CONTROLLER.LOGGER, level="ERROR") as logs:
            self.plugin._dispatch()
        self.assertIn("Controller command failed", logs.output[0])

    def test_polling_stops_and_joins_without_dispatch_after_cleanup(self):
        ready = threading.Event()

        def read():
            ready.set()
            return State()

        plugin = CONTROLLER.ControllerPlugin(self.connection, reader=read)
        self.assertTrue(ready.wait(1))
        threads = list(plugin._threads)
        plugin.cleanup()
        plugin.cleanup()
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertTrue(plugin.cleaned)


if __name__ == "__main__":
    unittest.main()
