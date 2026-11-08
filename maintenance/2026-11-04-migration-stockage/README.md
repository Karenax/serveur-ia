# Migration du stockage — 4 novembre 2026

État : bascule terminée et contrôlée. Le serveur et ses données actives utilisent F:.

Le dossier de travail est `F:\Serveur IA`. Le commit de départ est
`6cd796fad708d483d3fd976f72caedb30cdbe802` (Kiara 3.5.60 et EG2 sur P2200).
Les versions et les clés des clients restent identiques.

## Répartition

- **F:** sources, données actives, environnements Python, SDK Android, outils de
  construction et ressources nécessaires au serveur. Le moteur Strata et les
  poids IQ4_XS étaient déjà sur F: et restent à leur emplacement.
- **D:** preuves, sauvegardes, installateurs, anciens essais et copie de retour.
  `D:\Serveur IA` conserve l'état antérieur ; ne plus l'utiliser comme dossier
  de développement ni lancer son serveur pendant que celui de F: fonctionne.
- Les sources historiques suivies par Git restent aussi dans le dépôt sur F:
  pour conserver les références documentaires et les scripts de vérification.
- Les dépendances privées Hermes déjà installées sur C: restent en place.

Le dossier `F:\Serveur IA\strata-data\model-q4` pointe vers
`F:\Kiara\modeles\iq4-xs`. Ce dernier contient des liens physiques vers les
trois fichiers IQ4_XS déjà présents à la racine de F: ; les poids ne sont pas
dupliqués. Les anciennes variantes Q4/IQ3 conservées sur D: sont des archives,
à réinstaller sur un emplacement actif avant de réutiliser leurs anciens profils.

## Preuves et sauvegardes

La variable utilisateur `KIARA_EVIDENCE_DIR` désigne
`D:\Archives Kiara\preuves`. `maintenance/verify_project.py` et les tests UI
partagés l'utilisent pour leurs sorties par défaut. `--output` et
`UI_PROOF_DIRECTORY` restent prioritaires ; sans cette variable, le comportement
historique sous `toolchain/test-results` est conservé.

Les nouvelles sauvegardes chiffrées vont dans `D:\Archives Kiara\Sauvegardes`.
La programmation, la rétention et la seconde copie NAS sont conservées. Le
catalogue et son secret protégé restent avec les données actives sur F: ; les
anciennes archives référencées par le catalogue restent accessibles sur D:.

Les inventaires, journaux de copie, empreintes des données et validations de
cette opération sont conservés dans :

`D:\Archives Kiara\migration-20261104-184641`

Consulter les résultats JSON de ce dossier pour l'état effectivement validé,
notamment `critical-data-verification.json`, `sqlite-validation.json`, les
répertoires `validation-*` et le résultat du pare-feu.

## Poste Windows

Les chemins actifs des configurations, environnements Python et outils Android
sont adaptés à F:. Le démarrage automatique et le raccourci Android Studio sont
mis à jour. Des règles équivalentes autorisent WireGuard et ADB à leur nouveau
chemin, sans changement de ports ni de profils réseau. Les anciennes règles
restent disponibles pour un éventuel retour.

Les terminaux déjà ouverts peuvent garder leurs anciennes variables ; ouvrir
les nouveaux travaux depuis `F:\Serveur IA`. Les preuves historiques conservent
leurs chemins d'origine. Certains fichiers suivis par Git avaient seulement une
différence CRLF/LF masquée par l'ancien index : leur copie de travail sur F:
reprend les fins de ligne du commit, sans changer leur contenu logique ; les
octets originaux restent dans l'archive sur D:.

## Retour

Un point de retour chiffré protégé a été créé et vérifié avant la bascule, avec
seconde copie sur le NAS. Le dossier de contrôle contient les valeurs initiales
du registre et les raccourcis d'origine. `Update-Firewall.ps1 -Rollback` retire
les règles ajoutées pour F: en conservant celles de D:, avec les droits
administrateur Windows.

