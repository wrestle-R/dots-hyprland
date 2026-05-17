#!/usr/bin/env bash

choice=$(printf "No\nYes" | wofi --dmenu \
  --prompt "" \
  --width 260 \
  --height 80 \
  --lines 1 \
  --columns 2 \
  --hide-scroll \
  --location center \
  --style "$HOME/.config/wofi/confirm.css")

if [ "$choice" = "Yes" ]; then
  hyprctl dispatch 'hl.dsp.window.close()'
fi
