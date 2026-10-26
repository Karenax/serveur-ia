# Compatibilité des moteurs vocaux

Référence courante : Kiara 3.5.53, Android 1.0.24, 26 octobre 2026.

| Famille | Usage actuel | Décision |
|---|---|---|
| Low Windows, Parakeet v3 / Phonon serveur | Dictée et conversation habituelles | Support courant |
| Low Android, Whisper Small / Phonon serveur | Téléphone et tablette | Support courant |
| Pack Max format 2, API 6 | Whisper Turbo Vulkan et Phonon CPU | Pack actuel |
| Packs format 2, API 4–5 | Générations installées de reconnaissance progressive | Lecture et compatibilité conservées ; mise à jour proposée |
| Packs format 2, API antérieures | Anciens packs avec `qwen.dll` | Compatibilité explicite, pas de téléchargement silencieux |
| Runtime personnalisé format 1 | Ancien couple Voxtral/Qwen TTS | Installation historique ; ne pas le choisir pour une installation neuve |
| `voice_worker.py` | Ancien point d’entrée vers Phonon | Alias conservé pour les distributions existantes |
| `max_recognition.py` | Reconnaissance progressive utilisée par le worker de conversation | Module actif, à conserver |

`worker_protocol.py` porte le protocole commun des workers Max : taille des messages, une commande en attente, annulation, arrêt lors de la fermeture du parent et historique borné des annulations. Les moteurs restent séparés ; le protocole n’importe pas les bibliothèques de modèles.

La préparation historique copie le protocole à côté de son worker. Les constructions PyInstaller des packs courants l’incluent par import normal. Aucun modèle n’est téléchargé pendant un appel.

Un retrait de compatibilité exige un inventaire des packs distribués, un chemin de mise à jour vérifié, la conservation d’un retour et des essais sur les cartes prises en charge. Le seul nom ancien d’un fichier ou d’un dossier ne permet pas de conclure qu’il est inutilisé.

Les données et commandes restent identiques quel que soit le moteur de reconnaissance : le serveur vérifie le propriétaire, le projet et les révisions. Une réponse vocale n’annonce un enregistrement qu’après succès de la commande métier.
