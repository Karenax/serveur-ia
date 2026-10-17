# Plan global du serveur Fred et de ses clients

Date : 11 octobre 2026. Statut : lots **0 à 4 achevés, validés et en service** — 191 tests réussis, 32 scénarios console et essais Android téléphone/tablette sur émulateurs. Les **lots 6 et 8 sont achevés, validés et en service**, développés en parallèle : **246 tests de régression réussis**, 27 scénarios navigateur et essais Android sur émulateurs téléphone/tablette. Hermes est activé pour les conversations et les outils Fred autorisés. La refonte du tableau de bord du lot 5 et les extensions des lots 9/10 restent planifiées ; le lot 7 comprend désormais la dictée Windows/Android et la conversation Windows.

## Demande et décisions

Le périmètre comprend les sept axes proposés : sauvegardes automatiques et restauration, gestion des appareils, tableau de bord, recherche documentaire avec sources, messages vocaux et lecture des réponses, notifications, outils pour l’assistant.

Les sauvegardes et autorisations d’appareils sont exécutées côté serveur et administrées depuis la console locale. Aucun client ouvert n’est requis pour les sauvegardes. Le serveur reste responsable des données, droits, traitements et travaux persistants ; Windows et Android fournissent les interactions nécessaires : microphone, lecture audio, affichage des sources, notifications et demandes de validation.

Développer par lots utilisables, sans remplacer le stockage ni refaire la console. Préserver les accès, projets et historiques actuels. Après les cinq premiers lots, l’utilisateur a autorisé **les lots 6 et 8 en parallèle** et demandé une **explication du lot 9**. Une demande ultérieure autorise l’intégration complète de Hermes et des outils Fred contrôlés ; les outils système libres et connecteurs externes ne sont pas activés. Le journal minimal d’événements nécessaire aux notifications est intégré au périmètre des lots 6/8 ; il ne constitue pas la refonte du tableau de bord prévue au lot 5.

Livraison des lots 0–4 à l’époque : serveur et Windows **3.5.24**, Android **1.0.7, code 8**. Pour la version en service après l’audit, consulter le [contexte actuel](CONTEXTE-PROJET.md) et la [preuve de livraison](audits/2026-10-12/VALIDATION-CORRECTIONS.md). Les trois boutons du correcteur utilisent directement Qwen ; les conversations et tâches conservent Hermes. Sauvegardes actives chaque jour à 03 h avec conservation 7/4/6, sur le serveur selon le choix du demandeur ; deuxième destination laissée vide. Le modèle chargé et les clés existantes ont été préservés lors de la mise en service. Voir le [mode d’emploi](lanceur/SAUVEGARDES-APPAREILS.md), le [rapport de validation](preuves/lots-0-4/VALIDATION.md) et le [contexte](CONTEXTE-PROJET.md).

Livraison des lots 6/8 : EXE et APK publiés, signés avec les clés existantes, ressources incorporées vérifiées et mise à jour Android conservant profil et conversation. Le [rapport final](preuves/lots-6-8/VALIDATION.md) et le [contrôle de livraison](preuves/lots-6-8/delivery-final-check.json) rassemblent les preuves effectives. Le serveur a été rechargé sans arrêter les processus du modèle ; données, accès, clés et programmation des sauvegardes sont préservés.

## État constaté

