# SPDX-License-Identifier: Apache-2.0
"""Optional probe loaded as a Python plugin in a disposable GUI session.

Set CONTROLLER_PROBE_RESULT to an output JSON path and load this module's
create_plugin_instance via XSTUDIO_PYTHON_PLUGIN_PATH. Never use a review session:
the probe stops physical input, changes viewer state, and creates test media.
Optionally set CONTROLLER_PROBE_OVERLAY_IMAGE to capture the real overlay and
verify the GUI Log model; launch with its parent directory as the working directory.
"""
import json
import os
from pathlib import Path
import struct
import threading
import time
import traceback
import zlib


class RuntimeProbe:
    name = "Controller runtime probe"

    def __init__(self, connection):
        from xstudio.core import Uuid
        self.uuid = Uuid("bc744ea3-1cf4-4b3c-92ea-188f481c53e6")
        self.connection = connection
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def cleanup(self):
        self.stop.set()
        self.thread.join()

    def run(self):
        result = Path(os.environ["CONTROLLER_PROBE_RESULT"])
        checks = []
        try:
            deadline = time.monotonic() + 45
            plugin = None
            while not self.stop.wait(0.1):
                plugins = list(self.connection.plugins.values())
                plugin = next((p for p in plugins if p.name == "Controller Input"), None)
                if plugin and self.connection.api.app.viewport_names():
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("Python controller and GUI viewport did not start")
            if self.stop.is_set():
                return

            from controller_input.bindings import Bindings, Command
            from controller_input.input import (
                A, RB, X, Y, MENU, VIEW, DPAD_DOWN, DPAD_RIGHT, DPAD_UP, Edges, Sample, State)
            from xstudio.core import key_playhead_index_atom
            from xstudio.core import LoopMode, viewport_atom, colour_pipeline_atom, attribute_value_atom

            assert all(thread.is_alive() for thread in plugin._threads)
            assert isinstance(plugin.reader(), State)
            checks.append("automatic Python plugin discovery")
            plugin._stop.set()
            plugin._samples.put(None)
            for thread in plugin._threads:
                thread.join()
            plugin._threads.clear()
            plugin._stop.clear()
            plugin.edges = Edges()
            plugin.bindings = Bindings()
            sequence = 0

            def sample(buttons=0, connected=True):
                nonlocal sequence
                sequence += 1
                plugin.accept(Sample(1, sequence, State(connected, buttons)))

            def press(button):
                sample(button)
                sample()

            def with_menu(buttons):
                sample(MENU)
                sample(MENU | buttons)
                sample(MENU)

            overlay = plugin.get_attribute("Controller Input Overlay")
            assert overlay.value() is True, overlay.as_json()
            assert overlay.role_data("type") == "OnOffToggle", overlay.as_json()
            assert "!view.isQuickview" in overlay.role_data("qml_code")
            assert "viewport_overlay_plugins" in overlay.role_data("groups")
            checks.append("real boolean overlay gate and QML role")
            sample()
            assert plugin.connected.value() is True
            assert plugin.guide.value() is False
            assert plugin.mode.value() == "viewer"
            assert plugin.menu_held.value() is False
            sample(MENU)
            assert plugin.menu_held.value() is True
            sample(MENU | DPAD_RIGHT)
            assert plugin.browse_visible.value() is True
            sample()
            assert plugin.browse_visible.value() is False
            assert plugin.menu_held.value() is False
            assert plugin.mode.value() == "playlists"
            assert plugin.guide.value() is False
            press(VIEW)
            assert plugin.guide.value() is True
            press(VIEW)
            assert plugin.guide.value() is False
            assert plugin.mode.value() == "playlists"
            checks.append("real UI attributes, mode changes and independent guide")

            plugin.bindings.mode = "viewer"
            plugin.execute(Command("select_mode", "viewer", 1, sequence))
            playhead = plugin.current_playhead()
            playhead.looping = LoopMode.LM_LOOP
            for expected in (LoopMode.LM_PLAY_ONCE, LoopMode.LM_PING_PONG, LoopMode.LM_LOOP):
                press(Y)
                assert playhead.looping == expected
            checks.append("all loop modes through real playhead API")

            mask = self.connection.get_named_python_plugin_instance("Mask")
            before = mask.toggle_attr.value()
            press(A)
            assert mask.toggle_attr.value() != before
            press(A)
            assert mask.toggle_attr.value() == before
            checks.append("mask callback and actual mask attribute")

            viewports = plugin._request(plugin.events, viewport_atom())[0]
            pipeline = plugin._request(viewports[0], colour_pipeline_atom())[0]
            exposure = lambda: plugin._request(pipeline, attribute_value_atom(), "Exposure (E)")[0].get()
            before = exposure()
            plugin.execute(Command("exposure_up", "viewer", 1, sequence))
            assert abs(exposure() - min(10.0, before + 0.25)) < 0.0001
            plugin.execute(Command("exposure_down", "viewer", 1, sequence))
            assert abs(exposure() - before) < 0.0001
            checks.append("real viewer relative exposure")

            media_path = result.with_suffix(".png")

            def chunk(kind, data):
                return struct.pack(">I", len(data)) + kind + data + struct.pack(
                    ">I", zlib.crc32(kind + data))

            media_path.write_bytes(
                b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress((b"\0" + bytes([32, 64, 128]) * 16) * 16))
                + chunk(b"IEND", b""))
            playlist = self.connection.api.session.create_playlist("Controller probe")[1]
            media = playlist.add_media(str(media_path))
            playlist.playhead_selection.set_selection([media.uuid])
            self.connection.api.session.viewed_container = playlist
            deadline = time.monotonic() + 10
            while str(plugin.current_playhead().remote) != str(playlist.playhead.remote):
                if time.monotonic() > deadline:
                    raise TimeoutError("Probe playlist did not activate")
                time.sleep(0.05)
            playhead = plugin.current_playhead()
            playhead.looping = LoopMode.LM_LOOP
            playhead.playing = False
            press(X)
            assert playhead.playing is True
            press(X)
            assert playhead.playing is False
            session = self.connection.api.session
            playlist.create_timeline("Preview timeline")
            other_playlist = session.create_playlist("Other playlist")[1]
            other_media = playlist.add_media(str(media_path))
            playlist.playhead_selection.set_selection([media.uuid])
            viewed_id = str(session.viewed_container.uuid)
            selected_ids = [str(item.uuid) for item in playlist.playhead_selection.selected_sources]
            plugin.bindings.mode = "viewer"
            with_menu(DPAD_RIGHT)
            sample()
            assert plugin.mode.value() == "playlists"
            rows = plugin.browse_rows.value()
            assert "Controller probe / Preview timeline" in rows, rows
            assert "Other playlist" in rows, rows
            press(DPAD_DOWN)
            assert plugin.browse_index.value() == 0
            assert plugin.browse_visible.value() is False
            sample(MENU)
            assert plugin.browse_visible.value() is True
            with_menu(DPAD_DOWN)
            assert "Preview timeline" in plugin.browse_rows.value()[plugin.browse_index.value()]
            assert str(session.viewed_container.uuid) == viewed_id
            assert playhead.playing is False
            with_menu(A)
            timeline = session.viewed_container
            assert timeline.name == "Preview timeline", timeline.name
            assert str(session.inspected_container.uuid) == str(timeline.uuid)
            assert str(plugin.current_playhead().remote) == str(timeline.playhead.remote)
            assert timeline.playhead.attrs_by_name_["Pinned Source Mode"].value() is True
            assert plugin.current_playhead().playing is False
            assert plugin.browse_marked.value()[plugin.browse_index.value()] is True
            checks.append("A views highlighted timeline pinned, panel follows, paused kept")
            plugin.current_playhead().playing = True
            for _ in range(len(plugin.browse_rows.value())):
                with_menu(DPAD_UP)
            assert plugin.browse_rows.value()[plugin.browse_index.value()] == "Controller probe"
            with_menu(A)
            assert str(session.viewed_container.uuid) == viewed_id
            assert str(plugin.current_playhead().remote) == str(playlist.playhead.remote)
            playhead = plugin.current_playhead()
            assert playhead.playing is True
            playhead.playing = False
            checks.append("A returns to playlist and keeps playing state")

            with_menu(DPAD_RIGHT)
            assert plugin.mode.value() == "media"
            assert len(plugin.browse_rows.value()) == 2
            selection = lambda: [str(item.uuid) for item in playlist.playhead_selection.selected_sources]
            with_menu(DPAD_DOWN)
            with_menu(A)
            assert selection() == [str(other_media.uuid)], selection()
            assert plugin.browse_marked.value() == [False, True]
            with_menu(DPAD_UP)
            sample(MENU | RB)
            sample(MENU | RB | A)
            sample(MENU | RB)
            sample(MENU)
            assert selection() == [str(media.uuid), str(other_media.uuid)], selection()
            assert plugin.browse_marked.value() == [True, True]
            assert plugin.status.value() == "2 media selected"
            sample()
            assert plugin.browse_visible.value() is False
            press(A)
            assert selection() == [str(media.uuid), str(other_media.uuid)], selection()
            assert playhead.playing is False
            checks.append("Menu-gated media A replaces and RB+A toggles real selection")

            with_menu(DPAD_RIGHT)
            with_menu(DPAD_RIGHT)
            sample()
            assert plugin.mode.value() == "viewer"
            playhead = plugin.current_playhead()
            playhead.compare_mode = "A/B"

            def key_index():
                return plugin._request(playhead.remote, key_playhead_index_atom())[0]

            def wait_key(expected):
                deadline = time.monotonic() + 5
                while key_index() != expected:
                    if time.monotonic() > deadline:
                        raise TimeoutError("Displayed item index %s != %s" % (key_index(), expected))
                    time.sleep(0.05)

            time.sleep(0.5)
            start = key_index()
            assert start in (0, 1), start
            press(DPAD_DOWN)
            wait_key(1 - start)
            press(DPAD_DOWN)
            wait_key(start)
            press(DPAD_UP)
            wait_key(1 - start)
            assert selection() == [str(media.uuid), str(other_media.uuid)], selection()
            checks.append("viewer D-pad up/down cycles displayed item of real multi-selection")
            sample(connected=False)
            assert playhead.playing is False
            assert plugin.connected.value() is False
            checks.append("playback toggles and safe disconnect")
            image_path = os.environ.get("CONTROLLER_PROBE_OVERLAY_IMAGE")
            if image_path:
                plugin.connected.set_value(True)
                plugin.execute(Command("select_mode", "viewer", 1, sequence))
                plugin.execute(Command("toggle_guide", "viewer", 1, sequence))
                hud_folder = Path(__file__).resolve().parents[3] / "ui" / "qml" / "xstudio" / "application" / "panels" / "viewport" / "hud"
                item = plugin.create_qml_item("""
                    import QtQuick
                    import QtQuick.Window
                    import "%s"
                    Window {
                        width: 1280
                        height: 720
                        visible: true
                        color: "#202020"
                        property QtObject view: QtObject { property bool isQuickview: false }
                        property var hud_plugins_display_data: ({})
                        property int imageIndex: 0
                        XsViewportOverlays { id: overlays; anchors.fill: parent }
                        Timer {
                            property int phase: 0
                            interval: 100
                            repeat: true
                            running: true
                            function hasGuide(item) {
                                if (item.visible && item.text !== undefined &&
                                    item.text.indexOf("Controller mode: viewer") === 0 &&
                                    item.text.indexOf("Menu + D-pad left / right: change mode") !== -1)
                                    return true
                                for (var i = 0; i < item.children.length; ++i)
                                    if (hasGuide(item.children[i])) return true
                                return false
                            }
                            function hasPreview(item) {
                                if (item.visible && item.text !== undefined &&
                                    item.text === "Media: Controller probe")
                                    return true
                                for (var i = 0; i < item.children.length; ++i)
                                    if (hasPreview(item.children[i])) return true
                                return false
                            }
                            onTriggered: {
                                if (phase === 0 && hasGuide(overlays)) {
                                    phase = 1
                                    overlays.grabToImage(function(result) {
                                        result.saveToFile(%s)
                                    })
                                    logger.saveLogToFile(%s)
                                } else if (phase === 1 && hasPreview(overlays)) {
                                    stop()
                                    overlays.grabToImage(function(result) {
                                        result.saveToFile(%s)
                                    })
                                }
                            }
                        }
                    }
                """ % (
                    hud_folder.as_uri(), json.dumps(image_path),
                    json.dumps(Path(image_path).with_suffix(".log").name),
                    json.dumps(str(Path(image_path).with_name("controller-browse-preview.png")))))
                deadline = time.monotonic() + 15
                while not Path(image_path).exists():
                    if time.monotonic() > deadline:
                        raise TimeoutError("Real UI-model overlay did not render mode and guide")
                    time.sleep(0.1)
                plugin.execute(Command("toggle_guide", "viewer", 1, sequence))
                plugin.menu_held.set_value(True)
                plugin.execute(Command("select_mode", "media", 1, sequence))
                preview_image = Path(image_path).with_name("controller-browse-preview.png")
                while not preview_image.exists():
                    if time.monotonic() > deadline:
                        raise TimeoutError("Real UI-model browse preview did not render")
                    time.sleep(0.1)
                plugin.delete_qml_item(item)
                checks.append("real UI models and XsHudItem render mode and button guide")
                checks.append("real UI models render media browse preview with guide closed")
                log_text = Path(image_path).with_suffix(".log").read_text(encoding="utf-8")
                for prefix in ("Controller Input: ", "Controller Command: "):
                    assert prefix in log_text, "Missing Log window records: " + prefix
                checks.append("Log window model contains input and commands")
            result.write_text(json.dumps({"passed": checks}, indent=2), encoding="utf-8")
        except Exception:
            result.write_text(json.dumps({
                "passed": checks, "error": traceback.format_exc(),
            }, indent=2), encoding="utf-8")
            traceback.print_exc()


def create_plugin_instance(connection):
    return RuntimeProbe(connection)
