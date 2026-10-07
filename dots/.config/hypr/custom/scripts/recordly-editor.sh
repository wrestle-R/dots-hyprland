#!/usr/bin/env bash
# Open Recordly's full editor without interrupting the recorder instance.
set -euo pipefail

# An existing editor already has its own import button for changing videos.
if python3 - <<'PYFOCUS'
import json
import subprocess
import sys

clients = json.loads(subprocess.check_output(["hyprctl", "clients", "-j"]))
for client in clients:
    if client.get("class") == "recordly" and client.get("title") == "Recordly Editor":
        address = "address:" + client["address"]
        subprocess.run(["hyprctl", "dispatch", "hl.dsp.focus({window = " + json.dumps(address) + "})"], check=True)
        sys.exit(0)
sys.exit(1)
PYFOCUS
then
    exit 0
fi

# Avoid multiple import dialogs when the shortcut is pressed repeatedly.
exec 9>"${XDG_RUNTIME_DIR:?}/recordly-editor-launch.lock"
flock -n 9 || exit 0
video=${1:-}
if [[ -z "$video" ]]; then
    video=$(kdialog --title "Open video in Recordly Editor" --getopenfilename         "$HOME" "*.mp4 *.webm *.mov *.avi *.mkv|Video files") || exit 0
fi
[[ -n "$video" && -f "$video" ]] || exit 1
video=$(realpath -- "$video")

# Recordly 1.4 provides this editor entry point. A separate profile prevents
# its recorder instance from intercepting the launch via the single-app lock.
exec env -u ELECTRON_RUN_AS_NODE RECORDLY_DEV_OPEN_RECORDING_INPUT="$video"     recordly --ozone-platform=x11     --user-data-dir="${XDG_CONFIG_HOME:-$HOME/.config}/Recordly-editor"
