"""Repository hygiene, dependency drift and redacted secret candidates."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
patterns = {
    "fred_token": re.compile(r"\bqwen_[0-9a-f]{16}_[A-Za-z0-9_-]{30,256}\b"),
    "provider_token": re.compile(r"\b(?:sk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{28,256}|hf_[A-Za-z0-9]{28,256}|gh[pousr]_[A-Za-z0-9]{30,256})\b"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
candidates, groups, total_bytes = [], {}, 0
for name in filter(None, files):
    path = ROOT / name
    raw = path.read_bytes()
    total_bytes += len(raw)
    groups.setdefault(name.split("/")[0] if "/" in name else "(racine)", {"files": 0, "bytes": 0})
    group = groups[name.split("/")[0] if "/" in name else "(racine)"]
    group["files"] += 1; group["bytes"] += len(raw)
    if path.suffix.lower() not in {".py", ".md", ".txt", ".json", ".js", ".html", ".cjs", ".mjs", ".yaml", ".yml", ".ps1", ".cmd", ".patch"} or path.name in {"vocab.json", "merges.txt", "token_type.json"}:
        continue
    text = raw.decode("utf-8-sig", errors="replace")
    for kind, pattern in patterns.items():
        for match in pattern.finditer(text):
            # Only location and a non-reversible fingerprint, never token values.
            candidates.append({"file": name, "line": text.count("\n", 0, match.start()) + 1,
                "kind": kind, "sha256": hashlib.sha256(match.group().encode()).hexdigest()[:16]})
print("Tracked scan complete:", len(files) - 1, "files; redacted candidates:", len(candidates), flush=True)
dependencies = []
for item in json.loads((ROOT / "dependances/moteurs.json").read_text(encoding="utf-8")):
    repo = ROOT / item["directory"]
    if not (repo / ".git").exists():
        dependencies.append({"directory": item["directory"], "available": False}); continue
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], timeout=30).decode().strip()
    patch = subprocess.check_output(["git", "-C", str(repo), "diff", "--binary", item["patch_base"], "--"], stderr=subprocess.DEVNULL, timeout=60)
    stored = (ROOT / "dependances" / item["patch"]).read_bytes() if item.get("patch") else b""
    dependencies.append({"directory": item["directory"], "available": True, "head_matches": head == item["head"],
        "patch_matches": patch == stored, "live_patch_bytes": len(patch), "stored_patch_bytes": len(stored)})
result = {"tracked_files": len(list(filter(None, files))), "tracked_bytes": total_bytes,
          "groups": groups, "secret_candidates": candidates, "dependencies": dependencies}
(OUT / "repo-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
