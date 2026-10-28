import unittest
from window_sizing import startup_geometry

class StartupSizingTests(unittest.TestCase):
    def test_work_area_and_minimum_at_supported_scales(self):
        for scale in (1,1.25,1.5,2):
            for left,top,width,height in ((0,0,1920,1040),(-1920,0,1920,1040),(48,32,1872,1048),(0,0,3840,2080),(0,0,1280,680)):
                with self.subTest(scale=scale,area=(left,top,width,height)):
                    x,y,w,h,mw,mh=startup_geometry(left,top,width,height,scale)
                    self.assertGreaterEqual(x,left);self.assertGreaterEqual(y,top)
                    self.assertLessEqual(x+w,left+width);self.assertLessEqual(y+h,top+height)
                    self.assertLessEqual(mw,w);self.assertLessEqual(mh,h)
                    self.assertGreater(w,0);self.assertGreater(h,0)
    def test_large_screen_keeps_preferred_logical_size(self):
        self.assertEqual(startup_geometry(0,0,3840,2080,1.5)[2:4],(2400,1560))
    def test_1080p_is_not_scaled_offscreen(self):
        self.assertEqual(startup_geometry(0,0,1920,1040,1.5)[2:4],(1872,992))

if __name__=='__main__':unittest.main()
