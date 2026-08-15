import QtQuick
import QtQuick.Window
import "."
import "components"
import "screens"

Window {
    id: window
    visible: true
    width: Config.width
    height: Config.height
    visibility: Config.fullscreen ? Window.FullScreen : Window.Windowed
    color: Theme.bg
    title: "Photobooth"

    // Keeps the singleton's active palette in sync with the persisted
    // setting -- a plain binding rather than a one-time assignment in
    // onCompleted, so it also picks up the new value's notify signal if
    // the theme is changed and saved in Settings without restarting.
    Binding { target: Theme; property: "name"; value: App.theme }

    Component.onCompleted: {
        screenLoader.sourceComponent = screenForState(App.state)
    }

    // -- ambient abstract background ----------------------------------------
    // A couple of very faint, slow-drifting soft-edged forms plus a single
    // thin outline ring -- restrained "abstract art" accent rather than a
    // busy multi-blob glow, kept low-opacity so it reads as texture, not noise.
    Item {
        id: bgLayer
        anchors.fill: parent
        z: 0

        Repeater {
            model: 2
            delegate: Rectangle {
                id: blob
                readonly property real baseX: index === 0 ? bgLayer.width * 0.72 : bgLayer.width * -0.12
                readonly property real baseY: index === 0 ? bgLayer.height * -0.16 : bgLayer.height * 0.62
                readonly property color tint: index === 0 ? Theme.accentA : Theme.accentC
                x: baseX
                y: baseY
                width: 640
                height: 640
                radius: width / 2
                color: tint
                opacity: Theme.dark ? 0.09 : 0.13

                SequentialAnimation on x {
                    loops: Animation.Infinite
                    NumberAnimation { from: blob.baseX - 40; to: blob.baseX + 50; duration: 17000 + index * 2200; easing.type: Easing.InOutSine }
                    NumberAnimation { from: blob.baseX + 50; to: blob.baseX - 40; duration: 17000 + index * 2200; easing.type: Easing.InOutSine }
                }
                SequentialAnimation on y {
                    loops: Animation.Infinite
                    NumberAnimation { from: blob.baseY - 30; to: blob.baseY + 40; duration: 19000 + index * 1900; easing.type: Easing.InOutSine }
                    NumberAnimation { from: blob.baseY + 40; to: blob.baseY - 30; duration: 19000 + index * 1900; easing.type: Easing.InOutSine }
                }
            }
        }

        // thin decorative ring -- adds an abstract, hand-drawn touch
        Rectangle {
            width: 360
            height: 360
            radius: width / 2
            color: "transparent"
            border.width: 1.5
            border.color: Theme.accentB
            opacity: Theme.dark ? 0.14 : 0.20
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: -110
            anchors.bottomMargin: -140
        }
    }

    // -- active screen ------------------------------------------------------
    Loader {
        id: screenLoader
        anchors.fill: parent
        z: 1
        Behavior on opacity { NumberAnimation { duration: Theme.durationNormal; easing.type: Easing.OutCubic } }
    }

    Connections {
        target: App
        function onStateChanged() { crossfade.restart() }
    }

    SequentialAnimation {
        id: crossfade
        NumberAnimation { target: screenLoader; property: "opacity"; to: 0; duration: Theme.durationFast }
        ScriptAction { script: screenLoader.sourceComponent = screenForState(App.state) }
        NumberAnimation { target: screenLoader; property: "opacity"; to: 1; duration: Theme.durationNormal }
    }

    function screenForState(state) {
        switch (state) {
        case "idle": return idleComponent
        case "greeter": return greeterComponent
        case "countdown": return countdownComponent
        case "capture": return captureComponent
        case "processing": return processingComponent
        case "review": return reviewComponent
        case "postprocess": return postprocessComponent
        case "settings": return settingsComponent
        case "error": return errorComponent
        default: return idleComponent
        }
    }

    Component { id: idleComponent; IdleScreen {} }
    Component { id: greeterComponent; GreeterScreen {} }
    Component { id: countdownComponent; CountdownScreen {} }
    Component { id: captureComponent; CaptureScreen {} }
    Component { id: processingComponent; ProcessingScreen {} }
    Component { id: reviewComponent; ReviewScreen {} }
    Component { id: postprocessComponent; PostprocessScreen {} }
    Component { id: settingsComponent; SettingsScreen {} }
    Component { id: errorComponent; ErrorScreen {} }

    Toast {
        id: toast
        z: 1000
    }

    Connections {
        target: App
        function onToast(message) { toast.show(message) }
    }
}
