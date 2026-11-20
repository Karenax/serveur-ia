# Bascule de Kiara et retour arrière

## Livraison Kiara 4.0.22

Le 20 novembre 2026 à 11 h 20, la vérification en production a retrouvé les
11 projets et le nouvel écran Documents sur le portail privé. Elle a confirmé
la recherche groupée, les huit types actifs et la vue en lecture seule.
Depuis un client 4.0.21, le canal HTTPS a proposé la 4.0.22. Le contrôle a
vérifié la signature Ed25519 du manifeste et le téléchargement complet de
l’installateur.

Les preuves `production-verifiee.json` et `canal-client-verifie.json`, ainsi
que les fichiers conservés pour le retour à la 4.0.21, se trouvent dans
`D:\KRecette\publication-documents-422`.

## Livraison Kiara 4.0.16

Conversations adopte la navigation Kiara dès la réponse du portail privé
ou du relais Windows authentifié. Les préférences d’apparence sont reprises
dès le début du chargement et l’état des brouillons partage la ligne de
l’historique sous le composeur.

La recette a retardé l’historique et le catalogue en 720p, 1080p et 1440p.
La largeur de la barre et la position du composeur visible sont restées
stables en clair et en sombre. L’installateur a passé la recette WebView2
et sa signature de manifeste a été vérifiée. Les preuves sont conservées
sous D:\KRecette\conversations-416 avec la procédure de retour à la 4.0.15.

## Livraison Kiara 4.0.15

Le correctif serveur de la 4.0.15 permet à chaque compte d’enregistrer ses
préférences de réunion et ses critères pour les huit trames documentaires.
Les traitements suivent le créateur de la séance. Les recherches de trames
et leur historique suivent le compte qui lance la recherche. Les critères
communs servent de point de départ aux comptes sans version personnelle.
Le propriétaire conserve les réglages des moteurs et les critères communs
dans les sections d’administration. Les preuves du déploiement et les recettes
sont dans D:\KRecette\preferences-personnelles-415.

Le 18 novembre 2026, la navigation des réglages a été harmonisée sur le
portail privé et sous Windows. Les 17 entrées Windows et les 14 entrées
du portail conservent le menu à gauche. Les formulaires pris en charge
apparaissent à droite. Les boutons Précédent et Suivant restaurent la
rubrique sélectionnée.

Les parcours ont été vérifiés avec des données fictives en 720p, 1080p
et 1440p, avec l’installateur candidat pour WebView2. Le téléchargement
signé, les deux accès HTTPS et les 11 projets ont été contrôlés en
production. Le moteur d’inférence a conservé son processus.

Les preuves et le script de retour à la 4.0.14 sont conservés sous
D:\KRecette\publication-415. Le retour complet du portail comprend
l’index compilé et la restauration du code du panneau côté serveur.

## Livraison Kiara 4.0.14

Le 18 novembre 2026, le canal Windows et le portail privé ont reçu la
navigation principale de 216 px et l’ouverture directe des réglages de
l’appareil et du compte. Le bouton de retour ramène à l’espace de travail.

Le portail et l’installateur Windows ont passé la recette à 720p, 1080p et
1440p. Le téléchargement signé, les deux accès HTTPS et le catalogue de
11 projets ont été contrôlés après publication. Le moteur d’inférence a
conservé son processus.

Les preuves se trouvent dans D:\KRecette\publication-414. La commande
`publier.ps1 -Retour` y rétablit le canal Windows et l’index du portail
compilé de la 4.0.13. Les anciennes ressources de Conversations sont
conservées dans le dossier `conversations-4.0.13`.

## Livraison Kiara 4.0.13

