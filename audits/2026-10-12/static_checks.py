"""Run audit tools against tracked first-party Python, excluding runtime caches."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
records = json.loads((OUT / "inventory.json").read_text(encoding="utf-8"))["sources"]
files = [r["path"] for r in records if r["active"] and not r["test"] and not r["vendor"] and r["path"].endswith(".py")]
for tool, arguments, target in [
    ("ruff", ["check", "--select", "F,B,PLE", "--output-format", "json", "--no-cache"], "ruff.json"),
    ("bandit", ["-q", "-f", "json"], "bandit.json"),
    ("vulture", ["--min-confidence", "80"], "vulture.txt"),
]:
    result = subprocess.run([sys.executable, "-m", tool, *arguments, *files], cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace")
    (OUT / target).write_text(result.stdout, encoding="utf-8")
    (OUT / (tool + "-stderr.txt")).write_text(result.stderr, encoding="utf-8")
    print(tool, "exit", result.returncode, "files", len(files), flush=True)
ruff = json.loads((OUT / "ruff.json").read_text(encoding="utf-8"))
bandit = json.loads((OUT / "bandit.json").read_text(encoding="utf-8"))
print("Ruff", len(ruff), dict(Counter(r["code"] for r in ruff)))
print("Bandit", len(bandit["results"]), dict(Counter(r["issue_severity"] for r in bandit["results"])))
print("Vulture", (OUT / "vulture.txt").read_text(encoding="utf-8"))
