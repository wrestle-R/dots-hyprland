import QtQuick
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.widgets

Rectangle {
    implicitWidth: 430
    implicitHeight: column.implicitHeight + 28
    radius: Appearance.rounding.normal
    color: Appearance.colors.colLayer1
    ColumnLayout {
        id: column
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 9
            MaterialSymbol { text: "battery_charging_full"; iconSize: 22; color: Appearance.colors.colOnLayer0 }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                StyledText { text: "Battery care"; font.pixelSize: 14; font.bold: true }
                StyledText { text: ChargeLimit.supported ? "Current limit · " + ChargeLimit.actual + "%" : "Charge limits unavailable"; font.pixelSize: 11; color: Appearance.colors.colSubtext }
            }
            StyledSwitch { checked: ChargeLimit.enabled; enabled: ChargeLimit.supported && !ChargeLimit.busy; onClicked: ChargeLimit.apply(checked) }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: ChargeLimit.supported
            StyledText { text: "Stop charging at"; font.pixelSize: 12; Layout.fillWidth: true }
            StyledText { text: ChargeLimit.requested + "%"; font.pixelSize: 13; font.bold: true }
        }
        StyledSlider {
            visible: ChargeLimit.supported
            Layout.fillWidth: true
            configuration: StyledSlider.Configuration.XS
            usePercentTooltip: false
            from: 55; to: 95; stepSize: 5
            value: ChargeLimit.requested
            onMoved: ChargeLimit.requested = Math.round(value)
            enabled: !ChargeLimit.busy
        }
        RowLayout {
            Layout.fillWidth: true
            visible: ChargeLimit.supported
            StyledText { Layout.fillWidth: true; text: ChargeLimit.busy ? "Waiting for authentication…" : "For plugged-in charging"; font.pixelSize: 11; color: Appearance.colors.colSubtext }
            RippleButton {
                implicitWidth: 96; implicitHeight: 32; buttonRadius: 16
                enabled: !ChargeLimit.busy
                colBackground: Appearance.colors.colLayer2
                onClicked: ChargeLimit.apply(true)
                contentItem: StyledText { text: "Apply limit"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }
        StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; visible: ChargeLimit.error.length > 0; text: ChargeLimit.error; font.pixelSize: 11; color: Appearance.colors.colError }
    }
}
