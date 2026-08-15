import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../"
import "../components"

Item {
    id: root
    objectName: "settingsRoot"
    // NOTE: must not be named "data" -- Item.data is Qt Quick's built-in
    // default property that parents all child items; shadowing it silently
    // breaks the item's children from attaching to the visual tree.
    property var settingsData: ({})
    property int currentIndex: 0
    // Which per-mode sub-tab is active within the Layout section (see
    // layoutModeTabs below): 0=single, 1=grid, 2=gif, 3=boomerang.
    property int layoutSubIndex: 0

    // Mirrors of the layout fields the margin preview depends on. settingsData
    // is a plain JS object (not real QML properties), so mutating it doesn't
    // trigger binding re-evaluation elsewhere -- these properties are kept in
    // sync by hand (see onValueModified below) so the preview stays reactive.
    property int previewNumX: 2
    property int previewNumY: 2
    property int previewSizeX: 3496
    property int previewSizeY: 2362
    property int previewMargin: 40

    // Responsive breakpoint: below this the nav rail collapses to icons only
    // and field grids stack into a single column instead of label|control.
    readonly property bool wide: width >= 900
    readonly property real navWidth: wide ? Math.min(240, width * 0.22) : 88

    readonly property var sections: [
        { icon: "⚙", label: Translator.tr("settings.tab.general") },
        { icon: "▶", label: Translator.tr("settings.tab.modes") },
        { icon: "◎", label: Translator.tr("settings.tab.camera") },
        { icon: "⎙", label: Translator.tr("settings.tab.printer") },
        { icon: "↗", label: Translator.tr("settings.tab.sharing") },
        { icon: "⏻", label: Translator.tr("settings.tab.gpio") },
        { icon: "▦", label: Translator.tr("settings.tab.layout") },
        { icon: "↻", label: Translator.tr("settings.tab.update") }
    ]

    readonly property var allModes: ["single", "grid", "gif", "boomerang"]

    function isModeEnabled(mode) {
        return !!(settingsData.flow && settingsData.flow.enabled_modes
            && settingsData.flow.enabled_modes.indexOf(mode) !== -1)
    }

    // Returns false (and leaves enabled_modes untouched) if this would
    // disable the last remaining mode -- callers must revert their own
    // toggle's visual state when that happens. Backed by the authoritative
    // guard in Settings.FlowConfig (at least one mode must stay enabled);
    // this is just the UI-side version so unchecking the last switch gives
    // immediate feedback instead of a rejected-save toast.
    function setModeEnabled(mode, enabled) {
        if (!settingsData.flow) return true
        var modes = settingsData.flow.enabled_modes.slice()
        var idx = modes.indexOf(mode)
        if (enabled && idx === -1) {
            modes.push(mode)
        } else if (!enabled && idx !== -1) {
            if (modes.length <= 1) return false
            modes.splice(idx, 1)
        }
        settingsData.flow.enabled_modes = modes
        return true
    }

    Component.onCompleted: settingsData = App.getSettingsJson()

    onSettingsDataChanged: {
        if (settingsData.layout) {
            previewNumX = settingsData.layout.num_x
            previewNumY = settingsData.layout.num_y
            previewSizeX = settingsData.layout.size_x
            previewSizeY = settingsData.layout.size_y
            previewMargin = settingsData.layout.inner_dist_x
        }
    }

    function save() {
        App.saveSettingsJson(root.settingsData)
    }

    Rectangle { anchors.fill: parent; color: Theme.bg }

    // subtle decorative accent, purely abstract -- echoes the app shell
    Rectangle {
        width: 420; height: 420
        radius: width / 2
        color: Theme.accentA
        opacity: 0.05
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: -170
        anchors.rightMargin: -150
        z: 0
    }

    // Close button -- floats in the top-right corner, well clear of the edge.
    IconButton {
        id: closeButton
        objectName: "settingsCloseButton"
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Theme.spaceLg
        z: 10
        vectorClose: true
        onClicked: App.exitSettings()
    }

    // Save button -- floats in the bottom-right corner, well clear of the edge.
    PrimaryButton {
        id: saveButton
        objectName: "settingsSaveButton"
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: Theme.spaceLg
        z: 10
        text: Translator.tr("settings.save")
        onClicked: root.save()
    }

    Text {
        id: titleText
        anchors.verticalCenter: closeButton.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Theme.spaceLg
        text: Translator.tr("settings.title")
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeH1
        font.weight: Font.DemiBold
        font.letterSpacing: 0.3
        color: Theme.textPrimary
        z: 1
    }

    Text {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: Theme.spaceLg
        text: Translator.tr("settings.restart_required")
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeCaption + 2
        z: 1
    }

    // -- navigation rail (right) --------------------------------------------
    Item {
        id: navRail
        anchors.top: closeButton.bottom
        anchors.topMargin: Theme.spaceMd
        anchors.right: parent.right
        anchors.bottom: saveButton.top
        anchors.rightMargin: Theme.spaceLg
        anchors.bottomMargin: Theme.spaceMd
        width: root.navWidth
        z: 1

        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.spaceXs

            Repeater {
                model: root.sections

                delegate: Rectangle {
                    id: navCard
                    readonly property bool selected: root.currentIndex === index
                    Layout.fillWidth: true
                    Layout.preferredHeight: 64
                    radius: Theme.radiusMd
                    color: selected ? Theme.bgElevated : "transparent"
                    border.width: selected ? 1 : 0
                    border.color: Theme.border

                    Behavior on color { ColorAnimation { duration: Theme.durationFast } }

                    // accent indicator bar for the active section
                    Rectangle {
                        visible: navCard.selected
                        width: 4
                        radius: 2
                        color: Theme.accentA
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.margins: 10
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: root.wide ? Theme.spaceMd + 6 : 0
                        anchors.rightMargin: Theme.spaceXs
                        spacing: Theme.spaceXs

                        Item { Layout.fillWidth: !root.wide; Layout.preferredWidth: root.wide ? 0 : 1 }

                        Text {
                            text: modelData.icon
                            font.pixelSize: 22
                            color: navCard.selected ? Theme.accentA : Theme.textSecondary
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            visible: root.wide
                            text: modelData.label
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeBody
                            font.weight: navCard.selected ? Font.DemiBold : Font.Normal
                            color: navCard.selected ? Theme.textPrimary : Theme.textSecondary
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            elide: Text.ElideRight
                        }

                        Item { Layout.fillWidth: !root.wide; Layout.preferredWidth: root.wide ? 0 : 1 }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.currentIndex = index
                    }
                }
            }

            Item { Layout.fillHeight: true }
        }
    }

    // -- content card (left) -------------------------------------------------
    GlassCard {
        id: contentCard
        anchors.top: closeButton.bottom
        anchors.topMargin: Theme.spaceMd
        anchors.left: parent.left
        anchors.leftMargin: Theme.spaceLg
        anchors.right: navRail.left
        anchors.rightMargin: Theme.spaceMd
        anchors.bottom: saveButton.top
        anchors.bottomMargin: Theme.spaceMd
        z: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceSm

            Text {
                text: root.sections[root.currentIndex] ? root.sections[root.currentIndex].label : ""
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeH2
                font.weight: Font.DemiBold
                color: Theme.textPrimary
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.border
            }

            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.topMargin: Theme.spaceSm
                contentHeight: stack.height
                clip: true

                Pane {
                    id: fieldsFont
                    width: parent.width
                    padding: 0
                    background: Item {}
                    font.family: Theme.fontFamily
                    font.pixelSize: 22

                    StackLayout {
                        id: stack
                        width: parent.width
                        currentIndex: root.currentIndex

                        // -- General ------------------------------------------------
                        GridLayout {
                            columns: root.wide ? 2 : 1
                            columnSpacing: Theme.spaceLg
                            rowSpacing: Theme.spaceMd
                            width: stack.width

                            Label { text: Translator.tr("settings.field.language"); color: Theme.textSecondary }
                            WideCombo {
                                objectName: "settingsLanguageCombo"
                                model: ["en", "de"]
                                currentIndex: model.indexOf(root.settingsData.app ? root.settingsData.app.language : "en")
                                onActivated: root.settingsData.app.language = currentText
                            }

                            Label { text: Translator.tr("settings.field.theme"); color: Theme.textSecondary }
                            WideCombo {
                                model: ["aurora-dark", "aurora-light"]
                                currentIndex: model.indexOf(root.settingsData.app ? root.settingsData.app.theme : "aurora-dark")
                                onActivated: root.settingsData.app.theme = currentText
                            }

                            Label { text: Translator.tr("settings.field.fullscreen"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.app ? root.settingsData.app.fullscreen : true
                                onToggled: root.settingsData.app.fullscreen = checked
                            }

                            Label { text: Translator.tr("settings.field.hide_cursor"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.app ? root.settingsData.app.hide_cursor : true
                                onToggled: root.settingsData.app.hide_cursor = checked
                            }

                            Label { text: Translator.tr("settings.field.admin_pin"); color: Theme.textSecondary }
                            WideText {
                                text: root.settingsData.admin ? root.settingsData.admin.pin : ""
                                onEditingFinished: root.settingsData.admin.pin = text
                            }
                        }

                        // -- Photo Modes ------------------------------------------------
                        GridLayout {
                            columns: root.wide ? 2 : 1
                            columnSpacing: Theme.spaceLg
                            rowSpacing: Theme.spaceMd
                            width: stack.width

                            Label { text: Translator.tr("idle.mode.single"); color: Theme.textSecondary }
                            Switch {
                                objectName: "modeSwitch_single"
                                checked: root.isModeEnabled("single")
                                onToggled: if (!root.setModeEnabled("single", checked)) checked = true
                            }

                            Label { text: Translator.tr("idle.mode.grid"); color: Theme.textSecondary }
                            Switch {
                                objectName: "modeSwitch_grid"
                                checked: root.isModeEnabled("grid")
                                onToggled: if (!root.setModeEnabled("grid", checked)) checked = true
                            }

                            Label { text: Translator.tr("idle.mode.gif"); color: Theme.textSecondary }
                            Switch {
                                objectName: "modeSwitch_gif"
                                checked: root.isModeEnabled("gif")
                                onToggled: if (!root.setModeEnabled("gif", checked)) checked = true
                            }

                            Label { text: Translator.tr("idle.mode.boomerang"); color: Theme.textSecondary }
                            Switch {
                                objectName: "modeSwitch_boomerang"
                                checked: root.isModeEnabled("boomerang")
                                onToggled: if (!root.setModeEnabled("boomerang", checked)) checked = true
                            }

                            Text {
                                Layout.columnSpan: root.wide ? 2 : 1
                                Layout.topMargin: Theme.spaceXs
                                text: Translator.tr("settings.modes_hint")
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeCaption
                                color: Theme.textSecondary
                            }

                            Rectangle {
                                Layout.columnSpan: root.wide ? 2 : 1
                                Layout.fillWidth: true
                                Layout.topMargin: Theme.spaceXs
                                Layout.bottomMargin: Theme.spaceXs
                                height: 1
                                color: Theme.border
                            }

                            Label { text: Translator.tr("settings.field.default_filter"); color: Theme.textSecondary }
                            WideCombo {
                                model: ["none", "bw", "sepia", "vintage", "vivid"]
                                currentIndex: model.indexOf(root.settingsData.effects ? root.settingsData.effects.default_filter : "none")
                                onActivated: root.settingsData.effects.default_filter = currentText
                            }
                            Label { text: Translator.tr("settings.field.chroma_key"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.effects ? root.settingsData.effects.chroma_key_enabled : false
                                onToggled: root.settingsData.effects.chroma_key_enabled = checked
                            }
                            Label { text: Translator.tr("settings.field.chroma_key_path"); color: Theme.textSecondary }
                            WideText {
                                text: root.settingsData.effects ? root.settingsData.effects.chroma_key_background : ""
                                onEditingFinished: root.settingsData.effects.chroma_key_background = text
                            }
                        }

                        // -- Camera ---------------------------------------------------
                        GridLayout {
                            columns: root.wide ? 2 : 1
                            columnSpacing: Theme.spaceLg
                            rowSpacing: Theme.spaceMd
                            width: stack.width

                            Label { text: Translator.tr("settings.field.camera_backend"); color: Theme.textSecondary }
                            WideCombo {
                                model: ["auto", "gphoto2", "picamera2", "opencv", "dummy"]
                                currentIndex: model.indexOf(root.settingsData.camera ? root.settingsData.camera.backend : "auto")
                                onActivated: root.settingsData.camera.backend = currentText
                            }

                            Label { text: Translator.tr("settings.field.rotation"); color: Theme.textSecondary }
                            WideCombo {
                                model: ["0", "90", "180", "270"]
                                currentIndex: model.indexOf(String(root.settingsData.camera ? root.settingsData.camera.rotation : 0))
                                onActivated: root.settingsData.camera.rotation = parseInt(currentText)
                            }

                            Label { text: Translator.tr("settings.field.mirror_preview"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.camera ? root.settingsData.camera.mirror_preview : true
                                onToggled: root.settingsData.camera.mirror_preview = checked
                            }

                            Label { text: Translator.tr("settings.field.usb_index"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 0; to: 8
                                value: root.settingsData.camera ? root.settingsData.camera.opencv_device_index : 0
                                onValueModified: root.settingsData.camera.opencv_device_index = value
                            }

                            Label { text: Translator.tr("settings.field.inter_shot_delay"); color: Theme.textSecondary }
                            WideSpin {
                                objectName: "interShotDelaySpin"
                                editable: true
                                from: 0; to: 10
                                value: root.settingsData.camera ? Math.round(root.settingsData.camera.inter_shot_delay_s) : 1
                                onValueModified: root.settingsData.camera.inter_shot_delay_s = value
                            }
                        }

                        // -- Printer ---------------------------------------------------
                        GridLayout {
                            columns: root.wide ? 2 : 1
                            columnSpacing: Theme.spaceLg
                            rowSpacing: Theme.spaceMd
                            width: stack.width

                            Label { text: Translator.tr("settings.field.enable_printing"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.printer ? root.settingsData.printer.enable : true
                                onToggled: root.settingsData.printer.enable = checked
                            }

                            Label { text: Translator.tr("settings.field.printer_backend"); color: Theme.textSecondary }
                            WideCombo {
                                model: ["cups", "pdf"]
                                currentIndex: model.indexOf(root.settingsData.printer ? root.settingsData.printer.backend : "cups")
                                onActivated: root.settingsData.printer.backend = currentText
                            }

                            Label { text: Translator.tr("settings.field.cups_name"); color: Theme.textSecondary }
                            WideText {
                                text: root.settingsData.printer ? root.settingsData.printer.cups_printer_name : ""
                                onEditingFinished: root.settingsData.printer.cups_printer_name = text
                            }

                            Label { text: Translator.tr("settings.field.print_confirmation"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.printer ? root.settingsData.printer.confirmation : true
                                onToggled: root.settingsData.printer.confirmation = checked
                            }

                            Label { text: Translator.tr("settings.field.paper_width"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 50; to: 300
                                value: root.settingsData.printer ? root.settingsData.printer.paper_width_mm : 148
                                onValueModified: root.settingsData.printer.paper_width_mm = value
                            }

                            Label { text: Translator.tr("settings.field.paper_height"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 50; to: 300
                                value: root.settingsData.printer ? root.settingsData.printer.paper_height_mm : 100
                                onValueModified: root.settingsData.printer.paper_height_mm = value
                            }
                        }

                        // -- Sharing ---------------------------------------------------
                        GridLayout {
                            columns: root.wide ? 2 : 1
                            columnSpacing: Theme.spaceLg
                            rowSpacing: Theme.spaceMd
                            width: stack.width

                            Label { text: Translator.tr("settings.field.email_enable"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.mailer ? root.settingsData.mailer.enable : false
                                onToggled: root.settingsData.mailer.enable = checked
                            }
                            Label { text: Translator.tr("settings.field.smtp_server"); color: Theme.textSecondary }
                            WideText {
                                text: root.settingsData.mailer ? root.settingsData.mailer.server : ""
                                onEditingFinished: root.settingsData.mailer.server = text
                            }
                            Label { text: Translator.tr("settings.field.smtp_port"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 1; to: 65535
                                value: root.settingsData.mailer ? root.settingsData.mailer.port : 587
                                onValueModified: root.settingsData.mailer.port = value
                            }
                            Label { text: Translator.tr("settings.field.smtp_user"); color: Theme.textSecondary }
                            WideText {
                                text: root.settingsData.mailer ? root.settingsData.mailer.user : ""
                                onEditingFinished: root.settingsData.mailer.user = text
                            }
                            Label { text: Translator.tr("settings.field.smtp_password"); color: Theme.textSecondary }
                            WideText {
                                echoMode: TextInput.Password
                                text: root.settingsData.mailer ? root.settingsData.mailer.password : ""
                                onEditingFinished: root.settingsData.mailer.password = text
                            }
                            Label { text: Translator.tr("settings.field.recipient"); color: Theme.textSecondary }
                            WideText {
                                text: root.settingsData.mailer ? root.settingsData.mailer.recipient : ""
                                onEditingFinished: root.settingsData.mailer.recipient = text
                            }

                            Label { text: Translator.tr("settings.field.webdav_enable"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.webdav ? root.settingsData.webdav.enable : false
                                onToggled: root.settingsData.webdav.enable = checked
                            }
                            Label { text: Translator.tr("settings.field.webdav_url"); color: Theme.textSecondary }
                            WideText {
                                text: root.settingsData.webdav ? root.settingsData.webdav.url : ""
                                onEditingFinished: root.settingsData.webdav.url = text
                            }
                            Label { text: Translator.tr("settings.field.webdav_user"); color: Theme.textSecondary }
                            WideText {
                                text: root.settingsData.webdav ? root.settingsData.webdav.user : ""
                                onEditingFinished: root.settingsData.webdav.user = text
                            }
                            Label { text: Translator.tr("settings.field.webdav_password"); color: Theme.textSecondary }
                            WideText {
                                echoMode: TextInput.Password
                                text: root.settingsData.webdav ? root.settingsData.webdav.password : ""
                                onEditingFinished: root.settingsData.webdav.password = text
                            }

                            Label { text: Translator.tr("settings.field.usb_export_enable"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.usb_export ? root.settingsData.usb_export.enable : true
                                onToggled: root.settingsData.usb_export.enable = checked
                            }
                        }

                        // -- GPIO ---------------------------------------------------
                        GridLayout {
                            columns: root.wide ? 2 : 1
                            columnSpacing: Theme.spaceLg
                            rowSpacing: Theme.spaceMd
                            width: stack.width

                            Label { text: Translator.tr("settings.field.gpio_enable"); color: Theme.textSecondary }
                            Switch {
                                checked: root.settingsData.gpio ? root.settingsData.gpio.enable : false
                                onToggled: root.settingsData.gpio.enable = checked
                            }
                            Label { text: Translator.tr("settings.field.trigger_pin"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 0; to: 27
                                value: root.settingsData.gpio ? root.settingsData.gpio.trigger_pin : 23
                                onValueModified: root.settingsData.gpio.trigger_pin = value
                            }
                            Label { text: Translator.tr("settings.field.exit_pin"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 0; to: 27
                                value: root.settingsData.gpio ? root.settingsData.gpio.exit_pin : 24
                                onValueModified: root.settingsData.gpio.exit_pin = value
                            }
                            Label { text: Translator.tr("settings.field.lamp_pin"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 0; to: 27
                                value: root.settingsData.gpio ? root.settingsData.gpio.lamp_pin : 4
                                onValueModified: root.settingsData.gpio.lamp_pin = value
                            }
                            Label { text: Translator.tr("settings.field.rgb_red_pin"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 0; to: 27
                                value: root.settingsData.gpio ? root.settingsData.gpio.chan_r_pin : 27
                                onValueModified: root.settingsData.gpio.chan_r_pin = value
                            }
                            Label { text: Translator.tr("settings.field.rgb_green_pin"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 0; to: 27
                                value: root.settingsData.gpio ? root.settingsData.gpio.chan_g_pin : 22
                                onValueModified: root.settingsData.gpio.chan_g_pin = value
                            }
                            Label { text: Translator.tr("settings.field.rgb_blue_pin"); color: Theme.textSecondary }
                            WideSpin {
                                editable: true
                                from: 0; to: 27
                                value: root.settingsData.gpio ? root.settingsData.gpio.chan_b_pin : 17
                                onValueModified: root.settingsData.gpio.chan_b_pin = value
                            }
                        }

                        // -- Layout -----------------------------------------------------
                        // One sub-tab per capture mode, each showing only the settings
                        // that mode actually uses. Single/Grid still share one underlying
                        // [layout] config section (output size, margin, background,
                        // overlay) -- editing either tab edits the same values, since a
                        // single photo is just a 1x1 grid at capture time -- while
                        // GIF/Boomerang each get their own independent [burst] fields.
                        ColumnLayout {
                            width: stack.width
                            spacing: Theme.spaceSm

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spaceXs

                                LayoutModeTabButton {
                                    objectName: "layoutModeTab_single"
                                    mode: "single"
                                    selected: root.layoutSubIndex === 0
                                    onActivated: root.layoutSubIndex = 0
                                }
                                LayoutModeTabButton {
                                    objectName: "layoutModeTab_grid"
                                    mode: "grid"
                                    selected: root.layoutSubIndex === 1
                                    onActivated: root.layoutSubIndex = 1
                                }
                                LayoutModeTabButton {
                                    objectName: "layoutModeTab_gif"
                                    mode: "gif"
                                    selected: root.layoutSubIndex === 2
                                    onActivated: root.layoutSubIndex = 2
                                }
                                LayoutModeTabButton {
                                    objectName: "layoutModeTab_boomerang"
                                    mode: "boomerang"
                                    selected: root.layoutSubIndex === 3
                                    onActivated: root.layoutSubIndex = 3
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

                            StackLayout {
                                id: layoutSubStack
                                Layout.fillWidth: true
                                currentIndex: root.layoutSubIndex

                                // -- Single ---------------------------------------------
                                GridLayout {
                                    columns: root.wide ? 2 : 1
                                    columnSpacing: Theme.spaceLg
                                    rowSpacing: Theme.spaceMd
                                    width: layoutSubStack.width

                                    Text {
                                        Layout.columnSpan: root.wide ? 2 : 1
                                        Layout.bottomMargin: Theme.spaceXs
                                        text: Translator.tr("settings.layout_shared_hint")
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeCaption
                                        color: Theme.textSecondary
                                    }

                                    Label { text: Translator.tr("settings.field.output_width"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 600; to: 8000
                                        value: root.settingsData.layout ? root.settingsData.layout.size_x : 3496
                                        onValueModified: {
                                            root.settingsData.layout.size_x = value
                                            root.previewSizeX = value
                                        }
                                    }
                                    Label { text: Translator.tr("settings.field.output_height"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 600; to: 8000
                                        value: root.settingsData.layout ? root.settingsData.layout.size_y : 2362
                                        onValueModified: {
                                            root.settingsData.layout.size_y = value
                                            root.previewSizeY = value
                                        }
                                    }
                                    Label { text: Translator.tr("settings.field.margin"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 0; to: 400
                                        value: root.settingsData.layout ? root.settingsData.layout.inner_dist_x : 40
                                        onValueModified: {
                                            root.settingsData.layout.inner_dist_x = value
                                            root.settingsData.layout.inner_dist_y = value
                                            root.settingsData.layout.outer_dist_x = value
                                            root.settingsData.layout.outer_dist_y = value
                                            root.previewMargin = value
                                        }
                                    }
                                    Label { text: Translator.tr("settings.field.background_path"); color: Theme.textSecondary }
                                    WideText {
                                        text: root.settingsData.layout ? root.settingsData.layout.background : ""
                                        onEditingFinished: root.settingsData.layout.background = text
                                    }
                                    Label { text: Translator.tr("settings.field.overlay_path"); color: Theme.textSecondary }
                                    WideText {
                                        text: root.settingsData.layout ? root.settingsData.layout.overlay : ""
                                        onEditingFinished: root.settingsData.layout.overlay = text
                                    }
                                }

                                // -- Grid -------------------------------------------------
                                GridLayout {
                                    columns: root.wide ? 2 : 1
                                    columnSpacing: Theme.spaceLg
                                    rowSpacing: Theme.spaceMd
                                    width: layoutSubStack.width

                                    Text {
                                        Layout.columnSpan: root.wide ? 2 : 1
                                        Layout.bottomMargin: Theme.spaceXs
                                        text: Translator.tr("settings.layout_shared_hint")
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeCaption
                                        color: Theme.textSecondary
                                    }

                                    Label { text: Translator.tr("settings.field.grid_columns"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 1; to: 4
                                        value: root.settingsData.layout ? root.settingsData.layout.num_x : 2
                                        onValueModified: {
                                            root.settingsData.layout.num_x = value
                                            root.previewNumX = value
                                        }
                                    }
                                    Label { text: Translator.tr("settings.field.grid_rows"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 1; to: 4
                                        value: root.settingsData.layout ? root.settingsData.layout.num_y : 2
                                        onValueModified: {
                                            root.settingsData.layout.num_y = value
                                            root.previewNumY = value
                                        }
                                    }
                                    Label { text: Translator.tr("settings.field.output_width"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 600; to: 8000
                                        value: root.settingsData.layout ? root.settingsData.layout.size_x : 3496
                                        onValueModified: {
                                            root.settingsData.layout.size_x = value
                                            root.previewSizeX = value
                                        }
                                    }
                                    Label { text: Translator.tr("settings.field.output_height"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 600; to: 8000
                                        value: root.settingsData.layout ? root.settingsData.layout.size_y : 2362
                                        onValueModified: {
                                            root.settingsData.layout.size_y = value
                                            root.previewSizeY = value
                                        }
                                    }
                                    Label { text: Translator.tr("settings.field.margin"); color: Theme.textSecondary }
                                    WideSpin {
                                        objectName: "settingsMarginSpin"
                                        editable: true
                                        from: 0; to: 400
                                        value: root.settingsData.layout ? root.settingsData.layout.inner_dist_x : 40
                                        onValueModified: {
                                            root.settingsData.layout.inner_dist_x = value
                                            root.settingsData.layout.inner_dist_y = value
                                            root.settingsData.layout.outer_dist_x = value
                                            root.settingsData.layout.outer_dist_y = value
                                            root.previewMargin = value
                                        }
                                    }

                                    // -- margin preview: paper rectangle with a
                                    // num_x*num_y grid of unstretched photo rectangles,
                                    // spaced by margin as a proportion of paper size.
                                    Item {
                                        id: layoutPreview
                                        objectName: "layoutMarginPreview"
                                        Layout.columnSpan: root.wide ? 2 : 1
                                        Layout.fillWidth: true
                                        // Paper rect height (up to maxPaperHeight) plus the
                                        // caption below it plus breathing room on both ends --
                                        // previously the paper rect could claim the *entire*
                                        // preferredHeight, leaving the caption with nowhere to
                                        // go but overlap the field above/below it.
                                        Layout.preferredHeight: 200 + captionReserve + Theme.spaceSm
                                        Layout.topMargin: Theme.spaceSm
                                        Layout.bottomMargin: Theme.spaceXs

                                        readonly property real captionReserve: Theme.sizeCaption + Theme.spaceXs + 6
                                        readonly property real maxPaperHeight: Math.max(40, height - captionReserve)
                                        readonly property real fotoAspect: 3 / 2
                                        readonly property real paperAspect: root.previewSizeY > 0 ? root.previewSizeX / root.previewSizeY : 1.5
                                        readonly property real fitWidth: Math.min(width, maxPaperHeight * paperAspect)
                                        readonly property real fitHeight: fitWidth / paperAspect

                                        Rectangle {
                                            id: paperRect
                                            width: layoutPreview.fitWidth
                                            height: layoutPreview.fitHeight
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            anchors.top: parent.top
                                            color: Theme.bgElevated
                                            border.width: 1
                                            border.color: Theme.border
                                            radius: Theme.radiusSm

                                            readonly property real marginPreview: Math.max(2, Math.min(
                                                width * (root.previewMargin / Math.max(root.previewSizeX, 1)),
                                                Math.min(width, height) * 0.16
                                            ))

                                            Grid {
                                                id: photoGrid
                                                anchors.centerIn: parent
                                                columns: Math.max(1, root.previewNumX)
                                                rows: Math.max(1, root.previewNumY)
                                                spacing: paperRect.marginPreview
                                                readonly property real cellW: (paperRect.width - 2 * paperRect.marginPreview - (columns - 1) * spacing) / columns
                                                readonly property real cellH: (paperRect.height - 2 * paperRect.marginPreview - (rows - 1) * spacing) / rows

                                                Repeater {
                                                    model: root.previewNumX * root.previewNumY
                                                    delegate: Item {
                                                        width: Math.max(1, photoGrid.cellW)
                                                        height: Math.max(1, photoGrid.cellH)
                                                        Rectangle {
                                                            anchors.centerIn: parent
                                                            width: Math.min(parent.width, parent.height * layoutPreview.fotoAspect)
                                                            height: width / layoutPreview.fotoAspect
                                                            radius: 2
                                                            color: Theme.accentA
                                                            opacity: 0.35
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        Text {
                                            anchors.top: paperRect.bottom
                                            anchors.topMargin: Theme.spaceXs
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: Translator.tr("settings.field.margin_preview_hint")
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.sizeCaption
                                            color: Theme.textSecondary
                                        }
                                    }

                                    Label { text: Translator.tr("settings.field.background_path"); color: Theme.textSecondary }
                                    WideText {
                                        text: root.settingsData.layout ? root.settingsData.layout.background : ""
                                        onEditingFinished: root.settingsData.layout.background = text
                                    }
                                    Label { text: Translator.tr("settings.field.overlay_path"); color: Theme.textSecondary }
                                    WideText {
                                        text: root.settingsData.layout ? root.settingsData.layout.overlay : ""
                                        onEditingFinished: root.settingsData.layout.overlay = text
                                    }
                                }

                                // -- GIF --------------------------------------------------
                                GridLayout {
                                    columns: root.wide ? 2 : 1
                                    columnSpacing: Theme.spaceLg
                                    rowSpacing: Theme.spaceMd
                                    width: layoutSubStack.width

                                    Label { text: Translator.tr("settings.field.gif_shot_count"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 2; to: 30
                                        value: root.settingsData.burst ? root.settingsData.burst.gif_shot_count : 6
                                        onValueModified: root.settingsData.burst.gif_shot_count = value
                                    }
                                    Label { text: Translator.tr("settings.field.gif_frame_duration"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 20; to: 2000
                                        value: root.settingsData.burst ? root.settingsData.burst.gif_frame_duration_ms : 150
                                        onValueModified: root.settingsData.burst.gif_frame_duration_ms = value
                                    }
                                    Label { text: Translator.tr("settings.field.gif_frame_width"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 200; to: 4000
                                        value: root.settingsData.burst ? root.settingsData.burst.gif_frame_max_width_px : 900
                                        onValueModified: root.settingsData.burst.gif_frame_max_width_px = value
                                    }
                                }

                                // -- Boomerang ----------------------------------------------
                                GridLayout {
                                    columns: root.wide ? 2 : 1
                                    columnSpacing: Theme.spaceLg
                                    rowSpacing: Theme.spaceMd
                                    width: layoutSubStack.width

                                    Label { text: Translator.tr("settings.field.boomerang_shot_count"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 2; to: 30
                                        value: root.settingsData.burst ? root.settingsData.burst.boomerang_shot_count : 12
                                        onValueModified: root.settingsData.burst.boomerang_shot_count = value
                                    }
                                    Label { text: Translator.tr("settings.field.boomerang_frame_duration"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 20; to: 2000
                                        value: root.settingsData.burst ? root.settingsData.burst.boomerang_frame_duration_ms : 80
                                        onValueModified: root.settingsData.burst.boomerang_frame_duration_ms = value
                                    }
                                    Label { text: Translator.tr("settings.field.boomerang_frame_width"); color: Theme.textSecondary }
                                    WideSpin {
                                        editable: true
                                        from: 200; to: 4000
                                        value: root.settingsData.burst ? root.settingsData.burst.boomerang_frame_max_width_px : 900
                                        onValueModified: root.settingsData.burst.boomerang_frame_max_width_px = value
                                    }
                                }
                            }
                        }

                        // -- Update ---------------------------------------------------
                        ColumnLayout {
                            width: stack.width
                            spacing: Theme.spaceMd

                            GridLayout {
                                Layout.fillWidth: true
                                columns: root.wide ? 2 : 1
                                columnSpacing: Theme.spaceLg
                                rowSpacing: Theme.spaceMd

                                Label { text: Translator.tr("settings.update.current_version"); color: Theme.textSecondary }
                                Text {
                                    text: App.currentVersion
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 22
                                    color: Theme.textPrimary
                                }

                                Label { text: Translator.tr("settings.update.latest_version"); color: Theme.textSecondary }
                                Text {
                                    objectName: "updateLatestVersionText"
                                    text: App.updateChecking
                                        ? Translator.tr("settings.update.checking")
                                        : (App.latestVersion || Translator.tr("settings.update.not_checked_yet"))
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 22
                                    color: Theme.textPrimary
                                }
                            }

                            Text {
                                objectName: "updateStatusText"
                                Layout.fillWidth: true
                                text: {
                                    if (App.updateApplying) return Translator.tr("settings.update.applying")
                                    if (App.updateChecking) return Translator.tr("settings.update.checking")
                                    if (App.updateError) return App.updateError
                                    if (App.latestVersion === "") return ""
                                    return App.updateAvailable
                                        ? Translator.tr("settings.update.available")
                                        : Translator.tr("settings.update.up_to_date")
                                }
                                color: App.updateAvailable ? Theme.accentA : Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeBody
                                wrapMode: Text.WordWrap
                            }

                            RowLayout {
                                spacing: Theme.spaceMd

                                PrimaryButton {
                                    objectName: "checkForUpdatesButton"
                                    text: Translator.tr("settings.update.check_button")
                                    outlined: true
                                    enabled: !App.updateChecking && !App.updateApplying
                                    onClicked: App.checkForUpdates()
                                }
                                PrimaryButton {
                                    objectName: "applyUpdateButton"
                                    text: Translator.tr("settings.update.update_button")
                                    visible: App.updateAvailable
                                    enabled: !App.updateApplying
                                    onClicked: App.applyUpdate()
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }
                }
            }
        }
    }
}
