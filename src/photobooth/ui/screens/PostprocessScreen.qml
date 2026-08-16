import QtQuick
import "../"
import "../components"

Item {
    id: root

    Row {
        anchors.fill: parent
        anchors.margins: Theme.spaceXl
        spacing: Theme.spaceXl

        Rectangle {
            width: parent.width * 0.42
            height: parent.height
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

        Column {
            width: parent.width - parent.width * 0.42 - Theme.spaceXl
            height: parent.height
            spacing: Theme.spaceLg

            Text {
                text: Translator.tr("postprocess.title")
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeH1
                font.weight: Font.Bold
            }

            Grid {
                columns: 2
                spacing: Theme.spaceMd

                PrimaryButton {
                    visible: App.printerEnabled
                    text: Translator.tr("postprocess.print")
                    minWidth: 260
                    enabled: !App.postprocessBusy
                    onClicked: {
                        if (App.printConfirmation) {
                            printConfirm.visible = true
                        } else {
                            App.requestPrint()
                        }
                    }
                }
                PrimaryButton {
                    visible: App.mailerEnabled
                    text: Translator.tr("postprocess.email")
                    outlined: true
                    minWidth: 260
                    enabled: !App.postprocessBusy
                    onClicked: App.requestEmail()
                }
                PrimaryButton {
                    visible: App.webdavEnabled
                    text: Translator.tr("postprocess.webdav")
                    outlined: true
                    minWidth: 260
                    enabled: !App.postprocessBusy
                    onClicked: App.requestWebdavUpload()
                }
            }

            Item { width: 1; height: Theme.spaceMd }

            PrimaryButton {
                text: Translator.tr("postprocess.done")
                danger: false
                outlined: true
                onClicked: App.done()
            }
        }
    }

    Rectangle {
        id: printConfirm
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.6)
        visible: false
        z: 500

        GlassCard {
            // Sized to fit its content (label + two full-width buttons) plus
            // padding, instead of a fixed guess -- a hardcoded width here
            // was narrower than the two side-by-side buttons need, so they
            // overflowed flush against (and past) the card's border.
            width: printConfirmColumn.implicitWidth + Theme.spaceXl * 2
            height: printConfirmColumn.implicitHeight + Theme.spaceXl * 2
            anchors.centerIn: parent

            Column {
                id: printConfirmColumn
                anchors.centerIn: parent
                spacing: Theme.spaceLg

                Text {
                    text: Translator.tr("postprocess.print_confirm")
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
                        onClicked: printConfirm.visible = false
                    }
                    PrimaryButton {
                        text: Translator.tr("common.yes")
                        onClicked: {
                            printConfirm.visible = false
                            App.requestPrint()
                        }
                    }
                }
            }
        }
    }
}
