#!/usr/bin/env python3
"""Bounded, local-only helpers. Never stores passwords or notification text."""
import argparse
import glob
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def lid_closed():
    paths = glob.glob('/proc/acpi/button/lid/*/state')
    if not paths:
        raise RuntimeError('No readable laptop lid sensor')
    return any('closed' in Path(p).read_text().lower() for p in paths)


def watch_lid():
    from gi.repository import Gio, GLib
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    result, descriptors = bus.call_with_unix_fd_list_sync(
        'org.freedesktop.login1', '/org/freedesktop/login1',
        'org.freedesktop.login1.Manager', 'Inhibit',
        GLib.Variant('(ssss)', ('handle-lid-switch', 'Slumber',
                               'Use selected Slumber lid action', 'block')),
        GLib.VariantType.new('(h)'), Gio.DBusCallFlags.NONE, 5000, None, None)
    fd = descriptors.get(result.unpack()[0])
    signal.signal(signal.SIGTERM, lambda *_: exit(0))
    previous = None
    try:
        while True:
            closed = lid_closed()
            if closed != previous:
                print(json.dumps({'ready': True, 'closed': closed}), flush=True)
                previous = closed
            time.sleep(0.5)
    finally:
        os.close(fd)


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=5).stdout


def display(action):
    # Never light the built-in panel under a closed lid.
    closed = lid_closed() if action == 'enable' else False
    if not closed:
        run(['hyprctl', 'dispatch', 'hl.dsp.dpms({action="' + action + '"})'])
    else:
        monitors = json.loads(run(['hyprctl', '-j', 'monitors']))
        for monitor in monitors:
            if not monitor['name'].startswith(('eDP', 'LVDS', 'DSI')):
                run(['hyprctl', 'dispatch', 'hl.dsp.dpms({action="enable", monitor=' + json.dumps(monitor['name']) + '})'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['watch-lid', 'enable', 'disable', 'idle-suspend', 'battery-status'])
    args = parser.parse_args()
    if args.action == 'watch-lid':
        watch_lid()
    elif args.action == 'idle-suspend':
        config = Path.home()/'.config/quickshell/ii'
        try:
            run(['qs', '-p', str(config), 'ipc', 'call', 'slumber', 'idleSuspend'])
        except (OSError, subprocess.SubprocessError):
            # Shell/helper unavailable: retain normal suspend policy.
            run(['systemctl', 'suspend'])
    elif args.action == 'battery-status':
        from battery_status import snapshot
        print(json.dumps(snapshot()))
    else:
        display(args.action)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': str(exc)}), flush=True)
        raise SystemExit(1)
