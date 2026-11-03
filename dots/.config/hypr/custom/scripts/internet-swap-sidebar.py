#!/usr/bin/env python3
"""Private local bridge to Internet Swap; never probes or changes Wi-Fi itself."""
import json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

def request(command):
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", str(Path(tempfile.gettempdir()) / ("internet-swap-" + os.environ.get("USER", "")))))
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        client.connect(str(runtime / "internet-swap/socket"))
        client.sendall((command + "\n").encode())
        with client.makefile("rb") as stream:
            result = json.loads(stream.readline(262144))
    if "error" in result:
        raise ValueError(result["error"])
    return result

def main():
    action = sys.argv[1] if len(sys.argv) == 2 else "status"
    if action == "open":
        for name in ("internet-swap.AppImage", "internet-swap"):
            binary = Path.home() / ".local/bin" / name
            if binary.is_file():
                subprocess.Popen([str(binary)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                print(json.dumps({"ok": True}), flush=True)
                return
        raise ValueError("Install Internet Swap to open the window")
    if action not in ("watch", "status", "enable", "disable"):
        raise ValueError("Unknown action")
    while True:
        try:
            result = request("status" if action == "watch" else action)
            result["ok"] = True
        except (OSError, ValueError) as error:
            result = {"ok": False, "message": str(error) if action != "watch" else "Internet Swap is unavailable"}
        print(json.dumps(result), flush=True)
        if action != "watch":
            if not result["ok"]:
                sys.exit(1)
            return
        time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(json.dumps({"ok": False, "message": str(error)}), flush=True)
        sys.exit(1)
