#!/usr/bin/env python3
"""Checked desktop integration: all-file preflight, private backups, atomic writes and rollback."""
import argparse
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import tempfile

HERE=Path(__file__).resolve().parent


def destination(root, relative):
    rel=Path(relative)
    if rel.is_absolute() or '..' in rel.parts: raise RuntimeError('Unsafe integration path')
    path=root/rel
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise RuntimeError(f'Symlink/outside config root: {path}')
    return path


def plan(root):
    changes=[]
    versions=json.loads((HERE/'asset-versions.json').read_text()) if (HERE/'asset-versions.json').exists() else {}
    # Assets first, watched consumers next, shell entry point last.
    for relative,asset in json.loads((HERE/'assets.json').read_text()).items():
        path=destination(root,relative); old=path.read_bytes() if path.exists() else None; new=(HERE/asset).read_bytes()
        if old==new: continue
        if old is not None and hashlib.sha256(old).hexdigest() not in versions.get(relative,[]): raise RuntimeError(f'Changed custom asset; review required: {path}')
        changes.append((path,old,new))
    for item in sorted(json.loads((HERE/'integration.json').read_text()),key=lambda x:x['path']=='quickshell/ii/shell.qml'):
        path=destination(root,item['path']); old=path.read_bytes()
        variants=[item,*item.get('variants',[])]
        if any(old==v['after'].encode() for v in variants): continue
        selected=next((v for v in variants if old in [v['before'].encode(),*[value.encode() for value in v.get('previous',[])]]),None)
        if selected is None: raise RuntimeError(f'Changed upstream/custom file; no writes: {path}')
        changes.append((path,old,selected['after'].encode()))
    return changes


def write(path,data,mode=0o644):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.chmod(name,mode); os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def transact(changes):
    applied=[]
    try:
        for path,old,new in changes:
            current=path.read_bytes() if path.exists() else None
            if current!=old: raise RuntimeError(f'File changed during installation: {path}')
            mode=path.stat().st_mode & 0o777 if path.exists() else (0o755 if path.name == "screen-ocr" else 0o644)
            applied.append((path,old,mode))
            if new is None: path.unlink()
            else: write(path,new,mode)
    except Exception:
        errors=[]
        for path,old,mode in reversed(applied):
            try:
                if old is None: path.unlink(missing_ok=True)
                else: write(path,old,mode)
            except Exception as exc: errors.append(str(exc))
        if errors: raise RuntimeError('Rollback incomplete: '+'; '.join(errors))
        raise


def install(root,backup_root):
    if root.resolve() == (Path.home()/'.config').resolve():
        data=Path.home()/'.local/share/rdp-screen-ocr'
        if not (data/'venv/bin/python').exists(): raise RuntimeError('Run OCR setup before installation')
        for entry in json.loads((HERE/'models.json').read_text()).values():
            model=data/'models'/entry['file']
            if not model.exists() or hashlib.sha256(model.read_bytes()).hexdigest()!=entry['sha256']: raise RuntimeError('Run OCR setup: models missing or checksum mismatch')
    changes=plan(root)
    if not changes: print('Compatible: 0 changes'); return None
    backup_root.mkdir(parents=True,exist_ok=True,mode=0o700)
    saved=Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'),dir=backup_root));saved.chmod(0o700)
    records=[]
    for i,(path,old,new) in enumerate(changes):
        if old is not None: write(saved/f'{i}.before',old,0o600)
        write(saved/f'{i}.after',new,0o600)
        records.append({'path':str(path.relative_to(root)),'before':f'{i}.before' if old is not None else None,'after':f'{i}.after'})
    write(saved/'manifest.json',json.dumps({'root':str(root.resolve()),'files':records},indent=2).encode(),0o600)
    transact(changes)
    print(f'Installed {len(changes)} files. Backup: {saved}')
    return saved


def restore(root,saved):
    manifest=json.loads((saved/'manifest.json').read_text())
    if str(root.resolve())!=manifest['root']: raise RuntimeError('Backup belongs to another config root')
    changes=[]
    for item in reversed(manifest['files']):
        path=destination(root,item['path']); current=path.read_bytes() if path.exists() else None
        if current!=(saved/item['after']).read_bytes(): raise RuntimeError(f'Edited after install; restore refused: {path}')
        changes.append((path,current,(saved/item['before']).read_bytes() if item['before'] else None))
    transact(changes)
    print(f'Restored {len(changes)} files')


def checkpoint(root,baseline,backup_root):
    if plan(root): raise RuntimeError('Install latest package before taking rollback checkpoint')
    manifest=json.loads((baseline/'manifest.json').read_text())
    if manifest['root']!=str(root.resolve()): raise RuntimeError('Baseline belongs to another config root')
    backup_root.mkdir(parents=True,exist_ok=True,mode=0o700)
    saved=Path(tempfile.mkdtemp(prefix='rollback-',dir=backup_root));saved.chmod(0o700)
    records=[]
    for i,item in enumerate(manifest['files']):
        before=f'{i}.before' if item['before'] else None
        if before: write(saved/before,(baseline/item['before']).read_bytes(),0o600)
        after=f'{i}.after'
        write(saved/after,destination(root,item['path']).read_bytes(),0o600)
        records.append({'path':item['path'],'before':before,'after':after})
    write(saved/'manifest.json',json.dumps({'root':str(root.resolve()),'files':records},indent=2).encode(),0o600)
    print('Combined rollback checkpoint:',saved)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['check','install','restore','checkpoint'])
    parser.add_argument('--config-root',type=Path,default=Path.home()/'.config')
    parser.add_argument('--backup',type=Path)
    parser.add_argument('--backup-root',type=Path,default=Path.home()/'.local/state/hypr-ocr-backups')
    args=parser.parse_args();root=args.config_root.resolve()
    if args.action=='check': print(f'Compatible: {len(plan(root))} changes')
    elif args.action=='install': install(root,args.backup_root)
    elif args.action=='checkpoint':
        if not args.backup: parser.error('checkpoint requires --backup BASELINE')
        checkpoint(root,args.backup,args.backup_root)
    else:
        if not args.backup: parser.error('restore requires --backup')
        restore(root,args.backup)

if __name__=='__main__': main()
