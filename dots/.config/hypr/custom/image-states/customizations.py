#!/usr/bin/env python3
"""Install distinct image/app placeholders with exact-version checks and rollback."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile

HERE = Path(__file__).resolve().parent

def plan(root):
    changes = []
    for item in json.loads((HERE / 'integration.json').read_text()):
        path = root / item['path']
        old = path.read_bytes()
        if old == item['after'].encode():
            continue
        if old not in [value.encode() for value in [item['before'], *item.get('previous', [])]]:
            raise RuntimeError(f'Changed upstream/custom file; review required: {path}')
        changes.append((path, old, item['after'].encode()))
    for rel, asset in json.loads((HERE / 'assets.json').read_text()).items():
        path = root / rel
        old = path.read_bytes() if path.exists() else None
        new = (HERE / asset).read_bytes()
        if old == new:
            continue
        if old is not None:
            raise RuntimeError(f'Customized asset; review required: {path}')
        changes.append((path, old, new))
    return changes

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(data)
    temp.chmod(0o644)
    temp.replace(path)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'install', 'restore'])
    parser.add_argument('--config-root', type=Path, default=Path.home()/'.config')
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    root = args.config_root.resolve()
    if args.action == 'restore':
        if not args.backup:
            parser.error('restore requires --backup')
        records = json.loads((args.backup/'manifest.json').read_text())
        # Refuse to overwrite edits made since this package was installed.
        for record in records:
            path = root/record['path']
            if not path.exists() or path.read_bytes() != (args.backup/record['installed']).read_bytes():
                raise RuntimeError(f'File changed after install: {path}')
        for record in records:
            path = root/record['path']
            if record['original'] is None:
                path.unlink()
            else:
                write(path, (args.backup/record['original']).read_bytes())
        print('Restored', len(records), 'files')
        return
    changes = plan(root)
    print('Compatible:', len(changes), 'changes')
    if args.action == 'check' or not changes:
        return
    backups = Path.home()/'.local/state/hypr-image-state-backups'
    backups.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=backups))
    destination.chmod(0o700)
    records=[]
    for index, (path, old, new) in enumerate(changes):
        original=f'{index}.before' if old is not None else None
        if old is not None:
            (destination/original).write_bytes(old)
        installed=f'{index}.after'
        (destination/installed).write_bytes(new)
        records.append(dict(path=str(path.relative_to(root)), original=original, installed=installed))
    (destination/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    applied=[]
    try:
        for path, old, new in changes:
            applied.append((path,old))
            write(path,new)
    except Exception:
        for path,old in reversed(applied):
            if old is None:
                path.unlink(missing_ok=True)
            else:
                write(path,old)
        raise
    print('Installed. Backup:', destination)

if __name__ == '__main__':
    main()
