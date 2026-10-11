"""Windows Explorer product name and version for the compiled application."""
from pathlib import Path
from product import APP_NAME, EXE_NAME
from updater import VERSION, version
numbers = (*version(VERSION), 0)
values = {'CompanyName':'Fred', 'FileDescription':APP_NAME, 'FileVersion':VERSION,
          'InternalName':APP_NAME, 'OriginalFilename':EXE_NAME,
          'ProductName':APP_NAME, 'ProductVersion':VERSION}
strings = ',\n'.join('StringStruct('+repr(k)+', '+repr(v)+')' for k,v in values.items())
source = f'''VSVersionInfo(ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r},
mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)),
kids=[StringFileInfo([StringTable('040c04b0', [{strings}])]),
VarFileInfo([VarStruct('Translation', [1036,1200])])])'''
Path(__file__).with_name('product-version.txt').write_text(source, encoding='utf-8')
