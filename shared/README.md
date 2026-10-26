# Paquet partagé Kiara

`kiara-shared` contient les contrats et primitives communs au serveur et au client Windows : HTTP borné, validation des messages et profils, fichiers protégés, signatures de mise à jour et gestion du runtime vocal facultatif. Il ne dépend pas d’un répertoire de sources du client.

Installer ce paquet local après les dépendances publiques verrouillées :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' -m pip install --no-deps --no-build-isolation -e shared
```

Le constructeur Windows est préparé par `maintenance/prepare_build_environment.py`, qui installe aussi ce paquet. PyInstaller suit les imports du paquet. Les anciens modules `fred_http`, `chat_attachments`, `history_store`, `file_lock`, `advanced_voice` et `max_installation` sont des alias de compatibilité.

Une règle de transport ou une validation partagée se modifie ici, puis se vérifie dans les tests serveur et Windows. Les règles métier de mémoire, tâches et documents restent dans leurs services du serveur. Les composants natifs Android conservent leurs contrôles de plateforme ; les contrats communs sont vérifiés par les tests et les manifestes.
