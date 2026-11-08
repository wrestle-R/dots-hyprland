import QtQuick
import Quickshell.Io
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.widgets

ContentPage {
    id: root
    forceWidth: true
    property var appNames: []
    property var knownApps: [...new Set([...appNames, ...Slumber.hiddenApps])].sort()
    FileView {
        path: Directories.notificationsPath
        watchChanges: true
        onFileChanged: reload()
        onLoaded: { try { root.appNames = JSON.parse(text()).map(n => n.appName); } catch(e) { root.appNames = []; } }
    }
    ContentSection {
        icon: "notifications"
        title: "Notifications"
        ContentSubsection {
            title: "Lockscreen visibility"
            tooltip: "Notifications show sender and message while locked. Hidden apps also cannot wake the screen during Slumber."
            StyledText {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "Choose which apps may show notifications while locked. New apps are visible by default. Apps appear here after they send a notification."
                font.pixelSize: 13
            }
            Repeater {
                model: root.knownApps
                delegate: ConfigSwitch {
                    required property string modelData
                    text: modelData || "Unknown app"
                    buttonIcon: "notifications"
                    checked: Slumber.hiddenApps.indexOf(modelData) < 0
                    onClicked: Slumber.hideApp(modelData, Slumber.hiddenApps.indexOf(modelData) < 0)
                }
            }
            StyledText { visible: root.knownApps.length === 0; text: "No apps have sent notifications yet."; font.pixelSize: 13 }
        }
        ContentSubsection {
            title: "Slumber"
            StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Allowed notifications wake an open display for 6 seconds. Typing or clicking gives you 30 seconds to unlock. The built-in display stays off with the lid closed. Do Not Disturb prevents notification wakes."; font.pixelSize: 13 }
        }
    }
}