Le 18 novembre 2026 à 19 h 48, le canal Windows et le portail privé ont
reçu les quatre lots de l’[audit de cohérence](../2026-11-18-coherence-interface/RAPPORT.md).
Les nouveaux réglages, Notes et les accès aux parcours transversaux figurent
dans le [guide Kiara](../../GUIDE-ASSISTANT-KIARA.md#retrouver-les-réglages).

La recette a contrôlé les trois exécutables extraits de l’installateur,
les panneaux de réglages dans WebView2 et le manifeste Ed25519 avec la clé
du canal existant. L’empreinte SHA-256 de l’installateur téléchargé depuis
le canal est 00187d85bfc12041b237abc77b5d92970d6d0d3098e9ee7db910cccb417225af. Les deux entrées HTTPS ont répondu 200
avec le nouveau rendu de connexion. Le catalogue a conservé ses 11 projets
et le processus d’inférence est resté actif.

Les preuves et les scripts sont sous D:\KRecette\publication-413.
En cas de retour, publier.ps1 -Retour rétablit le canal Windows et le
portail compilé 4.0.12. Les ressources précédentes de Conversations sont
conservées dans conversations-4.0.12. La réinstallation locale se fait
séparément avec l’installateur de la version voulue, Kiara fermé.

Le client Windows de Fred a été mis à niveau de la 4.0.8 à la 4.0.13.
Le registre et les trois exécutables ont été contrôlés. Conversations et
Réglages ont répondu 200 via le relais installé avec le bundle publié.

## Audit des réglages de Kiara 4.0.11

La passe a comparé les réglages du client Serveur IA historique, la 4.0.10
distribuée et le portail qui l’accompagne. Les actions du poste reprennent les
écrans et les contrôles de signature existants du client Windows.

| Priorité | Constat | Correction et vérification |
| --- | --- | --- |
| P1 | Les mises à jour se trouvaient derrière « Compte et appareil », puis dans un second écran. | **Réglages → Mises à jour** figure dans la page du portail Windows. Un client 4.0.10 ouvre ses onglets locaux. Un client 4.0.11 ouvre directement l’onglet Mises à jour. |
| P1 | Depuis Conversations, le bouton Réglages dépendait de l’ouverture du portail. Une coupure pouvait empêcher d’atteindre les réglages de connexion. | Conversations ouvre les réglages locaux. Le bouton **Réglages du portail** revient aux réglages serveur en ligne. Accès local et message d’erreur de vérification rejoués hors connexion. |
| P1 | Statistiques, transcription, recherche documentaire, modèles de livrables et de documents et maintenance dépendaient du menu « … ». | Les 11 rubriques sont visibles à l’ouverture. Les parcours de navigation, le chargement différé, la reprise après erreur et la protection des modifications en cours sont couverts par les tests du portail. |
| P2 | Les réglages audio et de notifications se trouvaient dans des pages différentes. Dans le web privé, les préférences de lecture étaient accessibles depuis Conversations. | Les accès Windows à la connexion, à l’API et aux intégrations, à la mémoire, au vocal, à la dictée et aux préférences de notification figurent dans Réglages. Le navigateur donne accès à Mon accès et Lecture des conversations. |

La navigation a été rejouée dans WebView2 à 1280 × 720, 1920 × 1080 et
2560 × 1440 avec les binaires extraits de l’installateur 4.0.11. La recette a
utilisé des données fictives et simulé la disponibilité et le lancement de la
mise à jour. Le parcours de secours emploie les ressources du relais 4.0.10.
Les 85 tests ciblés du portail, les 18 tests de transport Windows exécutés et
la suite de navigation et de récupération Windows ont réussi.

La bascule du 18 novembre à 13 h 57 a vérifié l’installateur signé, les deux
entrées HTTPS, les 11 projets et le processus Qwen. Le téléchargement donne
le SHA-256 `de65111d87c68e5cb108d9d0502e0c7139f51055d814948fc5a2c6343f283102`.
Les captures, la preuve de bascule et les références de retour sont sous
`D:\KRecette\reglages-410`. Le script `publier.ps1 -Retour` remet le canal et
l’index du portail 4.0.10 en préservant l’état de Qwen.

## Correctif d’interface 4.0.10

La comparaison de la 4.0.9 avec la 4.0.8 a porté sur Conversations, Vocal,
le Correcteur, l’historique et l’Assistant de projet. Les contrôles du
portail privé ont utilisé le rendu du serveur avec des données fictives.

| Priorité | Régression constatée | Correction |
| --- | --- | --- |
| P1 | Vocal et Correcteur étaient dans les options de rédaction. Le seul micro visible démarrait la dictée. | Boutons Vocal et Correcteur dans le composeur Windows. Le clavier ouvre Vocal et place le focus sur son titre. |
| P1 | En 720p, les ondes repoussaient le bouton de démarrage du vocal sous la partie visible. | La visualisation s’ajuste à la hauteur disponible pour garder le bouton de démarrage visible. |
| P1 | Les commandes de reprise d’historique et d’enregistrement d’un échange projet dépendaient d’un menu fermé. | Les actions de reprise et le statut d’enregistrement restent visibles lorsque l’intervention est nécessaire. Le rattachement des sources se fait depuis l’Assistant de projet. |
| P1 | Après une réflexion sans réponse finale, le menu extérieur masquait l’action proposée. | « Réessayer sans réflexion » s’affiche lors de l’erreur si le modèle permet ce réglage. |
| P1 | Le web privé présentait des commandes microphone et des rubriques d’appareil sans relais local. | Vocal explique où ouvrir le client Windows. Les entrées Connexion au serveur, Mises à jour et API locale sont retirées de la navigation du navigateur. |
| P2 | Le modèle, la réflexion, les sources et les choix de session projet avaient perdu leur accès direct. Le bouton Historique occupait toute une ligne de la barre. | Le modèle, la réflexion, les sources disponibles, l’historique de projet et le mode éphémère sont accessibles dans leurs vues. Historique et Nouvelle conversation partagent la barre, avec retour du focus au clavier. |

La recette a ouvert Conversations et Vocal dans WebView2 en 1280 × 720,
1920 × 1080 et 2560 × 1440. Aux mêmes tailles, le rendu du web privé a passé
le parcours Historique au clavier et l’ouverture de l’aide Vocal. Les suites
du client Windows et de la passerelle web ont donné 309 et 5 réussites.
Les scénarios vocaux Low et Max utilisent une reconnaissance et un son
simulés. L’essai sur microphone physique reste à faire.

La **4.0.10** a été activée le 18 novembre à 12 h 15, heure de Paris. Le
téléchargement de production correspond au manifeste Ed25519 du canal et au
SHA-256 `c734c954382430787ddd7e65d58fc14f3a5f8ffc96a4812895f7ff7fde52b362`.
Les entrées `/kiara/` et `/agent/` répondent en HTTPS. Les 11 projets sont
présents et Qwen a gardé son processus pendant la bascule.

Les preuves de recette et de bascule sont sous
`D:\KRecette\correctif-interface-4.0.10`. Le script `publier.ps1 -Retour`
rétablit le canal Windows 4.0.9 en conservant Qwen chargé. Pour revenir aussi
sur les écrans web de Conversations, reprendre les fichiers sous `client-qwen`
dans `sources-conversations-4.0.9.zip`. Les données et le portail Projets
gardent leur procédure de reprise décrite ci-dessous.

### Typographie du portail

Le 18 novembre à 13 h 22, Segoe UI a été rétablie sur le portail chargé par
Kiara 4.0.10, avec la police système en secours. La recette a vérifié Projets,
Notes, Mails et Réunions dans Chrome et WebView2 en 720p, 1080p et 1440p.
Les 238 tests ciblés du portail passent. La publication des ressources a
conservé le processus Qwen et le catalogue de 11 projets. Le rapport de
production et l’index précédent se trouvent sous
`D:\KRecette\typographie-serveur-ia`.

## Livraison Windows et web du 18 novembre 2026

**Kiara 4.0.9** a été activée à 11 h 43, heure de Paris. Le canal classique
continue de servir la 3.5.63. Le portail ajoute Notes et regroupe les corrections
de reprise de navigation, de capture audio, de projection des notes et de
sauvegarde consignées dans le [suivi d’architecture](../2026-11-16-architecture-interface/AVANCEMENT.md).

- **Windows.** Les trois exécutables extraits du NSIS correspondent aux binaires
  de recette. Le manifeste Ed25519 est vérifié avec la clé du canal existante et
  les octets téléchargés depuis le lanceur correspondent au SHA-256
  `a2c85c74c55a8533901a179da6fd11ebce776d9679c4b94a96baf8ecdaae7d2b`.
  L’installateur est distribué sans Authenticode. La recette du candidat a
  exécuté WebView2 depuis les binaires extraits et simulé le collage d’une image.
  L’installation et la rétrogradation natives de ce NSIS restent à qualifier.
- **Suites Windows.** Le client compte 309 tests réussis et 24 ignorés. Le
  lanceur compte 672 tests réussis et un ignoré. Les tests du démarrage et du
  contrôle de taille des requêtes ont été alignés sur le comportement livré.
- **Portail.** Les 1 228 tests d’interface ont réussi. Notes a été ouvert dans
  WebView2 en 1280 × 720, 1920 × 1080 et 2560 × 1440 avec un projet fictif. Le
  passage du paquet précédent au candidat puis retour a conservé les écritures
  de recette et les refus hors périmètre.
- **Production.** Les 11 projets, leurs identifiants et états ont été comparés
  avant et après redémarrage. L’ERP passe les contrôles SQLite d’intégrité et de
  clés étrangères et contient les trois nouvelles tables de notes personnelles.
  `/kiara/` et `/agent/` répondent 200 en HTTPS. Le PID Qwen est resté le même.
- **Point de reprise.** Les empreintes de la paire chiffrée du 18 novembre à 03 h
  concordent sur D: et sur le NAS. Le contrôle de cette paire porte sur ses
  empreintes. Les preuves de la livraison, le sélecteur et l’index précédents,
  ainsi que le ZIP serveur de référence, sont sous
  `D:\KRecette\livraison-1794997317710`.

Pour revenir au canal 4.0.8, rétablir le sélecteur `releases.py` et l’index
conservés sous `retour-production`, puis lancer le redémarrage documenté en
préservant l’état de Qwen. Les ressources du portail 4.0.8 sont conservées.
Pour un retour complet du service, utiliser aussi le ZIP serveur de référence
et les contrôles de la section [Revenir en arrière](#revenir-en-arrière).

## Historique de la fusion

La première mise en service porte sur les écrans et le routage. Conversations conserve les API et les identifiants des fils existants. Le catalogue de recette laisse les projets et leurs objets dans leurs bases propriétaires. Une migration des données, si elle s’avère nécessaire, fera l’objet de sa propre répétition et de son propre point de reprise.

Sur cette machine, utiliser D: pour les compilations, les caches, les fichiers temporaires, les restaurations de recette et la production des preuves. E: sert à conserver les archives et les preuves finalisées. Tant que les accès à E: sont suspendus, utiliser des copies de recette déjà présentes sur D: et y conserver tous les résultats.

## Préparer le poste pilote

La console présente les habilitations sous **Clients & accès → Droits sur les projets**. Dans le lanceur candidat, la console utilise `/api/project-service`. Les scripts d’exploitation antérieurs peuvent encore appeler `/api/agent-service` avec les mêmes contrôles locaux. Pendant le retour à un lanceur antérieur, la console reprend cette route de compatibilité.

Le script de démarrage Windows interroge aussi `/api/project-service` avant et après un redémarrage. Il utilise l’ancienne route uniquement si la nouvelle répond 404. Le contrôle vérifie que les refus d’accès et les indisponibilités remontent sans nouvel appel.

Pour le portail HTTPS partagé, publier `/kiara/` après avoir vérifié que le tunnel achemine cette adresse vers la passerelle. Les liens déjà publiés sous `/agent/` restent utilisables, y compris pour les documents, et les deux préfixes partagent la même session sur la passerelle. En cas de retour vers une passerelle antérieure, publier à nouveau `/agent/`. Une installation qui utilise un port dédié conserve son adresse sans préfixe.

Le 16 novembre, une recette Chrome derrière un proxy HTTPS de boucle locale a ouvert `/kiara/` avec deux comptes fictifs, contrôlé les autorisations, et réutilisé la session depuis `/agent/`. Conversations a relu le brouillon personnel après rechargement et gardé hors du stockage du navigateur le brouillon de projet éphémère. Le catalogue des projets a répondu avec le moteur arrêté. La trace et les huit fichiers du portail de production sauvegardés par empreinte se trouvent sous `D:\Kiara\essais\pilote-https-kiara`.

Sur ce poste, `D:\Kiara\essais\pilote-https-kiara\bascule-production.ps1` vérifie le ZIP testé, les sources courantes, le portail actif, les deux archives de retour et l’existence d’une paire de sauvegardes vérifiée sur le NAS. L’exécution sans option réalise le contrôle préalable. En session Windows administrateur, `-Activer` met en place le bundle candidat et redémarre le lanceur en conservant le moteur chargé. `-Retour` remet le bundle précédent et les sources du lanceur de référence. Le fichier `activer-pilote.ps1` journalise la bascule et tente le retour si une erreur survient après la mise de côté du bundle précédent.

Le 16 novembre à 09 h 24, le candidat a pris le relais sur la passerelle en service. `/kiara/` et `/agent/` ont tous deux servi leur page de connexion via le tunnel HTTPS. Le contrôle de production a retrouvé les 11 projets, le moteur chargé et l’empreinte du bundle testé. La preuve est dans `D:\Kiara\essais\pilote-https-kiara\pilote-production-verifie.json`. Les scénarios avec connexion, échanges et reprise de brouillon qui précèdent ont été exécutés sur la recette isolée.

Pour une installation neuve, le fichier de configuration du service Projets est `project-service.json` dans le dossier des données du lanceur. Le lanceur lit `agent-service.json` quand le nouveau fichier est absent. Si les deux fichiers existent, seul le nouveau fait autorité. Reporter la migration du fichier en production après le pilote ou répercuter les changements de configuration avant tout retour vers une version qui ne lit que l’ancien fichier.

Le lanceur candidat accepte les variables de démarrage `KIARA_PROJECT_*` et lit encore les variables `KIARA_AGENT_*` correspondantes. Sur une copie isolée de la configuration actuelle, le lanceur candidat a obtenu les mêmes paramètres métier et HTTPS avec le fichier historique, sa copie sous le nouveau nom et le retour au fichier historique. La vérification des variables de démarrage couvre également leur priorité et le retour aux valeurs héritées.

1. Identifier le commit et les dépendances du serveur, du portail et de chaque client distribué. Construire le paquet serveur avec le nouveau bundle du portail. Relever la version, l’empreinte et l’emplacement de chaque paquet candidat et de la version précédente. Vérifier les signatures des installateurs utilisés en déploiement.
2. Constituer un point de reprise cohérent avec le mécanisme de sauvegarde du lanceur. Relever l’identifiant de l’archive, les empreintes validées et l’heure en UTC. Contrôler la copie hors machine et restaurer en environnement isolé. Vérifier l’ouverture des bases, l’accès aux objets liés et les téléchargements d’originaux. Garder l’accès aux secrets via le mécanisme de restauration prévu pour la machine.
3. Répéter le contrôle du catalogue à partir des trois bases isolées. Comparer les identifiants et les liens de projet, et traiter tout historique orphelin ou changement de propriétaire avant la mise en service.
4. Choisir un poste pilote et des accès de test avec des périmètres distincts. Consigner la version cliente initiale, les raccourcis publiés et les réglages de connexion à rétablir si nécessaire.

Le volet de projet a été retiré du portail candidat. Le nouveau lien utilise la capacité annoncée par le portail ou le relais. Pour les postes de bureau, déployer d’abord un relais qui annonce Conversations avec l’assistant de projet, puis activer le bundle du portail candidat. Pour rétablir le volet, restaurer le bundle précédent en même temps que le paquet serveur correspondant.

Le candidat reconstruit le 16 novembre dans `D:\Kiara\essais\kiara-serveur-sans-panneau` retire aussi le composant React et ses styles dédiés. Les écrans Projets et la console de maintenance utilisent les libellés Kiara. Le composeur commun a relu un fil historique et enregistré sa suite sur les parcours de recette Windows et Android. La recette couvre aussi la liaison explicite au projet, la conservation des brouillons, la résolution d’un conflit et l’absence d’écriture pour un échange éphémère.

Pour la répétition serveur de ce candidat, utiliser `maintenance/rehearse_portal_packages.py --previous-has-conversations` avec le paquet `kiara-serveur-route-projets` comme référence. Le rapport `recette-retour.json` consigne les empreintes des deux paquets et de leurs bundles. La répétition a conservé les écritures du pilote et du retour et vérifié le refus hors périmètre sur des données fictives.

Le 16 novembre, `publier-portail.ps1 -Operation Activer` a publié le nouveau portail en copiant ses ressources puis en remplaçant l’index de façon atomique. Le lanceur et le service Projets sont restés actifs. La console locale a confirmé les 11 projets lors du précontrôle. Les deux entrées HTTPS répondent 200 avec `Cache-Control: no-store`. La preuve `publication-statique-verifiee.json` contient les empreintes et le PID du lanceur. Ce contrôle HTTPS porte sur l’entrée publique de connexion. Les parcours connectés ont été validés en recette.

Pour revenir au portail précédent, exécuter le même script avec `-Operation Retour`. Le script restaure l’index de référence et retrouve ses ressources conservées dans le dossier du portail. Cette publication couvre le portail Projets compilé. Les nouveaux libellés du lanceur seront chargés lors de sa prochaine mise en service.

Depuis la racine du dépôt et avec le Python de construction du projet, les commandes suivantes préparent le paquet et vérifient le catalogue sur la restauration. Les variables désignent des chemins absolus vers le bundle validé, les trois bases restaurées et des répertoires de recette.

```powershell
& $Python maintenance/package_server.py --output $Paquets --web-dist $BundleWeb
& $Python maintenance/rehearse_project_migration.py --workspace $BaseEspaces --erp $BaseProjets --brain $BaseConnaissances --output $CatalogueRecette
```

## Activer et observer

1. Mettre en place le paquet serveur validé et vérifier l’état du lanceur et des services. Contrôler la session HTTPS du portail, le relais natif et les liens déjà publiés. Rendre le client candidat accessible au pilote et conserver le paquet précédent à portée de main.
2. Sur le pilote, ouvrir les cinq rubriques principales. Depuis une fiche, ouvrir le composeur sur le projet courant. Reprendre un fil existant, enregistrer une suite et rouvrir le brouillon après relance. Exécuter un échange éphémère et vérifier qu’aucune écriture de fil n’en découle. Interrompre une réponse, la relancer et simuler une révision concurrente. Contrôler une citation et l’empreinte de l’original téléchargé. Répéter les refus avec un accès hors périmètre.
3. Suspendre l’élargissement si un accès dépasse son périmètre, si un brouillon ou un fil disparaît, si un échange éphémère est enregistré ou si le retour arrière ne peut plus être exécuté. Noter le parcours, le client, les versions et l’heure. Les guides d’exploitation et les anciens liens restent disponibles durant le pilote.

## Revenir en arrière

### Retour sur la version précédente

1. Stopper le déploiement et faire fermer le client pilote après enregistrement des brouillons. Exporter les conversations utiles si un client les indique comme non synchronisées.
2. Rétablir le paquet serveur, son bundle web et sa configuration issus du même inventaire. Remettre la version précédente du client pilote suivant sa procédure de retour. Garder les bases actuelles tant que la compatibilité de lecture et d’écriture est démontrée.
3. Confirmer la connexion, le périmètre des accès, le fil créé pendant le pilote et l’ouverture des projets. Reprendre le service après ces contrôles.

### Restauration des données si nécessaire

1. Geler les écritures et établir un inventaire des opérations intervenues depuis le point de reprise. Faire une copie de l’état incident complet pour permettre leur récupération. Contrôler que les écritures à préserver disposent d’un export ou d’une procédure de rejeu vérifiée.
2. Restaurer l’ensemble cohérent dans un emplacement isolé. Comparer les bases, les accès, les liens, les révisions et les empreintes avec l’inventaire du point de reprise. Tester le rejeu sur cette restauration.
3. Réouvrir les écritures après confirmation de l’intégrité et de la récupération des opérations à préserver. Tant que leur récupération reste indémontrée, garder l’état incident en lecture seule et différer la reprise.

Pour une sauvegarde appairée, partir de l’archive principale `.qwenbackup` et vérifier l’empreinte du fichier `.kiara-agent` associé. Restaurer le lanceur et les espaces personnels, puis utiliser la restauration des Projets vers un dossier isolé pour le fichier associé. Vérifier les trois bases et les originaux avant de rattacher les données et de rouvrir les accès.

Pour répéter cette restauration depuis la racine du dépôt, placer les deux fichiers de la paire dans le même dossier sur D:. `$ArchivePrincipale` désigne le fichier `.qwenbackup`. `$DossierRecette` désigne un dossier existant et réservé à cette exécution sur D:. Utiliser les interpréteurs de recette du lanceur et du service métier sur D:.

```powershell
$env:TEMP = $DossierRecette
$env:TMP = $DossierRecette
& $Python maintenance/rehearse_paired_restore.py --archive $ArchivePrincipale --work $DossierRecette --business-python $PythonMetier
```

Saisir la phrase de récupération à l’invite. La procédure vérifie l’empreinte du fichier associé avant de restaurer, garde les accès distants fermés et contrôle l’intégrité des trois bases ainsi que les originaux référencés. Après suppression des données de recette, le script écrit `restauration.json` dans le dossier de travail. Exiger un code de sortie nul et le rapport de cette exécution avant de considérer la répétition comme validée.

## Répétition du portail

Le bundle précédent est conservé dans `E:\Kiara-Integration\Build\fusion-kiara\reference-portail-avant-retrait` avec les empreintes de ses fichiers. Cette référence couvre le portail web.

Le test `test_portal_rollback_preserves_writes_and_project_scopes` sert successivement le portail précédent, le candidat, puis le précédent et le candidat à nouveau. Il utilise le véritable stockage SQLite de recette. Il compare le HTML et le JavaScript servis à chaque phase, crée un fil sur le candidat, le relit et le prolonge après retour arrière, puis vérifie la suite sur le candidat. Un compte limité à un autre projet reçoit un refus. Le test est passé avec les deux bundles de recette.

Les deux ZIP serveur ont aussi été extraits et leur service métier lancé dans quatre processus distincts avec les mêmes bases de recette. Le rapport `E:\Kiara-Integration\Build\fusion-kiara\recette-retour-paquets.json` consigne les empreintes et les écritures relues après chaque redémarrage. Le script utilise le Python du service métier et crée lui-même les bases fictives.

```powershell
& $PythonMetier maintenance/rehearse_portal_packages.py --previous $PaquetPrecedent --candidate $PaquetCandidat --report $RapportRecette
```

Le 16 novembre, la répétition a été rejouée sur D: avec le ZIP candidat et le paquet précédent conservé dans `D:\Kiara\integration-agent\verification-kiara\reprise-20261113\serveur-agent-distribution`. Les deux écritures ont été relues après retour et réactivation. Un accès cantonné à un autre projet a reçu un refus. Le ZIP, son manifeste et `recette-retour.json` se trouvent dans `D:\Kiara\essais\kiara-serveur-portail-candidat`.

Le candidat suivant retire le code de l’ancien bureau, de ses fenêtres et de sa navigation. Ses 1 041 tests web passent et son retour arrière a été rejoué sur la base de recette. Utiliser le ZIP, son manifeste et `recette-retour.json` sous `D:\Kiara\essais\kiara-serveur-sans-bureau` pour ce candidat. Le contrôle préalable du lanceur a retrouvé les 11 projets avant tout redémarrage de production.

La suite isolée du lanceur a passé 62 tests de sauvegarde, de restauration et de reprise après interruption. Le contrôle de volume a restauré huit originaux totalisant 16 Mio avec des empreintes identiques. La répétition sur une paire d’archives du serveur réel et le contrôle des opérateurs de production restent à qualifier.

## Pilote Windows

La finalisation et la qualification portent d’abord sur Windows. Reporter les nouvelles recettes Linux et Android après la mise en service Windows. Sur ce poste, l’installation Windows actuellement enregistrée est la 4.0.4. Le lanceur distribue la 4.0.5. Prévoir les deux références pour qualifier une mise à niveau depuis un poste existant et le retour au paquet précédemment distribué.

Les empreintes des installateurs 4.0.4 et 4.0.5 concordent avec leurs manifestes locaux. Le canal de mise à jour Kiara contrôle les manifestes signés en Ed25519. Authenticode est un mécanisme distinct. Les deux installateurs de référence sont dépourvus de cette signature Windows, et aucun certificat de signature de code avec clé privée n’a été trouvé dans les magasins consultés sur ce poste.

Le candidat x64 4.0.6 a été construit avec l’identité de distribution `fr.kiara.desktop`. Les empreintes des trois exécutables extraits du NSIS concordent avec les fichiers construits. L’autotest du relais et la recette Conversations dans WebView2 ont passé les contrôles sur données fictives, dont l’historique de projet, les brouillons et le mode éphémère. Le paquet, `recette-distribution.json` et `references-retour.json` sont sous `D:\Kiara\essais\windows-distribution-4.0.6`. Ce paquet de recette est sans Authenticode.

La recette NSIS sur le poste Windows a mis à niveau la 4.0.4 vers la 4.0.6 dans le dossier d’installation existant, avec le client fermé. Les versions au registre et les empreintes des trois exécutables ont été vérifiées aux deux étapes. WebView2 a passé la recette depuis le binaire installé avec un profil fictif. Le retour par l’installateur 4.0.4 a restauré les trois empreintes de référence et la version au registre. Voir `recette-nsis.json`.

Le manifeste Ed25519 de la 4.0.6 a été vérifié avec la même clé publique que celui de la 4.0.5. Depuis Réglages → Mises à jour, le client 4.0.4 a téléchargé le paquet par un tunnel de recette, l’a vérifié puis a lancé NSIS et s’est fermé. La 4.0.6 a redémarré automatiquement dans le même dossier, avec Conversations et Projets visibles. La preuve est dans `mise-a-jour-interface/mise-a-jour-verifiee.json`. Le profil de ce parcours est fictif et séparé du profil habituel.

Le canal Windows sert la 4.0.6 depuis le redémarrage du lanceur en session administrateur. La console locale annonce la nouvelle version et le fichier téléchargé depuis le canal de production correspond au manifeste signé. Le service Projets a retrouvé les 11 projets et le lanceur a conservé l’état du moteur. La preuve est dans `D:\Kiara\essais\windows-distribution-4.0.6\publication-windows-verifiee.json`. Pour revenir au canal précédent, rétablir `releases-avant-publication.py` en tant que `lanceur/releases.py`, puis redémarrer le lanceur en conservant le moteur. Le paquet 4.0.5 et son manifeste restent disponibles.

Le candidat Windows 4.0.7 inclut les libellés corrigés dans le relais. L’extraction NSIS a confirmé les trois empreintes et la recette WebView2 a validé Conversations depuis l’exécutable extrait, avec des données fictives. Le candidat et son rapport sont sous `D:\Kiara\essais\windows-distribution-4.0.7`. Le paquet serveur de recette se trouve sous `D:\Kiara\essais\kiara-serveur-libelles-windows`. Il incorpore les messages serveur corrigés et le même bundle web que la production. Le canal en service distribue la 4.0.6.

Dans `D:\Kiara\essais\recette-couple-windows-4.0.7`, le rapport
`recette-retour-portail-actuel.json` compare le paquet de référence du portail
sans panneau et le candidat. Les quatre phases servent le même bundle web.
L’empreinte du service Projets change à l’activation et revient à sa valeur de
référence au retour. Les deux écritures de recette et le contrôle de périmètre
ont passé les vérifications sur la même base fictive.

La recette Windows Sandbox de la 4.0.7 a désormais réussi. Elle a installé la
4.0.6, mis à niveau vers la 4.0.7 puis réinstallé la 4.0.6. Les versions au
registre et les trois exécutables ont été contrôlés à chaque étape. Le fichier
sentinelle du profil fictif est resté intact. Voir
`sandbox-resultats/installation.json` dans le dossier de recette.

La publication Windows 4.0.7 a ensuite été vérifiée après redémarrage du lanceur. Le canal sert le manifeste signé et l’installateur correspondant. La 4.0.6 est conservée pour le retour arrière. Voir `publication-4.0.7/publication-verifiee.json` dans le même dossier.

La répétition du portail de fusion compare ce ZIP serveur de référence à un ZIP construit depuis les sources courantes avec un nouveau bundle. Les deux empreintes, service et interface, reviennent à leur valeur de référence pendant le retour. Les deux écritures de recette et le refus hors périmètre sont vérifiés sur les mêmes bases isolées. Voir `D:\Kiara\essais\fusion-windows-web-3ec6b20c\retour-verifie.json`.

La qualification suivante inclut le retrait des derniers écrans historiques. Le dossier `D:\Kiara\essais\fusion-windows-qualification` réunit le ZIP serveur et sa répétition de retour arrière sous `serveur`, ainsi que le paquet NSIS de recette et `recette-installee.json` sous `client`. Le paquet a été installé sous l’identité Kiara Prototype dans un dossier séparé sur D:, sans raccourci, puis désinstallé. Les trois binaires installés ont les empreintes attendues. Le relais installé a conservé le brouillon et le thème après redémarrage sur un profil fictif hors ligne. La recette `client/recette-wireguard.json` utilise l’application installée et le tunnel WireGuard en boucle locale avec un serveur fictif. Elle confirme le nom Unicode et les octets de l’original téléchargé, la reprise de l’historique et du brouillon et l’absence d’écriture pour l’échange éphémère. La mise à niveau avec l’identité de distribution reste à qualifier.

Le dossier `distribution` contient le candidat Windows 4.0.8 sous l’identité Kiara. Il contient également le manifeste de construction, la preuve du canal signé avec une clé isolée, la recette WireGuard exécutée avec les binaires extraits et le journal des 1 032 tests du portail. La configuration `recette-mise-a-niveau.wsb` vise la séquence 4.0.7 → 4.0.8 → 4.0.7 et contrôle le registre, les trois empreintes et la conservation du profil fictif. Cette séquence est préparée et attend un Bac à sable Windows fonctionnel ou un poste Windows isolé.

Pour enregistrer une livraison limitée à Windows, utiliser `maintenance/deployment_manifest.py --scope windows` avec les manifestes de l’installateur et du serveur. La preuve d’interface Windows est produite par `maintenance/verify_project.py --checks ui-windows`. Elle couvre Conversations, Projets, les brouillons, le mode éphémère, Vocal et l’assistant. La recette de mise à niveau reste une étape distincte.

Le contrôle Go et l’audit npm du client passent. Le rapport Python signale `opentelemetry-api 1.45.1` dans l’environnement Hermes. La version corrigée 1.45.2 a été chargée depuis un dossier de recette sur D: avec l’interpréteur de Hermes. Le contrôle des dépendances dans cet environnement de test passe. Le verrou Hermes et son manifeste référencent désormais 1.45.2. Une superposition de recette confirme que les dépendances sont cohérentes et que la version ne remonte aucun avis OSV. Le runtime en service reste à mettre à niveau puis à vérifier au moment de la bascule. Voir `validation-dependances/python-security.json` et [l’avis OpenTelemetry](https://github.com/open-telemetry/opentelemetry-python/security/advisories/GHSA-mf5v-w3w3-f6cg).

Le rapport `E:\Kiara-Integration\Build\fusion-kiara\recette-pilote-natif.json` identifie par empreinte le relais précédent et le relais candidat. La recette lance Kiara avec son hôte Tauri et WebView2, quatre fois, sur un même profil fictif et un stockage DPAPI isolé. L’ordre est précédent, candidat, retour au précédent, puis candidat. Le tunnel WireGuard de recette est renouvelé entre les phases. Les deux brouillons et le fil enregistré pendant le pilote sont retrouvés après retour et après réactivation. Les deux demandes de réponse ont produit une seule écriture de fil, celle de l’échange enregistré.

Cette répétition échange le relais sous un même hôte Windows. La mise à niveau et le retour par l’installateur signé restent à qualifier sur un poste pilote.

Le 16 novembre, le pont WireGuard, le relais et l’hôte Tauri ont été reconstruits sur D:. L’hôte candidat a exécuté la recette Conversations dans WebView2, avec un serveur fictif. Les brouillons par fil, la reprise après rechargement, l’historique de projet, les conflits et le mode éphémère ont passé les contrôles. Les trois exécutables extraits de l’installateur NSIS correspondent par empreinte aux fichiers de recette. Le composant WASAPI est repris de l’installation existante et son inventaire a été vérifié. L’installateur de recette et `recette-windows.json` se trouvent sous `D:\Kiara\essais\windows-fusion-20261116`. La recette a exécuté l’hôte directement. L’installation, le retour par installateur et la signature Authenticode restent à qualifier.

La recette NSIS en bac à sable prépare l’installation de la référence, du candidat puis le retour à la référence. Elle compare les trois exécutables, l’identité d’installation et un fichier local fictif. Le lancement standard a été refusé par Windows et la demande d’élévation a été annulée. La recette n’a produit aucun résultat d’installation.

La suite générale du serveur a exécuté 651 tests. 649 réussissent, un est ignoré et un échoue dans le scénario de corruption du manifeste du canal Android. Le contrôle `server-windows`, requis pour la livraison Windows, a exécuté les 647 autres tests du lanceur avec 646 réussites et un test ignoré faute de binaire hérité 3.5.63. Les rapports sont dans `validation-serveur-windows`. Les quatre tests propres au canal APK restent dans la suite générale.

Le binaire classique 3.5.63 a été retrouvé sur D: et son empreinte comparée à celle de l’artefact conservé. Le test omis par la suite a passé avec ce binaire. Il vérifie le remplacement signé de l’exécutable, la conservation du profil et la conservation de la version précédente. Voir `validation-serveur-windows\reprise-client-3.5.63.txt`.

Le paquet serveur du candidat regroupé est dans `D:\Kiara\essais\fusion-windows-qualification\serveur-verrou-hermes`. Son manifeste identifie le commit amont Hermes, dont le dépôt local a retrouvé les objets Git après la restauration de Windows. Le rapport `retour-verifie.json` couvre l’archive exacte avec le verrou Hermes 1.45.2. Le portail a conservé les écritures faites avant et après le retour, puis a interdit l’accès au projet d’un autre compte. Les deux roues Python avec leurs empreintes sont dans `validation-dependances\hermes-roue`. Le rapport `recette-bascule-hermes.json` vérifie la mise à jour, le retour et la réapplication du correctif hors ligne en Python 3.14.9, dans un environnement temporaire.

La copie complète du runtime Hermes corrigé a également passé `pip check` et chargé le module de passerelle depuis le dossier de lancement réel. Les sept verrous et l’audit OSV des 219 versions passent avec cette copie utilisée comme environnement de recette Hermes. Voir `validation-dependances\runtime-locks-candidat.json` et `validation-dependances\python-security-candidat.json`. La version active de Hermes reste sur 1.45.1 jusqu’à la bascule.

La recette Python ciblée couvre la bibliothèque de sources, l’accès aux projets, les régressions de la fusion, la restauration des notes et le triage. Elle compte 153 réussites et un test ignoré. Le journal JUnit se trouve dans `validation-projets-python\resultats.xml`.

La fiche projet utilise les quatre rubriques Vue d’ensemble, Pilotage, Documents et Réunions. Le rendu secondaire et les styles de son menu ont été retirés. Les sauvegardes JSON manuelles sont téléchargées sous le nom `Kiara-Projet-<code>.json`. Les 1 032 tests du portail, le contrôle TypeScript et la compilation passent dans `validation-portail-unifie`.

Le paquet serveur final a été lancé derrière un proxy HTTPS local et testé dans Chrome avec deux comptes fictifs. Le certificat de recette est épinglé pour le navigateur et approuvé uniquement pour le processus Node des requêtes de test. La recette a vérifié les quatre rubriques, le rechargement d’un lien Documents, les refus hors périmètre, la reprise du brouillon et l’absence de stockage du brouillon éphémère. Le rapport et l’empreinte du paquet sont dans `recette-https-paquet-final\recette-https.json`.

La recette NSIS peut être lancée sans Bac à sable depuis PowerShell administrateur avec `D:\Kiara\essais\fusion-windows-qualification\distribution\recette-installateur-compte-local.ps1`. Elle utilise un compte Windows standard temporaire, un dossier de travail sur D:, les deux installateurs de distribution et le registre du compte de recette. Le scénario qualifie le passage 4.0.7 vers 4.0.8 puis le retour à 4.0.7. La recette du compte temporaire reste à exécuter.

Le même cycle a passé sur le poste Windows hôte, sans Bac à sable et avec le client fermé. Le test a sauvegardé les binaires et la clé de désinstallation de la 4.0.6 locale sur D:, puis exécuté les trois phases 4.0.7 → 4.0.8 → 4.0.7. Chaque phase a contrôlé la version au registre, le dossier d’installation et les empreintes des trois exécutables. L’environnement de l’installateur pointait vers un profil fictif. Le test a réinstallé et vérifié la 4.0.6 locale, et le canal du lanceur répondait toujours 4.0.7. Voir `distribution\recette-installateur-poste.json`.

La recette du canal de mise à jour a passé avec l’archive serveur finale et les deux installateurs exacts. Le client a rejeté un téléchargement dont un octet était altéré et a supprimé le fichier incomplet. Au retour du canal sur la 4.0.7, un client 4.0.6 a reçu le paquet signé de référence. Un client 4.0.8 ne s’est pas vu proposer de rétrogradation automatique. Le rapport `distribution\recette-canal.json` renseigne les empreintes. La clé Ed25519 utilisée est celle de la recette isolée.

Les installateurs de retour 4.0.7 et 4.0.6 ont été contrôlés avec la clé du lanceur en service. Leurs tailles et empreintes correspondent aux manifestes signés et aux copies conservées sur D:. Le canal en service annonce la 4.0.7 et le flux téléchargé depuis le lanceur local correspond à cette référence. Voir `distribution\retour-references-verifiees.json`.

Le précontrôle de la bascule regroupée a retrouvé les 11 projets via le lanceur. Les quatre fichiers du portail actif contenus dans l’archive du serveur 4.0.7 sont identiques à la référence de retour. Les preuves HTTPS, canal de mise à jour, cycle NSIS et retour serveur correspondent aux empreintes du paquet et de l’installateur candidats. Voir `precontrole-couple-windows.json`. Aucun certificat avec clé privée autorisé pour Authenticode n’est disponible dans les magasins personnels consultés sur le poste. La signature Ed25519 du canal et Authenticode de l’installateur sont deux opérations distinctes.

Le manifeste 4.0.8 est signé avec la clé Ed25519 du canal Kiara et préparé sous `distribution\canal-pret`. Le sélecteur 4.0.8 a accepté le manifeste et l’installateur dans un dossier de publication isolé. Le rapport `precontrole.json` enregistre les empreintes du sélecteur candidat et du sélecteur de retour 4.0.7. Le certificat Authenticode n’a pas été ajouté. Toute modification de l’installateur, y compris l’ajout d’une signature Authenticode, invalide son empreinte et impose de signer un nouveau manifeste Ed25519.

Les 23 écarts des fichiers exécutés ou servis entre les deux ZIP ont été inventoriés dans `fichiers-bascule-et-retour.json`. La répétition 4.0.8 → 4.0.7 → 4.0.8 a contrôlé leur contenu, y compris la réapparition des fichiers supprimés, et préservé un fichier de données fictif hors de cette liste. Voir `repetition-fichiers-bascule.json`. Le droit de redémarrage du PID du lanceur a été vérifié par ouverture d’un handle Windows, sans arrêter le processus.

La 4.0.8 Windows a été publiée avec l’installateur validé sans Authenticode et son manifeste Ed25519. Le portail unifié a été activé dans la même fenêtre. Après redémarrage du lanceur, le service Projets a retrouvé les 11 projets et le téléchargement du canal a renvoyé l’empreinte du paquet candidat. L’installateur et le manifeste 4.0.7, ainsi que le sélecteur du canal et l’index du portail de référence, ont été conservés. La procédure de retour du canal et du portail est `publication-4.0.8\publier-windows-4.0.8.ps1 -Retour`. Voir `publication-4.0.8\publication-verifiee.json`.

Le superviseur autonome qui subsistait dans le dépôt a été retiré. Il était
déjà absent du paquet serveur 4.0.8. Le lanceur Kiara reste l’entrée de
production, et le contrôle d’isolation des variables de test a été déplacé
vers sa suite de supervision.

## APK Android de recette du 16 novembre

Le paquet debug 1.0.27 (code 28) et l’APK de tests sont sous `D:\Kiara\essais\android-fusion-20261116`. Le lint Gradle, la signature Android Debug et l’empreinte de l’interface embarquée ont été vérifiés. Sur l’émulateur API 36, le démarrage, le chiffrement et la fusion des historiques, la conservation du rattachement projet et les contrôles du mécanisme de mise à jour ont passé la recette. La sonde vers le serveur réel valide DNS et TLS et reçoit le refus attendu sans identifiant. Le téléchargement de gros originaux avec ce paquet et le parcours autorisé sur téléphone physique restent à vérifier. Voir `recette-android.json` et les journaux du dossier.

## Compatibilité à suivre après le pilote

État relevé le 16 novembre 2026. Revoir ces compatibilités avant le retrait de toute route ou de tout format. Les liens et archives précédemment distribués peuvent rester nécessaires après la mise à jour des clients.

L’activité déclarée au lanceur enregistre un poste Windows en 4.0.5 le
16 novembre à 10 h 51 et un poste en 3.5.55 le 7 novembre à 12 h 25.
Les deux déclarations indiquent HTTPS et le protocole 4. Le catalogue de
distribution enregistre par ailleurs quatre profils générés en 3.5.63 et
un en 3.5.3. La version générée renseigne la distribution, tandis que
l’activité renseigne le dernier contact connu. Ces relevés ne donnent
pas le chemin HTTP emprunté par ces postes.

| Contrat en transition | Composant responsable | Versions et preuve à obtenir avant retrait |
| --- | --- | --- |
| `/agent/` et les liens sous ce préfixe | Passerelle HTTPS Kiara | `/kiara/` est disponible depuis le pilote du 16 novembre. Recenser les liens publiés, tester leurs remplacements et conserver un accès aux destinations diffusées. |
| `/api/agent-service` et `agent-service.json` | Lanceur Kiara | Le candidat accepte `/api/project-service` et `project-service.json`. Migrer la configuration et les appels des scripts d’exploitation puis éprouver le retour en lisant la configuration précédente. |
| `/client/agent/session` | Relais Windows et client Linux | L’interface extraite du relais livré dans l’installateur Windows 4.0.5 appelle cette adresse. La version candidate utilise `/client/project-session`. Conserver l’alias tant que la 4.0.5 reste une version installée ou une référence de retour. Vérifier l’ouverture de Projets après la mise à niveau des postes relevés. |
| `/v1/client/kiara4/release` et `/v1/client/kiara4/download` | Canal Windows | Le lanceur candidat sert le même manifeste signé et le même installateur que le canal Windows courant. Garder les anciennes adresses pendant la migration des clients qui les appellent. La 3.5.63 a été validée en recette. Pour le poste déclaré en 3.5.55, confirmer la mise à jour ou le remplacement de son accès avant de retirer ces adresses. |
| `.qwenbackup` et compagnon `.kiara-agent` | Sauvegardes et restauration Kiara | La restauration isolée de la paire du 16 novembre est vérifiée. Garder le lecteur du format ancien tant que des points de reprise conservés l’utilisent. |

## Paquets Linux

Les archives Linux candidates pour amd64 et arm64 sont dans `E:\Kiara-Integration\Build\fusion-kiara\candidat-linux`. Les empreintes des 80 fichiers de chaque archive, la présence du composeur commun et l’architecture du relais ELF ont été contrôlées. Le démarrage avec un WebView sur un poste Linux reste à tester.

Les archives 3.5.63 reconstruites le 16 novembre et le rapport `recette-linux.json` sont sous `D:\Kiara\essais\linux-fusion-20261116`. Les 80 fichiers par architecture correspondent à leur manifeste. Chaque pont WireGuard est un ELF de l’architecture annoncée et l’interface embarquée correspond aux sources communes de Conversations. Le démarrage Qt/WebView sur Linux reste à vérifier.

La recette Ubuntu 24.04 amd64 sous WSL a installé le paquet et validé l’autotest du relais avec un profil fictif chiffré. Qt WebEngine a chargé l’interface après ajout de `libxcb-shape0`. La sonde graphique échoue ensuite car `pywebview.evaluate_js` utilise `eval`, que la politique de contenu de Kiara bloque. Lors de la reprise Linux, traiter aussi l’appel équivalent du contrôle de fermeture et vérifier la conservation des brouillons. La distribution de recette est arrêtée et son disque est sur D:.
