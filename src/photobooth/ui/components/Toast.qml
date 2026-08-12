import QtQuick
import "../"

Item {
    id: root
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: parent.bottom
    anchors.bottomMargin: Theme.spaceXl
    width: card.width
    height: card.height
    z: 1000

    property string message: ""
    visible: opacity > 0
    opacity: 0

    function show(text) {
        message = text;
        opacity = 1;
        hideTimer.restart();
    }

    Timer {
        id: hideTimer
        interval: 2600
        onTriggered: root.opacity = 0
    }

    Behavior on opacity { NumberAnimation { duration: Theme.durationNormal; easing.type: Easing.OutCubic } }

    Rectangle {
        id: card
        width: label.implicitWidth + Theme.spaceLg
        height: 64
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.width: 1
        border.color: Theme.border
        anchors.horizontalCenter: parent.horizontalCenter

        Text {
            id: label
            anchors.centerIn: parent
            text: root.message
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
        }
    }
}
