# Dossiers des clients — validation du 11 octobre 2026

**En service.** Les deux accès enregistrés disposent d’un dossier privé sous `D:\Serveur IA\lanceur\donnees-clients\<identifiant>`. Les bases individuelles et fichiers sont synchronisés automatiquement. La console affiche les chemins complets dans Clients, Appareils et Espaces et fichiers, avec copie du chemin et mise à jour manuelle.

| Contrôle | Résultat | Preuve |
| --- | --- | --- |
| Stockage ciblé final | Neuf tests réussis : isolation des bases et fichiers, originaux, absence de jetons dans les JSON, profil DPAPI, conservation après renommage/archivage, suppression de fichiers gérés, réparation, mise à jour automatique/restauration, refus des jonctions et exports antérieurs à une restauration | [Journal](tests-cibles.txt), [tests](../../lanceur/test_client_storage.py) |
| Console Chrome | Sept scénarios réussis, aucune erreur JavaScript ; affichage dans trois rubriques, sélection du client, presse-papiers, mise à jour, petit écran et jeton administrateur obligatoire | [Résultats](console-validation.json), [capture](console-dossiers.png) |
| Régression générale | 268 tests exécutés ; 267 réussis au premier passage. Un contrôle de démarrage d’EXE a dépassé 60 s et laissé son processus d’essai verrouiller le fichier. Le même scénario repasse en 15,438 s lors du retest isolé. Le processus orphelin a été arrêté par son identité et son chemin de test vérifiés | [Passage complet](regression.txt), [retest réussi](retest-updater.txt) |
| Serveur réel | Deux dossiers prêts, toutes les empreintes de fichiers vérifiées ; intégrité SQLite et comparaison exacte de chaque table individuelle avec les seules lignes de son accès dans la base commune | [Contrôle réel](production-validation.json) |
| Conservation de l’existant | Processus Qwen, données logiques, accès, réglages et programmation des sauvegardes préservés. EG2 est prêt. La voix serveur existante reste prête | [Contrôle réel](production-validation.json) |
| Sauvegarde | Archives chiffrées vérifiées avant et après ; les dossiers se reconstruisent depuis les données originales déjà sauvegardées | [Archives et inventaires](production-validation.json) |

La régression générale a commencé avant les derniers contrôles de génération ; les neuf tests ciblés finaux couvrent ces ajustements. Le timeout du contrôle EXE n’a pas été reproduit lors du retest ; sa cause précise n’est pas établie. Les preuves gardent le résultat initial et le résultat du retest. Le dossier synthétique `lanceur/tmpaxzsojxu` subsiste : sa suppression a été refusée par le contrôle automatique avec le motif « blocked by policy ». Son processus est arrêté.

Les tests utilisent des identités et contenus synthétiques. Sur le serveur réel, seules les données déjà présentes ont été lues et exportées ; aucun client, projet ou souvenir de test n’a été ajouté. Les preuves contiennent des compteurs, chemins et empreintes, sans conversations, jetons ou clés privées.

## Portée

La base partagée reste la source transactionnelle. Chaque dossier contient une base autonome isolée et ses exports lisibles, tenus à jour automatiquement ; les fichiers manuels ne sont pas réimportés. Cette organisation ne remplace pas les sauvegardes chiffrées et n’ajoute pas de synchronisation des réglages/brouillons demeurés uniquement sur l’appareil. Les exécutables et modèles restent à leurs emplacements actuels.

Un fichier SQLite maintenu ouvert par un lecteur peut empêcher son remplacement sous Windows ; le serveur conserve ses données originales et retente la publication, avec erreur visible. Les volumes maximaux et le débit pendant des requêtes Qwen simultanées n’ont pas été mesurés pour ces nouveaux exports.

[Guide d’utilisation](../../lanceur/DOSSIERS-CLIENTS.md).
