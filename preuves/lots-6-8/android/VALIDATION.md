# Android 1.0.2 — preuves des lots 6 et 8

Le même APK signé fonctionne sur téléphone et tablette. La version **1.0.2**, code
**3**, est publiée dans [client-android/dist](../../../client-android/dist/Acces-serveur-Fred-Android.apk).
Son empreinte correspond à la release vérifiée en staging ; la [signature du fichier publié](../android-published-signature.txt)
utilise le certificat existant. Aucun profil utilisateur réel n’a été utilisé lors des essais.

- APK : **8 505 669 octets**.
- SHA-256 : `cf400128ca9714a84b57016daa3b4c339411dd7d86b2aaea2eff88a19abc6dd3`.
- Certificat conservé depuis 1.0.0 :
  `40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`.
- Android 8/API 26 minimum, cible API 36 ; moteurs ARM64 et x86_64.
- [Métadonnées, empreintes des sources incorporées et rapports](delivery.json).

| Contrôle final | Résultat et preuve |
| --- | --- |
| Release signé | Construction, 13 tests Python de livraison, signatures v2/v3, RSA 3072, alignement 16 Ko, licences et absence de profil personnel : PASS ([journal](android-1.0.2-build-final.log)) |
| Debug et instrumentation | Construction et `lintDebug` : PASS ([journal](android-1.0.2-gradle-final.log)) ; `lintRelease` : PASS ([journal](android-1.0.2-lint-release-final.log)) |
| Tests natifs avec permission refusée | Téléphone et tablette : PASS ([téléphone](lots6-8-core-denied-emulator-5554.log), [tablette](lots6-8-core-denied-emulator-5556.log)) |
| Tests natifs avec permission autorisée | Téléphone et tablette : PASS ([téléphone](lots6-8-core-granted-emulator-5554.log), [tablette](lots6-8-core-granted-emulator-5556.log)) |
| WireGuard Android réel | Exécutables natifs Android → serveur Go Windows isolé : modèles, SSE jusqu’à `[DONE]`, déclaration Android, sources PDF, boîte persistante/get/read : PASS ([téléphone](lots6-8-udp-emulator-5554.log), [tablette](lots6-8-udp-emulator-5556.log), [routes reçues](wireguard-request-counts.json)) |
| Interface réelle téléphone/tablette | **13 contrôles par format**, soit 26, aucune exception JavaScript : PASS ([téléphone](phone-ui.json), [tablette](tablet-ui.json)) |
| Permission demandée au clic | Dialogue Android réel, refus puis accord ; boîte serveur toujours disponible : PASS ([refus téléphone](phone-denied.json), [accord téléphone](phone-granted.json), [refus tablette](tablet-denied.json), [accord tablette](tablet-granted.json)) |
| Application arrêtée puis rouverte | Événement publié pendant l’arrêt, retrouvé à l’ouverture : PASS ([téléphone](phone-reconnected.json), [tablette](tablet-reconnected.json)) |
| Clic système | Clic réel dans le tiroir Android, tablette depuis l’écran d’accueil ; bon résultat ouvert et lu sur serveur : PASS ([téléphone](phone-system-click.json), [tablette](tablet-system-click.json)) |
| Mise à jour signée 1.0.1 → 1.0.2 | Installation avec la même clé, profil chiffré, choix WireGuard et conversation synthétique conservés ; version/code confirmés et `DEBUGGABLE` absent : PASS ([téléphone](phone-release-upgrade.log), [tablette](tablet-release-upgrade.log)) |
| Nouveau lancement Release | État vierge, argument `fred_demo=true` ignoré, import d’un vrai profil obligatoire : PASS ([téléphone](phone-release-fresh.log), [tablette](tablet-release-fresh.log)) |

Les suites natives vérifient aussi AES-GCM et altérations, imports JSON/EXE,
conflits d’historique, API locale protégée, garde de restauration avec copie
locale déchiffrable et refus des corps WireGuard dépassant 2 Mo. Une cache
optionnelle d’alertes illisible conserve son fichier et ne bloque pas le client.

L’interface a interrogé les vrais modules `Workspace` et `Notifications` d’un
serveur isolé, par le vrai tunnel. Le PDF contient deux pages réelles ; le passage
cité est extrait de la page 2 avec sa version et son texte. Les notes n’inventent
aucune page. Une source modifiée ou supprimée conserve son ancien extrait et
signale son état. Les sources des tâches restent cliquables et Retour ferme le
passage. Les préférences par type, la lecture et l’absence de doublons sont
vérifiées côté serveur. La tâche terminée est une fixture de résultat ; aucun
raisonnement de modèle réel n’est revendiqué.

Captures : [PDF téléphone](phone-pdf-source.png), [PDF tablette](tablet-pdf-source.png),
[document modifié](phone-source-modified.png), [document supprimé](phone-source-unavailable.png),
[notification téléphone](phone-system-notifications.png),
[notification tablette](tablet-system-notifications.png),
[Release après mise à jour téléphone](phone-release-after-upgrade.png),
[Release après mise à jour tablette](tablet-release-after-upgrade.png).

Le réglage serveur **Alertes discrètes** choisit les prochaines alertes : canal
`fred_results` silencieux si coché, `fred_results_standard` avec le son Android
si décoché. `preferences.discreet` prévaut sur `subscription.discreet` ; ce
dernier sert uniquement de repli si la préférence globale manque. Un payload
partiel sans réglage conserve la dernière valeur. Deux canaux sont nécessaires,
car Android conserve leurs choix de son après création. Les réglages système de
l’utilisateur restent prioritaires. Les tests vérifient URI de son nulle ou
présente, sélection du canal réellement posté, effet de la checkbox serveur,
persistance, refus de permission et changement de mode sans doublon.

Le texte système est fixe et générique, y compris pour la version publique sur
écran verrouillé. Le clic transporte seulement un identifiant opaque puis relit
sa destination après authentification. Un rattrapage crée au maximum une alerte,
vingt alertes au maximum sont conservées. Lecture, révocation et expiration
annulent les alertes correspondantes.

Les essais utilisent deux émulateurs Android 16/API 36 **x86_64**. Le moteur
ARM64 est compilé ; essais physiques ARM64, veille/batterie et conversation HTTPS
avec compte autorisé restent à effectuer. La sortie audible des haut-parleurs
n’est pas mesurée sur ces émulateurs sans audio ; configuration et sélection
des canaux sont vérifiées. Cette livraison reçoit pendant l’utilisation et
rattrape à l’ouverture. Aucun push externe pour une application totalement
arrêtée n’est configuré.
