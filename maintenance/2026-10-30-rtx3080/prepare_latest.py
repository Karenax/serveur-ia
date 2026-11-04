"""Download a hash-pinned official CUDA12 engine into an isolated F: test folder."""
import hashlib
import json
from pathlib import Path
import tarfile
import time
import urllib.request

HERE = Path(__file__).resolve().parent
URL = 'https://github.com/Niko1221/Strata/releases/download/v0.2.8/strata-engine-0.1.54-windows-x86_64-cuda-cuda12.tar.gz'
SHA = 'd9bb160fc73599bb1eeee64a74ea8a7eede4843b76c8fa1750335f1504811517'
OUT = Path('F:/Kiara-tests/strata-0.1.54-cuda12')


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    archive = OUT / 'engine.tar.gz'
    h = hashlib.sha256()
    total = 0
    started = last = time.monotonic()
    with urllib.request.urlopen(URL, timeout=60) as response, archive.open('xb') as target:
        while block := response.read(4 * 2**20):
            h.update(block)
            target.write(block)
            total += len(block)
            if time.monotonic() - last > 15:
                print(json.dumps({'downloaded_mib': round(total/2**20), 'seconds': round(time.monotonic()-started)}), flush=True)
                last = time.monotonic()
    assert h.hexdigest() == SHA, 'Official release archive hash mismatch'
    print('Official archive SHA-256 verified; extracting.', flush=True)
    with tarfile.open(archive, 'r:gz') as bundle:
        bundle.extractall(OUT / 'package', filter='data')
    engines = list((OUT / 'package').rglob('strata.exe'))
    assert len(engines) == 1, engines
    directory = engines[0].parent
    record = {'release': 'v0.2.8', 'engine_version': '0.1.54', 'url': URL, 'archive_sha256': SHA,
              'archive_bytes': total, 'directory': str(directory),
              'files': {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in directory.rglob('*') if p.is_file()}}
    (HERE / 'latest-engine.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'engine_directory': str(directory), 'download_seconds': time.monotonic()-started}), flush=True)


if __name__ == '__main__':
    main()
