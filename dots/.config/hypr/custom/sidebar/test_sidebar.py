import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


summary = load("sidebar_summary", HERE / "hyprtrack-summary.py")
installer = load("sidebar_installer", HERE / "customizations.py")


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "activity.db"
        self.connection = sqlite3.connect(self.database)
        self.addCleanup(self.connection.close)
        self.connection.execute("CREATE TABLE activity_samples (sampled_at TEXT, ended_at TEXT, last_seen_at TEXT)")
        self.now = summary.parse_timestamp("2026-10-26T12:00:00+05:30")

    def add(self, start, end=None, seen=None):
        self.connection.execute("INSERT INTO activity_samples VALUES (?, ?, ?)", (start, end, seen))
        self.connection.commit()

    def result(self):
        return summary.summarize(self.database, self.now)

    def test_overnight_session_is_split_at_ist_midnight(self):
        self.add("2026-10-25T23:45:00+05:30", "2026-10-26T00:30:00+05:30")
        result = self.result()
        self.assertEqual(result["todayMinutes"], 30)
        self.assertEqual(result["days"][-2]["minutes"], 15)
        self.assertEqual(result["averageMinutes"], 22.5)

    def test_open_session_stops_at_last_checkpoint(self):
        self.add("2026-10-26T09:00:00+05:30", seen="2026-10-26T09:15:00+05:30")
        result = self.result()
        self.assertEqual(result["todayMinutes"], 15)
        self.assertTrue(result["quiet"])

    def test_closed_session_uses_end_in_preference_to_checkpoint(self):
        self.add("2026-10-26T09:00:00+05:30", "2026-10-26T10:00:00+05:30", "2026-10-26T09:15:00+05:30")
        self.assertEqual(self.result()["todayMinutes"], 60)

    def test_future_checkpoint_capped_at_now(self):
        self.add("2026-10-26T11:45:00+05:30", seen="2026-10-26T13:00:00+05:30")
        self.assertEqual(self.result()["todayMinutes"], 15)

    def test_offset_equivalent_timestamp_uses_ist_day(self):
        self.add("2026-10-25T18:15:00Z", "2026-10-25T19:00:00Z")
        self.assertEqual(self.result()["todayMinutes"], 30)
        self.assertEqual(self.result()["days"][-2]["minutes"], 15)

    def test_range_crossing_start_is_clipped(self):
        self.add("2026-10-19T23:00:00+05:30", "2026-10-20T01:00:00+05:30")
        self.add("2026-10-19T09:00:00+05:30", "2026-10-19T12:00:00+05:30")
        result = self.result()
        self.assertEqual(result["days"][0]["minutes"], 60)
        self.assertEqual(sum(day["minutes"] for day in result["days"]), 60)
        self.assertEqual(result["averageMinutes"], 60)

    def test_legacy_minute_fallback_and_empty_state(self):
        self.assertEqual(self.result()["averageMinutes"], 0)
        self.assertEqual(len(self.result()["days"]), 7)
        self.add("2026-10-26T11:59:30+05:30")
        self.assertEqual(self.result()["todayMinutes"], 0.5)

    def test_read_does_not_change_database_and_missing_path_not_created(self):
        self.add("2026-10-26T11:00:00+05:30", seen="2026-10-26T11:59:45+05:30")
        before = hashlib.sha256(self.database.read_bytes()).hexdigest()
        self.assertFalse(self.result()["quiet"])
        self.assertEqual(before, hashlib.sha256(self.database.read_bytes()).hexdigest())
        missing = self.database.parent / "missing.db"
        with self.assertRaises(sqlite3.OperationalError):
            summary.summarize(missing, self.now)
        self.assertFalse(missing.exists())

    def test_committed_wal_data_is_visible(self):
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.add("2026-10-26T11:00:00+05:30", "2026-10-26T11:45:00+05:30")
        self.assertEqual(self.result()["todayMinutes"], 45)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        import json
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "config"
        self.backups = Path(self.temp.name) / "backups"
        self.edit = json.loads((HERE / "sidebar-integration.json").read_text())[0]
        self.content = self.root / self.edit["path"]
        self.content.parent.mkdir(parents=True)
        self.content.write_text(self.edit["before"])

    def test_install_is_idempotent_and_restore_preserves_fallback(self):
        installer.install(self.root, self.backups)
        self.assertEqual(self.content.read_text(), self.edit["after"])
        self.assertEqual(installer.plan(self.root), [])
        snapshots = list(self.backups.iterdir())
        installer.install(self.root, self.backups)
        self.assertEqual(list(self.backups.iterdir()), snapshots)
        installer.restore(self.root, self.backups, snapshots[0])
        self.assertEqual(self.content.read_text(), self.edit["before"])
        self.assertFalse((self.content.parent / "SidebarDashboard.qml").exists())
        self.assertEqual(len(list(self.backups.iterdir())), 2)

    def test_unknown_upstream_or_asset_edits_stop_before_install(self):
        self.content.write_text(self.edit["before"] + "\n// user change\n")
        with self.assertRaises(installer.CompatibilityError):
            installer.install(self.root, self.backups)
        self.assertFalse(self.backups.exists())
        self.content.write_text(self.edit["before"])
        (self.content.parent / "SidebarDashboard.qml").write_text("// user asset\n")
        with self.assertRaises(installer.CompatibilityError):
            installer.install(self.root, self.backups)
        self.assertEqual(self.content.read_text(), self.edit["before"])

    def test_partial_write_failure_rolls_back(self):
        from unittest.mock import patch
        original = installer.write_atomic
        count = 0

        def failing_write(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 3:
                raise OSError("simulated write failure")
            return original(*args, **kwargs)

        with patch.object(installer, "write_atomic", failing_write):
            with self.assertRaises(OSError):
                installer.install(self.root, self.backups)
        self.assertEqual(self.content.read_text(), self.edit["before"])
        self.assertFalse((self.content.parent / "HyprTrackSummary.qml").exists())


if __name__ == "__main__":
    unittest.main()
