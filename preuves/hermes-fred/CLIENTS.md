# Clients Hermes — 11 octobre 2026

Windows **3.5.22** et Android **1.0.6**, code **7**, annoncent le protocole
conversationnel **4**. Le format **3** des manifestes Windows de mise à jour
est conservé pour permettre aux versions précédentes de télécharger la
nouvelle application. Les profils existants restent compatibles.

La validation client prépare les paquets dans
`toolchain/releases-staging/hermes-fred-20261011/`. Leur publication sur le
serveur est ensuite contrôlée dans [delivery-validation.json](delivery-validation.json).
Aucune installation sur un poste ou appareil utilisateur n’est effectuée par
ces essais.

## Comportement vérifié

- Les conversations et le correcteur transmettent leur identifiant de
  discussion, un identifiant distinct pour chaque tour et la révision
  d’historique. Le tour est conservé localement avant l’envoi.
- La progression des outils et les demandes d’accord restent en dehors du
  texte de la réponse. La voix reçoit la réponse finale.
- L’accord est limité à l’action présentée ; son effet est affiché en texte
  simple, avec les choix d’autoriser une fois ou de refuser.
- Une coupure du flux et le redémarrage de l’interface récupèrent le résultat
  serveur par son identifiant, sans doublon ni nouvelle exécution.
- Une demande d’accord en attente est également retrouvée après redémarrage.
  Son reçu opaque reste valide pendant les messages de maintien de connexion ;
  la reprise suit la même exécution jusqu’à son état final.
- La réponse finale remplace la copie locale partielle lorsque les
  identifiants, le message utilisateur et la discussion concordent. Les
  modifications hors ligne concurrentes conservent le mécanisme de copie.
- L’arrêt attend l’accusé de réception serveur avant d’interrompre le flux
  local. Le téléchargement et l’installation Android restent disponibles
  dans le parcours de mise à jour existant.

## Contrôles

| Contrôle | Résultat |
| --- | --- |
| Interface Windows avec serveur SSE synthétique | Identifiants, voix finale, reçus d’accord opaques, heartbeat, accord/refus, coupure et redémarrage avec texte partiel, suivi de la même exécution et correcteur réussis (`client-qwen/test_hermes_ui.cjs`) |
| Interface Android téléphone et tablette | Flux, heartbeat, accord/refus, coupure et reprise d’accord dans le même projet, arrêt, correcteur, mises à jour et parcours existants réussis (`client-android/scripts/Test-Assets.cjs`) |
| Historique et distribution Windows | 7 tests réussis : récupération, protection des autres modifications, identifiants bornés, manifeste Ed25519 et formats compatibles |
| Historique serveur existant | 16 tests `test_history_sync` et `test_chat_356` réussis |
| Distribution Android | 13 tests de profils, licences et distribution réussis pendant le build final |
| Windows embarqué | Auto-test natif sans ouverture de l’interface réussi ; 5 fichiers d’interface, bridge Go et 481 fichiers de voix vérifiés par empreinte |
| Android Release | Compilation, `lintRelease`, package et assets vérifiés ; signature APK v2/v3 et alignement 16 Ko valides |

L’analyse Android a également permis de corriger une vérification de permission
préexistante : la dictée revérifie maintenant l’accord microphone au moment de
l’ouverture de `AudioRecord`, après le lancement de son worker.

Les [métadonnées finales](clients-build-20261011.json) donnent les empreintes,
tailles, versions et signatures vérifiées. Les builds et les journaux de
construction sont conservés dans le staging indiqué ci-dessus.

Le manifeste Windows est signé Ed25519 avec la clé de distribution existante.
Ce contrôle ne constitue pas une signature Authenticode de l’EXE. L’APK utilise
le certificat conservé depuis Android 1.0.0, empreinte SHA-256
`40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`.

Les essais d’interface utilisent des serveurs de test isolés. Le client
Android ARM64 est compilé ; aucune installation sur l’appareil physique de
l’utilisateur ni conversation avec son compte réel n’est revendiquée ici.
