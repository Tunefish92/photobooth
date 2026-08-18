import QtQuick

// Vector-drawn backup glyph (a down-arrow saving into a drive tray) -- see
// GearIcon.qml for why icons here are hand-drawn rather than Unicode
// glyphs (the "⏏" EJECT SYMBOL used before this has the same patchy font
// coverage the rest of this file's icons were already replaced for).
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.strokeStyle = root.color
        ctx.fillStyle = root.color
        ctx.lineCap = "round"
        ctx.lineJoin = "round"
        ctx.lineWidth = width * 0.12

        var cx = width / 2

        // Arrow shaft, straight down from the top.
        ctx.beginPath()
        ctx.moveTo(cx, height * 0.08)
        ctx.lineTo(cx, height * 0.5)
        ctx.stroke()

        // Arrowhead, tip resting where the shaft ends.
        var tipY = height * 0.62
        var headHalf = width * 0.18
        ctx.beginPath()
        ctx.moveTo(cx, tipY)
        ctx.lineTo(cx - headHalf, tipY - headHalf * 1.1)
        ctx.lineTo(cx + headHalf, tipY - headHalf * 1.1)
        ctx.closePath()
        ctx.fill()

        // Drive tray the arrow is saving into.
        ctx.beginPath()
        ctx.moveTo(width * 0.14, height * 0.78)
        ctx.lineTo(width * 0.14, height * 0.9)
        ctx.lineTo(width * 0.86, height * 0.9)
        ctx.lineTo(width * 0.86, height * 0.78)
        ctx.stroke()
    }

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
}
