import QtQuick
import "../"

Item {
    id: root

    Image {
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        source: "image://preview/" + App.previewFrameId
        cache: false
    }

    Text {
        anchors.centerIn: parent
        text: Translator.tr("capture.smile")
        color: Theme.textPrimary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeDisplay
        font.weight: Font.Bold
        style: Text.Outline
        styleColor: Theme.bg
    }

    Rectangle {
        id: flash
        anchors.fill: parent
        color: "white"
        opacity: 0
        SequentialAnimation on opacity {
            running: true
            NumberAnimation { to: 0.85; duration: 60 }
            NumberAnimation { to: 0; duration: 220 }
        }
    }
}
