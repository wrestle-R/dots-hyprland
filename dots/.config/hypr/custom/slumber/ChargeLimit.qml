pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root
    property bool supported: false
    property bool enabled: false
    property int actual: 100
    property int requested: 95
    property string error: ""
    property bool busy: setter.running
    function refresh() { if (!reader.running) reader.running = true; }
    function apply(on) {
        if (setter.running || !supported) return;
        error = "";
        setter.command = ["pkexec", "/usr/local/libexec/rdp-charge-limit", on ? "apply" : "off", String(requested)];
        setter.running = true;
    }
    Component.onCompleted: refresh()
    Timer { interval: 15000; running: true; repeat: true; onTriggered: root.refresh() }
    Process {
        id: reader
        command: ["python3", Quickshell.shellPath("services/slumber_backend.py"), "battery-status"]
        stdout: StdioCollector {
            onStreamFinished: {
                try { const data = JSON.parse(text); root.supported = data.supported; root.actual = data.batteries.length ? data.batteries[0].end : 100; root.enabled = root.actual < 100; }
                catch (e) { root.supported = false; }
            }
        }
    }
    Process {
        id: setter
        stdout: StdioCollector {}
        stderr: StdioCollector {}
        onExited: (code, status) => {
            root.refresh();
            if (code !== 0) root.error = "Charge limit was not changed. Authentication may have been cancelled; previous limits retained.";
        }
    }
}
