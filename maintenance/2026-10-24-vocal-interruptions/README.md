# Interruption des réponses : réglage rétabli en Low

La restauration de Low/Phonon avait masqué `conversation-options` en Low et
contourné le choix `voice_interruptions` dans la boucle classique. Le test rapide
de Low attendait explicitement que le réglage soit caché ; il ne vérifiait pas
le fonctionnement de sa position désactivée. C’était une régression.

Le réglage **Interrompre Kiara en parlant** reste désormais visible en Low et Max,
dans **Vocal → Microphone**. Décoché, il laisse terminer la réflexion et toute la
lecture audio avant de traiter une nouvelle question. Son aide indique « Kiara
termine sa réponse avant de vous écouter ». Coché, il permet l’interruption.
La préférence existante est conservée, sans remise à zéro ni nouvelle clé.

Les paroles reconnues pendant une réponse protégée sont acquittées et ignorées,
y compris leurs transcriptions finales tardives. La boucle Low garde sa synthèse
Phonon et l’acceptation des réponses courtes. Une nouvelle parole après la lecture
reste acceptée, même si la synchronisation de l’historique n’est pas finie : cette
sauvegarde ne provoque plus une annulation de la réponse déjà terminée.

Sur Android, la commande de protection du microphone suit maintenant ce réglage
en Low, pendant le calcul et la lecture. Un appareil sans annulation d’écho garde
la protection automatique ; l’option et son explication restent visibles. Aucun
moteur ASR, modèle, worker natif, dictée ou complément Max n’est remplacé.

## Vérifications contre les régressions

`test_voice_interruptions_ui.cjs` est intégré à `npm test`. Il exerce Low Windows,
Low Android avec/sans annulation d’écho et Max Windows. Les scénarios couvrent :

- visibilité du réglage et absence d’interruption par défaut ;
- conservation du choix lors d’un changement d’animation et d’un rechargement ;
- parole pendant la réflexion puis la lecture, sans annulation ni coupure audio ;
- conservation du texte complet, rejet d’une transcription tardive du même bruit ;
- prise en compte du « Oui » suivant, pendant la sauvegarde si nécessaire ;
- interruption effective du calcul et de la lecture quand le réglage est coché ;
- protection du microphone Android avec la préférence désactivée.

Le test est aussi exécuté avec le vrai `conversation.js` extrait de l’EXE publié
**3.5.46**, conservé dans `before-conversation.txt`. Il échoue sur « The interruption
choice must be visible in Low and Max » : le contrôle négatif reproduit le défaut
de la version livrée. La commande est conservée pour reproduction :

```powershell
node client-qwen/test_conversation_ui.cjs --interruptions '--voice-source=D:/Serveur IA/maintenance/2026-10-24-vocal-interruptions/before-conversation.txt'
```

La suite classique vérifie maintenant explicitement le mode avec interruptions
activées et sa réponse immédiate d’un mot. Les suites Max, animations et stabilité
restent dans l’exécution complète. Une course préexistante du test de tiroir mobile
a également été rendue déterministe : il attend la livraison des événements de
redimensionnement avant d’ouvrir le tiroir, sans retirer ses assertions de focus.

Contrôles : 10 suites UI, contrôles de sources, UX et 13 tests de livraison Android.
Les neuf avertissements UX de longueur concernent la console serveur et précèdent
cette tâche. Captures Playwright MCP lues dans `ui/`, ordinateur 1440×900 et assets
Android à 390×844 : réglage visible, aide associée, focus, absence de débordement.
Les appels et transcriptions des tests UI sont simulés ; aucun microphone physique
n’a été utilisé et aucune donnée utilisateur n’a servi aux tests.

## Livraison

Windows **3.5.47**, Android **1.0.20/code 21**, signés avec les clés existantes.
La publication vérifie la sauvegarde, les profils et les téléchargements servis,
et conserve les processus Qwen. Les deux animations restent disponibles.

APK : `D:\Serveur IA\client-android\dist\Acces-serveur-Kiara-Android.apk`.
Preuves : `production.json`, `publication.json`, `android-publication.json` et
les journaux de tests présents dans ce dossier.
