import QtQuick
import "../"

GlassCard {
    id: root
    property string mode: "single"
    property string label: ""
    signal activated()

    width: 200
    height: 200
    opacity: 0.96

    scale: mouse.pressed ? 0.95 : 1.0
    Behavior on scale { NumberAnimation { duration: Theme.durationFast; easing.type: Easing.OutCubic } }

    Column {
        anchors.centerIn: parent
        spacing: Theme.spaceSm

        Item {
            width: 56
            height: 56
            anchors.horizontalCenter: parent.horizontalCenter

            CameraIcon { anchors.fill: parent; color: Theme.accentC; visible: root.mode === "single" }
            GridIcon { anchors.fill: parent; color: Theme.accentC; visible: root.mode === "grid" }
            FilmIcon { anchors.fill: parent; color: Theme.accentC; visible: root.mode === "gif" }
            RepeatIcon { anchors.fill: parent; color: Theme.accentC; visible: root.mode === "boomerang" }
        }
        Text {
            text: root.label
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        onClicked: root.activated()
    }
}
