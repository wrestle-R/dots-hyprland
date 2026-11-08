import QtQuick
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.widgets

Rectangle {
    id: root
    opacity: 0
    Component.onCompleted: opacity = 1
    Behavior on opacity { NumberAnimation { duration: 300 } }
    property var entries: Notifications.list.filter(n => Slumber.allowed(n)).slice().sort((a,b) => b.time-a.time)
    implicitWidth: Math.min(560, parent.width - 40)
    implicitHeight: content.implicitHeight + 28
    radius: 28
    color: Appearance.colors.colLayer0
    border.width: 1
    border.color: Appearance.colors.colLayer2
    ColumnLayout {
        id: content
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            MaterialSymbol { text: "lock"; iconSize: 17; color: Appearance.colors.colOnLayer0 }
            StyledText { text: "Locked"; font.pixelSize: 12 }
            Item { Layout.fillWidth: true }
            StyledText { text: root.entries.length ? root.entries.length + " notifications" : "No notifications"; font.pixelSize: 11; color: Appearance.colors.colSubtext }
        }
        Repeater {
            model: root.entries.slice(0, 3)
            delegate: ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 3
                StyledText { Layout.fillWidth: true; text: modelData.appName + " · " + modelData.summary; textFormat: Text.PlainText; font.pixelSize: 13; elide: Text.ElideRight; font.bold: true }
                StyledText { Layout.fillWidth: true; text: modelData.body; textFormat: Text.PlainText; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight; color: Appearance.colors.colSubtext; visible: text.length > 0 }
            }
        }
    }
}
