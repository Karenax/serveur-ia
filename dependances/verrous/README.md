# Environnements Kiara verrouillés

Les six fichiers `*.requirements.txt` enregistrent les versions effectivement
résolues par Python et les empreintes SHA-256 des distributions publiques PyPI.
`manifest.json` enregistre aussi l’empreinte de chaque verrou.

Vérification sans accès réseau :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/verrous_runtime.py check
```

Pour reconstruire, créer un environnement neuf avec la même version de Python,
puis installer son verrou avec `pip install --require-hashes -r <verrou>`.
Les verrous ne doivent pas être synchronisés aveuglément dans un environnement
partagé ou dans l’installation personnelle Hermes.

Strata, EG2 et la voix utilisent Python 3.12 ; Hermes Fred utilise Python 3.14.
Les SDK et poids restent séparés. `artifact-tool-v2` est un outil du poste et
n’appartient pas à l’application. `hermes-agent` provient du commit et du patch
locaux, pas d’un paquet PyPI versionné `0.0.0` : installer ses dépendances publiques
avec le verrou puis sa source locale en mode éditable avec `--no-deps`.

Le runtime Hermes privé est préparé par
`maintenance/2026-10-21-correctifs-audit/preparer_hermes.py`, avec son patch
`hermes-security.patch` et son inventaire de référence. Il est installé sur le SSD
sous `%LOCALAPPDATA%\Fred\runtime-security\hermes-20261021`. Le pointeur validé
reste dans `toolchain/hermes-security-runtime/runtime.json`. Le code et les profils
de l’installation personnelle Hermes restent distincts.

Un environnement de développement peut hériter du `site-packages` du runtime
d’outillage. Le générateur retient la première distribution réellement résolue
par Python ; les doublons des dossiers de repli ne remplacent pas ses versions.
Une reconstruction avec les verrous dans un venv neuf n’exige pas cet héritage.

Depuis le 26 octobre, Strata n’hérite plus du runtime d’outillage et le constructeur
Windows dispose de son propre profil `construction-windows`. Préparer ce dernier
avec `maintenance/prepare_build_environment.py`. Le contrôle rapporte tous les
environnements avant d’échouer, afin qu’un écart ne masque pas les suivants.

`kiara-shared` est le paquet local du dépôt : installer ses sources après le verrou,
sans acquisition implicite de dépendances. Ses fichiers sont couverts par le manifeste
du composant. Le pointeur Hermes privé est résolu avant le bootstrap personnel ;
ses répertoires de dépendances et outils restent des prérequis explicites.

Ne régénérer ces fichiers qu’après installation et validation des mises à jour :
`maintenance/verrous_runtime.py create` consulte PyPI, sans transmettre de données
privées, pour récupérer les empreintes des distributions des versions choisies.
