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
if __name__=='__main__':unittest.main()
