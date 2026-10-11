# Android 1.0.7 — correcteur direct

Le Release signé **1.0.7**, code **8**, contient les trois actions du correcteur
direct Qwen. Les conversations gardent Hermes. L’APK publié mesure
**18 899 220 octets**, SHA-256
`21f635362daca34f5972abb64cfbd127b3dab1323c33157b0fd884504c898ab8`.
Le certificat SHA-256 est celui des versions précédentes :
`40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`.

| Vérification exécutée | Résultat |
| --- | --- |
| Gradle | `assembleRelease`, `lintRelease`, `assembleDebugAndroidTest` réussis ; 27 s, deux workers maximum |
| Distribution | 13 tests Python réussis ; licences et interface générée vérifiées |
| APK | Paquet `net.karenax.fred`, version/code 1.0.7/8, API 26 minimum et cible 36 ; Release non debuggable |
| Signature et alignement | Signature v2/v3, certificat existant et alignement 16 Ko vérifiés |
| Ressources embarquées | Interface et manifeste UI identiques aux fichiers générés ; adaptation Android du correcteur présente ; aucun fichier de profil personnel |
| Dictée et moteurs | Toutes les bibliothèques natives et `assets/voice/model.json` identiques bit à bit au Release 1.0.6 |
| Transport Android réel | Trois modes exécutés par le proxy natif du Release sur téléphone Android 16 x86_64, avec un vrai tunnel WireGuard et réponse SSE jusqu’à `[DONE]` |
| Contrat reçu | `stream: true` et `text_transform: {mode, text}` ; champs supplémentaires refusés par la fixture ; chaque mode reçu une fois, aucune authentification rejetée |
| Mise à jour signée | Installation du Release 1.0.7 par-dessus 1.0.5 sur l’émulateur, sans désinstallation |
| Préservation avant publication | APK `dist/` inchangé, processus fournisseur conservé et Qwen toujours chargé |

Les [22 contrôles et empreintes](android-release.json) et
l’[audit des ressources avant compilation](android-resources-before.json)
contiennent uniquement des métadonnées publiques. La compilation disposait
de 49,03 Gio de RAM libre et utilisait les outils locaux existants.

La fixture est indépendante des comptes et du serveur de production.
L’instrumentation n’importe pas de profil dans le coffre habituel ; elle
retire ses réglages synthétiques à la fin. L’APK d’instrumentation a ensuite
été désinstallé, son serveur de test arrêté et ses exports de profils supprimés.
Les helpers et journaux détaillés restent dans le staging ignoré.

Ce contrôle natif porte sur le transport d’un téléphone émulé. Aucun modèle
réel n’est appelé depuis la fixture Android ; les essais Qwen du serveur sont
décrits dans le rapport global. Le microphone, les performances acoustiques,
un appareil ARM64 physique et une conversation HTTPS authentifiée ne sont
pas remesurés ici. La publication et le rechargement sont vérifiés dans le
[rapport global](VALIDATION.md), avec les téléchargements authentifiés.
