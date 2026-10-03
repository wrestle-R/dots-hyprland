#!/usr/bin/env bash
set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_dir/window-close.py" restore
