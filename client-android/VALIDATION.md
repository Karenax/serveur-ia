# Validation Android — 12 octobre 2026

## Version 1.0.10 — réflexion propre à chaque modèle

APK **1.0.10/code 11** publiée avec le certificat existant. Les 36 contrôles
de l’artefact final et les neuf contrôles de la vraie popup Android passent.
Une garde conserve le statut, les options et les niveaux pendant les redraws
de bibliothèque. Les préférences chiffrées conservent les valeurs canoniques
et les choix par modèle, y compris après réouverture.

Quinze combinaisons annoncées sont transmises sans conversion dans le contexte
et le chat SSE via WireGuard authentifié ; 19 préférences invalides sont refusées
sans écriture. Les contrats du catalogue, du correcteur direct et de la mise
à jour passent sur l’APK finale. Les 23 ressources vocales et JNI restent
identiques à l’APK 1.0.9. Les réponses de fournisseur sont synthétiques ; aucun
nouvel essai physique ARM64 ni acoustique n’est revendiqué.

[Rapport Android](../preuves/reasoning-models-20261011/ANDROID.md),
[contrôles de livraison](../preuves/reasoning-models-20261011/delivery-validation.json).

## Version 1.0.9 — menu de modèles stable

APK Release **1.0.9**, code **10**, publié avec le certificat de distribution
existant. Les **31 vérifications** passent : compilation, analyse Android,
13 tests de distribution, signature v2/v3, alignement 16 Ko, ressources
vocales et bibliothèques natives identiques bit à bit à l’APK 1.0.8.

Huit contrôles passent dans la vraie WebView Android : liste de 121 modèles
utilisables, popup native ouverte, cinq actualisations différées, quatre
gestes de défilement et sélection du modèle 114, relecture au changement de
focus, réponse déjà en vol différée jusqu’à la fermeture du menu, absence
de débordement et d’exception. Cette vérification utilise la démo Debug sans
serveur ; ses fichiers d’interface sont identiques bit à bit au Release signé.

Le Release signé est installé sans désinstallation sur l’émulateur téléphone.
Les six groupes de contrats natifs du catalogue et du modèle choisi, les
trois modes stricts du correcteur direct Qwen et les contrôles `UpdateChecks`
passent aussi. Le tunnel WireGuard est réel et authentifié ; ses réponses
sont synthétiques. Le processus du modèle local reste chargé et inchangé.

Les [empreintes et compteurs](../preuves/model-picker-fix-20261011/android-release.json),
la [preuve WebView](../preuves/model-picker-fix-20261011/android-webview-picker.json)
et le [rapport Android](../preuves/model-picker-fix-20261011/ANDROID.md)
précisent les contrôles et leurs limites. Les essais physiques ARM64,
une conversation HTTPS authentifiée et la mesure acoustique de la dictée
ne sont pas refaits. Cette version est publiée avec Windows/serveur 3.5.26 ;
les [téléchargements authentifiés](../preuves/model-picker-fix-20261011/delivery-validation.json)
concordent avec les empreintes signées.

## Version 1.0.8 — choix du modèle par conversation

APK Release **1.0.8**, code **9**, publié avec le certificat de distribution
existant. Les **29 vérifications** passent : compilation et analyse Android,
13 tests de distribution, signature v2/v3, alignement 16 Ko, ressources vocales
et bibliothèques natives identiques bit à bit à l’APK 1.0.7, sources de
l’interface concordantes avec le paquet.

Le Release signé a été mis à jour depuis 1.0.7 sur l’émulateur téléphone Android
16 x86_64. Six groupes natifs vérifient le catalogue multi-fournisseurs avec
Qwen local déchargé, le maintien de la connexion après une erreur locale du
correcteur, la conservation chiffrée du modèle et les scopes de fusion, le
modèle transmis dans le contexte et le chat, la réponse SSE complète et un
modèle retiré sans substitution. Le catalogue reste consultable lorsque tous
les modèles sont indisponibles. Les trois modes directs du correcteur et les
contrôles natifs `UpdateChecks` réussissent également.

Les [empreintes et compteurs](../preuves/model-selector-20261011/android-release.json)
et le [rapport Android](../preuves/model-selector-20261011/ANDROID.md) précisent
les contrôles réels et leurs limites. Les fournisseurs répondent dans une
fixture synthétique isolée ; le tunnel WireGuard et le proxy Android sont réels.
Aucune inférence externe ni nouvelle mesure acoustique de la dictée n’est
revendiquée. Les essais physiques ARM64 et une conversation HTTPS authentifiée
restent distincts. Les instrumentations et profils synthétiques ont été retirés.
La publication est coordonnée avec la livraison Windows/serveur 3.5.25.

