"""Fetch official NVIDIA packages for offline inspection only; never install."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
VERSION = '581.80'
OUT = Path('F:/Kiara-tests/pilotes-581.80')
URLS = {
    'geforce': 'https://us.download.nvidia.com/Windows/581.80/581.80-desktop-win10-win11-64bit-international-dch-whql.exe',
    'quadro': 'https://us.download.nvidia.com/Windows/Quadro_Certified/581.80/581.80-quadro-rtx-desktop-notebook-win10-win11-64bit-international-dch-whql.exe',
}


def prepare(item):
    name, url = item
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / url.rsplit('/', 1)[1]
    start = last = time.monotonic()
    if not target.exists():
        partial = target.with_suffix('.partial')
        with urllib.request.urlopen(url, timeout=60) as source, partial.open('xb') as stream:
            count = 0
            while data := source.read(4 * 2**20):
                stream.write(data)
                count += len(data)
                if time.monotonic() - last > 15:
                    print(json.dumps({'package': name, 'downloaded_mib': round(count / 2**20)}), flush=True)
                    last = time.monotonic()
        partial.rename(target)
    result = subprocess.run(['C:/Program Files/7-Zip/7z.exe', 'x', str(target), '-o' + str(folder / 'extracted'),
                             '-y', 'Display.Driver/*.inf', 'Display.Driver/nvlddmkm.sys', 'Display.Driver/nvcuda64.dll',
                             'Display.Driver/*.cat'], capture_output=True, text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    records = []
    for inf in (folder / 'extracted').rglob('*.inf'):
        raw = inf.read_bytes()
        text = raw.decode('utf-16') if raw.startswith(b'\xff\xfe') else raw.decode('utf-8', errors='replace')
        ids = {device: [line.strip() for line in text.splitlines()
                         if 'PCI\\VEN_10DE&DEV_' + device in line.upper() and not line.lstrip().startswith(';')]
               for device in ('2216', '15F8', '1C31')}
        if any(ids.values()):
            records.append({'inf': str(inf), 'hardware_matches': ids})
    payloads = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (folder / 'extracted').rglob('*') if p.is_file() and p.suffix in ('.sys', '.dll')}
    record = {'name': name, 'version': VERSION, 'url': url, 'installer': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'matching_infs': records, 'payloads': payloads, 'elapsed_s': time.monotonic() - start}
    (HERE / f'driver-{name}-{VERSION.replace(".", "")}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, ensure_ascii=True), flush=True)
    return record


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as workers:
        for result in workers.map(prepare, URLS.items()):
            pass
