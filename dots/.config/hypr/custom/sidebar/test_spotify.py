import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("spotify_sidebar", HERE / "spotify-sidebar.py")
player = importlib.util.module_from_spec(spec)
spec.loader.exec_module(player)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "player.sock"

    def server(self, reply):
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(str(self.path))
        listener.listen(1)

        def run():
            with listener:
                connection, _ = listener.accept()
                with connection:
                    request = json.loads(connection.makefile("rb").readline())
                    reply(connection, request)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)

    def test_state_whitelists_metadata_and_reports_actual_pause(self):
        def reply(connection, request):
            self.assertEqual(request["method"], "state")
            self.assertIsNone(request["params"])
            result = dict(status="paused", connected=True, logged_in=True, title="A\x1b tune",
                          artist="Example", position_ms=1200, duration_ms=180000, volume=70,
                          private_field="must never leave adapter")
            connection.sendall((json.dumps(dict(version=1, id=request["id"], result=result)) + "\n").encode())
        self.server(reply)
        result = player.state(self.path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["title"], "A tune")
        self.assertNotIn("private_field", result)

    def test_toggle_is_a_single_provider_confirmed_command(self):
        def reply(connection, request):
            self.assertEqual(request["method"], "toggle_pause")
            self.assertIsNone(request["params"])
            connection.sendall((json.dumps(dict(version=1, id=request["id"], result={})) + "\n").encode())
        self.server(reply)
        player.request("toggle_pause", path=self.path)

    def test_mismatched_response_is_rejected(self):
        self.server(lambda conn, req: conn.sendall(b'{"version":1,"id":"wrong","result":{}}\n'))
        with self.assertRaises(player.PlayerError):
            player.request("state", path=self.path)

    def test_stalled_server_times_out(self):
        self.server(lambda conn, req: time.sleep(0.15))
        with self.assertRaises(player.PlayerError):
            player.request("state", path=self.path, timeout=0.04)

    def test_provider_errors_are_not_exported(self):
        def reply(conn, req):
            conn.sendall((json.dumps(dict(version=1, id=req["id"], error="private provider diagnostics")) + "\n").encode())
        self.server(reply)
        result = player.state(self.path)
        self.assertFalse(result["ok"])
        self.assertNotIn("private", result["message"])

    def test_missing_socket_never_starts_player(self):
        with patch.object(player.subprocess, "Popen") as launch:
            self.assertFalse(player.state(self.path)["ok"])
            launch.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_non_socket_and_oversized_messages_rejected(self):
        self.path.write_text("not a socket")
        with self.assertRaises(player.PlayerError):
            player.request("state", path=self.path)
        self.path.unlink()
        def reply(conn, req):
            try:
                conn.sendall(b"x" * (player.LIMIT + 1))
            except BrokenPipeError:
                pass
        self.server(reply)
        with self.assertRaises(player.PlayerError):
            player.request("state", path=self.path)

    def test_launcher_focuses_existing_window_without_spawning(self):
        with patch.object(player, "runtime_dir", return_value=Path(self.temp.name)), \
             patch.object(player, "executable", return_value="/installed/spotify-tui"), \
             patch.object(player.shutil, "which", return_value="/usr/bin/hyprctl"), \
             patch.object(player.subprocess, "check_output", side_effect=[b'[{"class":"spotify-tui","address":"0xabc"}]', "ok\n"]) as focus, \
             patch.object(player.subprocess, "Popen") as launch:
            player.open_player()
            self.assertEqual(focus.call_args.args[0][-1], 'hl.dsp.focus({window="address:0xabc"})')
            launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
