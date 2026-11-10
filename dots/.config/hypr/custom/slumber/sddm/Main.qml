import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 1920
    height: 1200
    color: "#162c40"
    // Injectable only for the isolated native preview. SDDM supplies these objects.
    property var authBackend: sddm
    property var users: userModel
    property var sessions: sessionModel
    property date now: new Date()
    property bool submitting: false
    property bool loginError: false
    property bool frameSeen: false
    property bool entryQueued: false
    property real introOpacity: 1
    property real landscapeScale: 1.025
    property real clockOpacity: 0
    property real haloOpacity: 0
    property real haloRotation: -7
    property real formOpacity: 0
    property real formOffset: 18
    property real detailsOpacity: 0
    property string notice: ""
    readonly property color ink: "#f8ead7"
    readonly property color muted: "#c9cdd0"
    readonly property color accent: "#f1c893"
    readonly property real fit: Math.min(width / 1600, height / 1000)
    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.now = new Date() }

    function queueEntry() {
        if (!entryQueued && frameSeen && backdrop.status !== Image.Loading && intro.status !== Image.Loading) {
            entryQueued = true;
            entryDelay.start();
        }
    }
    function login() {
        if (submitting) return;
        if (!username.text.trim()) { notice = "Enter your username."; username.forceActiveFocus(); return; }
        if (session.currentIndex < 0) { notice = "No session available."; session.forceActiveFocus(); return; }
        submitting = true;
        reveal.checked = false;
        loginError = false;
        notice = "Signing in…";
        // Authentication never waits for animation timers or frame delivery.
        root.authBackend.login(username.text.trim(), password.text, session.currentIndex);
    }
    Connections {
        target: root.Window.window
        function onFrameSwapped() {
            if (!root.frameSeen) root.frameSeen = true;
            root.queueEntry();
        }
    }
    Timer { id: entryDelay; interval: 180; onTriggered: entryMotion.start() }
    Timer {
        interval: 1800; running: true
        onTriggered: { if (!root.entryQueued) { root.entryQueued = true; entryMotion.start(); } }
    }
    ParallelAnimation {
        id: entryMotion
        NumberAnimation { target: root; property: "introOpacity"; to: 0; duration: 1350; easing.type: Easing.OutCubic }
        NumberAnimation { target: root; property: "landscapeScale"; to: 1; duration: 1600; easing.type: Easing.OutCubic }
        SequentialAnimation { PauseAnimation { duration: 100 } NumberAnimation { target: root; property: "clockOpacity"; to: 1; duration: 850; easing.type: Easing.OutCubic } }
        SequentialAnimation {
            PauseAnimation { duration: 180 }
            ParallelAnimation {
                NumberAnimation { target: root; property: "haloOpacity"; to: 1; duration: 1050; easing.type: Easing.OutCubic }
                NumberAnimation { target: root; property: "haloRotation"; to: 0; duration: 1400; easing.type: Easing.OutCubic }
            }
        }
        SequentialAnimation {
            PauseAnimation { duration: 400 }
            ParallelAnimation {
                NumberAnimation { target: root; property: "formOpacity"; to: 1; duration: 700; easing.type: Easing.OutCubic }
                NumberAnimation { target: root; property: "formOffset"; to: 0; duration: 900; easing.type: Easing.OutCubic }
            }
        }
        SequentialAnimation { PauseAnimation { duration: 550 } NumberAnimation { target: root; property: "detailsOpacity"; to: 1; duration: 750 } }
    }
    Component.onCompleted: Qt.callLater(function() {
        if (username.text.length) password.forceActiveFocus(); else username.forceActiveFocus();
    })

    // Setup bakes both blur levels. No shader, live blur or background worker.
    Image {
        id: backdrop
        anchors.fill: parent
        source: "wallpaper-blurred.jpg"
        fillMode: Image.PreserveAspectCrop
        scale: root.landscapeScale
        onStatusChanged: root.queueEntry()
    }
    Image {
        id: intro
        anchors.fill: parent
        source: "wallpaper-intro.jpg"
        fillMode: Image.PreserveAspectCrop
        opacity: root.introOpacity
        visible: opacity > 0.001
        scale: root.landscapeScale
        onStatusChanged: root.queueEntry()
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: "#a64a6791" }
            GradientStop { position: 0.38; color: "#8a243f60" }
            GradientStop { position: 0.7; color: "#85102338" }
            GradientStop { position: 1; color: "#ed041225" }
        }
    }
    Canvas {
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const c=getContext("2d"); c.reset();
            const x=width*0.73, y=height*0.31, r=Math.min(width,height)*0.27;
            const glow=c.createRadialGradient(x,y,0,x,y,r);
            glow.addColorStop(0,"rgba(255,198,145,0.48)");
            glow.addColorStop(0.48,"rgba(255,203,155,0.30)");
            glow.addColorStop(1,"rgba(255,203,155,0)");
            c.fillStyle=glow;c.fillRect(0,0,width,height);
        }
    }
    Item {
        id: stage
        width: 1600; height: 1000
        anchors.centerIn: parent
        scale: root.fit
        transformOrigin: Item.Center
        Row {
            x: 60; y: 42
            spacing: 15
            opacity: root.detailsOpacity
            Rectangle { width: 2; height: 21; color: root.accent }
            Text { text: "hyprland"; color: root.ink; font.family: "Noto Sans"; font.pixelSize: 17; font.weight: Font.DemiBold }
        }

        Item {
            x: 510; y: 172; width: 580; height: 430
            opacity: root.haloOpacity
            rotation: root.haloRotation
            HaloArc { anchors.fill: parent; lower: false }
            HaloArc { anchors.fill: parent; lower: true }
        }
        Column {
            x: 500; y: 316; width: 600; spacing: 9
            opacity: root.clockOpacity
            Text {
                width: parent.width; height: 145
                text: Qt.formatDateTime(root.now, "hh:mm")
                color: root.ink
                font.family: "Noto Sans"
                font.pixelSize: 132
                font.weight: Font.ExtraLight
                font.letterSpacing: -5
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            Text {
                width: parent.width
                text: Qt.formatDateTime(root.now, "dddd, d MMMM")
                color: root.ink
                font.family: "Noto Sans"
                font.pixelSize: 21
                font.weight: Font.Normal
                horizontalAlignment: Text.AlignHCenter
            }
        }
        Item {
            id: auth
            objectName: "authControls"
            x: 530; y: 550; width: 550; height: 220
            opacity: root.formOpacity
            transform: Translate { y: root.formOffset }
            TextField {
                id: username
                objectName: "usernameField"
                x: 105; y: 0; width: 330; height: 32
                text: root.users.lastUser || ""
                placeholderText: "Username"
                color: root.muted
                placeholderTextColor: root.muted
                selectionColor: root.accent
                selectedTextColor: "#172838"
                font.family: "Noto Sans"; font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                enabled: !root.submitting
                background: Rectangle { radius: 16; color: username.activeFocus ? "#45142334" : "transparent"; border.width: username.activeFocus ? 1 : 0; border.color: root.accent }
                onAccepted: password.forceActiveFocus()
                Accessible.name: "Username"
                KeyNavigation.tab: password
            }
            TextField {
                id: password
                objectName: "passwordField"
                x: 0; y: 58; width: 466; height: 58
                echoMode: TextInput.Password
                inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
                placeholderText: "Enter your password"
                placeholderTextColor: "#d1c7b9"
                color: root.ink
                selectionColor: root.accent
                selectedTextColor: "#172838"
                font.family: "Noto Sans"; font.pixelSize: 17
                leftPadding: 65; rightPadding: 58
                enabled: !root.submitting
                onAccepted: root.login()
                Keys.onEscapePressed: clear()
                KeyNavigation.tab: reveal
                Accessible.name: "Password"
                background: Rectangle {
                    radius: height / 2
                    gradient: Gradient { GradientStop { position: 0; color: "#66334654" } GradientStop { position: 1; color: "#a8172a3a" } }
                    border.width: 1
                    border.color: root.loginError ? "#efb4a6" : password.activeFocus ? "#f2d5ac" : "#9abbaa91"
                    Behavior on border.color { ColorAnimation { duration: 160 } }
                }
                StrokeIcon { x: 26; anchors.verticalCenter: parent.verticalCenter; width: 23; height: 23; glyph: "lock"; ink: root.accent }
                Button {
                    id: reveal
                    x: parent.width - width - 11; anchors.verticalCenter: parent.verticalCenter
                    width: 38; height: 38
                    enabled: !root.submitting
                    checkable: true
                    onToggled: password.echoMode = checked ? TextInput.Normal : TextInput.Password
                    KeyNavigation.tab: signIn
                    Accessible.name: checked ? "Hide password" : "Show password"
                    contentItem: StrokeIcon { glyph: "eye"; ink: root.accent }
                    padding: 8
                    background: Rectangle { radius: 19; color: reveal.hovered || reveal.activeFocus ? "#25f1c893" : "transparent"; border.width: reveal.activeFocus ? 1 : 0; border.color: root.accent }
                }
            }
            Button {
                id: signIn
                objectName: "signInButton"
                x: 490; y: 58; width: 58; height: 58
                enabled: !root.submitting
                Accessible.name: "Sign in"
                KeyNavigation.tab: session
                onClicked: root.login()
                scale: down ? 0.95 : hovered ? 1.035 : 1
                Behavior on scale { NumberAnimation { duration: 140 } }
                contentItem: StrokeIcon { glyph: "arrow"; ink: "#253340" }
                padding: 18
                background: Rectangle {
                    radius: height / 2
                    gradient: Gradient { GradientStop { position: 0; color: signIn.hovered ? "#ffe3bb" : "#fbd5a3" } GradientStop { position: 1; color: "#edbb80" } }
                    border.width: signIn.activeFocus ? 2 : 1
                    border.color: signIn.activeFocus ? "#fff5e5" : "#f8dcb5"
                }
            }
            ComboBox {
                id: session
                objectName: "sessionPicker"
                x: 34; y: 138; width: 430; height: 51
                model: root.sessions
                textRole: "name"
                currentIndex: root.sessions.lastIndex >= 0 ? root.sessions.lastIndex : 0
                enabled: !root.submitting
                leftPadding: 60; rightPadding: 45
                KeyNavigation.tab: sleepButton.visible ? sleepButton : restartButton.visible ? restartButton : powerButton
                Accessible.name: "Session"
                contentItem: Text { text: session.displayText; color: root.ink; font.family: "Noto Sans"; font.pixelSize: 17; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                indicator: StrokeIcon { x: session.width-width-19; anchors.verticalCenter: parent.verticalCenter; width: 19; height: 19; glyph: "down"; ink: root.ink }
                background: Rectangle { radius: height / 2; color: session.hovered ? "#70334958" : "#73203545"; border.width: 1; border.color: session.activeFocus ? root.accent : "#8bb9aa94"; Behavior on color { ColorAnimation { duration: 160 } } }
                StrokeIcon { x: 24; anchors.verticalCenter: parent.verticalCenter; width: 24; height: 24; glyph: "layers"; ink: root.ink }
                delegate: ItemDelegate {
                    required property var model
                    required property int index
                    width: session.width - 10
                    highlighted: session.highlightedIndex === index
                    contentItem: Text { text: parent.model.name; color: root.ink; font.family: "Noto Sans"; font.pixelSize: 16; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
                    background: Rectangle { radius: 16; color: parent.highlighted ? "#3f5361" : "transparent" }
                }
                popup: Popup {
                    y: session.height + 8; width: session.width; padding: 5
                    implicitHeight: Math.min(contentItem.implicitHeight + 10, 210)
                    contentItem: ListView { clip: true; implicitHeight: contentHeight; model: session.popup.visible ? session.delegateModel : null; currentIndex: session.highlightedIndex; ScrollIndicator.vertical: ScrollIndicator {} }
                    background: Rectangle { radius: 21; color: "#ef162b3e"; border.width: 1; border.color: "#9aab9c87" }
                }
            }
            Text {
                id: message
                objectName: "authMessage"
                x: -20; y: 199; width: 590; height: 40
                text: root.notice
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                color: root.loginError ? "#ffd0be" : root.muted
                font.family: "Noto Sans"; font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Accessible.role: Accessible.AlertMessage
            }
        }
        Row {
            x: (parent.width-width)/2; y: 852
            spacing: 24
            opacity: root.detailsOpacity
            QuietButton { id: sleepButton; text: "Sleep"; glyph: "moon"; visible: root.authBackend.canSuspend; onClicked: root.authBackend.suspend(); KeyNavigation.tab: restartButton.visible ? restartButton : powerButton }
            QuietButton { id: restartButton; text: "Restart"; glyph: "restart"; visible: root.authBackend.canReboot; onClicked: root.authBackend.reboot(); KeyNavigation.tab: powerButton.visible ? powerButton : username }
            QuietButton { id: powerButton; text: "Shut down"; glyph: "power"; visible: root.authBackend.canPowerOff; onClicked: root.authBackend.powerOff(); KeyNavigation.tab: username }
        }
    }
    Connections {
        target: root.authBackend
        function onLoginFailed() {
            root.submitting = false;
            root.loginError = true;
            password.clear();
            reveal.checked = false;
            root.notice = "Sign-in failed. Please try again.";
            password.forceActiveFocus();
        }
        function onLoginSucceeded() { password.clear(); reveal.checked = false; root.notice = ""; }
        function onInformationMessage(text) { root.notice = text; }
    }
    component QuietButton: Button {
        id: control
        property string glyph
        implicitWidth: text === "Shut down" ? 160 : 145
        implicitHeight: 45
        padding: 17
        scale: down ? 0.975 : 1
        Behavior on scale { NumberAnimation { duration: 120 } }
        contentItem: RowLayout {
            spacing: 11
            StrokeIcon { width: 19; height: 19; glyph: control.glyph; ink: root.accent }
            Text { text: control.text; color: root.ink; font.family: "Noto Sans"; font.pixelSize: 14; verticalAlignment: Text.AlignVCenter }
        }
        background: Rectangle { radius: height / 2; color: control.hovered ? "#663c4c58" : "#25102437"; border.width: 1; border.color: control.activeFocus ? root.accent : "#708a8b88"; Behavior on color { ColorAnimation { duration: 160 } } }
    }
    component HaloArc: Canvas {
        property bool lower: false
        onPaint: {
            const c = getContext("2d");
            c.reset();
            const count = 150;
            const cx = lower ? 277 : 291, cy = lower ? 206 : 265;
            const start = lower ? -0.08 : -3.08, span = lower ? 1.52 : 1.67;
            for (let i = 0; i < count; i++) {
                const t = i / count, a = start + span * t;
                const alpha = Math.pow(Math.sin(Math.PI * t), 2);
                for (const layer of [{w:15,a:0.06},{w:7,a:0.16},{w:2.5,a:0.55},{w:1.1,a:1}]) {
                    // Use a short elliptical arc; the faint wide strokes supply the glow.
                    c.beginPath();
                    c.moveTo(cx + 257*Math.cos(a), cy + 205*Math.sin(a));
                    const b = start + span*(i+1.4)/count;
                    c.lineTo(cx + 257*Math.cos(b), cy + 205*Math.sin(b));
                    c.strokeStyle = "rgba(255,213,163," + alpha*layer.a + ")";
                    c.lineWidth = layer.w;
                    c.lineCap = "round";
                    c.stroke();
                }
            }
        }
    }
    component StrokeIcon: Canvas {
        property string glyph
        property color ink: "white"
        onInkChanged: requestPaint()
        onGlyphChanged: requestPaint()
        onPaint: {
            const c=getContext("2d"); c.reset(); c.scale(width/24,height/24);
            c.strokeStyle=ink; c.lineWidth=1.7; c.lineCap="round"; c.lineJoin="round"; c.beginPath();
            if (glyph==="power") { c.moveTo(12,3);c.lineTo(12,12);c.moveTo(6,6);c.bezierCurveTo(-2,13,4,22,12,22);c.bezierCurveTo(21,22,26,13,18,6); }
            else if(glyph==="restart") { c.arc(12,13,8,-0.8,4.5);c.moveTo(20,4);c.lineTo(20,10);c.lineTo(14,10); }
            else if(glyph==="moon") { c.moveTo(16,3);c.bezierCurveTo(3,-1,-2,17,10,21);c.bezierCurveTo(17,24,23,18,22,13);c.bezierCurveTo(14,17,9,9,16,3); }
            else if(glyph==="lock") { c.rect(5,10,14,11);c.moveTo(8,10);c.lineTo(8,7);c.bezierCurveTo(8,1,16,1,16,7);c.lineTo(16,10);c.moveTo(12,14);c.lineTo(12,17); }
            else if(glyph==="eye") { c.moveTo(2,12);c.quadraticCurveTo(12,1,22,12);c.quadraticCurveTo(12,23,2,12);c.moveTo(15,12);c.arc(12,12,3,0,2*Math.PI); }
            else if(glyph==="arrow") { c.moveTo(3,12);c.lineTo(21,12);c.moveTo(14,5);c.lineTo(21,12);c.lineTo(14,19); }
            else if(glyph==="layers") { c.moveTo(2,8);c.lineTo(12,3);c.lineTo(22,8);c.lineTo(12,13);c.closePath();c.moveTo(2,12);c.lineTo(12,17);c.lineTo(22,12);c.moveTo(2,16);c.lineTo(12,21);c.lineTo(22,16); }
            else { c.moveTo(6,9);c.lineTo(12,15);c.lineTo(18,9); }
            c.stroke();
        }
    }
}
