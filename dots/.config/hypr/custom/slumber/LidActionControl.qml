import QtQuick
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.widgets

Rectangle {
    id: root
    implicitHeight: 98
    implicitWidth: 430
    radius: Appearance.rounding.normal
    color: Appearance.colors.colLayer1
    RowLayout {
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
        height: 36
        StyledText { Layout.fillWidth: true; text: Translation.tr("Lid action"); font.pixelSize: 13 }
        Repeater {
            model: [{label: "Sleep", value: "sleep", icon: "dark_mode"}, {label: "Slumber", value: "slumber", icon: "desktop_windows"}]
            delegate: RippleButton {
                required property var modelData
                implicitWidth: 105
                implicitHeight: 36
                buttonRadius: 20
                colBackground: Slumber.lidAction === modelData.value ? Appearance.colors.colPrimary : Appearance.colors.colLayer2
                onClicked: Slumber.setLidAction(modelData.value)
                contentItem: StyledText {
                    text: parent.modelData.label
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    color: Slumber.lidAction === parent.modelData.value ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer0
                    font.pixelSize: 12
                }
                StyledToolTip { text: parent.modelData.value === "slumber" ? "Lock and keep work running when the lid closes" : "Suspend when the lid closes" }
            }
        }
    }
    RowLayout {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 8 }
        StyledText { Layout.fillWidth: true; text: "Screen off, work continues"; font.pixelSize: 11; color: Appearance.colors.colSubtext }
        RippleButton {
            implicitWidth: 120; implicitHeight: 34; buttonRadius: 18
            colBackground: Appearance.colors.colPrimary
            onClicked: Slumber.enter()
            contentItem: StyledText { text: "Slumber now"; font.pixelSize: 12; color: Appearance.colors.colOnPrimary; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        }
    }
}
