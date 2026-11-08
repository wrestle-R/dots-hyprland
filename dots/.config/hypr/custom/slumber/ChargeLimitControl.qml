import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.widgets

Rectangle {
    implicitWidth: 430
    implicitHeight: column.implicitHeight + 20
    radius: Appearance.rounding.normal
    color: Appearance.colors.colLayer1
    ColumnLayout {
        id: column
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
        spacing: 5
        RowLayout {
            Layout.fillWidth: true
            MaterialSymbol { text: "battery_charging_full"; iconSize: 23; color: Appearance.colors.colOnLayer0 }
            StyledText { Layout.fillWidth: true; text: "Charge limit"; font.pixelSize: 13 }
            StyledText { text: ChargeLimit.supported ? ChargeLimit.actual + "%" : "Unsupported"; font.pixelSize: 12 }
            StyledSwitch { checked: ChargeLimit.enabled; enabled: ChargeLimit.supported && !ChargeLimit.busy; onClicked: ChargeLimit.apply(checked) }
        }
        RowLayout {
            Layout.fillWidth: true
            StyledText { text: "Limit"; font.pixelSize: 12 }
            StyledSlider { configuration: StyledSlider.Configuration.XS; usePercentTooltip: false; Layout.fillWidth: true; from: 55; to: 95; stepSize: 5; value: ChargeLimit.requested; onMoved: ChargeLimit.requested = Math.round(value); enabled: ChargeLimit.supported && !ChargeLimit.busy }
            StyledText { text: ChargeLimit.requested + "%"; font.pixelSize: 12 }
            RippleButton {
                implicitWidth: 58; implicitHeight: 30; buttonRadius: 15
                enabled: ChargeLimit.supported && !ChargeLimit.busy
                colBackground: Appearance.colors.colLayer2
                onClicked: ChargeLimit.apply(true)
                contentItem: StyledText { text: "Apply"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }
        StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; visible: ChargeLimit.error.length > 0; text: ChargeLimit.error; font.pixelSize: 11; color: Appearance.colors.colError }
    }
}
