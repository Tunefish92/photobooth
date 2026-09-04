import QtQuick
import QtQuick.Controls.Basic
import "../"

// Browse every photo on record (App.galleryImages) in a scrollable grid,
// open any one full-size, and re-print it. Two navigation levels, each
// with its own bottom-left back button (see IdleScreen.qml's mode-confirm
// back button for the same "bottom-left, icon-only" convention):
//   - grid -> idle (closes the whole overlay)
//   - detail -> grid (just clears the open image, overlay stays open)
Rectangle {
    id: root
    objectName: "galleryOverlay"
    anchors.fill: parent
    color: Theme.bg
    z: 500

    // -1 = showing the grid; otherwise the index into App.galleryImages
    // currently open full-size.
    property int detailIndex: -1

    onVisibleChanged: if (!visible) detailIndex = -1

    // -- grid view -----------------------------------------------------
    Item {
        id: gridPage
        anchors.fill: parent
        visible: root.detailIndex === -1

        Text {
            id: title
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.margins: Theme.spaceLg
            text: Translator.tr("gallery.title")
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeH1
            font.weight: Font.Bold
            color: Theme.textPrimary
        }

        Text {
            visible: App.galleryImages.length === 0
            anchors.centerIn: parent
            text: Translator.tr("gallery.empty")
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeH2
        }

        GridView {
            id: grid
            objectName: "galleryGridView"
            anchors.top: title.bottom
            anchors.topMargin: Theme.spaceMd
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: Theme.spaceLg
            clip: true
            cellWidth: 240
            cellHeight: 240
            model: App.galleryImages
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Item {
                width: grid.cellWidth
                height: grid.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    radius: Theme.radiusMd
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.border
                    clip: true

                    Image {
                        anchors.fill: parent
                        anchors.margins: 2
                        source: modelData
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.detailIndex = index
                    }
                }
            }
        }
    }

    IconButton {
        objectName: "galleryBackButton"
        visible: root.detailIndex === -1
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: Theme.spaceLg
        vectorBack: true
        onClicked: root.visible = false
    }

    // -- detail view -----------------------------------------------------
    Item {
        id: detailPage
        anchors.fill: parent
        visible: root.detailIndex !== -1

        readonly property string currentUrl: root.detailIndex >= 0 && root.detailIndex < App.galleryImages.length
            ? App.galleryImages[root.detailIndex] : ""

        Image {
            anchors.fill: parent
            anchors.margins: Theme.spaceXl
            fillMode: Image.PreserveAspectFit
            source: detailPage.currentUrl
            asynchronous: true
        }

        IconButton {
            objectName: "galleryPrevButton"
            visible: root.detailIndex > 0
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: Theme.spaceLg
            vectorBack: true
            onClicked: root.detailIndex -= 1
        }

        IconButton {
            objectName: "galleryNextButton"
            visible: root.detailIndex >= 0 && root.detailIndex < App.galleryImages.length - 1
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: Theme.spaceLg
            rotation: 180
            vectorBack: true
            onClicked: root.detailIndex += 1
        }

        PrimaryButton {
            objectName: "galleryPrintButton"
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottomMargin: Theme.spaceLg
            text: Translator.tr("postprocess.print")
            enabled: !App.postprocessBusy
            onClicked: App.printGalleryImage(detailPage.currentUrl)
        }

        IconButton {
            objectName: "galleryDetailBackButton"
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.margins: Theme.spaceLg
            vectorBack: true
            onClicked: root.detailIndex = -1
        }
    }
}
