"""Isolated tests; never writes to the real Blender profile."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import installer_core as core


class InstallerTests(unittest.TestCase):
    def test_application_upgrade_preserves_data_and_backs_up_exe(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(core, 'processes', return_value=[]):
            root = Path(temp); payload = root/'payload'; dest = root/'SS 中文'
            payload.mkdir(); (dest/'data').mkdir(parents=True)
            (payload/'Surface Studio.exe').write_bytes(b'new')
            (dest/'Surface Studio.exe').write_bytes(b'old')
            (dest/'data/state.json').write_bytes(b'keep my favorites')
            core.install_application(payload, dest)
            self.assertEqual((dest/'Surface Studio.exe').read_bytes(), b'new')
            self.assertEqual((dest/'data/state.json').read_bytes(), b'keep my favorites')
            self.assertEqual(next((dest/'data/installer-backups').rglob('*.exe')).read_bytes(), b'old')

    def test_running_application_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); exe = root/'Surface Studio.exe'; exe.write_bytes(b'old')
            with patch.object(core, 'processes', return_value=[{'ExecutablePath': str(exe), 'Name': exe.name}]):
                with self.assertRaisesRegex(RuntimeError, '仍在运行'): core.install_application(root, root)
            self.assertEqual(exe.read_bytes(), b'old')

    def test_running_blender_does_not_touch_preferences(self):
        with patch.object(core, 'processes', return_value=[{'Name': 'blender.exe'}]), patch.object(core, 'probe') as probe:
            with self.assertRaisesRegex(RuntimeError, '关闭所有 Blender'):
                core.install_blender({}, '', '', '', '')
            probe.assert_not_called()

    def test_failed_install_restores_addon_and_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); scripts = root/'scripts'; config = root/'config'
            addon = scripts/'addons'/core.MODULE; addon.mkdir(parents=True); config.mkdir()
            (addon/'__init__.py').write_bytes(b'original addon')
            (config/'userpref.blend').write_bytes(b'original prefs')
            info = {'path': 'blender.exe', 'supported': True, 'scripts': str(scripts), 'config': str(config)}
            def fail(*args, **kwargs):
                (addon/'__init__.py').write_bytes(b'broken addon')
                (config/'userpref.blend').write_bytes(b'broken prefs')
                (config/'userpref.blend1').write_bytes(b'new backup')
                raise RuntimeError('simulate a failed Blender process')
            with patch.object(core, 'probe', return_value=info), patch.object(core, 'worker', side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, 'simulate'):
                    core.install_blender(info, root/'SS.exe', root/'addon.zip', '', root/'backup', check_running=False)
            self.assertEqual((addon/'__init__.py').read_bytes(), b'original addon')
            self.assertEqual((config/'userpref.blend').read_bytes(), b'original prefs')
            self.assertFalse((config/'userpref.blend1').exists())

    def test_unsupported_version_rejected_before_backup(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(core, 'probe', return_value={'supported': False, 'reason': 'unsupported'}):
            with self.assertRaisesRegex(RuntimeError, 'unsupported'):
                core.install_blender({'path': 'blender.exe'}, '', '', '', Path(temp)/'backup', check_running=False)
            self.assertFalse((Path(temp)/'backup').exists())


if __name__ == '__main__': unittest.main()
