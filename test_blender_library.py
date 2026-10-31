import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import server as app
from blender_library import scan_blender_materials


class NativeLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.folder=self.root/'水面'/'涟漪';self.folder.mkdir(parents=True)
        self.meta={'format':'surface-studio-blender-material','version':1,'id':'f'*32,
            'name':'水面','materialName':'Water.001','blendFile':'material.blend','preview':'preview.png','blenderVersion':[4,2,4]}
        self.write();(self.folder/'material.blend').write_bytes(b'BLENDER')
        (self.folder/'preview.png').write_bytes(b'preview')

    def write(self):
        (self.folder/'surface-material.json').write_text(json.dumps(self.meta),encoding='utf-8')

    def tearDown(self): self.temp.cleanup()

    def test_portable_package_no_pbr_maps_and_no_index_required(self):
        assets=scan_blender_materials([self.root],[])
        self.assertEqual(len(assets),1);a=assets[0]
        self.assertEqual(a['maps'],[]);self.assertEqual(a['kind'],'blend')
        self.assertEqual(a['category'],'Uncategorized')
        moved=self.root.parent/(self.root.name+'-moved')
        self.root.rename(moved)
        try:
            b=scan_blender_materials([moved],[])[0]
            self.assertEqual(a['libraryKey'],b['libraryKey']);self.assertNotEqual(a['id'],b['id'])
        finally:moved.rename(self.root)

    def test_bad_manifest_and_incomplete_export_are_skipped(self):
        self.meta['blendFile']='../../outside.blend';self.write();warnings=[]
        self.assertEqual(scan_blender_materials([self.root],warnings),[]);self.assertTrue(warnings)
        self.meta['blendFile']='material.blend';self.write()
        stage=self.root/'.ss-export-pending';self.folder.rename(stage)
        self.assertEqual(scan_blender_materials([self.root],[]),[])

    def test_regular_root_and_extra_root_do_not_duplicate(self):
        self.assertEqual(len(scan_blender_materials([self.root,self.folder],[])),1)

    def test_server_exports_blend_path_and_preserves_backup_identity(self):
        saved={k:getattr(app,k) for k in ('DATA','CACHE','CONFIG','INDEX','ASSETS','STATE','SCANNING','SCAN_ERROR')}
        try:
            app.DATA=self.root/'data';app.DATA.mkdir();app.CACHE=app.DATA/'thumbs';app.CACHE.mkdir()
            ordinary=self.root/'pbr';ordinary.mkdir()
            app.CONFIG={'root':str(ordinary),'blenderRoots':[str(self.root/'水面')]}
            app.STATE={'favorites':[],'collections':[],'recent':[]};app.SCANNING=False;app.scan()
            a=app.categorized_library()['assets'][0]
            self.assertEqual(a['kind'],'blend');self.assertFalse(a['normalOnly'])
            self.assertEqual(app.asset_file(a['id'],'material.blend'),self.folder/'material.blend')
            with self.assertRaises(ValueError):app.asset_file(a['id'],'surface-material.json')
            backup=app.organizer.export(app.APP.snapshot_for_test())
            self.assertEqual(backup['materials'][a['id']],a['libraryKey'])
            self.assertEqual(app.categorized_library()['effectiveMaterialSaveRoot'],str(ordinary))
            # A custom save destination is indexed without manually adding a library source.
            app.CONFIG={'root':str(ordinary),'materialSaveRoot':str(self.root/'水面')}
            app.scan()
            library=app.categorized_library()
            self.assertEqual(library['effectiveMaterialSaveRoot'],str(self.root/'水面'))
            self.assertEqual(len(library['assets']),1)
            self.assertEqual(library['assets'][0]['category'],'Uncategorized')
            self.assertEqual(app.asset_file(library['assets'][0]['id'],'material.blend'),self.folder/'material.blend')
            app.edit_category({'action':'assign','asset':library['assets'][0]['id'],'category':'Rock'})
            app.scan()
            self.assertEqual(app.categorized_library()['assets'][0]['category'],'Rock')
            self.assertEqual(next(c['count'] for c in app.categorized_library()['categories'] if c['id']=='Uncategorized'),0)
        finally:
            for k,v in saved.items():setattr(app,k,v)


if __name__=='__main__':unittest.main()
