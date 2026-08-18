import QtQuick

// Vector-drawn stacked-cards glyph for the Photo Modes settings tab -- see
// GearIcon.qml for why icons here are hand-drawn rather than Unicode glyphs
// (the "▶" glyph used before this sits off-center by an amount that varies
// per font/platform, the same problem already fixed for the other tabs).
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.strokeStyle = root.color
        ctx.lineCap = "round"
        ctx.lineJoin = "round"
        ctx.lineWidth = width * 0.09

        var cardW = width * 0.62
        var cardH = height * 0.46
        var r = width * 0.06
        var x = (width - cardW) / 2
        var step = height * 0.14

        // Two faint cards behind, one solid card in front -- reads as a
        // stack of selectable options rather than any single mode.
        for (var i = 0; i < 2; i++) {
            ctx.globalAlpha = 0.35 + i * 0.25
            roundRect(ctx, x, height * 0.12 + i * step, cardW, cardH, r)
            ctx.stroke()
        }
        ctx.globalAlpha = 1
        ctx.fillStyle = root.color
        roundRect(ctx, x, height * 0.12 + 2 * step, cardW, cardH, r)
        ctx.fill()
    }

    function roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath()
        ctx.moveTo(x + r, y)
        ctx.arcTo(x + w, y, x + w, y + h, r)
        ctx.arcTo(x + w, y + h, x, y + h, r)
        ctx.arcTo(x, y + h, x, y, r)
        ctx.arcTo(x, y, x + w, y, r)
        ctx.closePath()
    }

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
}
