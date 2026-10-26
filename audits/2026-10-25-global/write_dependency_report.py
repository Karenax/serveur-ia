"""Build the dependency appendix from the saved, read-only audit observations."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent
runtimes = json.loads((OUT / 'runtimes.json').read_text(encoding='utf-8'))
python = json.loads((OUT / 'osv.json').read_text(encoding='utf-8'))
go = json.loads((OUT / 'go-summary.json').read_text(encoding='utf-8'))
parts = [
'''# Dépendances — observations des 25–26 octobre 2026

Cette annexe complète F03, F04 et F05 du [rapport](<D:/Serveur IA/audits/2026-10-25-global/RAPPORT.md>). Les versions proviennent des environnements installés et des métadonnées du binaire, et les avis ont été consultés pendant l’audit. Aucun paquet applicatif n’a été mis à jour.

## Environnements Python

Cinq environnements ont été inventoriés : Strata, EG2, voix serveur, conversation Windows et Hermes privé. Les 220 couples paquet/version non exclus ont été interrogés auprès d’OSV ; sept couples, soit cinq noms de paquets, remontent au moins un avis. Le nombre de réponses ci-dessous inclut d’éventuels alias entre bases, notamment pour pip. Il ne faut pas additionner ces chiffres pour annoncer un nombre de vulnérabilités distinctes.

| Paquet | Version observée | Environnements | Fiches renvoyées |
|---|---|---|---|
'''
]
for item in python:
    if not item.get('advisories'):
        continue
    environments = [name for name, value in runtimes.items()
                    if value.get('installed', {}).get(item['package']) == item['version']]
    parts.append(f"| `{item['package']}` | {item['version']} | {', '.join(environments)} | {len(item['advisories'])} |\n")
parts.append('''
### Interprétation et ordre de traitement

1. **pypdf : priorité d’exposition.** Le serveur appelle effectivement `PdfReader` pour traiter les documents importés. Les avis portent notamment sur des boucles et allocations excessives face à des PDF construits pour déclencher ces comportements. L’extraction est déjà isolée, avec délai, surveillance mémoire et limite de concurrence. Mettre à jour le parseur en conservant ces protections ; vérifier tous les avis, car la correction d’un seul ne suffit pas. Aucun PDF hostile n’a été envoyé au serveur réel. [Avis primaire sur les structures imbriquées](https://github.com/py-pdf/pypdf/security/advisories/GHSA-f54x-cmq8-qg57).
2. **filelock : examiner les primitives et les répertoires concernés.** Certains avis dépendent des verrous logiciels, liens ou permissions locales. Les ACL restrictives observées réduisent certaines possibilités d’attaque locale sans constituer une correction du paquet. Ne pas assimiler automatiquement la présence du paquet à une exploitation réseau. [Avis primaire Windows](https://github.com/tox-dev/filelock/security/advisories/GHSA-567q-5qvw-pf92).
3. **setuptools et pip : chaîne d’installation.** Les versions recensées nécessitent un traitement dans les environnements de construction/installation. L’avis setuptools décrit un problème Windows d’écriture lors d’une conversion legacy de wheel ; le correctif annoncé est 84.1.0. Cela ne prouve pas une exécution arbitraire à partir d’un message utilisateur. [Avis primaire setuptools](https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w).
4. **opentelemetry-api : applicabilité à qualifier.** Un avis vise le parsing de tracestate. La présence dans Hermes est confirmée ; le passage de données non fiables à ce parseur dans le déploiement Kiara n’a pas été démontré. Mettre à jour dans le lot du runtime concerné et vérifier la compatibilité.

Les identifiants complets, résumés et liens originaux sont conservés dans [osv.json](<D:/Serveur IA/audits/2026-10-25-global/osv.json>). Ne pas appliquer des mises à jour majeures sans essais, ni conclure qu’un paquet sans avis est exempt de défaut.

### Verrous et cohérence

Les cinq fichiers de verrou ont une empreinte conforme et les versions verrouillées correspondent à l’installation. Le contrôle officiel échoue néanmoins sur les cinq outils de construction supplémentaires dans Strata : `altgraph 0.17.5`, `pefile 2024.8.26`, `pyinstaller 6.22.3`, `pyinstaller-hooks-contrib 2026.9`, `pywin32-ctypes 0.2.3`. Les quatre autres environnements n’ont pas de supplément non exclu.

Quatre vérifications `pip check` réussissent. Hermes privé ne contient pas pip ; ce contrôle y est indisponible. Il faut vérifier les métadonnées avec un outil extérieur au runtime ou un environnement de validation identique, plutôt qu’installer pip en production uniquement pour faire disparaître cet état.

## Pont Go / WireGuard

Le binaire `client-qwen/wireguard-bridge.exe` a été compilé avec **Go 1.27.1**. Les dépendances de module comprennent notamment `x/crypto 0.37.0`, `x/net 0.39.0`, `x/sys 0.32.0`, WireGuard, Wintun et gVisor. Une interrogation par module remonte beaucoup d’avis qui ne correspondent pas nécessairement à des paquets importés.

Pour réduire ce bruit, `govulncheck 1.9.0` a été exécuté sur le code, au niveau des symboles, avec le toolchain 1.27.1 et la base dont la dernière modification annoncée était le 21 octobre. Il trouve dix avis dans la bibliothèque standard avec des chemins d’appel statiques depuis le programme :

| Avis | Sujet fourni par la base Go | Version corrigée indiquée, branche 1.27 |
|---|---|---|
''')
for item in go['called_advisories']:
    parts.append(f"| [{item['id']}](https://pkg.go.dev/vuln/{item['id']}) | {item['summary']} | {', '.join(item['fixed'])} |\n")
parts.append('''
Les traces passent notamment par les proxies HTTP et les serveurs du pont. L’atteignabilité statique est plus précise qu’un simple inventaire de modules, mais ne prouve pas la présence de toutes les conditions d’une attaque : protocole activé, origine des données, méthode autorisée et configuration de transport restent déterminants. Les filtres d’hôte, d’origine, de routes et de tailles existants sont à conserver. Les avis SSH de x/crypto qui ne disposent pas d’un chemin d’appel pertinent ne sont pas présentés comme des vulnérabilités SSH exploitables dans Kiara. [Méthode officielle govulncheck](https://go.dev/doc/security/vuln/).

**Action :** reconstruire avec une version corrigée, au moins 1.27.3 pour les avis relevés sur la branche 1.27, puis tester le tunnel, le repli prévu, l’annulation, le téléchargement et la distribution signée. Une modification de go.mod seule ne corrige pas un EXE déjà livré. Pour le sujet des certificats, l’avis explique les cas où la liste de confiance du système peut ne pas suffire : [GO-2026-6809](https://pkg.go.dev/vuln/GO-2026-6809).

Le contrôle JSON de govulncheck a terminé correctement ; son code de sortie ne doit pas être interprété comme « aucun avis ». Les résultats structurés font foi. Le test Go du projet passe, mais ne constitue pas un test de toutes les conditions des avis.

Preuves : [métadonnées binaires](<D:/Serveur IA/audits/2026-10-25-global/go-binary.txt>), [résumé des symboles](<D:/Serveur IA/audits/2026-10-25-global/go-summary.json>), [flux complet](<D:/Serveur IA/audits/2026-10-25-global/govulncheck.jsonl>), [inventaire des imports](<D:/Serveur IA/audits/2026-10-25-global/go-imports.txt>).

## Autres dépendances et limites

`npm audit` n’a remonté aucun avis pour les dépendances de développement installées. Ce résultat ne couvre pas les bibliothèques natives, les fichiers JavaScript vendus, les DLL, les AAR Android, le moteur d’inférence ni les poids de modèles.

Le lint Android n’a trouvé aucune erreur. Ce n’est pas un audit de sécurité complet des composants natifs ou de leur provenance. Le présent travail ne remplace pas un inventaire de composants livré avec chaque EXE/APK et chaque pack vocal.

Conserver une nomenclature de composants par livrable : version, origine, empreinte, licence, date de validation et mécanisme de mise à jour. La classification d’un avis doit distinguer : version concernée, code importé, fonction atteignable, exposition réelle, reproduction éventuelle et mitigation. Les résultats de cet audit ne justifient aucune annonce d’exploitation avérée.
''')
(OUT / 'DEPENDANCES.md').write_text(''.join(parts), encoding='utf-8')
print('Dependency appendix generated from saved observations.')
