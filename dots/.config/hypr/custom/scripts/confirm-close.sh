#!/usr/bin/env bash

choice=$(printf "No\nYes" | wofi --dmenu \
  --prompt "Close window?" \
  --width 300 --height 120 \
  --lines 1 --columns 2 \
  --location center \
  --style "$HOME/.config/wofi/confirm.css")

if [ "$choice" = "Yes" ]; then
  target_addr="$(hyprctl -j activewindow | jq -r '.address // empty')"
  if [ -n "$target_addr" ] && [ "$target_addr" != "null" ]; then
    hyprctl dispatch closewindow "address:$target_addr"
  fi
fi
