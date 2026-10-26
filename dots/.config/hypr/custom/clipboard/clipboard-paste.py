#!/usr/bin/env python3
"""Paste one cliphist item into the window captured before opening the picker."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


ADDRESS = re.compile(r"0x[0-9a-fA-F]+\Z")
TERMINAL = re.compile(
    r"(^|[._-])(kitty|alacritty|foot(client)?|wezterm|ghostty|konsole|terminal|"
    r"gnome-terminal|xfce4-terminal|qterminal|tilix|terminator|termite|"
    r"xterm|uxterm|urxvt|rxvt|st|rio|contour|sakura|guake|yakuake|ptyxis|kgx|warp)([._-]|$)",
    re.IGNORECASE,
)


class PasteError(Exception):
    pass


def run(argv, **kwargs):
    try:
        return subprocess.run(argv, timeout=5, check=True, **kwargs)
    except (OSError, subprocess.SubprocessError) as error:
        raise PasteError(f"{argv[0]} failed; automatic paste stopped.") from error


def hypr(command, *args):
    try:
        return json.loads(run(["hyprctl", "-j", command, *args], capture_output=True).stdout)
    except (ValueError, UnicodeError) as error:
        raise PasteError("Could not read the Hyprland session.") from error


def valid_target(target):
    return (
        isinstance(target, dict)
        and isinstance(target.get("address"), str)
        and ADDRESS.fullmatch(target["address"])
        and isinstance(target.get("pid"), int)
        and target["pid"] > 0
        and target.get("stableId") is not None
    )


def same_window(window, target):
    return all(window.get(key) == target.get(key) for key in ("address", "pid", "stableId"))


def find_target(target):
    if not valid_target(target):
        raise PasteError("No original window was captured. The item is copied; paste it manually.")
    for window in hypr("clients"):
        if window.get("mapped") and same_window(window, target):
            return window
    raise PasteError("The original window has closed. The item is copied; paste it manually.")


def paste_keys(window):
    terminal = any(TERMINAL.search(window.get(key, "")) for key in ("class", "initialClass"))
    # Linux input codes: left Ctrl=29, left Shift=42, V=47. No Enter/Return event.
    return (["29:1", "42:1", "47:1", "47:0", "42:0", "29:0"] if terminal
            else ["29:1", "47:1", "47:0", "29:0"])


def overview_visible():
    layers = hypr("layers")
    return any(
        surface.get("namespace") == "quickshell:overview"
        for monitor in layers.values()
        for surfaces in monitor.get("levels", {}).values()
        for surface in surfaces
    )


def wait_for_target(target):
    # The QML picker has been hidden, but wait for the compositor to unmap its layer.
    deadline = time.monotonic() + 1.5
    while overview_visible():
        if time.monotonic() >= deadline:
            raise PasteError("The clipboard is still open. The item is copied; paste it manually.")
        time.sleep(0.025)
    find_target(target)
    command = 'hl.dispatch(hl.dsp.focus({window = "address:' + target["address"] + '"}))'
    run(["hyprctl", "eval", command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while not same_window(hypr("activewindow"), target):
        if time.monotonic() >= deadline:
            raise PasteError("Could not focus the original window. The item is copied; paste it manually.")
        time.sleep(0.025)
    time.sleep(0.08)
    # A closed/replaced window or a focus change must never redirect the paste.
    window = find_target(target)
    if not same_window(hypr("activewindow"), target):
        raise PasteError("Focus changed before pasting. The item is copied; paste it manually.")
    return window


def paste(entry_id, target):
    if re.fullmatch(r"pin:[0-9a-f]{64}", entry_id):
        data = run(["python3", str(Path(__file__).with_name("clipboard-pins.py")),
                    "read", entry_id[4:]], capture_output=True).stdout
    elif re.fullmatch(r"[0-9]+", entry_id):
        # cliphist 0.7 parses a bare numeric stdin value literally; a trailing newline fails.
        data = run(["cliphist", "decode"], input=entry_id.encode(), capture_output=True).stdout
    else:
        raise PasteError("Invalid clipboard item.")
    run(["wl-copy"], input=data, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    window = wait_for_target(target)
    run(["ydotool", "key", "-d", "12", *paste_keys(window)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def notify(message):
    try:
        subprocess.Popen(["notify-send", "-a", "Clipboard", "Clipboard", message],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry_id")
    parser.add_argument("target", help="JSON window identity; never clipboard content")
    args = parser.parse_args()
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not runtime or not signature:
        parser.error("A running Hyprland session is required.")
    session = hashlib.sha256(signature.encode()).hexdigest()[:12]
    lock_path = Path(runtime) / f"clipboard-paste-{session}.lock"
    try:
        with lock_path.open("a") as lock:
            lock_path.chmod(0o600)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return 0
            try:
                target = json.loads(args.target)
            except ValueError as error:
                raise PasteError("Invalid original window identity.") from error
            paste(args.entry_id, target)
    except PasteError as error:
        notify(str(error))
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
