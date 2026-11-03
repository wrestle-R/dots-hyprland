# Settings and keybindings

Super+I opens the existing QuickShell settings window with five tabs:

- **General:** audio, battery, language, sounds and time.
- **Appearance:** wallpaper, colors and the everyday bar/screen options.
- **Keybindings:** searchable active shortcuts and an app/command/script editor.
- **Services:** search, weather, recording paths and other non-AI utilities.
- **Advanced:** detailed bar/workspace, background/clock, interface/font and color
  generation controls, plus About. Pick a section from the menu at the top.

The unused AI system-prompt section, Gemini translation generator, Gemini clock
styling switch and AI/anime policy controls are removed from the settings UI.
The integration keeps the AI sidebar, translator and AI clock styling disabled.
The AI text-summary mouse shortcut is unbound in the custom Hyprland config.
Upstream AI source files/packages are retained so updates remain straightforward;
this does not uninstall unrelated apps such as Codex or remove their settings.

Super+W opens `zen-browser`, overridden in the custom `keybinds.lua`; the matching
snippet is in `End-4/keybinds.txt`. Zen must be installed on a replacement device.

## Using the Keybindings tab

The list comes from `hyprctl -j binds`, including mouse bindings, submaps and
flags. Search by key or action; **Added here** shows only shortcuts made through
this tab. Use Refresh after editing config elsewhere. Many existing bindings are
Lua callbacks: Hyprland exposes their keys/descriptions but not the callback body.
They are shown honestly as Lua actions, and remain in their original config.
Bindings for which this Hyprland build returns neither a key name nor a keycode
are marked **Key not reported**, with their reported modifiers/flags retained.

Choose **Add shortcut**, give it a name and keys such as `SUPER + SHIFT + K`, then:

- **App:** search and choose an installed desktop launcher. Launching by desktop
  ID preserves the application's desktop entry behavior.
- **Command:** enter the command you want Hyprland to run.
- **Script:** choose an executable path, or enter a filename such as
  `open-work.sh` and choose **New script**. New scripts live in
  `~/.config/hypr/custom/scripts/`, are executable, and never overwrite a file.
  New/Edit opens a text editor explicitly, rather than executing the script.

Saving validates the key and generated Lua, checks occupied shortcuts, backs up
the previous managed file privately, reloads Hyprland with `config-only`, and
checks configuration errors and the resulting binding. Failure restores the
previous file and reloads it. Saving does not launch the app/command/script.
Edit and Remove apply to shortcuts created here. Remove asks for confirmation;
Cancel has initial keyboard focus. It keeps the underlying app/script.

Handwritten shortcuts stay in `~/.config/hypr/custom/keybinds.lua`; **Custom
bindings** opens that file. Keep the managed integration block last when adding
handwritten shortcuts. The generated `settings-shortcuts.lua` is separate
and should be edited through the tab. The helper refuses handwritten changes to
that generated file. Shortcuts are global; the editor does not create submaps or
replace existing shortcuts implicitly. Key names follow XKB/Hyprland naming.

## Reinstall and upstream updates

The canonical package is `Linux/End-4/settings/`. Matching copies live in
`dots-hyprland/dots/.config/hypr/custom/settings/` and the installed
`~/.config/hypr/custom/settings/`. The dotfiles repo's upstream QuickShell source
stays pristine. Its custom `keybinds.lua` includes the load hook and Zen override.

After the upstream dots are installed:

```bash
python3 End-4/settings/customizations.py check
python3 End-4/settings/customizations.py install
hyprctl reload config-only
hyprctl configerrors
```

Close and reopen Super+I if a settings window was already open. There is no need
to restart the desktop shell for this settings-only change.

Before applying an upstream update, check its merged source too:

```bash
python3 End-4/settings/customizations.py check --config-root ~/Desktop/dots-hyprland/dots/.config
```

Run the clipboard/sidebar checks as well; see the main Linux README. Reapply all
three integrations after upstream `./setup install`. The settings installer
preflights supported source and personal assets, snapshots desktop configs under
`~/.local/state/hypr-customization-backups/`, writes dependencies first, and rolls
back partial write failures. Unknown upstream versions or edits stop before any
files are changed. Adapt the integration before retrying; do not force old QML
over new source. Repeated installs are a no-op. It modifies only the three named
AI/translator config values and preserves all other config values.

Use the exact snapshot path printed during installation to restore:

```bash
python3 End-4/settings/customizations.py restore --backup /absolute/path/to/snapshot
hyprctl reload config-only
hyprctl configerrors
```

Restore also backs up the state it replaces. It restores configs, not packages,
Git history or personal app data. Snapshots may contain private settings: never
commit or upload them.

## Keeping shortcuts when moving machines

Keep the whole custom folder, including `settings-shortcuts.lua`, your handwritten
`keybinds.lua` and scripts. The managed file is created only when you add your
first shortcut. Per-edit backups are private under
`~/.local/state/hypr-keybinding-backups/`. Future UI edits stay local until you
deliberately copy them into a rebuild backup; they are not automatically committed
to either repository. Review commands for credentials before sharing them.
Reinstall applications and adjust machine-specific script paths on the new host.

Requirements: the installed Lua-capable Hyprland, QuickShell, Python 3, PyGObject
Gio, `luac`, libxkbcommon and `gtk-launch`. Script editing uses Code/Codium or a
supported desktop text editor, with Kitty+nvim as fallback. No new service or
network account is required.

## Verification

```bash
python3 -m unittest discover -s End-4/settings -p 'test_*.py'
python3 End-4/settings/customizations.py check
```

Tests cover conflict rejection, Lua escaping, create/edit/delete, rollback,
private backups, preservation of handwritten files and unrelated settings,
script path/executable checks, installer idempotency, unknown upstream rejection,
partial-write rollback and restore. Native QML checks run separately against an
isolated config and fake reload command, keeping personal bindings untouched.
