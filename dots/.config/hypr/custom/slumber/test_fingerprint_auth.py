"""Exercise the fingerprint setup and password-policy rollback without touching /etc."""

import importlib.util
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fingerprint_auth", HERE / "fingerprint-auth.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def main():
    stock = b"#%PAM-1.0\nauth include system-login\naccount include system-login\n"
    with TemporaryDirectory() as directory:
        root = Path(directory)
        paths = {key: root / key for key in ("SDDM", "HELPER", "SERVICE", "OVERRIDE", "POLICY")}
        with patch.multiple(setup, **paths, VISUDO="/usr/bin/true"):
            setup.SDDM.write_bytes(stock)
            setup.apply(setup.plan("tester", enabled=True))
            assert setup.SDDM.read_bytes().replace(setup.BLOCK, b"") == stock
            assert b"auth include sudo\n" in setup.SERVICE.read_bytes()
            assert b"pam_login_service=sudo" in setup.POLICY.read_bytes()
            assert setup.HELPER.stat().st_mode & 0o777 == 0o755
            assert setup.POLICY.stat().st_mode & 0o777 == 0o440
            assert setup.plan("tester", enabled=True) == []

            with patch.object(setup, "VISUDO", "/usr/bin/false"):
                try:
                    setup.apply(setup.plan("tester", enabled=False))
                except subprocess.CalledProcessError:
                    pass
                else:
                    raise AssertionError("Expected sudoers validation failure")
            assert setup.plan("tester", enabled=True) == []
            assert setup.POLICY.stat().st_mode & 0o777 == 0o440

            setup.apply(setup.plan("tester", enabled=False))
            assert setup.SDDM.read_bytes() == stock
            assert setup.plan("tester", enabled=False) == []
            assert not any(path.exists() for key, path in paths.items() if key != "SDDM")
    print("PASS: fingerprint setup, independent password service, rollback, disable, and repeat")


if __name__ == "__main__":
    main()
