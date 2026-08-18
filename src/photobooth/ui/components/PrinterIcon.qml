import QtQuick

// Vector-drawn printer glyph for the Printer settings tab -- see
// GearIcon.qml for why icons here are hand-drawn rather than Unicode glyphs
// (the "⎙" PRINT SCREEN SYMBOL used before this has patchy coverage outside
// of full desktop font sets, the same problem already fixed elsewhere).
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.fillStyle = root.color
        ctx.strokeStyle = root.color

        // Printer body
        ctx.beginPath()
        roundRect(ctx, width * 0.14, height * 0.34, width * 0.72, height * 0.34, width * 0.05)
        ctx.fill()

        // Paper feeding out the top
        ctx.beginPath()
        roundRect(ctx, width * 0.28, height * 0.10, width * 0.44, height * 0.26, width * 0.03)
        ctx.fill()

        // Output tray / printed sheet at the bottom
        ctx.beginPath()
        roundRect(ctx, width * 0.24, height * 0.62, width * 0.52, height * 0.28, width * 0.03)
        ctx.fill()

        // Punch the tray sheet white-on-solid so it reads as paper, not a
        // solid block -- leave a thin border by drawing an inset hole.
        ctx.globalCompositeOperation = "destination-out"
        ctx.beginPath()
        roundRect(ctx, width * 0.30, height * 0.68, width * 0.40, height * 0.16, width * 0.02)
        ctx.fill()
        ctx.globalCompositeOperation = "source-over"
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
