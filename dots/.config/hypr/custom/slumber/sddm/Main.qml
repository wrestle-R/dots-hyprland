import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 1920
    height: 1200
    color: "#102338"
    // Injectable only for the isolated native preview. SDDM supplies these objects.
    property var authBackend: sddm
    property var users: userModel
    property var sessions: sessionModel
    property date now: new Date()
    property bool submitting: false
    property bool loginError: false
    property string notice: ""
    readonly property color ink: "#f8ead7"
    readonly property color clockInk: wallpaper.status === Image.Ready ? "#183247" : ink
    readonly property color muted: "#c9cdd0"
    readonly property int rowWidth: 460
    readonly property int rowHeight: 58
    readonly property int rowGap: 22
    readonly property int fieldInset: 15
    readonly property int fieldFontSize: 20
    readonly property real fit: Math.min(width / 1600, height / 1000)
    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.now = new Date() }

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
    Component.onCompleted: Qt.callLater(function() {
        if (username.text.length) password.forceActiveFocus(); else username.forceActiveFocus();
    })

    Image { id: wallpaper; anchors.fill: parent; source: "wallpaper.jpg"; fillMode: Image.PreserveAspectCrop }
    Rectangle { anchors.fill: parent; gradient: Gradient { GradientStop { position: 0; color: "transparent" } GradientStop { position: 0.65; color: "#1011263b" } GradientStop { position: 1; color: "#90102338" } } }
    Item {
        id: stage
        width: 1600; height: 1000
        anchors.centerIn: parent
        scale: root.fit
        transformOrigin: Item.Center
        Canvas {
            id: clockFace
            x: 945; y: 165; width: 565; height: 115
            property string timeText: Qt.formatDateTime(root.now, "hhmm")
            onTimeTextChanged: requestPaint()
            Connections { target: root; function onClockInkChanged() { clockFace.requestPaint(); } }
            onPaint: {
                const c=getContext("2d"); c.reset(); c.fillStyle=root.clockInk;
                const maps=["111101101101111","010110010010111","111001111100111","111001111001111","101101111001001","111100111001111","111100111101111","111001001001001","111101111101111","111101111001111"];
                const unit=height/5;
                for(let n=0;n<4;n++) {
                    const digit=Number(timeText[n]); const x=n*width/4;
                    if(digit===1) { c.fillRect(x+unit,0,unit,unit*4); c.fillRect(x,unit*4,unit*3,unit); c.fillRect(x,0,unit,unit); }
                    else if(digit===4) { c.fillRect(x,0,unit,unit*2); c.fillRect(x,unit*2,unit*3,unit); c.fillRect(x+unit*2,0,unit,unit*5); }
                    else { const map=maps[digit]; for(let i=0;i<15;i++) if(map[i]==="1") c.fillRect(x+(i%3)*unit,Math.floor(i/3)*unit,unit,unit); }
                }
            }
        }
        Text { x: 945; y: 310; width: 540; text: Qt.formatDateTime(root.now,"dddd, d MMMM"); color: root.clockInk; font.family: "Noto Sans"; font.pixelSize: 27; horizontalAlignment: Text.AlignRight }
        Item {
            id: auth
            objectName: "authControls"
            x: 1025; y: 560; width: root.rowWidth
            height: message.y + message.height
            TextField {
                id: username
                objectName: "usernameField"
                width: parent.width; height: root.rowHeight
                text: root.users.lastUser || ""
                placeholderText: "Username"
                color: root.ink
                placeholderTextColor: root.ink
                selectionColor: root.ink
                selectedTextColor: "#172838"
                font.family: "Noto Sans"; font.pixelSize: root.fieldFontSize
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                leftPadding: root.fieldInset; rightPadding: root.fieldInset
                enabled: !root.submitting
                background: Rectangle {
                    radius: 16
                    color: username.activeFocus ? "#99142334" : "#69142334"
                    border.width: username.activeFocus ? 2 : 1
                    border.color: username.activeFocus ? root.ink : "#a8f8ead7"
                }
                onAccepted: password.forceActiveFocus()
                Accessible.name: "Username"
                KeyNavigation.tab: password
            }
            TextField {
                id: password
                objectName: "passwordField"
                anchors.top: username.bottom
                anchors.topMargin: root.rowGap
                width: parent.width; height: root.rowHeight
                echoMode: TextInput.Password
                inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
                placeholderText: "Password"
                placeholderTextColor: root.ink
                color: root.ink
                selectionColor: root.ink
                selectedTextColor: "#172838"
                font.family: "Noto Sans"; font.pixelSize: root.fieldFontSize
                verticalAlignment: Text.AlignVCenter
                leftPadding: root.fieldInset; rightPadding: 104
                enabled: !root.submitting
                onAccepted: root.login()
                Keys.onEscapePressed: clear()
                KeyNavigation.tab: reveal
                Accessible.name: "Password"
                background: Underline {
                    focused: password.activeFocus
                    lineColor: root.loginError ? "#ffb4a6" : root.ink
                }
                Button {
                    id: reveal
                    anchors.right: parent.right
                    anchors.rightMargin: 51
                    anchors.verticalCenter: parent.verticalCenter
                    width: 42; height: 42
                    enabled: !root.submitting
                    checkable: true
                    onToggled: password.echoMode = checked ? TextInput.Normal : TextInput.Password
                    KeyNavigation.tab: signIn
                    Accessible.name: checked ? "Hide password" : "Show password"
                    contentItem: StrokeIcon { glyph: "eye"; ink: root.ink }
                    padding: 9
                    background: Rectangle { radius: 19; color: reveal.hovered || reveal.activeFocus ? "#25f1c893" : "transparent"; border.width: reveal.activeFocus ? 1 : 0; border.color: root.ink }
                }
            }
            Button {
                id: signIn
                objectName: "signInButton"
                anchors.right: password.right
                anchors.rightMargin: 3
                anchors.verticalCenter: password.verticalCenter
                width: 42; height: 42
                enabled: !root.submitting
                Accessible.name: "Sign in"
                KeyNavigation.tab: session
                onClicked: root.login()
                scale: down ? 0.95 : hovered ? 1.035 : 1
                Behavior on scale { NumberAnimation { duration: 140 } }
                contentItem: StrokeIcon { glyph: "arrow"; ink: root.ink }
                padding: 10
                background: Rectangle { color: signIn.activeFocus || signIn.hovered ? "#25ffffff" : "transparent"; radius: 4 }
            }
            ComboBox {
                id: session
                objectName: "sessionPicker"
                anchors.top: password.bottom
                anchors.topMargin: root.rowGap
                width: parent.width; height: root.rowHeight
                model: root.sessions
                textRole: "name"
                currentIndex: root.sessions.lastIndex >= 0 ? root.sessions.lastIndex : 0
                enabled: !root.submitting
                leftPadding: root.fieldInset; rightPadding: 48
                KeyNavigation.tab: sleepButton.visible ? sleepButton : restartButton.visible ? restartButton : powerButton.visible ? powerButton : username
                Accessible.name: "Session"
                contentItem: Text { text: session.displayText; color: root.ink; font.family: "Noto Sans"; font.pixelSize: root.fieldFontSize; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                indicator: StrokeIcon { x: session.width-width-14; anchors.verticalCenter: parent.verticalCenter; width: 19; height: 19; glyph: "down"; ink: root.ink }
                background: Underline { focused: session.activeFocus }
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
                anchors.top: session.bottom
                anchors.topMargin: 10
                x: root.fieldInset; width: parent.width - 2 * x; height: 52
                text: root.notice
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                color: root.loginError ? "#ffd0be" : root.muted
                font.family: "Noto Sans"; font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignTop
                maximumLineCount: 2
                elide: Text.ElideRight
                Accessible.role: Accessible.AlertMessage
            }
        }
        Row {
            objectName: "powerControls"
            anchors.right: auth.right
            anchors.top: auth.bottom
            anchors.topMargin: 26
            spacing: 12
            QuietButton { id: sleepButton; text: "Sleep"; glyph: "moon"; visible: root.authBackend.canSuspend; onClicked: root.authBackend.suspend(); KeyNavigation.tab: restartButton.visible ? restartButton : powerButton.visible ? powerButton : username }
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
        implicitWidth: text === "Shut down" ? 156 : 140
        implicitHeight: 45
        padding: 10
        scale: down ? 0.975 : 1
        Behavior on scale { NumberAnimation { duration: 120 } }
        contentItem: RowLayout {
            spacing: 11
            StrokeIcon { width: 19; height: 19; glyph: control.glyph; ink: root.ink }
            Text { text: control.text; color: root.ink; font.family: "Noto Sans"; font.pixelSize: 14; verticalAlignment: Text.AlignVCenter }
        }
        background: Rectangle { radius: height / 2; color: control.hovered ? "#663c4c58" : "#25102437"; border.width: 1; border.color: control.activeFocus ? root.ink : "#708a8b88"; Behavior on color { ColorAnimation { duration: 160 } } }
    }
    component Underline: Rectangle {
        id: surface
        property bool focused: false
        property color lineColor: root.ink
        color: focused ? "#77142334" : "#42142334"
        radius: 6
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: surface.focused ? 2 : 1
            color: surface.lineColor
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
