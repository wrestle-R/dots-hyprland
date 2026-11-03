# Internet Swap in the sidebar

Internet Swap is a separate [Linux Wi-Fi companion](https://github.com/wrestle-R/Internet-swap). The new row sits below HyprTrack’s existing passive live traffic readout. It shows the current Wi-Fi, a persistent automatic-switching toggle, and an arrow to open the Tauri window. It follows the desktop colors; the separate app and website use HyprTrack’s Plum palette with light/dark modes.

`internet-swap-sidebar.py` talks only to the daemon’s private local Unix socket. The bridge polls every two seconds while the sidebar is visible and stops when hidden. It never runs network tests itself. If the service is absent, the row says unavailable and leaves HyprTrack’s traffic reader working independently. No HyprTrack app or collector source changes are needed.

The sidebar installer also appends a guarded `hyprland.start` hook to custom/execs.lua, preserving existing collectors and other startup entries. `internet-swap-start.sh` starts the installed user service, with an AppImage fallback. The daemon has an exclusive lock, so reopening the GUI or repeated startup calls don’t create duplicate monitors.

## Restore on a rebuilt desktop

Download the Linux x86_64 AppImage from the Internet Swap release, then use its repository’s `scripts/install-local.sh /absolute/path/to/download.AppImage`. This puts the AppImage under ~/.local/bin, adds the application launcher and creates the user service. No root permissions are needed for that installation; NetworkManager still enforces the session’s existing network permissions.

Reapply the desktop integration after the normal upstream configuration is in place:

```sh
python3 End-4/sidebar/customizations.py check
python3 End-4/sidebar/customizations.py install
hyprctl reload config-only
```

The equivalent package is stored at dots-hyprland/dots/.config/hypr/custom/sidebar. The source fork’s upstream QuickShell files remain unchanged; the installer applies the checked live patches. The Wi-Fi helper and startup script are mirrored in custom/scripts for restoring the fork.

## Behavior and limits

Only saved, visible secured Wi-Fi profiles are eligible. Passwords stay with NetworkManager. An enabled daemon checks internet access over HTTPS and runs a bounded speed test on the current Wi-Fi roughly every two minutes. Alternative networks are tested on demand or during recovery. A speed-based switch requires fresh evidence of a meaningful improvement across repeated checks; failed candidates attempt to restore the previous Wi-Fi.

This does not combine bandwidth or preserve every active session through a switch. One adapter must disconnect before joining a different network. USB is outside selection logic; wired routes and their metrics are unchanged. Successful speed tests use about 1.25 MiB each plus protocol overhead. Pause stops automatic selection and active probes; local status and passive traffic display continue.

Use the sidebar installer’s private snapshot restore if the desktop integration needs to be undone. Stop the separate service with `systemctl --user stop internet-swap.service`; pausing is usually enough. Restoring desktop config doesn’t remove the app or its local settings.
