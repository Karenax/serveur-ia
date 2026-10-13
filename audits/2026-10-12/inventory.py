"""Reproducible, read-only inventory of tracked first-party project sources."""
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ACTIVE = {"lanceur", "client-qwen", "client-android", "client-voice"}
EXTENSIONS = {".py", ".js", ".cjs", ".mjs", ".java", ".cpp", ".cu", ".h", ".ps1", ".cmd", ".html", ".css", ".gradle"}


def inventory():
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    records, trees, errors, functions = [], {}, [], []
    for name in filter(None, tracked):
        path = ROOT / name
        if not path.is_file():
            continue
        active = name.split("/")[0] in ACTIVE
        source = path.suffix.lower() in EXTENSIONS
        if not (active and source or "/" not in name and source):
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig", errors="replace")
        record = {"path": name, "bytes": len(raw), "lines": len(text.splitlines()),
                  "sha256": hashlib.sha256(raw).hexdigest(), "active": active,
                  "test": path.name.startswith("test") or "/tests/" in name or "/androidTest/" in name,
                  "vendor": "/vendor/" in name,
                  "generated": name == "client-android/app/src/main/assets/android-chat.html"}
        records.append(record)
        if path.suffix == ".py":
            try:
                tree = ast.parse(text, filename=name)
                compile(tree, name, "exec")
                trees[name] = tree
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append({"file": name, "name": node.name, "line": node.lineno,
                                          "end": node.end_lineno, "lines": node.end_lineno - node.lineno + 1})
            except (SyntaxError, ValueError) as exc:
                errors.append({"file": name, "error": str(exc)})
    duplicate_files = defaultdict(list)
    for record in records:
        duplicate_files[record["sha256"]].append(record["path"])
    result = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
              "tracked_files": len(list(filter(None, tracked))), "sources": records,
              "syntax_errors": errors,
              "largest_functions": sorted(functions, key=lambda r: r["lines"], reverse=True)[:40],
              "identical_files": [paths for paths in duplicate_files.values() if len(paths) > 1],
              "summary": {"files": len(records), "lines": sum(r["lines"] for r in records),
                          "active_non_test_non_vendor_lines": sum(r["lines"] for r in records if r["active"] and not r["test"] and not r["vendor"] and not r["generated"]),
                          "python_files": len(trees), "extensions": dict(Counter(Path(r["path"]).suffix for r in records))}}
    (OUT / "inventory.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"commit": result["commit"], "summary": result["summary"],
                      "syntax_errors": result["syntax_errors"], "largest_functions": result["largest_functions"][:12],
                      "identical_files": result["identical_files"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    inventory()