| Axe | Existant vérifié | Travail à prévoir |
| --- | --- | --- |
| Sauvegardes | Archives chiffrées vérifiées, catalogue, programmation et rattrapage, conservation 7/4/6, seconde copie avec reprise, restauration guidée et retour après interruption | Restauration sélective ; validation NAS physique et volumes maximaux ; service avant ouverture de session si demandé |
| Appareils | Fiches PC/téléphone/tablette, propriétaire/version/activité, profil Android direct, suspension/expiration, révocation durable, remplacement et archivage conservant les données ; abonnements de notifications privés implantés | Partage d’un espace après migration explicite |
| Tableau de bord | État du modèle, RAM/GPU, file d’attente et diagnostic ; socle minimal d’événements persistants utilisé par les notifications | Refonte consolidée, historique court, cartes de santé : lot 5 complet planifié |
| Documents et mémoire | Import TXT/MD/DOCX/PDF texte, recherche FTS5 et sémantique EG2 sur CPU, passages vérifiés ; connaissances par projet et hors projet isolées par accès ; sources conservées avec tâches | OCR optionnel ; mesures de concurrence EG2/Qwen à approfondir |
| Voix | Dictée locale Small Windows/Android ; conversation Windows 3.5.30 directement vers Qwen, Zipformer/Silero/Smart Turn local et Pocket TTS CPU serveur ; capture AEC et reprise corrigées | Conversation Android différée ; qualité ASR humaine et mesures acoustiques dans la pièce |
| Notifications | Boîte SQLite persistante, événements dédupliqués, lecture/préférences/abonnements/reçus, console administrative et clients Windows/Android publiés ; rattrapage à la reconnexion | Réveil Android totalement arrêté comme sous-lot distinct, aucun push externe configuré |
| Outils | Recherche web et lecture d’URL publiques, documents/mémoire et tâches ; outils hôte désactivés sur la passerelle | Registre d’outils serveur autorisés, contrôles par utilisateur, validation des actions |

Modules principaux : `lanceur/operations.py`, `workspace.py`, `notifications.py`, `remote.py`, `accounts.py`, `wireguard_access.py`, `app.py`, `lanceur/web/`, `client-qwen/`, `client-android/`.

Orientation demandée le 11 octobre 2026 : faire traiter toutes les conversations clientes par Hermes, déjà installé sur ce PC, et créer automatiquement un profil Hermes à la création de chaque accès. Le [plan d’intégration Hermes/Fred](PLAN-INTEGRATION-HERMES-FRED.md) définit l’architecture, les sessions, les outils, la migration et les lots H0 à H6. L’intégration est implantée et activée, avec profil par accès, session par conversation et projet natif par projet Fred. Les essais avec le Qwen local, les clients signés et les contrôles de livraison sont dans [les preuves](preuves/hermes-fred/VALIDATION.md). Les outils système libres restent désactivés.

## Lots et dépendances

| Lot | Résultat livrable | Dépendances | Statut |
| --- | --- | --- | --- |
| 0 | Inventaire, migrations et règles communes | Aucune | Achevé et validé |
| 1 | Sauvegarde complète vérifiée et catalogue | 0 | Achevé et validé |
| 2 | Sauvegardes automatiques, conservation et seconde copie | 1 | Achevé et validé |
| 3 | Restauration guidée et reprise après incident | 1, 2 | Achevé et validé |
| 4 | Gestion des appareils et profil Android direct | 0 ; articulation avec 3 | Achevé et validé |
| 5 | Tableau de bord consolidé et événements internes | 2, 3, 4 | Refonte planifiée ; socle d’événements minimal intégré pour 8 |
| 6 | Recherche documentaire et sources améliorées | 0 ; alimentation des états de 5 | Achevé, validé et en service sur Windows et Android |
| 7 | Messages vocaux et lecture des réponses | 0, 4, 5 | Dictée Windows/Android et conversation Windows livrées ; conversation Android différée |
| 8 | Notifications persistantes et livraison aux appareils | 4 ; socle d’événements de 5 ; événements de 6, puis 7 quand implanté | Achevé, validé et en service ; livraison connectée et rattrapage |
| 9 | Outils serveur et validation des actions | 4, 5, 6, 8 | Outils Fred contrôlés via Hermes livrés ; outils système et actions externes différés |
| 10 | Récupération complète, compatibilité et livraison globale | 1 à 9 | Planifié |

L’ordre initial était 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10. La demande initiale a priorisé **6 et 8 en parallèle**, avec le socle d’événements strictement nécessaire ; le tableau de bord complet reste planifié ; la dictée locale et la conversation Windows sont livrées. Chaque lot a sa propre validation ; le lot 10 vérifiera tous les axes ensemble.

## Lot 0 — fondations et inventaire

