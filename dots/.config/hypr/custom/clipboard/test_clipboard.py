import importlib.util
import base64
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paste = load("clipboard_paste", "clipboard-paste.py")
custom = load("customizations", "customizations.py")
pins = load("clipboard_pins", "clipboard-pins.py")
TARGET = {"address": "0x123", "pid": 123, "stableId": "a", "mapped": True, "class": "kitty"}


class PasteTests(unittest.TestCase):
    def test_terminal_shortcuts_do_not_include_enter(self):
        for app in ("kitty", "Alacritty", "footclient", "org.wezfurlong.wezterm", "org.gnome.Terminal", "org.kde.konsole"):
            with self.subTest(app=app):
                keys = paste.paste_keys({"class": app, "initialClass": ""})
                self.assertIn("42:1", keys)
                self.assertEqual(keys[-1], "29:0")
                self.assertFalse(any(key.split(":")[0] in ("28", "96") for key in keys))

    def test_browser_and_title_do_not_select_terminal_shortcut(self):
        keys = paste.paste_keys({"class": "zen", "title": "Terminal documentation"})
        self.assertEqual(keys, ["29:1", "47:1", "47:0", "29:0"])

    def test_reused_address_is_not_original_window(self):
        with patch.object(paste, "hypr", return_value=[dict(TARGET, stableId="b")]):
            with self.assertRaises(paste.PasteError):
                paste.find_target(TARGET)

    def test_missing_target_never_injects_keys(self):
        with patch.object(paste, "run") as run:
            with self.assertRaises(paste.PasteError):
                paste.find_target(None)
            run.assert_not_called()

    def test_invalid_entry_does_not_reach_commands(self):
        with patch.object(paste, "run") as run:
            with self.assertRaises(paste.PasteError):
                paste.paste("12;touch /tmp/bad", TARGET)
            run.assert_not_called()

    def test_decode_bytes_pass_unchanged_and_only_paste_keys_are_sent(self):
        data = b"hello\n$(never-a-shell)\x00\xff"
        with patch.object(paste, "run") as run, patch.object(paste, "wait_for_target", return_value=TARGET):
            run.return_value.stdout = data
            paste.paste("123", TARGET)
        self.assertEqual(run.call_args_list[1].kwargs["input"], data)
        self.assertEqual(run.call_args_list[2].args[0],
                         ["ydotool", "key", "-d", "12", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"])

    def test_closed_destination_leaves_copy_without_sending_keys(self):
        with patch.object(paste, "run") as run, patch.object(paste, "wait_for_target", side_effect=paste.PasteError("closed")):
            run.return_value.stdout = b"test"
            with self.assertRaises(paste.PasteError):
                paste.paste("123", TARGET)
        self.assertEqual([call.args[0][0] for call in run.call_args_list], ["cliphist", "wl-copy"])

    @unittest.skipUnless(shutil.which("cliphist"), "cliphist binary is required for the decode regression")
    def test_real_cliphist_decodes_selected_id_for_text_and_image(self):
        samples = (
            b"clipboard decode regression\nsecond line",
            base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1sAAAAASUVORK5CYII="),
        )
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "test.db")
            original_run = paste.run
            for sample in samples:
                with self.subTest(kind="image" if sample.startswith(b"\x89PNG") else "text"):
                    subprocess.run(["cliphist", "-db-path", db, "store"], input=sample, capture_output=True, check=True)
                    listing = subprocess.run(["cliphist", "-db-path", db, "list"], capture_output=True, check=True).stdout
                    entry_id = listing.splitlines()[0].split(b"\t", 1)[0].decode()
                    copied = []
                    injected = []

                    def execute(argv, **kwargs):
                        if argv == ["cliphist", "decode"]:
                            return original_run(["cliphist", "-db-path", db, "decode"], **kwargs)
                        if argv == ["wl-copy"]:
                            copied.append(kwargs["input"])
                            return subprocess.CompletedProcess(argv, 0)
                        if argv[0] == "ydotool":
                            injected.append(argv)
                            return subprocess.CompletedProcess(argv, 0)
                        self.fail(f"Unexpected command: {argv[0]}")

                    with patch.object(paste, "run", side_effect=execute), \
                         patch.object(paste, "wait_for_target", return_value=TARGET):
                        paste.paste(entry_id, TARGET)
                    self.assertEqual(copied, [sample])
                    self.assertEqual(len(injected), 1)

    def test_focus_switch_after_restore_aborts(self):
        with patch.object(paste, "overview_visible", return_value=False), \
             patch.object(paste, "find_target", return_value=TARGET), \
             patch.object(paste, "run"), patch.object(paste.time, "sleep"), \
             patch.object(paste, "hypr", side_effect=[TARGET, dict(TARGET, address="0x456")]):
            with self.assertRaises(paste.PasteError):
                paste.wait_for_target(TARGET)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config"
        self.backups = self.root / "backups"
        self.package = self.root / "package"
        self.package.mkdir()
        (self.package / "clipboard-paste.py").write_text("# helper\n")
        (self.package / "clipboard-integration.json").write_text(json.dumps([
            {"path": "quickshell/ii/one.qml", "before": "old one", "after": "new one"},
            {"path": "quickshell/ii/two.qml", "before": "old two", "after": "new two"},
        ]))
        for name, text in (("one.qml", "old one"), ("two.qml", "old two")):
            path = self.config / "quickshell/ii" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        (self.config / "hypr/custom").mkdir(parents=True)
        self.custom_file = self.config / "hypr/custom/keybinds.lua"
        self.custom_file.write_text("keep this binding")
        self.addCleanup(patch.stopall)
        patch.object(custom, "HERE", self.package).start()

    def test_repeated_install_does_not_change_or_rebackup(self):
        custom.install(self.config, self.backups)
        count = len(list(self.backups.iterdir()))
        self.assertEqual(custom.plan(self.config), [])
        custom.install(self.config, self.backups)
        self.assertEqual(len(list(self.backups.iterdir())), count)
        self.assertEqual(self.custom_file.read_text(), "keep this binding")

    def test_upstream_change_stops_entire_install(self):
        (self.config / "quickshell/ii/two.qml").write_text("unrecognized upstream code")
        with self.assertRaises(custom.CompatibilityError):
            custom.install(self.config, self.backups)
        self.assertEqual((self.config / "quickshell/ii/one.qml").read_text(), "old one")
        self.assertFalse(self.backups.exists())

    def test_supported_previous_version_can_upgrade_but_unknown_edits_stop(self):
        edits = json.loads((self.package / "clipboard-integration.json").read_text())
        edits[0].update(exact=True, previous=["previous one"])
        (self.package / "clipboard-integration.json").write_text(json.dumps(edits))
        target = self.config / "quickshell/ii/one.qml"
        target.write_text("previous one")
        custom.install(self.config, self.backups)
        self.assertEqual(target.read_text(), "new one")
        self.assertEqual(custom.plan(self.config), [])
        target.write_text("previous one with personal edits")
        with self.assertRaises(custom.CompatibilityError):
            custom.plan(self.config)

    def test_write_failure_rolls_back_all_previous_edits(self):
        original = custom.write_atomic
        calls = 0

        def fail_second(path, content, mode=None):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated write failure")
            original(path, content, mode)

        with patch.object(custom, "write_atomic", side_effect=fail_second):
            with self.assertRaises(OSError):
                custom.install(self.config, self.backups)
        self.assertEqual((self.config / "quickshell/ii/one.qml").read_text(), "old one")

    def test_restore_preserves_the_pre_restore_configuration(self):
        snapshot = custom.backup(self.config, self.backups)
        self.custom_file.write_text("newer binding")
        custom.restore(self.config, self.backups, snapshot)
        self.assertEqual(self.custom_file.read_text(), "keep this binding")
        others = [p for p in self.backups.iterdir() if p != snapshot]
        self.assertEqual(len(others), 1)
        self.assertEqual((others[0] / "hypr/custom/keybinds.lua").read_text(), "newer binding")


class PinTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "pins"
        self.store = pins.PinStore(self.root)

    def test_read_only_empty_list_does_not_create_storage(self):
        self.assertEqual(self.store.list(), [])
        self.assertFalse(self.root.exists())

    def test_text_survives_reopening_and_has_private_readable_file(self):
        data = "saved text\nwith unicode: café".encode()
        identifier = self.store.pin(data, "12\tsaved text")
        reopened = pins.PinStore(self.root)
        item = reopened.list()[0]
        self.assertEqual(reopened.read(identifier)[0], data)
        self.assertEqual(Path(item["path"]).suffix, ".txt")
        self.assertEqual(Path(item["path"]).read_bytes(), data)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual(Path(item["path"]).stat().st_mode & 0o777, 0o600)

    def test_repinning_same_content_deduplicates_and_tracks_history_references(self):
        identifier = self.store.pin(b"keep this", "1\tkeep this")
        again = self.store.pin(b"keep this", "2\tkeep this")
        self.assertEqual(identifier, again)
        self.assertEqual(len(self.store.list()), 1)
        self.assertEqual(self.store.list()[0]["sources"], ["1\tkeep this", "2\tkeep this"])

    def test_unpin_deletes_only_selected_pin(self):
        first = self.store.pin(b"one")
        second = self.store.pin(b"two")
        first_file = next(Path(p["path"]) for p in self.store.list() if p["id"] == first)
        self.store.unpin(first)
        self.assertFalse(first_file.exists())
        self.assertEqual(self.store.read(second)[0], b"two")
        self.store.unpin(first)
        self.assertEqual(len(self.store.list()), 1)

    def test_modified_file_is_not_silently_pasted(self):
        identifier = self.store.pin(b"original")
        Path(self.store.list()[0]["path"]).write_bytes(b"changed")
        with self.assertRaises(pins.PinError):
            self.store.read(identifier)

    def test_history_matching_handles_new_ids_without_hiding_preview_collisions(self):
        prefix = b"same visible prefix " * 6
        pinned = prefix + b"pinned ending"
        other = prefix + b"different ending"
        pin_id = self.store.pin(pinned, "1\tsame preview")
        samples = {"2": pinned, "3": other}
        matches = self.store.match_history(["2\tsame preview", "3\tsame preview"], samples.__getitem__)
        self.assertEqual(matches, {"2\tsame preview": pin_id})

    def test_reused_history_id_is_not_mistaken_for_saved_content(self):
        self.store.pin(b"original complete content", "1\tsame preview")
        matches = self.store.match_history(["1\tsame preview"], lambda _: b"other complete content")
        self.assertEqual(matches, {})

    @unittest.skipUnless(shutil.which("cliphist"), "cliphist is required")
    def test_real_history_wipe_does_not_delete_pinned_image(self):
        data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1sAAAAASUVORK5CYII=")
        db = str(Path(self.temp.name) / "history.db")
        subprocess.run(["cliphist", "-db-path", db, "store"], input=data, capture_output=True, check=True)
        listing = subprocess.run(["cliphist", "-db-path", db, "list"], capture_output=True, check=True).stdout
        entry = listing.splitlines()[0]
        identifier = entry.split(b"\t")[0]
        decoded = subprocess.run(["cliphist", "-db-path", db, "decode"], input=identifier, capture_output=True, check=True).stdout
        pin_id = self.store.pin(decoded, entry.decode())
        subprocess.run(["cliphist", "-db-path", db, "wipe"], capture_output=True, check=True)
        self.assertEqual(self.store.read(pin_id)[0], data)
        item = self.store.list()[0]
        self.assertEqual(item["mime"], "image/png")
        self.assertEqual(Path(item["path"]).suffix, ".png")


if __name__ == "__main__":
    unittest.main()
