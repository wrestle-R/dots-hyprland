import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io

Rectangle {
    id: root
    objectName: "spotifyMiniPlayer"
    property bool active: false
    // Optional fixture data is only used by the isolated documentation preview.
    property var previewState: null
    property var player: ({ok: false, message: "Open Spotify TUI to start listening"})
    property string errorText: ""
    readonly property var current: previewState ?? player
    readonly property bool ready: current.ok && current.connected && current.logged_in && !current.needs_reconnect
    readonly property bool playing: current.status === "playing"
    readonly property bool busy: action.running
    readonly property color green: "#1ed760"
    readonly property string helperPath: FileUtils.trimFileProtocol(`${Directories.config}/hypr/custom/scripts/spotify-sidebar.py`)
    implicitHeight: content.implicitHeight + 24
    radius: 15
    color: Appearance.colors.colLayer1
    border.color: Appearance.colors.colLayer0Border

    component PlayerButton: RippleButton {
        focusPolicy: Qt.StrongFocus
        colBackground: activeFocus ? Appearance.colors.colLayer1Hover : "transparent"
    }

    function timeLabel(ms) {
        const seconds = Math.floor(Math.max(0, ms || 0) / 1000);
        return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
    }
    function run(method, value) {
        if (busy || previewState !== null) return;
        errorText = "";
        action.command = ["python3", helperPath, method, ...(value === undefined ? [] : [String(value)])];
        action.running = true;
    }
    onActiveChanged: {
        restart.stop();
        watcher.running = active && previewState === null;
    }
    onPreviewStateChanged: { watcher.running = active && previewState === null; }
    Process {
        id: watcher
        command: ["python3", root.helperPath, "watch"]
        running: root.active && root.previewState === null
        stdout: SplitParser {
            onRead: line => {
                try { root.player = JSON.parse(line); }
                catch (error) { root.player = {ok: false, message: "Playback state unavailable"}; }
            }
        }
        onExited: {
            root.player = {ok: false, message: "Playback state unavailable"};
            if (root.active && root.previewState === null) restart.restart();
        }
    }
    Timer {
        id: restart
        interval: 3000
        onTriggered: { if (root.active && root.previewState === null) watcher.running = true; }
    }
    Process {
        id: action
        onStarted: deadline.restart()
        onExited: (code, status) => {
            deadline.stop();
            if (code !== 0 && !root.errorText) root.errorText = "Could not reach player. Open it and press c to reconnect.";
        }
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    if (!result.ok) root.errorText = result.message || "Playback command failed";
                } catch (error) { root.errorText = "Playback command failed"; }
            }
        }
    }
    Timer {
        id: deadline
        interval: 12000
        onTriggered: {
            root.errorText = "Player took too long. Open it and press c to reconnect.";
            action.running = false;
        }
    }

    ColumnLayout {
        id: content
        anchors { fill: parent; margins: 12 }
        spacing: 6
        RowLayout {
            Layout.fillWidth: true
            spacing: 7
            MaterialSymbol { text: "music_note"; iconSize: 19; color: root.green }
            StyledText {
                text: "Spotify TUI"
                font.pixelSize: 12
                font.weight: Font.DemiBold
            }
            StyledText {
                Layout.fillWidth: true
                text: root.busy ? "Working…" : !root.ready ? "" : root.playing ? "Playing" : root.current.status === "paused" ? "Paused" : root.current.status === "buffering" ? "Buffering…" : "Ready"
                font.pixelSize: 11
                color: Appearance.colors.colSubtext
            }
            PlayerButton {
                objectName: "openSpotifyPlayer"
                implicitWidth: 110
                implicitHeight: 28
                enabled: !root.busy
                Accessible.name: "Open Spotify TUI"
                onClicked: root.run("open")
                contentItem: StyledText {
                    text: "Open player  ↗"
                    font.pixelSize: 11
                    color: root.green
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                SidebarToolTip { horizontalBounds: root; visible: root.active && parent.hovered; text: "Open player, or focus its existing window" }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 7
            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 2
                StyledText {
                    objectName: "spotifyTrackTitle"
                    Layout.fillWidth: true
                    text: root.current.title || "Your music, right here"
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }
                StyledText {
                    Layout.fillWidth: true
                    text: root.current.artist || (root.ready ? "Pick a song in the player" : "Open player to get started")
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    font.pixelSize: 11
                    color: Appearance.colors.colSubtext
                }
            }
            PlayerButton {
                objectName: "spotifyPrevious"
                implicitWidth: 31; implicitHeight: 36
                enabled: root.ready && !root.busy
                Accessible.name: "Previous song"
                onClicked: root.run("previous")
                contentItem: MaterialSymbol { text: "skip_previous"; iconSize: 23; horizontalAlignment: Text.AlignHCenter }
                SidebarToolTip { horizontalBounds: root; visible: root.active && parent.hovered; text: "Previous song" }
            }
            PlayerButton {
                objectName: "spotifyPlayPause"
                implicitWidth: 37; implicitHeight: 37
                enabled: root.ready && !root.busy
                Accessible.name: root.playing ? "Pause" : "Resume"
                onClicked: root.run("toggle_pause")
                contentItem: MaterialSymbol {
                    text: root.playing ? "pause" : "play_arrow"
                    iconSize: 27
                    color: root.green
                    horizontalAlignment: Text.AlignHCenter
                }
                SidebarToolTip { horizontalBounds: root; visible: root.active && parent.hovered; text: root.playing ? "Pause" : "Resume" }
            }
            PlayerButton {
                objectName: "spotifyNext"
                implicitWidth: 31; implicitHeight: 36
                enabled: root.ready && !root.busy
                Accessible.name: "Next song"
                onClicked: root.run("next")
                contentItem: MaterialSymbol { text: "skip_next"; iconSize: 23; horizontalAlignment: Text.AlignHCenter }
                SidebarToolTip { horizontalBounds: root; visible: root.active && parent.hovered; text: "Next song" }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 7
            StyledText { text: root.timeLabel(root.current.position_ms); font.pixelSize: 10; color: Appearance.colors.colSubtext }
            Slider {
                id: progress
                objectName: "spotifySeek"
                Layout.fillWidth: true
                implicitHeight: 22
                from: 0
                to: Math.max(1, root.current.duration_ms || 0)
                value: root.current.position_ms || 0
                stepSize: 1000
                live: false
                focusPolicy: Qt.StrongFocus
                enabled: root.ready && !root.busy && root.current.duration_ms > 0
                Accessible.name: "Song position"
                onMoved: root.run("seek", Math.round(value))
                background: Rectangle {
                    x: progress.leftPadding
                    y: progress.topPadding + (progress.availableHeight - height) / 2
                    width: progress.availableWidth
                    height: 3
                    radius: 2
                    color: Appearance.colors.colLayer0Border
                    Rectangle { width: progress.visualPosition * parent.width; height: parent.height; radius: 2; color: root.green }
                }
                handle: Rectangle {
                    x: progress.leftPadding + progress.visualPosition * (progress.availableWidth - width)
                    y: progress.topPadding + (progress.availableHeight - height) / 2
                    width: 9; height: 9; radius: 5
                    color: progress.activeFocus || progress.hovered || progress.pressed ? root.green : "transparent"
                }
            }
            StyledText { text: root.timeLabel(root.current.duration_ms); font.pixelSize: 10; color: Appearance.colors.colSubtext }
        }
        StyledText {
            Layout.fillWidth: true
            visible: text.length > 0
            text: root.errorText || (!root.current.ok ? root.current.message || "Player unavailable" : !root.ready ? "Open player and press c to reconnect" : "")
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            font.pixelSize: 11
            color: Appearance.colors.colSubtext
        }
    }
}
