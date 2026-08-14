import QtQuick

// Vector-drawn camera glyph for "single" mode -- see GearIcon.qml for why
// icons here are hand-drawn rather than Unicode glyphs: emoji/symbol
// coverage isn't guaranteed on a minimal kiosk install, where a missing
// glyph renders as a blank box instead of the intended icon.
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.fillStyle = root.color

        var cx = width / 2
        var cy = height / 2
        var bodyRadius = width * 0.08

        // Body
        ctx.beginPath()
        roundRect(ctx, width * 0.06, height * 0.30, width * 0.88, height * 0.56, bodyRadius)
        ctx.fill()

        // Viewfinder bump
        ctx.beginPath()
        roundRect(ctx, width * 0.36, height * 0.14, width * 0.28, height * 0.18, width * 0.04)
        ctx.fill()

        // Lens ring: punch a hole then re-fill a smaller core dot
        ctx.globalCompositeOperation = "destination-out"
        ctx.beginPath()
        ctx.arc(cx, cy + height * 0.06, width * 0.20, 0, Math.PI * 2)
        ctx.fill()
        ctx.globalCompositeOperation = "source-over"
        ctx.beginPath()
        ctx.arc(cx, cy + height * 0.06, width * 0.09, 0, Math.PI * 2)
        ctx.fill()
    }

    function roundRect(ctx, x, y, w, h, r) {
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
