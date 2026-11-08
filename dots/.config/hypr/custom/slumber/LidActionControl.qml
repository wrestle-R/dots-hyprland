import QtQuick
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.widgets

Rectangle {
    id: root
    implicitHeight: 130
    implicitWidth: 430
    radius: Appearance.rounding.normal
    color: Appearance.colors.colLayer1
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 9
            MaterialSymbol { text: "desktop_windows"; iconSize: 22; color: Appearance.colors.colOnLayer0 }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                StyledText { text: "Slumber"; font.pixelSize: 14; font.bold: true }
                StyledText { text: "Screen off. Work keeps going."; font.pixelSize: 11; color: Appearance.colors.colSubtext }
            }
            RippleButton {
                implicitWidth: 96; implicitHeight: 34; buttonRadius: 17
                colBackground: Appearance.colors.colPrimary
                colBackgroundHover: Appearance.colors.colPrimaryHover
                onClicked: Slumber.enter()
                contentItem: StyledText { text: "Start now"; font.pixelSize: 12; color: Appearance.colors.colOnPrimary; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Appearance.colors.colLayer2 }
        RowLayout {
            Layout.fillWidth: true
            StyledText { Layout.fillWidth: true; text: "When lid closes"; font.pixelSize: 12 }
            Rectangle {
                implicitWidth: 176; implicitHeight: 36; radius: 18; color: Appearance.colors.colLayer0
                RowLayout {
                    anchors.fill: parent; anchors.margins: 3; spacing: 3
                    Repeater {
                        model: [{label:"Sleep",value:"sleep"},{label:"Slumber",value:"slumber"}]
                        delegate: RippleButton {
                            id: modeButton
                            required property var modelData
                            Layout.fillWidth: true; Layout.fillHeight: true
                            buttonRadius: 16
                            toggled: Slumber.lidAction === modelData.value
                            colBackground: "transparent"
                            onClicked: Slumber.setLidAction(modelData.value)
                            contentItem: StyledText { text: modeButton.modelData.label; font.pixelSize: 11; color: modeButton.toggled ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer0; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            StyledToolTip { text: modeButton.modelData.value === "slumber" ? "Keep work running with the lid closed" : "Suspend when the lid closes" }
                        }
                    }
                }
            }
        }
    }
}
