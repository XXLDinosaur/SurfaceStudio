import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid


@unittest.skipUnless(os.name == 'nt', 'Windows desktop ownership')
class SingleInstanceTests(unittest.TestCase):
    def test_concurrent_launches_wake_existing_owner_and_release(self):
        from single_instance import DesktopInstance
        name = 'Local\\SS-Test-' + uuid.uuid4().hex
        first = DesktopInstance(name)
        try:
            self.assertTrue(first.primary)
            code = 'from single_instance import DesktopInstance;import sys;i=DesktopInstance(sys.argv[1]);assert not i.primary;i.activate();i.close()'
            children = [subprocess.Popen([sys.executable, '-c', code, name], cwd=Path(__file__).parent) for _ in range(8)]
            self.assertTrue(all(p.wait(timeout=10) == 0 for p in children))
            self.assertTrue(first.wait(1000))
        finally:
            first.close()
        next_instance = DesktopInstance(name)
        try:
            self.assertTrue(next_instance.primary)
        finally:
            next_instance.close()

    def test_crashed_owner_does_not_leave_stale_lock(self):
        from single_instance import DesktopInstance
        name = 'Local\\SS-Test-' + uuid.uuid4().hex
        code = 'from single_instance import DesktopInstance;import sys,time;i=DesktopInstance(sys.argv[1]);print(i.primary,flush=True);time.sleep(60)'
        child = subprocess.Popen([sys.executable, '-u', '-c', code, name], cwd=Path(__file__).parent, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'True')
        finally:
            child.kill()
            child.wait(timeout=10)
            child.stdout.close()
        next_instance = DesktopInstance(name)
        try:
            self.assertTrue(next_instance.primary)
        finally:
            next_instance.close()


if __name__ == '__main__': unittest.main()
