import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io

ColumnLayout {
    id: root
    property bool active: false
    property var usage: null
    property string errorText: ""
    readonly property color accent: "#ff914d"
    readonly property string helperPath: FileUtils.trimFileProtocol(`${Directories.config}/hypr/custom/scripts/hyprtrack-summary.py`)
    property int selectedDay: -1
    readonly property var days: usage?.days ?? []
    spacing: 14

    function formatTime(minutes) {
        const value = Math.max(0, Math.floor(minutes));
        return value >= 60 ? `${Math.floor(value / 60)}h ${String(value % 60).padStart(2, "0")}m` : `${value}m`;
    }
    function refresh() {
        if (active && !reader.running) reader.running = true;
    }
    onActiveChanged: { if (active) refresh(); }
    onUsageChanged: chart.requestPaint()
    onSelectedDayChanged: chart.requestPaint()
    Component.onCompleted: refresh()

    Timer {
        interval: 15000
        repeat: true
        running: root.active
        onTriggered: root.refresh()
    }
    Process {
        id: reader
        command: ["python3", root.helperPath]
        onStarted: timeout.restart()
        onExited: (code, status) => {
            timeout.stop();
            if (code !== 0) {
                root.usage = null;
                if (!root.errorText) root.errorText = "Usage unavailable";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    if (!result.ok || !Array.isArray(result.days) || result.days.length !== 7)
                        throw new Error("Unavailable");
                    root.errorText = "";
                    root.usage = result;
                } catch (error) {
                    root.usage = null;
                    root.errorText = "Usage unavailable";
                }
            }
        }
    }
    Timer {
        id: timeout
        interval: 5000
        onTriggered: {
            reader.running = false;
            root.usage = null;
            root.errorText = "Usage request timed out";
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        Image {
            Layout.preferredWidth: 34
            Layout.preferredHeight: 34
            source: Qt.resolvedUrl("hyprtrack-logo.svg")
            sourceSize.width: 68
            sourceSize.height: 68
            fillMode: Image.PreserveAspectFit
        }
        StyledText {
            Layout.fillWidth: true
            text: "HyprTrack"
            font.pixelSize: 22
            font.weight: Font.DemiBold
        }
        StyledText {
            text: "Last 7 days"
            font.pixelSize: 12
            color: Appearance.colors.colSubtext
        }
        RippleButton {
            objectName: "openHyprTrack"
            implicitWidth: 32
            implicitHeight: 32
            Accessible.name: "Open HyprTrack"
            onClicked: Quickshell.execDetached([FileUtils.trimFileProtocol(`${Directories.home}/.local/bin/hyprtrack-desktop.AppImage`)])
            contentItem: MaterialSymbol {
                text: "arrow_outward"
                iconSize: 21
                horizontalAlignment: Text.AlignHCenter
                color: Appearance.colors.colSubtext
            }
            StyledToolTip { text: "Open HyprTrack" }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 4
        spacing: 20
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3
            StyledText {
                objectName: "hyprtrackToday"
                text: root.usage ? root.formatTime(root.usage.todayMinutes) : "—"
                font.pixelSize: 28
                font.weight: Font.DemiBold
            }
            StyledText {
                text: "Today’s usage"
                font.pixelSize: 13
                color: Appearance.colors.colSubtext
            }
        }
        Rectangle {
            Layout.preferredWidth: 1
            Layout.preferredHeight: 41
            color: Appearance.colors.colLayer0Border
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3
            StyledText {
                objectName: "hyprtrackAverage"
                text: root.usage ? root.formatTime(root.usage.averageMinutes) : "—"
                font.pixelSize: 28
                font.weight: Font.DemiBold
            }
            StyledText {
                text: "Daily average"
                font.pixelSize: 13
                color: Appearance.colors.colSubtext
            }
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 82
            Accessible.role: Accessible.Graphic
            Accessible.name: "Usage over the last seven days"
            Accessible.description: root.days.map(day => `${day.date}: ${root.formatTime(day.minutes)}`).join(", ")
            Canvas {
                id: chart
                anchors.fill: parent
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx = getContext("2d");
                    ctx.reset();
                    const left = 18, right = width - 18, top = 8, bottom = height - 10;
                    ctx.strokeStyle = Appearance.colors.colLayer0Border;
                    ctx.lineWidth = 1;
                    for (let i = 0; i < 3; i++) {
                        const y = top + (bottom - top) * i / 2;
                        ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
                    }
                    if (root.days.length !== 7) return;
                    const max = Math.max(60, ...root.days.map(day => day.minutes));
                    const points = root.days.map((day, i) => ({x: left + i * (right - left) / 6,
                        y: bottom - day.minutes / max * (bottom - top)}));
                    ctx.lineWidth = 2.5;
                    ctx.lineJoin = "round";
                    ctx.lineCap = "round";
                    ctx.strokeStyle = root.accent;
                    ctx.beginPath();
                    points.forEach((point, i) => i === 0 ? ctx.moveTo(point.x, point.y) : ctx.lineTo(point.x, point.y));
                    ctx.stroke();
                    points.forEach((point, i) => {
                        ctx.beginPath(); ctx.arc(point.x, point.y, i === root.selectedDay ? 4.5 : 3, 0, Math.PI * 2);
                        ctx.fillStyle = i === 6 || i === root.selectedDay ? root.accent : Appearance.colors.colLayer0;
                        ctx.fill(); ctx.lineWidth = 1.5; ctx.stroke();
                    });
                }
            }
            MouseArea {
                id: chartMouse
                anchors.fill: parent
                hoverEnabled: true
                onPositionChanged: mouse => root.selectedDay = Math.max(0, Math.min(6, Math.round((mouse.x - 18) / (width - 36) * 6)))
                onExited: root.selectedDay = -1
                ToolTip.visible: containsMouse && root.days.length === 7
                ToolTip.text: root.selectedDay >= 0 && root.days.length === 7
                    ? `${root.days[root.selectedDay].date} · ${root.formatTime(root.days[root.selectedDay].minutes)}` : ""
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: root.days
                StyledText {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData.label
                    font.pixelSize: 11
                    color: index === 6 ? root.accent : Appearance.colors.colSubtext
                }
            }
        }
    }
    StyledText {
        Layout.fillWidth: true
        text: root.errorText || (!root.usage ? "Loading usage…" : "")
        visible: text.length > 0
        font.pixelSize: 12
        color: Appearance.colors.colSubtext
    }
    StyledText {
        Layout.fillWidth: true
        text: "No recent activity"
        visible: root.usage?.quiet ?? false
        font.pixelSize: 11
        color: Appearance.colors.colSubtext
    }
    HoverHandler { id: summaryHover }
    ToolTip.visible: summaryHover.hovered && !chartMouse.containsMouse && root.usage !== null
    ToolTip.delay: 1200
    ToolTip.text: "Daily average covers days with recorded usage in the last 7 days, including today. Times use IST."
}
