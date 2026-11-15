"""Build a deterministic, unsigned ZIP from the current extension sources."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "extensions" / "infomaniak-auto-local"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    files = ["manifest.json", "core.js", "background.js", "content.js"]
    output = args.output.resolve()
    if output.exists():
        parser.error("La destination doit être nouvelle")
    output.parent.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            content = (root / name).read_bytes()
            hashes[name] = hashlib.sha256(content).hexdigest()
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    result = {"version": manifest["version"], "signed": False, "files": hashes,
              "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix(output.suffix + ".json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
