"""Build/sign the optional Windows voice pack; never included by Build-Client.ps1."""
import argparse
import base64
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def package(output, sign_home=None):
    source = ROOT/'toolchain/whisper.cpp-1.9.5'
    expected = json.loads((ROOT/'client-voice/max-models.json').read_text(encoding='utf-8'))
    if any(digest(source/name)!=value for name,value in expected['native_sources'].items()):
        raise ValueError('Unexpected Whisper source revision or unrecorded local patch.')
    build = ROOT/'toolchain/max-asr-build'
    if not (build/'kiara-asr.dll').is_file():
        raise ValueError('Build-Max-ASR.cmd must succeed first.')
    staging = Path(tempfile.mkdtemp(prefix='voice-max-pack-', dir=ROOT/'toolchain'))
    python = ROOT/'toolchain/max-realtime-python/Scripts/python.exe'
    subprocess.run([str(python), '-m', 'PyInstaller', '--noconfirm', '--onedir', '--console', '--name', 'max-worker',
                    '--collect-all', 'ptts', '--exclude-module', 'torch', '--exclude-module', 'scipy', '--exclude-module', 'sherpa_onnx', '--exclude-module', 'onnxruntime',
                    '--distpath', str(staging), '--workpath', str(ROOT/'toolchain/max-pack-pyinstaller'),
                    '--specpath', str(ROOT/'toolchain/max-pack-pyinstaller'), str(ROOT/'client-voice/max_pack_worker.py')], check=True)
    contents = staging/'max-worker'
    native = contents/'native'
    native.mkdir()
    for path in [*build.glob('*.dll'),*(build/'bin').glob('*.dll')]:
        shutil.copyfile(path, native/path.name)
    sys.path.insert(0,str(ROOT/'lanceur'))
    from phonon_model import verify as verify_phonon, SPEC as phonon_spec
    phonon_folder=verify_phonon();tts=contents/'tts';tts.mkdir()
    for name in phonon_spec['files']:
        destination=tts/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(phonon_folder/name,destination)
    (tts/'phonon-model.json').write_text(json.dumps(phonon_spec,ensure_ascii=False,indent=2),encoding='utf-8')
    # The loader is redistributed privately. Drivers and Vulkan SDK are never
    # installed or replaced on the user's PC by this optional pack.
    loader = ROOT/'toolchain/vulkan-sdk-1.4.363.0/Bin/vulkan-1.dll'
    if not loader.is_file():
        loader = ROOT/'toolchain/vulkan-runtime/VulkanRT-X64-1.4.363.0-Components/x64/vulkan-1.dll'
    if not loader.is_file():
        raise ValueError('Verified Vulkan loader required for the standalone voice pack.')
    shutil.copyfile(loader, native/'vulkan-1.dll')
    licenses = contents/'licenses'
    licenses.mkdir()
    shutil.copyfile(source/'LICENSE', licenses/'whisper-LICENSE.txt')
    shutil.copyfile(ROOT/'client-voice/max-licenses/GGML-LICENSE.txt', licenses/'ggml-LICENSE.txt')
    shutil.copyfile(phonon_folder/'README.md',licenses/'Phonon-40m-French-MODEL-CARD.md')
    (licenses/'Phonon-NOTICE.txt').write_text(
        'Phonon 0.4.1 runtime: https://github.com/gradium-ai/xn-ptts (MIT OR Apache-2.0).\n'
        'French model: https://huggingface.co/gradium/phonon-40m-fr (CC-BY-NC-4.0).\n'
        'French Tiphaine voice: https://huggingface.co/gradium/phonon-voices (Apache-2.0).\n'
        'Pinned revisions and attribution are provided in tts/phonon-model.json and this model card.\n',encoding='utf-8')
    loader_license = ROOT/'toolchain/vulkan-runtime/VulkanRT-X64-1.4.363.0-Components/VulkanRT-License.txt'
    if not loader_license.is_file():
        raise ValueError('Vulkan loader license required.')
    shutil.copyfile(loader_license, licenses/'Vulkan-Loader-LICENSE.txt')
    # Keep the original pin and local build-only Windows path quoting patch.
    shutil.copyfile(ROOT/'client-voice/whisper-vulkan-windows-spaces.patch', licenses/'ggml-windows-spaces.patch')
    (licenses/'SOURCES.json').write_text(json.dumps(expected, indent=2), encoding='utf-8')
    output.mkdir(parents=True, exist_ok=True)
    inventory = []
    with zipfile.ZipFile(output/'runtime.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(contents.rglob('*')):
            if path.is_file():
                name = path.relative_to(contents).as_posix()
                inventory.append({'name': name, 'bytes': path.stat().st_size, 'sha256': digest(path)})
                archive.write(path, name)
    runtime = output/'runtime.zip'
    asr = [item for item in json.loads((ROOT/'client-voice/conversation-models.json').read_text(encoding='utf-8'))['files'] if item['name'] in ('silero-vad.onnx','smart-turn.onnx')]
    models = [{**item, 'name': 'asr/'+item['name']} for item in asr] + expected['models']
    revision = 'vocal-rt-'+hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()[:16]
    catalogue = {'format': 2, 'runtime_api':6, 'gpu_engine':'asr', 'revision': revision, 'engine': expected['engine'],
                 'source_commit': expected['commit'], 'upstream_reference': expected['upstream_reference'],
                 'runtime': {'name': 'runtime.zip', 'bytes': runtime.stat().st_size, 'sha256': digest(runtime), 'files': inventory},
                 'models': models}
    if sign_home:
        sys.path[:0] = [str(ROOT/'client-qwen'), str(ROOT/'lanceur')]
        from signing import private
        from max_installation import canonical, verify_catalogue
        key = private(sign_home, create=False)
        catalogue['signature'] = base64.b64encode(key.sign(canonical(catalogue))).decode()
        from signing import public
        verify_catalogue(catalogue, public(sign_home, create=False))
    (output/('release.json' if sign_home else 'release-unsigned.json')).write_text(json.dumps(catalogue, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'revision': revision, 'runtime_bytes': runtime.stat().st_size,
                      'models_bytes': sum(x['bytes'] for x in models), 'installed_runtime_bytes': sum(x['bytes'] for x in inventory),
                      'signed': bool(sign_home)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'toolchain/voice-max-release')
    parser.add_argument('--sign-home', type=Path)
    args = parser.parse_args()
    package(args.output.resolve(), args.sign_home)
