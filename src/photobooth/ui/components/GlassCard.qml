import QtQuick
import "../"

Rectangle {
    radius: Theme.radiusLg
    color: Theme.bgGlass
    opacity: 0.92
    border.width: 1
    border.color: Theme.border

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.06) }
            GradientStop { position: 0.4; color: Qt.rgba(1, 1, 1, 0.0) }
        }
    }
}
