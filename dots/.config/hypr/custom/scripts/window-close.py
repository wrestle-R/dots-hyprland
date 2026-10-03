#!/usr/bin/env python3
"""A single close dialog and one-app undo for Hyprland's Lua configuration."""

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote, urlparse


HERE = Path(__file__).resolve().parent
ADDRESS = re.compile(r"0x[0-9a-fA-F]+\Z")


class CloseError(Exception):
    pass


def private_dir(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


def runtime_dir():
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not runtime or not signature:
        raise CloseError("A running Hyprland session is required.")
    session = hashlib.sha256(signature.encode()).hexdigest()[:12]
    return private_dir(Path(runtime) / f"hypr-close-{session}")


def state_dir():
    base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    return private_dir(base / "hypr/window-close")


@contextlib.contextmanager
def locked(path, blocking=False):
    with path.open("a") as handle:
        path.chmod(0o600)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def notify(message):
    if shutil.which("notify-send"):
        subprocess.Popen(
            ["notify-send", "-a", "Window shortcuts", "-t", "3500", "Window shortcuts", message],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def hypr(command, *args, json_output=False):
    argv = ["hyprctl"] + (["-j"] if json_output else []) + [command, *args]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=4, check=True)
        return json.loads(result.stdout) if json_output else result.stdout.strip()
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        raise CloseError("Could not communicate with Hyprland.") from error


def target_exists(target):
    return any(
        window.get("address") == target["address"]
        and window.get("pid") == target["pid"]
        and window_id(window) == window_id(target)
        for window in hypr("clients", json_output=True)
    )


def window_id(window):
    # hyprctl serializes stableId as hexadecimal; Lua exposes it as an integer.
    value = window.get("stableId", -1)
    return int(value, 16) if isinstance(value, str) else int(value)


def get_target(address=None, pid=None, stable_id=None):
    if address is None:
        target = hypr("activewindow", json_output=True)
    else:
        if not ADDRESS.fullmatch(address) or pid is None:
            raise CloseError("Invalid window identity.")
        target = next((w for w in hypr("clients", json_output=True)
                       if w.get("address") == address and w.get("pid") == pid
                       and (stable_id is None or window_id(w) == stable_id)), {})
    if not target.get("mapped") or not target.get("address") or target.get("pid", 0) <= 0:
        return None
    if not ADDRESS.fullmatch(target["address"]):
        raise CloseError("Invalid window identity.")
    return dict(target, stableId=window_id(target))


def process_info(pid):
    base = Path("/proc") / str(pid)
    try:
        argv = [part.decode(errors="surrogateescape") for part in (base / "cmdline").read_bytes().split(b"\0") if part]
        env = {}
        for part in (base / "environ").read_bytes().split(b"\0"):
            key, _, value = part.partition(b"=")
            if key in (b"APPIMAGE", b"GIO_LAUNCHED_DESKTOP_FILE", b"BAMF_DESKTOP_FILE_HINT"):
                env[key.decode()] = value.decode(errors="surrogateescape")
        return {"argv": argv, "exe": os.readlink(base / "exe"),
                "cwd": os.readlink(base / "cwd"), "env": env}
    except OSError as error:
        raise CloseError("The selected application is no longer running.") from error


def flag_value(argv, flag):
    for index, arg in enumerate(argv[1:], 1):
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
        if arg == flag and index + 1 < len(argv) and not argv[index + 1].startswith("-"):
            return argv[index + 1]
    return None


def desktop_api():
    import gi
    gi.require_version("GioUnix", "2.0")
    from gi.repository import Gio, GioUnix
    return Gio, GioUnix.DesktopAppInfo


def desktop_match(target, process):
    _, app_info = desktop_api()
    for key in ("GIO_LAUNCHED_DESKTOP_FILE", "BAMF_DESKTOP_FILE_HINT"):
        filename = process["env"].get(key)
        if filename and Path(filename).is_file():
            app = app_info.new_from_filename(filename)
            if app:
                return app
    classes = {target.get(key, "").casefold() for key in ("class", "initialClass")} - {""}
    executables = {Path(process["exe"]).name}
    if process["argv"] and len(process["argv"]) > 1:
        executables.add(Path(process["argv"][0]).name)
    scored = []
    for app in app_info.get_all():
        app_id = (app.get_id() or "").removesuffix(".desktop").casefold()
        wmclass = (app.get_string("StartupWMClass") or "").casefold()
        if any(x in app_id for x in ("urlhandler", "url-handler")):
            continue
        score = 100 if wmclass in classes or app_id in classes else 0
        executable = (app.get_executable() or "").strip('"')
        if Path(executable).name in executables:
            score += 10
        if score:
            scored.append((score, app.get_id() or "", app))
    return max(scored, key=lambda item: (item[0], item[1]))[2] if scored else None


def local_path(uri):
    if isinstance(uri, dict):
        uri = uri.get("external") or uri.get("path")
    if not isinstance(uri, str):
        return None
    parsed = urlparse(uri)
    if parsed.scheme == "file" and parsed.netloc in ("", "localhost"):
        return Path(unquote(parsed.path))
    if not parsed.scheme and Path(uri).is_absolute():
        return Path(uri)
    return None


def vscode_launch(target, process):
    argv = process["argv"]
    data_dir = flag_value(argv, "--user-data-dir")
    if not data_dir:
        try:
            for fd in (Path("/proc") / str(target["pid"]) / "fd").iterdir():
                try:
                    filename = os.readlink(fd)
                except OSError:
                    continue
                marker = "/User/globalStorage/"
                if marker in filename:
                    data_dir = filename.split(marker, 1)[0]
                    break
        except OSError:
            pass
    if not data_dir:
        data_dir = str(Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "Code")
    profile = Path(data_dir)
    try:
        stored = json.loads((profile / "User/globalStorage/storage.json").read_text())
    except (OSError, ValueError):
        stored = {}
    state = stored.get("windowsState", {})
    entries = [state.get("lastActiveWindow", {}), *state.get("openedWindows", [])]
    candidates = {}
    for entry in entries:
        resource = entry.get("folder") or entry.get("workspace", {}).get("configPath")
        path = local_path(resource)
        if path and path.exists():
            candidates[str(path)] = path
    # A newly opened project can exist before windowsState has been flushed.
    for metadata in (profile / "User/workspaceStorage").glob("*/workspace.json"):
        try:
            workspace = json.loads(metadata.read_text())
            path = local_path(workspace.get("folder") or workspace.get("workspace"))
            if path and path.exists():
                candidates[str(path)] = path
        except (OSError, ValueError):
            continue
    title_parts = [part.strip().casefold() for part in target.get("title", "").split(" - ")]
    matches = [path for path in candidates.values()
               if path.name.casefold() in title_parts
               or (path.suffix == ".code-workspace" and any(
                   part in (path.stem.casefold(), path.stem.casefold() + " (workspace)") for part in title_parts))]
    project = matches[0] if len(matches) == 1 else None
    if project is None:
        excluded = {str(profile), flag_value(argv, "--extensions-dir")}
        direct = [Path(arg) for arg in argv[1:] if not arg.startswith("-")
                  and Path(arg).exists() and (Path(arg).is_dir() or arg.endswith(".code-workspace"))
                  and str(Path(arg)) not in excluded]
        if len(direct) == 1:
            project = direct[0]
    launcher = shutil.which("code") or str(Path(process["exe"]).parent / "bin/code")
    command = [launcher]
    if project:
        command.append("--new-window")
    command.extend(["--user-data-dir", str(profile)])
    extensions = flag_value(argv, "--extensions-dir")
    if not extensions and profile.name == "vscode-user-data":
        sibling = profile.parent / "vscode-extensions"
        if sibling.is_dir():
            extensions = str(sibling)
    if extensions:
        command.extend(["--extensions-dir", extensions])
    if project:
        command.append(str(project))
    return {"kind": "argv", "argv": command, "cwd": process["cwd"]}


def launch_record(target):
    process = process_info(target["pid"])
    if "vscode" in target.get("class", "").casefold() or Path(process["exe"]).parent == Path("/usr/share/code"):
        launch = vscode_launch(target, process)
    elif process["env"].get("APPIMAGE"):
        appimage = process["env"]["APPIMAGE"]
        launch = {"kind": "argv", "argv": [appimage, *process["argv"][1:]], "cwd": process["cwd"]}
    else:
        app = desktop_match(target, process)
        if app:
            resources = []
            if app.supports_files() or app.supports_uris():
                for arg in process["argv"][1:]:
                    if arg.startswith("-"):
                        continue
                    path = Path(arg) if Path(arg).is_absolute() else Path(process["cwd"]) / arg
                    if path.exists():
                        resources.append(path.resolve().as_uri())
            launch = {"kind": "desktop", "desktop_file": app.get_filename(), "uris": resources,
                      "cwd": process["cwd"]}
        else:
            # A GUI executable fallback never replays a shell command or an Electron child.
            if Path(process["exe"]).name in ("sh", "bash", "fish", "zsh", "dash", "python", "python3"):
                launch = None
            else:
                arguments = process["argv"][1:]
                if any(arg.startswith("--type=") for arg in arguments):
                    arguments = []
                launch = {"kind": "argv", "argv": [process["exe"], *arguments], "cwd": process["cwd"]}
    return {"version": 1, "app": target.get("class") or Path(process["exe"]).name, "launch": launch}


def save_record(record):
    directory = state_dir()
    with locked(directory / "state.lock", blocking=True):
        destination = directory / "last-closed.json"
        try:
            current = json.loads(destination.read_text())
        except (OSError, ValueError):
            current = {}
        if current.get("closed_at", 0) > record["closed_at"]:
            return
        fd, filename = tempfile.mkstemp(prefix=".last-closed-", dir=directory)
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(record, handle, ensure_ascii=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(filename, destination)
        finally:
            Path(filename).unlink(missing_ok=True)


def event_socket():
    path = Path(os.environ["XDG_RUNTIME_DIR"]) / "hypr" / os.environ["HYPRLAND_INSTANCE_SIGNATURE"] / ".socket2.sock"
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.connect(str(path))
        connection.setblocking(False)
        return connection
    except OSError:
        connection.close()
        raise CloseError("Could not watch the selected window.")


def close_target(target):
    # Validation and dispatch run together in the compositor, avoiding address-reuse races.
    code = (
        f'local w = hl.get_window("address:{target["address"]}"); '
        f'if not w or w.pid ~= {int(target["pid"])} or w.stable_id ~= {int(target["stableId"])} '
        'then error("The selected window no longer exists") end; '
        'hl.dispatch(hl.dsp.window.close({window = w}))'
    )
    response = hypr("eval", code)
    if response != "ok":
        raise CloseError("Could not close the selected window.")


def stop_dialog(process, connection):
    if connection:
        try:
            connection.sendall(b"dismiss\n")
        except OSError:
            pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def show_dialog(target, runtime, events):
    monitors = hypr("monitors", json_output=True)
    monitor = next((m for m in monitors if m.get("id") == target.get("monitor")), None)
    if not monitor:
        return False
    with tempfile.TemporaryDirectory(prefix="dialog-", dir=runtime) as directory:
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(Path(directory) / "view.sock"))
        listener.listen(1)
        listener.setblocking(False)
        env = dict(os.environ, CONFIRM_CLOSE_SOCKET=str(Path(directory) / "view.sock"),
                   CONFIRM_CLOSE_MONITOR=monitor["name"])
        process = subprocess.Popen(["quickshell", "--no-duplicate", "--path", str(HERE / "confirm-close.qml")], env=env)
        connection = None
        buffer = b""
        last_check = time.monotonic()
        try:
            while process.poll() is None:
                readable, _, _ = select.select([connection or listener, events], [], [], 0.2)
                if events in readable:
                    if not events.recv(65536) or not target_exists(target):
                        return False
                if listener in readable:
                    connection, _ = listener.accept()
                elif connection and connection in readable:
                    chunk = connection.recv(1024)
                    if not chunk:
                        return False
                    buffer += chunk
                    if b"\n" in buffer:
                        return buffer.split(b"\n", 1)[0] == b"confirm"
                if time.monotonic() - last_check >= 1:
                    if not target_exists(target) or not any(m["name"] == monitor["name"] for m in hypr("monitors", json_output=True)):
                        return False
                    last_check = time.monotonic()
            if process.returncode:
                raise CloseError("The close dialog could not start.")
            return False
        finally:
            stop_dialog(process, connection)
            if connection:
                connection.close()
            listener.close()


def remember_when_closed(target, record, events, runtime):
    # One observer per requested window can wait for the app's own save prompt.
    # It watches only this target and exits when the window or compositor goes away.
    with locked(runtime / f'pending-{target["stableId"]}.lock') as acquired:
        if not acquired:
            return
        while True:
            if not target_exists(target):
                record["closed_at"] = time.time_ns()
                save_record(record)
                return
            readable, _, _ = select.select([events], [], [], 10)
            if readable and not events.recv(65536):
                return


def dialog(address=None, pid=None, stable_id=None):
    runtime = runtime_dir()
    with locked(runtime / "dialog.lock") as acquired:
        if not acquired:
            return
        target = get_target(address, pid, stable_id)
        if not target:
            return
        record = launch_record(target)
        events = event_socket()
        try:
            accepted = show_dialog(target, runtime, events)
            if not accepted or not target_exists(target):
                events.close()
                return
            close_target(target)
        except BaseException:
            events.close()
            raise
    if accepted:
        try:
            remember_when_closed(target, record, events, runtime)
        finally:
            events.close()


def launch_app(launch):
    if not launch:
        raise CloseError("This app did not provide a reusable launcher.")
    if launch["kind"] == "desktop":
        _, app_info = desktop_api()
        try:
            app = app_info.new_from_filename(launch["desktop_file"])
            if not app:
                raise CloseError("The application's desktop entry is no longer available.")
            actions = app.list_actions()
            new_window = next((a for a in actions if a.casefold() in ("new-window", "newwindow", "new_window")), None)
            cwd = launch.get("cwd")
            if not cwd or not Path(cwd).is_dir():
                cwd = str(Path.home())
            with contextlib.chdir(cwd):
                if new_window and not launch.get("uris"):
                    app.launch_action(new_window, None)
                elif not app.launch_uris(launch.get("uris", []), None):
                    raise CloseError("The application could not be reopened.")
        except CloseError:
            raise
        except Exception as error:
            raise CloseError("The application could not be reopened.") from error
    elif launch["kind"] == "argv":
        argv = launch["argv"]
        if not argv or not Path(argv[0]).is_file() or not os.access(argv[0], os.X_OK):
            raise CloseError("The application's executable is no longer available.")
        cwd = launch.get("cwd")
        if not cwd or not Path(cwd).is_dir():
            cwd = str(Path.home())
        env = dict(os.environ)
        env.pop("ELECTRON_RUN_AS_NODE", None)
        process = subprocess.Popen(argv, cwd=cwd, env=env, start_new_session=True,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            status = process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            return
        if status != 0:
            raise CloseError("The application exited before it could reopen.")
    else:
        raise CloseError("The saved launcher is not supported.")


def restore():
    with locked(runtime_dir() / "restore.lock") as acquired:
        if not acquired:
            return
        directory = state_dir()
        with locked(directory / "state.lock", blocking=True):
            path = directory / "last-closed.json"
            if not path.exists():
                notify("No closed application to reopen.")
                return
            try:
                record = json.loads(path.read_text())
                if record.get("version") != 1:
                    raise CloseError("The saved application record is not supported.")
                launch_app(record.get("launch"))
            except (OSError, ValueError, KeyError) as error:
                raise CloseError("The saved application could not be reopened.") from error
            path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    opening = commands.add_parser("dialog")
    opening.add_argument("address", nargs="?")
    opening.add_argument("pid", nargs="?", type=int)
    opening.add_argument("stable_id", nargs="?", type=int)
    commands.add_parser("restore")
    args = parser.parse_args()
    try:
        if args.command == "dialog":
            dialog(args.address, args.pid, args.stable_id)
        else:
            restore()
    except (CloseError, OSError, ImportError) as error:
        notify(str(error))
        print(f"window-close: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
