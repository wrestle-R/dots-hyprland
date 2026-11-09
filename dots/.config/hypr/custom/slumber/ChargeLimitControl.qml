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
    border.width: 1; border.color: Appearance.colors.colLayer2
    ColumnLayout {
        id: column
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
        spacing: 12
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            MaterialSymbol { text: "battery_charging_full"; iconSize: 24; color: Appearance.colors.colOnLayer0 }
            StyledText { text: "Battery care"; font.pixelSize: Appearance.font.pixelSize.small }
            Item { Layout.fillWidth: true }
            StyledText { text: ChargeLimit.supported ? "Limit " + ChargeLimit.actual + "%" : "Unsupported"; font.pixelSize: Appearance.font.pixelSize.smaller; color: Appearance.colors.colSubtext }
            StyledSwitch { checked: ChargeLimit.enabled; enabled: ChargeLimit.supported && !ChargeLimit.busy; onClicked: ChargeLimit.apply(checked) }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 12
            StyledSlider {
                Layout.fillWidth: true; Layout.minimumWidth: 70
                configuration: StyledSlider.Configuration.XS; usePercentTooltip: false
                from: 55; to: 95; stepSize: 5; value: ChargeLimit.requested
                onMoved: ChargeLimit.requested = Math.round(value)
                enabled: ChargeLimit.supported && !ChargeLimit.busy
            }
            StyledText { text: ChargeLimit.requested + "%"; font.pixelSize: Appearance.font.pixelSize.smallie }
            RippleButton {
                Layout.preferredWidth: 70; Layout.preferredHeight: 32; buttonRadius: 16
                enabled: ChargeLimit.supported && !ChargeLimit.busy
                colBackground: Appearance.colors.colLayer2
                onClicked: ChargeLimit.apply(true)
                contentItem: StyledText { text: ChargeLimit.busy ? "…" : "Apply"; font.pixelSize: Appearance.font.pixelSize.smaller; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                StyledToolTip { text: "Apply selected charge limit. Authentication required." }
            }
        }
        StyledText {
            Layout.fillWidth: true
            text: ChargeLimit.statusLabel
            font.pixelSize: Appearance.font.pixelSize.smaller
            color: Appearance.colors.colSubtext
            wrapMode: Text.Wrap
            StyledToolTip { text: ChargeLimit.explanation }
        }
        StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; visible: ChargeLimit.error.length > 0; text: ChargeLimit.error; font.pixelSize: Appearance.font.pixelSize.smaller; color: Appearance.colors.colError }
    }
}
