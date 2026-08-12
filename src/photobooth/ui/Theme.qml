pragma Singleton
import QtQuick

QtObject {
    id: theme

    // Toggle drives every color below; set from Settings ("aurora-dark" / "aurora-light")
    property bool dark: true

    // -- palette --------------------------------------------------------
    // Quiet neutral base with a single soft accent hue, used sparingly --
    // an "elegant, light-accent" system rather than saturated neon.
    readonly property color bg: dark ? "#101218" : "#f8f8fb"
    readonly property color bgElevated: dark ? "#171a22" : "#ffffff"
    readonly property color bgGlass: dark ? "#1b1f29" : "#ffffff"
    readonly property color border: dark ? "#262b36" : "#e7e8ee"

    readonly property color textPrimary: dark ? "#f3f4f7" : "#1b1d24"
    readonly property color textSecondary: dark ? "#8d92a3" : "#6b6f80"
    readonly property color textOnAccent: "#ffffff"

    // soft periwinkle / blush / sage -- pastel, low-saturation accents
    readonly property color accentA: dark ? "#a5b0fc" : "#6a74e0"
    readonly property color accentB: dark ? "#f5b8cf" : "#d9679c"
    readonly property color accentC: dark ? "#9fe6d2" : "#2fa583"

    readonly property color success: dark ? "#7fdcae" : "#2f9e6f"
    readonly property color danger: dark ? "#f3a0a6" : "#d5555f"
    readonly property color warning: dark ? "#f2cf8c" : "#c98a2b"

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
