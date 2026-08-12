import QtQuick
import "../"

Item {
    id: root
    property real progress: 1.0   // 1.0 = full time remaining, 0.0 = elapsed
    property string label: ""
    width: 260
    height: 260

    Canvas {
        id: canvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            var cx = width / 2, cy = height / 2;
            var r = Math.min(width, height) / 2 - 10;
            var start = -Math.PI / 2;

            ctx.lineWidth = 12;
            ctx.lineCap = "round";

            ctx.strokeStyle = Theme.border;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.stroke();

            var end = start + Math.PI * 2 * root.progress;
            var grad = ctx.createLinearGradient(0, 0, width, height);
            grad.addColorStop(0, Theme.accentA);
            grad.addColorStop(1, Theme.accentB);
            ctx.strokeStyle = grad;
            ctx.beginPath();
            ctx.arc(cx, cy, r, start, end);
            ctx.stroke();
        }
    }

    onProgressChanged: canvas.requestPaint()

    Text {
        anchors.centerIn: parent
        text: root.label
        color: Theme.textPrimary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeDisplay
        font.weight: Font.Bold
    }
}
