import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


editor = load('shortcut_editor', 'keybindings.py')
installer = load('settings_installer', 'customizations.py')


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.root / 'config'), 'XDG_STATE_HOME': str(self.root / 'state')})
        env.start()
        self.addCleanup(env.stop)
        self.custom = self.root / 'config/hypr/custom'
        self.custom.mkdir(parents=True)
        (self.custom / 'keybinds.lua').write_text(editor.HOOK)
        self.live = []
        self.fail_reload = False
        self.launches = []

        def fake_run(*args):
            self.assertEqual(args[0], 'hyprctl')
            if args[1] == 'configerrors':
                return ''
            if args[1] == 'reload':
                if self.fail_reload:
                    self.fail_reload = False
                    raise ValueError('simulated reload failure')
                entries, _ = editor.read_entries()
                self.live = [{'key': e['chord'].split(' + ')[-1], 'modmask': editor.normalize(e['chord'])[1], 'description': editor.LABEL + e['name'], 'submap': ''} for e in entries]
                return 'ok'
            raise AssertionError(args)

        self.patches = [patch.object(editor, 'run', side_effect=fake_run), patch.object(editor, 'active_binds', side_effect=lambda: self.live)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.request = {'chord': 'SUPER + SHIFT + K', 'name': 'Work', 'kind': 'command', 'target': 'kitty --directory ~/Desktop/code'}

    def test_save_edit_delete_and_private_backup_without_launching_command(self):
        result = editor.change('save', self.request)
        entries, original = editor.read_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(Path(result['backup']).stat().st_mode & 0o777, 0o600)
        edited = {**self.request, 'id': entries[0]['id'], 'chord': 'SUPER + SHIFT + J', 'name': 'Updated'}
        editor.change('save', edited)
        self.assertEqual(len(self.live), 1)
        self.assertEqual(self.live[0]['key'], 'J')
        editor.change('delete', {'id': entries[0]['id']})
        self.assertEqual(editor.read_entries()[0], [])
        self.assertEqual(self.live, [])
        self.assertTrue(original)

    def test_existing_conflict_preserves_everything(self):
        self.live = [{'key': 'k', 'modmask': 65, 'description': 'Existing action'}]
        with self.assertRaisesRegex(ValueError, 'already used'):
            editor.change('save', self.request)
        self.assertFalse(editor.shortcut_path().exists())
        self.assertFalse((self.root / 'state').exists())

    def test_reload_failure_rolls_back(self):
        editor.change('save', self.request)
        before = editor.shortcut_path().read_bytes()
        self.fail_reload = True
        with self.assertRaisesRegex(ValueError, 'rolled back'):
            editor.change('save', {**self.request, 'chord': 'SUPER + SHIFT + J'})
        self.assertEqual(editor.shortcut_path().read_bytes(), before)
        self.assertEqual(len(self.live), 1)

    def test_handwritten_generated_file_is_not_overwritten(self):
        editor.shortcut_path().write_text('hl.bind("SUPER + K", function() end)\n')
        with self.assertRaises(ValueError):
            editor.change('save', self.request)
        self.assertTrue(editor.shortcut_path().read_text().startswith('hl.bind'))

    def test_escaping_and_unicode_produce_valid_lua_without_executing(self):
        target = 'printf "hi\\n"; $(touch /nope)\n# café'
        editor.change('save', {**self.request, 'target': target, 'name': 'Café "work"'})
        saved = editor.shortcut_path().read_bytes()
        subprocess.run(['luac', '-p', '-'], input=saved, check=True, capture_output=True)
        self.assertEqual(editor.read_entries()[0][0]['command'], target)

    def test_invalid_keys_and_new_script_traversal_are_rejected(self):
        for key in ['SUPER + not_a_real_key', 'SUPER + CTRL + CTRL + K', 'SUPER + K\nprint(1)', 'SUPER + ']:
            with self.assertRaises(ValueError):
                editor.normalize(key)
        with self.assertRaises(ValueError):
            editor.new_script({'name': '../oops.sh'})
        result = editor.new_script({'name': 'open-work.sh'})
        path = Path(result['path'])
        self.assertEqual(path.stat().st_mode & 0o777, 0o700)
        self.assertTrue(path.read_text().startswith('#!/usr/bin/env bash'))
        with self.assertRaises(FileExistsError):
            editor.new_script({'name': 'open-work.sh'})

    def test_missing_app_and_nonexecutable_script_rejected(self):
        with patch.object(editor, 'apps', return_value=[]):
            with self.assertRaises(ValueError):
                editor.command_for({'kind': 'app', 'target': 'missing.desktop'})
        path = self.root / 'not-executable.sh'
        path.write_text('echo test')
        with self.assertRaises(ValueError):
            editor.command_for({'kind': 'script', 'target': str(path)})


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'config'
        self.backups = Path(self.temp.name) / 'backups'
        self.edits = json.loads((HERE / 'settings-integration.json').read_text())
        for edit in self.edits:
            p = self.root / edit['path']
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(edit['before'])
        self.keybinds = self.root / 'hypr/custom/keybinds.lua'
        self.keybinds.parent.mkdir(parents=True)
        self.keybinds.write_text('-- handwritten shortcut preserved\n')
        self.options = self.root / 'illogical-impulse/config.json'
        self.options.parent.mkdir(parents=True)
        self.options.write_text(json.dumps({'policies': {'ai': 1, 'weeb': 0}, 'unrelated': {'nested': 'preserve me'}}))

    def test_idempotency_config_preservation_and_restore(self):
        original = self.keybinds.read_bytes()
        installer.install(self.root, self.backups)
        self.assertEqual(installer.plan(self.root), [])
        data = json.loads(self.options.read_text())
        self.assertEqual(data['policies']['ai'], 0)
        self.assertEqual(data['unrelated'], {'nested': 'preserve me'})
        self.assertTrue(self.keybinds.read_bytes().startswith(original))
        snapshots = list(self.backups.iterdir())
        installer.install(self.root, self.backups)
        self.assertEqual(list(self.backups.iterdir()), snapshots)
        installer.restore(self.root, self.backups, snapshots[0])
        self.assertEqual(self.keybinds.read_bytes(), original)
        self.assertFalse((self.root / 'quickshell/ii/modules/settings/KeybindingsConfig.qml').exists())

    def test_unknown_upstream_or_personal_asset_stops_before_backup(self):
        path = self.root / self.edits[0]['path']
        path.write_text(path.read_text() + '// upstream change\n')
        with self.assertRaises(installer.CompatibilityError):
            installer.install(self.root, self.backups)
        self.assertFalse(self.backups.exists())

    def test_partial_write_failure_rolls_back(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        write = installer.write_atomic
        calls = 0

        def fail(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise OSError('simulated write failure')
            return write(*args, **kwargs)

        with patch.object(installer, 'write_atomic', side_effect=fail):
            with self.assertRaises(OSError):
                installer.install(self.root, self.backups)
        after = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
