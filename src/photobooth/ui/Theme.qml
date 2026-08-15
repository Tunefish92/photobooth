pragma Singleton
import QtQuick

QtObject {
    id: theme

    // Selects one of _palettes below; set from Settings (app.theme).
    // Falls back to "aurora-dark" for an unknown/missing name so a typo'd
    // config value degrades gracefully instead of breaking every binding
    // that reads a Theme.* color.
    property string name: "aurora-dark"
    readonly property var _palette: _palettes[name] || _palettes["aurora-dark"]

    // True for every theme except the light aurora variant -- drives a
    // couple of non-color tweaks elsewhere (main.qml's background blob
    // opacity) that only make sense as a light/dark binary.
    readonly property bool dark: _palette.dark

    readonly property var _palettes: ({
        "aurora-dark": {
            dark: true,
            bg: "#101218", bgElevated: "#171a22", bgGlass: "#1b1f29", border: "#262b36",
            textPrimary: "#f3f4f7", textSecondary: "#8d92a3", textOnAccent: "#ffffff",
            accentA: "#a5b0fc", accentB: "#f5b8cf", accentC: "#9fe6d2",
            success: "#7fdcae", danger: "#f3a0a6", warning: "#f2cf8c"
        },
        "aurora-light": {
            dark: false,
            bg: "#f8f8fb", bgElevated: "#ffffff", bgGlass: "#ffffff", border: "#e7e8ee",
            textPrimary: "#1b1d24", textSecondary: "#6b6f80", textOnAccent: "#ffffff",
            accentA: "#6a74e0", accentB: "#d9679c", accentC: "#2fa583",
            success: "#2f9e6f", danger: "#d5555f", warning: "#c98a2b"
        },
        // Deep navy with sky-blue/cyan accents.
        "ocean-blue": {
            dark: true,
            bg: "#0a1628", bgElevated: "#0f2038", bgGlass: "#122544", border: "#1e3a5f",
            textPrimary: "#eaf2fb", textSecondary: "#7fa3c9", textOnAccent: "#04121f",
            accentA: "#4fc3f7", accentB: "#7c9eff", accentC: "#45e0c7",
            success: "#4fd8a8", danger: "#ff8a80", warning: "#ffca6b"
        },
        // Deep forest with mint/lime/emerald accents.
        "forest-green": {
            dark: true,
            bg: "#0d1912", bgElevated: "#14241a", bgGlass: "#172b1e", border: "#24402c",
            textPrimary: "#eef6ee", textSecondary: "#8fae94", textOnAccent: "#04140a",
            accentA: "#6fe3a4", accentB: "#b6e26d", accentC: "#37c299",
            success: "#6fe3a4", danger: "#ff8f80", warning: "#f0c766"
        },
        // Near-black with a saturated magenta/violet/cyan gradient --
        // bold and energetic rather than the other themes' restrained,
        // low-saturation accents.
        "prism-modern": {
            dark: true,
            bg: "#0b0b12", bgElevated: "#15141f", bgGlass: "#1a1826", border: "#322d47",
            textPrimary: "#ffffff", textSecondary: "#a79ecb", textOnAccent: "#0b0b12",
            accentA: "#ff3ec8", accentB: "#7b5bff", accentC: "#29e6ff",
            success: "#3cf2a0", danger: "#ff4d6d", warning: "#ffcc33"
        }
    })

    // -- palette ----------------------------------------------------------
    readonly property color bg: _palette.bg
    readonly property color bgElevated: _palette.bgElevated
    readonly property color bgGlass: _palette.bgGlass
    readonly property color border: _palette.border

    readonly property color textPrimary: _palette.textPrimary
    readonly property color textSecondary: _palette.textSecondary
    readonly property color textOnAccent: _palette.textOnAccent

    readonly property color accentA: _palette.accentA
    readonly property color accentB: _palette.accentB
    readonly property color accentC: _palette.accentC

    readonly property color success: _palette.success
    readonly property color danger: _palette.danger
    readonly property color warning: _palette.warning

    readonly property Gradient accentGradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop { position: 0.0; color: theme.accentA }
        GradientStop { position: 1.0; color: theme.accentC }
    }

    // -- shape / spacing ------------------------------------------------
    readonly property int radiusSm: 10
    readonly property int radiusMd: 18
    readonly property int radiusLg: 28
    readonly property int radiusXl: 40

    readonly property int spaceXs: 8
    readonly property int spaceSm: 16
    readonly property int spaceMd: 24
    readonly property int spaceLg: 40
    readonly property int spaceXl: 64

    // -- typography -------------------------------------------------------
    readonly property string fontFamily: "Segoe UI, Inter, Helvetica Neue, sans-serif"
    readonly property int sizeDisplay: 72
    readonly property int sizeH1: 44
    readonly property int sizeH2: 30
    readonly property int sizeBody: 20
    readonly property int sizeCaption: 15

    // -- motion -----------------------------------------------------------
    readonly property int durationFast: 140
    readonly property int durationNormal: 260
    readonly property int durationSlow: 480
    readonly property int easingStandard: Easing.OutCubic
    readonly property int easingEmphasized: Easing.OutBack
}
