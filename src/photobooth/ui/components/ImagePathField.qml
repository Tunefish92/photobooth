import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import "../"

// A path text field (still freely editable by hand) plus a browse button
// that opens a native file picker pre-filtered to image types. Used for
// the layout background/overlay paths, which are otherwise easy to get
// wrong by hand (typos, forgetting the extension, an unreachable path).
RowLayout {
    id: root

    Layout.fillWidth: true

    property alias path: field.text
    // Set by the caller instead of a plain `objectName` on the root --
    // this is a RowLayout, not the field itself, so tests need names for
    // the actual field/button rather than this wrapper.
    property string fieldObjectName: ""
    property string browseObjectName: ""

    signal pathEdited(string path)

    spacing: Theme.spaceSm

    WideText {
        id: field
        objectName: root.fieldObjectName
        Layout.fillWidth: true
        onEditingFinished: root.pathEdited(text)
    }

    Button {
        id: browseButton
        objectName: root.browseObjectName
        implicitWidth: 48
        implicitHeight: 48

        scale: browseButton.pressed ? 0.92 : 1.0
        Behavior on scale {
            NumberAnimation { duration: Theme.durationFast; easing.type: Easing.OutCubic }
        }

        contentItem: FolderIcon {
            anchors.centerIn: parent
            width: 22
            height: 22
            color: Theme.textPrimary
        }

        background: Rectangle {
            radius: Theme.radiusMd
            color: Theme.bgGlass
            border.width: 1
            border.color: Theme.border
            opacity: browseButton.hovered ? 1.0 : 0.85
        }

        onClicked: fileDialog.open()
    }

    FileDialog {
        id: fileDialog
        title: Translator.tr("settings.field.browse_image_title")
        fileMode: FileDialog.OpenFile
        nameFilters: [
            Translator.tr("settings.field.image_files_filter") + " (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff)",
            Translator.tr("settings.field.all_files_filter") + " (*)",
        ]
        onAccepted: {
            var localPath = App.urlToLocalPath(selectedFile)
            field.text = localPath
            root.pathEdited(localPath)
        }
    }
}