- Inventorier données, configurations, secrets, versions des clients, volumes et ressources CPU/RAM/GPU/disque. Ne pas relever les valeurs secrètes dans les rapports.
- Documenter les API utilisées et prévoir les migrations de schéma réversibles, avec compatibilité des profils et clients déjà distribués.
- Définir droits, limites, contrats de tâches persistantes, annulation, erreurs lisibles et événements communs.
- Maintenir la console d’administration locale ; les API clientes restent limitées aux données et actions de leur propriétaire, quel que soit le transport HTTPS ou WireGuard.
- Distinguer identité personnelle et appareil : la première livraison conserve la propriété actuelle des données. Un regroupement visuel par personne ne fusionne pas les espaces.
- Identifier les réglages réellement synchronisés et ceux présents uniquement dans les clients. Décider explicitement lesquels envoyer au serveur, en conservant les conflits visibles.

Validation : inventaire et migrations testés sur une copie isolée ; pas de suppression automatique d’historiques ni de changement de clés.

## Lot 1 — sauvegarde complète et catalogue

- Étendre la sauvegarde existante aux données et réglages inventoriés : conversations, préférences synchronisées, projets, documents originaux, mémoire, tâches, quotas, comptes et secrets d’accès.
- Format chiffré versionné, manifeste, contrôle d’intégrité, création atomique, progression et un seul travail simultané.
- Instantané cohérent SQLite/configuration avec verrouillage bref ; chiffrement et copie en arrière-plan sans décharger le modèle.
- Catalogue dans la console : date, version, contenu, taille, emplacement et vérification.
- Conserver la lecture des `.qwenbackup` existants. Les modèles et caches volumineux sont exclus par défaut et clairement signalés.
- Prévoir séparément la récupération des clés de signature Windows et Android nécessaires aux futures mises à jour.

Validation : comparaison des données sauvegardées, serveur actif, archives corrompues, disque plein et absence de secrets dans les états/journaux.

## Lot 2 — sauvegardes automatiques

- Paramètres console : activation, heure, fréquence, destination et conservation. Paramètres effectivement activés : quotidienne à 03 h, 7 quotidiennes, 4 hebdomadaires, 6 mensuelles, destination serveur.
- Planificateur persistant côté serveur, navigateur et clients fermés ; une échéance manquée entraîne un rattrapage au redémarrage, sans avalanche de travaux.
- Secret d’automatisation protégé par Windows DPAPI ; phrase de récupération conservée séparément pour remettre le service sur une autre machine.
- Copie facultative sur un second disque/NAS ; distinguer réussite locale et échec de la seconde copie, avec nouvelles tentatives.
- Nettoyage après réussite vérifiée, protection du dernier point valide et des points de retour de restauration.

Validation : redémarrage, échéance manquée, conservation, destination inaccessible, charge limitée pendant une conversation.

Limite d’exploitation : le processus serveur doit fonctionner. Le lancement actuel dépend d’une ouverture de session Windows ; un service avant connexion reste une option distincte avec migration des secrets DPAPI.

## Lot 3 — restauration guidée

- Parcours console : sélectionner → vérifier/déchiffrer → voir contenu et effets → confirmer → restaurer → contrôler.
- Première livraison : restauration complète ; restauration sélective de documents/utilisateurs ensuite, avec stratégie de fusion explicite.
- Point de retour obligatoire, maintenance, gel des écritures, suspension des tâches et relances, arrêt coordonné des accès et du modèle selon les besoins existants.
- Journal persistant permettant de terminer la restauration ou revenir à l’état antérieur après coupure, avant réouverture aux clients.
- Invalidation des sessions, tâches restaurées sans reprise automatique, contrôle avant réactivation de l’accès distant.
- Registre de révocations protégé des retours dans le temps ; sur une nouvelle machine sans registre récent, accès restaurés désactivés jusqu’à validation.
- Génération de synchronisation serveur : un client revenant après restauration conserve sa copie locale et ne réinjecte pas silencieusement un état incompatible. Les clients anciens reçoivent une réponse compatible et explicite nécessitant une mise à jour avant une écriture incompatible.

Validation : restauration sur installation isolée, pannes à chaque étape, anciennes archives, accès révoqué et client revenant après une période hors ligne.

## Lot 4 — appareils et accès

