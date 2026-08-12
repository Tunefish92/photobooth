import QtQuick
import "../"
import "../components"

Item {
    id: root

    Column {
        anchors.fill: parent
        anchors.margins: Theme.spaceXl
        spacing: Theme.spaceLg

        Text {
            text: Translator.tr("review.title")
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeH1
            font.weight: Font.Bold
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Rectangle {
            width: parent.width * 0.62
            height: parent.height - 220
            anchors.horizontalCenter: parent.horizontalCenter
            radius: Theme.radiusLg
            color: Theme.bgElevated
            border.width: 1
            border.color: Theme.border
            clip: true

            Image {
                anchors.fill: parent
                anchors.margins: 4
                fillMode: Image.PreserveAspectFit
                source: App.resultImageUrl
                cache: false
            }
        }

        Row {
            spacing: Theme.spaceMd
            anchors.horizontalCenter: parent.horizontalCenter

            PrimaryButton {
                text: Translator.tr("review.retake")
                outlined: true
                onClicked: App.retake()
            }
            PrimaryButton {
                text: Translator.tr("review.confirm")
                onClicked: App.confirmReview()
            }
        }
    }
}
