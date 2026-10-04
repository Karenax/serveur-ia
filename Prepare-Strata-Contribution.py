from pathlib import Path
import json
import shutil

root = Path(__file__).resolve().parent
repo = root / 'Strata-src'
dest = repo / 'bench/results/2026-10-02-p100-resident-hybrid'
archive = root / 'comparatifs/2026-10-02-strata-hybride-p100'
protocol = json.loads((root / 'protocole-comparatif-q4.json').read_text(encoding='utf-8-sig'))
protocol = {k: v for k, v in protocol.items() if k not in ('future_prompt_suggestion', 'note')}

def write(name, value):
    (dest / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

write('protocol.json', protocol)
write('runs.json', json.loads((archive / 'essai-20261002-194111/resultats.json').read_text(encoding='utf-8-sig')))
write('startup-validation.json', json.loads((archive / 'validation-20261002-200515/resultats.json').read_text(encoding='utf-8-sig')))
summary = json.loads((archive / 'synthese.json').read_text(encoding='utf-8-sig'))
summary.pop('run', None)
write('summary.json', summary)
cfg = json.loads((root / 'strata-q4-p100-hybride.json').read_text(encoding='utf-8-sig'))
cfg.update(exe='./build-p100/strata.exe', cwd='.', lib_dirs=['<CUDA 12 toolkit>/bin'],
           tokenizer='./packs/ud-q4_k_xl/tokenizer', log='./strata-p100-engine.log')
replacements = {
    'D:/Serveur IA/strata-data/q4-local': './packs/ud-q4_k_xl',
    'D:/Serveur IA/strata-data/model-q4/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf': './models/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf',
    'D:/Serveur IA/Strata-src/data/expert-profile.bin': './data/expert-profile.bin',
    'D:/Serveur IA/strata-data/mtp-local-rt': './mtp/rt',
}
cfg['args'] = [replacements.get(v, v) for v in cfg['args']]
cfg['env'].pop('CUDA_VISIBLE_DEVICES', None)
cfg['env'].pop('STRATA_P100_DIAGNOSTIC_SYNC_FILE', None)
write('config.example.json', cfg)

# Port the tested adapter without workstation paths. Keep all quantization and tensor mappings.
source = (root / 'Convert-MTP-Strata.py').read_text(encoding='utf-8-sig')
source = source.replace("ROOT = Path(__file__).resolve().parent\nsys.path.insert(0, str(ROOT / 'Strata-src' / 'tools'))\n", '')
source = source.replace('import os\n', '').replace('import sys\n', '')
source = source.replace("out.mkdir(parents=True, exist_ok=True)", "out.mkdir(parents=True, exist_ok=False)")
source = source.replace("'source': a.gguf", "'source_name': Path(a.gguf).name")
source = source.replace("Norms in this GGUF already include\nthe Gemma +1 (see cafe-llama-src/conversion/qwen*.py), so preserve them.",
    "This adapter only accepts a blk.48 Q8 draft whose norms already include\nthe Gemma +1 offset. It preserves those norms; it does not add the offset.")
source = source.replace("    ap.add_argument('--out', required=True)",
    "    ap.add_argument('--out', required=True)\n    ap.add_argument('--norms-already-offset', action='store_true',\n                    help='Confirm that this GGUF already includes the Gemma +1 norm offset')")
source = source.replace("    a = ap.parse_args()", "    a = ap.parse_args()\n    if not a.norms_already_offset:\n        ap.error('This adapter requires --norms-already-offset; use mtp_rt.py for raw-norm drafts')")
source = source.replace("    ts = {t.name.removeprefix('blk.48.'): t for t in reader.tensors}",
    "    ts = {t.name.removeprefix('blk.48.'): t for t in reader.tensors}\n    for name in ('ffn_gate_exps.weight', 'ffn_up_exps.weight', 'ffn_down_exps.weight'):\n        if name not in ts or int(ts[name].tensor_type) != 8:\n            raise ValueError('Expected blk.48 Q8_0 expert tensors: ' + name)")
(repo / 'tools/mtp_q8_runtime.py').write_text(source, encoding='utf-8')
print('Prepared protocol, 16 measured runs, 2 startup validations, summary, example configuration and portable draft adapter')
