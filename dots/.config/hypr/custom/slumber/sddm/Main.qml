import QtQuick
import QtQuick.Effects
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 1920
    height: 1200
    color: "#152334"
    property bool submitting: false
    property real entryBlur: 0.8
    property real panelOffset: 12
    property real panelOpacity: 0
    Component.onCompleted: { entryBlur=0; panelOffset=0; panelOpacity=1; }
    Behavior on entryBlur { NumberAnimation { duration: 650; easing.type: Easing.OutCubic } }
    Behavior on panelOffset { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
    Behavior on panelOpacity { NumberAnimation { duration: 450 } }
    function login() {
        if (submitting || username.text.length === 0 || session.currentIndex < 0) return;
        submitting = true;
        message.text = "Signing in…";
        sddm.login(username.text, password.text, session.currentIndex);
    }
    Image { id: wallpaper; anchors.fill: parent; source: "wallpaper.jpg"; fillMode: Image.PreserveAspectCrop }
    MultiEffect { anchors.fill: wallpaper; source: wallpaper; blurEnabled: true; blurMax: 12; blur: root.entryBlur; visible: root.entryBlur > 0.01 }
    Rectangle { anchors.fill: parent; gradient: Gradient { GradientStop { position: 0; color: "#00000000" } GradientStop { position: 1; color: "#8c06101e" } } }
    Text { anchors { left: parent.left; top: parent.top; margins: 44 }; text: "WELCOME BACK"; color: "#243341"; font.pixelSize: 18; font.letterSpacing: 4 }
    Column {
        anchors { right: parent.right; top: parent.top; margins: 55 }
        property date now: new Date()
        Timer { interval: 1000; running: true; repeat: true; onTriggered: parent.now = new Date() }
        Text { anchors.right: parent.right; text: Qt.formatDateTime(parent.now,"hh:mm"); color: "#142334"; font.pixelSize: 80; font.weight: Font.Light }
        Text { anchors.right: parent.right; text: Qt.formatDateTime(parent.now,"dddd, d MMMM"); color: "#142334"; font.pixelSize: 18 }
    }
    ColumnLayout {
        id: auth
        width: Math.min(420, root.width-60)
        x: Math.min(root.width*0.61, root.width-width-30)
        y: root.height*0.60 + root.panelOffset
        opacity: root.panelOpacity
        spacing: 16
        TextField {
            id: username
            Layout.fillWidth: true
            text: userModel.lastUser
            placeholderText: "Username"
            horizontalAlignment: Text.AlignHCenter
            color: "#ffffff"
            font.pixelSize: 23
            enabled: !root.submitting
            background: Rectangle { color: "#a0111720"; radius: 22 }
            Keys.onReturnPressed: password.forceActiveFocus()
        }
        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: password
                Layout.fillWidth: true
                implicitHeight: 58
                placeholderText: "Password"
                placeholderTextColor: "#bfc0ca"
                echoMode: TextInput.Password
                inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
                color: "#f3f1f6"
                font.pixelSize: 18
                leftPadding: 24
                enabled: !root.submitting
                focus: true
                background: Rectangle { color: "#ee17171e"; radius: 29; border.color: password.activeFocus ? "#cbc6da" : "#554a4854" }
                Keys.onReturnPressed: root.login()
                Keys.onEnterPressed: root.login()
                Keys.onEscapePressed: clear()
            }
            Button {
                text: "→"
                implicitWidth: 58
                implicitHeight: 58
                enabled: !root.submitting
                onClicked: root.login()
                contentItem: Text { text: parent.text; color: "#282331"; font.pixelSize: 26; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: "#cbc6da"; radius: 29 }
            }
        }
        ComboBox {
            id: session
            Layout.alignment: Qt.AlignHCenter
            implicitWidth: Math.min(330,auth.width)
            implicitHeight: 45
            model: sessionModel
            textRole: "name"
            currentIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
            enabled: !root.submitting
            contentItem: Text { text: session.displayText; color: "#f1eef6"; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
            background: Rectangle { color: "#e617171e"; radius: 23; border.color: "#554a4854" }
        }
        Text { id: message; Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#ffffff"; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 16 }
    }
    RowLayout {
        anchors { right: parent.right; bottom: parent.bottom; margins: 30 }
        spacing: 16
        Button { text: "Sleep"; visible: sddm.canSuspend; onClicked: sddm.suspend() }
        Button { text: "Restart"; visible: sddm.canReboot; onClicked: sddm.reboot() }
        Button { text: "Shutdown"; visible: sddm.canPowerOff; onClicked: sddm.powerOff() }
    }
    Connections {
        target: sddm
        function onLoginFailed() { root.submitting=false; password.clear(); message.text="Incorrect login. Try again."; password.forceActiveFocus(); }
        function onLoginSucceeded() { password.clear(); message.text="Welcome back"; root.entryBlur=0.6; root.panelOpacity=0; }
        function onInformationMessage(message) { root.submitting=false; password.forceActiveFocus(); }
    }
}
