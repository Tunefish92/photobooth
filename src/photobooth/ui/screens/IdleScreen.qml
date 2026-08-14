import QtQuick
import "../"
import "../components"

Item {
    id: root

    // -- slideshow of recent shots, faded in behind everything -------------
    Image {
        id: slideshow
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        opacity: 0.16
        visible: App.slideshowImages.length > 0

        property int idx: 0
        source: App.slideshowImages.length > 0 ? App.slideshowImages[idx] : ""

        Timer {
            interval: 5000
            running: App.slideshowImages.length > 1
            repeat: true
            onTriggered: slideshow.idx = (slideshow.idx + 1) % App.slideshowImages.length
        }

        Behavior on source { PropertyAnimation { duration: Theme.durationSlow } }

        Rectangle { anchors.fill: parent; color: Theme.bg; opacity: 0.55 }
    }

    IconButton {
        id: settingsGearButton
        objectName: "settingsGearButton"
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Theme.spaceLg
        vectorGear: true
        onClicked: pinPopup.visible = true
    }

    // Small, unobtrusive indicator that a newer release is available --
    // AppController checks shortly after startup and whenever the Settings
    // screen's Update tab is used; this just reflects App.updateAvailable.
    Rectangle {
        id: updateBadge
        objectName: "updateAvailableBadge"
        visible: App.updateAvailable
        anchors.top: settingsGearButton.bottom
        anchors.topMargin: Theme.spaceXs
        anchors.horizontalCenter: settingsGearButton.horizontalCenter
        radius: height / 2
        height: badgeLabel.implicitHeight + Theme.spaceXs
        width: badgeLabel.implicitWidth + Theme.spaceSm
        color: Theme.accentA

        Text {
            id: badgeLabel
            anchors.centerIn: parent
            text: Translator.tr("idle.update_badge")
            color: Theme.textOnAccent
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            font.weight: Font.DemiBold
        }
    }

    IconButton {
        objectName: "exitButton"
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: Theme.spaceLg
        vectorPower: true
        onClicked: exitConfirm.visible = true
    }

    Column {
        anchors.centerIn: parent
        spacing: Theme.spaceXl

        Column {
            spacing: Theme.spaceSm
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                text: Translator.tr("idle.title")
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeDisplay
                font.weight: Font.Bold
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Text {
                text: Translator.tr("idle.tap_to_start")
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeH2
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }

        Row {
            spacing: Theme.spaceMd
            anchors.horizontalCenter: parent.horizontalCenter

            Repeater {
                model: App.enabledModes
                delegate: ModeTile {
                    mode: modelData
                    label: Translator.tr("idle.mode." + modelData)
                    onActivated: App.start(modelData, App.defaultFilter)
                }
            }
        }
    }

    // -- settings PIN gate --------------------------------------------------
    Rectangle {
        id: pinPopup
        objectName: "pinPopup"
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.6)
        visible: false
        z: 500

        MouseArea { anchors.fill: parent; onClicked: pinPopup.visible = false }

        GlassCard {
            id: pinCard
            objectName: "pinCard"
            // Sized to fit its content (label + display + digit grid) plus
            // padding, instead of a fixed guess -- a hardcoded height here
            // previously clipped the bottom row of digit buttons outside
            // the card's border.
            width: pinColumn.implicitWidth + Theme.spaceXl * 2
            height: pinColumn.implicitHeight + Theme.spaceXl * 2
            anchors.centerIn: parent

            MouseArea { anchors.fill: parent } // swallow clicks so backdrop doesn't close

            Column {
                id: pinColumn
                anchors.centerIn: parent
                spacing: Theme.spaceMd

                Text {
                    text: Translator.tr("settings.pin_prompt")
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                PinPad {
                    id: pad
                    anchors.horizontalCenter: parent.horizontalCenter
                    onAccepted: function (pin) {
                        if (App.enterSettings(pin)) {
                            pinPopup.visible = false
                            pad.value = ""
                        } else {
                            pad.value = ""
                        }
                    }
                }
            }
        }
    }

    // -- exit confirmation --------------------------------------------------
    Rectangle {
        id: exitConfirm
        objectName: "exitConfirm"
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.6)
        visible: false
        z: 500

        GlassCard {
            // Sized to fit its content (label + two full-width buttons) plus
            // padding, instead of a fixed guess -- a hardcoded width here
            // was narrower than the two side-by-side buttons need, so they
            // overflowed flush against (and past) the card's border.
            width: exitConfirmColumn.implicitWidth + Theme.spaceXl * 2
            height: exitConfirmColumn.implicitHeight + Theme.spaceXl * 2
            anchors.centerIn: parent

            Column {
                id: exitConfirmColumn
                anchors.centerIn: parent
                spacing: Theme.spaceLg

                Text {
                    text: Translator.tr("idle.exit_confirm")
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeH2
                    font.weight: Font.DemiBold
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Row {
                    spacing: Theme.spaceMd
                    anchors.horizontalCenter: parent.horizontalCenter

                    PrimaryButton {
                        text: Translator.tr("common.no")
                        outlined: true
                        onClicked: exitConfirm.visible = false
                    }
                    PrimaryButton {
                        text: Translator.tr("common.yes")
                        danger: true
                        onClicked: Qt.quit()
                    }
                }
            }
        }
    }

    onVisibleChanged: if (!visible) { pinPopup.visible = false; exitConfirm.visible = false }
}
