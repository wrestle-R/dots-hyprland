//@ pragma Env QS_NO_RELOAD_POPUP=1
//@ pragma Env QT_QUICK_CONTROLS_STYLE=Basic
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

ShellRoot {
    id: root

    readonly property string monitorName: Quickshell.env("CONFIRM_CLOSE_MONITOR")
    property bool decided: false
    property bool wasConnected: false
    property bool closeSelected: true
    property string pendingAction: ""

    function focusSelection() {
        if (!decided)
            (closeSelected ? closeButton : cancelButton).forceActiveFocus(Qt.TabFocusReason);
    }

    function selectClose(selected) {
        closeSelected = selected;
        focusSelection();
    }

    function sendPending() {
        if (!ipc.connected || pendingAction === "")
            return;
        ipc.write(pendingAction + "\n");
        ipc.flush();
        pendingAction = "";
    }

    function finish(action) {
        if (decided)
            return;
        decided = true;
        dialog.visible = false;
        pendingAction = action;
        sendPending();
    }

    function handleKey(event, closeSelected) {
        if (event.key === Qt.Key_Escape) {
            finish("cancel");
        } else if (event.key === Qt.Key_Left) {
            selectClose(false);
        } else if (event.key === Qt.Key_Right) {
            selectClose(true);
        } else if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
            selectClose(!closeSelected);
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            if (!event.isAutoRepeat)
                finish(closeSelected ? "confirm" : "cancel");
        } else {
            return;
        }
        event.accepted = true;
    }

    Socket {
        id: ipc
        path: Quickshell.env("CONFIRM_CLOSE_SOCKET")
        connected: true
        onConnectionStateChanged: {
            if (connected) {
                root.wasConnected = true;
                root.sendPending();
                Qt.callLater(root.focusSelection);
            } else if (root.wasConnected) {
                Qt.quit();
            }
        }
        parser: SplitParser {
            onRead: data => {
                if (data === "dismiss")
                    Qt.quit();
            }
        }
    }

    Timer {
        interval: 3000
        running: !root.wasConnected
        onTriggered: Qt.quit()
    }

    PanelWindow {
        id: dialog
        screen: Quickshell.screens.find(screen => screen.name === root.monitorName) ?? Quickshell.screens[0]
        anchors {
            top: true
            bottom: true
            left: true
            right: true
        }
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "quickshell:confirm-close"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
        onWindowConnected: Qt.callLater(root.focusSelection)

        // A transparent input surface makes clicks in desktop gaps cancel too.
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            onClicked: root.finish("cancel")
        }

        Rectangle {
            id: surface
            anchors.centerIn: parent
            width: 260
            height: 108
            radius: 18
            color: Qt.rgba(34 / 255, 34 / 255, 32 / 255, 0.72)
            border.width: 1
            border.color: Qt.rgba(1, 1, 0.97, 0.10)
            focus: true
            Keys.onPressed: event => root.handleKey(event, root.closeSelected)

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.AllButtons
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 18
                text: "Close window?"
                color: "#f4f3ee"
                font.family: "Noto Sans"
                font.pixelSize: 16
                font.weight: Font.DemiBold
                textFormat: Text.PlainText
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 58
                spacing: 8

                DialogButton {
                    id: cancelButton
                    text: "Cancel"
                    closesWindow: false
                }

                DialogButton {
                    id: closeButton
                    text: "Close"
                    closesWindow: true
                    focus: true
                }
            }
        }
    }

    component DialogButton: Button {
        id: button
        required property bool closesWindow
        implicitWidth: 92
        implicitHeight: 30
        padding: 0
        enabled: !root.decided
        hoverEnabled: true
        focusPolicy: Qt.StrongFocus
        onActiveFocusChanged: {
            if (activeFocus)
                root.closeSelected = closesWindow;
        }
        Accessible.name: text
        Keys.priority: Keys.BeforeItem
        Keys.onPressed: event => root.handleKey(event, button.closesWindow)
        onClicked: root.finish(closesWindow ? "confirm" : "cancel")

        contentItem: Text {
            text: button.text
            color: button.closesWindow ? "#222220" : "#edece6"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "Noto Sans"
            font.pixelSize: 12
            font.weight: Font.Medium
            textFormat: Text.PlainText
        }

        background: Rectangle {
            radius: 8
            color: button.closesWindow ? (button.down ? "#d4d3cc" : button.hovered ? "#ffffff" : "#edece6") : Qt.rgba(1, 1, 1, button.down ? 0.14 : button.hovered ? 0.09 : 0.025)
            border.width: 1
            border.color: button.activeFocus ? "#99978f" : Qt.rgba(1, 1, 1, button.closesWindow ? 0 : 0.10)
            Behavior on color {
                ColorAnimation {
                    duration: 90
                }
            }
        }
    }
}
