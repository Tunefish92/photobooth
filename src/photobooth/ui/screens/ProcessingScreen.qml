import QtQuick
import "../"

Item {
    id: root

    Column {
        anchors.centerIn: parent
        spacing: Theme.spaceLg

        Row {
            spacing: Theme.spaceSm
            anchors.horizontalCenter: parent.horizontalCenter

            Repeater {
                model: 3
                delegate: Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: index === 0 ? Theme.accentA : (index === 1 ? Theme.accentB : Theme.accentC)

                    SequentialAnimation on scale {
                        loops: Animation.Infinite
                        PauseAnimation { duration: index * 150 }
                        NumberAnimation { to: 1.5; duration: 380; easing.type: Easing.OutCubic }
                        NumberAnimation { to: 1.0; duration: 380; easing.type: Easing.InCubic }
                        PauseAnimation { duration: (2 - index) * 150 }
                    }
                }
            }
        }

        Text {
            text: Translator.tr("processing.title")
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeH1
            font.weight: Font.Bold
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Text {
            text: Translator.tr("processing.subtitle")
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
}
