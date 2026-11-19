#!/usr/bin/python3
"""Enable or disable optional SDDM and sudo fingerprint authentication on Arch."""

import argparse
import fcntl
import os
from pathlib import Path
import re
import subprocess

from customizations import transact, write

SDDM = Path("/etc/pam.d/sddm")
VISUDO = "/usr/bin/visudo"
POLICY = Path("/etc/sudoers.d/90-rdp-fingerprint")
HELPER = Path("/usr/local/libexec/sddm-empty-password")
SERVICE = Path("/etc/pam.d/sudo-fingerprint")
THEME = Path("/usr/share/sddm/themes/rdp-slumber")
OVERRIDE = THEME / "theme.conf.user"
LOCK = Path("/run/rdp-fingerprint-auth.lock")

START = b"# rdp fingerprint: begin\n"
END = b"# rdp fingerprint: end\n"
BLOCK = START + b"""# A nonempty or unavailable password selector keeps the normal password path.
auth [success=ignore default=4] pam_exec.so expose_authtok quiet quiet_log /usr/local/libexec/sddm-empty-password
auth requisite pam_shells.so
auth requisite pam_nologin.so
auth requisite pam_faillock.so preauth
auth [success=done default=die] pam_fprintd.so max-tries=1 timeout=8
""" + END
SUDO = b"""#%PAM-1.0
auth requisite pam_faillock.so preauth
auth [success=done default=ignore] pam_fprintd.so max-tries=1 timeout=2
auth include sudo
account include sudo
session include sudo
"""
PREVIOUS_SUDO = SUDO.replace(b"timeout=2", b"timeout=5")
SELECTOR = b"""#!/usr/bin/bash -p
# A nonempty response follows the original SDDM PAM configuration.
IFS= read -r -N 1 password_byte && exit 1
exit 0
"""
THEME_OPT_IN = b"[General]\nFingerprintEnabled=true\n"


def checked_bytes(path):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise RuntimeError(f"Refusing symlink: {path}")
    return path.read_bytes() if path.exists() else None


def plan(username, enabled):
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*", username):
        raise ValueError("Use a local Linux account name")
    policy = (
        "# Separate password-only PAM paths for sudo -i and graphical askpass.\n"
        f"Defaults:{username} pam_service=sudo-fingerprint, "
        "pam_login_service=sudo, pam_askpass_service=sudo\n"
    ).encode()
    raw = checked_bytes(SDDM)
    if raw is None:
        raise RuntimeError(f"Missing SDDM PAM policy: {SDDM}")
    if raw.count(START) != raw.count(BLOCK) or raw.count(END) != raw.count(BLOCK) or raw.count(BLOCK) > 1:
        raise RuntimeError("The SDDM fingerprint block has local edits")
    if enabled and BLOCK not in raw:
        matches = list(re.finditer(rb"^auth[\t ]+include[\t ]+system-login[\t ]*$", raw, re.M))
        if len(matches) != 1 or re.search(rb"^auth[\t ]", raw[:matches[0].start()], re.M):
            raise RuntimeError("SDDM PAM differs from the Arch package configuration")
        start = matches[0].start()
        sddm = raw[:start] + BLOCK + raw[start:]
    else:
        sddm = raw if enabled else raw.replace(BLOCK, b"")
    changes = {}
    for path, managed, mode in ((HELPER, SELECTOR, 0o755), (SERVICE, SUDO, 0o644),
                                (OVERRIDE, THEME_OPT_IN, 0o644), (POLICY, policy, 0o440)):
        old = checked_bytes(path)
        previous = PREVIOUS_SUDO if path == SERVICE else None
        if old not in (None, managed, previous):
            raise RuntimeError(f"Refusing to overwrite a local customization: {path}")
        changes[path] = (path, old, managed if enabled else None, mode)
    changes[SDDM] = (SDDM, raw, sddm, 0o644)
    # Publish PAM before the UI and policy. Reverse the order on removal.
    order = [HELPER, SERVICE, SDDM, OVERRIDE, POLICY]
    if not enabled:
        order.reverse()
    return [changes[path] for path in order if changes[path][1] != changes[path][2]]


def apply(changes):
    applied = []
    original_modes = {}
    try:
        for path, old, new, mode in changes:
            if checked_bytes(path) != old:
                raise RuntimeError(f"File changed during setup: {path}")
            if old is not None:
                original_modes[path] = path.stat().st_mode & 0o777
            if new is None:
                path.unlink()
            else:
                write(path, new, mode)
            applied.append((path, new, old))
        subprocess.run([VISUDO, "-c"], check=True)
    except BaseException:
        transact(list(reversed(applied)))
        # transact preserves existing modes. Restore modes of recreated files.
        for path, _, old in applied:
            if old is not None:
                path.chmod(original_modes[path])
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("enable", "disable"))
    parser.add_argument("username")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run this through sudo")
    if args.action == "enable":
        if not Path("/usr/lib/security/pam_fprintd.so").is_file():
            parser.error("Install fprintd first")
        theme = checked_bytes(THEME / "Main.qml")
        if not theme or b'boolValue("FingerprintEnabled")' not in theme:
            parser.error("Install the fingerprint-aware Slumber SDDM theme first")
    with LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        subprocess.run([VISUDO, "-c"], check=True)
        apply(plan(args.username, args.action == "enable"))
    print(f"Fingerprint authentication set to {args.action} for SDDM and sudo.")


if __name__ == "__main__":
    main()
