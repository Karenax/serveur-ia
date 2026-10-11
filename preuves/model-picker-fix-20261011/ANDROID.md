# Android 1.0.9 — menu de modèles

APK Release **1.0.9**, code **10**, publié dans
`client-android/dist/Acces-serveur-Fred-Android.apk`, avec Windows et le serveur 3.5.26.
Les [téléchargements authentifiés](delivery-validation.json) concordent avec
les empreintes signées.

| Contrôle exécuté | Résultat |
| --- | --- |
| Compilation | Release, analyse Android, variante QA Debug et instrumentation compilés ; 13 tests de distribution réussissent |
| Signature | Certificat de distribution conservé, signatures v2/v3 et alignement 16 Ko validés |
| Menu natif | 121 options utilisables ; modèle indisponible masqué ; popup et focus conservés pendant cinq tentatives d’actualisation |
| Défilement | Quatre gestes natifs déplacent la liste ; un vrai appui sélectionne le modèle 114 dans la conversation |
| Catalogue modifié | Le nouveau catalogue est relu après la fermeture du menu ; une réponse déjà en vol attend également la fermeture |
| Interface testée | La démo QA Android ne contacte aucun serveur ; ses fichiers d’interface sont identiques bit à bit au Release signé |
| Transport du Release | Six groupes natifs passent avec le vrai proxy et tunnel WireGuard authentifié : catalogue public, contexte et chat avec le modèle choisi, historique chiffré et erreur de modèle retiré sans substitution |
| Correcteur | Les trois modes directs Qwen passent avec le contrat strict `text_transform: {mode, text}`, chacun une fois jusqu’à `[DONE]` |
| Mise à jour | `UpdateChecks` valide les bornes du manifeste, l’intégrité, le paquet, la signature et le rejet des versions identiques ou antérieures |
| Ressources | Bibliothèques ARM64/x86_64 et manifeste Whisper Small identiques bit à bit à l’APK 1.0.8 ; interface embarquée et empreintes des sources concordantes |
| Serveur | Modèle local chargé et processus écoutant sur 8080 inchangés pendant la préparation |
| Console | Treize contrôles en navigateur isolé : token administrateur, partage global/individuel, modèles exposés automatiquement ou explicitement, masquage des indisponibles, recherche, défilement, actualisation forcée et relecture après refus |

Les [31 vérifications de l’APK](android-release.json), les
[huit contrôles de la vraie WebView](android-webview-picker.json), les
[treize contrôles de la console](console-sharing-ui.json) et l’
[audit préalable](android-resources-before.json) constituent les preuves.
Les helpers et journaux détaillés restent dans le staging exclu de Git.

Les réponses Android du test de transport sont synthétiques : aucune inférence
externe n’est effectuée. Les essais physiques ARM64, une conversation HTTPS
authentifiée et la mesure acoustique de la dictée ne sont pas refaits.
Les instrumentations et exports de profils de test sont retirés après les essais.

SHA-256 de l’APK : `a798cc18c1eb5a59a4473840e6c79974c724b61fe25ba6ea1a38f8687c70a427`.
Certificat SHA-256 : `40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`.
