import QtQuick

// Vector-drawn power glyph -- see GearIcon.qml for why icons here are
// hand-drawn rather than Unicode glyphs (the "⏻" POWER SYMBOL used
// before this has patchy coverage outside of full desktop font sets).
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.strokeStyle = root.color
        ctx.lineCap = "round"
        ctx.lineWidth = width * 0.13

        var cx = width / 2
        var cy = height * 0.56
        var r = width * 0.28

        // Ring with a gap at the top for the line to pass through
        ctx.beginPath()
        ctx.arc(cx, cy, r, -Math.PI * 0.65, Math.PI * 0.65, false)
        ctx.stroke()

        // Vertical line piercing the gap
        ctx.beginPath()
        ctx.moveTo(cx, height * 0.14)
        ctx.lineTo(cx, height * 0.52)
        ctx.stroke()
    }

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
}
