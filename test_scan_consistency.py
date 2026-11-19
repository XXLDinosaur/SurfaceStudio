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
class MaterialScanRegressionTests(unittest.TestCase):
 def setUp(self):
  self.saved={key:getattr(app,key) for key in ('DATA','CACHE','CONFIG','INDEX','ASSETS','SCANNING','SCAN_ERROR')}
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'library';self.root.mkdir()
  data=Path(self.temp.name)/'data';data.mkdir()
  app.DATA=data;app.CACHE=data;app.CONFIG={'root':str(self.root)};app.INDEX={'assets':[]};app.ASSETS={};app.SCANNING=False
  self.warm=patch.object(app,'schedule_hdr_previews');self.warm.start()
 def tearDown(self):
  self.warm.stop()
  for key,value in self.saved.items():setattr(app,key,value)
  self.temp.cleanup()
 def package(self,name,files,categories=('surface','marble')):
  folder=self.root/name;folder.mkdir()
  (folder/'asset.json').write_text(json.dumps({'name':name,'categories':list(categories)}),encoding='utf-8')
  for file in files:(folder/file).write_bytes(b'test texture')
 def test_builtin_review_persists_report_and_runs_for_new_imports(self):
  self.package('Artificial Turf',['test_AO.jpg','test_BaseColor.jpg','test_Normal.jpg'])
  self.package('Lake Plants',['test_BaseColor.jpg','test_Opacity.jpg'],('atlas','ocean'))
  app.scan();self.assertIsNone(app.SCAN_ERROR)
  review=app.INDEX.get('importReview')
  self.assertIsNotNone(review)
  self.assertEqual(review['excludedPlantAtlases'],0)
  self.assertEqual(review['includedPlantAtlases'],1)
  self.assertEqual(review['colorPreviews'],2)
  self.assertEqual(review['checkedFolders'],2)
  self.assertEqual(json.loads((app.DATA/'index.json').read_text(encoding='utf-8'))['importReview'],review)
  self.package('Rubber',['test_BaseColor.jpg','test_Normal.jpg'])
  app.scan();self.assertIsNone(app.SCAN_ERROR)
  library=app.categorized_library()
  self.assertEqual({a['category'] for a in library['assets']},{'Grass','Rubber','Plants'})
  self.assertEqual(library['importReview']['checkedFolders'],3)
  self.assertEqual(library['importReview']['excludedPlantAtlases'],0)
  self.assertEqual(library['importReview']['classified'],3)
  self.assertEqual(library['importReview']['unclassified'],0)
  self.assertFalse(app.import_review.needs_review(app.INDEX))
  self.assertTrue(app.import_review.needs_review({'assets':[]}))
  self.assertTrue(app.import_review.needs_review({'importReview':{'policyVersion':0}}))
  self.assertTrue(app.import_review.needs_review({'importReview':{'policyVersion':1}}))
 def test_review_keeps_every_plant_atlas(self):
  for number in range(23):self.package('Plant Debris '+str(number),['test_BaseColor.jpg'],('atlas','debris'))
  app.scan();self.assertIsNone(app.SCAN_ERROR)
  self.assertEqual(app.INDEX['importReview']['excludedPlantAtlases'],0)
  self.assertEqual(app.INDEX['importReview']['includedPlantAtlases'],23)
  self.assertEqual(len(app.INDEX['assets']),23)
  self.assertEqual(app.INDEX['importReview']['excludedExamples'],[])
 def test_color_channels_win_over_alphabetically_first_ao(self):
  for channel in ('BaseColor','Diffuse','Albedo'):
   self.package(channel,['test_4K_AO.jpg',f'test_4K_{channel}.jpg','test_4K_Normal.jpg'])
  self.package('with-preview',['material_Preview.png','test_AO.jpg','test_BaseColor.jpg'])
  app.scan();self.assertIsNone(app.SCAN_ERROR)
  assets={a['folder']:a for a in app.INDEX['assets']}
  for channel in ('BaseColor','Diffuse','Albedo'):
   self.assertEqual(assets[channel]['preview'],f'test_4K_{channel}.jpg')
   self.assertIn('AO',{m['channel'] for m in assets[channel]['maps']})
  self.assertEqual(assets['with-preview']['preview'],'material_Preview.png')
 def test_preserves_botanical_ground_and_other_atlases(self):
  for category in ('plant','tree','grass','bush','flowers','seaweed'):
   self.package('atlas-'+category,['test_BaseColor.jpg','test_Opacity.jpg'],('atlas',category))
  self.package('grass-ground',['test_BaseColor.jpg','test_Normal.jpg'],('surface','grass'))
  self.package('fallen-leaves',['test_BaseColor.jpg','test_Normal.jpg'],('surface','leaves'))
  self.package('fabric-atlas',['test_BaseColor.jpg','test_Opacity.jpg'],('atlas','fabric'))
  (self.root/'fabric-atlas'/'asset.json').write_text(json.dumps({'name':'Fabric Painting','categories':['atlas','fabric'],'tags':['flower']}),encoding='utf-8')
  app.scan();self.assertIsNone(app.SCAN_ERROR)
  self.assertEqual({a['folder'] for a in app.INDEX['assets']},{'grass-ground','fallen-leaves','fabric-atlas'} | {'atlas-'+c for c in ('plant','tree','grass','bush','flowers','seaweed')})
 def test_keeps_plant_atlases_with_generic_metadata(self):
  for name,categories in [('Dry Plant Debris',('atlas','debris','nature')),
                          ('Lake Plants',('atlas','ocean','debris')),
                          ('Lake Plant Stems',('atlas','ocean')),
                          ('Plant Debris',('atlas','scatter','piles')),
                          ('Unidentified Desert Plant',('atlas','debris'))]:
   self.package(name,['test_BaseColor.jpg','test_Opacity.jpg'],categories)
  self.package('plant_debris_export',['test_BaseColor.jpg','test_Opacity.jpg'],('atlas','debris'))
  (self.root/'plant_debris_export'/'asset.json').write_text(json.dumps({'name':'Exported Asset','categories':['atlas','debris']}),encoding='utf-8')
  self.package('generic-export',['test_BaseColor.jpg','test_Opacity.jpg'],('atlas','debris'))
  (self.root/'generic-export'/'asset.json').write_text(json.dumps({'name':'Debris','categories':['atlas','debris'],'tags':['leaves','branch']}),encoding='utf-8')
  self.package('Plant Foliage',['test_BaseColor.jpg','test_Normal.jpg'],('surface','grass','dried'))
  self.package('Metal Plant Equipment',['test_BaseColor.jpg','test_Normal.jpg'],('surface','metal'))
  self.package('fabric-atlas',['test_BaseColor.jpg','test_Opacity.jpg'],('atlas','fabric'))
  app.scan();self.assertIsNone(app.SCAN_ERROR)
  self.assertEqual(len(app.INDEX['assets']),10)
  self.assertTrue({'Dry Plant Debris','Lake Plants','Lake Plant Stems','Plant Debris','Unidentified Desert Plant','plant_debris_export','generic-export'}.issubset({a['folder'] for a in app.INDEX['assets']}))

if __name__=='__main__':unittest.main()

