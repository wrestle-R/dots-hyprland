

-- Internet Swap autostart (managed integration)
hl.on("hyprland.start", function ()
    hl.exec_cmd('"$HOME/.config/hypr/custom/scripts/internet-swap-start.sh"')
end)
