import QtQuick

// Vector-drawn folder glyph for "browse for a file" buttons -- see
// GearIcon.qml for why icons here are hand-drawn rather than Unicode
// glyphs.
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.fillStyle = root.color

        // Back tab, peeking out above the body.
        ctx.beginPath()
        roundRect(ctx, width * 0.08, height * 0.18, width * 0.38, height * 0.16, width * 0.04)
        ctx.fill()

        // Folder body.
        ctx.beginPath()
        roundRect(ctx, width * 0.08, height * 0.30, width * 0.84, height * 0.56, width * 0.06)
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
