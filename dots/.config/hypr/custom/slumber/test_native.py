#!/usr/bin/env python3
"""Isolated timed state-machine test. Uses fake display/lid commands and a private D-Bus."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='slumber-native-') as directory:
    root=Path(directory); config=root/'config'; shell=config/'quickshell/ii'
    shutil.copytree(Path.home()/'.config/quickshell/ii',shell,ignore=shutil.ignore_patterns('__pycache__'))
    for rel,asset in json.loads((HERE/'assets.json').read_text()).items():
        target=config/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/asset,target)
    service=shell/'services/Slumber.qml'
    # No compositor-global shortcut registrations from a test instance.
    service.write_text('\n'.join(line for line in service.read_text().splitlines() if not ('Loader { active: root.hardwareOwner;' in line)))
    (shell/'services/slumber_backend.py').write_text('''import sys,time,json
if sys.argv[1]=='watch-lid':
 print(json.dumps({'ready':True,'closed':False}),flush=True)
 while True:time.sleep(1)
elif sys.argv[1]=='battery-status':print('{"supported":false,"batteries":[]}')
''')
    (shell/'state-test.qml').write_bytes((HERE/'state-test.qml.fixture').read_bytes())
    binary=root/'bin';binary.mkdir()
    (binary/'hyprctl').write_text('''#!/bin/sh
if [ "$1" = "-j" ] && [ "$2" = "monitors" ]; then
 printf '[{"name":"eDP-1","dpmsStatus":false,"width":1920,"height":1200,"id":0,"activeWorkspace":{"id":1}}]\\n'
else
 exec /usr/bin/hyprctl "$@"
fi
''');(binary/'hyprctl').chmod(0o755)
    # Guard against future changes accidentally invoking system suspend in tests.
    (binary/'systemctl').write_text('#!/bin/sh\nexit 77\n');(binary/'systemctl').chmod(0o755)
    env=os.environ.copy();env.update(XDG_CONFIG_HOME=str(config),XDG_STATE_HOME=str(root/'state'),XDG_CACHE_HOME=str(root/'cache'),QT_QPA_PLATFORM='wayland',PATH=str(binary)+':/usr/bin')
    result=subprocess.run(['dbus-run-session','--','qs','-p',str(shell/'state-test.qml')],env=env,capture_output=True,text=True,timeout=30)
    combined=result.stdout+result.stderr
    if 'STATE_TEST_PASS' not in combined or 'TEST_FAIL' in combined:
        print(combined[-8000:]);raise SystemExit(1)
    print('PASS: no DPMS before secure confirmation, protected lid state, hidden notification suppression, allowed wake, real six-second reblank, user interaction, unlock cleanup, lock-timeout fail-safe')
