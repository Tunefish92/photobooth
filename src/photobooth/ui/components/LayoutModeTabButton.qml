import QtQuick
import QtQuick.Layouts
import "../"

// One sub-tab button in the Settings -> Layout section's per-mode tab bar
// (see SettingsScreen.qml). A plain component rather than a Repeater
// delegate -- Repeater-generated items in this codebase weren't reliably
// picking up a dynamically-built objectName, which the QML smoke tests
// need to find each tab button.
Rectangle {
    id: root
    property string mode: ""
    property bool selected: false
    signal activated()

    Layout.fillWidth: true
    Layout.preferredHeight: 40
    radius: Theme.radiusSm
    color: selected ? Theme.bgElevated : "transparent"
    border.width: selected ? 1 : 0
    border.color: Theme.border

    Behavior on color { ColorAnimation { duration: Theme.durationFast } }

    Text {
        anchors.centerIn: parent
        text: Translator.tr("idle.mode." + root.mode)
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeBody
        font.weight: root.selected ? Font.DemiBold : Font.Normal
        color: root.selected ? Theme.textPrimary : Theme.textSecondary
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.activated()
    }
}
