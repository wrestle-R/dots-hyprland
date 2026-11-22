"""Native settings-page smoke and interaction checks with a disposable helper."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='fingerprint-ui-') as directory:
    root = Path(directory)
    config = root/'config'; shell = config/'quickshell/ii'
    shutil.copytree(Path.home()/'.config/quickshell/ii', shell, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile(HERE/'FingerprintConfig.qml', shell/'modules/settings/FingerprintConfig.qml')
    shutil.copyfile(HERE/'fingerprint_settings.py', shell/'services/fingerprint_settings.py')
    # Only the read-only initial status contacts the real service. All mutations use this adapter.
    helper = root/'fake_helper.py'
    helper.write_text('''import json,sys,time,signal
state=dict(event="state",ok=True,available=True,device="Preview reader",stages=13,enrolled=["right-index-finger"])
def emit(**v): print(json.dumps(v),flush=True)
def stop(*args):
 emit(event="cancelled",ok=True,message="Enrollment stopped.")
 emit(**state)
 sys.exit(0)
signal.signal(signal.SIGTERM,stop)
if sys.argv[1]=="enroll":
 emit(event="progress",ok=True,done=False,completed=4,stages=13,message="Lift your finger and place it again.")
 while True: time.sleep(.1)
elif sys.argv[1]=="remove":
 state["enrolled"]=[]
 emit(**state)
else: emit(**state)
''')
    colors = Path.home()/'.local/state/quickshell/user/generated/colors.json'
    if colors.exists():
        color_target = root/'state/quickshell/user/generated/colors.json'
        color_target.parent.mkdir(parents=True)
        shutil.copyfile(colors, color_target)
    integration = json.loads((HERE/'integration.json').read_text())
    settings = next(e['after'] for e in integration if e['path']=='quickshell/ii/settings.qml')
    settings = settings.replace('import Quickshell\n', 'import Quickshell\nimport Quickshell.Io\n')
    settings = settings.replace('    id: root\n', '''    id: root
    function named(item, name) { if(item.objectName === name) return item; for(const child of item.children || []) { const hit = named(child, name); if(hit) return hit; } return null; }
    property bool captured: false
    IpcHandler {
        target: "fingerprintTest"
        function lastPage(): void { root.currentPage = root.pages.length - 1; }
        function navigation(): string { return JSON.stringify({y:navScroll.contentY,height:navScroll.height,content:navScroll.contentHeight,bottom:navTabs.y+root.currentPage*56+56}); }
        function fullList(): void { pageLoader.item.receive(JSON.stringify({event:"state",ok:true,available:true,device:"Preview reader",stages:13,enrolled:pageLoader.item.fingers})); }
        function refresh(helper: string): void { pageLoader.item.helperPath = helper; root.named(pageLoader.item, "refreshFingerprints").click(); }
        function scrolling(): bool { return pageLoader.item.contentHeight > pageLoader.item.height; }
        function page(): void { root.currentPage = 3; }
        function status(): string { return JSON.stringify({loaded:!!pageLoader.item,available:pageLoader.item?.available,enrolled:pageLoader.item?.enrolled,busy:pageLoader.item?.busy,message:pageLoader.item?.message,completed:pageLoader.item?.completed,failed:pageLoader.item?.failed}); }
        function enroll(helper: string): void { pageLoader.item.helperPath = helper; root.named(pageLoader.item, "addFingerprint").click(); }
        function cancel(): void { root.named(pageLoader.item, "cancelEnrollment").click(); }
        function remove(helper: string): void { pageLoader.item.helperPath = helper; root.named(pageLoader.item, "removeFingerprint-right-index-finger").click(); root.named(pageLoader.item, "confirmFingerprintAction").click(); }
        function resize(w: int, h: int): void { root.width=w; root.height=h; }
        function capture(path: string): void { root.captured = false; captureLayout.grabToImage(function(result) { root.captured = result.saveToFile(path); }); }
        function captured(): bool { return root.captured; }
        function close(): void { Qt.quit(); }
    }
''',1)
    settings = settings.replace('    ColumnLayout {', '    ColumnLayout {\n        id: captureLayout', 1)
    (shell/'fingerprint-test.qml').write_text(settings)
    env = dict(os.environ, XDG_CONFIG_HOME=str(config), XDG_STATE_HOME=str(root/'state'), XDG_CACHE_HOME=str(root/'cache'), QT_QPA_PLATFORM='wayland')
    with (root/'native.log').open('w+') as log:
        process = subprocess.Popen(['dbus-run-session','--','qs','-p',str(shell/'fingerprint-test.qml'),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
        def call(name,*args):
            return subprocess.check_output(['qs','-p',str(shell/'fingerprint-test.qml'),'ipc','call','fingerprintTest',name,*map(str,args)],text=True,stderr=subprocess.STDOUT,timeout=5).strip()
        def state(): return json.loads(call('status'))
        def wait_for(predicate, seconds=10):
            until=time.monotonic()+seconds
            while time.monotonic()<until and process.poll() is None:
                try:
                    value=state()
                    if predicate(value): return value
                except (subprocess.SubprocessError,ValueError): pass
                time.sleep(.1)
            log.seek(0);raise AssertionError(log.read()[-6000:])
        try:
            wait_for(lambda s:s['loaded'])
            call('page')
            wait_for(lambda s:s.get('available') and not s['busy'])
            if os.environ.get('FINGERPRINT_CAPTURE_DIR'):
                for width,height in ((1100,750),(750,500),(1450,900)):
                    call('resize',width,height);time.sleep(.4)
                    call('capture',str(Path(os.environ['FINGERPRINT_CAPTURE_DIR'])/f'fingerprints-{width}x{height}.png'));time.sleep(1)
                    if call('captured') != 'true':
                        log.seek(0); raise AssertionError(log.read()[-5000:])
            call('resize',750,500);call('lastPage');time.sleep(.6)
            nav=json.loads(call('navigation'))
            assert nav['y'] > 0 and nav['bottom'] <= nav['y']+nav['height']+1, nav
            call('page');time.sleep(.5)
            wait_for(lambda s:s.get('available') and not s['busy'])
            call('fullList')
            assert call('scrolling') == 'true', 'Long finger list must scroll'
            call('refresh',helper)
            wait_for(lambda s:not s['busy'] and len(s['enrolled'])==1)
            call('enroll', helper)
            wait_for(lambda s:s['busy'] and s['completed']==4)
            call('cancel')
            wait_for(lambda s:not s['busy'] and s['message']=='Enrollment stopped.')
            call('remove',helper)
            wait_for(lambda s:not s['busy'] and s['enrolled']==[])
            assert not state()['failed'], state()
        finally:
            if process.poll() is None:
                try: call('close')
                except subprocess.SubprocessError: process.terminate()
            process.wait(timeout=10)
        log.seek(0);text=log.read()
        if os.environ.get('FINGERPRINT_CAPTURE_DIR'):
            Path(os.environ['FINGERPRINT_CAPTURE_DIR']).joinpath('native.log').write_text(text)
        for error in ('FingerprintConfig.qml', 'fingerprint-test.qml'):
            relevant=[line for line in text.splitlines() if error in line and any(marker in line for marker in ('ReferenceError','TypeError','Cannot assign','is not a type'))]
            assert not relevant, relevant
print('PASS: native settings navigation, live reader status, simulated enrollment progress, cancel and per-finger removal')
