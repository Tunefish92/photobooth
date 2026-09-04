import QtQuick

// Vector-drawn "stacked photos" glyph for gallery access -- a dimmer card
// peeking out behind a solid front card with a tiny mountain+sun cutout,
// the classic "this is an image" pictogram. See GearIcon.qml for why icons
// here are hand-drawn rather than Unicode glyphs.
Canvas {
    id: root
    property color color: "white"

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        var r = width * 0.09

        // back card, dimmer -- conveys "more than one"
        ctx.fillStyle = root.color
        ctx.globalAlpha = 0.45
        ctx.beginPath()
        roundRect(ctx, width * 0.08, height * 0.08, width * 0.62, height * 0.62, r)
        ctx.fill()
        ctx.globalAlpha = 1.0

        // front card, full opacity
        ctx.beginPath()
        roundRect(ctx, width * 0.30, height * 0.30, width * 0.62, height * 0.62, r)
        ctx.fill()

        // punch a small sun + mountain out of the front card
        ctx.globalCompositeOperation = "destination-out"
        ctx.beginPath()
        ctx.arc(width * 0.50, height * 0.48, width * 0.05, 0, Math.PI * 2)
        ctx.fill()
        ctx.beginPath()
        ctx.moveTo(width * 0.36, height * 0.80)
        ctx.lineTo(width * 0.54, height * 0.58)
        ctx.lineTo(width * 0.66, height * 0.70)
        ctx.lineTo(width * 0.78, height * 0.56)
        ctx.lineTo(width * 0.92, height * 0.80)
        ctx.closePath()
        ctx.fill()
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
