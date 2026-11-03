-- Native Super tap: preserve chords and workspace-number indicators.
local qsIpcCall = "qs -c $qsConfig ipc call"
hl.unbind("SUPER + SUPER_L")
hl.unbind("SUPER + SUPER_R")
-- Native release bindings suppress the tap action after another Super shortcut.
local superTapCommand = qsIpcCall .. " search toggle || pkill fuzzel || fuzzel"
hl.bind("SUPER + SUPER_L", hl.dsp.exec_cmd(superTapCommand), { release = true, description = "Shell: Toggle search (Super tap)" })
hl.bind("SUPER + SUPER_R", hl.dsp.exec_cmd(superTapCommand), { release = true })

hl.bind("SUPER_L", hl.dsp.global("quickshell:workspaceNumber"), { ignore_mods = true, transparent = true, non_consuming = true })
hl.bind("SUPER_R", hl.dsp.global("quickshell:workspaceNumber"), { ignore_mods = true, transparent = true, non_consuming = true })
hl.bind("SUPER_L", hl.dsp.global("quickshell:workspaceNumber"),
    { ignore_mods = true, transparent = true, non_consuming = true, release = true })
hl.bind("SUPER_R", hl.dsp.global("quickshell:workspaceNumber"),
    { ignore_mods = true, transparent = true, non_consuming = true, release = true })
