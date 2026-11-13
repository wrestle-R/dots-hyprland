import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io

FocusScope {
    id: root
    property bool active: GlobalStates.sidebarLeftOpen
    property string kind: "todo"
    property var state: ({items: [], outbox: []})
    property bool connected: false
    property string errorText: ""
    property var suggestions: []
    property string searchedText: ""
    readonly property string executable: Quickshell.env("HOME") + "/.local/bin/tick-and-done"
    readonly property var unfinished: (state.items || []).filter(i => i.kind === root.kind && !i.done && !i.deletedAt && !i.parentId).sort((a,b) => a.position-b.position || a.id.localeCompare(b.id))
    readonly property var finished: (state.items || []).filter(i => i.kind === root.kind && i.done && !i.deletedAt && !i.parentId).sort((a,b) => Date.parse(b.updatedAt)-Date.parse(a.updatedAt))
    readonly property int completedSlots: Math.max(0, Math.floor(rows.height / 38) - unfinished.length - 1)
    readonly property var items: unfinished.concat(finished.slice(0, completedSlots))
    function focusActiveItem() { if (connected) input.forceActiveFocus();  }
    function refresh() { if (!read.running) { read.command = [executable, "--ipc", JSON.stringify({action:"state"})]; read.running = true; } }
    function mutate(value) { if (write.running) return; value.expectedAccount = root.state._account; write.command = [executable, "--ipc", JSON.stringify(value)]; write.running = true; }
    function addManual() { if(input.text.trim() && !write.running){mutate({action:"add",kind:kind,title:input.text.trim()});input.text="";suggestions=[];} }
    onKindChanged: {input.text=""; suggestions=[];errorText="";}
    onActiveChanged: { if (active) { kind = "todo"; refresh(); Qt.callLater(focusActiveItem); } }
    Component.onCompleted: refresh()
    Timer { interval: 1500; repeat: true; running: root.active; onTriggered: root.refresh() }
    Timer { id: searchDelay; interval: 350; onTriggered: {
        if(root.kind!=="movie" || input.text.trim().length<2 || search.running) return;
        root.searchedText=input.text.trim();
        search.command=[root.executable,"--ipc",JSON.stringify({action:"search",query:root.searchedText,expectedAccount:root.state._account})];search.running=true;
    } }
    Process {
        id: read
        stdout: StdioCollector { onStreamFinished: { try { const data=JSON.parse(text);root.connected=!data.error;if(root.connected){if(root.state._account!==data._account){root.suggestions=[];input.text="";}root.state=data;} } catch(e) {root.connected=false;} } }
    }
    Process {
        id: write
        stdout: StdioCollector { onStreamFinished: {try {const data=JSON.parse(text);if(data.error)root.errorText=data.error;else{if(data.items)root.state=data;root.errorText=data.existingId?"Already on your watchlist.":"";}}catch(e){root.errorText="Could not save. Try again.";} } }
        onExited: root.refresh()
    }
    Process {
        id: search
        stdout: StdioCollector { onStreamFinished: {try {const data=JSON.parse(text);if(root.kind==="movie"&&input.text.trim()===root.searchedText&&data._account===root.state._account){root.suggestions=(data.results||[]).slice(0,4);root.errorText="";}else if(data.error)root.errorText=data.error;}catch(e){root.suggestions=[];} } }
        onExited: {if(input.text.trim()!==root.searchedText) searchDelay.restart();}
    }
    Process { id: playback; command:["python3",Quickshell.env("HOME")+"/.local/lib/tick-and-done/spotify.py","toggle"] }
    StyledText { anchors.centerIn: parent; visible: !root.connected; text: "Open Task-tick and sign in to connect your lists."; wrapMode: Text.Wrap; width: parent.width - 40; horizontalAlignment: Text.AlignHCenter; color: Appearance.colors.colSubtext }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 14; spacing: 12; visible: root.connected
        HyprTrackSummary { Layout.fillWidth: true; Layout.maximumHeight: implicitHeight; active: root.active && root.visible }
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true; radius: 18
            color: Appearance.colors.colLayer1
            border.width: 1; border.color: Appearance.colors.colLayer0Border
            ColumnLayout {
                anchors.fill:parent;anchors.margins:14;spacing:10
                RowLayout {
                    Layout.fillWidth:true
                    StyledText {text:"Task-tick";font.pixelSize:15;font.weight:Font.DemiBold;Layout.fillWidth:true}
                    StyledText {text:root.unfinished.length+" left";font.pixelSize:11;color:Appearance.colors.colSubtext}
                }
                Rectangle {
                    Layout.fillWidth:true;implicitHeight:38;radius:10;color:Appearance.colors.colLayer0
                    RowLayout {anchors.fill:parent;anchors.margins:3;spacing:3
                        Repeater {model:[{kind:"todo",title:"Todos"},{kind:"movie",title:"Movies"}]
                            delegate: Button {
                                required property var modelData
                                Layout.fillWidth:true;Layout.fillHeight:true
                                onClicked:root.kind=modelData.kind
                                Accessible.name:modelData.title
                                contentItem:StyledText{text:modelData.title;horizontalAlignment:Text.AlignHCenter;font.pixelSize:12;font.weight:root.kind===modelData.kind?Font.DemiBold:Font.Normal;color:root.kind===modelData.kind?Appearance.colors.colOnLayer1:Appearance.colors.colSubtext}
                                background:Rectangle{radius:8;color:root.kind===parent.modelData.kind?Appearance.colors.colLayer2:"transparent";border.width:root.kind===parent.modelData.kind?1:0;border.color:Appearance.colors.colLayer0Border}
                            }
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth:true;implicitHeight:42;radius:10;color:Appearance.colors.colLayer0
                    border.width:input.activeFocus?1:0;border.color:Appearance.colors.colPrimary
                    RowLayout {anchors.fill:parent;anchors.leftMargin:12;anchors.rightMargin:5;spacing:4
                        TextField {
                            id:input;Layout.fillWidth:true;Layout.fillHeight:true;maximumLength:500;font.pixelSize:12;color:Appearance.colors.colOnLayer1
                            placeholderText:root.kind==="todo"?"Add a thought…":"Find a film or TV title…";placeholderTextColor:Appearance.colors.colSubtext
                            background:Item{}
                            padding:0
                            Keys.onSpacePressed: event => {if(text.trim().length===0){event.accepted=true;if(!playback.running)playback.running=true;}else event.accepted=false;}
                            onAccepted:root.addManual()
                            onTextChanged:{root.suggestions=[];searchDelay.restart();}
                        }
                        Button {implicitWidth:32;implicitHeight:32;enabled:input.text.trim().length>0&&!write.running;onClicked:root.addManual();Accessible.name:"Add item"
                            contentItem:StyledText{text:"+";font.pixelSize:22;horizontalAlignment:Text.AlignHCenter;color:Appearance.colors.colPrimary}
                            background:Rectangle{radius:8;color:parent.down?Appearance.colors.colLayer2:"transparent"}
                        }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth:true;spacing:0;visible:root.suggestions.length>0
                    Repeater {model:root.suggestions
                        delegate:Button {
                            required property var modelData;Layout.fillWidth:true;implicitHeight:40
                            onClicked:{root.mutate({action:"add",kind:"movie",title:modelData.title||modelData.name,tmdbId:modelData.id,mediaType:modelData.media_type,poster:modelData.poster_path});input.text="";root.suggestions=[];}
                            contentItem:StyledText{text:(modelData.title||modelData.name)+" · "+(modelData.media_type==="tv"?"TV":"Film");font.pixelSize:12;elide:Text.ElideRight}
                            background:Rectangle{radius:7;color:parent.hovered?Appearance.colors.colLayer2:"transparent"}
                        }
                    }
                }
                ListView {
                    id:rows;Layout.fillWidth:true;Layout.fillHeight:true;clip:true;model:root.items;spacing:0
                    ScrollBar.vertical:StyledScrollBar{}
                    delegate:Item {
                        id:row;required property var modelData;required property int index
                        readonly property bool firstDone: modelData.done && (index===0||!root.items[index-1].done)
                        width:ListView.view.width;height:firstDone?66:38
                        StyledText {visible:row.firstDone;text:root.kind==="todo"?"Completed":"Watched";font.pixelSize:10;color:Appearance.colors.colSubtext;anchors.top:parent.top;anchors.topMargin:10}
                        RowLayout {
                            anchors.left:parent.left;anchors.right:parent.right;anchors.bottom:parent.bottom;height:38;spacing:8
                            Button {
                                implicitWidth:28;implicitHeight:34;enabled:!write.running
                                Accessible.name:(row.modelData.done?"Mark unfinished ":"Complete ")+row.modelData.title
                                onClicked:root.mutate({action:"toggle",kind:root.kind,id:row.modelData.id})
                                background:Item{}
                                contentItem:Item {Rectangle {anchors.centerIn:parent;width:15;height:15;radius:4;border.width:1;border.color:row.modelData.done?Appearance.colors.colSubtext:Appearance.colors.colOutline;color:row.modelData.done?Appearance.colors.colLayer2:"transparent";StyledText{anchors.centerIn:parent;text:row.modelData.done?"✓":"";font.pixelSize:11;color:Appearance.colors.colSubtext}}}
                            }
                            StyledText {Layout.fillWidth:true;text:row.modelData.title;textFormat:Text.PlainText;elide:Text.ElideRight;font.pixelSize:13;font.strikeout:row.modelData.done;color:row.modelData.done?Appearance.colors.colSubtext:Appearance.colors.colOnLayer1}
                        }
                    }
                    StyledText {anchors.centerIn:parent;visible:root.items.length===0;text:"A little breathing room.";font.pixelSize:12;color:Appearance.colors.colSubtext}
                }
                StyledText {visible:root.finished.length>root.completedSlots;text:(root.finished.length-Math.min(root.finished.length,root.completedSlots))+" more completed in the app";font.pixelSize:10;color:Appearance.colors.colSubtext}
                StyledText {visible:root.errorText!=="";text:root.errorText;wrapMode:Text.Wrap;Layout.fillWidth:true;color:Appearance.colors.colSubtext;font.pixelSize:11}
                StyledText {text:(root.state.outbox||[]).length?`${root.state.outbox.length} waiting to sync`:"Saved on this device";color:Appearance.colors.colSubtext;font.pixelSize:10}
            }
        }
    }
}
