import json,statistics
from pathlib import Path
root=Path(__file__).resolve().parent
rows=[]
for folder in sorted((root/'comparatifs').glob('huihui-*')):
 p=folder/'synthese.json'
 if not p.exists():continue
 summary=json.loads(p.read_text(encoding='utf-8-sig'))
 measures=json.loads((folder/'mesures.json').read_text(encoding='utf-8-sig'))
 ram=None
 if (folder/'ram-observee.json').exists():ram=json.loads((folder/'ram-observee.json').read_text(encoding='utf-8-sig')).get('ram_observed_gib')
 elif (folder/'ram.json').exists():
  samples=json.loads((folder/'ram.json').read_text(encoding='utf-8-sig'));ram=max(s['ram_gib'] for s in samples)
 row=dict(archive=str(folder),mode=summary[0]['mode'],ram_gib=ram)
 for case in ('ciel','fibonacci'):
  r=[v['predicted_per_second'] for v in measures if v['case']==case]
  row[case]=dict(median=statistics.median(r),min=min(r),max=max(r))
 rows.append(row)
(root/'RESULTATS-HUIHUI.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
lines=['Huihui Qwen3.8 27B abliterated Q4_K_M - essais du 3 octobre 2026',
 'Model: D:\\modèle\\huihui-ai\\Huihui-Qwen3.8-27B-abliterated-GGUF\\Huihui-Qwen3.8-27B-abliterated-UD-DW-Q4_K_M.gguf',
 'Deux P100 16 Gio, contexte 4096, une conversation, température 0, seed 42, thinking/cache prompt désactivés, 256 tokens.',
 'Les débits excluent le chargement et le traitement du prompt. Médianes de deux réponses après chauffe.',
 'RAM = working set observé, incluant des pages du GGUF. Ce ne sont pas tous des pics mesurés.',
 'Les dernières séries chaudes ont un ralentissement thermique confirmé à environ 79 C. Leur classement mélange configuration et température.',
 'La confirmation finale attend <=68 C avant chaque réponse mesurée : débit maximal avec pauses de refroidissement, pas débit continu garanti.',
 'Le mode row échoue (split buffers non pris en charge). Le binaire llama-b11344 échoue en mode layer (invalid device function sur P100).',
 'Le mode tensor Café fonctionne avec le repli meta-backend butterfly; sampler sur CPU.',
 'Le fichier IQ3 voisin indique une provenance GSQ-RCO différente et n’a pas été substitué au Huihui abliterated.',
 '', 'Mode | ciel tok/s | Fibonacci tok/s | RAM Gio observée']
for r in rows:
 lines.append(f"{r['mode']} | {r['ciel']['median']:.2f} ({r['ciel']['min']:.2f}-{r['ciel']['max']:.2f}) | {r['fibonacci']['median']:.2f} ({r['fibonacci']['min']:.2f}-{r['fibonacci']['max']:.2f}) | {r['ram_gib'] if r['ram_gib'] is not None else 'non relevée'}")
lines+=['','Lancer : Start-Huihui-Rapide-P100.ps1. Arrêter : Stop-Huihui-P100.ps1.', 'Interface : http://127.0.0.1:8080. Télémétrie thermique : huihui-gpu-thermique.csv.', 'Archives détaillées et paramètres effectifs : voir RESULTATS-HUIHUI.json.']
(root/'RESULTATS-HUIHUI.txt').write_text('\n'.join(lines)+'\n',encoding='utf8')
print('\n'.join(lines[-len(rows)-5:]))

