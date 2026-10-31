import json,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
import server as app
class ScanConsistencyTests(unittest.TestCase):
 def test_changed_configuration_discards_old_scan_and_rescans(self):
  saved={key:getattr(app,key) for key in ('DATA','CACHE','CONFIG','INDEX','ASSETS','SCANNING','SCAN_ERROR')}
  try:
   with tempfile.TemporaryDirectory() as directory:
    root=Path(directory);old=root/'old';new=root/'new';data=root/'data'
    for p in (old,new,data):p.mkdir()
    app.DATA=data;app.CACHE=data;app.CONFIG={'root':str(old),'normalRoot':str(root/'normal')};app.INDEX={'root':'before','assets':[]};app.ASSETS={};app.SCANNING=False
    entered=threading.Event();release=threading.Event()
    def normals(*args):entered.set();assert release.wait(5);return []
    with patch.object(app,'scan_normals',side_effect=normals):
     worker=threading.Thread(target=app.scan);worker.start();self.assertTrue(entered.wait(5))
     with app.LOCK:app.CONFIG={'root':str(new),'normalRoot':str(root/'normal')}
     self.assertEqual(app.INDEX['root'],'before');release.set();worker.join(5)
     deadline=time.monotonic()+5
     while (app.SCANNING or app.INDEX['root']!=str(new)) and time.monotonic()<deadline:time.sleep(.01)
     self.assertFalse(app.SCANNING);self.assertEqual(app.INDEX['root'],str(new))
     self.assertEqual(json.loads((data/'index.json').read_text(encoding='utf-8'))['root'],str(new))
  finally:
   for key,value in saved.items():setattr(app,key,value)
if __name__=='__main__':unittest.main()

