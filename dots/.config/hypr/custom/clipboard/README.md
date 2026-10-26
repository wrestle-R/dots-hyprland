# Clipboard paste and desktop backups

The existing Super+V picker now pastes on click or Enter release. Up/Down moves
the selection without leaving the search field; the selected result stays visible.
Escape dismisses the picker. The Copy button remains copy-only. Ordinary app
launcher results still launch normally.

Direct paste, durable pins and the safe update procedure are implemented.
Moving all normal history into `/home/rdp/clipboard`, seven-day retention, an
explicit storage limit and transparency are still pending. Existing cliphist storage and capture watchers are unchanged.

## Pin and unpin

Click the pin icon beside an entry. The picker stays open and moves the saved
item to the top of the same clipboard list, marked Pinned. Recent unpinned history
follows it. There are no tabs. Click an item or use Up/Down and Enter to paste it;
the Copy action only copies. Use the crossed pin icon to unpin. Pin/unpin actions
are queued while the saved list is loading.

The Google Lens and music-recognition buttons are hidden in clipboard mode.
The shared general-purpose launcher still has its own controls. Search includes
both saved and recent items, with matching pins first. A background check compares
the bytes of potential history duplicates against pin hashes, so copied pins do
not repeat in the list even when cliphist assigns a new history ID. Entries with
identical previews and different content are kept.

Saved originals live under `~/clipboard/pinned/`:

```text
pinned/
  text/         original UTF-8 text files
  images/       original images, with their format extensions
  files/        other clipboard bytes
  index.json    pin metadata and history references
```

The folder is private (0700); originals and metadata use 0600. Pins have stable
content hashes, duplicate content shares one pin, and reads verify the saved
original before copying. They have no automatic expiry. Deleting or wiping the
normal history does not remove them. Unpin removes the saved original and its
metadata, leaving any normal-history entry alone. To edit a snippet, copy/edit it
in an app and pin the new version; directly changing a stored file invalidates its
content hash and stops paste until re-pinned.

Keep a separate private backup of `~/clipboard/pinned/` if you need pins after
formatting. The config backup tool does not include personal clipboard contents.
Never commit the pin folder to either source repository. `CLIPBOARD_PIN_ROOT`
can override its location (used only for isolated tests here).

## How paste works

1. Ask Hyprland for the active window before showing the clipboard layer.
2. Keep its address, PID and stable ID for this opening of the picker.
3. Click a result, or press and release Enter after choosing it with Up/Down.
4. Hide the layer, decode only the selected cliphist ID and copy its bytes using
   `wl-copy`.
5. Wait for the clipboard layer to disappear. Check that the original window
   still exists, restore its focus, and verify focus again before sending keys.
6. Send Ctrl+V for ordinary apps or Ctrl+Shift+V for known terminal window classes.

No Enter/Return is synthesized and clipboard content is never interpolated into
a shell command. Holding Enter keeps the picker open until release. Missing
targets, changed focus or command failures stop automatic paste and show a
notification. If copying already succeeded, the item remains available for a
manual paste. A lock prevents two paste helpers running at once.

Terminal matching uses `class` and `initialClass`, never the window title. It
covers kitty, Alacritty, foot/footclient, WezTerm, Ghostty, Konsole, GNOME Terminal,
Xfce Terminal, QTerminal, Tilix, Terminator, Termite, xterm/urxvt, st, Rio, Contour,
Sakura, Guake, Yakuake, Ptyxis, Console/kgx and Warp. Custom terminal app IDs may
need to be added to `TERMINAL` in `clipboard-paste.py`. Embedded terminals inside
editors share the editor's app ID, so their shortcut depends on the editor's
configuration. Programs decide how to interpret pasted text and supported MIME
types; the helper itself only sends the paste shortcut.

## Clear history

Use **Clear history** at the top of the clipboard picker. A modal shows how many
normal-history entries will be removed and explains that pinned items are kept.
The operation covers the entire history, even when a search filter is active.
Cancel has initial focus; Enter on Cancel or Escape dismisses the dialog without
deleting history. Select **Clear history** in the dialog to confirm.

While the wipe runs, the button is disabled. When normal history is empty the
button stays disabled, even if saved pins remain in the list. A failed wipe
shows a notification instead of reporting success. Clearing does not unpin items
or delete their independent saved originals.

