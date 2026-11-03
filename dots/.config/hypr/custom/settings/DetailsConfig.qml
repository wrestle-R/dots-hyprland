import QtQuick
import QtQuick.Layouts
import qs.modules.common
import qs.modules.common.widgets

ColumnLayout {
    spacing: 12
    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 20
        StyledText { text: "Advanced"; font.pixelSize: 23; font.weight: Font.Medium }
        Item { Layout.fillWidth: true }
        StyledComboBox {
            id: section
            buttonIcon: "tune"
            Layout.preferredWidth: 260
            Layout.fillWidth: false
            textRole: "name"
            model: [
                {name: "Bar & workspaces", file: "BarConfig.qml"},
                {name: "Background & clock", file: "BackgroundConfig.qml"},
                {name: "Interface & fonts", file: "InterfaceConfig.qml"},
                {name: "Color generation", file: "AdvancedConfig.qml"},
                {name: "About", file: "About.qml"}
            ]
        }
    }
    Loader {
        Layout.fillWidth: true
        Layout.fillHeight: true
        source: section.model[section.currentIndex]?.file || "BarConfig.qml"
    }
}
