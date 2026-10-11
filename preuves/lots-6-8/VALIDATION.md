# Livraison des lots 6 et 8

Les deux lots ont été développés en parallèle : recherche documentaire avec passages cités, et notifications conservées côté serveur. Ce rapport rassemble les preuves des fonctions, des interfaces et de la mise en service. Le lot 9 est expliqué dans le plan et le mode d’emploi ; son implantation reste planifiée.

## Vérifications ciblées

| Périmètre | Résultat | Preuve |
| --- | --- | --- |
| Recherche, migrations, tâches, sauvegardes et restaurations | 94 tests réussis ; empreintes suivies inchangées | [Rapport recherche](recherche/validation.json), [détails](recherche/LISEZ-MOI.md) |
| Notifications, préférences et transport HTTP authentifié | 28 tests réussis ; sources suivies inchangées | [Rapport notifications](notifications/notifications-tests.json), [détails](notifications/INDEX.md) |
| Panne serveur, relances et ancienne exécution annulée | 11 tests réussis ; événement et notification atomiques, nouvelle alerte par tentative | [Rapport de reprise](notifications/worker-recovery-tests.json) |
| Révocation pendant la préparation d’une réponse avec sources | 5 tests réussis, sans extrait ni inférence après désactivation | [Rapport de sécurité](notifications/source-access-fence-tests.json) |
| Console d’administration réellement rendue | 11 scénarios réussis, aucune exception JavaScript ; quatre captures relues | [Rapport console](notifications/notifications-ui.json) |
| Client partagé, vrai serveur et tunnel WireGuard UDP | 16 scénarios réussis, aucune exception JavaScript ; neuf captures relues | [Rapport client](client-ui/client-lots6-8-ui.json), [journal](client-ui-tests.log) |
| Windows compilé | 3.5.18, autotest réussi, quatre ressources incorporées identiques aux sources finales | [Rapport Windows](windows-release.json), [compilation](windows-build.log) |
| Android signé et distribué | 1.0.2, code 3 ; quatre suites natives, deux tunnels réels, 26 contrôles WebView ; mise à jour conservant profil et conversation | [Rapport Android](android/VALIDATION.md), [métadonnées](android/delivery.json), [signature publiée](android-published-signature.txt) |
| Serveur réel | 3.5.18 actif, sauvegarde chiffrée vérifiée, modèle et données préexistantes préservés | [Mise en service](production-validation.json) |

## Recherche documentaire

Le jeu contrôlé de cinq questions retrouve cinq fois le bon document en première position et un extrait littéral contenant la réponse. Un document de 460 075 caractères est découpé en 288 passages : indexation 32,60 ms et recherche de l’information finale 9,22 ms dans cet essai. Un PDF réellement extrait sur deux pages en 294,92 ms fournit la citation attendue page 2. Ces mesures concernent ce corpus et ce poste.

Les références portent un identifiant opaque, le document, le projet, la révision, l’extrait et la page réelle lorsqu’elle est connue. Une consultation vérifie les droits. Une modification conserve le passage cité et signale la révision actuelle ; une suppression conserve l’extrait avec la mention indisponible. Les tâches conservent leurs références. Les tests couvrent aussi l’index périmé, les archives anciennes, les questions sans résultat et l’isolation de deux propriétaires.

## Notifications et interfaces

La boîte, les lectures et les préférences sont stockées dans SQLite et incluses dans la sauvegarde/restauration. Les événements de tâches et d’indexation sont enregistrés avec leur notification dans la même transaction. Une tâche interrompue au redémarrage est signalée sans rejouer l’inférence ; les relances disposent d’un compteur durable et d’une nouvelle notification par tentative. Les tests injectent une panne de publication et annulent une ancienne exécution pendant une relance. Les alertes d’exploitation sont réservées à l’administration et contiennent des phrases génériques.

Les parcours du client partagé passent par le vrai serveur Workspace et le pont WireGuard compilé pour cette livraison. Ils couvrent les références actuelles, modifiées et supprimées ; l’ouverture d’une tâche depuis sa notification ; les préférences ; le rattrapage de 110 événements ; la lecture depuis une autre session ; la reconnexion ; la révocation ; une notification expirée ; un accusé de livraison devenu périmé ; et un changement de génération entre deux pages. La vue de 390 pixels ne déborde pas horizontalement.

