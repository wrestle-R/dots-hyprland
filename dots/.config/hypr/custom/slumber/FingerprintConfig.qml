import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.common
import qs.modules.common.widgets

ContentPage {
    id: root
    forceWidth: true
    baseWidth: Math.max(280, Math.min(660, width - 40))
    property string helperPath: Quickshell.env("XDG_CONFIG_HOME")
        ? Quickshell.env("XDG_CONFIG_HOME") + "/quickshell/ii/services/fingerprint_settings.py"
        : Quickshell.env("HOME") + "/.config/quickshell/ii/services/fingerprint_settings.py"
    property var enrolled: []
    property bool available: false
    property string deviceName: "Checking the reader…"
    property string message: ""
    property bool failed: false
    property string action: "status"
    property string activeFinger: ""
    property int completed: 0
    property int stages: 1
    property bool receivedState: false
    property bool cancelling: false
    property string confirmation: ""
    property string pendingFinger: ""
    readonly property bool busy: worker.running
    readonly property var fingers: [
        "left-thumb", "left-index-finger", "left-middle-finger", "left-ring-finger", "left-little-finger",
        "right-thumb", "right-index-finger", "right-middle-finger", "right-ring-finger", "right-little-finger"
    ]
    readonly property var remaining: fingers.filter(finger => enrolled.indexOf(finger) < 0)

    function label(finger) {
        const words = finger.replace(/-finger$/, "").replace(/-/g, " ");
        return words.charAt(0).toUpperCase() + words.slice(1);
    }
    function request(which, finger = "") {
        if (busy) return;
        action = which;
        activeFinger = finger;
        message = which === "enroll" ? "Waiting for the reader…" : "";
        failed = false;
        receivedState = false;
        cancelling = false;
        completed = 0;
        confirmation = "";
        worker.command = ["python3", helperPath, which].concat(finger ? [finger] : []);
        worker.running = true;
    }
    function cancelEnrollment() {
        if (busy && action === "enroll" && !cancelling) { cancelling = true; worker.signal(15); }
    }
    function receive(line) {
        try {
            const data = JSON.parse(line);
            if (data.event === "state") {
                receivedState = true;
                available = data.available;
                enrolled = data.enrolled;
                deviceName = data.device;
                stages = data.stages;
                if (action === "remove") message = label(activeFinger) + " removed.";
            } else {
                message = data.message || "";
                failed = !data.ok;
                if (data.event === "error" && action === "status") { available = false; deviceName = "Fingerprint reader unavailable"; }
                if (data.event === "progress") {
                    completed = data.completed;
                    stages = data.stages;
                }
            }
        } catch (error) {
            failed = true;
            message = "Could not read the fingerprint service response. Try Refresh.";
        }
    }
    Component.onCompleted: request("status")
    Component.onDestruction: { if (worker.running) worker.signal(15); }

    Process {
        id: worker
        stdout: SplitParser { onRead: line => root.receive(line) }
        stderr: StdioCollector {}
        onExited: (exitCode, exitStatus) => {
            if (!root.receivedState && !root.failed) {
                root.failed = true;
                root.message = "The fingerprint request stopped. Refresh to check the reader.";
            }
        }
    }

    ContentSection {
        icon: "fingerprint"
        title: "Fingerprint"
        StyledText {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Use your finger to unlock the screen or approve a terminal request. Your password stays available. The login screen uses your password."
            color: Appearance.colors.colSubtext
            textFormat: Text.PlainText
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 16
            spacing: 12
            MaterialSymbol { text: "sensors"; iconSize: 26; color: Appearance.colors.colPrimary }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.deviceName; textFormat: Text.PlainText }
                StyledText {
                    text: root.busy && root.action === "status" ? "Checking availability…" : root.available ? root.enrolled.length + (root.enrolled.length === 1 ? " finger saved" : " fingers saved") : "Reader unavailable"
                    color: Appearance.colors.colSubtext
                    font.pixelSize: Appearance.font.pixelSize.small
                }
            }
            RippleButtonWithIcon {
                objectName: "refreshFingerprints"
                materialIcon: "refresh"; mainText: "Refresh"
                enabled: !root.busy
                onClicked: root.request("status")
            }
        }
    }

    ContentSection {
        title: "Saved fingers"
        StyledText {
            visible: root.enrolled.length === 0
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: root.busy && root.action === "status" ? "Reading your saved fingers…" : root.available ? "No fingerprints yet. Add a finger below to get started." : "Connect a fingerprint reader, then refresh."
            color: Appearance.colors.colSubtext
        }
        Repeater {
            model: root.enrolled
            delegate: Rectangle {
                required property string modelData
                Layout.fillWidth: true
                implicitHeight: fingerRow.implicitHeight + 24
                color: Appearance.colors.colLayer1
                radius: Appearance.rounding.small
                GridLayout {
                    id: fingerRow
                    anchors { fill: parent; margins: 12 }
                    columns: root.baseWidth < 480 ? 1 : 2
                    columnSpacing: 12
                    rowSpacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        MaterialSymbol { text: "fingerprint"; iconSize: 28; color: Appearance.colors.colPrimary }
                        StyledText { Layout.fillWidth: true; text: root.label(modelData); wrapMode: Text.Wrap }
                    }
                    RowLayout {
                        Layout.alignment: Qt.AlignRight
                        spacing: 8
                        RippleButtonWithIcon {
                            materialIcon: "edit"; mainText: "Replace"
                            enabled: !root.busy
                            Accessible.name: "Replace " + root.label(modelData)
                            onClicked: { root.pendingFinger = modelData; root.confirmation = "replace"; }
                        }
                        RippleButtonWithIcon {
                            objectName: "removeFingerprint-" + modelData
                            materialIcon: "delete"; mainText: "Remove"
                            enabled: !root.busy
                            Accessible.name: "Remove " + root.label(modelData)
                            onClicked: { root.pendingFinger = modelData; root.confirmation = "remove"; }
                        }
                    }
                }
            }
        }
        ColumnLayout {
            visible: root.confirmation.length > 0
            Layout.fillWidth: true
            Layout.topMargin: 8
            spacing: 8
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: root.confirmation === "remove"
                    ? "Remove " + root.label(root.pendingFinger).toLowerCase() + "? You can add it again later."
                    : "Record a new scan for " + root.label(root.pendingFinger).toLowerCase() + "? Follow the reader instructions to replace it."
            }
            RowLayout {
                RippleButtonWithIcon {
                    objectName: "confirmFingerprintAction"
                    materialIcon: root.confirmation === "remove" ? "delete" : "fingerprint"
                    mainText: root.confirmation === "remove" ? "Remove finger" : "Start new scan"
                    onClicked: root.request(root.confirmation === "remove" ? "remove" : "enroll", root.pendingFinger)
                }
                RippleButtonWithIcon { materialIcon: "close"; mainText: "Keep current scan"; onClicked: root.confirmation = "" }
            }
        }
    }

    ContentSection {
        title: root.busy && root.action === "enroll" ? "Scanning " + root.label(root.activeFinger).toLowerCase() : "Add a finger"
        GridLayout {
            columns: root.baseWidth < 480 ? 1 : 2
            visible: !(root.busy && root.action === "enroll")
            Layout.fillWidth: true
            columnSpacing: 12
            rowSpacing: 10
            StyledComboBox {
                id: fingerChoice
                objectName: "fingerChoice"
                Layout.fillWidth: true
                model: root.remaining.map(finger => ({name: root.label(finger), finger: finger}))
                textRole: "name"
                buttonIcon: "front_hand"
                enabled: root.available && !root.busy && root.remaining.length > 0
                Accessible.name: "Finger to enroll"
            }
            RippleButtonWithIcon {
                objectName: "addFingerprint"
                materialIcon: "add"; mainText: "Add finger"
                enabled: root.available && !root.busy && fingerChoice.currentIndex >= 0 && root.remaining.length > 0
                onClicked: root.request("enroll", root.remaining[fingerChoice.currentIndex])
            }
        }
        StyledText {
            visible: root.remaining.length === 0
            text: "All ten fingers are saved. Replace an existing scan above."
            Layout.fillWidth: true; wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
        }
        ColumnLayout {
            visible: root.busy && root.action === "enroll"
            Layout.fillWidth: true
            spacing: 14
            MaterialSymbol { Layout.alignment: Qt.AlignHCenter; text: "fingerprint"; iconSize: 64; color: Appearance.colors.colPrimary }
            StyledProgressBar { Layout.fillWidth: true; from: 0; to: root.stages; value: root.completed; Accessible.name: "Fingerprint scan progress" }
            RowLayout {
                Layout.fillWidth: true
                StyledText { Layout.fillWidth: true; text: root.completed + " of " + root.stages + " scans"; color: Appearance.colors.colSubtext }
                RippleButtonWithIcon {
                    objectName: "cancelEnrollment"
                    materialIcon: "close"; mainText: root.cancelling ? "Stopping…" : "Cancel"
                    enabled: !root.cancelling
                    onClicked: root.cancelEnrollment()
                }
            }
        }
        StyledText {
            objectName: "fingerprintMessage"
            visible: root.message.length > 0
            Layout.fillWidth: true
            Layout.topMargin: 8
            wrapMode: Text.WordWrap
            text: root.message
            textFormat: Text.PlainText
            color: root.failed ? Appearance.m3colors.m3error : Appearance.colors.colPrimary
            Accessible.role: Accessible.AlertMessage
        }
        StyledText {
            Layout.fillWidth: true
            Layout.topMargin: 8
            wrapMode: Text.WordWrap
            text: "Use a clean, dry finger. Lift it between scans and vary the angle slightly. Saved scans stay in the system fingerprint service."
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.small
        }
    }
}
