"""Decal scanning and portable rename checks using isolated assets."""
import json,tempfile,unittest
from pathlib import Path
from PIL import Image
from decal_library import scan_decals

class DecalTests(unittest.TestCase):
    def test_complete_incomplete_and_rename(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'污渍_2K';folder.mkdir()
            for channel in ['Albedo','Opacity','Normal','Roughness']:
                Image.new('RGB',(8,8)).save(folder/('test_2K_'+channel+'.jpg'))
            bad=root/'incomplete';bad.mkdir();Image.new('RGB',(8,8)).save(bad/'only_Specular.jpg')
            warnings=[];assets=scan_decals(root,warnings)
            self.assertEqual(len(assets),1);self.assertEqual(len(warnings),1)
            item=assets[0];self.assertEqual(item['kind'],'decal');self.assertEqual(item['resolution'],'2K')
            (folder/'.surface-studio.json').write_text(json.dumps({'format':'surface-studio-name','id':item['id'],'name':'新的污渍','libraryKey':item['libraryKey']}),encoding='utf-8')
            folder.rename(root/'新的污渍')
            renamed=scan_decals(root,[])[0]
            self.assertEqual(renamed['id'],item['id']);self.assertEqual(renamed['name'],'新的污渍')
            self.assertEqual(renamed['folder'],'新的污渍')

    def test_no_library_is_optional(self):
        self.assertEqual(scan_decals('',[]),[])

if __name__=='__main__':unittest.main()
