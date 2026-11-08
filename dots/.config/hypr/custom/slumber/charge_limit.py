#!/usr/bin/python3
"""Root-owned charge threshold setter. Fixed sysfs paths; no arbitrary files/commands."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import tempfile

STATE = Path('/var/lib/rdp-charge-limit/settings.json')
SYSFS = Path('/sys/class/power_supply')


def thresholds(limit):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 55 <= limit <= 100:
        raise ValueError('Limit must be an integer from 55 to 100')
    return limit - 5, limit


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def write_pair(directory, start, end):
    a = directory/'charge_control_start_threshold'
    b = directory/'charge_control_end_threshold'
    # Lower start first so lowering end cannot conflict with the old start.
    if start < int(a.read_text()): a.write_text(str(start))
    b.write_text(str(end))
    a.write_text(str(start))
    if (int(a.read_text()), int(b.read_text())) != (start, end):
        raise RuntimeError('Hardware did not retain requested thresholds')


def apply(limit, enabled=True):
    thresholds(limit)
    start, end = thresholds(limit if enabled else 100)
    devices = [p for p in sorted(SYSFS.glob('BAT[0-9]*')) if (p/'charge_control_start_threshold').exists() and (p/'charge_control_end_threshold').exists()]
    if not devices: raise RuntimeError('Hardware charge thresholds unavailable')
    before = [(p, int((p/'charge_control_start_threshold').read_text()), int((p/'charge_control_end_threshold').read_text())) for p in devices]
    previous = STATE.read_text() if STATE.exists() else None
    original = json.loads(previous).get('original') if previous else {p.name:[a,b] for p,a,b in before}
    try:
        for p,_,_ in before: write_pair(p, start, end)
        atomic(STATE, json.dumps({'enabled':enabled,'limit':limit,'original':original})+'\n')
    except Exception:
        errors = []
        for p,a,b in reversed(before):
            try: write_pair(p,a,b)
            except Exception as exc: errors.append(str(exc))
        if errors: raise RuntimeError('Apply failed; hardware rollback also failed: ' + '; '.join(errors))
        raise
    return {'enabled':enabled,'limit':end}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['apply','off','restore','original'])
    parser.add_argument('limit', nargs='?', type=int, default=95)
    args = parser.parse_args()
    if os.geteuid() != 0: raise RuntimeError('Authentication is required')
    if args.action == 'restore':
        if not STATE.exists(): return
        data = json.loads(STATE.read_text()); print(json.dumps(apply(int(data['limit']), bool(data['enabled']))))
    elif args.action == 'original':
        if not STATE.exists(): return
        data=json.loads(STATE.read_text())
        for name,pair in data['original'].items():
            if not name.startswith('BAT') or '/' in name: raise ValueError('Invalid battery identity')
            write_pair(SYSFS/name,*pair)
        STATE.unlink()
        print('Original charge thresholds restored')
    else:
        print(json.dumps(apply(args.limit, args.action == 'apply')))

if __name__ == '__main__':
    try:
        with open("/run/lock/rdp-charge-limit.lock", "a") as guard:
            fcntl.flock(guard, fcntl.LOCK_EX)
            main()
    except Exception as exc:
        print(json.dumps({'error':str(exc)})); raise SystemExit(1)
