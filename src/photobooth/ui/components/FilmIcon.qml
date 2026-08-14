import QtQuick

// Vector-drawn filmstrip glyph for "gif" mode -- see GearIcon.qml for why
// icons here are hand-drawn rather than Unicode glyphs.
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.fillStyle = root.color

        var x = width * 0.10
        var y = height * 0.14
        var w = width * 0.80
        var h = height * 0.72

        ctx.beginPath()
        roundRect(ctx, x, y, w, h, width * 0.06)
        ctx.fill()

        ctx.globalCompositeOperation = "destination-out"

        // Sprocket holes along the left/right edges
        var holeSize = width * 0.07
        var holeInset = width * 0.05
        var holeCount = 3
        for (var i = 0; i < holeCount; i++) {
            var holeY = y + h * ((i + 0.5) / holeCount) - holeSize / 2
            ctx.fillRect(x + holeInset, holeY, holeSize, holeSize)
            ctx.fillRect(x + w - holeInset - holeSize, holeY, holeSize, holeSize)
        }

        // Frame dividers
        var dividerW = width * 0.035
        ctx.fillRect(x + w * 0.36, y, dividerW, h)
        ctx.fillRect(x + w * 0.64, y, dividerW, h)

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
