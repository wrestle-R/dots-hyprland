# Slumber, lock notifications and charge limits

Slumber locks using the existing QuickShell PAM/session-lock implementation, shows the lockscreen for two seconds, then switches displays off while apps continue working. Use **Super+Ctrl+L**, the notification-panel **play button**, or the Session menu. **Super+L** still locks; **Super+Shift+L** still sleeps.

The notification panel has a saved **Lid action: Sleep / Slumber** choice. Selecting a lid action changes future lid handling; Slumber now enters it immediately. Active Slumber keeps work running with either lid position until password unlock. It skips the normal 15-minute idle suspend, without blocking explicit sleep or critical-battery suspend. The coffee control retains its existing idle-inhibition role.

Allowed notifications display their app, sender/title and message on the secure lock surface. They wake an open display for six seconds, coalesced with a 15-second wake cooldown. Hidden apps and Do Not Disturb cannot trigger notification wakes. Keyboard/pointer activity gives 30 seconds to unlock, then reblanks. The built-in display stays off while the lid is closed. Lock notifications show the three newest allowed entries; the full list is available after unlock. Plain text is used; lockscreen notifications cannot execute links or app actions.

**Super+I → Notifications** controls visibility per app. Apps appear after sending notifications, and new apps are visible by default. The settings process reads app names from the existing notification cache; it does not start another notification server. Preferences live in `~/.local/state/quickshell/slumber.json`, separate from upstream settings.

The lockscreen follows the configured wallpaper, including a video thumbnail when applicable. Entry blur lasts 350ms, with no blur effect left active after the transition. SDDM uses `hehe.jpg`, a 650ms blur transition and a short login-panel fade/rise. Login still uses SDDM authentication and the selected session; no PAM or boot entries are changed.

## Charge limit

The notification panel reads actual hardware thresholds. The proposed limit defaults to95%, adjustable55–95%. Press Apply or enable the switch to authenticate and apply it. Turning it off sets the upper threshold to100%. Charging resumes five percentage points below the chosen upper limit. The firmware does not discharge a battery that is already above the cap.

The root-owned helper accepts only fixed battery sysfs paths and bounded integer thresholds. It serializes requests, verifies hardware readback and rolls back on write/persistence failure. A system service reapplies the last successful choice after reboot. Unsupported hardware shows Unsupported; rejected/cancelled authentication retains the previous limit. Initial installation does not change existing thresholds (this Dell was50/90%).

## Install

Requires the existing clipboard/sidebar/settings/image-state integrations, QuickShell, Lua Hyprland, hypridle, Python, PyGObject/Gio and the installed Polkit authentication agent. This version targets the inspected QuickShell0.3.2/Hyprland0.57.1 setup. It is intentionally strict about supported source versions.

From this directory:

```bash
python3 test_guardrails.py
python3 test_native.py
python3 customizations.py check
python3 customizations.py install
```

The installer preflights every file before writing, installs assets before consumers and the shell entry point last, preserves existing file modes, rejects concurrent edits and rolls back partial writes. It prints the private backup under `~/.local/state/hypr-slumber-backups/`. Review/save unsent settings/task drafts before reloading the shell. Do not reload while locked.

```bash
hyprctl reload config-only
hyprctl configerrors
# Restart the existing hypridle process after replacing its config.
# Restart QuickShell using the same environment as the current desktop:
env XDG_CONFIG_HOME="$HOME/.config" qs -p "$HOME/.config/quickshell/ii"
```

Do not start a second main shell while one is running. Stop the old main instance first using `qs -p "$HOME/.config/quickshell/ii" kill`; this temporarily removes the shell UI, not applications.

After reviewing/testing the SDDM theme and root helper:

```bash
pkexec /usr/bin/python3 "$PWD/install-system.py" install --wallpaper "$HOME/Pictures/Wallpapers/hehe.jpg"
```

This prints a root-only backup under `/var/lib/rdp-desktop/`, installs a separate `rdp-slumber` theme and SDDM override, and enables the threshold-restore unit. It never restarts SDDM or ends the session. The login theme takes effect at the next normal login. Theme images are copied to a system-readable directory, never loaded from a private home during login. Preserve the wallpaper file separately when reproducing on a new machine; it is not uploaded by this package.

## Pulling end-4 updates

Canonical code is `Linux/End-4/slumber/`; an identical package is kept at `dots-hyprland/dots/.config/hypr/custom/slumber/`. Fork upstream QuickShell files stay pristine; only custom assets/hooks are added to the source tree. The checked installer applies the live integration after the normal upstream setup and existing custom integrations.

1. Keep private backups and commit reviewed source changes before merging upstream.
2. Restore the Slumber layer using its printed backup before replacing upstream runtime files. An intervening personal edit stops restore for manual review.
3. Fetch/merge end-4 in the fork and review upstream changes. Do not automatically run `setup install` during a fetch or merge.
4. After a deliberate upstream install, check/reapply clipboard, sidebar, settings and image-state integrations, then run Slumber check/install last.
5. Unknown source changes stop before writes. Review/adapt the integration manifest against the new upstream files, rerun isolated checks and preserve existing customizations. Do not add unknown hashes merely to bypass the guard.
6. Recheck lock/wake, notifications, lid policy, explicit sleep, charge controls and restart persistence before relying on the update.

This prevents silent overwrites; it cannot guarantee compatibility with arbitrary future Hyprland/QuickShell/SDDM changes. A failed compositor lock must remain locked. A shell/compositor crash may require normal session recovery; the package does not disable the secure lock protocol to recover UI.

## Rollback

Restore only when unlocked. These commands do not clear notification history, tasks, app data or credentials.

```bash
python3 customizations.py restore --backup /path/printed/by/install
hyprctl reload config-only
# Restart hypridle and the main QuickShell instance after restore.
```

Restore refuses files edited after installation, rather than discarding those edits. Root file rollback is separate:

```bash
# If charge controls were used, restore the pre-feature hardware thresholds first:
pkexec /usr/local/libexec/rdp-charge-limit original
pkexec /usr/bin/python3 "$PWD/install-system.py" restore --backup /var/lib/rdp-desktop/PRINTED-BACKUP
```

Keep Breeze installed as a recovery theme. If the new login theme fails after a future update, use a TTY and remove only `/etc/sddm.conf.d/90-rdp-slumber.conf` to return to the previous theme choice. This does not bypass password authentication. Do not restart SDDM while unsaved apps are running.

## Verification

`test_guardrails.py` uses only temporary files and fake sysfs: install/restore/idempotency, unknown-file rejection, partial-write rollback, concurrent-edit refusal, charge apply/off and persistence-failure rollback. Native isolated checks and live deployment results are recorded separately in `VERIFICATION.md`; unperformed physical/reboot checks must remain identified there.

Combined rollback for the final live layer: `python3 customizations.py restore --backup /home/rdp/.local/state/hypr-slumber-backups/rollback-215127n0 --config-root /home/rdp/.config`. This returns all managed user-config files to their pre-feature versions in one checked transaction. System theme/helper rollback remains separate as described above.
