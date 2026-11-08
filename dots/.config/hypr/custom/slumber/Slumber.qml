pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs
import qs.services
import qs.modules.common

Singleton {
    id: root
    property bool ready: false
    property bool active: false
    property bool lockSecure: false
    property bool lidReady: false
    property bool lidClosed: false
    property bool dark: false
    property bool wantsDark: false
    property bool notificationWake: false
    property double lastNotificationWake: 0
    property string error: ""
    property string lidAction: "sleep"
    property list<string> hiddenApps: []
    readonly property string helper: Quickshell.shellPath("services/slumber_backend.py")
    readonly property string statePath: (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/quickshell/slumber.json"
    property bool settingsOnly: Quickshell.shellPath("shell.qml").toString().indexOf("settings.qml") >= 0
    // Settings process persists preferences; only the main shell owns hardware.
    property bool hardwareOwner: false
    function allowed(notification) { return notification && hiddenApps.indexOf(notification.appName) < 0; }
    function setLidAction(value) {
        if (value !== "sleep" && value !== "slumber") return;
        settings.lidAction = value;
        state.writeAdapter();
    }
    function hideApp(name, hidden) {
        let values = hiddenApps.filter(v => v !== name);
        if (hidden) values.push(name);
        settings.hiddenApps = values;
        state.writeAdapter();
    }
    function fail(message) {
        error = message;
        active = false;
        wantsDark = false;
        blankTimer.stop();
        lockTimeout.stop();
        dispatchDisplay();
        Quickshell.execDetached(["notify-send", "Slumber unavailable", message, "-u", "critical"]);
    }
    function enter() {
        if (!hardwareOwner || !ready) return;
        if (Config.options.lock.useHyprlock) {
            fail("Slumber needs the native QuickShell lock. Your normal lock is unchanged.");
            return;
        }
        error = "";
        active = true;
        GlobalStates.sidebarRightOpen = false;
        GlobalStates.sessionOpen = false;
        GlobalStates.screenLocked = true;
        lockTimeout.restart();
        beginIfSecure();
    }
    function beginIfSecure() {
        if (!active || !lockSecure || !lidReady) return;
        lockTimeout.stop();
        // Let the initiating shortcut/mouse release finish before DPMS off.
        blankTimer.interval = 700;
        blankTimer.restart();
    }
    function leave() {
        active = false;
        blankTimer.stop();
        lockTimeout.stop();
        wantsDark = false;
        dispatchDisplay();
    }
    function interact() {
        notificationWake = false;
        if (!active || !lockSecure || lidClosed) return;
        wantsDark = false;
        dispatchDisplay();
        blankTimer.interval = 30000;
        blankTimer.restart();
    }
    function dispatchDisplay() {
        if (!hardwareOwner || display.running) return;
        if (wantsDark && (!active || !lockSecure || !lidReady)) return;
        display.turningOff = wantsDark;
        display.command = ["python3", helper, wantsDark ? "disable" : "enable"];
        display.running = true;
    }
    onLockSecureChanged: beginIfSecure()
    onLidReadyChanged: beginIfSecure()
    FileView {
        id: state
        path: root.statePath
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            root.lidAction = settings.lidAction === "slumber" ? "slumber" : "sleep";
            root.hiddenApps = settings.hiddenApps;
            root.ready = true;
        }
        onLoadFailed: error => {
            if (error === FileViewError.FileNotFound) {
                root.ready = true;
                state.writeAdapter();
            } else {
                root.error = "Cannot read Slumber preferences; normal sleep retained";
                root.lidAction = "sleep";
            }
        }
        adapter: JsonAdapter {
            id: settings
            property string lidAction: "sleep"
            property list<string> hiddenApps: []
        }
    }
    Timer { id: lockTimeout; interval: 6000; onTriggered: root.fail("Lock or lid protection was not confirmed. Display stays on; normal sleep retained.") }
    Timer {
        id: blankTimer
        onTriggered: {
            root.notificationWake = false;
            if (root.active && root.lockSecure && root.lidReady) {
                root.wantsDark = true;
                root.dispatchDisplay();
            }
        }
    }
    Process {
        id: display
        property bool turningOff: false
        onExited: (code, status) => {
            if (code !== 0) {
                root.error = "Display command failed; Slumber stopped";
                root.active = false;
                root.wantsDark = false;
                blankTimer.stop();
                if (turningOff) root.dispatchDisplay();
                return;
            }
            root.dark = turningOff;
            if (root.wantsDark !== turningOff) root.dispatchDisplay();
        }
    }
    Process {
        id: lid
        running: root.hardwareOwner && root.ready && (root.lidAction === "slumber" || root.active)
        command: ["python3", root.helper, "watch-lid"]
        stdout: SplitParser {
            onRead: data => {
                try {
                    const value = JSON.parse(data);
                    if (value.error) { root.fail("Lid protection failed: " + value.error); return; }
                    const wasClosed = root.lidClosed;
                    root.lidClosed = value.closed;
                    root.lidReady = value.ready;
                    if (root.lidClosed && !wasClosed && root.lidAction === "slumber" && !root.active) root.enter();
                    if (root.active && root.lidClosed) { root.wantsDark = true; root.dispatchDisplay(); }
                    if (root.active && wasClosed && !root.lidClosed) root.interact();
                } catch (e) { root.fail("Invalid lid-helper response"); }
            }
        }
        onRunningChanged: { if (!running) root.lidReady = false; }
        onExited: (code, status) => {
            root.lidReady = false;
            if (root.hardwareOwner && (root.active || root.lidAction === "slumber")) {
                root.fail("Lid helper stopped. Normal lid sleep restored.");
                // Avoid automatic respawn loops after denial/errors.
                root.lidAction = "sleep";
            }
        }
    }
    Connections {
        target: GlobalStates
        function onScreenLockedChanged() { if (!GlobalStates.screenLocked && root.active) root.leave(); }
    }
    Connections {
        target: root.hardwareOwner ? Notifications : null
        function onNotify(notification) {
            if (!root.hardwareOwner || !root.active || !root.lockSecure || root.lidClosed || Notifications.silent || !root.allowed(notification)) return;
            // Do not cut short a user who is entering their password.
            if ((!root.dark && blankTimer.running && blankTimer.interval === 30000) || root.notificationWake || Date.now() - root.lastNotificationWake < 15000) return;
            root.notificationWake = true;
            root.lastNotificationWake = Date.now();
            root.wantsDark = false;
            root.dispatchDisplay();
            blankTimer.interval = 6000;
            blankTimer.restart();
        }
    }
    Timer {
        interval: 2000; repeat: true
        running: root.hardwareOwner && root.active && root.dark && !root.lidClosed
        onTriggered: { if (!monitorReader.running) monitorReader.running = true; }
    }
    Process {
        id: monitorReader
        command: ["hyprctl", "-j", "monitors"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    if (root.active && root.dark && root.wantsDark && !display.running && JSON.parse(text).some(m => m.dpmsStatus)) {
                        root.dark = false;
                        root.interact();
                    }
                } catch (e) { /* Failed reads do not change lock or power policy. */ }
            }
        }
    }
    IpcHandler {
        target: "slumber"
        function activate(): void { root.enter(); }
        function status(): string { return JSON.stringify({active:root.active, secure:root.lockSecure, lidAction:root.lidAction, lidReady:root.lidReady, lidClosed:root.lidClosed, dark:root.dark, error:root.error}); }
        function idleSuspend(): void {
            if (!root.active) Quickshell.execDetached(["systemctl", "suspend"]);
        }
    }
    Loader { active: root.hardwareOwner; sourceComponent: Scope { GlobalShortcut { name: "slumber"; description: "Lock and switch displays off while work continues"; onPressed: root.enter() } } }
}
