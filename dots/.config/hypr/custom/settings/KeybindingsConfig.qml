import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions as CF

Item {
    id: root
    property string configPath: CF.FileUtils.trimFileProtocol(Directories.config)
    property string helperPath: configPath + "/hypr/custom/settings/keybindings.py"
    property var bindings: []
    property var entries: []
    property var applications: []
    property string message: ""
    property bool failed: false
    property bool editing: false
    property var originalEntry: null
    property var pendingDelete: null
    property string action: "list"
    property string newScriptPath: ""
    property var shownApps: applications.filter(a => a.name.toLowerCase().includes(appSearch.text.toLowerCase()))
    property var shownBindings: bindings.filter(b => {
        const query = search.text.toLowerCase();
        return (!onlyMine.checked || b.entry) && (b.chord + " " + b.name + " " + b.detail + " " + b.submap).toLowerCase().includes(query);
    })

    function request(which, data) {
        if (worker.running) return;
        action = which;
        failed = false;
        worker.command = ["python3", helperPath, which, JSON.stringify(data || {})];
        worker.running = true;
        timeout.restart();
    }

    function beginEdit(entry) {
        originalEntry = entry;
        nameField.text = entry ? entry.name : "";
        chordField.text = entry ? entry.chord : "";
        kind.currentIndex = entry ? ["app", "command", "script"].indexOf(entry.kind) : 0;
        targetField.text = entry ? entry.target : "";
        appSearch.text = "";
        appChoice.currentIndex = entry && entry.kind === "app" ? shownApps.findIndex(a => a.id === entry.target) + 1 : 0;
        editing = true;
        Qt.callLater(() => nameField.forceActiveFocus());
    }

    function save() {
        const mode = ["app", "command", "script"][kind.currentIndex];
        const target = mode === "app" ? (shownApps[appChoice.currentIndex - 1]?.id || "") : targetField.text;
        request("save", {id: originalEntry?.id || "", name: nameField.text, chord: chordField.text, kind: mode, target: target});
    }

    function openPath(path) { Qt.openUrlExternally("file://" + path); }

    function confirmRemove(entry) {
        pendingDelete = entry;
        deleteDialog.open();
    }

    Component.onCompleted: request("list")

    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(text);
                    if (!data.ok) {
                        root.failed = true;
                        root.message = data.error;
                    } else if (root.action === "list") {
                        root.bindings = data.bindings;
                        root.entries = data.entries;
                        root.applications = data.apps;
                    } else if (root.action === "new-script") {
                        root.newScriptPath = data.path;
                        targetField.text = data.path;
                        root.message = data.message;
                        openNewScript.start();
                    } else if (root.action === "edit-script") {
                        root.message = data.message;
                    } else {
                        root.message = data.message;
                        root.editing = false;
                        refreshAfterWrite.start();
                    }
                } catch (error) {
                    root.failed = true;
                    root.message = "Could not read the shortcut helper response. Try Refresh.";
                }
            }
        }
        stderr: StdioCollector {}
        onExited: (exitCode, exitStatus) => {
            timeout.stop();
            if (exitCode !== 0 && !root.failed) {
                root.failed = true;
                root.message = "The shortcut helper could not finish. Try Refresh.";
            }
        }
    }
    Timer { id: refreshAfterWrite; interval: 100; onTriggered: root.request("list") }
    Timer { id: openNewScript; interval: 100; onTriggered: root.request("edit-script", {path: root.newScriptPath}) }
    Timer {
        id: timeout
        interval: 15000
        onTriggered: {
            worker.running = false;
            root.failed = true;
            root.message = "The helper timed out. Refresh to check the current state.";
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            StyledText { Layout.fillWidth: true; text: "Keybindings"; font.pixelSize: 23; font.weight: Font.Medium }
            RippleButtonWithIcon { materialIcon: "refresh"; mainText: "Refresh"; enabled: !worker.running; onClicked: root.request("list") }
            RippleButtonWithIcon { materialIcon: "add"; mainText: "Add shortcut"; enabled: !worker.running; onClicked: root.beginEdit(null) }
        }
        StyledText {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Your active Hyprland shortcuts, including custom bindings. Add an app, command or script below."
            color: Appearance.colors.colSubtext
        }
        RowLayout {
            Layout.fillWidth: true
            RippleButtonWithIcon { materialIcon: "code"; mainText: "Custom bindings"; onClicked: root.openPath(root.configPath + "/hypr/custom/keybinds.lua") }
            RippleButtonWithIcon { materialIcon: "folder_open"; mainText: "Scripts folder"; onClicked: root.openPath(root.configPath + "/hypr/custom/scripts") }
            Item { Layout.fillWidth: true }
            StyledText { text: worker.running ? "Loading…" : root.bindings.length + " active"; color: Appearance.colors.colSubtext }
        }
        StyledText {
            visible: root.message.length > 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: root.message
            color: root.failed ? Appearance.m3colors.m3error : Appearance.m3colors.m3primary
            textFormat: Text.PlainText
        }

        // The form scrolls on small windows so its Save/Cancel controls remain reachable.
        ScrollView {
            visible: root.editing
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(form.implicitHeight + 8, root.height * 0.53)
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                id: form
                width: parent.width
                enabled: !worker.running
                spacing: 7
                RowLayout {
                    Layout.fillWidth: true
                    MaterialTextField { id: nameField; Layout.fillWidth: true; placeholderText: "Name, e.g. Open music" }
                    MaterialTextField { id: chordField; Layout.fillWidth: true; placeholderText: "Keys, e.g. SUPER + SHIFT + K"; onAccepted: root.save() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    StyledComboBox { id: kind; buttonIcon: "category"; Layout.preferredWidth: 140; Layout.fillWidth: false; model: ["App", "Command", "Script"] }
                    MaterialTextField {
                        id: appSearch
                        visible: kind.currentIndex === 0
                        Layout.fillWidth: true
                        placeholderText: "Find an installed app"
                        onTextEdited: appChoice.currentIndex = 0
                    }
                    MaterialTextField {
                        id: targetField
                        visible: kind.currentIndex !== 0
                        Layout.fillWidth: true
                        placeholderText: kind.currentIndex === 1 ? "Command, e.g. kitty --directory ~/Desktop/code" : "Executable script path, e.g. ~/.config/hypr/custom/scripts/open-work.sh"
                    }
                }
                StyledComboBox {
                    id: appChoice
                    buttonIcon: "apps"
                    visible: kind.currentIndex === 0
                    Layout.fillWidth: true
                    model: [{name: "Choose an app…", id: ""}, ...root.shownApps.map(a => ({name: a.name + "  (" + a.id + ")", id: a.id}))]
                    textRole: "name"
                }
                RowLayout {
                    visible: kind.currentIndex === 2
                    Layout.fillWidth: true
                    MaterialTextField { id: scriptName; Layout.fillWidth: true; placeholderText: "New script name, e.g. open-work.sh" }
                    RippleButtonWithIcon { materialIcon: "note_add"; mainText: "New script"; onClicked: root.request("new-script", {name: scriptName.text}) }
                    RippleButtonWithIcon { materialIcon: "edit"; mainText: "Edit script"; enabled: targetField.text.trim().length > 0; onClicked: root.request("edit-script", {path: targetField.text}) }
                }
                StyledText {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "Save checks for conflicts and applies the shortcut. The app or script runs only when you press its keys."
                    color: Appearance.colors.colSubtext
                    font.pixelSize: 12
                }
                RowLayout {
                    RippleButtonWithIcon { materialIcon: "check"; mainText: root.originalEntry ? "Save changes" : "Add shortcut"; onClicked: root.save() }
                    RippleButtonWithIcon { materialIcon: "close"; mainText: "Cancel"; onClicked: root.editing = false }
                    Item { Layout.fillWidth: true }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            MaterialTextField { id: search; Layout.fillWidth: true; placeholderText: "Search keys, app names or actions" }
            CheckBox {
                id: onlyMine
                text: "Added here"
                spacing: 7
                contentItem: StyledText { text: onlyMine.text; leftPadding: 27; verticalAlignment: Text.AlignVCenter }
                indicator: Rectangle {
                    x: 0
                    y: (parent.height - height) / 2
                    width: 20
                    height: 20
                    radius: 5
                    color: onlyMine.checked ? Appearance.m3colors.m3primary : "transparent"
                    border.width: onlyMine.checked ? 0 : 1
                    border.color: Appearance.m3colors.m3outline
                    MaterialSymbol { anchors.centerIn: parent; text: "check"; iconSize: 16; visible: onlyMine.checked; color: Appearance.m3colors.m3onPrimary }
                }
            }
        }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: root.shownBindings
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                id: row
                required property var modelData
                width: list.width
                implicitHeight: Math.max(62, rowContent.implicitHeight + 16)
                radius: 8
                color: modelData.entry ? Appearance.colors.colLayer2 : "transparent"
                RowLayout {
                    id: rowContent
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 10
                    StyledText {
                        Layout.preferredWidth: Math.max(150, list.width * 0.29)
                        Layout.maximumWidth: 230
                        wrapMode: Text.WrapAnywhere
                        text: row.modelData.chord
                        textFormat: Text.PlainText
                        font.family: Appearance.font.family.monospace
                        color: Appearance.m3colors.m3primary
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        StyledText { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: row.modelData.name; textFormat: Text.PlainText }
                        StyledText {
                            Layout.fillWidth: true
                            wrapMode: Text.WrapAnywhere
                            text: (row.modelData.entry ? row.modelData.entry.target : row.modelData.detail) + (row.modelData.submap ? " · submap: " + row.modelData.submap : "") + (row.modelData.flags ? " · " + row.modelData.flags : "")
                            textFormat: Text.PlainText
                            font.pixelSize: 12
                            color: Appearance.colors.colSubtext
                        }
                    }
                    RippleButtonWithIcon { visible: !!row.modelData.entry; enabled: !worker.running; materialIcon: "edit"; mainText: "Edit"; onClicked: root.beginEdit(row.modelData.entry) }
                    RippleButtonWithIcon { visible: !!row.modelData.entry; enabled: !worker.running; materialIcon: "delete"; mainText: ""; onClicked: root.confirmRemove(row.modelData.entry) }
                }
            }
            StyledText {
                anchors.centerIn: parent
                visible: !worker.running && root.shownBindings.length === 0
                text: root.bindings.length ? "No matching shortcuts" : "No shortcuts loaded. Try Refresh."
                color: Appearance.colors.colSubtext
            }
        }
        StyledText {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Existing Lua actions keep their original configuration. Use Custom bindings to edit handwritten shortcuts."
            font.pixelSize: 12
            color: Appearance.colors.colSubtext
        }
    }

    Dialog {
        id: deleteDialog
        anchors.centerIn: parent
        width: Math.min(root.width - 32, 420)
        padding: 16
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape
        onOpened: Qt.callLater(() => cancelDelete.forceActiveFocus())
        onAccepted: root.request("delete", {id: root.pendingDelete.id})
        header: StyledText { text: "Remove shortcut?"; padding: 16; font.pixelSize: 20 }
        contentItem: StyledText { text: root.pendingDelete ? root.pendingDelete.name + "\nThe app or script itself will be kept." : ""; textFormat: Text.PlainText; wrapMode: Text.WordWrap }
        footer: RowLayout {
            spacing: 8
            Item { Layout.fillWidth: true }
            DialogButton {
                id: cancelDelete
                buttonText: "Cancel"
                focusPolicy: Qt.StrongFocus
                KeyNavigation.tab: removeDelete
                KeyNavigation.backtab: removeDelete
                Keys.onReturnPressed: deleteDialog.reject()
                Keys.onEnterPressed: deleteDialog.reject()
                onClicked: deleteDialog.reject()
            }
            DialogButton {
                id: removeDelete
                buttonText: "Remove"
                focusPolicy: Qt.StrongFocus
                KeyNavigation.tab: cancelDelete
                KeyNavigation.backtab: cancelDelete
                Keys.onReturnPressed: deleteDialog.accept()
                Keys.onEnterPressed: deleteDialog.accept()
                onClicked: deleteDialog.accept()
            }
        }
        background: Rectangle { color: Appearance.m3colors.m3surfaceContainerHigh; radius: 12 }
    }
}
