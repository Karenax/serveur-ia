# Essai de vision locale — 14 octobre 2026

Essai autorisé après le signalement du refus des images par Qwen dans Hermes.
Le serveur précédent annonçait `images=false` et ne chargeait aucun projecteur visuel.

## Installation et isolation

Le modèle texte reste sur les deux P100, avec ses réglages existants. L'encodeur
visuel est un processus séparé, limité par UUID à la Quadro P2200. Le projecteur
BF16 de 907 543 008 octets est vérifié par SHA-256 contre les métadonnées LFS de
la révision Hugging Face épinglée par Strata : voir [projector.json](projector.json).
Les poids et binaires ne sont pas dans Git.

Le binaire visuel officiel CUDA 12.9 a échoué sur ce poste :
`failed to initialize CUDA: device kernel image is invalid`. Il continuait
silencieusement sur CPU. Ce résultat n'est pas une validation de la P2200.
Voir [encoder-cpu-fallback.json](encoder-cpu-fallback.json).

L'encodeur a donc été recompilé depuis les sources de Strata 0.1.43.1 et le
commit llama.cpp `3cf03257f219afbe7334045ff7c6a06ac68c627d`, avec CUDA 12.4.131,
MSVC 19.44, AVX2 portable et code machine `61-real` sans PTX.
[build_encoder.cmd](build_encoder.cmd) conserve la recette ; le chemin stable
est `dependances/strata-0.1.43.1/vision-p2200-cuda12.4/strata-vision.exe` et son
empreinte figure dans le `BUILD.json` voisin. Le moteur texte officiel est conservé.
Le pilote NVIDIA 528.89 est conservé.

## Mesures isolées de l'encodeur

[encoder.json](encoder.json) valide une véritable allocation sur la P2200,
sans variation de mémoire des deux P100. Image synthétique de 640 × 384 pixels,
240 tokens d'image, plafond de 1 024 tokens :

- Initialisation et préchauffage : 7,31 s.
- Encodage : 0,563 s, contre 6,094 s lors du repli CPU initial.
- P2200 : environ 1 356 Mio supplémentaires après chargement.
- RAM physique disponible : diminution d'environ 980 Mio ; mémoire résidente
  de l'encodeur environ 1 016 Mio, mémoire privée Windows environ 2 502 Mio.

La mémoire privée Windows inclut des allocations CUDA ; elle ne doit pas être
présentée comme autant de RAM physique supplémentaire. Ces mesures portent sur
une seule image, pas sur un benchmark général ni la vitesse des réponses texte.
Une image plus grande est réduite au budget de tokens configuré ; les tâches de
lecture très fine ou de localisation peuvent nécessiter davantage de tokens.

## Pic mémoire du rechargement à froid

La table ngram de 28 800 138 464 octets reste sur le SSD Kingston `C:`, à
`C:/Temp/Strata-ngram-recherche/iq4-xs-ple-iq4_nl.gguf`, avec `--ple-io direct`.
Les experts sont lus depuis les GGUF de `D:`, disque SATA HDD. Leur copie de
51,55 Gio en RAM est lente à froid. Le moteur conserve temporairement des pages
partagées pendant cette copie ; son ensemble de travail a atteint 85,27 Gio,
dont 42,66 Gio de pages privées, avec seulement 21,92 Gio de RAM disponibles.
Ce pic ne correspond pas à la consommation du seul encodeur visuel.

Une requête Windows `EmptyWorkingSet`, limitée au processus moteur vérifié,
a ramené la RAM disponible à 64,70 Gio. L'allocation privée engagée du moteur
est restée à 53,49 Gio, les adresses et allocations restent valides et la copie
a continué : [preuve](working-set-trim.json). Cette opération peut déplacer des
pages privées vers la liste modifiée ou le fichier d'échange ; elle ne garantit
pas que toutes les pages restent dans l'ensemble de travail du processus.

Le [superviseur](../../lanceur/runtime.py) prévoit désormais une seule tentative
de ce type pendant le démarrage si la RAM disponible descend sous la marge
configurée + 16 Gio. Le [contrôle](../../lanceur/startup_memory.py) exige le même
serveur vivant, un enfant direct, le chemin exact du moteur configuré et des
identités de processus recoupées. L'encodeur P2200 et les autres applications
ne sont pas visés. La protection RAM initiale reste active après la tentative ;
aucune purge périodique n'est exécutée pendant les conversations.

## Activation et retour arrière

[activate.py](activate.py) ajoute `vision` et `--vision` dans les deux configurations
de base, arrête Qwen à file vide, recharge la console sans chargement automatique
implicite, puis relance le modèle avec les réglages initiaux. La configuration de
vision reste persistante pour les prochains démarrages. Les sauvegardes privées
préalables sont dans `toolchain/vision-trial-20261014/before/`, hors Git.

Pour revenir à la configuration texte précédente, sur le serveur :

```powershell
.\Strata-src\.venv\Scripts\python.exe maintenance\2026-10-14-vision\activate.py --restore
```

Cette opération redémarre Qwen. Elle ne supprime pas le projecteur ni le binaire
visuel et ne modifie pas les accès, les clés ou les réglages réseau.

## Validation de bout en bout

[verify.py](verify.py) utilise une image contenant le texte « VISION 47 », un cercle
rouge et un carré bleu. La question ne révèle ni le code ni les formes attendues.
Le passage Hermes utilise un compte et un profil temporaires, sans conversation
de production. Les rapports `direct.json`, `hermes.json` et `production.json`
sont produits au fil de la validation et leur champ `passed` constitue le résultat.
Le simple indicateur `images=true` ne prouve pas la compréhension d'une image.

Résultats réels :

- [Qwen direct](direct.json) : « Le code est **VISION 47**. La forme rouge est un
  **cercle** et la forme bleue est un **carré**. », réponse complète en 14,484 s.
- [Hermes isolé](hermes.json) : même lecture correcte, tour finalisé et réconcilié
  en 31,438 s, sans réponse cloud ni modification d'une conversation utilisateur.
- [Catalogue HTTPS réel](catalogue.json) : cinq modèles, `fred-qwen` disponible
  avec `images=true` et `vision=true`. Aucune reconstruction du client nécessaire.
- [Production](production.json) : modèle prêt après 2 985,3 s, moteur texte
  officiel inchangé, accès, clés, réglages et programmation des sauvegardes
  conservés. Environ 54,4 Gio de RAM disponibles après les essais.
- [Contrôle texte](text-after.json) : 323 pour 17 × 19, comme
  [avant l'activation](text-before.json). Ces réponses très courtes vérifient le
  fonctionnement ; elles ne constituent pas une comparaison de débit texte.
- [Tests](tests.json) : six contrôles d'identité/périmètre du mécanisme mémoire
  et huit tests du lanceur passent, dont la protection RAM. Les
  [contrôles de syntaxe](syntax.json) passent également.

La vision est conservée dans les deux configurations de base. Le mécanisme du
superviseur s'appliquera aux prochains démarrages ; le démarrage actuel a reçu
la même intervention ponctuelle manuellement, avec preuve avant/après. Pour
essayer côté client, actualiser Fred, choisir **Qwen local** et envoyer une image
dans une nouvelle conversation.
