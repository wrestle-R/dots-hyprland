import qs
import qs.modules.common
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Pam

Scope {
    id: root

    enum ActionEnum { Unlock, Poweroff, Reboot }

    signal shouldReFocus()
    signal unlocked(targetAction: var)
    signal failed()

    // These properties are in the context and not individual lock surfaces
    // so all surfaces can share the same state.
    property string currentText: ""
    property bool unlockInProgress: false
    property bool showFailure: false
    property bool fingerprintsConfigured: false
    readonly property bool fingerprintScanning: fingerPam.active
    property var targetAction: LockContext.ActionEnum.Unlock
    property bool alsoInhibitIdle: false

    function resetTargetAction() {
        root.targetAction = LockContext.ActionEnum.Unlock;
    }

    function clearText() {
        root.currentText = "";
    }

    function resetClearTimer() {
        passwordClearTimer.restart();
    }

    function reset() {
        root.resetTargetAction();
        root.fingerprintsConfigured = false;
        root.clearText();
        root.unlockInProgress = false;
        stopFingerPam();
    }

    Timer {
        id: passwordClearTimer
        interval: 10000
        onTriggered: {
            if (!root.unlockInProgress) {
                root.clearText();
                root.resetTargetAction();
            }
        }
    }

    // PAM ends a scan after a timeout or missed finger. Re-arm while locked,
    // including after the password field clears, without taking its focus.
    Timer {
        interval: 1500
        repeat: true
        running: GlobalStates.screenLocked && root.fingerprintsConfigured
            && !root.unlockInProgress && root.targetAction === LockContext.ActionEnum.Unlock
        onTriggered: root.tryFingerUnlock()
    }

    onTargetActionChanged: {
        if (targetAction !== LockContext.ActionEnum.Unlock) stopFingerPam();
    }

    onCurrentTextChanged: {
        if (currentText.length > 0) {
            showFailure = false;
            GlobalStates.screenUnlockFailed = false;
        }
        GlobalStates.screenLockContainsCharacters = currentText.length > 0;
        passwordClearTimer.restart();
    }

    function tryUnlock(alsoInhibitIdle = false) {
        root.alsoInhibitIdle = alsoInhibitIdle;
        root.unlockInProgress = true;
        stopFingerPam();
        pam.start();
    }

    function tryFingerUnlock() {
        if (!GlobalStates.screenLocked || root.targetAction !== LockContext.ActionEnum.Unlock
            || root.unlockInProgress || fingerPam.active) {
            return;
        }
        if (root.fingerprintsConfigured) {
            fingerPam.start();
        } else {
            fingerprintCheckProc.running = true;
        }
    }

    function stopFingerPam() {
        if (fingerPam.active) {
            fingerPam.abort();
        }
    }

    Process {
        id: fingerprintCheckProc
        running: true
        command: ["fprintd-list", Quickshell.env("USER")]
        stdout: StdioCollector {
            id: fingerprintOutputCollector
            onStreamFinished: {
                root.fingerprintsConfigured = fingerprintOutputCollector.text.includes("Fingerprints for user");
                if (root.fingerprintsConfigured) root.tryFingerUnlock();
            }
        }
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0) {
                // console.warn("[LockContext] fprintd-list command exited with error:", exitCode, exitStatus);
                root.fingerprintsConfigured = false;
            }
        }
    }
    
    PamContext {
        id: pam

        // pam_unix will ask for a response for the password prompt
        onPamMessage: {
            if (this.responseRequired) {
                this.respond(root.currentText);
            }
        }

        // pam_unix won't send any important messages so all we need is the completion status.
        onCompleted: result => {
            if (result == PamResult.Success) {
                root.unlocked(root.targetAction);
                stopFingerPam();
            } else {
                root.clearText();
                root.unlockInProgress = false;
                GlobalStates.screenUnlockFailed = true;
                root.showFailure = true;
                if (root.fingerprintsConfigured) root.tryFingerUnlock();
            }
        }
    }

    PamContext {
        id: fingerPam

        configDirectory: "pam"
        config: "fprintd.conf"

        onCompleted: result => {
            if (result == PamResult.Success && GlobalStates.screenLocked
                && root.targetAction === LockContext.ActionEnum.Unlock && !root.unlockInProgress) {
                root.clearText();
                root.unlocked(LockContext.ActionEnum.Unlock);
            }
        }
    }
}