## Version 1.0.7 — correcteur direct Qwen

APK Release **1.0.7**, code **8**, publié avec le certificat de distribution
existant, signature v2/v3 et alignement 16 Ko vérifiés. `assembleRelease`,
`lintRelease`, `assembleDebugAndroidTest` et les **13 tests de distribution**
réussissent. Les ressources de l’interface et du correcteur adaptées à Android
correspondent à celles incluses dans l’APK. Toutes les bibliothèques natives
et le manifeste Whisper Small sont identiques bit à bit à l’APK 1.0.6.

Les trois modes **Corriger**, **Reformuler professionnel** et **Reformuler
amical** ont été exécutés sur le Release signé, après sa mise à jour depuis
1.0.5 sur l’émulateur téléphone Android 16 x86_64. Le vrai proxy natif et
le tunnel WireGuard transmettent le contrat strict `text_transform: {mode,
text}` au serveur synthétique isolé et reçoivent une réponse SSE complète.
Le serveur de test refuse les champs hors contrat ; chaque mode est reçu
exactement une fois et aucune authentification n’est rejetée. Les exports
de profils synthétiques et l’instrumentation ont été retirés après l’essai.

Les **22 vérifications**, empreintes et limites sont dans
[android-release.json](../preuves/direct-corrector-20261011/android-release.json)
et le [rapport Android](../preuves/direct-corrector-20261011/ANDROID.md).
Cette validation ciblée n’effectue aucun appel au modèle ni nouvelle mesure
acoustique de la dictée. Les essais physiques ARM64 restent distincts.
La publication de l’APK et le rechargement du serveur ont été coordonnés avec
la livraison Windows 3.5.24 ; les téléchargements authentifiés sont vérifiés
dans le [rapport global](../preuves/direct-corrector-20261011/VALIDATION.md).

## Version 1.0.6 — conversations Hermes

APK Release **1.0.6**, code **7**, construit avec le même certificat depuis
1.0.0. Le protocole conversationnel 4, les demandes d’accord, la récupération
des réponses après coupure et le parcours existant de mise à jour sont
intégrés. La compilation, l’analyse Android, les 13 tests de distribution,
la signature v2/v3 et l’alignement 16 Ko sont validés.

Les parcours d’interface téléphone et tablette ont été vérifiés avec des
serveurs synthétiques isolés, y compris accord/refus, reprise et arrêt.
Les empreintes finales et limites des essais sont dans le
[rapport clients Hermes](../preuves/hermes-fred/CLIENTS.md) et ses
[métadonnées de build](../preuves/hermes-fred/clients-build-20261011.json).
Les paquets sont préparés dans un staging ; aucun appareil utilisateur n’a
été installé ou mis à jour pendant ces essais.

Les tests utilisent des profils, historiques et serveurs synthétiques isolés.
Aucun compte réel, pair actif ou coffre du serveur utilisateur n’a été modifié.

## Historique de la version 1.0.2 — lots 6 et 8

APK signé **1.0.2**, code **3**, **8 505 669 octets**, SHA-256
`cf400128ca9714a84b57016daa3b4c339411dd7d86b2aaea2eff88a19abc6dd3`.
Le certificat est conservé depuis 1.0.0. La livraison finale et ses empreintes
sont dans le [rapport Android des lots 6 et 8](../preuves/lots-6-8/android/VALIDATION.md)
et les [métadonnées vérifiées](../preuves/lots-6-8/android/delivery.json).

Construction Release/Debug/instrumentation et analyses Android réussies ;
quatre suites natives avec permission refusée puis accordée et deux parcours
WireGuard réel réussis. Vingt-six contrôles WebView téléphone/tablette sont
réussis sans exception JavaScript : citations avec page/version/extrait réels,
sources modifiées/supprimées, Retour, boîte persistante et lecture/préférences
serveur, effet réel du réglage son/silence sur Android. Les dialogues Android,
le rattrapage après arrêt et les clics système sont vérifiés sur les deux formats.
Le Release signé a été mis à jour depuis 1.0.1 avec profil, mode et conversation
synthétiques conservés ; `DEBUGGABLE` absent.

