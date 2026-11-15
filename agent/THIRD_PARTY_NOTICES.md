# Provenance et dépendances

Inventaire actualisé le 11 octobre 2026 :
[versions et métadonnées des dépendances](docs/dependencies.json).
Il porte sur les profils déclarés dans les fichiers de dépendances du projet,
y compris les outils de test, et conserve les informations fournies par les
distributions installées. Il ne remplace pas les textes de licences livrés par
leurs auteurs. Le moteur distant EG2 est configuré dans LM Studio et ne fait
pas partie des dépendances Python installées par Agent.

| Composant | Provenance | Déclaration observée |
|---|---|---|
| Modules ERP MiniPilot | Historique de ce dépôt, absorption conservée | Aucune licence distincte attribuée ici |
| Moteur CDC | Port XPilot décrit dans docs/17 ; règles conservées | Droits du propriétaire à confirmer pour redistribution |
| Catalogue livrables L3 | Onze types et 67 points XPilot ; source, commit d'audit et SHA dans docs/32 et deliverable_catalogue.json | Provenance XPilot conservée ; aucune nouvelle licence attribuée |
| FastAPI, SQLAlchemy, React | Distributions verrouillées | Métadonnées dans l’inventaire généré |
| Extension Infomaniak | Sources extensions/infomaniak-auto-local | 0.2.0 actuelle ; XPI 0.1.1 historique |
| Actions GitHub | Dépôts officiels actions/checkout, setup-python, setup-node | Révisions SHA fixées dans le workflow |

Agent n’a pas de licence déclarée à la racine à cette révision. La décision
d’accorder une licence appartient au propriétaire ; aucune licence n’a été
inventée ou appliquée aux modules hérités. Les ZIP/XPI historiques de `Divers`
sont conservés. Le paquet reconstruit est non signé et ne prouve pas une
qualification Firefox ou Infomaniak.

Régénération de l’inventaire après installation des locks :
`python scripts/dependency_inventory.py`.
Packaging actuel : `python scripts/package_extension.py --output <nouveau ZIP>`.
Le fichier JSON voisin liste version, empreintes de chaque source et du paquet.
La documentation officielle des actions utilisées est dans
[checkout](https://github.com/actions/checkout),
[setup-python](https://github.com/actions/setup-python) et
[setup-node](https://github.com/actions/setup-node).

Runtime audio optionnel : [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)
et modèles Whisper, [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx),
[segmentation Pyannote](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-segmentation-models)
et [empreintes WeSpeaker](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models).
Les versions applicatives sont épinglées dans `requirements-audio.txt` ; les
modèles sont téléchargés séparément par `scripts/setup_meeting_audio.py` et
ne sont pas redistribués dans Git. Les licences et conditions des distributions
amont s’appliquent ; `.venv-speech` et `.models/audio` restent hors du dépôt.
