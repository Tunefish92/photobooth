import QtQuick
import "../"

Column {
    id: root
    spacing: Theme.spaceMd
    property string value: ""
    property int maxLength: 8
    signal accepted(string pin)

    Rectangle {
        width: 260
        height: 64
        radius: Theme.radiusMd
        color: Theme.bg
        border.width: 1
        border.color: Theme.border
        anchors.horizontalCenter: parent.horizontalCenter

        Text {
            anchors.centerIn: parent
            text: "●".repeat(root.value.length) || " "
            font.pixelSize: 22
            font.letterSpacing: 6
            color: Theme.textPrimary
        }
    }

    Grid {
        columns: 3
        spacing: Theme.spaceSm
        anchors.horizontalCenter: parent.horizontalCenter

        Repeater {
            model: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "✓"]
            delegate: Rectangle {
                width: 72
                height: 72
                radius: Theme.radiusMd
                color: Theme.bgGlass
                border.width: 1
                border.color: Theme.border

                Text {
                    anchors.centerIn: parent
                    text: modelData
                    font.pixelSize: 24
                    color: Theme.textPrimary
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (modelData === "⌫") {
                            root.value = root.value.slice(0, -1)
                        } else if (modelData === "✓") {
                            root.accepted(root.value)
                        } else if (root.value.length < root.maxLength) {
                            root.value += modelData
                        }
                    }
                }
            }
        }
    }
}
