# SPDX-License-Identifier: Apache-2.0
import json
import logging
from pathlib import Path
from queue import Empty, Queue
from threading import Event as StopEvent, Thread

from xstudio.core import (
    JsonStore, LogLevel, LoopMode, attribute_value_atom, change_attribute_value_atom,
    colour_pipeline_atom, log_atom, play_atom, redraw_viewport_atom, viewport_atom,
)
from xstudio.plugin import PluginBase

from .bindings import Bindings
from .input import MENU, Edge, Edges, Sample, State, XInputReader


LOGGER = logging.getLogger(__name__)
LEGACY_UUID = "6d11e948-b80d-4409-9c11-d6b4eb30ad13"


class StudioLogHandler(logging.Handler):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.records = Queue()

    def emit(self, record):
        level = (
            LogLevel.SPDLOG_LEVEL_ERROR if record.levelno >= logging.ERROR else
            LogLevel.SPDLOG_LEVEL_WARN if record.levelno >= logging.WARNING else
            LogLevel.SPDLOG_LEVEL_INFO)
        message = self.format(record)
        self.connection.send(self.connection.remote(), log_atom(), level, message)
        self.records.put([record.created * 1000, int(level), message])

    def take_records(self):
        records = []
        for _ in range(256):
            try:
                records.append(self.records.get_nowait())
            except Empty:
                break
        return records


