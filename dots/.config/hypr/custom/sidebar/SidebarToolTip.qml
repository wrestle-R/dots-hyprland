import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ToolTip {
    id: root
    property string heading: ""
    property string value: ""
    property real maximumWidth: 280
    property Item horizontalBounds: null
    readonly property real minimumX: horizontalBounds ? horizontalBounds.mapToItem(parent, 0, 0).x : 0
    readonly property real boundsWidth: horizontalBounds ? horizontalBounds.width : parent.width
    readonly property color accent: "#ff914d"
    objectName: "sidebarToolTip"
    popupType: Popup.Item
    visible: parent?.hovered ?? false
    delay: 450
    timeout: -1
    margins: 8
    padding: 12
    // Keep hints inside the drawer even when the target is at either edge.
    width: Math.min(maximumWidth, Math.max(1, boundsWidth), Math.max(150, body.implicitWidth + 2 * padding))
    x: Math.max(minimumX, Math.min(minimumX + boundsWidth - width, (parent.width - width) / 2))
    y: -height - 8
    focus: false
    closePolicy: Popup.NoAutoClose
    background: Rectangle {
        radius: 12
        color: Appearance.colors.colLayer2Base
        border.width: 1
        border.color: Appearance.colors.colLayer0Border
        Rectangle {
            x: 12
            y: 12
            width: 3
            height: 13
            radius: 1.5
            visible: root.value.length > 0
            color: root.accent
        }
    }
    contentItem: ColumnLayout {
        id: body
        spacing: 5
        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: root.value.length > 0 ? 10 : 0
            visible: root.heading.length > 0
            text: root.heading
            textFormat: Text.PlainText
            font.pixelSize: 12
            font.weight: Font.Medium
            color: Appearance.colors.colSubtext
            wrapMode: Text.Wrap
        }
        StyledText {
            Layout.fillWidth: true
            visible: root.value.length > 0
            text: root.value
            textFormat: Text.PlainText
            font.pixelSize: 22
            font.weight: Font.DemiBold
            color: root.accent
        }
        StyledText {
            Layout.fillWidth: true
            visible: root.text.length > 0
            text: root.text
            textFormat: Text.PlainText
            font.pixelSize: 12
            color: Appearance.colors.colOnLayer2
            wrapMode: Text.Wrap
        }
    }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 100 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 80 } }
}