Runtime requirements: the existing Hyprland Lua setup, QuickShell, Python 3,
`cliphist`, `wl-copy`, `ydotool`, a working ydotool daemon/socket and `notify-send`.
These were already installed on this machine. The focus dispatch uses Hyprland's
[Lua dispatch API](https://wiki.hypr.land/Configuring/Basics/Dispatchers/).

## Files and source copies

- `clipboard-paste.py`: runtime helper, installed into
  `~/.config/hypr/custom/scripts/clipboard-paste.py`.
- `clipboard-pins.py`: private pin storage, list, pin/unpin, read and copy helper,
  installed alongside the paste helper. Pinning decodes the original from
  cliphist; pasted pins are read from their saved files instead of a history ID.
- `clipboard-integration.json`: supported original, previous and current versions
  of the six integrated QuickShell files, stored separately from upstream source.
- `customizations.py`: read-only compatibility check, backup, installation and restore.
- `test_clipboard.py`: window guards, terminal shortcuts, idempotency, failure
  rollback and restore tests.

This directory is the rebuild record in `~/Desktop/code/Linux/End-4/clipboard/`.
An identical package is stored in
`~/Desktop/dots-hyprland/dots/.config/hypr/custom/clipboard/`, with the helper also
in that repository's `dots/.config/hypr/custom/scripts/`. The six upstream
QuickShell files in the dotfiles repo remain untouched. Installation applies
the checked integration only to the live config, reducing upstream merge
conflicts. Exact supported file versions allow upgrading the earlier paste-only
installation without stacking duplicate changes. Unknown upstream or personal
edits stop installation before writes, even when they look unrelated; update
the integration deliberately instead of replacing those edits. Compatibility
with an arbitrary future upstream version is not assumed.

## Recreate after reinstall

Install the upstream dotfiles and the runtime dependencies first. Restore the
other custom device settings from this Linux repository. From the Linux repo:

```bash
python3 End-4/clipboard/customizations.py check
python3 End-4/clipboard/customizations.py install
```

Alternatively, after restoring the dotfiles repository's custom folder:

```bash
python3 ~/.config/hypr/custom/clipboard/customizations.py check
python3 ~/.config/hypr/custom/clipboard/customizations.py install
```

The installer is idempotent. If already installed, it does not rewrite files or
create another snapshot. It checks all supported file versions before writing, backs up current
configs, checks for edits made during backup, then atomically replaces each file.
A write failure restores the files it already changed. Installation does not
fetch, merge, install packages or reload the desktop automatically.

QuickShell normally reloads when watched QML changes. If needed, trigger reload
after a successful install and review the loaded configuration:

```bash
touch ~/.config/quickshell/ii/shell.qml
qs -c ii log --tail 40
hyprctl configerrors
```

Check for `Configuration Loaded` and resolve new errors before continuing.
If no `ii` instance is running, use the existing desktop launch method or
`qs --daemonize --config ii`. Do not start duplicate shell instances.

## Backup, update and rollback

Follow the update procedure in `~/Desktop/code/Linux/README.md`.
Never delete `~/.config/hypr/custom` to make an update proceed. Check both the
merged repository and the live installed config before applying the integration.

```bash
python3 End-4/clipboard/customizations.py backup
python3 End-4/clipboard/customizations.py check --config-root ~/Desktop/dots-hyprland/dots/.config
python3 End-4/clipboard/customizations.py check
```

Snapshots live outside Git in `~/.local/state/hypr-customization-backups/`, with
private directory permissions. They include `hypr/`, `quickshell/ii/` and
`illogical-impulse/` if present, plus a manifest. These can contain private
settings; never commit or upload the snapshots. They do not back up clipboard
history, home directories, package versions or all desktop application settings.

Restore uses the exact snapshot directory printed by `backup`:

```bash
python3 End-4/clipboard/customizations.py restore --backup /absolute/path/to/saved-snapshot
hyprctl reload config-only
hyprctl configerrors
touch ~/.config/quickshell/ii/shell.qml
```

Restore first snapshots the current configuration, then replaces the saved
configuration directories. If a write fails it puts the previous directories
back. Review the restored custom Lua against the installed Hyprland version
before reloading. Restore does not downgrade packages or reset Git.

## Verification

```bash
python3 -m unittest discover -s End-4/clipboard -p 'test_*.py'
python3 End-4/clipboard/customizations.py check
```

Implementation checks on 2026-10-26 include 22 Python tests and an isolated
running picker using sample history and fake copy/paste executables. Keyboard
checks verified Down selects the second entry, Enter release closes the picker,
holding Enter does not paste, and terminal targets select Ctrl+Shift+V without
an Enter event. A mouse click also activated the expected entry exactly once and
closed the picker. The simulated backend leaves the real clipboard untouched.

A follow-up regression runs the installed `cliphist` binary against a separate
temporary database and verifies exact text and PNG bytes reach the copy step.
This caught a `cliphist` 0.7 input requirement: a bare numeric ID must be passed
without a trailing newline. The helper now uses that format. The test does not
read or change the real clipboard or history database.

Pin checks use private test storage and a separate real cliphist database. They
cover readable/private saved files, deduplication, reopening, unpinning, modified
file detection, history-wipe survival for PNG bytes, and guarded upgrades. The
running test picker additionally verified the pin button and Pinned tab, pinning
an image, shell restart persistence, pasting saved PNG bytes after history wipe,
and unpinning back to an empty list. Copy and key injection are simulated in
those UI tests, so personal clipboard contents stay untouched.

The unified-list update also verified pin-first ordering, recent-history ordering,
copied-pin deduplication with real cliphist ID changes, and unpin returning an
item to normal history. Two regression checks ensure preview collisions and
reused history IDs do not hide different clipboard contents.

Clear-history UI checks used a separate real cliphist database: opening/canceling
the dialog, initial Cancel focus, actual Escape/Enter cancellation, explicit
confirmation clearing every history row while keeping pins, and disabling Clear
when history is empty. The dialog was also rendered and visually checked. No
personal history was cleared during setup or verification.
