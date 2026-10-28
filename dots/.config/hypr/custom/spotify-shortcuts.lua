-- Personal Spotify launcher. Base/upstream keybindings stay untouched.
local spotifyHelper = (os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")) .. "/hypr/custom/scripts/spotify-sidebar.py"
hl.unbind("SUPER + S")
hl.bind("SUPER + S", hl.dsp.exec_cmd('python3 "' .. spotifyHelper .. '" open'), {description = "Spotify TUI"})
