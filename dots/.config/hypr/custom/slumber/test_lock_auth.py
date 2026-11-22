"""Run the real lock context with isolated PAM adapters, never the desktop lock."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
entry = next(x for x in json.loads((HERE/'integration.json').read_text())
             if x['path'].endswith('/LockContext.qml'))
context = entry['after']
with tempfile.TemporaryDirectory(prefix='lock-auth-test-') as directory:
    root = Path(directory)
    context = context.replace('import qs\n', '').replace('import qs.modules.common\n', '')
    context = context.replace('import Quickshell.Services.Pam', 'import "stubs"')
    context = context.replace('PamContext {', 'FakePam {')
    context = context.replace('enum ActionEnum', 'function miss() { fingerPam.finish(1); }\n    function failPassword() { pam.finish(1); }\n    function match() { fingerPam.finish(0); }\n    enum ActionEnum')
    context = context.replace('id: pam\n', 'id: pam\n        objectName: "passwordPam"\n')
    context = context.replace('id: fingerPam\n', 'id: fingerPam\n        objectName: "fingerPam"\n')
    context = context.replace('["fprintd-list", Quickshell.env("USER")]', '["printf", "Fingerprints for user tester"]')
    (root/'LockContext.qml').write_text(context)
    stubs = root/'stubs'; stubs.mkdir()
    (stubs/'qmldir').write_text('FakePam 1.0 FakePam.qml\nsingleton GlobalStates 1.0 GlobalStates.qml\nsingleton PamResult 1.0 PamResult.qml\n')
    (stubs/'GlobalStates.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { property bool screenLocked: true; property bool screenUnlockFailed: false; property bool screenLockContainsCharacters: false }')
    # QML enums match the real plugin's result type.
    (stubs/'PamResult.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { enum Result { Success, Failed } }')
    (stubs/'FakePam.qml').write_text('''import QtQuick
QtObject {
 property bool active: false
 property bool responseRequired: false
 property string configDirectory
 property string config
 signal pamMessage()
 signal completed(int result)
 function start() { active = true; }
 function abort() { active = false; }
 function respond(text) {}
 function finish(result) { active = false; completed(result); }
}''')
    (root/'shell.qml').write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "stubs"
ShellRoot {
 id: test
 property int unlocks: 0
 LockContext { id: context; onUnlocked: { test.unlocks++; GlobalStates.screenLocked = false; reset(); } }
 IpcHandler {
  target: "authTest"
  function status(): string { return JSON.stringify({scanning:context.fingerprintScanning,unlocks:test.unlocks,text:context.currentText,busy:context.unlockInProgress}); }
  function missed(): void { context.miss(); }
  function type(): void { context.currentText = "fixture"; context.resetClearTimer(); }
  function password(): void { context.tryUnlock(); }
  function failPassword(): void { context.failPassword(); }
  function finger(): void { context.match(); }
  function close(): void { Qt.quit(); }
 }
}''')
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    with (root/'log').open('w+') as log:
        process = subprocess.Popen(['qs','-p',str(root/'shell.qml'),'--no-color'], env=env, stdout=log, stderr=subprocess.STDOUT)
        def call(name):
            return subprocess.check_output(['qs','-p',str(root/'shell.qml'),'ipc','call','authTest',name], text=True, stderr=subprocess.STDOUT, timeout=5).strip()
        def state(): return json.loads(call('status'))
        def eventually(predicate, timeout=3):
            end=time.monotonic()+timeout
            while time.monotonic()<end:
                if process.poll() is not None: break
                try:
                    if predicate(state()): return
                except subprocess.SubprocessError: pass
                time.sleep(.1)
            log.seek(0)
            raise AssertionError('Lock authentication state did not recover: '+log.read()[-2500:])
        try:
            eventually(lambda s:s['scanning'])
            call('missed')
            eventually(lambda s:s['scanning'])
            call('type')
            eventually(lambda s:not s['text'] and s['scanning'], timeout=12)
            call('password')
            call('failPassword')
            eventually(lambda s:s['scanning'] and not s['busy'])
            call('finger')
            eventually(lambda s:s['unlocks']==1 and not s['scanning'])
        finally:
            process.terminate(); process.wait(timeout=5)
print('PASS: scan retries, password-clear timeout retains reader, password failure recovers, fingerprint unlock stops scanning')
