import QtQuick
import "../"
import "../components"

Item {
    id: root

    Image {
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        source: "image://preview/" + App.previewFrameId
        cache: false
        visible: App.cameraReady || true
    }

    Rectangle { anchors.fill: parent; color: Theme.bg; opacity: 0.35 }

    Text {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: Theme.spaceXl
        text: Translator.tr("countdown.look_here") + "  ·  " + Translator.tr("capture.shot_label") + " " + (App.shotsTaken + 1) + "/" + App.shotsTotal
        color: Theme.textPrimary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeH2
        font.weight: Font.DemiBold
    }

    CountdownRing {
        anchors.centerIn: parent
        progress: App.countdownProgress
        label: App.countdownValue > 0 ? String(App.countdownValue) : ""
    }
}
