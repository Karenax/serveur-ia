"""Build a locally paired Thunderbird extension from Kiara's bundled files."""

import json
import os
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile


def package(source, output, token, *, kiara=False):
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(suffix='.tmp', dir=output.parent)
    try:
        with os.fdopen(fd, 'wb') as stream, ZipFile(stream, 'w', ZIP_DEFLATED) as archive:
            for name in ('manifest.json', 'core.js', 'background.js', 'options.html', 'options.js'):
                archive.write(source / name, name)
            archive.writestr('pairing.json', json.dumps({'token': token, 'kiara': kiara}))
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
