import QtQuick

// Vector-drawn share glyph (an up-arrow leaving a tray) for the Sharing
// settings tab -- deliberately the mirror of BackupIcon's down-arrow, since
// Sharing sends photos out (email/WebDAV) while Backup pulls them in. See
// GearIcon.qml for why icons here are hand-drawn rather than Unicode glyphs.
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

        // Arrow shaft, rising from the tray toward the top.
        ctx.beginPath()
        ctx.moveTo(cx, height * 0.92)
        ctx.lineTo(cx, height * 0.5)
        ctx.stroke()

        // Arrowhead, tip pointing up.
        var tipY = height * 0.38
        var headHalf = width * 0.18
        ctx.beginPath()
        ctx.moveTo(cx, tipY)
        ctx.lineTo(cx - headHalf, tipY + headHalf * 1.1)
        ctx.lineTo(cx + headHalf, tipY + headHalf * 1.1)
        ctx.closePath()
        ctx.fill()

        // Tray the arrow is leaving from.
        ctx.beginPath()
        ctx.moveTo(width * 0.14, height * 0.1)
        ctx.lineTo(width * 0.14, height * 0.22)
        ctx.lineTo(width * 0.86, height * 0.22)
        ctx.lineTo(width * 0.86, height * 0.1)
        ctx.stroke()
    }

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
}
