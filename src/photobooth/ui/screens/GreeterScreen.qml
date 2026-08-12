import QtQuick
import "../"

Item {
    id: root

    Column {
        anchors.centerIn: parent
        spacing: Theme.spaceMd

        Text {
            text: Translator.tr("greeter.get_ready")
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeDisplay
            font.weight: Font.Bold
            anchors.horizontalCenter: parent.horizontalCenter

            scale: 0.85
            opacity: 0
            Component.onCompleted: {
                scale = 1.0
                opacity = 1.0
            }
            Behavior on scale { NumberAnimation { duration: Theme.durationSlow; easing.type: Easing.OutBack } }
            Behavior on opacity { NumberAnimation { duration: Theme.durationSlow } }
        }

        Text {
            text: Translator.tr("greeter.subtitle")
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeH2
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
}
