import QtQuick
import QtQuick.Controls.Basic
import "../"

Button {
    id: root

    property bool outlined: false
    property bool danger: false
    property int minWidth: 220

    implicitHeight: 76
    implicitWidth: Math.max(minWidth, label.implicitWidth + Theme.spaceLg)
    font.family: Theme.fontFamily
    font.pixelSize: Theme.sizeBody
    font.weight: Font.DemiBold

    scale: root.pressed ? 0.96 : 1.0
    Behavior on scale {
        NumberAnimation { duration: Theme.durationFast; easing.type: Easing.OutCubic }
    }

    contentItem: Text {
        id: label
        text: root.text
        color: root.outlined ? Theme.textPrimary : Theme.textOnAccent
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: Theme.radiusLg
        border.width: root.outlined ? 2 : 0
        border.color: Theme.border
        color: root.outlined ? "transparent" : (root.danger ? Theme.danger : "transparent")

        gradient: (!root.outlined && !root.danger) ? Theme.accentGradient : null

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "#ffffff"
            opacity: root.hovered && !root.outlined ? 0.08 : 0.0
            Behavior on opacity { NumberAnimation { duration: Theme.durationFast } }
        }
    }
}
