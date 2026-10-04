"""Compte rendu des mesures validées ; n'invente pas de score pour un échec."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / 'comparatifs' / '2026-10-02-strata-q4-p100'
with (ROOT / 'comparatifs' / 'comparatif-q4-p100.csv').open(encoding='utf-8-sig', newline='') as stream:
    rows = list(csv.DictReader(stream))
resources = json.loads((ROOT / 'comparatifs' / 'ressources-q4-p100.json').read_text(encoding='utf-8'))
protocol = json.loads((ARCHIVE / 'protocole.json').read_text(encoding='utf-8-sig'))
strict = [r for r in rows if r['mode'] == 'strata-mtp-gpu-seul']
assert len(strict) == 2, 'Les deux mesures GPU sont requises.'
config = json.loads((ARCHIVE / 'configuration-tests.json').read_text(encoding='utf-8-sig'))
assert config['diagnostic_sync'] is False, 'Synchronisation diagnostique restée active pendant la mesure.'
for n in (1, 2):
    log = (ARCHIVE / f'engine-strata-mtp-test-{n}.log').read_text(encoding='utf-8-sig')
    assert 'decode expert compute: 0 CPU jobs,' in log
    assert '0 blob reads from the file' in log
    request = json.loads((ARCHIVE / f'requete-strata-mtp-test-{n}.json').read_text(encoding='utf-8-sig'))
    assert request['messages'][0]['content'] == protocol['prompts'][n-1]
    assert request['temperature'] == 0 and request['seed'] == 42
    assert request['max_tokens'] == 256 and request['cache_prompt'] is False
    assert request['chat_template_kwargs']['enable_thinking'] is False

def rate(mode, test):
    return float(next(r['generation_tps'] for r in rows if r['mode'] == mode and int(float(r['test'])) == test))

stats = resources['strata-mtp-gpu-seul']
lines = [
    'Comparatif Q4 sur deux Tesla P100 — 2 octobre 2026',
    '',
    'Strata adapté pour les P100 est validé sur les deux requêtes de ce protocole.',
    'Serveur local : http://127.0.0.1:8080/ ; API : http://127.0.0.1:8080/v1',
    'Alias : qwen3.8-flash-next ; contexte 4096 ; une requête à la fois.',
    '',
    'Matériel : Threadripper PRO 3955WX (16 cœurs/32 threads), environ 128 Gio de RAM,',
    'deux Tesla P100 PCIe 16 Gio ; Quadro P2200 réservée à l’affichage.',
    'CUDA 12.4, code compilé pour sm_60 ; pilote NVIDIA 528.89.',
    'Modèle : les quatre shards Qwen3.8-Flash-Next-UD-Q4_K_XL existants, 103,69 Gio.',
    '48 couches, 512 experts par couche, 10 experts actifs par token.',
    '',
    'Protocole commun :',
    '1. ' + protocol['prompts'][0],
    '2. ' + protocol['prompts'][1],
    'Température 0, seed 42, réflexion désactivée, cache de prompt désactivé,',
    'limite 256 tokens de sortie. Chaque essai a effectivement produit 256 tokens.',
    'Les mêmes textes figurent dans le script Café archivé et les requêtes Strata.',
    'La poésie sur les fourmis est réservée à une prochaine série commune.',
    '',
    'Débit de génération (tokens/s ; temps de génération du moteur, hors prompt) :',
    '                                 Ciel          Fibonacci',
]
for mode, title in (
    ('cafe-sans-mtp', 'Café / llama.cpp sans MTP'),
    ('cafe-mtp', 'Café / llama.cpp avec MTP'),
    ('strata-mtp-gpu-seul', 'Strata avec MTP, experts GPU'),
):
    lines.append(f'{title:31s} {rate(mode, 1):9.2f}      {rate(mode, 2):9.2f}')
lines += ['', 'Écart Strata par rapport à Café avec MTP :']
for n, title in ((1, 'Ciel'), (2, 'Fibonacci')):
    delta = (rate('strata-mtp-gpu-seul', n) / rate('cafe-mtp', n) - 1) * 100
    lines.append(f'{title} : {delta:+.1f} %.')
lines += ['', 'Mesures Strata par requête :']
for row in strict:
    lines.append(
        f"Test {int(float(row['test']))} : {float(row['elapsed_seconds']):.2f} s au total, "
        f"prompt {float(row['prompt_tps']):.1f} tokens/s, MTP "
        f"{int(float(row['draft_accepted']))}/{int(float(row['draft_tokens']))} "
        f"({float(row['draft_acceptance'])*100:.1f} %) accepté."
    )
lines += [
    '',
    'Répartition mémoire et calcul :',
    f"Pics VRAM : {stats['vram_peak_mib']['1']:.0f} et {stats['vram_peak_mib']['2']:.0f} Mio.",
    f"RAM du processus moteur : pic {stats['ram_peak_gib']:.2f} Gio.",
    'Table PLE/n-gram entière : 26,82 Gio copiés en RAM et verrouillés.',
    'Experts : environ 16,02 Gio de cache VRAM, complément 55,71 Gio de RAM épinglée.',
    'Les experts absents du cache VRAM transitent par PCIe avant calcul sur GPU.',
    'Les journaux des deux requêtes confirment 0 travail de calcul d’expert sur CPU',
    'et 0 lecture de blob d’expert depuis les fichiers pendant les réponses.',
    'Le taux de cache affiché à 100 % exclut les experts transférés par PCIe :',
    'il ne signifie pas que tous les experts utilisés résident en VRAM.',
    'Le mode strict refuse la requête si un calcul d’expert CPU devient nécessaire.',
    'Le CPU continue à préparer les entrées, chercher les n-grams et piloter CUDA.',
    f"CPU moteur moyen mesuré : {stats['cpu_equivalent_cores']:.2f} cœur(s) équivalent(s).",
    f"Pic lecture I/O du processus : {stats['process_io_read_peak_bytes_s']:.0f} octets/s.",
    f"Pic lecture physique du disque D: : {stats['disk_d_read_peak_bytes_s']:.0f} octets/s.",
    'Le compteur physique porte sur tout le disque : une activité Windows éventuelle',
    'n’est pas attribuable au modèle par ce compteur seul. La mesure est échantillonnée.',
    '',
    'Utilisation des deux GPU :',
    f"Moyennes sur les réponses : {stats['gpu_mean_util_pct']['1']:.1f} % et {stats['gpu_mean_util_pct']['2']:.1f} %.",
    'Les couches 0–23 passent sur le premier P100, puis 24–47 sur le second.',
    'Une réponse séquentielle les fait donc principalement travailler à tour de rôle.',
    'Une somme proche de 100 % n’est pas une limite de mesure imposée à deux GPU.',
    'Le partage actuel des couches ne maintient pas les deux cartes à 100 % ensemble.',
    '',
    'Adaptations et limites du comparatif :',
    'Strata source d9ab8435f654c368c586340d490915f6addf56a3 ; ggml épinglé',
    'à 3cf03257f219afbe7334045ff7c6a06ac68c627d ; Café source',
    '0ae77ef4914fcd6e78e0b13ab157ff3acccc9edf.',
    'Adaptations Windows/Pascal : mémoire RAM verrouillée pour PLE, lecture initiale',
    'séquentielle du complément d’experts, métadonnées locales des shards, GEMM FP16',
    'sur GPU à la place du BF16 matériel, buffers PCIe de 64 experts, garde anti CPU.',
    'Une requête initiale de 1 token utilise une synchronisation de diagnostic ;',
    'elle est désactivée avant les mesures. C’est un contournement d’initialisation',
    'de cette version expérimentale, pas une validation générale de toutes les charges.',
    'Le suivi des en-têtes C++ a aussi été corrigé pour Visual Studio en français.',
    'Les tests numériques natifs, préfill FP16 et MMQ ont passé sur les deux P100 ;',
    'les conversions de déquantification comparées à ggml sont identiques bit à bit.',
    'Les poids des grands experts Q4/Q5/Q8 restent ceux des GGUF originaux.',
    'Le pack Strata arrondit certains petits tenseurs de compatibilité en BF16',
    '(195 conversions avec arrondi ; détails et erreurs dans conversions.json).',
    'Le draft MTP Strata est converti du Q8_0 local vers Q2_0 ; Café utilise le Q8_0.',
    'Strata combine MTP et recherche de suffixes, fenêtre de vérification jusqu’à',
    '5 tokens, seuil spec-min-p 0,5, cache d’experts statique. Ces différences',
    'empêchent d’attribuer tout écart de vitesse au seul logiciel serveur.',
    'Deux prompts, une mesure par mode : ils décrivent ces essais, pas toutes les tâches.',
    'La limite 256 tokens coupe les réponses ; ce n’est pas un test de 200 mots.',
    'Les sorties brutes permettent de contrôler la qualité et les différences.',
    'Inspection des deux sorties : français cohérent ; l’explication du ciel est',
    'coupée avant le coucher du soleil ; la fonction Fibonacci et son exemple',
    '[0, 1, 1, 2, 3, 5, 8, 13] sont complets, mais le commentaire final est tronqué.',
    '',
    'Historique conservé :',
    'L’essai Strata staging16 achevé utilisait aussi le CPU : 8,91 tokens/s pour',
    'le ciel, 11,23 pour Fibonacci. Il reste séparé dans essai-hybride-staging16.',
    'Les échecs CUDA et refus CPU ne figurent pas comme scores de performance.',
    'Une première reconstruction n’avait pas recompilé verify.cpp : malgré le nom',
    'staging64 de cet ancien binaire, son buffer effectif restait à 16. Le binaire',
    'final strata-p100-gpu-seul.exe utilise bien les 64 emplacements.',
    '',
    'Utilisation :',
    'Démarrer : powershell -ExecutionPolicy Bypass -File "D:\\Serveur IA\\Start-Strata-P100.ps1"',
    'Arrêter : powershell -ExecutionPolicy Bypass -File "D:\\Serveur IA\\Stop-Strata-P100.ps1"',
    'Les lanceurs Start-Qwen.ps1 / Stop-Qwen.ps1 correspondent encore à Café.',
    'Arrêter le moteur actif avant de changer de serveur (ils utilisent le port 8080).',
    'Chargement initial observé sur HDD : environ un quart d’heure.',
    '',
    'Archives :',
    str(ROOT / 'comparatifs' / '2026-10-02-cafe-q4-p100'),
    str(ARCHIVE),
    'Chaque nouveau test Strata a son dossier essais/date-heure avec requêtes, réponses,',
    'journaux, paramètres, version du binaire et mesures. manifest-final.json fournit',
    'les SHA256 des fichiers archivés ; les GGUF de 111 Go ne sont pas dupliqués.',
]
text = '\n'.join(lines) + '\n'
(ROOT / 'COMPARATIF-Q4-STRATA.txt').write_text(text, encoding='utf-8-sig')
print(text)
