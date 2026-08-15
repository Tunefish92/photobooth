import QtQuick

// Vector-drawn loop-arrow glyph for "boomerang" mode -- see GearIcon.qml for
// why icons here are hand-drawn rather than Unicode glyphs.
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.strokeStyle = root.color
        ctx.fillStyle = root.color
        ctx.lineCap = "round"

        var cx = width / 2
        var cy = height / 2
        var r = width * 0.30
        var lineWidth = width * 0.11

        // Ring with a gap at the bottom (90deg, since Canvas angles
        // increase clockwise from the positive x-axis): arc runs from just
        // past the gap clockwise all the way around to just before it.
        var gapHalf = Math.PI * 0.22
        var startAngle = Math.PI * 0.5 + gapHalf
        var endAngle = Math.PI * 0.5 - gapHalf + Math.PI * 2

        ctx.lineWidth = lineWidth
        ctx.beginPath()
        ctx.arc(cx, cy, r, startAngle, endAngle, false)
        ctx.stroke()

        // Arrowhead based at the arc's trailing end, tip extending further
        // along the direction of travel (tangent = endAngle + 90deg for a
        // clockwise sweep) -- shows the loop's rotation direction.
        var endX = cx + r * Math.cos(endAngle)
        var endY = cy + r * Math.sin(endAngle)
        var tangent = endAngle + Math.PI / 2
        var normal = tangent + Math.PI / 2
        var headLen = width * 0.24
        var headSpread = width * 0.14

        var tipX = endX + headLen * Math.cos(tangent)
        var tipY = endY + headLen * Math.sin(tangent)
        var leftX = endX + headSpread * Math.cos(normal)
        var leftY = endY + headSpread * Math.sin(normal)
        var rightX = endX - headSpread * Math.cos(normal)
        var rightY = endY - headSpread * Math.sin(normal)

        ctx.beginPath()
        ctx.moveTo(tipX, tipY)
        ctx.lineTo(leftX, leftY)
        ctx.lineTo(rightX, rightY)
        ctx.closePath()
        ctx.fill()
    }

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
}
