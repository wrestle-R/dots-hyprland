# HyprTrack and to-do sidebar

Super+A opens the existing left drawer, at its original 460px configured width.
The top shows **Today’s usage**, **Daily average**, and a seven-day line chart.
Hover over the line for a day's date and duration. The arrow opens the installed
HyprTrack app. There is no weekly-total metric, scratchpad, or shortcut footer.
The logo is the original `next/app/icon.svg` asset copied byte-for-byte from
HyprTrack, rather than a recreated waveform. The source app remains unchanged.

The to-do list underneath shares the shell's existing task service. Opening the
drawer focuses the input automatically: start typing, then press Enter to create
a task. Focus stays there for the next one, and unfinished drafts survive closing
and reopening the drawer. You can also click its plus button. The heading's plus moves
focus to that input. Click a checkbox to complete/reopen a task, or its close
button to delete it. Unfinished tasks come first, with original order preserved
inside each group. Text wraps, long lists scroll, and tasks persist across shell
restarts in `${XDG_STATE_HOME:-~/.local/state}/quickshell/user/todo.json` on this
QuickShell setup. Existing tasks are reused; no demonstration tasks are installed.
The other shell to-do widget uses this same list. Back it up privately if needed
when formatting the device; configuration snapshots do not include personal tasks.

## Data and refresh

`hyprtrack-summary.py` reads only timestamp columns from the installed collector's
database at `~/.local/bin/hyprtrack/collector/hyprtrack.db`. It does not change
HyprTrack source, the collector, or its schema. SQLite is opened read-only with
query-only enabled; committed WAL data remains visible. A missing database is
never created. No window titles, app names, URLs, network data, or telemetry are
read or sent anywhere. Runtime requirements are existing QuickShell and Python 3
with its standard SQLite module. There is no extra collector or service.

The range is today and the preceding six calendar days in IST, matching
HyprTrack. Intervals are split at midnight and clipped to the range/current time.
Closed sessions use their end time; open sessions stop at their last checkpoint,
so idle/closed collectors do not accumulate invented usage. Legacy minute samples
use HyprTrack's one-minute fallback. The average matches HyprTrack's seven-day
overview: days with recorded usage, including today's partial day. Zero-usage days
still appear in the chart. The metric tooltip explains this definition.

Refresh happens on opening the drawer and every 15 seconds while it is visible.
At most one request runs at once; a five-second timeout bounds failures. Missing
or incompatible data shows an unavailable state rather than fake zero values.
No recent checkpoints are marked quietly as “No recent activity”. Database reads
never launch the full app; only the explicit arrow does that.

## Install or recreate

Canonical rebuild package: `~/Desktop/code/Linux/End-4/sidebar/`. An identical
copy lives in the dotfiles repo's `dots/.config/hypr/custom/sidebar/`. The upstream
QuickShell source files in that repo remain unchanged. The installer applies
one supported-version integration to the live `SidebarLeftContent.qml`, adds
two local QML components plus the original logo, and installs the helper under
`~/.config/hypr/custom/scripts/hyprtrack-summary.py`. Existing optional
AI/Translator/Anime pages remain available when enabled; the dashboard is first.

From the Linux repo, after installing the upstream dots:

```bash
python3 End-4/sidebar/customizations.py check
python3 End-4/sidebar/customizations.py install
touch ~/.config/quickshell/ii/shell.qml
qs -c ii log --tail 40
hyprctl configerrors
```

Or use `~/.config/hypr/custom/sidebar/customizations.py` from a restored custom
folder. The installer verifies all integration points before writing, backs up
configs privately under `~/.local/state/hypr-customization-backups/`, detects
intervening edits, writes atomically, and rolls back partial write failures.
Repeated installs are a no-op. Unknown upstream or personal edits stop installation
before writes; adapt the integration deliberately instead of overwriting them.
Updates to existing custom component versions likewise need explicit migration
support; the installer does not silently replace differing assets.

Before upstream updates, run both the clipboard and sidebar compatibility checks
against the merged source, then reapply both packages after `./setup install`.
See the main Linux README for the full update procedure. To restore, use the
exact snapshot directory printed at installation:

```bash
python3 End-4/sidebar/customizations.py restore --backup /absolute/path/to/snapshot
hyprctl reload config-only
touch ~/.config/quickshell/ii/shell.qml
```

Restore snapshots the state it replaces too. It restores configs, not personal
usage/task data, installed packages, or Git state.

## Verification

```bash
python3 -m unittest discover -s End-4/sidebar -p 'test_*.py'
python3 End-4/sidebar/customizations.py check
```

Tests cover midnight/range clipping, timezone equivalence, stale checkpoints,
future limits, legacy data, empty/missing databases, committed WAL reads,
read-only preservation, install idempotency, unknown edits, rollback and restore.
An isolated running QML drawer also checks task creation, sorting, completion,
deletion, persistence, data/error states, visibility-based refresh and original
drawer width. Test usage/tasks stay separate from personal data.
