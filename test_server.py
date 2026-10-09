"""Integration tests using a temporary material library; never change user assets."""
import io, json, tempfile, threading, time, unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from PIL import Image
import server as app

class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        root=Path(cls.temp.name)
        app.DATA=root/'data'; app.DATA.mkdir()
        app.CACHE=app.DATA/'thumbnails'; app.CACHE.mkdir()
        app.BRIDGE=app.BlenderBridge(app.DATA/'blender')
        cls.root=root/'中文 材质库'; cls.root.mkdir()
        material=cls.root/'Concrete_Test_a1Kxyz_4K_surface_ms'; material.mkdir()
        Image.new('RGBA',(32,32),(100,120,100,0)).save(material/'material_Preview.png')
        Image.new('RGB',(64,64),(120,130,120)).save(material/'test_4K_Albedo.jpg')
        Image.new('RGB',(64,64),(128,128,255)).save(material/'test_4K_Normal.jpg')
        (material/'test.json').write_text(json.dumps({'name':'Cracked Concrete','id':'test','tags':['cracked','grey'],'meta':[{'key':'tileable','value':True}]}))
        app.CONFIG={'root':str(cls.root)}
        app.STATE={'favorites':[],'collections':[],'recent':[]}
        app.scan()
        cls.http=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        cls.url='http://127.0.0.1:'+str(cls.http.server_port)
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()
        cls.asset=app.INDEX['assets'][0]

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close(); cls.temp.cleanup()

    def request(self,path,body=None,token=True):
        headers={'Content-Type':'application/json'}
        if token: headers['X-Studio-Token']=app.TOKEN
        return urlopen(Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers=headers),timeout=10)

    def test_index_metadata_and_resolution_boundary(self):
        a=self.asset
        self.assertEqual(a['resolution'],'4K')
        self.assertEqual(a['categoryZh'],'混凝土')
        self.assertIn('开裂',a['search'])
        self.assertEqual({m['channel'] for m in a['maps']},{'Albedo','Normal'})
        self.assertTrue(a['meta']['tileable'])

    def test_transparent_thumbnail_and_cache(self):
        with self.request('/api/image?id='+self.asset['id']+'&file=material_Preview.png&size=96') as r:
            image=Image.open(io.BytesIO(r.read()))
            self.assertEqual(image.mode,'RGBA')
            self.assertEqual(image.getpixel((0,0))[3],0)
        self.assertTrue(list(app.CACHE.glob('*.webp')))

    def test_disallow_unindexed_file(self):
        with self.assertRaises(HTTPError) as error:
            self.request('/api/image?id='+self.asset['id']+'&file=../../server.py')
        self.assertEqual(error.exception.code,400)

    def test_mutation_requires_token(self):
        with self.assertRaises(HTTPError) as error:
            self.request('/api/state',{'favorites':['bad']},token=False)
        self.assertEqual(error.exception.code,403)

    def test_favorites_and_collections_persist(self):
        payload={'favorites':[self.asset['id']],'collections':[{'id':'test-collection','name':'测试集合','ids':[self.asset['id']]}],'recent':[]}
        self.request('/api/state',payload).close()
        self.assertEqual(app.read_json(app.DATA/'state.json',{}),payload)
        with self.request('/api/state') as r: self.assertEqual(json.load(r),payload)

    def test_invalid_library_preserves_config(self):
        old=app.CONFIG.copy()
        with self.assertRaises(HTTPError) as error:
            self.request('/api/rescan',{'root':str(self.root/'missing')})
        self.assertEqual(error.exception.code,400)
        self.assertEqual(app.CONFIG,old)

    def test_library_api_matches_disk(self):
        with self.request('/api/library') as r:
            data=json.load(r)
            self.assertEqual(len(data['assets']),1)
            self.assertEqual(data['categories'][0]['count'],1)
            self.assertEqual(data['warnings'],[])

    def test_blender_http_export_contains_real_paths(self):
        import uuid
        sid=uuid.uuid4().hex
        session={'id':sid,'heartbeat':time.time(),'revision':'http-test','objects':[{'name':'Cube'}],'mode':'OBJECT'}
        app.BRIDGE.write(app.BRIDGE.root/'sessions'/(sid+'.json'),session)
        with self.request('/api/blender/status') as r:
            self.assertTrue(any(s['id']==sid for s in json.load(r)['sessions']))
        with self.request('/api/blender/apply',{'session':sid,'revision':'http-test','asset':self.asset['id']}) as r:
            queued=json.load(r)
        job=app.BRIDGE.read(app.BRIDGE.root/'requests'/(sid+'.json'))
        self.assertEqual(job['material']['id'],self.asset['id'])
        self.assertTrue(all(Path(m['path']).is_file() for m in job['material']['maps']))
        with self.request('/api/blender/result?id='+queued['id']) as r:
            self.assertEqual(json.load(r)['status'],'pending')

if __name__=='__main__': unittest.main(verbosity=2)
