import QtQuick
import xStudio 1.0
import xstudio.qml.models 1.0
import xstudio.qml.helpers 1.0

Item {
    anchors.fill: parent
    visible: !view.isQuickview && ((connectedValue.value === true && menuValue.value === true) || guideValue.value === true)
    XsModuleData {
        id: controllerState
        modelDataName: "controller_input_state"
    }
    XsAttributeValue {
        id: layerValue
        attributeTitle: "Controller Layer"
        model: controllerState
    }
    XsAttributeValue {
        id: shiftValue
        attributeTitle: "Controller Shift Input"
        model: controllerState
    }
    XsAttributeValue {
        id: buttonGuideValue
        attributeTitle: "Controller Button Guide"
        model: controllerState
    }
    XsAttributeValue {
        id: menuValue
        attributeTitle: "Controller Menu Open"
        model: controllerState
    }
    XsAttributeValue {
        id: browseVisible
        attributeTitle: "Controller Browse Visible"
        model: controllerState
    }
    XsAttributeValue {
        id: browseTitle
        attributeTitle: "Controller Browse Title"
        model: controllerState
    }
    XsAttributeValue {
        id: browseRows
        attributeTitle: "Controller Browse Rows"
        model: controllerState
    }
    XsAttributeValue {
        id: browseIndex
        attributeTitle: "Controller Browse Index"
        model: controllerState
    }
    XsAttributeValue {
        id: browseMarked
        attributeTitle: "Controller Browse Marked"
        model: controllerState
    }
    XsAttributeValue {
        id: connectedValue
        attributeTitle: "Controller Connected"
        model: controllerState
    }
    XsAttributeValue {
        id: modeValue
        attributeTitle: "Controller Mode"
        model: controllerState
    }
    XsAttributeValue {
        id: guideValue
        attributeTitle: "Controller Guide"
        model: controllerState
    }
    XsAttributeValue {
        id: statusValue
        attributeTitle: "Controller Status"
        model: controllerState
    }
    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24
        width: 360
        height: content.implicitHeight + 32
        radius: 8
        color: "#dd17191d"
        border.color: "#8899aabb"
        Column {
            id: content
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 16
            spacing: 8
            Text {
                id: guideText
                width: parent.width
                visible: menuValue.value === true || guideValue.value === true
                color: "white"
                font.pixelSize: 18
                text: "Controller mode: " + (modeValue.value === undefined ? "" : modeValue.value)
                    + (layerValue.value === "shifted" ? " / Shifted" : "")
                    + (guideValue.value === true ? "\n\n" + statusValue.value
                    + "\n\nMenu: toggle controller menu"
                    + "\n" + (shiftValue.value === undefined ? "LT" : shiftValue.value) + ": held Shift"
                    + "\nMenu open: D-pad left / right changes mode"
                    + "\nMenu closed:\n" + (buttonGuideValue.value === undefined ? "" : buttonGuideValue.value)
                    + "\nDefault mode (menu closed): D-pad left / right exposure"
                    + "\nDefault mode (menu closed): D-pad up / down previous / next media"
                    + "\nMenu open: playlists / media / timeline apply only until the menu closes"
                    + "\nPlaylists / Media (menu open): D-pad up / down browse, A view"
                    + "\nMedia (menu open): RT checks, Y clears checks" : "")
                wrapMode: Text.WordWrap
            }
            Column {
                width: parent.width
                spacing: 4
                visible: browseVisible.value === true && menuValue.value === true
                Text {
                    width: parent.width
                    color: "white"
                    font.pixelSize: 18
                    text: browseTitle.value === undefined ? "" : browseTitle.value
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: browseRows.value === undefined ? [] : browseRows.value
                    Rectangle {
                        width: content.width
                        height: 28
                        radius: 4
                        color: index === browseIndex.value ? "#526985" : "transparent"
                        Text {
                            anchors.fill: parent
                            anchors.leftMargin: 6
                            anchors.rightMargin: 6
                            verticalAlignment: Text.AlignVCenter
                            color: "white"
                            font.pixelSize: 16
                            text: (modeValue.value === "media"
                                ? (browseMarked.value !== undefined && browseMarked.value[index] === true
                                    ? "\u2611  " : "\u2610  ")
                                : (browseMarked.value !== undefined && browseMarked.value[index] === true
                                    ? "\u25CF  " : "     ")) + modelData
                            elide: Text.ElideRight
                        }
                    }
                }
                Text {
                    width: parent.width
                    visible: modeValue.value === "media"
                    color: "white"
                    font.pixelSize: 16
                    text: "RT: check | Y: clear checks\nA: view checked media, or highlighted if none"
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    color: "white"
                    font.pixelSize: 16
                    text: statusValue.value === undefined ? "" : statusValue.value
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