- Étendre Clients & accès avec fiches PC/téléphone/tablette : nom, propriétaire administratif, version, création, dernière activité et statut.
- Une clé API et un pair WireGuard par appareil ; accès existants conservés, type « non renseigné » au besoin.
- Déclaration authentifiée minimale de type/version ; heure d’activité fixée par le serveur. Ces informations déclarées ne constituent pas une preuve d’identité ni un droit.
- Actions console : ajouter, renommer, suspendre/réactiver, expiration, révoquer, remplacer et archiver une fiche en conservant les données.
- Générer un `.fred-android` directement, indépendamment du binaire Windows ; téléchargement privé depuis la console.
- Révocation : API HTTPS/WireGuard refusée, sessions invalidées, flux/travaux concernés annulés, pair retiré et action persistante ; autres appareils inchangés.
- Une révocation ne peut pas effacer les copies déjà présentes sur un appareil hors ligne.

Validation : profils existants, import Android, révocation pendant un flux, redémarrage et maintien de l’accès des autres appareils.

## Lot 5 — tableau de bord et événements

Statut : refonte du tableau de bord toujours planifiée. Le socle d’événements persistants et les branchements d’alertes nécessaires au lot 8 sont implantés dans le stockage et les services existants ; cela ne déclare pas les cartes, métriques et parcours consolidés ci-dessous terminés.

- Consolider la vue existante : modèle disponible, état réel du moteur, RAM/GPU, disque, demandes actives/en attente et erreurs.
- Ajouter cartes sauvegardes, appareils actifs estimés, indexation, voix et notifications ; distinguer « fonction désactivée » et « service en panne ».
- Historique court et borné de mesures ; rafraîchissement raisonnable et collecte légère, sans benchmark automatique ni contenu de conversations dans les métriques.
- Un journal d’événements persistants avec identifiants stables alimente les notifications : fin/échec de tâche, échec de sauvegarde, erreur de copie, stockage insuffisant et action administrative.
- Rubriques console cohérentes : Vue d’ensemble, Sauvegardes, Appareils, Documents/recherche, Voix, Notifications, Outils.

Validation : panne d’un service, état après redémarrage, absence de secrets, consommation faible sous charge.

## Lot 6 — recherche documentaire avec sources

Statut : **achevé, validé et en service**, serveur et clients Windows/Android compilés et publiés. Les contrats de recherche et consultation passent par le transport Workspace authentifié existant.

- Améliorer l’existant FTS5 avant de choisir un moteur supplémentaire : pertinence, gestion des longs documents, passages sélectionnés et état d’indexation.
- Afficher des références structurées, cliquables : document, page si disponible, extrait et version du document utilisée. Ne pas inventer de page pour un format qui n’en fournit pas.
- Ouvrir le passage cité dans les clients Windows et Android ; conserver les sources utilisées avec les résultats des tâches.
- Vérifier les droits avant recherche et consultation ; aucune fuite entre propriétaires. Suppression/modification entraîne mise à jour de l’index ; les anciennes références signalent une source devenue indisponible ou modifiée.
- Ensemble de questions/documents de référence pour mesurer la qualité ; une recherche sans résultat le signale plutôt que fabriquer une source.
- Sous-lot optionnel : OCR local pour PDF scannés, isolé et borné. Recherche sémantique ensuite seulement si les mesures montrent un bénéfice et que les ressources le permettent.

Validation : questions connues, citations fidèles, pages PDF, documents longs, index périmé, tentative d’accès à un autre espace et fonctionnement des liens sur les deux clients.

Résultat serveur obtenu : références `source_id` opaques, document/projet, titre, page réelle ou inconnue, extrait littéral et version ; `source_get` vérifie le propriétaire et distingue source actuelle, modifiée ou indisponible. Le catalogue est dédupliqué et limité à 2 000 références par propriétaire et 12 000 globalement ; les tâches conservent leur copie de sources. L’état d’indexation, le nombre de passages et la version sont exposés. Un index FTS périmé se reconstruit à partir des passages actuels ; les migrations d’archives anciennes sont reconnues sans exécuter de SQL reçu. Les limites de fichier et de stockage restent en place. Aucun OCR ni moteur sémantique n’est ajouté à cette livraison.

Preuve ciblée : [94 tests isolés réussis](preuves/lots-6-8/recherche/validation.json), sources suivies inchangées, cinq questions connues correctes en première position et citations fidèles. Document de 460 075 caractères : 288 passages, indexation 32,60 ms et recherche de l’information finale 9,22 ms ; PDF réel de deux pages correctement cité page 2. Ces mesures sont celles du jeu contrôlé sur ce poste, pas une précision générale garantie.

