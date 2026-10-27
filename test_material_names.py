import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import server as app
from material_names import rename_material

class RenameTests(unittest.TestCase):
    def setUp(self):
        self.saved={k:getattr(app,k) for k in ('DATA','CACHE','CONFIG','INDEX','ASSETS','STATE','SCANNING','SCAN_ERROR')}
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        app.DATA=self.base/'data';app.DATA.mkdir();app.CACHE=app.DATA/'thumbs';app.CACHE.mkdir()
        self.root=self.base/'library';self.root.mkdir();self.normal=self.base/'normals';self.normal.mkdir()
        folder=self.root/'Rock_Original';folder.mkdir()
        Image.new('RGB',(8,8)).save(folder/'Albedo.png')
        (folder/'meta.json').write_text(json.dumps({'name':'Original stone'}))
        native=self.root/'native';native.mkdir();Image.new('RGB',(8,8)).save(native/'preview.png');(native/'material.blend').write_bytes(b'BLENDER_TEST')
        (native/'surface-material.json').write_text(json.dumps({'format':'surface-studio-blender-material','version':1,'id':'a'*32,'name':'Native','materialName':'Original','blendFile':'material.blend','preview':'preview.png','blenderVersion':[4,2,4]}))
        Image.new('RGB',(8,8)).save(self.normal/'water.png');Image.new('RGB',(8,8)).save(self.normal/'another.png')
        app.CONFIG={'root':str(self.root),'normalRoot':str(self.normal)};app.STATE={'favorites':[],'collections':[],'recent':[]};app.SCANNING=False;app.scan()
    def tearDown(self):
        for k,v in self.saved.items():setattr(app,k,v)
        self.tmp.cleanup()
    def test_rename_all_kinds_preserves_identity_files_and_records(self):
        for asset in list(app.ASSETS.values()):
            if asset['name']=='another':continue
            ident=asset['id'];original=app.asset_file(ident,asset['preview']).read_bytes()
            app.STATE['favorites'].append(ident);app.edit_category({'action':'assign','asset':ident,'category':'Metal'})
            old_key=asset.get('libraryKey',asset['folder']);name='新材质'+ident[:3]
            result=rename_material(app,ident,name)
            renamed=app.ASSETS[ident]
            self.assertEqual(renamed['name'],name);self.assertTrue(Path(result['path']).exists())
            self.assertEqual(renamed['libraryKey'],old_key);self.assertEqual(app.asset_file(ident,renamed['preview']).read_bytes(),original)
            self.assertIn(ident,app.STATE['favorites']);self.assertEqual(next(a['category'] for a in app.categorized_library()['assets'] if a['id']==ident),'Metal')
            app.scan();self.assertEqual(app.ASSETS[ident]['name'],name)
            if asset.get('kind')=='blend':self.assertEqual(json.loads((Path(result['path'])/'surface-material.json').read_text(encoding='utf-8'))['materialName'],'Original')
        self.assertTrue((self.normal/'another.png').exists())
    def test_conflicts_and_invalid_names_do_not_change_source(self):
        a=next(a for a in app.ASSETS.values() if a.get('kind') is None)
        for name in ['../bad','CON','bad.','native','']:
            with self.assertRaises(ValueError):rename_material(app,a['id'],name)
        self.assertTrue((self.root/a['folder']).exists());self.assertFalse((self.root/a['folder']/'.surface-studio.json').exists())
    def test_move_failure_rolls_back_metadata(self):
        a=next(a for a in app.ASSETS.values() if a.get('kind') is None)
        original=Path.rename
        def fail(path,target):
            if path.name.startswith('.ss-rename-') and Path(target).name=='Failed':raise PermissionError('locked')
            return original(path,target)
        with patch.object(Path,'rename',fail):
            with self.assertRaises(PermissionError):rename_material(app,a['id'],'Failed')
        self.assertTrue((self.root/a['folder']).exists());self.assertEqual(app.ASSETS[a['id']]['name'],a['name'])
        self.assertFalse((self.root/a['folder']/'.surface-studio.json').exists())

if __name__=='__main__':unittest.main()
