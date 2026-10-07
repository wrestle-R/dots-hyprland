hl.bind("CTRL+SUPER+ALT+Slash", hl.dsp.exec_cmd("xdg-open ~/.config/hypr/custom/keybinds.lua"), {description = "Edit user keybinds"})

hl.unbind("SUPER + B")
hl.bind("SUPER + B", hl.dsp.exec_cmd("brave-origin-nightly"), {description = "Brave Nightly"})

hl.bind("mouse:275", hl.dsp.focus({workspace = "e-1"}))
hl.bind("mouse:276", hl.dsp.focus({workspace = "e+1"}))

hl.unbind("SUPER + T")
hl.bind("SUPER + T", hl.dsp.exec_cmd("gtk-launch tlauncher"), {description = "TLauncher"})

hl.unbind("SUPER + Space")
hl.bind("SUPER + Space", hl.dsp.exec_cmd("$HOME/.local/bin/multi-codex.AppImage"), {description = "Multi Codex"})

hl.bind("mouse:274", hl.dsp.exec_cmd("ydotool key 29:1 15:1 15:0 && sleep 0.3 && ydotool key 29:0"), {mouse = true})

hl.unbind("SUPER + Q")
hl.bind("SUPER + Q", function()
    local window = hl.get_active_window()
    if not window then return end
    hl.dispatch(hl.dsp.exec_cmd(string.format(
        '"$HOME/.config/hypr/custom/scripts/confirm-close.sh" %s %d %d',
        window.address, window.pid, window.stable_id
    )))
end, {description = "Confirm before closing"})

hl.unbind("SUPER + SHIFT + Q")
hl.bind("SUPER + SHIFT + Q", hl.dsp.exec_cmd('"$HOME/.config/hypr/custom/scripts/restore-closed.sh"'), {description = "Reopen last closed app"})

hl.bind("ALT + F4", function() end, {non_consuming = false})

hl.unbind("SUPER + C")
hl.bind("SUPER + C", hl.dsp.exec_cmd("code"), {description = "VS Code"})

hl.unbind("SUPER + S")
hl.bind("SUPER + S", hl.dsp.exec_cmd("flatpak run com.stremio.Stremio"), {description = "Stremio"})

hl.bind("SUPER + A", function() end)
hl.bind("SUPER + O", function() end)
hl.bind("SUPER + mouse:275", function() end)
hl.bind("SUPER + mouse_up", function() end)
hl.bind("SUPER + mouse_down", function() end)
hl.bind("SUPER + H", hl.dsp.exec_cmd("~/.local/bin/hyprtrack-desktop.AppImage"))

hl.unbind("SUPER + R")
hl.bind("SUPER + R", hl.dsp.exec_cmd("env -u ELECTRON_RUN_AS_NODE recordly --ozone-platform=x11"), {description = "Recordly"})
