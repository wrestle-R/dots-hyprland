import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

FocusScope {
    id: root
    property bool active: GlobalStates.sidebarLeftOpen
    readonly property color accent: "#ff914d"
    readonly property var tasks: Todo.list.map((task, i) => ({content: task.content, done: task.done, originalIndex: i}))
        .sort((a, b) => Number(a.done) - Number(b.done) || a.originalIndex - b.originalIndex)

    function focusActiveItem() { root.focusTaskInput(); }
    onActiveChanged: { if (active) Qt.callLater(root.focusTaskInput); }
    onVisibleChanged: { if (visible && active) Qt.callLater(root.focusTaskInput); }
    Component.onCompleted: { if (active) Qt.callLater(root.focusTaskInput); }
    Connections {
        target: root.Window.window
        function onActiveChanged() {
            if (root.Window.active && root.active) root.focusTaskInput();
        }
    }
    function focusTaskInput() {
        taskList.positionViewAtEnd();
        taskList.footerItem?.inputField.forceActiveFocus();
    }
    function addTask() {
        const input = taskList.footerItem?.inputField;
        if (!input) return;
        const task = input.text.trim();
        if (task.length === 0) return;
        Todo.addTask(task);
        input.text = "";
        focusTaskInput();
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 18

        HyprTrackSummary {
            objectName: "hyprtrackSummary"
            Layout.fillWidth: true
            active: root.active && root.visible
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: Appearance.colors.colLayer0Border
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            StyledText {
                text: "To-do"
                font.pixelSize: 23
                font.weight: Font.DemiBold
            }
            StyledText {
                Layout.fillWidth: true
                visible: Todo.list.length > 0
                text: `${Todo.list.filter(task => task.done).length} of ${Todo.list.length} done`
                font.pixelSize: 12
                color: Appearance.colors.colSubtext
            }
            Item { visible: Todo.list.length === 0; Layout.fillWidth: true }
            RippleButton {
                objectName: "addSidebarTask"
                implicitWidth: 34
                implicitHeight: 34
                Accessible.name: "Add a task"
                onClicked: root.focusTaskInput()
                contentItem: MaterialSymbol {
                    text: "add"
                    iconSize: 25
                    horizontalAlignment: Text.AlignHCenter
                }
                StyledToolTip { text: "Add a task" }
            }
        }
        ListView {
            id: taskList
            objectName: "sidebarTasks"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            model: root.tasks
            delegate: Item {
                id: row
                required property var modelData
                width: ListView.view.width
                implicitHeight: Math.max(54, taskCheck.implicitHeight + 12)
                RowLayout {
                    anchors.fill: parent
                    spacing: 4
                    CheckBox {
                        id: taskCheck
                        objectName: "sidebarTaskCheck"
                        Layout.fillWidth: true
                        checked: row.modelData.done
                        spacing: 13
                        padding: 4
                        Accessible.name: row.modelData.content
                        onClicked: {
                            if (row.modelData.done) Todo.markUnfinished(row.modelData.originalIndex);
                            else Todo.markDone(row.modelData.originalIndex);
                        }
                        indicator: Rectangle {
                            x: taskCheck.leftPadding
                            y: (taskCheck.height - height) / 2
                            implicitWidth: 19
                            implicitHeight: 19
                            radius: 4
                            color: taskCheck.checked ? root.accent : "transparent"
                            border.width: 1.5
                            border.color: taskCheck.checked || taskCheck.activeFocus ? root.accent : Appearance.colors.colSubtext
                            MaterialSymbol {
                                anchors.centerIn: parent
                                text: "check"
                                iconSize: 16
                                visible: taskCheck.checked
                                color: "#19191b"
                            }
                        }
                        contentItem: StyledText {
                            leftPadding: taskCheck.indicator.width + taskCheck.spacing
                            text: row.modelData.content
                            textFormat: Text.PlainText
                            wrapMode: Text.Wrap
                            font.pixelSize: 14
                            font.strikeout: taskCheck.checked
                            color: taskCheck.checked ? Appearance.colors.colSubtext : Appearance.colors.colOnLayer0
                        }
                    }
                    RippleButton {
                        objectName: "deleteSidebarTask"
                        implicitWidth: 30
                        implicitHeight: 32
                        Accessible.name: "Delete task: " + row.modelData.content
                        onClicked: Todo.deleteItem(row.modelData.originalIndex)
                        contentItem: MaterialSymbol {
                            text: "close"
                            iconSize: 17
                            horizontalAlignment: Text.AlignHCenter
                            color: Appearance.colors.colSubtext
                        }
                        StyledToolTip { text: "Delete task" }
                    }
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Appearance.colors.colLayer0Border
                }
            }
            footer: ColumnLayout {
                property alias inputField: taskInput
                width: taskList.width
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 10
                    spacing: 7
                    TextField {
                        id: taskInput
                        focus: true
                        objectName: "sidebarTaskInput"
                        Layout.fillWidth: true
                        implicitHeight: 42
                        placeholderText: "Add a task…"
                        placeholderTextColor: Appearance.colors.colSubtext
                        color: Appearance.colors.colOnLayer0
                        font.family: Appearance.font.family.main
                        font.pixelSize: 14
                        selectByMouse: true
                        maximumLength: 2000
                        selectedTextColor: Appearance.colors.colOnSecondaryContainer
                        selectionColor: Appearance.colors.colSecondaryContainer
                        Accessible.name: "New task"
                        onAccepted: root.addTask()
                        background: Rectangle {
                            radius: 9
                            color: Appearance.colors.colLayer1
                            border.width: taskInput.activeFocus ? 1 : 0
                            border.color: root.accent
                        }
                    }
                    RippleButton {
                        objectName: "saveSidebarTask"
                        implicitWidth: 36
                        implicitHeight: 38
                        enabled: taskInput.text.trim().length > 0
                        Accessible.name: "Save task"
                        onClicked: root.addTask()
                        contentItem: MaterialSymbol {
                            text: "add"
                            iconSize: 22
                            horizontalAlignment: Text.AlignHCenter
                            color: root.accent
                        }
                    }
                }
                StyledText {
                    Layout.fillWidth: true
                    visible: Todo.list.length === 0
                    text: "A little room for what’s next."
                    font.pixelSize: 12
                    color: Appearance.colors.colSubtext
                }
            }
        }
    }
}
