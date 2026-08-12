import QtQuick
import "../"

GlassCard {
    id: root
    property string glyph: "*"
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

        Text {
            text: root.glyph
            font.pixelSize: 56
            color: Theme.accentC
            anchors.horizontalCenter: parent.horizontalCenter
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
