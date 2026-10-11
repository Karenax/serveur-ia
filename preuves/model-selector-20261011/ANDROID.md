# Android 1.0.8 — choix du modèle

APK Release **1.0.8**, code **9**, publié dans
`client-android/dist/Acces-serveur-Fred-Android.apk`. La mise à jour authentifiée
est annoncée et téléchargée avec son empreinte vérifiée, avec Windows 3.5.25.
Voir [delivery-validation.json](delivery-validation.json).

| Contrôle exécuté | Résultat |
| --- | --- |
| Compilation | `assembleRelease`, `lintRelease` et `assembleDebugAndroidTest` réussissent ; 13 tests de distribution réussissent |
| Signature | Certificat de distribution conservé, signatures v2/v3 et alignement 16 Ko validés |
| Release installé | Mise à jour 1.0.7/code8 vers 1.0.8/code9 sur téléphone Android 16 x86_64, sans désinstallation |
| Catalogue natif | Fournisseur, libellé, disponibilité, capacités et modèle par défaut conservés ; un modèle distant reste utilisable avec Qwen local déchargé |
| Erreur locale | L’erreur `model_unloaded` du correcteur Qwen laisse la connexion au modèle distant disponible |
| Historique | Modèle de la conversation conservé dans le stockage chiffré et après relecture ; anciens historiques acceptés ; valeurs invalides et fusion de scopes de modèles différents refusées |
| Contexte et réponse | `body.model` arrive intact dans les POST natifs `/v1/context` et `/v1/chat/completions`, via un vrai tunnel WireGuard authentifié ; estimation de contexte distante et réponse SSE complète reçues |
| Indisponibilité | Catalogue conservé en HTTP 200 lorsque tous les modèles deviennent indisponibles ; sélection retirée signalée en HTTP 503 `model_unavailable`, sans substitution ni réécriture du choix |
| Correcteur | Les trois modes directs Qwen passent avec le contrat strict `text_transform: {mode, text}`, chacun une fois, jusqu’à `[DONE]` |
| Mises à jour | `UpdateChecks` natif valide les bornes du manifeste et le rejet d’une intégrité invalide, d’un autre paquet, d’une autre signature, d’une version identique ou d’un retour de version |
| Ressources | Bibliothèques ARM64/x86_64 et manifeste Whisper Small identiques bit à bit à l’APK 1.0.7 ; interface embarquée et empreintes des sources concordantes |
| Serveur pendant les essais | Modèle local chargé et processus écoutant sur 8080 inchangés ; paquet publié 1.0.7 conservé pendant la préparation |

Les six groupes de tests natifs du sélecteur, les trois modes du correcteur et
la politique de mise à jour ont réussi sur le Release signé. Les serveurs de
test utilisent des profils synthétiques isolés et valident les corps reçus.
Les instrumentations et exports de profils ont été retirés, et les fixtures
arrêtées après les contrôles.

Les **29 vérifications**, compteurs de requêtes et empreintes sont dans
[android-release.json](android-release.json). L’[audit préalable](android-resources-before.json)
consigne les ressources disponibles et l’état du modèle avant la compilation.
Les helpers et journaux détaillés restent dans le staging exclu de Git.

Les réponses du test Android sont synthétiques : ce parcours vérifie le
transport natif et la sélection, sans inférence auprès d’un fournisseur externe.
Les essais physiques ARM64, une conversation HTTPS authentifiée et la mesure
acoustique de la dictée n’ont pas été refaits. L’installateur Android conserve
son parcours existant ; sa politique est contrôlée ici, sans nouvelle mise à jour
par l’interface de l’installateur.

SHA-256 de l’APK : `16e1baa343081a463d857ed7a00f5a0af13e5aa7a218d9130ba1a85a8142737c`.
Certificat SHA-256 : `40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`.
