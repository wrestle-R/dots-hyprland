import QtQuick
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.widgets

ContentPage {
    forceWidth: true
    ContentSection {
        icon: "notifications"
        title: "Notifications"
        ContentSubsection {
            title: "Lockscreen visibility"
            tooltip: "Enabled apps show sender and message while locked and may wake Slumber."
            StyledText {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "Only T3 Code, Codex and Visual Studio Code are allowed on the lockscreen. All other apps stay hidden and cannot wake Slumber."
                font.pixelSize: Appearance.font.pixelSize.smallie
            }
            Repeater {
                model: [
                    {group: "t3code", label: "T3 Code"},
                    {group: "codex", label: "Codex / Multi Codex"},
                    {group: "vscode", label: "Visual Studio Code"}
                ]
                delegate: ConfigSwitch {
                    id: toggle
                    required property var modelData
                    text: modelData.label
                    buttonIcon: "notifications"
                    enabled: Slumber.ready
                    checked: Slumber.allowedApps.indexOf(modelData.group) >= 0
                    onClicked: Slumber.setAllowedApp(modelData.group, Slumber.allowedApps.indexOf(modelData.group) < 0)
                }
            }
        }
        ContentSubsection {
            title: "Slumber"
            StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Allowed notifications wake an open display for 6 seconds. Typing or clicking gives you 30 seconds to unlock. The built-in display stays off with the lid closed. Do Not Disturb prevents notification wakes."; font.pixelSize: Appearance.font.pixelSize.smallie }
        }
    }
}