Les canaux de notification respectent les réglages Android et affichent
uniquement du texte générique. La sélection réelle du canal et son URI de son
sont contrôlées ; aucun test de haut-parleur physique n’est revendiqué.
Il n’y a pas de push externe lorsque l’application est totalement arrêtée.
Les émulateurs Android 16 sont x86_64 ; essais physiques ARM64 et conversation
HTTPS avec compte autorisé restent à effectuer.

## Historique de la version 1.0.1 — lots 0 à 4

APK livré : `dist/Acces-serveur-Fred-Android.apk`, **1.0.1**, code de version
**2**, **8 493 381 octets**. Android 8 minimum (API 26), cible API 36,
moteurs ARM64 et x86_64 ; les appareils limités aux applications 32 bits
ne sont pas pris en charge.

SHA-256 de l’APK :
`a0cdb80a49c892f38b647aaa6d300398cac53b1eee64727636594f0fb9bf5751`.
Empreinte SHA-256 du certificat de signature, conservé depuis la version 1.0.0 :
`40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`.

| Contrôle refait sur 1.0.1 | Résultat et preuve |
| --- | --- |
| Construction du Release | Build final réussi, 13 tests Python de profils, licences et distribution réussis ; signature RSA 3072 v2/v3 et alignement 16 Ko vérifiés ([journal](../preuves/lots-0-4/android-1.0.1-build-final.log)) |
| Debug, instrumentation et analyse | `assembleDebug`, `assembleDebugAndroidTest` et `lintRelease` réussis ([journal](../preuves/lots-0-4/android-1.0.1-debug-lint.log)) |
| Stockage, import et synchronisation natifs | Android Keystore/AES-GCM, altérations rejetées, imports JSON/EXE synthétiques, conflits de synchronisation, API locale et limite WireGuard de 2 Mo : contrôles réussis sur téléphone et tablette ([téléphone](../preuves/lots-0-4/lots-core-5554.log), [tablette](../preuves/lots-0-4/lots-core-5556.log)) |
| Restauration de l’historique | Nouvelle génération serveur détectée ; ancien historique non renvoyé avant confirmation explicite ; après confirmation, la copie chiffrée de l’ancien historique local reste déchiffrable, vérifié sur les deux émulateurs dans les journaux natifs ci-dessus |
| WireGuard Android réel | Moteur natif Android → serveur Go Windows isolé : modèles, réponse SSE progressive jusqu’à `[DONE]` et déclaration authentifiée `POST /v1/device` réussis sur les deux formats ([téléphone](../preuves/lots-0-4/lots-udp-5554.log), [tablette](../preuves/lots-0-4/lots-udp-5556.log), [requêtes reçues](../preuves/lots-0-4/android-device-fixture-counts.json)) |
| Release signé installé | APK 1.0.1 installé sur les deux émulateurs ; version/code confirmés, drapeau `DEBUGGABLE` absent, `fred_demo=true` ignoré et import obligatoire ([téléphone](../preuves/lots-0-4/lots-release-5554.log), [tablette](../preuves/lots-0-4/lots-release-5556.log)) |
| Gestion d’appareils côté serveur | 17 tests réussis : profils Android directs chiffrés, révocation durable, session et flux interrompus, suspension/réactivation, remplacement et conservation des autres accès ([journal](../preuves/lots-0-4/device-tests-final.log)) |

Captures du Release 1.0.1 :
[premier lancement téléphone](../preuves/lots-0-4/lots-release-5554.png) et
[premier lancement tablette](../preuves/lots-0-4/lots-release-5556.png).
Le [rapport de livraison](../preuves/lots-0-4/client-delivery-evidence.json)
conserve les versions, empreintes et limites de ces contrôles.

Les tests natifs sont exécutés avec l’instrumentation Debug, les mêmes
classes de production et des fixtures isolées réservées au Debug.
Le Release signé est installé et vérifié séparément. Les deux émulateurs
Android 16 utilisent x86_64 ; le moteur ARM64 est compilé, mais les essais
sur téléphone ou tablette physique ARM64 restent à effectuer. Une
conversation HTTPS avec un compte autorisé reste également à vérifier.
Les essais d’interface détaillés ci-dessous concernent la version 1.0.0
et n’ont pas tous été répétés sur 1.0.1.

## Historique des essais de la version 1.0.0

