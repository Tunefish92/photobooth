import QtQuick
import "../"
import "../components"

Item {
    id: root

    Column {
        anchors.centerIn: parent
        spacing: Theme.spaceLg

        Text {
            text: "⚠"
            font.pixelSize: 72
            color: Theme.danger
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Text {
            text: Translator.tr("error.title")
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeH1
            font.weight: Font.Bold
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Text {
            text: App.errorMessage
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            anchors.horizontalCenter: parent.horizontalCenter
            wrapMode: Text.WordWrap
            width: 600
            horizontalAlignment: Text.AlignHCenter
        }

        Row {
            spacing: Theme.spaceMd
            anchors.horizontalCenter: parent.horizontalCenter

            PrimaryButton {
                text: Translator.tr("error.abort")
                outlined: true
                onClicked: App.abortError()
            }
            PrimaryButton {
                text: Translator.tr("error.retry")
                onClicked: App.retryError()
            }
        }
    }
}
