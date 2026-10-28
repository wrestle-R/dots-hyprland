#!/usr/bin/env python3
"""Personal sidebar adapter for the installed Spotify TUI. No account credentials."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import uuid


LIMIT = 256 * 1024


class PlayerError(Exception):
    pass


def runtime_dir():
    return Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "spotify-tui"


def request(method, params=None, path=None, timeout=3):
    path = path or runtime_dir() / "player.sock"
    try:
        info = path.stat()
        if info.st_uid != os.getuid() or not stat.S_ISSOCK(info.st_mode):
            raise PlayerError("Playback socket is unavailable")
        request_id = uuid.uuid4().hex
        deadline = time.monotonic() + timeout
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout)
            connection.connect(str(path))
            connection.sendall((json.dumps({"version": 1, "id": request_id,
                                           "method": method, "params": params}) + "\n").encode())
            data = bytearray()
            while b"\n" not in data:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                connection.settimeout(remaining)
                chunk = connection.recv(min(4096, LIMIT + 1 - len(data)))
                if not chunk:
                    raise PlayerError("Playback connection closed")
                data.extend(chunk)
                if len(data) > LIMIT:
                    raise PlayerError("Playback response is too large")
            response = json.loads(data.split(b"\n", 1)[0])
            if not isinstance(response, dict) or response.get("version") != 1 or response.get("id") != request_id:
                raise PlayerError("Playback protocol changed; update the sidebar adapter")
            if response.get("error"):
                raise PlayerError("Playback command failed. Open the player and press c to reconnect")
            return response.get("result")
    except FileNotFoundError as error:
        raise PlayerError("Player is closed. Open Spotify TUI to start listening") from error
    except (OSError, ValueError, TypeError) as error:
        raise PlayerError("Player is not responding. Open it and press c to reconnect") from error


def clean_text(value):
    return "".join(c for c in str(value or "") if c.isprintable())[:500]


def number(value, maximum):
    return max(0, min(maximum, value)) if type(value) is int else 0


def state(path=None):
    try:
        result = request("state", path=path)
        if not isinstance(result, dict) or not isinstance(result.get("status"), str):
            raise PlayerError("Playback state is unavailable")
        duration = number(result.get("duration_ms"), 86400000)
        return {"ok": True, "connected": result.get("connected") is True,
                "logged_in": result.get("logged_in") is True,
                "status": clean_text(result["status"]),
                "title": clean_text(result.get("title")), "artist": clean_text(result.get("artist")),
                "position_ms": number(result.get("position_ms"), duration), "duration_ms": duration,
                "volume": number(result.get("volume"), 100),
                "needs_reconnect": bool(result.get("error"))}
    except PlayerError as error:
        return {"ok": False, "message": str(error)}


def executable():
    installed = Path.home() / ".local/bin/spotify-tui"
    found = str(installed) if installed.is_file() else shutil.which("spotify-tui")
    if not found:
        raise PlayerError("Install Spotify TUI first; see the sidebar setup guide")
    return found


def open_player():
    """Focus an existing TUI window, otherwise launch the downloaded installation."""
    binary = executable()
    directory = runtime_dir()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / "sidebar-open.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if shutil.which("hyprctl"):
            try:
                clients = json.loads(subprocess.check_output(["hyprctl", "-j", "clients"], timeout=3))
                for client in clients:
                    address = client.get("address", "")
                    if client.get("class") == "spotify-tui" and re.fullmatch(r"0x[0-9a-fA-F]+", address):
                        command = f'hl.dsp.focus({{window="address:{address}"}})'
                        focused = subprocess.check_output(["hyprctl", "dispatch", command],
                                                          timeout=3, stderr=subprocess.DEVNULL, text=True)
                        if focused.strip() != "ok":
                            raise PlayerError("Could not focus the existing player. Switch to its workspace")
                        return
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                raise PlayerError("Could not inspect player windows. Try opening it from your terminal") from error
        terminal = shutil.which("kitty")
        if not terminal:
            raise PlayerError("Kitty is required to open the player on this setup")
        subprocess.Popen([terminal, "--class", "spotify-tui", "--title", "Spotify TUI", binary],
                         start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Serialize repeated hotkeys until the terminal has registered its window.
        time.sleep(1.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("state", "watch", "open", "toggle_pause", "next", "previous", "seek"))
    parser.add_argument("value", nargs="?", type=int)
    args = parser.parse_args()
    try:
        if args.action == "watch":
            while True:
                print(json.dumps(state()), flush=True)
                time.sleep(1)
        elif args.action == "state":
            print(json.dumps(state()))
        elif args.action == "open":
            open_player()
            print(json.dumps({"ok": True}))
        else:
            params = None
            if args.action == "seek":
                if args.value is None or not 0 <= args.value <= 86400000:
                    raise PlayerError("Seek position must be between 0 and 86400000 milliseconds")
                params = {"position_ms": args.value}
            request(args.action, params, timeout=9)
            print(json.dumps({"ok": True}))
    except PlayerError as error:
        print(json.dumps({"ok": False, "message": str(error)}))
        return 1
    except (BrokenPipeError, KeyboardInterrupt):
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