## Lot 7 — messages vocaux et lecture des réponses

Statut : **dictée locale Windows/Android et conversation Windows livrées le 11 octobre 2026 ; conversation Android différée**. Le demandeur a retenu Whisper Small multilingue sur Windows et Android. [Guide](client-voice/README.md), [preuves et limites](preuves/voix-small-20261011/VALIDATION.md), [étude des moteurs](recherche/voix-20261011/ETUDE-ASR-CLIENTS.md). La dictée affiche un texte provisoire, finalise avec Terminer, puis attend l’envoi explicite. L’audio reste dans le client et n’est pas conservé. Les permissions, l’annulation, les buffers/durée bornés, l’installation vérifiée et la libération du modèle sont intégrés. Small peut prendre du retard ; aucun téléphone physique n’a été mesuré. Le lot 7 complet n’est pas déclaré achevé.

Windows 3.5.21 utilise Zipformer FR progressif, Silero et Smart Turn localement ; Pocket TTS 3.3.0 français/Estelle sur CPU serveur, lecture progressive et interruption de la demande courante. [Guide](client-voice/CONVERSATION-WINDOWS.md), [preuves](preuves/conversation-windows-20261011/VALIDATION.md). Les projets, droits, sauvegardes et mémoire EG2 du chat existant sont conservés. Le microphone reste en mémoire dans Windows ; aucune API de réception audio n’est requise. Le plan initial ci-dessous reste une référence pour une éventuelle extension mobile ou un repli serveur, sans déclarer le lot 7 complet sur Android.

- Clients : bouton microphone, permission demandée à l’utilisation, enregistrer/arrêter/annuler, durée visible et écoute facultative avant envoi.
- Serveur : API authentifiée de réception audio, validation format/durée/taille, file de transcription persistante et conversion isolée. Première étape : enregistrement puis transcription, sans conversation vocale continue.
- Afficher le texte transcrit pour correction avant envoi au chat. L’annulation ne publie pas de message incomplet.
- Ajouter synthèse vocale côté serveur puis lecture/pause/arrêt sur les clients ; commencer par une réponse complète, puis évaluer la lecture progressive.
- Sélectionner moteurs et versions après essais CPU/GPU sur ce poste, vérification de compatibilité, qualité française et licences. Isoler les processus et réserver des ressources pour éviter d’évincer le modèle Qwen des P100.
- Définir une politique de conservation : audio temporaire supprimé après traitement par défaut, texte final conservé selon l’historique. L’archivage volontaire d’audio est une option explicite, avec quotas et sauvegarde.
- Adapter le transport : la passerelle WireGuard actuelle borne les requêtes à 2 Mo. Prévoir des transferts audio découpés ou une limite compatible, avec plafonds serveur, assemblage et nettoyage des transferts abandonnés ; ne pas relever globalement les limites du chat.
- Console Voix : activation, moteurs disponibles, ressources, limites, état et erreurs.

Validation : français, bruit, annulation, audio invalide, limites, HTTPS/WireGuard, fonctionnement téléphone/tablette/Windows et absence d’impact excessif sur le chat.

## Lot 8 — notifications

Statut : **achevé, validé et en service**, stockage, contrats, console et clients publiés. Première livraison retenue : **clients ouverts/connectés avec rattrapage à la reconnexion**, sans fournisseur externe.

- Créer une boîte de notifications persistante côté serveur : événement, destinataire, date, lecture, livraison et déduplication.
- Première livraison : alertes console et notifications dans les clients ouverts ; rattrapage à la reconnexion, marqué lu synchronisé et préférences par type d’événement.
- Déclencheurs : résultat de tâche, analyse/recherche terminée, transcription disponible si traitement différé ; alertes d’exploitation réservées à l’administration.
- Android : permission système, clic ouvrant le bon résultat et réglages de discrétion. Ne pas afficher le texte privé d’un document ou d’une conversation sur l’écran verrouillé par défaut.
- Livraison Android lorsque l’app est arrêtée : sous-lot distinct, choix documenté d’un mécanisme système de push ou d’un service persistant. La file serveur seule ne garantit pas le réveil de l’app, et le tunnel WireGuard intégré n’est pas permanent lorsque le processus est arrêté.
- Si un fournisseur de push externe est retenu, décision explicite sur le compte, les métadonnées et la configuration ; charge utile minimale opaque, puis récupération du contenu depuis le serveur après authentification. Ne pas promettre de push hors ligne.
- Révoquer un appareil retire ses abonnements ; pas de livraison d’événements privés à un autre propriétaire.

