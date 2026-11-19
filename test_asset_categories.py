import unittest
from asset_categories import automatic_category,asset_group
class Categories(unittest.TestCase):
 def test_names(self):
  for name,key in [('Wall Crack','Crack'),('Drain Cover','DrainCover'),('Metal Piece','Metal'),('Green Weed Vines','Climber'),('水波','Water'),('unknown_123','Uncategorized')]:
   self.assertEqual(automatic_category({'name':name,'category':'Decal'}),key)
 def test_groups(self):
  self.assertEqual(asset_group({'kind':'decal','normalOnly':True}),'decal')
  self.assertEqual(asset_group({'normalOnly':True}),'normal')
  self.assertEqual(asset_group({'kind':'blend'}),'material')
 def test_new_library_material_names(self):
  examples={'Artificial Turf':'Grass','Arid Gravel Ground':'Gravel','Wooden Planks':'Wood',
   'Basket Weave Ash Parquet':'Wood','Ash Veneer':'Wood','Polystyrene Sheet':'Plastic',
   'Packing Foam':'Foam','Rubber':'Rubber','Scratched Polypropylene Plastic':'Plastic',
   'Stucco Facade':'Plaster','Forest Floor':'Ground','Mossy Ground':'Moss',
   'Luna Pearl Granite':'Stone','Cobblestone':'Stone','Charred Bricks':'Brick',
   'Fresh Windswept Snow':'Snow','Burnt Cardboard':'Paper','Plain Weave Cotton':'Fabric',
   'Ground Rubble':'Debris','Animal Skin':'Animal','Turkey Feathers':'Animal',
   'Noodles':'Food','Banana Peel':'Food','Broken Glass':'Glass','Fabric Painting':'Artwork'}
  for name,category in examples.items():
   with self.subTest(name=name):self.assertEqual(automatic_category({'name':name,'category':'Other'}),category)
 def test_structured_metadata_and_technical_names(self):
  for categories,key in [(['surface','Wood','Floor'],'Wood'),(['surface','grass','plastic'],'Grass'),
                          (['surface','stone','granite'],'Stone'),(['atlas','debris','construction'],'Debris')]:
   self.assertEqual(automatic_category({'name':'Scan 123','category':'Other','categories':categories}),key)
  self.assertEqual(automatic_category({'name':'Scan 123','folder':'oak_veneer_asset_4k','category':'Other'}),'Wood')
  self.assertEqual(automatic_category({'name':'Scan 123','tags':['woven cotton'],'category':'Other'}),'Fabric')
  self.assertEqual(automatic_category({'name':'unknown_123','category':'Other'}),'Uncategorized')
  self.assertEqual(automatic_category({'name':'Wooden Planks','kind':'blend','category':'Uncategorized'}),'Uncategorized')
if __name__=='__main__':unittest.main()
