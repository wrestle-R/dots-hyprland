#!/usr/bin/env python3
"""Keep pinned clipboard originals independently of rolling cliphist history."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


PIN_ID = re.compile(r"[0-9a-f]{64}\Z")
EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
              "image/webp": ".webp", "image/bmp": ".bmp", "image/tiff": ".tiff",
              "image/svg+xml": ".svg", "image/avif": ".avif"}


class PinError(Exception):
    pass


def atomic_write(path, data):
    fd, name = tempfile.mkstemp(prefix=".pin-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class PinStore:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else Path(os.environ.get("CLIPBOARD_PIN_ROOT", str(Path.home() / "clipboard/pinned")))

    @contextmanager
    def locked(self, write=False):
        if write:
            self.root.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.root.chmod(0o700)
        if not self.root.exists():
            yield False
            return
        with (self.root / ".lock").open("a") as lock:
            os.chmod(self.root / ".lock", 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX if write else fcntl.LOCK_SH)
            yield True

    def load(self):
        path = self.root / "index.json"
        if not path.exists():
            return []
        try:
            index = json.loads(path.read_text())
            items = index["items"]
            if index["version"] != 1 or not isinstance(items, list):
                raise ValueError()
            for item in items:
                if not isinstance(item, dict) or not PIN_ID.fullmatch(item.get("id", "")):
                    raise ValueError()
                self.content_path(item)
            return items
        except (ValueError, KeyError, TypeError) as error:
            raise PinError("The pinned clipboard index is invalid; it has been left untouched.") from error

    def content_path(self, item):
        relative = Path(item["file"])
        if relative.is_absolute() or len(relative.parts) != 2 or relative.parts[0] not in ("text", "images", "files"):
            raise PinError("Invalid pinned file path.")
        if not relative.name.startswith(item["id"] + ".") or ".." in relative.parts:
            raise PinError("Invalid pinned file name.")
        path = self.root / relative
        if self.root.resolve() not in path.resolve().parents:
            raise PinError("Pinned file points outside the clipboard folder.")
        return path

    def save(self, items):
        atomic_write(self.root / "index.json", (json.dumps({"version": 1, "items": items}, ensure_ascii=False, indent=2) + "\n").encode())

    def list(self):
        with self.locked() as exists:
            if not exists:
                return []
            return [dict(item, path=str(self.content_path(item))) for item in self.load()]

    def pin(self, data, source_entry=""):
        digest = hashlib.sha256(data).hexdigest()
        try:
            mime = subprocess.run(["file", "--brief", "--mime-type", "-"], input=data,
                                  capture_output=True, timeout=10, check=True).stdout.decode().strip()
        except (OSError, subprocess.SubprocessError, UnicodeError):
            mime = "application/octet-stream"
        text = None
        if not mime.startswith("image/") and b"\0" not in data:
            try:
                text = data.decode("utf-8")
                mime = "text/plain;charset=utf-8"
            except UnicodeError:
                pass
        category = "images" if mime.startswith("image/") else ("text" if text is not None else "files")
        extension = EXTENSIONS.get(mime, ".txt" if text is not None else ".bin")
        preview = " ".join(text[:300].split())[:120] if text is not None else f"{mime} · {len(data):,} bytes"
        with self.locked(write=True):
            items = self.load()
            existing = next((item for item in items if item["id"] == digest), None)
            if existing:
                if source_entry and source_entry not in existing["sources"]:
                    existing["sources"] = (existing["sources"] + [source_entry])[-32:]
                # Re-pinning can repair a missing content file without losing the pin.
                atomic_write(self.content_path(existing), data)
            else:
                directory = self.root / category
                directory.mkdir(exist_ok=True, mode=0o700)
                relative = f"{category}/{digest}{extension}"
                atomic_write(self.root / relative, data)
                items.insert(0, {"id": digest, "file": relative, "mime": mime,
                                 "preview": preview or "Empty text", "bytes": len(data),
                                 "created_at": datetime.now(timezone.utc).isoformat(),
                                 "sources": [source_entry] if source_entry else []})
            self.save(items)
        return digest

    def read(self, identifier):
        if not PIN_ID.fullmatch(identifier):
            raise PinError("Invalid pinned item.")
        with self.locked() as exists:
            item = next((item for item in self.load() if item["id"] == identifier), None) if exists else None
            if item is None:
                raise PinError("This item is no longer pinned.")
            try:
                data = self.content_path(item).read_bytes()
            except OSError as error:
                raise PinError("The pinned file is missing or unreadable.") from error
            if hashlib.sha256(data).hexdigest() != identifier:
                raise PinError("The pinned file has changed. Re-pin the original item before pasting.")
            return data, item["mime"]

    def unpin(self, identifier):
        if not PIN_ID.fullmatch(identifier):
            raise PinError("Invalid pinned item.")
        with self.locked(write=True):
            items = self.load()
            removed = next((item for item in items if item["id"] == identifier), None)
            self.save([item for item in items if item["id"] != identifier])
            if removed:
                self.content_path(removed).unlink(missing_ok=True)

    def match_history(self, entries, decode=None):
        items = self.list()
        identifiers = {item["id"] for item in items}
        previews = {source.split("\t", 1)[1] for item in items
                    for source in item["sources"] if "\t" in source}
        matches = {}
        for entry in entries:
            identifier, separator, preview = entry.partition("\t")
            if not separator or preview not in previews or not re.fullmatch(r"[0-9]+", identifier):
                continue
            try:
                data = (decode(identifier) if decode is not None else subprocess.run(
                    ["cliphist", "decode"], input=identifier.encode(), capture_output=True,
                    timeout=5, check=True).stdout)
            except (OSError, subprocess.SubprocessError):
                continue  # The rolling history may have removed this item during refresh.
            digest = hashlib.sha256(data).hexdigest()
            if digest in identifiers:
                matches[entry] = digest
        return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "pin", "unpin", "read", "copy", "match"))
    parser.add_argument("identifier", nargs="?")
    args = parser.parse_args()
    store = PinStore()
    try:
        if args.command not in ("list", "match") and not args.identifier:
            parser.error("This command requires an item ID.")
        if args.command == "match":
            print(json.dumps(store.match_history(sys.stdin.read().splitlines()), ensure_ascii=False))
            return 0
        if args.command == "pin":
            if not re.fullmatch(r"[0-9]+", args.identifier):
                raise PinError("Invalid history item.")
            try:
                data = subprocess.run(["cliphist", "decode"], input=args.identifier.encode(),
                                      capture_output=True, timeout=10, check=True).stdout
            except (OSError, subprocess.SubprocessError) as error:
                raise PinError("Could not pin this history item. It may have been removed.") from error
            store.pin(data, sys.stdin.read())
        elif args.command == "unpin":
            store.unpin(args.identifier)
        elif args.command in ("read", "copy"):
            data, mime = store.read(args.identifier)
            if args.command == "read":
                sys.stdout.buffer.write(data)
            else:
                subprocess.run(["wl-copy", "--type", mime], input=data, check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            return 0
        print(json.dumps(store.list(), ensure_ascii=False))
    except (PinError, OSError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, PinError) else "Pinned clipboard operation failed."
        if args.command != "read":
            try:
                subprocess.Popen(["notify-send", "-a", "Clipboard", "Clipboard", message],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                pass
        print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