class ControllerPlugin(PluginBase):
    def __init__(self, connection, reader=None, start=True):
        for detail in connection.api.plugin_manager.plugin_detail:
            if str(detail.uuid()) == LEGACY_UUID:
                raise RuntimeError(
                    "Remove the legacy controller_input.dll and restart xSTUDIO "
                    "before loading the Python controller; dual input is unsafe")
        self.reader = XInputReader() if reader is None else reader
        super().__init__(connection, "Controller Input")
        self.edges = Edges()
        self.bindings = Bindings()
        self._stop = StopEvent()
        self._samples = Queue()
        self._threads = []
        self._guide = False
        self._browse_selection = {}
        self._browse_context = None
        self.events = connection.api.app.global_playhead_events.remote
        self.status = self._state_attribute("Controller Status", "Controller disconnected")
        self.connected = self._state_attribute("Controller Connected", False)
        self.mode = self._state_attribute("Controller Mode", "viewer")
        self.guide = self._state_attribute("Controller Guide", False)
        self.menu_held = self._state_attribute("Controller Menu Held", False)
        self.browse_visible = self._state_attribute("Controller Browse Visible", False)
        self.browse_title = self._state_attribute("Controller Browse Title", "")
        self.browse_rows = self._state_attribute("Controller Browse Rows", [])
        self.browse_index = self._state_attribute("Controller Browse Index", -1)
        self.add_attribute("Controller Input Overlay", True, {
            "groups": ["viewport_overlay_plugins"],
        }).set_role_data(
            "qml_code", Path(__file__).with_name("overlay.qml").read_text(encoding="utf-8"))
        self._logger = LOGGER.getChild(str(id(self)))
        self._logger.setLevel(logging.INFO)
        self._log_handler = StudioLogHandler(connection)
        self._logger.addHandler(self._log_handler)
        self.add_attribute("Controller Log Bridge", False, {
            "groups": ["dynamic qml items"],
            "qml_code": Path(__file__).with_name("log.qml").read_text(encoding="utf-8"),
            "attr_enabled": True,
        })
        self.connect_to_ui()
        if start:
            self._threads = [
                Thread(target=self._dispatch, name="controller-actions", daemon=True),
                Thread(target=self._poll, name="controller-xinput", daemon=True),
            ]
            for thread in self._threads:
                thread.start()

    def _state_attribute(self, title, value):
        return self.add_attribute(title, value, {"groups": ["controller_input_state"]})

    def _request(self, actor, *message):
        return self.connection.request_receive_timeout(2000, actor, *message)

    def _poll(self):
        previous = State()
        generation = sequence = 0
        try:
            while not self._stop.is_set():
                state = self.reader()
                if state.connected and not previous.connected:
                    generation += 1
                if state != previous:
                    sequence += 1
                    self._samples.put(Sample(generation, sequence, state))
                previous = state
                self._stop.wait(0.016)
        except Exception as error:
            self._logger.exception("Controller input polling stopped")
            self._samples.put(error)

    def _dispatch(self):
        while True:
            sample = self._samples.get()
            if sample is None or self._stop.is_set():
                return
            try:
                if isinstance(sample, Exception):
                    self.connected.set_value(False)
                    self.menu_held.set_value(False)
                    self.browse_visible.set_value(False)
                    self.status.set_value("Controller input failed: " + str(sample))
                    self._redraw()
                    return
                self.accept(sample)
            except Exception:
                self._logger.exception("Controller command failed for sample %s", sample)
                self.browse_visible.set_value(False)
                self.status.set_value("Controller command failed; see Log")
                self._redraw()

    def accept(self, sample):
        events = self.edges.accept(sample)
        if events is None:
            self._logger.warning("Controller rejected stale sample %s", sample)
            return
        for event in events:
            if self._stop.is_set():
                return
            self._logger.info("Controller Input: %s", json.dumps({
                "backend": "xinput1_4", "slot": 0,
                "generation": event.generation, "sequence": event.sequence,
                "edge": event.edge.value, "button": event.button, "buttons": event.buttons,
            }))
            if event.edge in (Edge.CONNECTED, Edge.DISCONNECTED):
                connected = event.edge == Edge.CONNECTED
                self.connected.set_value(connected)
                self.menu_held.set_value(False)
                self.browse_visible.set_value(False)
                self.status.set_value(
                    "Controller connected" if connected else "Controller disconnected")
                self._redraw()
            command = self.bindings.accept(event)
            if event.button == MENU:
                self.menu_held.set_value(self.bindings.menu_held)
                self._redraw()
            if command:
                self._logger.info("Controller Command: %s", json.dumps({
                    "action": command.action, "mode": command.mode,
                    "generation": command.generation, "sequence": command.sequence,
                }))
                self.execute(command)

    def execute(self, command):
        action = command.action
        if action == "select_mode":
            self.mode.set_value(command.mode)
            self.status.set_value("Mode: " + command.mode)
            self.browse_visible.set_value(False)
            if command.mode in ("playlists", "media"):
                self._browse(command.mode)
            else:
                self._redraw()
        elif action == "toggle_guide":
            self._guide = not self._guide
            self.guide.set_value(self._guide)
            self.status.set_value(
                "Controller guide shown" if self._guide else "Controller guide hidden")
            self._redraw()
        elif action == "toggle_playback":
            playing = self._request(self.events, play_atom())[0]
            self._request(self.events, play_atom(), not playing)
        elif action == "cycle_loop":
            playhead = self.current_playhead()
            modes = (LoopMode.LM_LOOP, LoopMode.LM_PLAY_ONCE, LoopMode.LM_PING_PONG)
            playhead.looping = modes[(modes.index(playhead.looping) + 1) % len(modes)]
        elif action == "toggle_mask":
            mask = self.connection.get_named_python_plugin_instance("Mask")
            mask.toggle_mask_cb(True, "controller_input")
        elif action in ("exposure_up", "exposure_down"):
            self._exposure(0.25 if action == "exposure_up" else -0.25)
        elif action in ("browse_previous", "browse_next"):
            self._browse(command.mode, -1 if action == "browse_previous" else 1)
        elif action == "back":
            self.browse_visible.set_value(False)
            self.status.set_value("Browse preview closed; source unchanged")
            self._redraw()
        elif action == "confirm":
            self.status.set_value("Source activation is not available yet; preview only")
            self._logger.warning("Controller Command: %s is not available yet", action)
            self._redraw()
        else:
            raise ValueError("Unknown controller action: " + action)

    def _exposure(self, delta):
        viewports = self._request(self.events, viewport_atom())[0]
        pipelines = []
        addresses = set()
        for viewport in viewports:
            pipeline = self._request(viewport, colour_pipeline_atom())[0]
            # Python actor wrappers have no value equality; use their CAF addresses.
            if pipeline and str(pipeline) not in addresses:
                addresses.add(str(pipeline))
                pipelines.append(pipeline)
        if not pipelines:
            raise RuntimeError("Controller exposure failed: no viewer colour pipelines")
        values = [
            self._request(pipeline, attribute_value_atom(), "Exposure (E)")[0].get()
            for pipeline in pipelines
        ]
        # Snapshot all values before any write; pipelines may synchronise their attributes.
        for pipeline, value in zip(pipelines, values):
            target = max(-10.0, min(10.0, value + delta))
            if not self._request(
                    pipeline, change_attribute_value_atom(), "Exposure (E)",
                    JsonStore(target), True)[0]:
                raise RuntimeError("Controller exposure update was rejected")

    def _browse(self, mode, step=0):
        session = self.connection.api.session
        session_id = str(session.uuid)
        if self._browse_context != session_id:
            self._browse_context = session_id
            self._browse_selection.clear()
        if mode == "playlists":
            entries = []
            for playlist in session.playlists:
                entries.append((str(playlist.uuid), playlist.name))
                for child in playlist.containers:
                    entries.append((str(child.uuid), playlist.name + " / " + child.name))
            context = (mode, session_id)
            viewed = session.viewed_container
            initial = str(viewed.uuid) if viewed else None
            title = "Playlists preview"
        elif mode == "media":
            # The viewer may have no container yet; fall back to the Media panel's container.
            container = session.viewed_container or session.inspected_container
            if container is None:
                context = (mode, None)
                entries = []
                initial = None
                title = "Media preview: no playlist open"
            else:
                context = (mode, str(container.uuid))
                entries = [(str(media.uuid), media.name) for media in container.media]
                selected = container.playhead_selection.selected_sources
                initial = str(selected[0].uuid) if selected else None
                title = "Media preview: " + container.name
        else:
            raise ValueError("Browsing is not supported in mode " + mode)
        identifiers = [entry[0] for entry in entries]
        previous = self._browse_selection.get(context, initial)
        if previous in identifiers:
            index = max(0, min(len(entries) - 1, identifiers.index(previous) + step))
        else:
            if context in self._browse_selection:
                self._logger.warning("Controller browse candidate was removed; refreshing preview")
            index = 0
        self.browse_title.set_value(title)
        if entries:
            self._browse_selection[context] = identifiers[index]
            start = max(0, min(index - 3, len(entries) - 7))
            self.browse_rows.set_value([name for _, name in entries[start:start + 7]])
            self.browse_index.set_value(index - start)
            self.status.set_value(
                "Preview %s of %s; source unchanged" % (index + 1, len(entries)))
        else:
            self._browse_selection.pop(context, None)
            self.browse_rows.set_value([])
            self.browse_index.set_value(-1)
            self.status.set_value("No items to browse; source unchanged")
            self._logger.warning("Controller browse: %s is empty", title)
        self.browse_visible.set_value(True)
        self._redraw()

    def _redraw(self):
        self.connection.send(self.events, redraw_viewport_atom())

    def take_log_records(self):
        return self._log_handler.take_records()

    def cleanup(self):
        self._stop.set()
        self._samples.put(None)
        for thread in self._threads:
            thread.join()
        self._threads.clear()
        self.cleanup_message_handler()
        self._logger.removeHandler(self._log_handler)
        self._log_handler.close()
