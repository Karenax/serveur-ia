# Preuves des notifications — lot 8

Validation du 10 octobre 2026, sur des dossiers temporaires, des identités et des ports locaux jetables. Aucun compte, réglage, modèle chargé ni document de production n’a été utilisé ou modifié.

| Contrôle | Résultat | Preuve |
| --- | --- | --- |
| Stockage, contrats et transport authentifié | 28 tests réussis en 16,441 s ; sources identiques avant/après | [Rapport](notifications-tests.json), [journal](notifications-tests.log) |
| Interruptions serveur et relances successives | 11 tests réussis en 7,554 s ; sources corrigées identiques avant/après | [Rapport](worker-recovery-tests.json), [journal](worker-recovery-tests.log) |
| Console réellement rendue, vrai Controller et SQLite | 11 scénarios réussis, aucune exception JavaScript | [Rapport console](notifications-ui.json) |
| Révocation entre lecture documentaire et premier flux SSE | 5 tests réussis en 5,619 s ; source corrigée identique avant/après | [Rapport](source-access-fence-tests.json), [journal](source-access-fence-tests.log) |
| Consultation visuelle | Quatre captures relues, bureau et largeur 390 pixels | Captures ci-dessous |

Les 21 tests de stockage vérifient la migration additive, la sauvegarde/restauration de la boîte avec les espaces, l’ordre par séquence persistante malgré un recul de l’horloge, le redémarrage, le rattrapage sur plusieurs pages et les nouvelles tentatives réseau. Ils contrôlent également la déduplication concurrente, les lectures idempotentes et synchronisées, les préférences persistantes, le refus d’une révision périmée, l’isolation des destinataires et les limites de conservation. Les abonnements et reçus disparaissent à la révocation, tandis que les données restent conservées et les accès désactivés sont refusés.

Les sept tests HTTP utilisent les vraies routes de la passerelle. Ils vérifient les réponses GET et POST, deux propriétaires authentifiés, l’isolation des alertes administratives, le refus de paramètres permettant de choisir un autre propriétaire, la limite de 64 Ko, les corps JSON invalides, le refus d’Origin, les réponses 401 après révocation et 503 pendant la maintenance. Une référence documentaire du lot 6 est consultable par son propriétaire, mais sa consultation depuis l’autre accès est refusée avec une réponse 403. Le déclenchement des quatre alertes d’exploitation est testé avec le véritable module de notifications, y compris la déduplication et l’absence de chemins ou de texte privé dans le résultat.

Les onze tests de reprise vérifient qu’une tâche en cours lors d’une interruption devient échouée avec son événement et sa notification dans la même transaction, sans relancer l’inférence. Une panne injectée pendant la publication annule ensemble ces trois changements. Une relance échouée après lecture du premier échec produit une nouvelle notification non lue ; les répétitions d’un événement de la même tentative gardent le même identifiant. Le compteur durable reste correct après recul de l’horloge, suppression du journal des événements, redémarrage et sauvegarde/restauration. Les compteurs corrompus ou sans tâche sont refusés à la restauration, leur taille entre dans le quota et ils disparaissent quand leurs tâches sont purgées. Une ancienne exécution annulée ne peut ni conclure la nouvelle tentative ni retirer son signal d’annulation. Le cas d’un accès révoqué avant une interruption utilise la vraie passerelle : réponse 401 pour l’ancien accès, réponse 403 depuis l’autre propriétaire, aucun appel au moteur.

La console teste le lien direct `#notifications`, la lecture persistante, le filtre des alertes non lues, les préférences par type, une panne réseau suivie du rattrapage, le refus d’une action en maintenance et son nouvel essai, ainsi que des alertes publiées pendant que la page est fermée. Le client privé créé dans cette instance conserve sa notification, qui n’apparaît jamais dans la boîte d’administration.

La revue d’intégration a identifié un changement d’accès possible pendant la préparation du contexte documentaire. Trois des cinq tests du flux SSE bloquent cette préparation après lecture d’extraits réels, puis révoquent, suspendent ou mettent l’accès en maintenance : aucun extrait ni aucune requête d’inférence n’est envoyé. Le quatrième suspend l’accès après émission autorisée des références et après l’attente dans la file ; le moteur n’est pas appelé. Le cinquième vérifie que le flux valide conserve ses références et sa réponse. Tous les scénarios retrouvent un compteur de demandes actives nul et une file vide. Ces tests utilisent leur propre modèle HTTP fictif et les vraies routes de la passerelle.

## Captures

- [Boîte d’administration sur bureau](01-console-notifications-desktop.png)
- [Préférences persistantes](02-console-notifications-preferences.png)
- [Toutes les alertes lues](03-console-notifications-toutes-lues.png)
- [Console à 390 pixels, après fermeture de la navigation](04-console-notifications-telephone.png)

## Contrat et limites vérifiées

Le stockage reste dans la base SQLite des espaces existants. Un événement et sa notification de tâche ou d’indexation sont inscrits dans la même transaction. Les identifiants sont stables et opaques ; aucun extrait de conversation, de document, titre personnel, secret d’accès ou URL externe ne figure dans la notification. Les cibles permises sont une tâche, un document ou la boîte, avec un contrôle des droits à la consultation de l’objet.

Les préférences désactivent les annonces sans supprimer les éléments consultables. La boîte retourne les identifiants lus et tous ceux encore conservés, pour synchroniser les lectures et retirer les notifications locales expirées. La génération serveur permet au client de renouveler ses curseurs et sa déduplication après une restauration. La conservation est limitée à 90 jours, 1 000 événements par accès et 20 000 sur le serveur ; les reçus de livraison sont supprimés avec leur événement.

La livraison couverte est celle des clients ouverts et connectés, avec rattrapage à la reconnexion. Aucun fournisseur de push externe n’est configuré. Une application Android totalement arrêtée ne peut pas être réveillée par cette seule boîte serveur ; ce fonctionnement reste le sous-lot distinct décrit dans le plan. Les tests de ce dossier ne prétendent pas valider le réveil en arrière-plan d’un téléphone physique ni un serveur HTTPS public.

Reproduction : `Strata-src\.venv\Scripts\python.exe lanceur\validate_notifications.py`, puis `node lanceur\web\tests\notifications_ui.mjs`, depuis la racine du projet. Les cas de reprise se rejouent avec `..\Strata-src\.venv\Scripts\python.exe -m unittest -v test_notifications_worker_recovery`, depuis `lanceur`. Le script navigateur utilise Chrome et le runtime Playwright local de cette machine. Les fixtures arrêtent leur serveur et leur navigateur puis suppriment leur stockage jetable.
