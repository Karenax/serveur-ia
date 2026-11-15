"""Install public local models; no meeting audio is sent to a remote service."""
import argparse
import hashlib
import json
import tarfile
import urllib.request
from pathlib import Path

from faster_whisper import download_model

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/"


def fetch(url, target):
    if not target.is_file():
        temporary = target.with_suffix(target.suffix + ".part")
        urllib.request.urlretrieve(url, temporary)
        temporary.replace(target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=ROOT / ".models" / "audio")
    parser.add_argument("--model", choices=["base", "small", "medium", "large-v3-turbo"], default="small")
    args = parser.parse_args()
    root = args.directory.resolve()
    root.mkdir(parents=True, exist_ok=True)
    print("Téléchargement Whisper " + args.model, flush=True)
    whisper = root / ("whisper-" + args.model)
    download_model(args.model, output_dir=str(whisper))
    archive = root / "segmentation.tar.bz2"
    fetch(RELEASE + "speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2", archive)
    segmentation = root / "segmentation.onnx"
    if not segmentation.is_file():
        with tarfile.open(archive) as package:
            member = next(m for m in package.getmembers() if m.name.endswith("/model.int8.onnx"))
            segmentation.write_bytes(package.extractfile(member).read())
    embedding = root / "speaker-embedding.onnx"
    fetch(RELEASE + "speaker-recongition-models/wespeaker_en_voxceleb_resnet34.onnx", embedding)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [segmentation, embedding]}
    config = {"whisper": str(whisper), "segmentation": str(segmentation),
              "embedding": str(embedding), "model": args.model, "sha256": files}
    (root / "models.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print("Modèles audio prêts : " + str(root), flush=True)


if __name__ == "__main__":
    main()
