import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
import installer_sketchup as su


class SketchUpSetupTest(unittest.TestCase):
    def test_detection_and_version_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entries = [('SketchUp '+year, root/year) for year in ('2025','2026','2024')]
            for _, location in entries:
                location.mkdir()
            (root/'2025/SketchUp.exe').touch()
            self.assertEqual([i['version_string'] for i in su.discover(entries)], ['2025'])
            (root/'2026/SketchUp.exe').touch()
            (root/'2024/SketchUp.exe').touch()
            items = su.discover(entries)
            self.assertEqual([i['version_string'] for i in items], ['2025','2026'])
            archive = root/'bridge.rbz'
            with ZipFile(archive, 'w') as zipped:
                for name in su.MEMBERS:
                    zipped.write(Path('sketchup_addon')/name,name)
            prefs = root/'profile'
            su.install(items[1], archive, root/'backups', prefs)
            self.assertFalse((prefs/'SketchUp/SketchUp 2025').exists())
            installed = prefs/'SketchUp/SketchUp 2026/SketchUp/Plugins'
            for name in su.MEMBERS:
                self.assertEqual((installed/name).read_bytes(), (Path('sketchup_addon')/name).read_bytes())
            (installed/su.MEMBERS[0]).write_text('previous')
            su.install(items[1], archive, root/'backups', prefs)
            self.assertTrue(any(p.read_text()=='previous' for p in (root/'backups').rglob(su.MEMBERS[0])))
