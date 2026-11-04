# Cause confirmée : encodage du texte envoyé au complément Max Windows

Le 31 octobre 2026, la phrase exacte fournie par l’utilisateur a permis de
reproduire le défaut avec le **programme installé sur ce PC**, sans modifier
son installation ni les modèles.

## Le modèle français était correct, le texte reçu était corrompu

Installation examinée : `%LOCALAPPDATA%/QwenClient/voice-max/runtime.json`,
complément `vocal-rt-de5e67a320a06b1f`, API 6, Phonon 40m français Q8,
Tiphaine, ptts 0.4.1. `config.json` déclare `languages: ["fr"]`.
Les empreintes du modèle, du tokenizer, de la voix, du runtime natif et de
l’EXE installé correspondent à l’inventaire du complément.

`AdvancedVoice._write` écrivait le JSON en UTF-8 avec `ensure_ascii=False`.
Le complément figé Windows forçait seulement stdout et stderr en UTF-8.
Son entrée stdin conservait la page de codes Windows, ici CP1252.
`Popen(encoding='utf-8')` configure les flux du parent, pas ceux du programme
enfant. Il en résultait, avant toute synthèse :

| Texte demandé | Texte après décodage UTF-8 comme CP1252 |
| --- | --- |
| `Léa` | `LÃ©a` |
| `dés` | `dÃ©s` |
| `lança` | `lanÃ§a` |
| `avança` | `avanÃ§a` |
| `d’une` | `dâ€™une` |

Cela explique une dégradation concentrée sur les accents, cédilles et apostrophes
typographiques alors que beaucoup de mots ordinaires restent compréhensibles.
La langue du modèle n’était pas remplacée par une autre.

## Comparaison avec la phrase fournie

Phrase : « Léa posa le plateau sur la table. Les dés colorés attendaient
patiemment. Elle lança les dés, espérant un six. Son pion avança d’une case,
puis d’une autre. »

`lea.py` utilise l’EXE installé dans un processus isolé et le compare au même
modèle lancé directement. `lea-results.json` conserve les paramètres,
empreintes, durées et retranscriptions. La phrase entière et les quatre
fragments produits par le vrai découpage du client sont testés.

- EXE installé, échange initial : 12,56 secondes de son pour le texte entier,
  13,04 secondes pour les quatre phrases. La retranscription donne notamment
  « Loa », « coloraos », « avanaca » ou « avannequa ».
- Même modèle et voix par l’API Python : 8,96 secondes, texte correctement
  retranscrit, y compris Léa, dés, lança et avança.
- EXE installé **inchangé**, quatre phrases transmises par le writer corrigé :
  10,08 secondes. Les mots de la phrase sont correctement retranscrits, avec
  une répétition terminale supplémentaire dans la retranscription automatique.
  Ce dernier point n’est pas une preuve de répétition acoustique et mérite
  une écoute humaine.

Changer la voix, la température ou passer le calcul en f32 n’était pas nécessaire
pour éliminer la corruption du texte. Les essais correspondants sont conservés
dans `lea-results.json` ; ils ne constituent pas un classement perceptif des voix.

## Correctif source et preuve avec l’ancien complément

1. `shared/kiara_shared/voice_runtime.py` envoie les commandes JSON avec
   `ensure_ascii=True`. Les caractères restent identiques après `json.loads`,
   mais le transport contient seulement de l’ASCII : les anciens compléments
   installés sous Windows peuvent donc les décoder sans corrompre les accents.
2. `client-voice/worker_protocol.py` force stdin en UTF-8 pour les futurs
   compléments. Ce protocole est commun aux générations de workers Max.

`verify_encoding.py` appelle le vrai `AdvancedVoice._write` corrigé avec
l’**ancien EXE installé**, et force volontairement son entrée en CP1252 pour
vérifier le cas défaillant. Résultat dans `encoding-result.json` et son dans
`lea-client-corrige.wav`.

Les tests de non-régression vérifient la conservation exacte du texte à travers
UTF-8, CP1252 et CP850, ainsi que la lecture UTF-8 d’une entrée initialement
configurée en CP1252. Les suites vocales ciblées ont été exécutées.

Les sources sont corrigées ; **le client installé et le complément publié n’ont
pas été remplacés par ces essais**. Reconstruire et distribuer le client permet
de corriger les échanges avec les compléments existants sans retélécharger les
modèles. La correction de stdin sera incluse lors d’une reconstruction du pack.

## Limites et rectification du premier diagnostic

Les premiers tests vérifiaient les bons fichiers et le modèle directement par
Python. Ils contournaient l’entrée de l’EXE figé et ne pouvaient donc pas
détecter ce défaut Windows. Ils ne permettaient pas d’attribuer le signalement
à une simple difficulté du modèle sur les mots ambigus.

Les retranscriptions automatiques sont une preuve d’intelligibilité et de
comparaison, pas une mesure exhaustive des phonèmes, des e muets ou de la
qualité perceptive. L’enregistrement corrigé reste disponible pour écoute.

Rejouer sans changer l’installation :

```powershell
node maintenance/2026-10-31-max-prononciation/inspect_segments.cjs
& './toolchain/phonon-server-python/Scripts/python.exe' maintenance/2026-10-31-max-prononciation/lea.py
& './toolchain/phonon-server-python/Scripts/python.exe' maintenance/2026-10-31-max-prononciation/verify_encoding.py
```
