#!/usr/bin/env python3
"""Disposable native theme/auth checks; never contacts the real authentication backend."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys
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
        source=root/"sample with spaces.ppm"
        source.write_bytes(b"P6\n64 48\n255\n"+bytes([65,90,118])*64*48)
        images=installer.blurred_wallpapers(source)
        assert set(images)=={"wallpaper-blurred.jpg","wallpaper-intro.jpg"}
        assert images==installer.blurred_wallpapers(source), "Blur output must be reproducible"
        with patch.object(installer,"blurred_wallpapers",side_effect=RuntimeError("injected conversion failure")),patch.object(installer,"transact") as transaction,patch.object(installer,"write") as write:
            try:
                installer.install(source)
                raise AssertionError("Installation accepted failed asset preparation")
            except RuntimeError as exc:
                assert "injected conversion failure" in str(exc)
            transaction.assert_not_called()
            write.assert_not_called()
        theme=root/"theme";theme.mkdir()
        for name in ("Main.qml","theme.conf","metadata.desktop"):
            shutil.copy2(HERE/"sddm"/name,theme/name)
        for name,data in images.items():
            (theme/name).write_bytes(data)
        complete={p.name:p.read_bytes() for p in theme.iterdir()}
        installer.validate_theme(complete)
        try:
            installer.validate_theme(dict(complete,**{"Main.qml":b"import QtQuick\nRectangle { broken syntax; }\n"}))
            raise AssertionError("Preflight accepted invalid QML")
        except RuntimeError as exc:
            assert "preflight" in str(exc)
        (root/"shell.qml").write_text((HERE/"sddm-test.qml.fixture").read_text())
        env=dict(os.environ,QT_FORCE_STDERR_LOGGING="1",QT_LOGGING_TO_CONSOLE="1")
        subprocess.run(["qmllint",str(theme/"Main.qml")],check=True,capture_output=True)
        # Use SDDM's real engine with the software renderer and no login socket.
        for missing in (False,True):
            if missing:
                for name in images:
                    (theme/name).unlink()
            with (root/"greeter.log").open("w+") as log:
                process=subprocess.Popen(["sddm-greeter-qt6","--test-mode","--theme",str(theme)],env=dict(env,QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software"),stdout=log,stderr=subprocess.STDOUT)
                try:
                    time.sleep(2)
                    assert process.poll() is None,"Greeter exited during loading"
                finally:
                    process.terminate()
                    process.wait(timeout=5)
                log.seek(0);text=log.read()
                assert "Adding view" in text,text
                for error in ("Unexpected token","ReferenceError","TypeError","is not a type","Cannot assign","is not installed"):
                    assert error not in text,text
            if missing:
                for name,data in images.items():
                    (theme/name).write_bytes(data)
        with (root/"native.log").open("w+") as log:
            process=subprocess.Popen(["qs","-p",str(root/"shell.qml"),"--no-color"],env=env,stdout=log,stderr=subprocess.STDOUT)
            def call(name):
                return subprocess.check_output(["qs","-p",str(root/"shell.qml"),"ipc","call","themeTest",name],text=True,stderr=subprocess.STDOUT,timeout=3).strip()
            def state():
                return json.loads(call("status"))
            try:
                deadline=time.monotonic()+10
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
                # Frame-gated motion eventually settles, with no repeating animation.
                deadline=time.monotonic()+5
                while True:
                    s=state()
                    if s["intro"]==0 and s["form"]==1 and s["halo"]==1:
                        break
                    assert time.monotonic()<deadline,s
                    time.sleep(.1)
                assert s["entryQueued"]
            finally:
                if process.poll() is None:
                    try:call("close")
                    except subprocess.SubprocessError:process.terminate()
                process.wait(timeout=5)
            log.seek(0);text=log.read()
            for error in ("ReferenceError","TypeError","ERROR:","Cannot assign"):
                assert error not in text,text
    print("PASS: deterministic offline blur assets; asset-failure no-write guard; real SDDM software/missing-image load; native validation/auth/duplicate/failure/success states; bounded entry motion.")

if __name__=="__main__":
    main()
