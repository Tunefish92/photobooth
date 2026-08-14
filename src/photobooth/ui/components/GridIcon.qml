import QtQuick

// Vector-drawn 2x2 grid glyph for "grid" mode -- see GearIcon.qml for why
// icons here are hand-drawn rather than Unicode glyphs.
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.fillStyle = root.color

        var gap = width * 0.10
        var cell = (width * 0.82 - gap) / 2
        var x0 = width * 0.09
        var y0 = height * 0.09
        var r = cell * 0.16

        for (var row = 0; row < 2; row++) {
            for (var col = 0; col < 2; col++) {
                ctx.beginPath()
                roundRect(ctx, x0 + col * (cell + gap), y0 + row * (cell + gap), cell, cell, r)
                ctx.fill()
            }
        }
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
