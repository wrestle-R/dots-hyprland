#!/usr/bin/env python3
"""Back up desktop configs and check/reapply the personal sidebar customization."""

import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


HERE = Path(__file__).resolve().parent
CONFIG_DIRS = ("hypr", "quickshell/ii", "illogical-impulse")
SPOTIFY_HOOK = '''
-- Spotify sidebar launcher (managed integration)
local spotifyShortcuts = (os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")) .. "/hypr/custom/spotify-shortcuts.lua"
if is_file_exists(spotifyShortcuts) then dofile(spotifyShortcuts) end
'''


class CompatibilityError(Exception):
    pass


def default_backup_root():
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "hypr-customization-backups"


def backup(config_root, backup_root):
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup_root.chmod(0o700)
    destination = Path(tempfile.mkdtemp(
        prefix=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-"), dir=backup_root))
    entries = []
    for name in CONFIG_DIRS:
        source = config_root / name
        if source.is_dir():
            shutil.copytree(source, destination / name, symlinks=True)
            entries.append(name)
    if not entries:
        destination.rmdir()
        raise CompatibilityError("No desktop configuration directories found to back up.")
    manifest = {"version": 1, "config_root": str(config_root), "directories": entries}
    (destination / "backup.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Backup: {destination}")
    return destination


def plan(config_root):
    edits = json.loads((HERE / "sidebar-integration.json").read_text())
    changes = []
    for edit in edits:
        relative = Path(edit["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise CompatibilityError("Unsafe integration path.")
        path = config_root / relative
        try:
            old = path.read_bytes()
            text = old.decode()
        except (OSError, UnicodeError) as error:
            raise CompatibilityError(f"Required integration file missing or unreadable: {relative}") from error
        if text == edit["after"]:
            continue
        if text not in [edit["before"], *edit.get("previous", [])]:
            raise CompatibilityError(f"Upstream integration changed in {relative}; no files were installed.")
        changes.append((path, old, edit["after"].encode()))
    assets = {
        "hyprtrack-logo.svg": "quickshell/ii/modules/ii/sidebarLeft/hyprtrack-logo.svg",
        "SidebarToolTip.qml": "quickshell/ii/modules/ii/sidebarLeft/SidebarToolTip.qml",
        "HyprTrackSummary.qml": "quickshell/ii/modules/ii/sidebarLeft/HyprTrackSummary.qml",
        "SidebarDashboard.qml": "quickshell/ii/modules/ii/sidebarLeft/SidebarDashboard.qml",
        "hyprtrack-summary.py": "hypr/custom/scripts/hyprtrack-summary.py",
        "SpotifyMiniPlayer.qml": "quickshell/ii/modules/ii/sidebarLeft/SpotifyMiniPlayer.qml",
        "spotify-sidebar.py": "hypr/custom/scripts/spotify-sidebar.py",
        "spotify-shortcuts.lua": "hypr/custom/spotify-shortcuts.lua",
    }
    previous_assets = json.loads((HERE / "asset-versions.json").read_text())
    for name, relative in assets.items():
        path = config_root / relative
        old = path.read_bytes() if path.exists() else None
        new = (HERE / name).read_bytes()
        if old == new:
            continue
        # New assets may be absent. Never replace unrecognized personal edits.
        if old is not None and hashlib.sha256(old).hexdigest() not in previous_assets.get(name, []):
            raise CompatibilityError(f"Customized sidebar asset differs: {relative}; installation stopped.")
        changes.append((path, old, new))
    keybinds = config_root / "hypr/custom/keybinds.lua"
    old = keybinds.read_bytes() if keybinds.exists() else None
    text = old.decode() if old is not None else ""
    if SPOTIFY_HOOK not in text:
        if "spotifyShortcuts" in text or "Spotify sidebar launcher (managed integration)" in text:
            raise CompatibilityError("Spotify shortcut hook was edited; installation stopped.")
        # The settings installer owns the final block; preserve its exact suffix.
        settings_marker = "-- Local settings shortcuts (managed integration)"
        updated = text.replace(settings_marker, SPOTIFY_HOOK + "\n" + settings_marker, 1) if settings_marker in text else text + SPOTIFY_HOOK
        changes.append((keybinds, old, updated.encode()))
    # Install dependencies before the watched entry point can load them.
    return sorted(changes, key=lambda change: change[0].name in ("SidebarLeftContent.qml", "keybinds.lua"))


def write_atomic(path, content, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    permissions = mode if mode is not None else (path.stat().st_mode & 0o777 if path.exists() else 0o644)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, permissions)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def install(config_root, backup_root):
    changes = plan(config_root)  # Validate every integration point before any mutation.
    if not changes:
        print("Sidebar integration already installed; no changes needed.")
        return
    saved = backup(config_root, backup_root)
    # A snapshot can take time; refuse to overwrite edits made while it was being copied.
    for path, old, _ in changes:
        current = path.read_bytes() if path.exists() else None
        if current != old:
            raise CompatibilityError(f"Configuration changed during backup: {path}; installation stopped.")
    written = []
    try:
        for path, old, new in changes:
            mode = path.stat().st_mode & 0o777 if path.exists() else None
            write_atomic(path, new, 0o755 if path.name.endswith(".py") else mode)
            written.append((path, old, mode))
    except Exception:
        for path, old, mode in reversed(written):
            if old is None:
                path.unlink(missing_ok=True)
            else:
                write_atomic(path, old, mode)
        raise
    print(f"Installed sidebar integration ({len(changes)} files). Previous configs: {saved}")


def restore(config_root, backup_root, source):
    manifest = json.loads((source / "backup.json").read_text())
    directories = manifest.get("directories", [])
    if manifest.get("version") != 1 or not directories or any(name not in CONFIG_DIRS for name in directories):
        raise CompatibilityError("Invalid backup manifest.")
    if source == config_root or config_root in source.parents:
        raise CompatibilityError("The backup must be outside the configuration being restored.")
    for name in directories:
        if not (source / name).is_dir():
            raise CompatibilityError(f"Incomplete backup: {name}")
    # Preserve the current state too; restoring never discards the only copy of newer edits.
    saved = backup(config_root, backup_root)
    written = []
    try:
        for name in directories:
            destination = config_root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=".restore-", dir=destination.parent))
            try:
                shutil.copytree(source / name, temporary / "replacement", symlinks=True)
                previous = temporary / "previous"
                had_previous = destination.exists() or destination.is_symlink()
                if had_previous:
                    os.replace(destination, previous)
                try:
                    os.replace(temporary / "replacement", destination)
                except Exception:
                    if had_previous:
                        os.replace(previous, destination)
                    raise
                written.append((destination, temporary, had_previous))
            except Exception:
                shutil.rmtree(temporary)
                raise
    except Exception:
        for destination, temporary, had_previous in reversed(written):
            if destination.is_symlink():
                destination.unlink()
            else:
                shutil.rmtree(destination)
            if had_previous:
                os.replace(temporary / "previous", destination)
            shutil.rmtree(temporary)
        raise
    for _, temporary, _ in written:
        shutil.rmtree(temporary)
    print(f"Restored {source}. Configs from before restore: {saved}")
    print("Run hyprctl reload config-only, check configerrors, then reload QuickShell after reviewing the restored files.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("backup", "check", "install", "restore"))
    parser.add_argument("--config-root", type=Path,
                        default=Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))))
    parser.add_argument("--backup-root", type=Path, default=default_backup_root())
    parser.add_argument("--backup", type=Path, help="Snapshot directory for restore")
    args = parser.parse_args()
    config_root = args.config_root.expanduser().resolve()
    backup_root = args.backup_root.expanduser().resolve()
    try:
        if config_root == backup_root or config_root in backup_root.parents:
            raise CompatibilityError("Backups must be outside the configuration root.")
        if args.command == "backup":
            backup(config_root, backup_root)
        elif args.command == "check":
            changes = plan(config_root)
            print(f"Compatible: {len(changes)} files would change. Nothing installed.")
        elif args.command == "install":
            install(config_root, backup_root)
        elif args.command == "restore":
            if args.backup is None:
                parser.error("restore requires --backup SNAPSHOT_DIRECTORY")
            restore(config_root, backup_root, args.backup.expanduser().resolve())
    except (CompatibilityError, OSError, ValueError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
