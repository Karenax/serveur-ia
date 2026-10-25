"""Build the Windows icon from the administration console's K favicon."""
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw


class Favicon(HTMLParser):
    href=None
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=='link' and values.get('rel')=='icon':self.href=values.get('href')


def polygon(path):
    tokens=re.findall(r'[MmLlHhVvZz]|-?\d+(?:\.\d+)?',path)
    points=[];x=y=0;i=0
    while i<len(tokens):
        command=tokens[i];i+=1
        if command in ('M','m','L','l'):
            a,b=float(tokens[i]),float(tokens[i+1]);i+=2
            x,y=(a,b) if command in ('M','L') else (x+a,y+b)
        elif command in ('H','h'):
            a=float(tokens[i]);i+=1;x=a if command=='H' else x+a
        elif command in ('V','v'):
            a=float(tokens[i]);i+=1;y=a if command=='V' else y+a
        elif command in ('Z','z'):break
        else:raise ValueError('Unsupported favicon path command.')
        points.append((x,y))
    return points


def main():
    root=Path(__file__).resolve().parent
    parser=Favicon();parser.feed((root.parent/'lanceur/web/index.html').read_text(encoding='utf-8'))
    prefix='data:image/svg+xml,'
    if not parser.href or not parser.href.startswith(prefix):raise ValueError('SVG favicon missing.')
    svg=ET.fromstring(unquote(parser.href[len(prefix):]))
    if svg.get('viewBox')!='0 0 32 32':raise ValueError('Unexpected favicon dimensions.')
    scale=32
    canvas=Image.new('RGBA',(32*scale,32*scale));draw=ImageDraw.Draw(canvas)
    for child in svg:
        kind=child.tag.rsplit('}',1)[-1]
        if kind=='rect':
            draw.rounded_rectangle((0,0,float(child.get('width'))*scale,float(child.get('height'))*scale),
                radius=float(child.get('rx','0'))*scale,fill=child.get('fill'))
        elif kind=='path':
            draw.polygon([(x*scale,y*scale) for x,y in polygon(child.get('d'))],fill=child.get('fill'))
        else:raise ValueError('Unsupported favicon element.')
    sizes=[(n,n) for n in (16,20,24,32,40,48,64,128,256)]
    image=canvas.resize((256,256),Image.Resampling.LANCZOS)
    image.save(root/'fred.ico',sizes=sizes)
    image.resize((128,128),Image.Resampling.LANCZOS).save(root/'fred-icon.png')
    print('K icon generated in 9 Windows sizes from the console favicon.')


if __name__=='__main__':main()
