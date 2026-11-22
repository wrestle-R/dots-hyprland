#!/usr/bin/python3
"""Manage the current user's fingerprints through fprintd, emitting JSON events."""
import argparse
import json
import os
import pwd
import signal

FINGERS = tuple(f'{hand}-{finger}-finger' if finger != 'thumb' else f'{hand}-thumb'
                for hand in ('left', 'right')
                for finger in ('thumb', 'index', 'middle', 'ring', 'little'))
MESSAGES = {
    'enroll-stage-passed': 'Good scan. Lift your finger and place it again.',
    'enroll-retry-scan': 'Try again. Cover the reader with your fingertip.',
    'enroll-swipe-too-short': 'Swipe across the whole reader.',
    'enroll-finger-not-centered': 'Move your finger to the center of the reader.',
    'enroll-remove-and-retry': 'Lift your finger, then try again.',
    'enroll-completed': 'Fingerprint saved.',
    'enroll-failed': 'The scan could not be saved. Try again.',
    'enroll-data-full': 'The reader is full. Remove an unused fingerprint first.',
    'enroll-disconnected': 'The fingerprint reader disconnected.',
    'enroll-unknown-error': 'The reader could not finish enrollment.',
    'enroll-duplicate': 'This finger is already registered. Choose another finger.',
}


def emit(**event):
    print(json.dumps(event), flush=True)


def describe(device, properties, username):
    try:
        enrolled = list(map(str, device.ListEnrolledFingers(username)))
    except Exception as exc:
        if getattr(exc, 'get_dbus_name', lambda: '')() != 'net.reactivated.Fprint.Error.NoEnrolledPrints':
            raise
        enrolled = []
    return dict(available=True, enrolled=enrolled,
                device=str(properties.Get('net.reactivated.Fprint.Device', 'name')),
                stages=max(1, int(properties.Get('net.reactivated.Fprint.Device', 'num-enroll-stages'))))


def remove(device, username, finger):
    # Deleting a specific finger must never fall back to deleting every finger.
    device.Claim(username)
    try:
        try:
            device.DeleteEnrolledFinger(finger)
        except Exception as exc:
            if getattr(exc, 'get_dbus_name', lambda: '')() != 'net.reactivated.Fprint.Error.NoEnrolledPrints':
                raise
    finally:
        device.Release()


def enroll(device, username, finger, stages, loop, glib, report=emit):
    completed = 0
    success = False
    terminal = False

    def status(result, done):
        nonlocal completed, success, terminal
        result = str(result)
        if result == 'enroll-stage-passed':
            completed = min(stages, completed + 1)
        success = result == 'enroll-completed'
        terminal = bool(done)
        report(event='progress', ok=success if done else True, done=bool(done),
               completed=stages if success else completed, stages=stages,
               message=MESSAGES.get(result, 'Adjust your finger and try again.'))
        if done:
            loop.quit()

    def cancel():
        loop.quit()
        return False

    match = device.connect_to_signal('EnrollStatus', status)
    device.Claim(username)
    started = False
    sources = []
    try:
        sources = [glib.unix_signal_add(glib.PRIORITY_DEFAULT, sig, cancel)
                   for sig in (signal.SIGTERM, signal.SIGINT)]
        sources.append(glib.timeout_add_seconds(120, cancel))
        device.EnrollStart(finger)
        started = True
        report(event='progress', ok=True, done=False, completed=0, stages=stages,
               message='Place your finger on the reader, then lift it between scans.')
        loop.run()
    finally:
        for source in sources:
            # A fired one-shot source is already removed by GLib.
            if glib.MainContext.default().find_source_by_id(source):
                glib.source_remove(source)
        try:
            if started:
                device.EnrollStop()
        finally:
            device.Release()
            match.remove()
    if not terminal:
        report(event='cancelled', ok=True, message='Enrollment stopped. Your saved-finger list has been refreshed.')
    return success


def error_message(exc):
    name = getattr(exc, 'get_dbus_name', lambda: '')()
    if name.endswith(('AlreadyInUse', 'ClaimDevice')):
        return 'The reader is busy. Finish the other fingerprint request and try again.'
    if name.endswith(('PermissionDenied', 'NotAuthorized', 'AuthFailed')):
        return 'Fingerprint access was denied. Approve the authentication request and try again.'
    if name.endswith(('NoSuchDevice', 'ServiceUnknown', 'NameHasNoOwner')):
        return 'No fingerprint reader is available. Check that fprintd is installed and the reader is connected.'
    if name.endswith('UnknownMethod'):
        return 'This fprintd version cannot remove one finger. Update fprintd to use this action.'
    return 'The fingerprint service could not finish. Refresh and try again.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'enroll', 'remove'))
    parser.add_argument('finger', nargs='?', choices=FINGERS)
    args = parser.parse_args()
    if args.action != 'status' and not args.finger:
        parser.error('Choose a finger')
    try:
        import dbus
        from dbus.mainloop.glib import DBusGMainLoop
        from gi.repository import GLib
        DBusGMainLoop(set_as_default=True)
        username = pwd.getpwuid(os.getuid()).pw_name
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object('net.reactivated.Fprint', '/net/reactivated/Fprint/Manager'), 'net.reactivated.Fprint.Manager')
        path = manager.GetDefaultDevice()
        obj = bus.get_object('net.reactivated.Fprint', path)
        device = dbus.Interface(obj, 'net.reactivated.Fprint.Device')
        properties = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
        state = describe(device, properties, username)
        if args.action == 'remove':
            remove(device, username, args.finger)
            state = describe(device, properties, username)
        elif args.action == 'enroll':
            enroll(device, username, args.finger, state['stages'], GLib.MainLoop(), GLib)
            state = describe(device, properties, username)
        emit(event='state', ok=True, **state)
    except ImportError:
        emit(event='error', ok=False, message='Install python-dbus and python-gobject to manage fingerprints.')
        return 1
    except Exception as exc:
        emit(event='error', ok=False, message=error_message(exc))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
