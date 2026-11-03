#!/bin/sh
# Hyprland starts the user service; the daemon also enforces a single instance.
if systemctl --user cat internet-swap.service >/dev/null 2>&1; then
    exec systemctl --user start internet-swap.service
fi
# Compatibility with a manually installed AppImage.
if [ -x "$HOME/.local/bin/internet-swap.AppImage" ]; then
    exec "$HOME/.local/bin/internet-swap.AppImage" --daemon
fi
