"""Collecte de métadonnées publiques uniquement, sans télécharger les poids."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
HEADERS = {"User-Agent": "Kiara-DeepSeek-feasibility-study"}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as response:
        data = response.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("Réponse trop volumineuse pour une collecte de métadonnées")
    return data


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    source_dir = ROOT / "sources"
    source_dir.mkdir(exist_ok=True)
    release = json.loads(fetch("https://api.github.com/repos/Niko1221/Strata/releases/latest"))
    head = json.loads(fetch("https://api.github.com/repos/Niko1221/Strata/commits/main"))
    sha = head["sha"]
    paths = ["docs/DEEPSEEK41.md", "docs/OLDER_GPUS.md", "CMakeLists.txt",
             "src/dsv41/vendor/exl3_legacy.cu", "src/dsv41/ds4_kernels.cu",
             "src/dsv41/ds4_model.cu", "strata_control/dsv41_engine.py",
             "strata_control/dsv41_fit.py", "tools/dsv41/pack_gguf.py"]
    jobs = {"strata-" + path.replace("/", "_"):
            f"https://raw.githubusercontent.com/Niko1221/Strata/{sha}/{path}" for path in paths}
    models = ["unsloth/DeepSeek-V4-Flash-0731-GGUF",
              "unsloth/DeepSeek-R1-Distill-Qwen-32B-GGUF",
              "unsloth/DeepSeek-R1-Distill-Llama-70B-GGUF",
              "ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF"]
    for model in models:
        jobs["hf-" + model.split("/")[1] + ".json"] = f"https://huggingface.co/api/models/{model}?blobs=true"
    manifest = {"collected_at_utc": datetime.now(timezone.utc).isoformat(),
                "strata_head": sha, "strata_head_date": head["commit"]["committer"]["date"],
                "release": {key: release.get(key) for key in
                            ["tag_name", "published_at", "updated_at", "html_url"]},
                "deepseek_packages": [{"name": a["name"], "size": a["size"],
                                       "url": a["browser_download_url"]}
                                      for a in release["assets"] if "dsv41" in a["name"]],
                "sources": [], "model_sizes": {}}
    (source_dir / "strata-release.json").write_text(json.dumps(release, ensure_ascii=False, indent=2), encoding="utf-8")

    def collect(item):
        name, url = item
        try:
            data = fetch(url)
            (source_dir / name).write_bytes(data)
            return name, url, data, None
        except Exception as exc:
            return name, url, None, str(exc)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, url, data, error in pool.map(collect, jobs.items()):
            entry = {"file": name, "url": url}
            if error:
                entry["error"] = error
            else:
                entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                if name.startswith("hf-"):
                    model = json.loads(data)
                    groups = {}
                    for file in model.get("siblings", []):
                        path = file["rfilename"]
                        if not path.endswith(".gguf"):
                            continue
                        group = path.split("/")[0] if "/" in path else re.sub(r"-\d{5}-of-\d{5}\.gguf$", "", path)
                        size = file.get("size", file.get("lfs", {}).get("size", 0))
                        target = groups.setdefault(group, {"bytes": 0, "files": 0})
                        target["bytes"] += size
                        target["files"] += 1
                    for group in groups.values():
                        group.update(GB=round(group["bytes"] / 1e9, 3), GiB=round(group["bytes"] / 2**30, 3))
                    manifest["model_sizes"][model["id"]] = {"revision": model["sha"], "groups": groups}
            manifest["sources"].append(entry)
    (ROOT / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
