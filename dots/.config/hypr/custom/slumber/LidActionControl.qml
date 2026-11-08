import QtQuick
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.widgets

Rectangle {
    implicitHeight: 120
    implicitWidth: 430
    radius: Appearance.rounding.normal
    color: Appearance.colors.colLayer1
    border.width: 1; border.color: Appearance.colors.colLayer2
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 14; spacing: 12
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            MaterialSymbol { text: "dark_mode"; iconSize: 24; color: Appearance.colors.colOnLayer0 }
            Column {
                spacing: 3
                StyledText { text: "Slumber"; font.pixelSize: Appearance.font.pixelSize.small }
                StyledText { text: "Screen off. Work keeps going."; font.pixelSize: Appearance.font.pixelSize.smaller; color: Appearance.colors.colSubtext }
            }
            Item { Layout.fillWidth: true; Layout.minimumWidth: 8 }
            RippleButton {
                text: "Start Slumber now"
                Layout.preferredWidth: 40; Layout.preferredHeight: 36
                buttonRadius: 18
                colBackground: Appearance.colors.colPrimary; colBackgroundHover: Appearance.colors.colPrimaryHover
                onClicked: Slumber.enter()
                contentItem: MaterialSymbol { text: "play_arrow"; iconSize: 24; color: Appearance.colors.colOnPrimary; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                StyledToolTip { text: "Start Slumber now · Super+Ctrl+L" }
            }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Appearance.colors.colLayer2 }
        RowLayout {
            Layout.fillWidth: true
            StyledText { text: "On lid close"; font.pixelSize: Appearance.font.pixelSize.smallie }
            Item { Layout.fillWidth: true }
            Rectangle {
                Layout.preferredWidth: 174; Layout.preferredHeight: 32; radius: 16; color: Appearance.colors.colLayer0
                RowLayout {
                    anchors.fill: parent; anchors.margins: 2; spacing: 2
                    Repeater {
                        model: [{label:"Sleep",value:"sleep"},{label:"Slumber",value:"slumber"}]
                        delegate: RippleButton {
                            id: modeButton
                            required property var modelData
                            Layout.fillWidth: true; Layout.fillHeight: true
                            buttonRadius: 15; toggled: Slumber.lidAction === modelData.value; colBackground: "transparent"
                            onClicked: Slumber.setLidAction(modelData.value)
                            contentItem: StyledText { text: modeButton.modelData.label; font.pixelSize: Appearance.font.pixelSize.smaller; color: modeButton.toggled ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer0; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                    }
                }
            }
        }
    }
}
