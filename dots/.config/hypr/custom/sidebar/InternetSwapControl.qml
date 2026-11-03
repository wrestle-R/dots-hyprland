import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io

RowLayout {
    id: root
    objectName: "internetSwapControl"
    property bool active: false
    property var state: ({ok: false})
    property string errorText: ""
    readonly property string helperPath: FileUtils.trimFileProtocol(`${Directories.config}/hypr/custom/scripts/internet-swap-sidebar.py`)
    readonly property var current: state.networks?.find(n => n.uuid === state.current)
    spacing: 8
    function run(command) {
        if (action.running) return;
        errorText = "";
        action.command = ["python3", helperPath, command];
        action.running = true;
    }
    onActiveChanged: {
        retry.stop();
        watcher.running = active;
        if (!active) state = {ok: false};
    }
    Process {
        id: watcher
        command: ["python3", root.helperPath, "watch"]
        running: root.active
        stdout: SplitParser {
            onRead: line => {
                try { root.state = JSON.parse(line); }
                catch (error) { root.state = {ok: false}; }
            }
        }
        onExited: {
            root.state = {ok: false};
            if (root.active) retry.restart();
        }
    }
    Timer { id: retry; interval: 3000; onTriggered: { if (root.active) watcher.running = true; } }
    Process {
        id: action
        stdout: StdioCollector {
            onStreamFinished: {
                try { const result = JSON.parse(text); if (!result.ok) root.errorText = result.message || "Action failed"; }
                catch (error) { root.errorText = "Internet Swap is unavailable"; }
            }
        }
    }
    MaterialSymbol {
        text: "wifi"
        iconSize: 17
        color: root.state.ok && root.state.enabled ? "#ff914d" : Appearance.colors.colSubtext
    }
    StyledText {
        text: "Wi-Fi"
        font.pixelSize: 12
        color: Appearance.colors.colSubtext
    }
    StyledText {
        Layout.fillWidth: true
        text: root.state.ok ? (root.current?.name || "Not connected") : "Swap unavailable"
        elide: Text.ElideRight
        font.pixelSize: 12
        color: Appearance.colors.colOnLayer0
    }
    RippleButton {
        objectName: "toggleInternetSwap"
        implicitWidth: 40
        implicitHeight: 26
        enabled: root.state.ok && !action.running
        Accessible.name: root.state.enabled ? "Turn automatic Wi-Fi switching off" : "Turn automatic Wi-Fi switching on"
        onClicked: root.run(root.state.enabled ? "disable" : "enable")
        contentItem: StyledText {
            text: root.state.ok ? (root.state.enabled ? "On" : "Off") : "—"
            font.pixelSize: 11
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            color: root.state.enabled ? "#ff914d" : Appearance.colors.colSubtext
        }
    }
    RippleButton {
        objectName: "openInternetSwap"
        implicitWidth: 26
        implicitHeight: 26
        Accessible.name: "Open Internet Swap"
        onClicked: root.run("open")
        contentItem: MaterialSymbol { text: "arrow_outward"; iconSize: 17; horizontalAlignment: Text.AlignHCenter; color: Appearance.colors.colSubtext }
    }
    HoverHandler { id: hover }
    SidebarToolTip {
        horizontalBounds: root
        visible: root.active && hover.hovered
        heading: "Internet Swap"
        text: root.errorText || (root.state.ok ? ((root.state.enabled ? "Automatic switching on. " : "Automatic switching off. ") + (root.state.message || "") + "\nSwitching can interrupt active requests. USB is outside selection logic.") : "Start or install Internet Swap. Live traffic above still works independently.")
    }
}
