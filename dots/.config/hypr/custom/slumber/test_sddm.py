#!/usr/bin/env python3
"""Disposable native theme/auth checks; never contacts the real authentication backend."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import time
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("system_installer",HERE/"install-system.py")
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

def main():
    with tempfile.TemporaryDirectory(prefix="rdp-sddm-test-") as temp:
        root=Path(temp)
        wallpaper = root / "sample with spaces.ppm"
        wallpaper.write_bytes(b"P6\n64 48\n255\n" + bytes([65, 90, 118]) * 64 * 48)
        with patch.object(installer, "validate_theme", side_effect=RuntimeError("injected preflight failure")), \
             patch.object(installer, "INDEX", root / "installed.json"), \
             patch.object(installer, "THEME_ROOT", root / "installed-theme"), \
             patch.object(installer, "transact") as transaction, \
             patch.object(installer, "write") as write:
            # Empty Linux fixture paths guarantee preflight runs without examining system files.
            with patch.object(installer, "Path", lambda path: root / path.lstrip("/")):
                try:
                    installer.install(wallpaper)
                    raise AssertionError("Installation accepted failed preflight")
                except RuntimeError as exc:
                    assert "injected preflight failure" in str(exc)
            transaction.assert_not_called()
            write.assert_not_called()
        theme = root / "theme"
        theme.mkdir()
        for name in ("Main.qml", "theme.conf", "metadata.desktop"):
            shutil.copy2(HERE / "sddm" / name, theme / name)
        (theme / "wallpaper.jpg").write_bytes(wallpaper.read_bytes())
        complete={p.name:p.read_bytes() for p in theme.iterdir()}
        installer.validate_theme(complete)
        try:
            installer.validate_theme(dict(complete,**{"Main.qml":b"import QtQuick\nRectangle { broken syntax; }\n"}))
            raise AssertionError("Preflight accepted invalid QML")
        except RuntimeError as exc:
            assert "preflight" in str(exc)
        (root/"shell.qml").write_text((HERE/"sddm-test.qml.fixture").read_text())
        env=dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
                 QT_FORCE_STDERR_LOGGING="1", QT_LOGGING_TO_CONSOLE="1")
        subprocess.run(["qmllint",str(theme/"Main.qml")],check=True,capture_output=True)
        (theme / "wallpaper.jpg").unlink()
        installer.validate_theme({p.name:p.read_bytes() for p in theme.iterdir()})
        if os.environ.get("SDDM_CAPTURE_WALLPAPER"):
            shutil.copyfile(os.environ["SDDM_CAPTURE_WALLPAPER"], theme/"wallpaper.jpg")
        with (root/"native.log").open("w+") as log:
            process=subprocess.Popen(["qs","-p",str(root/"shell.qml"),"--no-color"],env=env,stdout=log,stderr=subprocess.STDOUT)
            def call(name, *args):
                return subprocess.check_output(["qs","-p",str(root/"shell.qml"),"ipc","call","themeTest",name,*map(str,args)],text=True,stderr=subprocess.STDOUT,timeout=10).strip()
            def state():
                return json.loads(call("status"))
            try:
                deadline=time.monotonic()+25
                while True:
                    try:
                        initial=state()
                        break
                    except (ValueError,subprocess.SubprocessError):
                        if process.poll() is not None or time.monotonic()>deadline:
                            log.seek(0);raise AssertionError(log.read())
                        time.sleep(.1)
                call("emptyUser");call("submit")
                assert state()["requests"]==0 and state()["notice"]=="Enter your username."
                call("credentials");call("noSession");call("submit")
                assert state()["requests"]==0 and state()["notice"]=="No session available."
                call("selectSession");call("submit")
                assert state()["requests"]==1 and state()["submitting"]
                call("submit")
                assert state()["requests"]==1
                call("info")
                assert state()["submitting"] and state()["notice"]=="<b>literal message</b>"
                call("fail");s=state()
                assert s["failed"] and not s["submitting"] and s["passwordEmpty"] and s["passwordFocused"] and s["masked"]
                call("credentials");call("submit");call("success")
                assert state()["requests"]==2 and state()["passwordEmpty"] and state()["masked"]
                assert call("passwordOnly") == "true", "SDDM still offers fingerprint sign-in"
                layout = json.loads(call("layout"))
                assert layout["powerFits"], layout
                for width, height in ((1920, 1200), (1366, 768), (1024, 768)):
                    call("resize", width, height)
                    time.sleep(.1)
                    bounds = json.loads(call("layout"))
                    assert bounds["powerFits"] and bounds["powerBottom"] <= height and bounds["powerRight"] <= width, bounds
                    if os.environ.get("SDDM_CAPTURE_DIR"):
                        call("capture", str(Path(os.environ["SDDM_CAPTURE_DIR"]) / f"login-{width}x{height}.png"))
                        time.sleep(.4)
                for dimension in ("insets", "widths", "heights", "gaps"):
                    values = layout[dimension]
                    assert values[0] > 0 and len(set(values)) == 1, layout
            finally:
                if process.poll() is None:
                    try:call("close")
                    except subprocess.SubprocessError:process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                    raise
            log.seek(0);text=log.read()
            for error in ("ReferenceError","TypeError","ERROR:","Cannot assign"):
                assert error not in text,text
    print("PASS: preflight prevents system writes; real Qt6 SDDM with and without wallpaper; native authentication states; aligned form rows.")

if __name__=="__main__":
    main()
