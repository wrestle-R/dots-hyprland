#!/usr/bin/env python3
"""Read local activity totals and passive network counters for the sidebar."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time


IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_DATABASE = Path.home() / ".local/bin/hyprtrack/collector/hyprtrack.db"


def parse_timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp has no timezone")
    return result.astimezone(IST)


def summarize(database, now=None):
    now = (now or datetime.now(IST)).astimezone(IST)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = midnight - timedelta(days=6)
    buckets = [0.0] * 7
    latest = None
    # mode=ro never creates a missing database. Do not use immutable=1 on a
    # live collector database: committed WAL pages must remain visible.
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)
    try:
        connection.execute("PRAGMA query_only = ON")
        connection.execute("BEGIN")
        internet = today_internet(connection, midnight, now)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(activity_samples)")}
        if "sampled_at" not in columns:
            raise ValueError("Unsupported activity database")
        intervals = {"ended_at", "last_seen_at"}.issubset(columns)
        end_column = "ended_at" if intervals else "NULL"
        seen_column = "last_seen_at" if intervals else "NULL"
        # Read timestamps only, never app names, window titles or browser URLs.
        # julianday also handles offset-equivalent RFC3339 timestamps correctly.
        end_expression = f"COALESCE({end_column}, {seen_column}, datetime(sampled_at, '+1 minute'))"
        query = f"""SELECT sampled_at, {end_column}, {seen_column}
                    FROM activity_samples
                    WHERE julianday(sampled_at) <= julianday(?)
                      AND julianday({end_expression}) >= julianday(?)"""
        for sampled, ended, seen in connection.execute(query, (now.isoformat(), start.isoformat())):
            sample_start = parse_timestamp(sampled)
            sample_end = parse_timestamp(ended or seen) if ended or seen else sample_start + timedelta(minutes=1)
            checkpoint = parse_timestamp(seen or ended or sampled)
            latest = max(latest, checkpoint) if latest else checkpoint
            cursor = max(sample_start, start)
            stop = min(sample_end, now)
            while cursor < stop:
                boundary = cursor.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                end = min(stop, boundary)
                index = (cursor.date() - start.date()).days
                if 0 <= index < 7:
                    buckets[index] += (end - cursor).total_seconds() / 60
                cursor = end
    finally:
        connection.close()

    # HyprTrack's 7d overview averages days with recorded usage. Match that
    # definition, including today's partial day, instead of inventing a new one.
    rounded = [round(value, 2) for value in buckets]
    active = [value for value in rounded if value > 0]
    return {
        "ok": True,
        "todayInternetBytes": internet,
        "todayMinutes": rounded[-1],
        "averageMinutes": round(sum(active) / len(active), 2) if active else 0,
        "activeDays": len(active),
        "days": [{"date": (start + timedelta(days=i)).date().isoformat(),
                  "label": (start + timedelta(days=i)).strftime("%a"),
                  "minutes": minutes} for i, minutes in enumerate(rounded)],
        "latestAt": latest.isoformat() if latest else None,
        "quiet": latest is None or (now - latest).total_seconds() > 120,
    }


def today_internet(connection, midnight, now):
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "network_samples" not in tables:
        return None
    total = connection.execute(
        "SELECT COALESCE(SUM(rx_bytes),0)+COALESCE(SUM(tx_bytes),0) FROM network_samples "
        "WHERE sampled_at>=? AND sampled_at<=?",
        (int(midnight.timestamp()), int(now.timestamp())),
    ).fetchone()[0]
    if "network_daily_summaries" in tables:
        total += connection.execute(
            "SELECT COALESCE(SUM(rx_bytes),0)+COALESCE(SUM(tx_bytes),0) "
            "FROM network_daily_summaries WHERE day=?", (midnight.date().isoformat(),)
        ).fetchone()[0]
    return total


def network_counters(sys_net=Path("/sys/class/net")):
    """Read one physical interface layer only. No sockets, requests or probes."""
    counters = {}
    for entry in sys_net.iterdir():
        if not (entry / "device").exists():
            continue
        try:
            if (entry / "operstate").read_text().strip() not in ("up", "unknown"):
                continue
            counters[entry.name] = (int((entry / "ifindex").read_text()),
                int((entry / "statistics/rx_bytes").read_text()),
                int((entry / "statistics/tx_bytes").read_text()))
        except (OSError, ValueError):
            continue
    return counters


def network_rates(previous, current, elapsed):
    rx = tx = 0
    if elapsed <= 0:
        return None, None
    for name, (identity, received, sent) in current.items():
        old = previous.get(name)
        # Reconnects, recreated interfaces and reset counters need a fresh baseline.
        if old is None or identity != old[0] or received < old[1] or sent < old[2]:
            continue
        rx += received - old[1]
        tx += sent - old[2]
    return rx / elapsed, tx / elapsed


def watch_speed():
    previous = None
    previous_time = None
    while True:
        try:
            current = network_counters()
            now = time.monotonic()
            rx, tx = network_rates(previous, current, now - previous_time) if previous is not None else (None, None)
            result = {"ready": rx is not None, "rxBytesPerSecond": rx,
                      "txBytesPerSecond": tx, "connected": bool(current)}
            previous, previous_time = current, now
        except OSError:
            previous = previous_time = None
            result = {"ready": False}
        try:
            print(json.dumps(result, separators=(",", ":")), flush=True)
        except BrokenPipeError:
            return 0
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--watch-speed", action="store_true", help="Passively sample local byte counters once per second")
    args = parser.parse_args()
    if args.watch_speed:
        return watch_speed()
    try:
        result = summarize(args.database)
    except (OSError, sqlite3.Error, ValueError, TypeError, OverflowError):
        # Keep private paths and database contents out of shell notifications/logs.
        print(json.dumps({"ok": False, "message": "Usage unavailable. Check the HyprTrack database."}))
        return 1
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