Les neuf captures du client ont été relues, dont [la recherche](client-ui/01-recherche-sources.png), [le passage cité](client-ui/02-passage-current.png), [la source modifiée](client-ui/03-source-modifiee.png), [les préférences](client-ui/05-inbox-preferences.png) et [la consultation sur téléphone](client-ui/08-mobile-passage.png).

## Mise en service préservant les données

La console a été redémarrée avec préservation de l’état du modèle. Les processus Strata 8200 et 14628, avec leurs dates de création, sont identiques. Les empreintes des réglages, des accès et des clés restent inchangées. Les lignes préexistantes des historiques, projets, documents, mémoires, conversations, règles et tâches ont les mêmes nombres et empreintes logiques avant/après la migration additive.

Une archive préalable et une nouvelle archive chiffrée vérifiée ont été créées. La programmation quotidienne à 03 h, sa conservation 7/4/6 et sa destination sur le serveur sont inchangées. Le manifeste Windows est signé et vérifié avec la clé existante. Les fichiers antérieurs sont conservés en staging pour retour éventuel. Aucun test de restauration n’a été exécuté sur les données réelles ; les essais de restauration utilisent des dossiers isolés.

## Contrôles finaux réussis

La suite globale a réussi : **246 tests en 354,218 s**, sans échec ni erreur, exécutés dans deux interpréteurs avec fixtures isolées. Les empreintes des sources produit et des fichiers de test sont identiques avant/après et correspondent aux fichiers actuels. Voir le [rapport complet](regressions-final.json), le [journal](regressions-final.log) et le [contrôle final de livraison](delivery-final-check.json). Les nombres des suites ciblées sont inclus dans les 246 tests et ne s’ajoutent pas à ce total. Les preuves Android sont terminées et rattachées à l’APK signé distribué : canaux silencieux/sonores, permission refusée ou accordée, rattrapage à la réouverture, clic réel sur une annonce système et mise à jour 1.0.1 → 1.0.2 sur téléphone et tablette. Les deux captures après mise à jour ont été relues, en complément des parcours de citation et de boîte.

Les fichiers prêts à utiliser sont [Windows 3.5.18](../../client-qwen/dist/Accès%20serveur%20Fred.exe) et [Android 1.0.2/code 3](../../client-android/dist/Acces-serveur-Fred-Android.apk). Leurs empreintes, signatures et ressources incorporées correspondent aux rapports vérifiés ; les versions précédentes sont conservées pour retour éventuel.

## Limites de la livraison

La boîte est consultable lorsque le client est connecté et se rattrape à sa prochaine ouverture. Aucun fournisseur externe de push n’est configuré et une application Android totalement arrêtée n’est pas réveillée. Les essais Android utilisent des émulateurs téléphone/tablette, sans prétendre valider la veille et la batterie d’appareils physiques. L’OCR et la recherche sémantique restent optionnels ; ce lot utilise l’index documentaire local existant. Le tableau de bord complet du lot 5 et les lots 7, 9 et 10 restent planifiés.

## Reproduction

Depuis `D:\Serveur IA` : `Strata-src\.venv\Scripts\python.exe lanceur\validate_lots6_8.py` pour la suite complète ; `Strata-src\.venv\Scripts\python.exe lanceur\validate_notifications.py` et `Strata-src\.venv\Scripts\python.exe preuves\lots-6-8\recherche\validate.py` pour les essais ciblés. Le navigateur se vérifie avec `node lanceur\web\tests\lots6_8_client_ui.mjs`. Le contrôle des fichiers publiés se rejoue avec `Strata-src\.venv\Scripts\python.exe lanceur\validate_delivery_lots6_8.py`. Ces tests utilisent des identités, documents, clés de fixture et ports temporaires. Les données réelles ne sont utilisées que par le script explicite de mise en service `lanceur\validate_live_lots6_8.py`, qui ne doit pas être confondu avec un test isolé.

Le [mode d’emploi](../../lanceur/RECHERCHE-NOTIFICATIONS.md), le [plan](../../PLAN-GLOBAL-SERVEUR-FRED.md) et le [contexte](../../CONTEXTE-PROJET.md) décrivent les fonctions et les décisions.
