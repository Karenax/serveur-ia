"""Keep dependency license texts alongside the packaged conversation worker."""
import importlib.metadata
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent.parent
TARGET=ROOT/'client-qwen/voice/licenses/conversation'
for package in ('sherpa-onnx','sherpa-onnx-core','onnxruntime','numpy'):
    distribution=importlib.metadata.distribution(package)
    target=TARGET/package;target.mkdir(parents=True,exist_ok=True)
    found=False
    for name in distribution.files or []:
        if any(part.lower().startswith(('license','copying','notice')) for part in name.parts):
            path=Path(distribution.locate_file(name))
            if path.is_file():shutil.copyfile(path,target/path.name);found=True
    if not found and package=='sherpa-onnx-core':
        for path in (TARGET/'sherpa-onnx').glob('*'):
            if path.name!='VERSION.txt':shutil.copyfile(path,target/path.name);found=True
    if not found:raise ValueError('License text not found for '+package)
    (target/'VERSION.txt').write_text(package+' '+distribution.version+'\n',encoding='utf-8')
