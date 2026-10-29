# SPDX-License-Identifier: Apache-2.0
import json
import logging
import os
from pathlib import Path
from queue import Empty, Queue
import re
from threading import Event as StopEvent, RLock, Thread
import time
from urllib.parse import unquote, urlsplit

from xstudio.core import (
    JsonStore, LogLevel, LoopMode, attribute_value_atom, change_attribute_value_atom,
    Uuid, colour_pipeline_atom, create_playhead_atom, hotkey_event_atom, log_atom, play_atom, redraw_viewport_atom,
    viewport_atom, viewport_playhead_atom,
)
from xstudio.plugin import PluginBase

from .bindings import BROWSE_MODES, DEFAULT_MODE, Bindings
from .input import Edge, Edges, Sample, State, XInputReader
from .mapping import BUTTONS, CATEGORIES, FUNCTIONS, LAYERS, SCOPES, SHIFT_BUTTONS
from .presets import PresetStore


LOGGER = logging.getLogger(__name__)
LEGACY_UUID = "6d11e948-b80d-4409-9c11-d6b4eb30ad13"
COMPARE_LAYOUTS = ("Off", "A/B", "String", "Grid", "Horizontal", "Vertical", "Wipe")


def _display_name(name):
    # Media added by path is named after the full path; show the file name like the Media panel.
    return re.split(r"[\\/]", name.rstrip("\\/"))[-1] or name


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
    def __init__(self, connection, reader=None, start=True, preset_path=None):
        for detail in connection.api.plugin_manager.plugin_detail:
            if str(detail.uuid()) == LEGACY_UUID:
                raise RuntimeError(
                    "Remove the legacy controller_input.dll and restart xSTUDIO "
                    "before loading the Python controller; dual input is unsafe")
        self.reader = XInputReader() if reader is None else reader
        super().__init__(connection, "Controller Input")
        self.edges = Edges()
        self.bindings = Bindings()
        if preset_path is None:
            preset_path = (
                Path.home() / ".config" / "DNEG" / "xstudio" / "preferences"
                / "controller_input" / "button-presets.json")
        self.presets = PresetStore(preset_path)
        self.bindings.load_configuration(self.presets.configuration)
        self.bindings.revision = 0
        self._mapping_lock = RLock()
        self._stop = StopEvent()
        self._samples = Queue()
        self._threads = []
        self._guide = False
        self._browse_selection = {}
        self._checked = {}
        self._browse_context = None
        self.events = connection.api.app.global_playhead_events.remote
        self.status = self._state_attribute("Controller Status", "Controller disconnected")
        self.connected = self._state_attribute("Controller Connected", False)
        self.mode = self._state_attribute("Controller Mode", DEFAULT_MODE)
        self.layer = self._state_attribute("Controller Layer", "normal")
        self.shift_button = self._state_attribute("Controller Shift Input", self.bindings.configuration.shift.upper())
        self.guide = self._state_attribute("Controller Guide", False)
        self.menu_open = self._state_attribute("Controller Menu Open", False)
        self.browse_visible = self._state_attribute("Controller Browse Visible", False)
        self.browse_title = self._state_attribute("Controller Browse Title", "")
        self.browse_rows = self._state_attribute("Controller Browse Rows", [])
        self.browse_index = self._state_attribute("Controller Browse Index", -1)
        self.browse_marked = self._state_attribute("Controller Browse Marked", [])
        self.button_guide = self._state_attribute("Controller Button Guide", self._button_guide())
        self._published_layer = self.bindings.layer
        self._published_mode = self.bindings.mode
        self.add_attribute("Controller Input Overlay", True, {
            "groups": ["viewport_overlay_plugins"],
        }).set_role_data(
            "qml_code", Path(__file__).with_name("overlay.qml").read_text(encoding="utf-8"))
        self._logger = LOGGER.getChild(str(id(self)))
        self._logger.setLevel(logging.INFO)
        self._log_handler = StudioLogHandler(connection)
        self._logger.addHandler(self._log_handler)
        if self.presets.warning:
            self._logger.warning("Controller presets: %s", self.presets.warning)
            self.status.set_value(self.presets.warning)
        self.add_attribute("Controller Log Bridge", False, {
            "groups": ["dynamic qml items"],
            "qml_code": Path(__file__).with_name("log.qml").read_text(encoding="utf-8"),
            "attr_enabled": True,
        })
        self.connect_to_ui()
        self.register_ui_panel_qml(
            "Controller Mapping",
            Path(__file__).with_name("mapping.qml").read_text(encoding="utf-8").replace(
                "__CONTROLLER_UUID__", str(self.uuid)),
            20.0)
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
                    with self._mapping_lock:
                        self.bindings.reset_input()
                        self._update_mapping_state()
                    self.menu_open.set_value(False)
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
        with self._mapping_lock:
            self._accept(sample)

    def _accept(self, sample):
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
                self.menu_open.set_value(False)
                self.browse_visible.set_value(False)
                self.status.set_value(
                    "Controller connected" if connected else "Controller disconnected")
                self._redraw()
            was_open = self.bindings.menu_open
            command = self.bindings.accept(event)
            if (self._published_layer != self.bindings.layer
                    or self._published_mode != self.bindings.mode):
                self._update_mapping_state()
                self._redraw()
            if was_open != self.bindings.menu_open:
                opened = self.bindings.menu_open
                self.menu_open.set_value(opened)
                if opened and self.bindings.mode in BROWSE_MODES:
                    self._browse(self.bindings.mode)
                else:
                    self.browse_visible.set_value(False)
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
            self.button_guide.set_value(self._button_guide())
            self.status.set_value("Mode: " + command.mode)
            self.browse_visible.set_value(False)
            if command.mode in BROWSE_MODES:
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
        elif action == "cycle_compare":
            self._cycle_compare()
        elif action in ("previous_media", "next_media"):
            self._step_media(action == "next_media")
        elif action in ("confirm", "toggle_select"):
            self._activate(command.mode, action == "toggle_select")
        elif action == "clear_selection":
            context, _, _, _, _ = self._candidates("media")
            self._checked.pop(context, None)
            self._browse("media", status="Checked media cleared; viewer unchanged")
        else:
            raise ValueError("Unknown controller action: " + action)

    def _cycle_compare(self):
        # xstudio exposes no list of registered layouts, so try each known layout in turn
        # and keep the first one the playhead actually accepts.
        playhead = self.current_playhead()
        current = playhead.compare_mode
        start = COMPARE_LAYOUTS.index(current) if current in COMPARE_LAYOUTS else -1
        for offset in range(1, len(COMPARE_LAYOUTS) + 1):
            layout = COMPARE_LAYOUTS[(start + offset) % len(COMPARE_LAYOUTS)]
            playhead.compare_mode = layout
            if playhead.compare_mode == layout:
                self.status.set_value("Compare: " + layout)
                self._redraw()
                return
        playhead.compare_mode = current
        raise RuntimeError("Controller compare failed: no layout was accepted")

    def _step_media(self, forwards):
        # Reuse the playhead's Up/Down hotkeys: cycle the multi-selection in compare
        # modes, step clips in a timeline/string, else step the playlist selection.
        hotkey = Uuid()
        hotkey.generate_from_name(
            ("Jump to next media/clip" if forwards else "Jump to previous media/clip")
            + "Playback")
        self.connection.send(
            self.current_playhead().remote, hotkey_event_atom(), hotkey, True,
            "controller_input", "", False)

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

    def _candidates(self, mode):
        session = self.connection.api.session
        session_id = str(session.uuid)
        if self._browse_context != session_id:
            self._browse_context = session_id
            self._browse_selection.clear()
            self._checked.clear()
        if mode == "playlists":
            items = []
            for playlist in session.playlists:
                items.append((str(playlist.uuid), playlist.name, playlist))
                for child in playlist.containers:
                    items.append((str(child.uuid), playlist.name + " / " + child.name, child))
            viewed = session.viewed_container
            active = [str(viewed.uuid)] if viewed else []
            return (mode, session_id), items, active, "Playlists", None
        if mode == "media":
            # The viewer may have no container yet; fall back to the Media panel's container.
            container = session.viewed_container or session.inspected_container
            if container is None:
                return (mode, None), [], [], "Media: no playlist open", None
            items = [(str(media.uuid), _display_name(media.name), media) for media in container.media]
            active = [str(media.uuid) for media in container.playhead_selection.selected_sources]
            return (mode, str(container.uuid)), items, active, "Media: " + container.name, container
        raise ValueError("Browsing is not supported in mode " + mode)

    def _browse(self, mode, step=0, status=None):
        context, items, active, title, _ = self._candidates(mode)
        identifiers = [item[0] for item in items]
        previous = self._browse_selection.get(context, active[0] if active else None)
        if mode == "media":
            checked = self._checked.get(context, set())
            removed = checked - set(identifiers)
            if removed:
                self._logger.warning("Controller checked media were removed; refreshing checks")
            self._checked[context] = checked & set(identifiers)
            active = self._checked[context]
        if previous in identifiers:
            index = max(0, min(len(items) - 1, identifiers.index(previous) + step))
        else:
            if context in self._browse_selection:
                self._logger.warning("Controller browse candidate was removed; refreshing list")
            index = 0
        self.browse_title.set_value(title)
        if items:
            self._browse_selection[context] = identifiers[index]
            start = max(0, min(index - 3, len(items) - 7))
            window = items[start:start + 7]
            self.browse_rows.set_value([item[1] for item in window])
            self.browse_marked.set_value([item[0] in active for item in window])
            self.browse_index.set_value(index - start)
            self.status.set_value(status or "Item %s of %s" % (index + 1, len(items)))
        else:
            self._browse_selection.pop(context, None)
            self.browse_rows.set_value([])
            self.browse_marked.set_value([])
            self.browse_index.set_value(-1)
            self.status.set_value(status or "No items to browse")
            self._logger.warning("Controller browse: %s is empty", title)
        self.browse_visible.set_value(True)
        self._redraw()

    def _activate(self, mode, toggle=False):
        context, items, active, _, container = self._candidates(mode)
        identifiers = [item[0] for item in items]
        target = self._browse_selection.get(context)
        if target not in identifiers:
            self._logger.warning("Controller activation: highlighted item is no longer available")
            self._browse(mode, status="Highlighted item is no longer available; nothing changed")
            return
        name, item = items[identifiers.index(target)][1:]
        if toggle:
            if mode != "media":
                raise ValueError("Checkbox selection is only supported in Media")
            checked = self._checked.get(context, set()) & set(identifiers)
            self._checked[context] = checked ^ {target}
            self._browse(mode, status="%s media checked; A views checked media" % len(self._checked[context]))
            return
        session = self.connection.api.session
        playing = self._request(self.events, play_atom())[0]
        if mode == "playlists":
            playhead = self._show_container(session, item)
            if item.type == "Timeline":
                self._set_pinned(playhead, True)
            status = "Viewing " + name
        else:
            chosen = (self._checked.get(context, set()) & set(identifiers)) or {target}
            selection = [entry[2] for entry in items if entry[0] in chosen]
            container.playhead_selection.set_selection([media.uuid for media in selection])
            viewed = session.viewed_container
            if viewed is None or str(viewed.uuid) != str(container.uuid):
                playhead = self._show_container(session, container)
            else:
                playhead = self._request(container.remote, create_playhead_atom())[0].actor
            if container.type == "Timeline":
                # Like the Media panel: unpin so the timeline playhead plays the selected media.
                self._set_pinned(playhead, False)
            status = ("%s media selected" % len(selection)) if len(selection) > 1 else "Viewing " + name
        self._request(self.events, play_atom(), playing)
        self._logger.info("Controller activation: %s", status)
        self._browse(mode, status=status)

    def _show_container(self, session, container):
        session.inspected_container = container
        session.viewed_container = container
        playhead = self._request(container.remote, create_playhead_atom())[0].actor
        deadline = time.monotonic() + 3.0
        while str(self._request(self.events, viewport_playhead_atom())[0]) != str(playhead):
            if time.monotonic() > deadline:
                raise RuntimeError("Viewers did not switch to " + container.name)
            time.sleep(0.05)
        return playhead

    def _set_pinned(self, playhead, value):
        from xstudio.api.session.playhead import Playhead
        Playhead(self.connection, playhead).attrs_by_name_["Pinned Source Mode"].set_value(value)

    def _redraw(self):
        self.connection.send(self.events, redraw_viewport_atom())

    def take_log_records(self):
        return self._log_handler.take_records()

    def _button_guide(self):
        mode = self.bindings.mode
        return "\n".join(
            button.upper() + ": " + FUNCTIONS[action][0]
            for button in BUTTONS
            for action in (self.bindings.configuration.action(mode, button, self.bindings.layer),)
            if action is not None)

    def _update_mapping_state(self):
        self._published_layer = self.bindings.layer
        self._published_mode = self.bindings.mode
        self.layer.set_value(self._published_layer)
        self.mode.set_value(self._published_mode)
        self.shift_button.set_value(self.bindings.configuration.shift.upper())
        self.button_guide.set_value(self._button_guide())

    def mapping_snapshot(self):
        with self._mapping_lock:
            return {
                "revision": self.bindings.revision,
                "dirty": self.bindings.dirty,
                "can_undo": self.bindings.can_undo,
                "can_redo": self.bindings.can_redo,
                "active_mode": self.bindings.mode,
                "active_layer": self.bindings.layer,
                "shift": self.bindings.configuration.shift,
                "shift_buttons": list(SHIFT_BUTTONS),
                "layers": list(LAYERS),
                "connected": self.edges.state.connected,
                "menu_open": self.bindings.menu_open,
                "selected_preset": self.presets.selected,
                "presets": self.presets.entries(),
                "preset_warning": self.presets.warning,
                "preset_folder": self.presets.path.parent.as_uri(),
                "modes": list(SCOPES),
                "buttons": list(BUTTONS),
                "functions": [
                    {"id": action, "label": label,
                     "modes": (["common", *modes] if tuple(modes) == tuple(SCOPES[1:]) else list(modes)),
                     "category": CATEGORIES[action]}
                    for action, (label, modes) in FUNCTIONS.items()
                ],
                "bindings": [
                    {"mode": binding.mode, "button": binding.button, "action": binding.action,
                     "layer": binding.layer}
                    for binding in self.bindings.configuration.bindings
                ],
                "effective": [
                    {"mode": mode, "button": button, "layer": layer,
                     "action": action, "source": source}
                    for mode in SCOPES for button in BUTTONS for layer in LAYERS
                    for action, source in (
                        self.bindings.configuration.effective(mode, button, layer),)
                ],
            }

    def edit_mapping(self, operation, revision, mode=None, button=None, action=None,
                     layer="normal", confirmed=False):
        with self._mapping_lock:
            try:
                if self._stop.is_set():
                    raise ValueError("Controller plugin is stopping")
                self.bindings.check_revision(revision)
                if operation == "shift":
                    if type(confirmed) is not bool:
                        raise ValueError("Invalid Shift confirmation")
                    self.bindings.configuration.with_shift(button)
                    conflicts = [
                        b.mode + " / " + b.layer + ": " + FUNCTIONS[b.action][0]
                        if b.action in FUNCTIONS else b.mode + " / " + b.layer + ": Unassigned"
                        for b in self.bindings.configuration.bindings if b.button == button]
                    if conflicts and not confirmed:
                        return {"ok": False, "code": "shift_conflict",
                                "error": "Changing Shift disconnects:\n" + "\n".join(conflicts),
                                "state": self.mapping_snapshot()}
                self.bindings.edit(operation, revision, mode, button, action, layer)
            except ValueError as error:
                self._logger.warning("Controller mapping edit rejected: %s", error)
                self.status.set_value("Controller mapping edit rejected: " + str(error))
                return {"ok": False, "error": str(error), "state": self.mapping_snapshot()}
            self._update_mapping_state()
            self._logger.info("Controller mapping revision %s", self.bindings.revision)
            self._redraw()
            return {"ok": True, "state": self.mapping_snapshot()}

    @staticmethod
    def _preset_file_path(value):
        if not isinstance(value, str) or not value:
            raise ValueError("Choose a preset file")
        if value.lower().startswith("file:"):
            url = urlsplit(value)
            if url.query or url.fragment:
                raise ValueError("Invalid preset file URL")
            path = unquote(url.path)
            if url.netloc and url.netloc != "localhost":
                path = "//" + url.netloc + path
            elif os.name == "nt" and re.match(r"^/[A-Za-z]:", path):
                path = path[1:]
            return Path(path)
        if "://" in value:
            raise ValueError("Preset files must be local files")
        return Path(value)

    def preset_operation(self, operation, revision, options):
        with self._mapping_lock:
            try:
                if self._stop.is_set():
                    raise ValueError("Controller plugin is stopping")
                self.bindings.check_revision(revision)
                if not isinstance(options, dict):
                    raise ValueError("Invalid preset operation options")
                replace = options.get("replace", False)
                if type(replace) is not bool:
                    raise ValueError("Invalid preset replacement confirmation")
                if operation in ("save", "save_as"):
                    name = self.presets.selected if operation == "save" else options.get("name")
                    self.presets.save(name, self.bindings.configuration,
                                      replace=operation == "save" or replace)
                    self.bindings.mark_saved()
                elif operation == "load":
                    name = options.get("name")
                    decision = options.get("decision", "cancel")
                    self.presets.get(name)
                    if self.bindings.dirty:
                        if decision == "cancel":
                            return {"ok": True, "state": self.mapping_snapshot()}
                        if decision == "save":
                            save_name = options.get("save_name", self.presets.selected)
                            self.presets.save(
                                save_name, self.bindings.configuration,
                                replace=save_name == self.presets.selected or replace,
                                select_after=name)
                        elif decision == "discard":
                            self.presets.select(name)
                        else:
                            raise ValueError("Choose Save, Discard, or Cancel")
                    else:
                        self.presets.select(name)
                    self.bindings.load_configuration(self.presets.configuration)
                elif operation == "import":
                    self.presets.import_file(
                        self._preset_file_path(options.get("path")), replace=replace)
                    self.bindings.set_baseline(self.presets.configuration)
                elif operation == "export":
                    self.presets.export_file(
                        self._preset_file_path(options.get("path")),
                        self.presets.selected, self.bindings.configuration)
                else:
                    raise ValueError("Unknown preset operation: " + str(operation))
            except (OSError, ValueError, UnicodeError) as error:
                self._logger.warning("Controller preset operation rejected: %s", error)
                self.status.set_value("Controller preset operation failed: " + str(error))
                return {
                    "ok": False, "error": str(error),
                    "code": "exists" if isinstance(error, FileExistsError) else "error",
                    "state": self.mapping_snapshot(),
                }
            self._update_mapping_state()
            self._logger.info("Controller preset %s: %s", operation, self.presets.selected)
            self._redraw()
            return {"ok": True, "state": self.mapping_snapshot()}

    def cleanup(self):
        self._stop.set()
        self._samples.put(None)
        for thread in self._threads:
            thread.join()
        self._threads.clear()
        self.cleanup_message_handler()
        self._logger.removeHandler(self._log_handler)
        self._log_handler.close()