La copie sur D: est un état d'avant migration. Après de nouveaux échanges sur F:,
utiliser la sauvegarde vérifiée la plus récente et la procédure de restauration
existante avant de revenir à cet ancien dossier ; ne pas remplacer des données
récentes par la copie figée.

## Vérifications effectuées

- 632 fichiers de données, clés et distributions personnelles comparés par SHA-256
  après l'arrêt du service sur D: ; contrôle SQLite `quick_check` réussi.
- Sept environnements verrouillés conformes ; tests des sources, du serveur,
  de Windows, de la voix, de l'interface, de Go et d'Android exécutés sur F:.
  La suite serveur comporte 586 tests : trois échecs ont été revérifiés avec
  succès après correction de l'import `parse_qs` de la console et sélection du
  client livré 3.5.60, à la place du staging historique 3.5.53.
- Modèle chargé avec contexte 262144, génération synthétique réussie, EG2 prêt
  sur P2200, Phonon/Tiphaine prêt sur CPU, catalogue Hermes accessible.
- Nouvelle sauvegarde chiffrée créée et vérifiée depuis F:, écrite sur D: et
  copiée sur le NAS ; programmation quotidienne à 03:00 conservée.
- Les 2328 fichiers de l'ancien dossier d'essais sur F: sont archivés sur D: :
  noms et tailles vérifiés, SHA-256 des 734 fichiers documentaires comparés.
  Le manifeste SHA-256 initial de tous les fichiers est conservé. Les 1594
  fichiers binaires n'ont pas tous été relus intégralement après le déplacement,
  en raison du faible débit de relecture du disque d'archive.

## Allègement après migration — 4 novembre 2026

À la demande de l'utilisateur, les émulateurs Android, leurs profils et leurs
instantanés sont intégralement conservés : 16 185 229 646 octets avant et après.
Les outils Android, les environnements de production et de construction, les
versions livrées actuelles et les fixtures de tests restent sur F:.

Le projet passe de 87,25 Go à 54,67 Go de fichiers (81,26 à 50,91 Gio, unités
utilisées par l'affichage Windows), sans compter les cibles des jonctions.
107 anciennes installations, distributions, caches et binaires historiques,
soit 32,58 Go, sont déplacés vers :

`D:\Archives Kiara\nettoyage-F-20261104-203825\archives`

Principaux postes : anciennes voix et environnements Max (16,19 Go), anciennes
livraisons en staging (8,50 Go), anciens packs IQ3/Q4 (3,04 Go), anciens moteurs
et binaires de retour (3,05 Go), autres essais et caches (1,79 Go). L'historique
Git, les sources et les preuves suivies par Git sont conservés. Les modifications
de migration en cours n'ont été ni commitées ni remplacées.

Le descripteur local `toolchain/voice-max-server/runtime.json` désignait encore
le pack sur D:. Sa racine est corrigée vers le pack format 2/API 6 actif sur F:.
Le catalogue signé est inchangé ; les manifestes ASR et TTS sont vérifiés, le
sondage GPU natif et un démarrage réel TTS du pack actuel réussissent. Les
anciennes installations Voxtral/Qwen TTS de format 1 ne sont plus nécessaires.

Validation après déplacement : 107 destinations présentes, sources absentes et
tailles cumulées conformes ; lecture des chemins Windows longs incluse. Les
binaires archivés n'ont pas tous été relus intégralement par SHA-256. Les neuf
tests Max/Android passent après la fin du déplacement, ainsi que les 54 tests de
contrôleur vocal et les contrôles des sept environnements verrouillés. Le
serveur est prêt, le modèle chargé, EG2 prêt sur P2200 et Phonon prêt. Le
contrôle des différences Git passe.

Mesures, plan de restauration par chemin et résultats détaillés :
`D:\Archives Kiara\nettoyage-F-20261104-203825\verification.json`.
Le plan `plan.json` associe chaque chemin initial sur F: à sa destination sur D:.
L'espace libre final mesuré est de 324,13 Go sur F: (301,87 Gio) et 4,22 To sur D:.
