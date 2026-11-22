# Slumber, lock notifications and charge limits

Slumber locks using the existing QuickShell PAM/session-lock implementation, shows the lockscreen for two seconds, then switches displays off while apps continue working. Use **Super+Ctrl+L**, the notification-panel **play button**, or the Session menu. **Super+L** still locks; **Super+Shift+L** still sleeps.

The notification panel has a saved **Lid action: Sleep / Slumber** choice. Selecting a lid action changes future lid handling; Slumber now enters it immediately. Active Slumber keeps work running with either lid position until password unlock. It skips the normal 15-minute idle suspend, without blocking explicit sleep or critical-battery suspend. The coffee control retains its existing idle-inhibition role.

Only T3 Code, Codex/Multi Codex and Visual Studio Code notifications are allowed on the lockscreen. They display their app, sender/title and message on the secure lock surface. All other apps, including new or unknown apps, remain hidden and cannot wake Slumber. They wake an open display for six seconds, coalesced with a 15-second wake cooldown. Hidden apps and Do Not Disturb cannot trigger notification wakes. Keyboard/pointer activity gives 30 seconds to unlock, then reblanks. The built-in display stays off while the lid is closed. Lock notifications show the three newest allowed entries; the full list is available after unlock. Plain text is used; lockscreen notifications cannot execute links or app actions.

**Super+I → Notifications** has three switches for these approved app groups. Turning one off also blocks its Slumber wakes. Exact normalized aliases cover the installed desktop names/IDs; substring matches and generic Electron names are rejected. The settings page does not start another notification server. Notification app names are routing metadata, not cryptographically authenticated sender identities. Preferences live in `~/.local/state/quickshell/slumber.json`, separate from upstream settings.

The lockscreen follows the current configured wallpaper (or video thumbnail), with a stronger settled blur: blurMax24 at0.45, entering from1 over650ms after the image loads. Password controls and notifications remain crisp. SDDM displays a sharp local wallpaper, geometric clock and three aligned login rows. The installer validates the theme in the native greeter before writing system files.

## Charge limit

The notification panel reads actual hardware thresholds. The proposed limit defaults to95%, adjustable55–95%. Press Apply or enable the switch to authenticate and apply it. Turning it off sets the upper threshold to100%. Charging resumes five percentage points below the chosen upper limit. The firmware does not discharge a battery that is already above the cap. The panel shows actual capacity, AC state and charging status, and explicitly identifies an above-cap battery with charging paused. A saved but inactive Custom-mode policy prompts Apply instead of showing the toggle as active.

On Dell systems advertising charge modes, enabling the cap also selects Custom mode; thresholds saved under Adaptive mode are not treated as enforced. Turning the cap off selects Standard mode where available. The helper records the original charge mode for restoration and rolls it back along with thresholds on a failed apply.

The root-owned helper accepts only fixed battery sysfs paths and bounded integer thresholds. It serializes requests, verifies hardware readback and rolls back on write/persistence failure. A system service reapplies the last successful choice after reboot. Unsupported hardware shows Unsupported; rejected/cancelled authentication retains the previous limit. Initial installation does not change existing thresholds (this Dell was50/90%).

## Install

Requires a Qt6 SDDM greeter and the existing clipboard/sidebar/settings/image-state integrations, QuickShell, Lua Hyprland, hypridle, Python, PyGObject/Gio and the installed Polkit authentication agent. This version targets the inspected QuickShell0.3.2/Hyprland0.57.1 setup. It is intentionally strict about supported source versions.

From this directory:

```bash
python3 test_sddm.py
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

Image preparation and an isolated software-rendered SDDM test-mode load complete before any system configuration writes. Failed conversion, missing Qt modules or invalid QML leave the previous installation untouched. The existing all-file hash preflight and transactional rollback protect against overwrite and partial-write failures. Missing images at runtime retain a solid dark background and usable controls.

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

### Optional fingerprint sign-in

Install Arch's `fprintd` package, then run `fprintd-enroll` and `fprintd-verify` as your regular user. The Quickshell lock checks for enrolled fingers and automatically re-arms the reader after a missed scan or timeout. Its password field stays available while scanning. Clearing an idle password field does not stop fingerprint authentication.

SDDM uses passwords only. The fingerprint installer removes the previous SDDM PAM block, selector helper and theme override when upgrading. It does not change the stock password, account or session stack.

For concurrent terminal password entry and fingerprint scanning, install `pam-fprint-grosshack` from the AUR, then run `sudo python3 fingerprint-auth.py enable "$USER"` from this directory. This uses a separate `sudo-fingerprint` PAM service. The password prompt appears immediately and the reader scans for up to 60 seconds, allowing up to 10 missed scans. After that, sudo keeps its normal password fallback. This replaces the old two-second fingerprint-first wait. The module is an additional third-party PAM dependency; SDDM and the lock's password authentication do not use it.

`sudo -k -i` and graphical askpass retain the stock sudo password service for recovery. Only touch the reader for sudo requests you initiated. From a password-only root shell, run `python3 /absolute/path/to/fingerprint-auth.py disable your-username` to remove the terminal integration. Disabling it does not delete enrolled fingerprints.