Validation : client fermé puis reconnecté, doublons, ordre, panne réseau, événement déjà lu, révocation et permission Android refusée ; essais sur appareil physique pour l’arrière-plan.

Résultat implanté : boîte dans SQLite avec identifiants et séquences persistantes, événements dédupliqués, lecture synchronisée, préférences, abonnements et reçus. Les notifications de tâche et document sont atomiques avec leur événement ; une tâche interrompue est signalée sans rejouer l’inférence et chaque relance a sa notification, grâce à un compteur durable sauvegardé. Les alertes d’exploitation sont réservées à l’administration. Conservation bornée à 90 jours, 1 000 événements par accès et 20 000 au total. Windows et Android ouvrent le résultat ou document ciblé depuis la boîte. Android ajoute permission système, contenu générique discret et clic vers le bon résultat ; refuser la permission n’interdit pas la boîte interne. Les curseurs/doublons sont renouvelés après restauration et les abonnements/reçus retirés après révocation.

Preuves ciblées : [28 tests de stockage et HTTP](preuves/lots-6-8/notifications/notifications-tests.json) et [11 scénarios de console](preuves/lots-6-8/notifications/INDEX.md), avec migrations, reconnexion, préférences, maintenance, isolation et révocation. Les [11 tests de reprise après panne et relances](preuves/lots-6-8/notifications/worker-recovery-tests.json) et [5 tests de contrôle des droits pendant le flux](preuves/lots-6-8/notifications/source-access-fence-tests.json) passent également. Les 16 scénarios du client partagé et les 26 contrôles WebView Android, permissions, canaux silencieux/standard, rattrapage et clic système sont rattachés aux binaires signés publiés dans le [rapport final](preuves/lots-6-8/VALIDATION.md). Le réveil d’une application Android totalement arrêtée et le fonctionnement physique en arrière-plan ne sont pas déclarés validés.

## Lot 9 — outils de l’assistant

Statut : explication demandée, implantation non demandée. Ce lot permettra à l’assistant d’utiliser des fonctions serveur précises pour aider dans le chat : chercher un document, lire une page publique ou préparer un brouillon. Une modification présentera d’abord une proposition lisible avec sa cible, son contenu et son effet ; elle ne sera exécutée qu’après validation explicite par l’utilisateur autorisé.

Exemple : « Mets le budget à 2 500 € » prépare une proposition visible pour le document Budget. L’utilisateur peut relire le nouveau texte, annuler ou cliquer sur « Valider la modification ». Ce clic autorise uniquement cette modification de la version affichée ; si le document a changé entre-temps, l’assistant doit préparer une nouvelle proposition. Aucun accès général au terminal n’est exposé, et aucun envoi de message/calendrier n’est activé par cette explication.

- Étendre les capacités déjà présentes : rechercher dans les documents, lire une URL publique, recherche web, créer un brouillon ou proposer une tâche.
- Ajouter un registre d’outils côté serveur avec paramètres validés, droits, quotas, délais et journal de résultat. La console permet activation globale et autorisation par propriétaire.
- Priorité aux opérations de lecture ; les documents et pages web sont traités comme sources, sans pouvoir élargir les autorisations.
- Pour une action qui écrit/modifie : préparer une proposition visible indiquant cible, contenu et effet ; exécution uniquement après validation explicite de l’utilisateur autorisé.
- L’autorisation est liée à cette proposition et à la révision de la cible, expire et ne peut être rejouée. Une modification concurrente impose une nouvelle proposition.
- Annulation, erreurs et résultats visibles dans le chat et/ou les tâches ; notifications si travail long.
- Conserver l’exécution MCP de l’hôte désactivée sur la passerelle. Tout nouvel outil utilise un traitement serveur spécifique et limité, pas un accès général au terminal.
- Connecteurs de messagerie, calendrier ou autres services : lots supplémentaires seulement après demande, choix du compte et définition des opérations autorisées. Ils ne sont pas activés par ce plan.

