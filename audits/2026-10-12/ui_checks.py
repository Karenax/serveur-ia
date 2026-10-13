"""Syntax and existing headless client UI tests with separate audit outputs."""
import json
import os
from pathlib import Path
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
NODE = "node"
env = dict(os.environ, PLAYWRIGHT_MODULE="C:/Users/karen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright",
           UI_PROOF_DIRECTORY=str(OUT / "ui"), PYTHON_EXE=str(ROOT / "Strata-src/.venv/Scripts/python.exe"), PYTHONUTF8="1")
records = json.loads((OUT / "inventory.json").read_text(encoding="utf-8"))["sources"]
summary = {"syntax": [], "tests": []}
for record in records:
    path = ROOT / record["path"]
    if not record["active"] or record["vendor"]:
        continue
    sources = []
    if path.suffix in (".js", ".cjs", ".mjs"):
        sources.append(path)
    elif path.suffix == ".html":
        for index, code in enumerate(re.findall(r"<script\b[^>]*>(.*?)</script>", path.read_text(encoding="utf-8"), re.S | re.I)):
            if code.strip():
                target = OUT / "ui" / (path.parent.name + "-" + path.name + "-" + str(index) + ".js")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(code.replace("__CONFIG__", "{}"), encoding="utf-8")
                sources.append(target)
    for source in sources:
        result = subprocess.run([NODE, "--check", str(source)], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        summary["syntax"].append({"source": record["path"], "exit": result.returncode, "error": result.stderr})
tests = list((ROOT / "client-qwen").glob("test_*.cjs")) + list((ROOT / "lanceur").glob("test_*.js"))
for test in sorted(tests):
    try:
        result = subprocess.run([NODE, str(test)], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        (OUT / (test.stem + ".log")).write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        summary["tests"].append({"test": test.relative_to(ROOT).as_posix(), "exit": result.returncode})
        print(test.name, "exit", result.returncode, flush=True)
    except subprocess.TimeoutExpired as exc:
        summary["tests"].append({"test": test.relative_to(ROOT).as_posix(), "error": "timeout"})
        print(test.name, "timeout", flush=True)
    (OUT / "ui-results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("Syntax checks:", len(summary["syntax"]), "failures:", [r for r in summary["syntax"] if r["exit"]])
