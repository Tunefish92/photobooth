import QtQuick

// Vector-drawn close ("X") glyph -- see GearIcon.qml for why icons here are
// hand-drawn rather than Unicode glyphs (the "✕" MULTIPLICATION X used
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

        var inset = width * 0.24

        ctx.beginPath()
        ctx.moveTo(inset, inset)
        ctx.lineTo(width - inset, height - inset)
        ctx.stroke()

        ctx.beginPath()
        ctx.moveTo(width - inset, inset)
        ctx.lineTo(inset, height - inset)
        ctx.stroke()
    }

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
}