| Contrôle effectué | Résultat vérifié |
| --- | --- |
| Compilation Debug et APK de tests | `assembleDebug` et `assembleDebugAndroidTest` réussis |
| APK Release final | Compilation réussie, signature locale RSA 3072 vérifiée en v2/v3, APK aligné sur 16 Ko ; profils personnels absents, licences et deux architectures incluses |
| Moteurs natifs | ARM64 et x86_64 : tous les segments ELF `LOAD` sont alignés sur `0x4000` (16 Ko) |
| Analyse Android | `lintRelease` réussi |
| Export et licences | 13 tests Python réussis ; ACL Windows réelles, profils invalides sans secrets dans les erreurs, licences complètes et versions des dépendances |
| Signature locale | Test sur APK de contrôle réussi sous PowerShell 5.1 et 7 : RSA 3072, signatures v2/v3, alignement 16 Ko, clé réutilisée, mot de passe DPAPI et environnement nettoyé |
| Tests natifs téléphone et tablette | Instrumentation réussie sur les deux émulateurs Android 16 |
| Stockage natif | Android Keystore et AES-GCM, rejet des altérations, conservation du fichier lors d’un échec de lecture |
| Import | Profils JSON et footer d’EXE personnels synthétiques acceptés ; entrées invalides rejetées |
| Historique | Branches concurrentes conservées ; un conflit `409` reste en attente après upload seul, puis est traité par la synchronisation explicite |
| API locale | Authentification locale, contrôles `Host` et `Origin`, erreurs nettoyées et réponse JSON de secours |
| WireGuard natif réel | Bridge PIE Android → serveur Go Windows isolé, deux pairs distincts : liste des modèles et POST avec SSE progressif jusqu’à `[DONE]` réussis sur téléphone et tablette |
| Limite WireGuard | Sur l’APK final téléphone et tablette, requêtes de chat et de contexte dépassant 2 Mo : erreur JSON `413` structurée, sans modifier l’historique chiffré existant |
| HTTPS public | Vérification TLS de `ia.karenax.net`, puis GET `/v1/models` sans authentification : réponse `401` attendue sur téléphone et tablette |
| Interface Debug via WireGuard | Téléphone : réponse SSE rendue en Markdown, sauvegarde de l’historique et conservation après redémarrage réussies |
| Première passe interface navigateur | SSE, espaces de travail, création/lecture/modification/suppression de documents UTF-8, correcteur, tâches et annulation, historique et préférences ; aucune erreur JavaScript ni débordement détectés |
| Interface WebView finale téléphone/tablette | Huit groupes de contrôles réussis sur les deux émulateurs : SSE et Markdown, jauge de contexte, documents UTF-8, tâches, correcteur SSE/JSON, annulation et conservation du texte partiel ; aucune erreur JavaScript ni débordement |
| Installation Release | Même APK signé installé sur téléphone et tablette ; `fred_demo=true` est ignoré et l’import du profil reste obligatoire |
| Accès Release sur tablette | Import JSON par le sélecteur Android, choix explicite WireGuard et connexion au modèle du serveur de test réussis |
| Accès Release sur téléphone | Import d’un EXE personnel synthétique par le sélecteur Android, choix explicite WireGuard et connexion au modèle du serveur de test réussis |
| Export Release sur tablette | Sélecteur `ACTION_CREATE_DOCUMENT`, historique JSON UTF-8 enregistré puis relu avec succès |
| Mise à jour Release finale | Réinstallation du même APK signé avec `adb install -r` réussie sur téléphone et tablette ; profil, mode de connexion, historique chiffré et réponse Markdown conservés |
| Clavier Android réel | Téléphone et tablette : le clavier réduit la hauteur de la WebView, le champ de saisie et Envoyer restent visibles, puis la hauteur est restaurée à la fermeture |
| Fermeture native | Sur les deux formats, le geste Retour ouvre la confirmation ; un échec d’enregistrement refuse de quitter avec « Enregistrement non confirmé » ; la fermeture normale puis la reprise conservent la même empreinte du fichier d’historique chiffré |

Ancien APK 1.0.0 archivé dans
`toolchain/releases-staging/android-1.0.0/Acces-serveur-Fred-Android.apk`,
**8 493 381 octets**.
SHA-256 : `4af4c6ceec76894599b45a31cb2a4f4d883534a821f16ab2561c792b99200670`.
Empreinte SHA-256 du certificat de signature :
`40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`.

