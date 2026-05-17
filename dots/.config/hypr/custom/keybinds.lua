hl.bind("CTRL+SUPER+ALT+Slash", hl.dsp.exec_cmd("xdg-open ~/.config/hypr/custom/keybinds.lua"), {description = "Edit user keybinds"} )

hl.bind("CTRL+SUPER+ALT+Slash", hl.dsp.exec_cmd("xdg-open ~/.config/hypr/custom/keybinds.lua"), {description = "Edit user keybinds"})

hl.unbind("SUPER + B")
hl.bind("SUPER + B", hl.dsp.exec_cmd("brave-origin-nightly"), {description = "Brave Nightly"})

hl.bind("mouse:275", hl.dsp.focus({workspace = "e-1"}))
hl.bind("mouse:276", hl.dsp.focus({workspace = "e+1"}))

hl.unbind("SUPER + X")
hl.bind("SUPER + X", hl.dsp.exec_cmd("env CODEX_HOME=$HOME/.codex-cursor cursor --user-data-dir ~/.cursor-free"), {description = "Cursor (separate profile)"})

hl.bind("mouse:274", hl.dsp.exec_cmd("ydotool key 29:1 15:1 15:0 && sleep 0.3 && ydotool key 29:0"), {mouse = true})

hl.unbind("SUPER + Q")
hl.bind("SUPER + Q", hl.dsp.exec_cmd("$HOME/.config/hypr/custom/scripts/confirm-close.sh"), {description = "Confirm before closing"})

hl.bind("ALT + F4", function() end, {non_consuming = false})

hl.bind("SUPER + C", hl.dsp.exec_cmd("code"), {description = "VS Code"})

hl.bind("SUPER + A", function() end)
hl.bind("SUPER + O", function() end)
hl.bind("SUPER + mouse:275", function() end)
hl.bind("SUPER + mouse_up", function() end)
hl.bind("SUPER + mouse_down", function() end)
