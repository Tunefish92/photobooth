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
        var startAngle = -Math.PI * 0.85
        var endAngle = Math.PI * 0.65

        ctx.lineWidth = lineWidth
        ctx.beginPath()
        ctx.arc(cx, cy, r, startAngle, endAngle, false)
        ctx.stroke()

        // Arrowhead at the arc's leading end
        var tipAngle = endAngle
        var tipX = cx + r * Math.cos(tipAngle)
        var tipY = cy + r * Math.sin(tipAngle)
        var tangent = tipAngle + Math.PI / 2
        var headLen = width * 0.20
        var headSpread = width * 0.13

        var backX = tipX - headLen * Math.cos(tangent)
        var backY = tipY - headLen * Math.sin(tangent)
        var normal = tangent + Math.PI / 2

        ctx.beginPath()
        ctx.moveTo(tipX + headSpread * Math.cos(tipAngle), tipY + headSpread * Math.sin(tipAngle))
        ctx.lineTo(backX + headSpread * Math.cos(normal), backY + headSpread * Math.sin(normal))
        ctx.lineTo(backX - headSpread * Math.cos(normal), backY - headSpread * Math.sin(normal))
        ctx.closePath()
        ctx.fill()
    }

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
}
