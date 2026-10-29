// SPDX-License-Identifier: Apache-2.0
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import xStudio 1.0

Rectangle {
    id: panel
    anchors.fill: parent
    color: XsStyleSheet.panelBgColor
    property var mappingState: null
    property string errorText: ""
    property string editMode: "common"
    property string editLayer: "normal"
    property string ownerUuid: "__CONTROLLER_UUID__"

    function callback(method, args) {
        return helpers.python_callback(method, ownerUuid, args)
    }

    function refresh() {
        var result = callback("mapping_snapshot", [])
        if (!result || typeof result !== "object" || result.revision === undefined) {
            errorText = "Controller mapping bridge failed: " + result
            return
        }
        if (JSON.stringify(result) !== JSON.stringify(mappingState))
            mappingState = result
    }

    function edit(operation, button, action, confirmed, revision) {
        if (!mappingState) return
        var targetRevision = revision === undefined ? mappingState.revision : revision
        var result = callback("edit_mapping",
            [operation, targetRevision, editMode, button, action, editLayer, confirmed === true])
        if (!result || typeof result !== "object" || result.ok === undefined) {
            errorText = "Controller mapping edit failed: " + result
            return
        }
        mappingState = result.state
        errorText = result.ok ? "" : result.error
        if (!result.ok && result.code === "shift_conflict") {
            Qt.callLater(function() {
                dialogHelpers.multiChoiceDialog(function(choice) {
                    if (choice === "Change Shift")
                        panel.edit("shift", button, null, true, targetRevision)
                }, "Change Shift input?", result.error,
                ["Cancel", "Change Shift"])
            })
        }
    }

    function preset(operation, options, revision) {
        var result = callback("preset_operation", [operation, revision, options])
        if (!result || typeof result !== "object" || result.ok === undefined) {
            errorText = "Controller preset operation failed: " + result
            return
        }
        mappingState = result.state
        errorText = result.ok ? "" : result.error
        if (!result.ok && result.code === "exists") {
            Qt.callLater(function() {
                dialogHelpers.multiChoiceDialog(function(choice) {
                    if (choice === "Replace") {
                        options.replace = true
                        panel.preset(operation, options, revision)
                    }
                }, "Replace preset?", result.error,
                ["Cancel", "Replace"])
            })
        }
    }

    function saveAs(revision, loadTarget) {
        dialogHelpers.textInputDialog(function(name, choice) {
            if (choice !== "Save") return
            var options = loadTarget === null ? {name: name} :
                {name: loadTarget, decision: "save", save_name: name}
            panel.preset(loadTarget === null ? "save_as" : "load", options, revision)
        }, "Save controller preset", "Name this controller configuration:",
        mappingState.selected_preset === "Factory" ? "My Controller" : mappingState.selected_preset,
        ["Cancel", "Save"])
    }

    function save() {
        if (!mappingState) return
        if (mappingState.selected_preset === "Factory")
            saveAs(mappingState.revision, null)
        else
            preset("save", {}, mappingState.revision)
    }

    function loadPreset(name) {
        if (!mappingState || name === mappingState.selected_preset) return
        var revision = mappingState.revision
        if (!mappingState.dirty) {
            preset("load", {name: name}, revision)
            return
        }
        var factory = mappingState.selected_preset === "Factory"
        dialogHelpers.multiChoiceDialog(function(choice) {
            if (choice === "Cancel") return
            if (choice === "Save" && factory) {
                Qt.callLater(function() { panel.saveAs(revision, name) })
            } else {
                panel.preset("load", {name: name,
                    decision: choice === "Save" ? "save" : "discard"}, revision)
            }
        }, "Unsaved controller mappings", "Save your changes before loading " + name + "?",
        ["Cancel", "Discard", "Save"])
    }

    function presetFile(operation) {
        if (!mappingState) return
        var revision = mappingState.revision
        dialogHelpers.showFileDialog(function(path) {
            if (path === false) return
            panel.preset(operation, {path: String(path)}, revision)
        }, mappingState.preset_folder,
        operation === "import" ? "Import controller preset" : "Export live controller mappings",
        "json", ["Controller preset (*.json)"], operation === "import", false)
    }

    function presetIndex() {
        if (!mappingState) return -1
        for (var i = 0; i < mappingState.presets.length; ++i)
            if (mappingState.presets[i].name === mappingState.selected_preset) return i
        return -1
    }

    function choices() {
        var result = [{id: "", label: editLayer === "shifted" ? "Inherit Normal / Common"
            : editMode === "common" ? "Unassigned" : "Inherit Common"}]
        if (editMode !== "common" || editLayer === "shifted")
            result.push({id: "disabled", label: "Unassigned"})
        if (mappingState) {
            for (var i = 0; i < mappingState.functions.length; ++i) {
                var entry = mappingState.functions[i]
                if (entry.modes.indexOf(editMode) !== -1)
                    result.push({id: entry.id, label: entry.category + ": " + entry.label})
            }
        }
        return result
    }

    function assignedIndex(button, entries) {
        if (!mappingState) return 0
        for (var i = 0; i < mappingState.bindings.length; ++i) {
            var binding = mappingState.bindings[i]
            if (binding.mode === editMode && binding.button === button
                    && binding.layer === editLayer) {
                for (var j = 0; j < entries.length; ++j)
                    if (entries[j].id === binding.action) return j
            }
        }
        return 0
    }

    function effectiveLabel(button) {
        if (!mappingState || !mappingState.effective) return ""
        for (var i = 0; i < mappingState.effective.length; ++i) {
            var entry = mappingState.effective[i]
            if (entry.mode !== editMode || entry.button !== button || entry.layer !== editLayer) continue
            if (entry.source === "shift") return "Dedicated held Shift input"
            if (entry.source === "disabled") return "Unassigned in this mode (Common not inherited)"
            if (entry.source === "suppressed") return "Common action assigned to another button in this mode"
            if (!entry.action) return "No action"
            for (var j = 0; j < mappingState.functions.length; ++j) {
                if (mappingState.functions[j].id === entry.action)
                    return (entry.source === "common" && editMode !== "common"
                        ? "Inherited Common: " : editLayer === "shifted"
                            && !hasExplicit(button) ? "Inherited Normal: " : "Effective: ")
                        + mappingState.functions[j].label
            }
        }
        return ""
    }

    function hasExplicit(button) {
        return mappingState.bindings.some(function(binding) {
            return binding.mode === editMode && binding.button === button && binding.layer === editLayer
        })
    }

    Component.onCompleted: refresh()
    Timer {
        interval: 250
        repeat: true
        running: panel.visible
        onTriggered: panel.refresh()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10
        XsLabel {
            text: "Controller Mapping" + (panel.mappingState && panel.mappingState.dirty ? " *" : "")
            font.bold: true
            horizontalAlignment: Text.AlignLeft
        }
        XsLabel {
            text: panel.mappingState
                ? (panel.mappingState.connected ? "Connected" : "Disconnected")
                    + " | Live mode: " + panel.mappingState.active_mode
                    + " / " + panel.mappingState.active_layer
                    + (panel.mappingState.menu_open ? " | Menu open" : " | Menu closed")
                : "Connecting to controller plugin..."
            horizontalAlignment: Text.AlignLeft
        }
        XsLabel {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Common mappings apply in every mode unless overridden or disabled. "
                + "Save edits to keep them across restarts. "
                + "Menu toggles open/closed; while open, use the D-pad and A to navigate/select. "
                + "Hold " + (panel.mappingState ? panel.mappingState.shift.toUpperCase() : "LT")
                + " for Shift. Media menu: RT checks, Y clears checks, A views checked media "
                + "(or highlighted media if none checked). Capture, continuous analog mapping "
                + "and the wiring view are not available yet."
            horizontalAlignment: Text.AlignLeft
        }
        RowLayout {
            XsLabel { text: "Held Shift:" }
            XsComboBox {
                objectName: "mappingShift"
                model: panel.mappingState ? panel.mappingState.shift_buttons : []
                currentIndex: panel.mappingState ? model.indexOf(panel.mappingState.shift) : -1
                onActivated: function(index) {
                    var target = model[index]
                    currentIndex = Qt.binding(function() {
                        return panel.mappingState ? model.indexOf(panel.mappingState.shift) : -1
                    })
                    panel.edit("shift", target, null)
                }
            }
            XsLabel { text: "Edit layer:" }
            XsComboBox {
                objectName: "mappingLayer"
                model: panel.mappingState ? panel.mappingState.layers : []
                currentIndex: model.indexOf(panel.editLayer)
                onActivated: function(index) { panel.editLayer = model[index] }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            XsLabel { text: "Preset:" }
            XsComboBox {
                objectName: "mappingPreset"
                Layout.fillWidth: true
                model: panel.mappingState ? panel.mappingState.presets : []
                textRole: "name"
                currentIndex: panel.presetIndex()
                onActivated: function(index) {
                    var entry = model[index]
                    // Activation must not leave the selector showing an uncommitted load.
                    currentIndex = Qt.binding(function() { return panel.presetIndex() })
                    if (entry.available) panel.loadPreset(entry.name)
                    else panel.errorText = entry.error
                }
            }
            XsPrimaryButton {
                objectName: "mappingSave"
                focusPolicy: Qt.StrongFocus
                text: "Save"
                enabled: panel.mappingState !== null && panel.mappingState.dirty
                    && panel.mappingState.selected_preset !== "Factory"
                ToolTip.visible: hovered
                ToolTip.text: !panel.mappingState ? "Loading controller mappings"
                    : panel.mappingState.selected_preset === "Factory"
                        ? "Factory is read-only. Use Save As to save your changes."
                        : panel.mappingState.dirty ? "Save changes to the selected preset"
                            : "No unsaved changes"
                onClicked: panel.save()
            }
            XsPrimaryButton {
                objectName: "mappingSaveAs"
                focusPolicy: Qt.StrongFocus
                text: "Save As"
                ToolTip.visible: hovered
                ToolTip.text: "Save the current mappings as a named local preset"
                enabled: panel.mappingState !== null
                onClicked: panel.saveAs(panel.mappingState.revision, null)
            }
        }
        RowLayout {
            XsPrimaryButton {
                objectName: "mappingImport"
                focusPolicy: Qt.StrongFocus
                text: "Import"
                enabled: panel.mappingState !== null
                onClicked: panel.presetFile("import")
            }
            XsPrimaryButton {
                objectName: "mappingExport"
                focusPolicy: Qt.StrongFocus
                text: "Export Live"
                ToolTip.visible: hovered
                ToolTip.text: "Export current mappings to a portable file without saving the local preset"
                enabled: panel.mappingState !== null
                onClicked: panel.presetFile("export")
            }
        }
        RowLayout {
            XsLabel { text: "Edit mode:" }
            XsComboBox {
                id: modeSelector
                objectName: "mappingMode"
                model: panel.mappingState ? panel.mappingState.modes : []
                currentIndex: model.indexOf(panel.editMode)
                onActivated: function(index) { panel.editMode = model[index] }
            }
            XsPrimaryButton {
                objectName: "mappingUndo"
                focusPolicy: Qt.StrongFocus
                text: "Undo"
                enabled: panel.mappingState !== null && panel.mappingState.can_undo
                onClicked: panel.edit("undo", null, null)
            }
            XsPrimaryButton {
                objectName: "mappingRedo"
                focusPolicy: Qt.StrongFocus
                text: "Redo"
                enabled: panel.mappingState !== null && panel.mappingState.can_redo
                onClicked: panel.edit("redo", null, null)
            }
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ColumnLayout {
                width: parent.width
                Repeater {
                    model: panel.mappingState ? panel.mappingState.buttons : []
                    delegate: RowLayout {
                        id: mappingRow
                        required property string modelData
                        Layout.fillWidth: true
                        XsLabel {
                            text: mappingRow.modelData.toUpperCase()
                            Layout.preferredWidth: 60
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            XsComboBox {
                                objectName: "mapping_" + mappingRow.modelData
                                enabled: panel.mappingState !== null
                                    && mappingRow.modelData !== panel.mappingState.shift
                                Layout.fillWidth: true
                                model: panel.choices()
                                textRole: "label"
                                currentIndex: panel.assignedIndex(mappingRow.modelData, model)
                                onActivated: function(index) {
                                    panel.edit("assign", mappingRow.modelData,
                                        model[index].id === "" ? null : model[index].id)
                                }
                            }
                            XsLabel {
                                objectName: "mapping_effective_" + mappingRow.modelData
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignLeft
                                text: panel.effectiveLabel(mappingRow.modelData)
                            }
                        }
                    }
                }
            }
        }
        XsLabel {
            Layout.fillWidth: true
            visible: text.length > 0
            text: panel.mappingState ? panel.mappingState.preset_warning : ""
            wrapMode: Text.WordWrap
            color: "#efb080"
            horizontalAlignment: Text.AlignLeft
        }
        XsLabel {
            Layout.fillWidth: true
            visible: text.length > 0
            text: panel.errorText
            wrapMode: Text.WordWrap
            color: "#ef8080"
            horizontalAlignment: Text.AlignLeft
        }
    }
}
