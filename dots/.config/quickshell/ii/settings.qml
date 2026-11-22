//@ pragma UseQApplication
//@ pragma Env QS_NO_RELOAD_POPUP=1
//@ pragma Env QT_QUICK_CONTROLS_STYLE=Basic
//@ pragma Env QT_QUICK_FLICKABLE_WHEEL_DECELERATION=10000

// Adjust this to make the app smaller or larger
//@ pragma Env QT_SCALE_FACTOR=1

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Quickshell
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions as CF

ApplicationWindow {
    id: root
    property string firstRunFilePath: CF.FileUtils.trimFileProtocol(`${Directories.state}/user/first_run.txt`)
    property string firstRunFileContent: "This file is just here to confirm you've been greeted :>"
    property real contentPadding: 8
    property bool showNextTime: false
    property var pages: [
        {name: Translation.tr("General"), icon: "browse", component: "modules/settings/GeneralConfig.qml"},
        {name: Translation.tr("Appearance"), icon: "palette", component: "modules/settings/QuickConfig.qml"},
        {name: Translation.tr("Keybindings"), icon: "keyboard", component: "modules/settings/KeybindingsConfig.qml"},
        {name: Translation.tr("Fingerprint"), icon: "fingerprint", component: "modules/settings/FingerprintConfig.qml"},
        {name: Translation.tr("Notifications"), icon: "notifications", component: "modules/settings/NotificationsConfig.qml"},
        {name: Translation.tr("Services"), icon: "settings", component: "modules/settings/ServicesConfig.qml"},
        {name: Translation.tr("Advanced"), icon: "construction", component: "modules/settings/DetailsConfig.qml"}
    ]
    property int currentPage: 0

    visible: true
    onClosing: Qt.quit()
    title: "illogical-impulse Settings"

    Component.onCompleted: {
        MaterialThemeLoader.reapplyTheme()
        Config.readWriteDelay = 0 // Settings app always only sets one var at a time so delay isn't needed
    }

    minimumWidth: 750
    minimumHeight: 500
    width: 1100
    height: 750
    color: Appearance.m3colors.m3background

    ColumnLayout {
        anchors {
            fill: parent
            margins: contentPadding
        }

        Keys.onPressed: (event) => {
            if (event.modifiers === Qt.ControlModifier) {
                if (event.key === Qt.Key_PageDown) {
                    root.currentPage = Math.min(root.currentPage + 1, root.pages.length - 1)
                    event.accepted = true;
                } 
                else if (event.key === Qt.Key_PageUp) {
                    root.currentPage = Math.max(root.currentPage - 1, 0)
                    event.accepted = true;
                }
                else if (event.key === Qt.Key_Tab) {
                    root.currentPage = (root.currentPage + 1) % root.pages.length;
                    event.accepted = true;
                }
                else if (event.key === Qt.Key_Backtab) {
                    root.currentPage = (root.currentPage - 1 + root.pages.length) % root.pages.length;
                    event.accepted = true;
                }
            }
        }

        Item { // Titlebar
            visible: Config.options?.windows.showTitlebar
            Layout.fillWidth: true
            Layout.fillHeight: false
            implicitHeight: Math.max(titleText.implicitHeight, windowControlsRow.implicitHeight)
            StyledText {
                id: titleText
                anchors {
                    left: Config.options.windows.centerTitle ? undefined : parent.left
                    horizontalCenter: Config.options.windows.centerTitle ? parent.horizontalCenter : undefined
                    verticalCenter: parent.verticalCenter
                    leftMargin: 12
                }
                color: Appearance.colors.colOnLayer0
                text: Translation.tr("Settings")
                font {
                    family: Appearance.font.family.title
                    pixelSize: Appearance.font.pixelSize.title
                    variableAxes: Appearance.font.variableAxes.title
                }
            }
            RowLayout { // Window controls row
                id: windowControlsRow
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                RippleButton {
                    buttonRadius: Appearance.rounding.full
                    implicitWidth: 35
                    implicitHeight: 35
                    onClicked: root.close()
                    contentItem: MaterialSymbol {
                        anchors.centerIn: parent
                        horizontalAlignment: Text.AlignHCenter
                        text: "close"
                        iconSize: 20
                    }
                }
            }
        }

        RowLayout { // Window content with navigation rail and content pane
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: contentPadding
            Item {
                id: navRailWrapper
                Layout.fillHeight: true
                Layout.margins: 5
                implicitWidth: navRail.expanded ? 150 : fab.baseSize
                Behavior on implicitWidth {
                    animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                }
                StyledFlickable {
                    id: navScroll
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: navRail.implicitHeight
                    clip: true
                    function revealCurrent() {
                        const top = navTabs.y + root.currentPage * 56;
                        const bottom = top + 56;
                        let nextY = contentY;
                        if (top < contentY) nextY = top;
                        else if (bottom > contentY + height) nextY = bottom - height;
                        contentY = Math.max(0, Math.min(nextY, contentHeight - height));
                    }
                    onHeightChanged: Qt.callLater(revealCurrent)
                    Connections {
                        target: root
                        function onCurrentPageChanged() { Qt.callLater(navScroll.revealCurrent); }
                    }
                    NavigationRail { // Window content with navigation rail and content pane
                        id: navRail
                        width: navScroll.width
                        spacing: 10
                        expanded: root.width > 900

                        NavigationRailExpandButton {
                            focus: root.visible
                        }

                        FloatingActionButton {
                            id: fab
                            property bool justCopied: false
                            iconText: justCopied ? "check" : "edit"
                            buttonText: justCopied ? Translation.tr("Path copied") : Translation.tr("Config file")
                            expanded: navRail.expanded
                            downAction: () => {
                                Qt.openUrlExternally(`${Directories.config}/illogical-impulse/config.json`);
                            }
                            altAction: () => {
                                Quickshell.clipboardText = CF.FileUtils.trimFileProtocol(`${Directories.config}/illogical-impulse/config.json`);
                                fab.justCopied = true;
                                revertTextTimer.restart()
                            }

                            Timer {
                                id: revertTextTimer
                                interval: 1500
                                onTriggered: {
                                    fab.justCopied = false;
                                }
                            }

                            StyledToolTip {
                                text: Translation.tr("Open the shell config file\nAlternatively right-click to copy path")
                            }
                        }

                        NavigationRailTabArray {
                            id: navTabs
                            currentIndex: root.currentPage
                            expanded: navRail.expanded
                            Repeater {
                                model: root.pages
                                NavigationRailButton {
                                    required property var index
                                    required property var modelData
                                    toggled: root.currentPage === index
                                    onPressed: root.currentPage = index;
                                    expanded: navRail.expanded
                                    buttonIcon: modelData.icon
                                    buttonIconRotation: modelData.iconRotation || 0
                                    buttonText: navRail.expanded ? modelData.name : ""
                                    Accessible.name: modelData.name
                                    StyledToolTip { extraVisibleCondition: !navRail.expanded; text: modelData.name }
                                    showToggledHighlight: false
                                }
                            }
                        }

                        Item {
                            Layout.fillHeight: true
                        }
                    }
                }
            }
            Rectangle { // Content container
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Appearance.m3colors.m3surfaceContainerLow
                radius: Appearance.rounding.windowRounding - root.contentPadding

                Loader {
                    id: pageLoader
                    anchors.fill: parent
                    opacity: 1.0

                    active: Config.ready
                    Component.onCompleted: {
                        source = root.pages[0].component
                    }

                    Connections {
                        target: root
                        function onCurrentPageChanged() {
                            switchAnim.complete();
                            switchAnim.start();
                        }
                    }

                    SequentialAnimation {
                        id: switchAnim

                        NumberAnimation {
                            target: pageLoader
                            properties: "opacity"
                            from: 1
                            to: 0
                            duration: 100
                            easing.type: Appearance.animation.elementMoveExit.type
                            easing.bezierCurve: Appearance.animationCurves.emphasizedFirstHalf
                        }
                        ParallelAnimation {
                            PropertyAction {
                                target: pageLoader
                                property: "source"
                                value: root.pages[root.currentPage].component
                            }
                            PropertyAction {
                                target: pageLoader
                                property: "anchors.topMargin"
                                value: 20
                            }
                        }
                        ParallelAnimation {
                            NumberAnimation {
                                target: pageLoader
                                properties: "opacity"
                                from: 0
                                to: 1
                                duration: 200
                                easing.type: Appearance.animation.elementMoveEnter.type
                                easing.bezierCurve: Appearance.animationCurves.emphasizedLastHalf
                            }
                            NumberAnimation {
                                target: pageLoader
                                properties: "anchors.topMargin"
                                to: 0
                                duration: 200
                                easing.type: Appearance.animation.elementMoveEnter.type
                                easing.bezierCurve: Appearance.animationCurves.emphasizedLastHalf
                            }
                        }
                    }
                }
            }
        }
    }
}
