"""Validate artifacts and configuration without loading the model or starting a server."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source-officielle"
sys.path.insert(0, str(SOURCE))
from serve.server import child_env, engine_args
from serve.frontend import ChatTemplate
sys.path.insert(0, str(SOURCE / "tools"))
import strata_tokenizer as tokenizer_module

expected = "646ded0105aa5213a75e16621d559670d09dac26b5c720c9fd651ca83bdf14ec"
archive = ROOT / "telechargements/strata-windows-x64-cuda12.zip"
with archive.open("rb") as stream:
    if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
        raise SystemExit("Empreinte du paquet officiel incorrecte.")
build = json.loads((ROOT / "engine-cuda12/BUILD.json").read_text())
assert build["version"] == "0.1.41" and 60 in build["archs"] and build["toolkit"] == 12
results = []
for profile in ("reference", "trim", "pipeline", "benchmark", "fp16", "cpu-prefill", "cpu-court", "cpu-court-pin", "cpu-court-pin-4096"):
    cfg = json.loads((ROOT / f"config-{profile}.json").read_text(encoding="utf-8-sig"))
    args = engine_args(cfg)
    assert cfg["host"] == "127.0.0.1" and cfg["port"] == 8081
    assert Path(cfg["exe"]).resolve() == ROOT / "engine-cuda12/strata.exe"
    assert Path(cfg["cwd"]).resolve() == SOURCE
    assert ("--resident-cpu-experts" in args or "--resident-experts" in args) and "--layer-split" in args
    assert not any(k.startswith("STRATA_P100") for k in cfg["env"])
    assert "before_load" not in cfg and not cfg.get("lazy_load")
    for flag in ("--pack", "--native", "--mtp", "--expert-profile", "--ple-gguf"):
        assert Path(args[args.index(flag) + 1]).exists(), flag
    tokpath = Path(cfg["tokenizer"])
    vocab = json.loads((tokpath / "vocab.json").read_text(encoding="utf-8"))
    tokens = [None] * len(vocab)
    for token, index in vocab.items():
        tokens[index] = token
    types = json.loads((tokpath / "token_type.json").read_text())
    tok = tokenizer_module.Tokenizer(tokens, (tokpath / "merges.txt").read_text(encoding="utf-8").split("\n"), types)
    encoded = tok.encode("Bonjour, test du moteur hybride.")
    assert encoded and tok.decode(encoded) == "Bonjour, test du moteur hybride."
    ChatTemplate(tokpath / "chat_template.jinja")
    version = subprocess.run([cfg["exe"], "--version"], env=child_env(cfg), capture_output=True, text=True, timeout=20)
    if version.returncode != 0 or "0.1.41" not in version.stdout + version.stderr:
        raise SystemExit(f"Moteur non executable ({version.returncode}): {version.stdout} {version.stderr}")
    results.append({"profile": profile, "version": version.stdout.strip(), "tokenizer": "ok", "paths": "ok"})
output = {"profiles": results, "model_loaded": False, "gpu_inference_tested": False}
(ROOT / "validation/preparation.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
print(f"0.1.41 CUDA12/sm60 : paquet, moteur, tokenizer et {len(results)} profils valides ; aucun modele charge.")
