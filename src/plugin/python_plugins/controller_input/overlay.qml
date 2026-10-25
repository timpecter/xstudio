import QtQuick
import xStudio 1.0
import xstudio.qml.models 1.0
import xstudio.qml.helpers 1.0

Item {
    anchors.fill: parent
    visible: !view.isQuickview && ((connectedValue.value === true && menuValue.value === true) || guideValue.value === true || browseVisible.value === true)
    XsModuleData {
        id: controllerState
        modelDataName: "controller_input_state"
    }
    XsAttributeValue {
        id: menuValue
        attributeTitle: "Controller Menu Held"
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
                text: "Controller mode: " + (modeValue.value === undefined ? "" : modeValue.value) + (guideValue.value === true ? "\n\n" + statusValue.value + "\n\nMenu + D-pad: change mode" + "\nX: play / pause; View: guide" + "\nViewer: D-pad exposure, A mask, Y loop" + "\nPlaylists / Media: D-pad preview, B close" + "\nA: source activation not available yet" : "")
                wrapMode: Text.WordWrap
            }
            Column {
                width: parent.width
                spacing: 4
                visible: browseVisible.value === true
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
                            text: modelData
                            elide: Text.ElideRight
                        }
                    }
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