Validation : outil refusé sans droit, paramètres invalides, contenu tentant d’injecter des instructions, aucune mutation sans accord, accord expiré/rejoué, révision concurrente et annulation.

## Lot 10 — livraison et récupération globale

- À chaque lot : tests ciblés, migrations sur copie, parcours console et clients concernés, documentation et état d’avancement mis à jour.
- Vérification globale Windows + Android téléphone/tablette, sur HTTPS et WireGuard ; garder la compatibilité de lecture des profils distribués.
- Restaurer une sauvegarde sur installation isolée et vérifier conversations, fichiers, paramètres, appareils, événements et droits. Les données/index récupérables doivent être distingués des caches reconstructibles.
- Vérifier concurrence chat/tâches/transcription/sauvegarde, limites de stockage et reprise après coupure.
- Publier les limites réellement mesurées et la compatibilité ; tests Android physiques nécessaires pour microphone, son, permissions et notifications en arrière-plan.
- Avant toute activation réelle : point de retour vérifié, réglages visibles dans la console et services externes configurés seulement si retenus. Ne pas restaurer destructivement la production pour un essai.

Critère de fin : les sept axes sont livrés avec leurs contrôles, sauvegarde/restauration éprouvées, droits effectifs, sources vérifiables, voix fonctionnelle et notifications conformes au mode de livraison effectivement choisi.

## Suivi et décisions encore à prendre

Les lots 0 à 4 sont achevés, validés et en production. Les sauvegardes quotidiennes à 03 h et la conservation 7/4/6 sont réellement activées sur le serveur ; la seconde destination est vide selon le choix du demandeur. Les lots 6 et 8 sont achevés et en service, avec leurs preuves finales ; la refonte du tableau de bord du lot 5 et les lots 7, 9 et 10 restent planifiés.

Livraison 6/8 vérifiée : **246 tests complets réussis en 354,218 s**, sources produit et tests inchangées, Windows 3.5.18 et Android 1.0.2/code 3 signés et publiés, autotests et parcours téléphone/tablette réussis sur émulateurs. Les fichiers antérieurs et l’archive préalable sont conservés ; une nouvelle sauvegarde chiffrée est vérifiée après rechargement. Le [rapport final](preuves/lots-6-8/VALIDATION.md) et le [contrôle final](preuves/lots-6-8/delivery-final-check.json) donnent les résultats et leur portée.

À résoudre lors du lot concerné : destination du second exemplaire de sauvegarde ; traitement des réglages uniquement locaux ; moteurs vocaux et budget de ressources après mesure ; éventuel push Android hors application ouverte ; éventuelle installation comme service Windows. Ces choix ne bloquent pas les fonctions déjà livrées ni la livraison connectée des notifications.

Le contexte de reprise est dans [CONTEXTE-PROJET.md](CONTEXTE-PROJET.md). Le détail sauvegardes/appareils est conservé dans [PLAN-SAUVEGARDES-APPAREILS.md](PLAN-SAUVEGARDES-APPAREILS.md).

## Extension mémoire — livraison du 11 octobre 2026

L’utilisateur a autorisé l’intégration d’EmbeddingGemma 2. Elle est **installée, activée et validée en service** : moteur Sentence Transformers/PyTorch sur CPU indépendant de Qwen/Strata, connaissances par projet et hors projet isolées par accès, indexation des conversations synchronisées et recherche combinant mots-clés et sémantique. La console permet le pilotage du moteur et les souvenirs personnels. Les sources sont revérifiées et les conversations archivées/supprimées/déplacées ne restent pas accessibles via leur ancien cache.

La base originale et ses nouveaux souvenirs entrent dans les sauvegardes ; le cache est reconstructible. Les contrôles du modèle réel, de la console et de l’ancien contrat de chat passent. Les processus Qwen, les données, accès et réglages antérieurs sont conservés et les sauvegardes avant/après vérifiées. EG2 utilise environ 1,63 Gio de RAM sur les fixtures ; l’impact pendant une génération Qwen simultanée reste à mesurer. [Guide et limites](lanceur/MEMOIRE-EG2.md), [preuves](preuves/eg2-20261011/VALIDATION.md). Versions client conservées : Windows 3.5.20 et Android 1.0.3/code 4.
