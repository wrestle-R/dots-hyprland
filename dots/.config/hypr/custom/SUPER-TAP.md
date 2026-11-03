# Super tap and clipboard lifecycle

A plain left/right Super tap toggles the app drawer. Other Super shortcuts never
trigger that drawer action on release. The override uses Hyprland's native
`release = true` binding to run the existing search IPC action, rather than
Quickshell's global shortcut release signal (which fires after a chord too).
Workspace-number press/release signals remain non-consuming. Fuzzel is only a
fallback if the search IPC call fails.

`super-tap.lua` lives in `~/.config/hypr/custom/`. The custom `keybinds.lua`
loads it before the final managed settings-shortcuts block. Keep that ordering:
the settings installer checks its final hook. The dots repo already includes the
file and hook. In the Linux rebuild record the matching files are
`End-4/super-tap.lua` and `End-4/keybinds.txt`.

To rebuild, install the fragment into the custom directory and retain the hook:

```bash
install -m 644 End-4/super-tap.lua ~/.config/hypr/custom/super-tap.lua
```

```lua
-- Native Super tap override
dofile((os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")) .. "/hypr/custom/super-tap.lua")
```

Then run `hyprctl reload config-only` and `hyprctl configerrors`.
No upstream base keybindings need editing; the custom override survives updates
when the custom directory is preserved.

The clipboard integration additionally cancels pending target capture on close
and switches between emoji/clipboard modes by the actual search prefix. An
asynchronous capture cannot reopen a canceled clipboard. Super+V toggles the
clipboard without the Super-release drawer competing for focus.

The image-states integration retains decoded thumbnail files for the shell
session. Entry IDs share cache files, so destroying one preview must not delete
a file another preview is loading. Existing startup cleanup clears this cache.
Reapply clipboard and image-states integrations after upstream config updates.

Verified on the live desktop using synthesized key events: left/right Super,
Super+A and an unbound Super+Z, three repeated Super+V open/close cycles,
Escape dismissal/reopen and cancellation of in-flight capture. Existing 22
clipboard tests and all customization compatibility checks pass.
