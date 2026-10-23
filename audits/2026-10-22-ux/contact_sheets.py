from pathlib import Path
from PIL import Image, ImageDraw
root=Path(__file__).parent
import sys
recent='--recent' in sys.argv
cutoff=(root/'sheet-01.jpg').stat().st_mtime if recent else 0
files=sorted(p for p in (root/'captures').glob('*.png') if p.stat().st_mtime>cutoff)
for start in range(0,len(files),4):
    batch=files[start:start+4]
    sheet=Image.new('RGB',(1440,990),'#e5e5e5')
    draw=ImageDraw.Draw(sheet)
    for i,p in enumerate(batch):
        img=Image.open(p).convert('RGB');img.thumbnail((716,460))
        x=(i%2)*720;y=(i//2)*495
        draw.text((x+8,y+5),p.name,fill='black')
        sheet.paste(img,(x+(720-img.width)//2,y+27))
    sheet.save(root/f'{"detail" if recent else "sheet"}-{start//4+1:02}.jpg',quality=92)
print(len(files),'captures;', (len(files)+3)//4,'planches')
