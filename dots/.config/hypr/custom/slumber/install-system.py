#!/usr/bin/python3
"""Install the reviewed SDDM theme and narrow charge helper; never restarts SDDM."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from customizations import write, transact

HERE=Path(__file__).resolve().parent
ROOT=Path('/var/lib/rdp-desktop')
INDEX=ROOT/'installed.json'


def command(*args):
    subprocess.run(args,check=True,timeout=15,capture_output=True)


def install(wallpaper):
    targets={
        Path('/usr/local/libexec/rdp-charge-limit'):(HERE/'charge_limit.py').read_bytes(),
        Path('/etc/systemd/system/rdp-charge-limit.service'):(HERE/'rdp-charge-limit.service').read_bytes(),
        Path('/etc/sddm.conf.d/90-rdp-slumber.conf'):b'[Theme]\nCurrent=rdp-slumber\n',
    }
    for name in ['Main.qml','metadata.desktop','theme.conf']:
        targets[Path('/usr/share/sddm/themes/rdp-slumber')/name]=(HERE/'sddm'/name).read_bytes()
    targets[Path('/usr/share/sddm/themes/rdp-slumber/wallpaper.jpg')]=wallpaper.read_bytes()
    known=json.loads(INDEX.read_text()) if INDEX.exists() else {}
    changes=[]
    for path,new in targets.items():
        if path.is_symlink():raise RuntimeError(f'Refusing symlink: {path}')
        for parent in path.parents:
            if parent.is_symlink():raise RuntimeError(f'Refusing symlink parent: {parent}')
        old=path.read_bytes() if path.exists() else None
        if old==new:continue
        if old is not None and hashlib.sha256(old).hexdigest()!=known.get(str(path)):
            raise RuntimeError(f'Unknown system customization; no writes: {path}')
        changes.append((path,old,new))
    if not changes:
        print('System integration already current');return
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    saved=Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'),dir=ROOT));saved.chmod(0o700)
    records=[]
    enabled=subprocess.run(['systemctl','is-enabled','rdp-charge-limit.service'],capture_output=True,text=True).stdout.strip()=='enabled'
    for i,(path,old,new) in enumerate(changes):
        if old is not None:write(saved/f'{i}.before',old,0o600)
        write(saved/f'{i}.after',new,0o600)
        records.append({'path':str(path),'before':f'{i}.before' if old is not None else None,'after':f'{i}.after'})
    write(saved/'manifest.json',json.dumps({'files':records,'service_enabled':enabled,'index':known},indent=2).encode(),0o600)
    try:
        transact(changes)
        os.chmod('/usr/local/libexec/rdp-charge-limit',0o755)
        # Theme assets must be readable by SDDM; created dirs are public.
        for path in targets:
            path.chmod(0o755 if str(path)=='/usr/local/libexec/rdp-charge-limit' else 0o644)
        command('systemctl','daemon-reload')
        command('systemctl','enable','rdp-charge-limit.service')
        write(INDEX,json.dumps({str(p):hashlib.sha256(v).hexdigest() for p,v in targets.items()},indent=2).encode(),0o600)
    except Exception:
        transact([(path,new,old) for path,old,new in reversed(changes)])
        if not enabled:subprocess.run(['systemctl','disable','rdp-charge-limit.service'],capture_output=True)
        subprocess.run(['systemctl','daemon-reload'],capture_output=True)
        raise
    print(f'System integration installed. Backup: {saved}. Current session and charge limits unchanged.')


def restore(saved):
    if not saved.resolve().is_relative_to(ROOT.resolve()):raise RuntimeError('Not a system integration backup')
    data=json.loads((saved/'manifest.json').read_text());changes=[]
    for item in reversed(data['files']):
        p=Path(item['path']);old=p.read_bytes() if p.exists() else None
        if old!=(saved/item['after']).read_bytes():raise RuntimeError(f'Edited after install; refusing overwrite: {p}')
        changes.append((p,old,(saved/item['before']).read_bytes() if item['before'] else None))
    # Thresholds were not changed by installation. Restore original thresholds
    # separately with the helper before uninstalling if the controls were used.
    transact(changes)
    if not data['service_enabled']:subprocess.run(['systemctl','disable','rdp-charge-limit.service'],capture_output=True)
    command('systemctl','daemon-reload')
    write(INDEX,json.dumps(data['index']).encode(),0o600)
    print('System files restored. No display manager restart performed.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install','restore'])
    parser.add_argument('--wallpaper',type=Path,default=Path('/home/rdp/Pictures/Wallpapers/hehe.jpg'))
    parser.add_argument('--backup',type=Path)
    args=parser.parse_args()
    if os.geteuid()!=0:raise RuntimeError('Run through pkexec or sudo')
    if args.action=='install':install(args.wallpaper)
    else:
        if not args.backup:parser.error('restore requires --backup')
        restore(args.backup)

if __name__=='__main__':main()
