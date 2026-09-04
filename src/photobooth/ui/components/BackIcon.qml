import QtQuick

// Vector-drawn back-arrow glyph -- see GearIcon.qml for why icons here are
// hand-drawn rather than Unicode glyphs.
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.strokeStyle = root.color
        ctx.lineCap = "round"
        ctx.lineJoin = "round"
        ctx.lineWidth = width * 0.13

        var headX = width * 0.30
        var tailX = width * 0.74
        var midY = height * 0.5
        var headSpan = height * 0.22

        // shaft
        ctx.beginPath()
        ctx.moveTo(headX, midY)
        ctx.lineTo(tailX, midY)
        ctx.stroke()

        // arrowhead ("<")
        ctx.beginPath()
        ctx.moveTo(headX + headSpan, midY - headSpan)
        ctx.lineTo(headX, midY)
        ctx.lineTo(headX + headSpan, midY + headSpan)
        ctx.stroke()
    }

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
}
