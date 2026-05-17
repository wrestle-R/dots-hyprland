#!/usr/bin/env bash

target_pid="$(hyprctl -j activewindow | jq -r '.pid // empty')"

choice=$(printf "No\nYes" | wofi --dmenu \
  --prompt "Close window?" \
  --width 300 --height 120 \
  --lines 2 --columns 2 \
  --location center \
  --style "$HOME/.config/wofi/confirm.css")

if [ "$choice" = "Yes" ] && [ -n "$target_pid" ] && [ "$target_pid" != "null" ]; then
  kill -TERM "$target_pid" 2>/dev/null || true
fi