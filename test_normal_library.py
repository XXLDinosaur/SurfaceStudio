"""Normal-only source integration: temporary files, never user material data."""
import copy
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
from PIL import Image
import server as app


class NormalLibraryTests(unittest.TestCase):
    def setUp(self):
        self.saved={k:getattr(app,k) for k in ('DATA','CACHE','CONFIG','INDEX','ASSETS','STATE','BRIDGE','SCANNING','SCAN_ERROR')}
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        app.DATA=self.base/'data';app.DATA.mkdir();app.CACHE=app.DATA/'thumbs';app.CACHE.mkdir()
        app.BRIDGE=app.BlenderBridge(app.DATA/'blender');app.STATE={'favorites':[],'collections':[],'recent':[]}
        self.root=self.base/'pbr';self.root.mkdir();p=self.root/'Rock_Demo_4K';p.mkdir()
        Image.new('RGB',(24,24)).save(p/'demo_albedo.png')
        self.normals=self.base/'水面法线';self.normals.mkdir()
        for name in ('涟漪.png','波纹.png','海水/涟漪.png'):
            p=self.normals/name;p.parent.mkdir(exist_ok=True);Image.new('RGB',(24,24),(128,128,255)).save(p)
        app.CONFIG={'root':str(self.root),'normalRoot':str(self.normals)};app.SCANNING=False;app.scan()
        self.http=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        threading.Thread(target=self.http.serve_forever,daemon=True).start();self.url='http://127.0.0.1:'+str(self.http.server_port)

    def tearDown(self):
        self.http.shutdown();self.http.server_close()
        for k,v in self.saved.items():setattr(app,k,v)
        self.temp.cleanup()

    def request(self,path,body=None):
        return urlopen(Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Studio-Token':app.TOKEN}),timeout=10)

    def test_each_normal_is_independent_and_real_path_is_exported(self):
        normals=[a for a in app.categorized_library()['assets'] if a.get('kind')=='normal']
        self.assertEqual(len(normals),3);self.assertEqual(len({a['id'] for a in normals}),3)
        self.assertEqual(len(app.ASSETS),4)
        for a in normals:
            self.assertTrue(a['normalOnly']);self.assertEqual(len(a['maps']),1);self.assertEqual(a['maps'][0]['channel'],'Normal')
            self.assertEqual(app.asset_file(a['id'],a['preview']),self.normals/a['folder']/a['preview'])
            with self.request('/api/image?'+urlencode({'id':a['id'],'file':a['preview']})) as r:
                im=Image.open(io.BytesIO(r.read()));self.assertEqual(im.size,(24,24))
            with self.request('/api/blender/drop',{'asset':a['id'],'options':{}}) as r:drop=json.load(r)
            payload=json.loads(Path(drop['path']).read_text(encoding='utf-8'))
            self.assertEqual(payload['material']['root'],str(self.normals.resolve()))
            self.assertTrue(Path(payload['material']['maps'][0]['path']).is_file())
            with self.assertRaises(ValueError):app.asset_file(a['id'],'../outside.png')
        before={a['id'] for a in normals};app.scan()
        self.assertEqual(before,{a['id'] for a in app.ASSETS.values() if a.get('kind')=='normal'})

    def test_backup_matches_files_not_parent_folder_and_survives_move(self):
        normals=[a for a in app.ASSETS.values() if a.get('kind')=='normal']
        first,second=normals[:2]
        app.STATE['favorites']=[first['id']];app.STATE['collections']=[{'id':'water','name':'水','ids':[second['id']]}]
        assigned_category='Water' if 'Water' in app.CATEGORIES else 'Grass'
        app.edit_category({'action':'assign','asset':second['id'],'category':assigned_category})
        backup=app.organizer.export(app.APP.snapshot_for_test())
        self.assertEqual(len(set(backup['materials'].values())),4)
        relocated=self.base/'other-drive';self.normals.rename(relocated);app.CONFIG['normalRoot']=str(relocated);app.scan()
        moved={a['libraryKey']:a for a in app.ASSETS.values() if a.get('kind')=='normal'}
        self.assertNotIn(first['id'],app.ASSETS)
        first_id=moved[first['libraryKey']]['id'];second_id=moved[second['libraryKey']]['id']
        app.STATE={'favorites':[],'collections':[],'recent':[]};(app.DATA/'categories.json').unlink()
        app.organizer.handle(app.APP.snapshot_for_test(),{'action':'restore','backup':backup})
        self.assertEqual(app.STATE['favorites'],[first_id])
        self.assertEqual(app.STATE['collections'][0]['ids'],[second_id])
        self.assertEqual(next(a for a in app.categorized_library()['assets'] if a['id']==second_id)['category'],assigned_category)

    def test_invalid_source_preserves_config_and_pbr_normal_detection(self):
        old=app.CONFIG.copy()
        for source in (str(self.base/'missing'),str(self.root),str(self.base)):
            with self.assertRaises(HTTPError):self.request('/api/rescan',{'normalRoot':source})
            self.assertEqual(app.CONFIG,old)
        normal_mat=self.root/'Water_4K';normal_mat.mkdir();Image.new('RGB',(8,8),(128,128,255)).save(normal_mat/'water_normal.png')
        Image.new('RGB',(8,8)).save(normal_mat/'water_Preview.png')
        app.scan();a=next(a for a in app.categorized_library()['assets'] if a['folder']=='Water_4K')
        self.assertEqual(a['preview'],'water_normal.png')
        self.assertTrue(a['normalOnly'])
        Image.new('RGB',(8,8)).save(normal_mat/'water_albedo.png');app.scan()
        self.assertFalse(next(a for a in app.categorized_library()['assets'] if a['folder']=='Water_4K')['normalOnly'])

    def test_normal_source_inside_pbr_is_not_double_indexed(self):
        nested=self.root/'法线';self.normals.rename(nested);app.CONFIG['normalRoot']=str(nested);app.scan()
        self.assertEqual(len(app.ASSETS),4)
        self.assertEqual(sum(a.get('kind')=='normal' for a in app.ASSETS.values()),3)

if __name__=='__main__':unittest.main()
