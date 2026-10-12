"""Windows OLE source event regression: reject drops before the recipient gets data."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

if os.name == 'nt':
    sys.path.insert(0, str(Path(__file__).parent/'.desktop-runtime'))
    import clr
    clr.AddReference('System.Windows.Forms')
    from System import Array, Object
    from System.Reflection import BindingFlags
    from System.Windows.Forms import Form, QueryContinueDragEventArgs, DragAction
    from material_drag import install_drop_guard, blender_under_pointer


@unittest.skipUnless(os.name == 'nt', 'Windows native drag source')
class DropGuardTests(unittest.TestCase):
    def setUp(self):
        self.form = Form()
        self.target = Mock(return_value=False)
        self.guard = install_drop_guard(self.form, self.target)

    def tearDown(self):
        self.form.QueryContinueDrag -= self.guard
        self.form.Dispose()

    def release(self, keys=0, escape=False, action=None):
        event = QueryContinueDragEventArgs(keys, escape, action or DragAction.Drop)
        self.form.GetType().GetMethod('OnQueryContinueDrag', BindingFlags.Instance | BindingFlags.NonPublic).Invoke(self.form, Array[Object]([event]))
        return event.Action

    def test_browser_desktop_and_ss_release_cancel_before_delivery(self):
        for keys in [0, 4, 8, 12]:  # Modifier keys must not turn cancel into copy/link.
            with self.subTest(keys=keys):
                self.assertEqual(self.release(keys), DragAction.Cancel)

    def test_blender_release_preserves_drop(self):
        self.target.return_value = True
        self.assertEqual(self.release(), DragAction.Drop)

    def test_hold_outside_blender_continues_until_release(self):
        self.assertEqual(self.release(keys=1, action=DragAction.Continue), DragAction.Continue)
        self.target.assert_not_called()

    def test_escape_cancels_even_over_blender(self):
        self.target.return_value = True
        self.assertEqual(self.release(escape=True), DragAction.Cancel)

    def test_lookup_failure_cancels(self):
        self.target.side_effect = OSError('Target window vanished')
        self.assertEqual(self.release(), DragAction.Cancel)

    def test_guard_detaches_after_drag(self):
        self.form.QueryContinueDrag -= self.guard
        try:
            self.assertEqual(self.release(), DragAction.Drop)
        finally:
            self.form.QueryContinueDrag += self.guard

    def test_real_pointer_lookup_is_boolean(self):
        self.assertIsInstance(blender_under_pointer(), bool)


if __name__ == '__main__':
    unittest.main()