Captures stables de la WebView Android en mode de test :
[conversation téléphone](validation/phone-conversation.png),
[conversation tablette](validation/tablet-conversation.png),
[document téléphone](validation/phone-projet-document.png),
[document tablette](validation/tablet-projet-document.png),
[correcteur téléphone](validation/phone-correcteur.png),
[correcteur tablette](validation/tablet-correcteur.png),
[tâches téléphone](validation/phone-taches.png) et
[tâches tablette](validation/tablet-taches.png).
Captures du Release 1.0.0 :
[import initial téléphone](validation/phone-release-onboarding.png),
[import initial tablette](validation/tablet-release-onboarding.png),
[choix de connexion tablette](validation/tablet-release-choice.png),
[connexion téléphone](validation/phone-release-connected.png) et
[connexion tablette](validation/tablet-release-connected.png).
Clavier natif : [téléphone](validation/phone-keyboard-native.png) et
[tablette](validation/tablet-keyboard-native.png).
Confirmation de fermeture : [téléphone](validation/phone-close-native.png) et
[tablette](validation/tablet-close-native.png).
Refus de quitter après échec d’enregistrement :
[téléphone](validation/phone-close-blocked-native.png) et
[tablette](validation/tablet-close-blocked-native.png).
Rapports de ces contrôles :
[clavier téléphone](validation/phone-keyboard-result.json),
[clavier tablette](validation/tablet-keyboard-result.json),
[fermeture téléphone](validation/phone-close-result.json) et
[fermeture tablette](validation/tablet-close-result.json).
Le [dernier rapport WireGuard](validation/wireguard-ui-result.json) conserve
le résultat du dernier contrôle ; les deux émulateurs ont été vérifiés.

Pour relancer l’instrumentation sur un émulateur où les APK Debug et de
tests sont installés :

```powershell
adb -s IDENTIFIANT_EMULATEUR shell am instrument -w `
  net.karenax.fred.test/net.karenax.fred.SelfTestInstrumentation
```

Restent à vérifier les essais sur un téléphone ou une tablette physique ARM64
et une conversation HTTPS avec un compte autorisé. La requête HTTPS sans identifiant
vérifie le transport et le refus d’accès ; elle ne valide pas une conversation
HTTPS avec un compte réel.

## Inspection WebView du Release : limite des émulateurs

Le Release contient `BuildConfig.DEBUG=false`, son manifeste ne porte
pas le drapeau `DEBUGGABLE`, et l’argument de lancement `fred_demo=true` est
ignoré : le premier lancement affiche l’import obligatoire du profil.
L’application appelle explicitement
`WebView.setWebContentsDebuggingEnabled(false)` dans cette variante.

Les deux images SDK utilisées pour ces essais ont `ro.build.type=userdebug` et
`ro.debuggable=1`, avec Google WebView `133.0.6943.137`. Dans cette version,
le fournisseur WebView active lui-même l’inspection lorsque le système
Android est `userdebug` ou `eng`, puis ignore les demandes de désactivation
de l’application. Cela explique la présence du socket DevTools sur ces
émulateurs après installation de l’APK Release. Le comportement est vérifié
dans les sources officielles correspondant exactement à la version installée :
[détection du système de développement](https://chromium.googlesource.com/chromium/src/+/refs/tags/133.0.6943.137/base/android/java/src/org/chromium/base/BuildInfo.java),
[activation dans WebViewChromiumAwInit](https://chromium.googlesource.com/chromium/src/+/refs/tags/133.0.6943.137/android_webview/glue/java/src/com/android/webview/chromium/WebViewChromiumAwInit.java),
[demande de désactivation ignorée dans SharedStatics](https://chromium.googlesource.com/chromium/src/+/refs/tags/133.0.6943.137/android_webview/glue/java/src/com/android/webview/chromium/SharedStatics.java).

Les contrôles du build Release sont donc confirmés, tandis que l’absence
effective de socket DevTools reste à vérifier sur un appareil utilisant
une version Android de production (`user`). Aucune modification du
fournisseur système ni contournement par réflexion n’a été ajouté à l’app.

La version 1.0.3 (code 4) ajoute la dictée locale Whisper Small. Sa compilation,
sa signature, sa mise à jour sans désinstallation sur les deux émulateurs,
la transcription JNI, l’installation/reprise du modèle et le comportement du
microphone sont documentés dans les [preuves vocales du 11 octobre 2026](../preuves/voix-small-20261011/VALIDATION.md).
