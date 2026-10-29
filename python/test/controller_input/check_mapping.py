# SPDX-License-Identifier: Apache-2.0
"""Exercise panel behavior with the callback and styled-widget boundaries faked."""
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[3]
source = (
    ROOT / "src" / "plugin" / "python_plugins" / "controller_input" / "mapping.qml"
).read_text(encoding="utf-8")
source = "\n".join(line for line in source.splitlines() if not line.startswith("import "))
source = source.replace("XsStyleSheet.", "testStyle.")
test = """
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtTest

Item {
    width: 640
    height: 640
    QtObject {
        id: testStyle
        property color panelBgColor: "#333333"
    }
    component XsLabel: Label {}
    component XsComboBox: ComboBox {}
    component XsPrimaryButton: Button {}
    QtObject {
        id: dialogHelpers
        property var answer: "Cancel"
        property string presetName: "Review"
        property var filePath: "file:///C:/test/preset.json"
        property string lastTitle: ""
        function multiChoiceDialog(callback, title, body, choices) {
            lastTitle = title
            callback(answer)
        }
        function textInputDialog(callback, title, body, initial, choices) {
            lastTitle = title
            callback(presetName, answer)
        }
        function showFileDialog(callback, folder, title, suffix, filters, existing, multiple) {
            lastTitle = title
            callback(filePath)
        }
    }
    QtObject {
        id: helpers
        property bool fail: false
        property var calls: []
        property var state: ({
            revision: 0, dirty: false, connected: true, active_mode: "common",
            active_layer: "normal", layers: ["normal", "shifted"], shift: "lt",
            shift_buttons: ["lt", "rb", "b"],
            can_undo: false, can_redo: false,
            selected_preset: "Factory", preset_warning: "", preset_folder: "file:///C:/test",
            presets: [{name: "Factory", available: true, error: ""},
                      {name: "Other", available: true, error: ""}],
            modes: ["common", "timeline", "media"], buttons: ["a", "b", "x", "lt", "rb", "rt"],
            functions: [
                {id: "toggle_playback", label: "Play / Pause", category: "Transport",
                    modes: ["common", "timeline", "media"]},
                {id: "toggle_mask", label: "Toggle Mask", category: "Image/display",
                    modes: ["common", "timeline", "media"]}
            ],
            bindings: [{mode: "timeline", button: "x", action: "toggle_playback", layer: "normal"}],
            effective: [{mode: "timeline", button: "x", action: "toggle_playback", source: "timeline", layer: "normal"}]
        })
        function python_callback(method, uuid, args) {
            calls.push([method, uuid, args])
            if (fail) return "simulated bridge failure"
            if (method === "mapping_snapshot") return JSON.parse(JSON.stringify(state))
            if (method === "preset_operation") {
                if (args[1] !== state.revision)
                    return {ok: false, error: "stale revision", state: state}
                if (args[0] === "save_as" && args[2].name === "Other" && !args[2].replace)
                    return {ok: false, code: "exists", error: "Already exists", state: state}
                if (args[0] === "load") {
                    state.selected_preset = args[2].name
                    state.dirty = false
                    state.can_undo = false
                    state.revision++
                } else if (args[0] === "save_as" || args[0] === "save") {
                    if (args[0] === "save_as") {
                        state.selected_preset = args[2].name
                        if (!args[2].replace)
                            state.presets.push({name: args[2].name, available: true, error: ""})
                    }
                    state.dirty = false
                    state.revision++
                }
                return {ok: true, state: JSON.parse(JSON.stringify(state))}
            }
            if (method === "edit_mapping") {
                if (args[1] !== state.revision)
                    return {ok: false, error: "stale revision", state: state}
                if (args[0] === "assign") {
                    state.bindings = args[4] === null ? [] :
                        [{mode: args[2], button: args[3], action: args[4], layer: args[5]}]
                    state.revision++
                    state.dirty = true
                    state.can_undo = true
                } else if (args[0] === "undo") {
                    state.bindings = [{mode: "timeline", button: "x", action: "toggle_playback", layer: "normal"}]
                    state.revision++
                    state.dirty = false
                    state.can_undo = false
                    state.can_redo = true
                } else if (args[0] === "shift") {
                    if (args[3] === "b" && args[6] !== true)
                        return {ok: false, code: "shift_conflict", error: "Disconnect B", state: state}
                    state.shift = args[3]
                    state.bindings = state.bindings.filter(function(b) { return b.button !== args[3] })
                    state.revision++
                }
                return {ok: true, state: JSON.parse(JSON.stringify(state))}
            }
            return "unknown method"
        }
    }
    PRODUCTION_PANEL
    TestCase {
        name: "ControllerMapping"
        when: windowShown
        function test_panel_edits_and_error_feedback() {
            tryVerify(function() { return panel.mappingState !== null })
            panel.editMode = "timeline"
            var saveButton = findChild(panel, "mappingSave")
            verify(!saveButton.enabled)
            var buttonB = findChild(panel, "mapping_b")
            verify(buttonB !== null)
            compare(buttonB.currentIndex, 0)
            buttonB.activated(2)
            compare(helpers.calls[helpers.calls.length - 1][0], "edit_mapping")
            compare(helpers.calls[helpers.calls.length - 1][2][3], "b")
            compare(panel.mappingState.revision, 1)
            verify(panel.mappingState.dirty)
            verify(!saveButton.enabled) // Factory remains read-only after edits.
            verify(findChild(panel, "mappingSaveAs").enabled)
            tryCompare(findChild(panel, "mapping_b"), "currentIndex", 2)
            tryCompare(findChild(panel, "mapping_x"), "currentIndex", 0)
            mouseClick(findChild(panel, "mappingUndo"))
            compare(panel.mappingState.dirty, false)
            tryCompare(findChild(panel, "mapping_x"), "currentIndex", 2)
            var modes = findChild(panel, "mappingMode")
            modes.activated(2)
            compare(panel.editMode, "media")
            compare(panel.choices().length, 4)
            compare(panel.choices()[0].label, "Inherit Common")
            compare(panel.choices()[1].label, "Unassigned")
            compare(panel.choices()[2].label, "Transport: Play / Pause")
            panel.editMode = "common"
            compare(panel.choices()[0].label, "Unassigned")
            compare(panel.choices().length, 3)
            panel.editMode = "media"
            helpers.state.effective = [
                {mode: "media", button: "x", action: "toggle_playback", source: "common", layer: "normal"},
                {mode: "media", button: "a", action: null, source: "disabled", layer: "normal"},
                {mode: "media", button: "b", action: null, source: "suppressed", layer: "normal"}]
            panel.refresh()
            compare(findChild(panel, "mapping_effective_x").text, "Inherited Common: Play / Pause")
            compare(findChild(panel, "mapping_effective_a").text,
                "Unassigned in this mode (Common not inherited)")
            verify(findChild(panel, "mapping_effective_b").text.indexOf("another button") !== -1)
            var modeButton = findChild(panel, "mapping_b")
            modeButton.activated(1)
            compare(helpers.calls[helpers.calls.length - 1][2][4], "disabled")
            tryCompare(findChild(panel, "mapping_b"), "currentIndex", 1)
            modeButton.activated(0)
            compare(helpers.calls[helpers.calls.length - 1][2][4], null)
            tryCompare(findChild(panel, "mapping_b"), "currentIndex", 0)
            helpers.state.dirty = true
            panel.refresh()
            dialogHelpers.answer = "Cancel"
            var beforeCalls = helpers.calls.length
            panel.loadPreset("Other")
            compare(helpers.calls.length, beforeCalls)
            compare(panel.mappingState.selected_preset, "Factory")
            dialogHelpers.answer = "Discard"
            panel.loadPreset("Other")
            compare(panel.mappingState.selected_preset, "Other")
            compare(panel.mappingState.dirty, false)
            verify(!saveButton.enabled)
            helpers.state.dirty = true
            panel.refresh()
            verify(saveButton.enabled)
            mouseClick(saveButton)
            compare(helpers.calls[helpers.calls.length - 1][2][0], "save")
            verify(!saveButton.enabled)
            dialogHelpers.answer = "Save"
            panel.saveAs(panel.mappingState.revision, null)
            compare(panel.mappingState.selected_preset, "Review")
            dialogHelpers.presetName = "Other"
            dialogHelpers.answer = "Replace"
            panel.preset("save_as", {name: "Other"}, panel.mappingState.revision)
            tryCompare(panel, "errorText", "")
            compare(panel.mappingState.selected_preset, "Other")
            helpers.state.dirty = true
            panel.refresh()
            panel.presetFile("export")
            compare(panel.mappingState.dirty, true)
            compare(helpers.calls[helpers.calls.length - 1][2][0], "export")
            panel.presetFile("import")
            compare(panel.mappingState.selected_preset, "Other")
            helpers.state.selected_preset = "Factory"
            helpers.state.dirty = true
            panel.refresh()
            dialogHelpers.answer = "Save"
            dialogHelpers.presetName = "Saved Before Switch"
            panel.loadPreset("Other")
            tryCompare(panel, "errorText", "")
            tryVerify(function() { return panel.mappingState.selected_preset === "Other" })
            var loadCall = helpers.calls[helpers.calls.length - 1]
            compare(loadCall[0], "preset_operation")
            compare(loadCall[2][0], "load")
            compare(loadCall[2][2].save_name, "Saved Before Switch")
            verify(saveButton !== null)
            verify(findChild(panel, "mappingSaveAs") !== null)
            verify(findChild(panel, "mappingImport") !== null)
            verify(findChild(panel, "mappingExport") !== null)
            verify(!findChild(panel, "mapping_lt").enabled)
            findChild(panel, "mappingLayer").activated(1)
            compare(panel.editLayer, "shifted")
            compare(panel.choices()[0].label, "Inherit Normal / Common")
            findChild(panel, "mapping_b").activated(2)
            compare(helpers.calls[helpers.calls.length - 1][2][5], "shifted")
            tryCompare(findChild(panel, "mapping_b"), "currentIndex", 2)
            dialogHelpers.answer = "Cancel"
            findChild(panel, "mappingShift").activated(2)
            tryCompare(dialogHelpers, "lastTitle", "Change Shift input?")
            compare(panel.mappingState.shift, "lt")
            dialogHelpers.answer = "Change Shift"
            findChild(panel, "mappingShift").activated(2)
            tryCompare(panel, "errorText", "")
            compare(panel.mappingState.shift, "b")
            verify(!findChild(panel, "mapping_b").enabled)
            verify(findChild(panel, "mapping_lt").enabled)
            helpers.fail = true
            panel.refresh()
            verify(panel.errorText.indexOf("simulated bridge failure") !== -1)
            panel.edit("assign", "b", "toggle_playback")
            verify(panel.errorText.indexOf("edit failed") !== -1)
        }
    }
}
""".replace("PRODUCTION_PANEL", source)

with tempfile.TemporaryDirectory(prefix="xstudio-controller-mapping-") as folder:
    path = Path(folder) / "tst_mapping.qml"
    path.write_text(test, encoding="utf-8")
    output = Path(folder) / "results.txt"
    result = subprocess.run(
        [sys.argv[1], "-platform", "offscreen", "-input", str(path),
         "-o", str(output) + ",txt"],
        timeout=30)
    if output.exists():
        print(output.read_text(encoding="utf-8"))
    result.check_returncode()
