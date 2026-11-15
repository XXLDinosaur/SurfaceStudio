import importlib
import tempfile
import unittest
from pathlib import Path


class HDRLibraryTests(unittest.TestCase):
    def test_scene_name_rules_and_priority(self):
        self.assertIsNotNone(importlib.util.find_spec('hdr_categories'), 'HDR 场景分组尚未实现')
        from hdr_categories import classify_hdr
        cases = {
            'studio_small_08_4k': 'HDRStudio',
            '城市摄影棚_4K': 'HDRStudio',
            'kloofendal_misty_morning_puresky_4k': 'HDRSky',
            'sunset_forest_4k': 'HDRForest',
            'forest_road_02_4k': 'HDRForest',
            'indoor_garden_4k': 'HDRInterior',
            'abandoned_factory_canteen_01_4k': 'HDRIndustrial',
            'abandoned_games_room_01_4k': 'HDRInterior',
            'city_night_4k': 'HDRStreet',
            'parking_lot_4k': 'HDRStreet',
            '公园清晨_4k': 'HDRForest',
            '海边日落_4k': 'HDRCoast',
            'alps_field_4k': 'HDRMountain',
            'meadow_noon_4k': 'HDRField',
            'desert_sunrise_4k': 'HDRDesert',
            'snowy_park_4k': 'HDRForest',
            'winter_snow_4k': 'HDRSnow',
            'aarfontein_dawn_2_4k': 'HDRSky',
            'altanka_4k': 'HDROther',
            'roadmap_4k': 'HDROther',
            'hillside_02_4k': 'HDRMountain',
            'abandoned_hopper_terminal_01_4k': 'HDRIndustrial',
            'aviation_museum_4k': 'HDRInterior',
            'ballroom_4k': 'HDRInterior',
            'old_shop_4k': 'HDRInterior',
            'piazza_clear_4k': 'HDRStreet',
            'golf_course_4k': 'HDRField',
            'approaching_storm_4k': 'HDRSky',
        }
        for name, expected in cases.items():
            with self.subTest(name=name): self.assertEqual(classify_hdr(name),expected)

    def test_scene_scan_rescan_new_files_and_stable_identity(self):
        hdr = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('forest_01_4k.hdr','forest_01_4k.exr','room_01_4k.hdr'):
                (root/name).touch()
            first=hdr.scan_hdrs(root,[])
            self.assertEqual({a['category'] for a in first},{'HDRForest','HDRInterior'})
            ids={a['preview']:a['id'] for a in first}
            (root/'beach_02_4k.hdr').touch()
            second=hdr.scan_hdrs(root,[])
            self.assertEqual(next(a for a in second if a['preview'].startswith('beach'))['category'],'HDRCoast')
            self.assertTrue(all(a['id']==ids[a['preview']] for a in second if a['preview'] in ids))

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('hdr_library'), 'HDR 图库尚未实现')
        return importlib.import_module('hdr_library')

    def test_recursive_scan_stable_ids_and_format_isolation(self):
        hdr = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sub = root / '中文天空'; sub.mkdir()
            for name in ('天空.hdr', '天空.exr', 'UPPER.HDR', 'color.png'):
                (sub / name).write_bytes(b'fixture')
            warnings = []
            assets = hdr.scan_hdrs(str(root), warnings)
            self.assertEqual(len(assets), 3)
            self.assertEqual(len({a['id'] for a in assets}), 3)
            self.assertEqual([a['id'] for a in assets], [a['id'] for a in hdr.scan_hdrs(root, [])])
            self.assertTrue(all(a['kind'] == 'hdr' for a in assets))
            self.assertEqual({a['preview']:a['category'] for a in assets},
                             {'天空.hdr':'HDRSky','天空.exr':'HDRSky','UPPER.HDR':'HDROther'})
            self.assertTrue(all(a['maps'][0]['channel'] == 'Environment' for a in assets))
            self.assertEqual(warnings, [])

    def test_missing_and_empty_library(self):
        hdr = self.module()
        self.assertEqual(hdr.scan_hdrs('', []), [])
        with tempfile.TemporaryDirectory() as directory:
            warnings = []
            self.assertEqual(hdr.scan_hdrs(Path(directory)/'missing', warnings), [])
            self.assertEqual(len(warnings), 1)

    def test_root_overlap_rejected(self):
        hdr = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); child = root/'child'; child.mkdir()
            for source, others in [(root, [child]), (child, [root]), (root, [root])]:
                with self.assertRaises(ValueError):
                    hdr.validate_hdr_root(str(source), [str(p) for p in others])
            self.assertEqual(hdr.validate_hdr_root('', [str(root)]), '')

    def test_real_hdr_exr_thumbnail_and_source_untouched(self):
        hdr = self.module()
        import numpy as np
        import OpenImageIO as oiio
        with tempfile.TemporaryDirectory() as directory:
            for ext in ('hdr', 'exr'):
                path = Path(directory) / ('中文环境.' + ext)
                pixels = np.ones((8, 16, 3), dtype=np.float32)
                pixels[:, :8] *= 4
                output = oiio.ImageOutput.create(str(path))
                self.assertTrue(output.open(str(path), oiio.ImageSpec(16, 8, 3, oiio.FLOAT)))
                self.assertTrue(output.write_image(pixels)); output.close()
                before = path.read_bytes()
                preview = hdr.hdr_thumbnail(path, 8)
                self.assertEqual(preview.size, (8, 4))
                self.assertEqual(preview.mode, 'RGB')
                self.assertGreater(preview.getpixel((0, 0))[0], preview.getpixel((7, 0))[0])
                self.assertEqual(path.read_bytes(), before)

    def test_corrupt_preview_has_clear_error(self):
        hdr = self.module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'broken.hdr'; path.write_bytes(b'invalid')
            with self.assertRaises(ValueError): hdr.hdr_thumbnail(path, 64)


