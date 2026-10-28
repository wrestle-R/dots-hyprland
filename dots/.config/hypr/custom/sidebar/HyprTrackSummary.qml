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
    property var speed: null
    readonly property color accent: "#ff914d"
    readonly property string helperPath: FileUtils.trimFileProtocol(`${Directories.config}/hypr/custom/scripts/hyprtrack-summary.py`)
    property int selectedDay: -1
    readonly property var days: usage?.days ?? []
    spacing: 14

    function formatTime(minutes) {
        const value = Math.max(0, Math.floor(minutes));
        return value >= 60 ? `${Math.floor(value / 60)}h ${String(value % 60).padStart(2, "0")}m` : `${value}m`;
    }
    function formatBytes(bytes) {
        if (bytes === null || bytes === undefined || !Number.isFinite(bytes)) return "—";
        const units = ["B", "KB", "MB", "GB", "TB"];
        let value = Math.max(0, bytes), unit = 0;
        while (value >= 1000 && unit < units.length - 1) { value /= 1000; unit++; }
        return `${value.toFixed(unit === 0 || value >= 100 ? 0 : 1)} ${units[unit]}`;
    }
    function refresh() {
        if (active && !reader.running) reader.running = true;
    }
    onActiveChanged: {
        root.speed = null;
        speedRestart.stop();
        speedReader.running = active;
        if (active) refresh();
    }
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

    Process {
        id: speedReader
        command: ["python3", root.helperPath, "--watch-speed"]
        running: root.active
        stdout: SplitParser {
            onRead: line => {
                try { root.speed = JSON.parse(line); }
                catch (error) { root.speed = null; }
            }
        }
        onExited: {
            root.speed = null;
            if (root.active) speedRestart.restart();
        }
    }
    Timer {
        id: speedRestart
        interval: 3000
        onTriggered: { if (root.active) speedReader.running = true; }
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
            SidebarToolTip { horizontalBounds: root; visible: root.active && parent.hovered; text: "Open HyprTrack" }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 4
        spacing: 12
        Repeater {
            model: [
                { key: "hyprtrackToday", value: root.usage ? root.formatTime(root.usage.todayMinutes) : "—", label: "Today’s usage", hint: "Screen time recorded today. Resets at midnight IST." },
                { key: "hyprtrackAverage", value: root.usage ? root.formatTime(root.usage.averageMinutes) : "—", label: "Daily average", hint: "Average across days with recorded usage in the last 7 days, including today. Times use IST." },
                { key: "hyprtrackInternet", value: root.usage ? root.formatBytes(root.usage.todayInternetBytes) : "—", label: "Today’s internet", hint: "Today’s downloads + uploads across apps and services, using IST. A dash means internet data is unavailable." }
            ]
            ColumnLayout {
                id: metric
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                spacing: 4
                StyledText {
                    objectName: modelData.key
                    Layout.fillWidth: true
                    text: modelData.value
                    font.pixelSize: 23
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                StyledText {
                    Layout.fillWidth: true
                    text: modelData.label
                    font.pixelSize: 11
                    color: Appearance.colors.colSubtext
                    elide: Text.ElideRight
                }
                HoverHandler { id: metricHover }
                SidebarToolTip {
                    horizontalBounds: root
                    visible: root.active && metricHover.hovered
                    heading: metric.modelData.label
                    text: metric.modelData.hint
                }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        id: speedRow
        Layout.topMargin: 2
        spacing: 8
        MaterialSymbol {
            text: "swap_vert"
            iconSize: 19
            color: Appearance.colors.colSubtext
        }
        StyledText {
            text: "Live"
            font.pixelSize: 12
            color: Appearance.colors.colSubtext
        }
        Item { Layout.fillWidth: true }
        StyledText {
            objectName: "hyprtrackDownloadSpeed"
            text: `↓ ${root.speed?.ready ? root.formatBytes(root.speed.rxBytesPerSecond) + "/s" : "—"}`
            font.pixelSize: 13
            font.weight: Font.Medium
            Accessible.name: `Download speed: ${text}`
        }
        StyledText {
            Layout.leftMargin: 10
            objectName: "hyprtrackUploadSpeed"
            text: `↑ ${root.speed?.ready ? root.formatBytes(root.speed.txBytesPerSecond) + "/s" : "—"}`
            font.pixelSize: 13
            font.weight: Font.Medium
            Accessible.name: `Upload speed: ${text}`
        }
        HoverHandler { id: speedHover }
        SidebarToolTip {
            horizontalBounds: root
            visible: root.active && speedHover.hovered
            heading: "Live transfer speed"
            text: "↓ Download  ·  ↑ Upload\nCurrent traffic, including LAN. Read locally once a second; no speed tests or internet requests."
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
                function selectAt(position) {
                    root.selectedDay = Math.max(0, Math.min(6, Math.round((position - 18) / Math.max(1, width - 36) * 6)));
                }
                onEntered: selectAt(mouseX)
                onPositionChanged: mouse => selectAt(mouse.x)
                onExited: root.selectedDay = -1
                SidebarToolTip {
                    horizontalBounds: root
                    id: chartTip
                    readonly property var day: root.selectedDay >= 0 ? root.days[root.selectedDay] : null
                    visible: root.active && chartMouse.containsMouse && root.days.length === 7 && day !== null
                    delay: 180
                    maximumWidth: 190
                    x: Math.max(0, Math.min(chartMouse.width - width,
                        18 + root.selectedDay * (chartMouse.width - 36) / 6 - width / 2))
                    heading: day ? Qt.formatDate(new Date(`${day.date}T12:00:00`), "ddd, d MMM yyyy") : ""
                    value: day ? root.formatTime(day.minutes) : ""
                    text: "Screen time · IST"
                }
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
}
