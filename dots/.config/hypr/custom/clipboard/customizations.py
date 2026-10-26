#!/usr/bin/env python3
"""Back up desktop configs and check/reapply the clipboard customization."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


HERE = Path(__file__).resolve().parent
CONFIG_DIRS = ("hypr", "quickshell/ii", "illogical-impulse")


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
    edits = json.loads((HERE / "clipboard-integration.json").read_text())
    original, updated = {}, {}
    for edit in edits:
        relative = Path(edit["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise CompatibilityError("Unsafe integration path.")
        path = config_root / relative
        if path not in original:
            try:
                original[path] = path.read_bytes()
                updated[path] = original[path].decode()
            except (OSError, UnicodeError) as error:
                raise CompatibilityError(f"Required integration file missing or unreadable: {relative}") from error
        text = updated[path]
        before, after = edit["before"], edit["after"]
        if edit.get("exact"):
            if text == after:
                continue
            if text not in [before, *edit.get("previous", [])]:
                raise CompatibilityError(f"Upstream integration changed in {relative}; no files were installed.")
            updated[path] = after
            continue
        if text.count(after) == 1:
            continue
        if text.count(before) != 1:
            raise CompatibilityError(f"Upstream integration changed in {relative}; no files were installed.")
        updated[path] = text.replace(before, after, 1)
    for name in ("clipboard-paste.py", "clipboard-pins.py"):
        source = HERE / name
        if not source.exists() and name == "clipboard-pins.py":
            continue  # Supports minimal integration fixtures and older saved packages.
        helper = config_root / "hypr/custom/scripts" / name
        original[helper] = helper.read_bytes() if helper.exists() else None
        updated[helper] = source.read_text()
    return [(path, original[path], text.encode()) for path, text in updated.items()
            if original[path] != text.encode()]


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
        print("Clipboard integration already installed; no changes needed.")
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
            write_atomic(path, new, 0o755 if path.name in ("clipboard-paste.py", "clipboard-pins.py") else mode)
            written.append((path, old, mode))
    except Exception:
        for path, old, mode in reversed(written):
            if old is None:
                path.unlink(missing_ok=True)
            else:
                write_atomic(path, old, mode)
        raise
    print(f"Installed clipboard integration ({len(changes)} files). Previous configs: {saved}")


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
