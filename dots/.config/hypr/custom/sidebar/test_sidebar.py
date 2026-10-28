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


class NetworkTests(unittest.TestCase):
    def test_rates_ignore_new_reset_and_recreated_interfaces(self):
        self.assertEqual(summary.network_rates({"wlan0": (2, 1000, 500)}, {"wlan0": (2, 3000, 1000)}, 2), (1000, 250))
        for current in [{"wlan0": (3, 900000, 800000)}, {"wlan0": (2, 2, 1)}, {"eth0": (4, 80000, 90000)}]:
            self.assertEqual(summary.network_rates({"wlan0": (2, 1000, 500)}, current, 1), (0, 0))
        self.assertEqual(summary.network_rates({}, {}, 0), (None, None))

    def test_only_active_physical_counters_are_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, physical, state in [("lo", False, "up"), ("tun0", False, "up"), ("wlan0", True, "up"), ("eth0", True, "down")]:
                path = root / name
                (path / "statistics").mkdir(parents=True)
                if physical: (path / "device").mkdir()
                for file, value in [("operstate", state), ("ifindex", "2"), ("statistics/rx_bytes", "1000"), ("statistics/tx_bytes", "200")]:
                    (path / file).write_text(value)
            self.assertEqual(summary.network_counters(root), {"wlan0": (2, 1000, 200)})

    def test_today_total_uses_ist_and_both_directions_without_mutation(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        now = summary.parse_timestamp("2026-10-27T12:00:00+05:30")
        midnight = now.replace(hour=0)
        self.assertIsNone(summary.today_internet(connection, midnight, now))
        connection.execute("CREATE TABLE network_samples(sampled_at INTEGER, rx_bytes INTEGER, tx_bytes INTEGER)")
        connection.execute("CREATE TABLE network_daily_summaries(day TEXT, rx_bytes INTEGER, tx_bytes INTEGER)")
        connection.executemany("INSERT INTO network_samples VALUES(?,?,?)", [(int(midnight.timestamp())-1, 10000, 10000), (int(midnight.timestamp()), 100, 25), (int(now.timestamp()), 50, 5), (int(now.timestamp())+1, 9999, 9999)])
        connection.executemany("INSERT INTO network_daily_summaries VALUES(?,?,?)", [("2026-10-27", 20, 10), ("2026-10-26", 9000, 9000)])
        connection.execute("PRAGMA query_only=ON")
        self.assertEqual(summary.today_internet(connection, midnight, now), 210)


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

    def test_upgrade_preserves_custom_shortcuts_and_settings_suffix(self):
        self.content.write_text(self.edit["previous"][-1])
        keybinds = self.root / "hypr/custom/keybinds.lua"
        keybinds.parent.mkdir(parents=True)
        original = 'hl.bind("SUPER + W", "zen-browser")\n'
        suffix = '\n-- Local settings shortcuts (managed integration)\n-- existing settings integration\n'
        keybinds.write_text(original + suffix)
        installer.install(self.root, self.backups)
        updated = keybinds.read_text()
        self.assertTrue(updated.startswith(original))
        self.assertTrue(updated.endswith(suffix))
        self.assertEqual(updated.count(installer.SPOTIFY_HOOK), 1)
        self.assertEqual(installer.plan(self.root), [])

    def test_partial_spotify_hook_stops_before_any_writes(self):
        keybinds = self.root / "hypr/custom/keybinds.lua"
        keybinds.parent.mkdir(parents=True)
        keybinds.write_text('local spotifyShortcuts = "personal-change"\n')
        with self.assertRaises(installer.CompatibilityError):
            installer.install(self.root, self.backups)
        self.assertFalse(self.backups.exists())
        self.assertEqual(self.content.read_text(), self.edit["before"])


if __name__ == "__main__":
    unittest.main()
