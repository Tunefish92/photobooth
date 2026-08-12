import QtQuick

// A small vector-drawn gear, geometrically centered on the canvas by
// construction (every tooth is placed via rotation around the exact canvas
// center). Exists because the "⚙" GEAR Unicode glyph's visible ink isn't
// centered within its own character cell -- how far off varies by font and
// even by rendering backend, so no fixed pixel nudge stayed correct across
// environments. Drawing it ourselves removes that uncertainty entirely.
Canvas {
    id: root
    property color color: "white"
    property int teeth: 8

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()

        var cx = width / 2
        var cy = height / 2
        var bodyR = width * 0.30
        var toothLen = width * 0.16
        var toothHalfWidth = width * 0.095
        var holeR = width * 0.13

        ctx.fillStyle = root.color

        ctx.beginPath()
        ctx.arc(cx, cy, bodyR, 0, Math.PI * 2)
        ctx.fill()

        for (var i = 0; i < teeth; i++) {
            var angle = (Math.PI * 2 / teeth) * i
            ctx.save()
            ctx.translate(cx, cy)
            ctx.rotate(angle)
            ctx.fillRect(-toothHalfWidth, -(bodyR + toothLen), toothHalfWidth * 2, toothLen + 1)
            ctx.restore()
        }

        ctx.globalCompositeOperation = "destination-out"
        ctx.beginPath()
        ctx.arc(cx, cy, holeR, 0, Math.PI * 2)
        ctx.fill()
        ctx.globalCompositeOperation = "source-over"
    }

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
}
