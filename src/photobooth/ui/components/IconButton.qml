import QtQuick
import QtQuick.Controls.Basic
import "../"

Button {
    id: root

    property string glyph: "?"
    // The "⚙" GEAR glyph's visible ink isn't centered within its own
    // character cell in any font/backend combination we could rely on --
    // rather than chase a pixel nudge that only happened to work in one
    // environment, draw it as a small vector gear instead (see
    // GearIcon.qml), which is centered by construction.
    property bool vectorGear: false
    property bool vectorPower: false
    property bool vectorClose: false
    implicitWidth: 60
    implicitHeight: 60

    scale: root.pressed ? 0.9 : 1.0
    Behavior on scale {
        NumberAnimation { duration: Theme.durationFast; easing.type: Easing.OutCubic }
    }

    contentItem: Item {
        GearIcon {
            visible: root.vectorGear
            anchors.centerIn: parent
            width: 26
            height: 26
            color: Theme.textPrimary
        }
        PowerIcon {
            visible: root.vectorPower
            anchors.centerIn: parent
            width: 26
            height: 26
            color: Theme.textPrimary
        }
        CloseIcon {
            visible: root.vectorClose
            anchors.centerIn: parent
            width: 26
            height: 26
            color: Theme.textPrimary
        }
        Text {
            visible: !root.vectorGear && !root.vectorPower && !root.vectorClose
            text: root.glyph
            color: Theme.textPrimary
            font.pixelSize: 26
            anchors.centerIn: parent
        }
    }

    background: Rectangle {
        radius: width / 2
        color: Theme.bgGlass
        border.width: 1
        border.color: Theme.border
        opacity: root.hovered ? 1.0 : 0.85
    }
}
