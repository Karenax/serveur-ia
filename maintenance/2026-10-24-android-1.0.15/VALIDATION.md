# Android 1.0.15 — Vocal Low

Correction de l’absence de la rubrique Vocal dans l’APK 1.0.14.
La page partagée est désormais incluse dans les assets Android. Son transport
utilise un contrôleur Android de conversation continue et les routes audio
authentifiées du serveur. La dictée conserve son parcours dans le chat.

Le modèle Whisper Small est partagé avec la dictée, téléchargé séparément après
annonce de sa taille et consentement. Aucun modèle lourd n’est ajouté à l’APK.
Le moteur conserve une session et transmet chaque phrase finale une seule fois,
avec acquittement. Le microphone se ferme pendant les réponses sans interruption,
en mode muet, au raccrochage et au passage en arrière-plan. Les commandes périmées
sont rejetées. La reconnaissance et la dictée ne capturent pas simultanément.

## Vérifications

- Build Release ARM64/x86_64, treize tests de livraison et licences : succès.
- Lint Android : zéro erreur, cinq avertissements existants.
- `maintenance/check_sources.py` : 318 sources Python, 68 JavaScript,
  93 PowerShell vérifiées dans les deux moteurs.
- `npm --prefix client-qwen run ux:check` : neuf avertissements de textes longs
  préexistants dans la console serveur ; aucun dans la page modifiée.
- `Test-Assets.cjs --browser` : douze scripts, parcours Android, clavier,
  pièces jointes, historique, correcteur et formats téléphone/tablette : succès.
- `test_conversation_ui.cjs --android` : navigation Vocal, dictée conservée,
  Low seul, phrase reconnue, requête orale Qwen, lecture PCM, pause/reprise
  du microphone, muet, arrière-plan et récupération après erreur : succès.
- `test_conversation_ui.cjs` : régression Windows Low : succès.
- Instrumentation sur émulateur Android API 36 : reconnaissance réelle du WAV
  français, phrase finale après silence, acquittement, capture suspendue,
  AudioRecord réel, muet/réactivation, fermeture pendant lecture et arrière-plan,
  routes locales audio authentifiées et fin SSE JSON : succès.
- Dialogue Android réel : refus du microphone, message de récupération et absence
  de capture : succès. Un premier essai a été bloqué par une fenêtre système de
  l’émulateur ; le test a été rejoué avec succès après fermeture de cette fenêtre.
- Vérification de la WebView réellement installée : ouverture de Vocal depuis
  le menu, Low seul, accès au pont natif et retour au chat avec dictée. Capture
  `native-android-vocal.png` et script `native_ui.cjs`.
- Audit Playwright MCP sur fixture isolée : téléphone 390×844 et tablette 768×1024,
  thèmes clair/sombre, réglages défilants, états écoute/réflexion/parole. Captures
  ouvertes et relues ; aucun débordement horizontal. Les tests Windows existants
  vérifient le focus, l’animation réduite et la conservation des préférences.

Les journaux sont conservés dans `toolchain/android-1.0.15-*.log` et les captures
dans ce dossier. Aucun téléphone physique n’a été connecté. Le test acoustique
complet microphone/haut-parleur d’un appareil réel reste à confirmer ; aucune
conformité WCAG complète n’est revendiquée.

## Livraison

APK : `client-android/dist/Acces-serveur-Kiara-Android.apk`.
Version 1.0.15, code 16, 18 940 180 octets.
SHA-256 : `861df091e14a0937a8afd7373249ed1dfc814106a0280681c86f1fb29e8db5b0`.
La clé et le certificat Android existants sont conservés. L’ancienne distribution
est sauvegardée dans le staging. Le manifeste servi et le téléchargement complet
authentifié ont été comparés au fichier signé : succès (`publication.json`).
Installer par-dessus la version existante ; aucune désinstallation nécessaire.
