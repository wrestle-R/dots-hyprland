//@ pragma UseQApplication
import QtQuick
import QtQuick.Window
import Quickshell
ShellRoot {
    property bool dark: false
    Window {
        id: win
        width:800; height:400; visible:true
        title: "Local OCR verification"
        Rectangle {
            anchors.fill: parent
            color: dark ? "#1e1e1e" : "white"
            Column {
                x:24; y:24; spacing:8
                Repeater {
                    model: dark ? ['def greet(name):','    if name:','        print("Hello, " + name)','    else:','        return None','','result = greet("Alex")'] : ['The quick brown fox jumps over the lazy dog.','Please keep the original words and punctuation.','Local screenshots stay on this computer.']
                    delegate: Text { required property string modelData; text:modelData; textFormat:Text.PlainText; height:22; color:dark ? "#e8eaed" : "#222222"; font.family:dark ? "JetBrains Mono NF" : "Google Sans Flex"; font.pixelSize:14 }
                }
            }
        }
    }
    Timer {
        interval:1000;running:true
        onTriggered:win.contentItem.grabToImage(result=>{
            result.saveToFile(Quickshell.env("RDP_OCR_SAMPLE_DIR") + "/native-light-14.png");dark=true;second.start();
        })
    }
    Timer { id:second;interval:500;onTriggered:win.contentItem.grabToImage(result=>{result.saveToFile(Quickshell.env("RDP_OCR_SAMPLE_DIR") + "/native-dark-code-14.png");Qt.quit();}) }
}
