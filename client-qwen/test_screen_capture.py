import base64
import io
import unittest
from PIL import Image
from screen_capture import encode_region


class RegionCaptureTests(unittest.TestCase):
    def test_only_selected_pixels_leave_the_capture(self):
        image=Image.new('RGB',(80,40),'red');image.paste('blue',(40,0,80,40))
        data=base64.b64decode(encode_region(image,(40,0,80,40)).split(',')[1])
        with Image.open(io.BytesIO(data)) as selected:
            self.assertEqual(selected.size,(40,40));r,g,b=selected.getpixel((10,10));self.assertGreater(b,200);self.assertLess(r,30)
        for rect in [(-1,0,40,40),(0,0,100,40),(0,0,2,2)]:
            with self.assertRaises(ValueError):encode_region(image,rect)
        image.close()


if __name__=='__main__':unittest.main()
