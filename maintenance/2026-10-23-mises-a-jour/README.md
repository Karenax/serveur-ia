# Client Windows 3.5.36 : dossier de mise à jour stable

L'ancien client créait un dossier aléatoire `qwen-update-*` à côté de l'EXE
à chaque mise à jour. Son helper restait dans ce dossier. Le remplacement
renommait également l'EXE avec la nouvelle version et accumulait des archives
dans `Sauvegardes client Fred`.

À partir de 3.5.36, le nom de l'EXE reste identique pendant une mise à jour.
Le dossier voisin reprend exactement son nom sans l'extension `.exe` :
`Mon client.exe` utilise `Mon client/`. Ce dossier contient le helper, le
résultat de l'opération et une seule copie de retour `previous.exe`, remplacée
à la mise à jour suivante. Les téléchargements, le plan chiffré et les fichiers
temporaires sont supprimés après application. Un verrou sérialise les opérations.
Un marqueur associe le dossier au profil sans enregistrer son jeton en clair.
Un dossier préexistant contenant des fichiers personnels est conservé et refusé.

La première transition depuis un ancien client utilise encore son ancien helper.
Le nouveau client retire uniquement le dossier `qwen-update-*` exact qui lui a
transmis son accusé de démarrage, après validation de l'identité du profil,
confirmation de la version et sortie du helper. Les fichiers inconnus et les
autres anciens dossiers sont conservés. L'ancien helper peut encore renommer
l'EXE et créer sa dernière archive lors de cette transition. Les mises à jour
suivantes utilisent exclusivement le dossier stable. Les données et historiques
existants sous `%LOCALAPPDATA%\QwenClient` gardent leur emplacement.

La fenêtre « Version du profil incompatible avec le binaire » observée pendant
les essais provenait d'un test qui associait le binaire 3.5.35 à un profil 3.5.36.
Le contrôle de version reste obligatoire. Les échecs `--self-test` renvoient
désormais un code non nul sans déclencher le dialogue d'exception PyInstaller,
afin que le helper puisse rendre la main et conserver l'ancienne version.
Le test natif vérifie préalablement la version Windows du binaire choisi et
exerce aussi ce refus dans le nouvel EXE compilé.

## Vérification et publication

Depuis la racine :

```powershell
& '.\client-qwen\Build-Client.ps1' -DistributionDirectory "$PWD\toolchain\releases-staging\windows-3.5.36" -SkipManifest
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/2026-10-23-mises-a-jour/verify.py
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/check_sources.py
npm --prefix client-qwen run ux:check
```

`verify.py` lance 16 tests isolés, dont le remplacement signé, deux mises à jour
successives, un profil incompatible, l'échec du contrôle de démarrage, l'échec
de la nouvelle fenêtre avec restauration, et la conservation des fichiers
étrangers lors du nettoyage. Les ouvertures de fenêtre et leurs accusés sont
simulés dans le test du helper ; le contrôle de démarrage utilise réellement
l'EXE compilé. L'ancienne fixture des intégrations a également été actualisée
pour fournir son catalogue et attendre l'identifiant Hermes déjà utilisé en production.

`exe-proof.json` contient le résultat et l'empreinte du binaire. `activate.py`
publie ce binaire avec la clé de signature existante et reconditionne les EXE
personnels du serveur. Il vérifie une sauvegarde chiffrée, conserve la précédente
distribution et recharge uniquement la console. `production.json` atteste la
conservation des processus Qwen, des clés, des données et de la programmation
des sauvegardes. Ne pas relancer l'activation après son premier démarrage sans
examiner les preuves et l'état réel. Le client ouvert doit appliquer la mise à
jour pour bénéficier de ce comportement.