class HDRAPITests(unittest.TestCase):
    def test_startup_and_rescan_warm_new_assets_incrementally(self):
        import server as app
        from preview_cache import HDRPreviewCache
        from unittest.mock import patch
        from PIL import Image
        names=('DATA','CACHE','CONFIG','INDEX','ASSETS','SCANNING','SCAN_ERROR',
               'HDR_PREVIEWS','PREVIEW_WARMUP_ENABLED')
        saved={name:getattr(app,name) for name in names}
        temporary=tempfile.TemporaryDirectory();cache=HDRPreviewCache();calls=[]
        try:
            base=Path(temporary.name);root=base/'materials';root.mkdir()
            source=base/'hdr';source.mkdir();data=base/'data';data.mkdir()
            (source/'forest_01.hdr').touch()
            app.DATA=data;app.CACHE=data/'thumbs';app.CACHE.mkdir()
            app.CONFIG={'root':str(root),'hdrRoot':str(source)};app.SCANNING=False
            app.HDR_PREVIEWS=cache;app.PREVIEW_WARMUP_ENABLED=False
            def decode(path,size):calls.append(path.name);return Image.new('RGB',(16,8))
            with patch.object(app,'hdr_thumbnail',side_effect=decode):
                app.scan();app.start_preview_cache();self.assertTrue(cache.wait(5))
                self.assertEqual(cache.status()['ready'],1)
                (source/'studio_02.hdr').touch()
                app.scan();self.assertTrue(cache.wait(5))
                self.assertEqual(cache.status()['ready'],2)
                self.assertEqual(sorted(calls),['forest_01.hdr','studio_02.hdr'])
                self.assertEqual(cache.status()['failed'],0)
        finally:
            cache.cancel();cache.wait(5)
            for name,value in saved.items():setattr(app,name,value)
            temporary.cleanup()

    def test_old_index_manual_override_rescan_and_new_import(self):
        import json
        import server as app
        names=('DATA','CONFIG','INDEX','ASSETS','SCANNING','SCAN_ERROR','STATE')
        saved={name:getattr(app,name) for name in names}
        try:
            with tempfile.TemporaryDirectory() as directory:
                base=Path(directory); root=base/'materials'; root.mkdir()
                source=base/'hdr'; source.mkdir(); data=base/'data'; data.mkdir()
                (source/'forest_01_4k.hdr').touch()
                app.DATA=data; app.CONFIG={'root':str(root),'hdrRoot':str(source)}
                app.STATE={'favorites':[],'collections':[],'recent':[]}; app.SCANNING=False
                app.scan()
                self.assertIsNone(app.SCAN_ERROR)
                asset=app.INDEX['assets'][0]; ident=asset['id']
                # Simulate a cached 1.8.0 index: derive groups without demanding a scan.
                asset['category']='HDR';asset['categoryZh']='HDR 环境';asset['search']='forest hdri 环境 天空'
                categorized=app.categorized_library()['assets'][0]
                self.assertEqual(categorized['category'],'HDRForest')
                self.assertNotIn('天空',categorized['search'], '旧版通用关键词不能让所有 HDR 都匹配天空')
                app.edit_category({'action':'create','name':'我的外景','asset':ident})
                manual=app.categorized_library()['assets'][0]['category']
                self.assertTrue(manual.startswith('custom-'))
                app.STATE['favorites']=[ident]
                (source/'studio_small_02_4k.exr').touch()
                app.scan()
                items={a['id']:a for a in app.categorized_library()['assets']}
                self.assertEqual(items[ident]['category'],manual)
                self.assertTrue(items[ident]['manualCategory'])
                self.assertEqual(next(a for a in items.values() if a['id']!=ident)['category'],'HDRStudio')
                self.assertIn(ident,app.STATE['favorites'])
                # A fresh metadata read after rescan models the restart path.
                records=json.loads((data/'categories.json').read_text(encoding='utf-8'))
                self.assertTrue(records)
                app.edit_category({'action':'assign','asset':ident,'category':None})
                app.scan()
                item=next(a for a in app.categorized_library()['assets'] if a['id']==ident)
                self.assertEqual(item['category'],'HDRForest')
                self.assertFalse(item['manualCategory'])
        finally:
            for name,value in saved.items():setattr(app,name,value)

    def test_config_scan_preview_drop_and_invalid_requests(self):
        import io, json, os, threading, time
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        from PIL import Image
        import numpy as np
        import OpenImageIO as oiio
        import server as app
        names = ('DATA','CACHE','CONFIG','INDEX','ASSETS','STATE','BRIDGE','SCANNING','SCAN_ERROR')
        saved = {name: getattr(app, name) for name in names}
        http = None
        try:
            with tempfile.TemporaryDirectory() as directory:
                base = Path(directory); root = base/'materials'; root.mkdir()
                source = base/'天空'; source.mkdir(); data = base/'data'; data.mkdir()
                app.DATA = data; app.CACHE = data/'thumbs'; app.CACHE.mkdir()
                app.CONFIG = {'root':str(root)}; app.INDEX = {'root':str(root),'assets':[]}
                app.ASSETS = {}; app.STATE = {'favorites':[],'collections':[],'recent':[]}
                app.SCANNING = False; app.BRIDGE = app.BlenderBridge(data/'blender')
                for ext in ('hdr','exr'):
                    path = source/('中文天空.'+ext)
                    output = oiio.ImageOutput.create(str(path))
                    output.open(str(path), oiio.ImageSpec(16, 8, 3, oiio.FLOAT))
                    output.write_image(np.ones((8,16,3),np.float32)); output.close()
                http = app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
                threading.Thread(target=http.serve_forever,daemon=True).start()
                base_url = 'http://127.0.0.1:'+str(http.server_port)
                def request(path, body=None):
                    return urlopen(Request(base_url+path, data=None if body is None else json.dumps(body).encode(),
                        headers={'Content-Type':'application/json','X-Studio-Token':app.TOKEN}),timeout=10)
                with request('/api/rescan', {'root':str(root),'hdrRoot':str(source)}): pass
                deadline = time.monotonic()+5
                while (app.SCANNING or not app.INDEX.get('scannedAt')) and time.monotonic()<deadline: time.sleep(.01)
                self.assertFalse(app.SCANNING)
                self.assertEqual(app.CONFIG.get('hdrRoot'),str(source.resolve()))
                with request('/api/library') as r: library = json.load(r)
                self.assertEqual(len(library['assets']),2)
                self.assertTrue(all(a['assetGroup']=='hdr' for a in library['assets']))
                for asset in library['assets']:
                    from urllib.parse import urlencode
                    from unittest.mock import patch
                    with patch.object(app,'hdr_thumbnail',wraps=app.hdr_thumbnail) as decode:
                        for preview_size in (64,96,480):
                            with request('/api/image?'+urlencode({'id':asset['id'],'file':asset['preview'],'size':preview_size})) as r:
                                self.assertEqual(Image.open(io.BytesIO(r.read())).size,(16,8))
                        self.assertEqual(decode.call_count,1,'不同常用预览尺寸应复用同一张缓存底图')
                    with request('/api/blender/drop',{'asset':asset['id']}) as r: drop = json.load(r)
                    task = json.loads(Path(drop['path']).read_text(encoding='utf-8'))
                    self.assertEqual(task['material']['kind'],'hdr')
                    self.assertEqual(task['protocol'],3, '旧插件必须拒绝 HDR，避免误改模型材质')
                    with self.assertRaises(HTTPError): request('/api/blender/apply',{'asset':asset['id']})
                    with self.assertRaises(ValueError): app.asset_file(asset['id'],'../outside.hdr')
                target = next(a for a in library['assets'] if a['maps'][0]['ext']=='HDR')
                with request('/api/state', {'favorites':[target['id']]}): pass
                with request('/api/material/rename', {'id':target['id'],'name':'新天空'}): pass
                self.assertTrue((source/'新天空.hdr').is_file())
                self.assertTrue((source/'中文天空.exr').is_file())
                self.assertTrue(source.is_dir())
                self.assertEqual(app.ASSETS[target['id']]['name'],'新天空')
                self.assertIn(target['id'], app.STATE['favorites'])
                old = dict(app.CONFIG)
                with self.assertRaises(HTTPError): request('/api/rescan',{'hdrRoot':str(root)})
                self.assertEqual(app.CONFIG,old)
                self.assertEqual(json.loads((data/'config.json').read_text(encoding='utf-8'))['hdrRoot'],str(source.resolve()))
        finally:
            if http: http.shutdown(); http.server_close()
            for name, value in saved.items(): setattr(app,name,value)


if __name__ == '__main__': unittest.main()
