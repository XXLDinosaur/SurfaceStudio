"""Host-side drag manifest tests with temporary data only."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from blender_bridge import BlenderBridge


class DragManifestTests(unittest.TestCase):
    def test_drag_is_independent_of_selected_session(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge = BlenderBridge(directory)
            drop = bridge.prepare_drop({'id': 'fixture', 'maps': []}, {'repeat': 2})
            data = json.loads(Path(drop['path']).read_text())
            self.assertEqual(data['app'], 'SurfaceStudio')
            self.assertEqual(data['id'], drop['id'])
            self.assertEqual(data['options']['repeat'], 2)
            self.assertEqual(Path(drop['path']).suffix, '.ssmat')
            self.assertEqual(bridge.result(drop['id'])['status'], 'pending')
            self.assertGreater(data['expires'], time.time()+290)

    def test_bad_options_do_not_create_files(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge = BlenderBridge(directory)
            for value in [-1, float('nan'), float('inf'), 1000]:
                with self.assertRaises(ValueError): bridge.prepare_drop({}, {'repeat': value})
            self.assertEqual(list((Path(directory)/'drops').iterdir()), [])

    def test_only_old_generated_drop_files_are_cleaned(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            bridge = BlenderBridge(directory)
            old = Path(bridge.prepare_drop({}, {})['path'])
            os.utime(old, (time.time()-90000, time.time()-90000))
            keep = Path(directory)/'drops/personal.ssmat'; keep.write_text('keep')
            bridge.prepare_drop({}, {})
            self.assertFalse(old.exists()); self.assertTrue(keep.exists())


if __name__ == '__main__': unittest.main()
