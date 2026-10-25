# Plan d’intégration de l’assistant Kiara

Date : 25 octobre 2026. Statut : **première intégration publiée — serveur/Windows
3.5.52, Android 1.0.23/code 24 ; validations matérielles et compléments en cours**.

Ce document organise les six améliorations demandées : mémoire gérée en
conversation, actions vocales, rappels et travaux récurrents, bilans de projet,
activation mains libres et images pendant une conversation. Il organise leur réalisation et leur qualification. Le [rapport de livraison](maintenance/2026-10-25-assistant-integration/README.md)
distingue désormais code intégré, tests, publication et limites matérielles.
Les fonctions d’attente vocale, de relevé Android et de synthèse automatique restent
facultatives et désactivées initialement.

Le [guide commun](GUIDE-ASSISTANT-KIARA.md) décrit les fonctions publiées pour
les utilisateurs Windows et Android.

## Résultat attendu

Depuis Windows et Android, l’utilisateur peut :

- demander à Kiara de retenir, montrer, corriger ou oublier une information ;
- retrouver une information, créer une note ou gérer une tâche en parlant ;
- programmer un rappel ou un compte rendu récurrent et vérifier sa programmation ;
- reprendre un projet avec ses décisions, ses prochaines étapes et ses sources ;
- démarrer l’écoute sans toucher l’écran, sur les appareils compatibles et activés ;
- joindre une photo ou une capture choisie et poser sa question oralement.

Les commandes écrites et orales ont les mêmes droits et effets. Chaque résultat
enregistré est vérifiable dans le client, y compris après reconnexion.

## État de départ vérifié dans les sources

L’inventaire décrit les points d’appui du 25 octobre. Les documents historiques
ne suffisent pas à établir l’état d’un appareil ou une publication.

| Domaine | Existant à réutiliser | Complément nécessaire |
| --- | --- | --- |
| Mémoire Kiara | Souvenirs personnels et par projet dans SQLite, recherche EG2 et lexicale, sources et quotas | Gestion en conversation, révisions, provenance, correction et oubli |
| Mémoire Hermes | Souvenirs, compétences et sessions propres au profil | Clarifier l’autorité et éviter deux mémoires personnelles contradictoires |
| Chat écrit | Sessions Hermes et outils Kiara de lecture, calcul et web | Écritures métier bornées et résultats persistants |
| Vocal | Réponse directe Qwen, recherche web intégrée, lecture progressive, interruption et contexte borné | Le parcours direct refuse les outils génériques ; ajouter un contrat de commandes contrôlé |
| Tâches | File persistante, annulation, reprise explicite, échéance et répétition | Projet actuellement obligatoire ; répétition limitée à 24/168 heures, sans calendrier local complet |
| Notifications | Boîte persistante, synchronisation et annonces connectées Windows/Android | Rappels sans inférence ; livraison Android hors application à concevoir et mesurer |
| Vision | Images jointes au chat, validation des formats et vision locale | Capture choisie, liaison au tour oral et comptage multimodal du contexte |
| Clients | UI partagée, adaptations Android et couches natives audio | Parcours communs pour les six améliorations |

Sources locales principales : [mémoire](lanceur/MEMOIRE-EG2.md),
[Hermes](lanceur/HERMES-FRED.md), [stockage et tâches](lanceur/workspace.py),
[outils](lanceur/hermes_tools.py), [passerelle](lanceur/remote.py),
[protocole vocal](lanceur/voice_response.py),
[contexte vocal](lanceur/voice_context.py),
[notifications](lanceur/RECHERCHE-NOTIFICATIONS.md) et
[pièces jointes](client-qwen/chat_attachments.py).

Le [rapport vocal du 25 octobre](maintenance/2026-10-25-vocal-realtime/README.md)
documente des attentes ponctuelles très longues, sans cause unique démontrée.
Le premier lot mesure les performances avant tout ajout de travail en arrière-plan.
Les variantes Low/Max et leurs réglages actuels sont conservés.

## Principes d’intégration

1. **SQLite Kiara porte les données métier de référence.** EG2 reste un index
   reconstructible. Hermes et le vocal appellent les mêmes services pour les
   nouvelles commandes, sans ajouter une troisième mémoire autonome.
2. **Le serveur détermine le périmètre.** Propriétaire, projet, conversation et
   demande active viennent de l’authentification, jamais du choix libre du modèle.
3. **La discussion simple reste rapide.** Conserver la réponse orale progressive
   sans ajouter une classification à chaque échange. Une commande passe par une
   sortie structurée validée ; un texte prononcé ne devient pas une action.
4. **Une demande explicite autorise une action simple et réversible.** Ne pas
   redemander systématiquement confirmation pour « retiens ceci » ou « crée une
   note ». Clarifier une cible ambiguë ; présenter les modifications sensibles ou
   destructrices avant validation, suivant le lot 9 du plan global.
5. **Un résultat confirmé correspond à une opération enregistrée.** Une coupure,
   une répétition réseau ou un double clic ne doivent pas répéter l’écriture.
6. **Récupération et confidentialité suivent les contrats existants.** Révocation,
   annulation, quotas, sauvegarde chiffrée et restauration couvrent les nouvelles
   données. Les fonctions matérielles restent désactivables par appareil.

## Ordre et dépendances

Les identifiants I0–I8 appartiennent à cette extension et ne renumérotent pas les
lots du [plan global](PLAN-GLOBAL-SERVEUR-FRED.md).

| Lot | Contenu | Dépendance | Livraison vérifiable |
| --- | --- | --- | --- |
| I0 | Inventaire, migrations et référence de performance | — | Contrats et mesures de référence |
| I1 | Services communs de commandes et contrôle des écritures | I0 | Même commande testée par chat et voix |
| I2 | Mémoire en conversation | I1 | Retenir, consulter, corriger et oublier |
| I3 | Actions vocales métier | I1, I2 pour les commandes mémoire | Recherche, notes et gestion des tâches |
| I4 | Rappels et travaux récurrents | I3 | Échéances, calendrier local et livraison des alertes |
| I5 | Bilans durables de projet | I2, I4 pour l’automatisation | Reprise du travail avec sources |
| I6 | Activation mains libres | I0, I3 et stabilité vocale | Activation locale Windows/Android selon capacités vérifiées |
| I7 | Photo et capture pendant le vocal | I1, I3 et stabilité vocale | Image choisie associée au bon tour |
| I8 | Validation commune et publication progressive | Lots concernés | Versions signées, preuves et récupération |

Chaque lot peut être livré séparément après ses propres contrôles. I8 s’applique
à chaque livraison ; il ne reporte pas tous les tests à la fin du chantier.

## I0 — Préparer et mesurer

- [x] Relever les versions réellement publiées, les capacités client/serveur,
  moteurs actifs et réglages vocaux ; préserver les modifications en cours.
- [x] Inventorier les écritures mémoire Hermes et Kiara ainsi que leurs lecteurs,
  les données déjà dupliquées et leurs contrats de sauvegarde.
- [ ] Mesurer fin de parole → transcription finale → attente de file → premier
  texte → premier son, à froid et à chaud. Distinguer réseau, préparation du
  contexte, inférence et lecture ; ne pas déduire une cause de la seule latence.
- [ ] Constituer un corpus fictif commun : conversation simple, mémoire, document,
  action, rappel et image. Répéter les essais sur matériel réel ; publier le nombre
  d’essais et les médianes/p95 comme mesures exploratoires, sans garantie générale.
- [x] Définir les migrations additives, la négociation de capacités et le format
  des commandes, résultats et éventuelles propositions à confirmer.

**Sortie :** inventaire sourcé, schémas proposés et référence mesurée. Les lots
fonctionnels peuvent avancer en test isolé ; l’automatisation de fond n’est
activée qu’après un essai de concurrence sans aggravation des longues attentes.

## I1 — Partager les commandes entre chat et voix

- [x] Extraire des services métier réutilisables autour de `workspace.py` ; garder
  la passerelle responsable de l’authentification, des droits et de l’annulation.
- [x] Exposer un catalogue borné : lecture, mémoire, notes, tâches et rappels.
  Les adaptateurs Hermes et vocal utilisent ce catalogue. Distinguer les outils
  de lecture des mutations : les annotations actuelles de `hermes_tools.py`
  décrivent uniquement des lectures.
- [ ] Faire évoluer le protocole vocal `R:`/`W:` avec négociation de version et
  messages de commande structurés. Une sortie mal formée ne devient ni une
  commande ni du texte technique lu à voix haute. Conserver l’ancienne voie pour
  les anciens clients et les réponses ordinaires.
- [x] Journaliser identité logique de commande, cible, révision et résultat.
  Pour les écritures locales, effet et résultat sont atomiques dans SQLite ; la
  reconnexion consulte le résultat au lieu de rejouer l’action.
- [ ] Prévoir les états préparé, à confirmer, en cours, terminé, échoué et annulé.
  Une interruption annule les opérations non engagées ; une écriture déjà validée
  est rapportée comme telle, sans annoncer une annulation fictive.
- [ ] Pour une opération sensible : proposition précise, révision de la cible,
  expiration et validation consommable une seule fois. Une validation orale est
  liée à cette proposition dans la conversation active ; un « oui » isolé, ancien
  ou issu de la voix de Kiara n’autorise rien.

**Validation :** droits retirés avant écriture, projet déplacé/archivé, annulation,
confirmation expirée, commande mal formée, double envoi et coupure juste après
validation. Aucun nouvel accès libre au système, au terminal ou aux fichiers.

## I2 — Retenir, consulter, corriger et oublier

Parcours : « Retiens que je préfère des réponses courtes à l’oral »,
« Qu’as-tu retenu ? », « Remplace cette préférence », « Oublie ce souvenir ».

- [x] Étendre les souvenirs existants avec catégorie, portée, révision, origine,
  date et état. Les anciennes entrées restent lisibles sans provenance inventée.
- [x] Garder le cloisonnement actuel par défaut. Une préférence valable dans tous
  les projets doit être désignée explicitement comme telle ; elle ne donne jamais
  accès aux conversations ou documents personnels depuis un autre périmètre.
- [x] Définir la priorité : demande actuelle explicite, consigne du projet puis
  préférence applicable ; signaler les contradictions utiles au lieu de les fusionner.
- [x] Ajouter les commandes au chat et au vocal, puis une gestion commune dans les
  clients pour consulter, modifier et supprimer. L’utilisateur n’a pas à passer
  par la console d’administration pour gérer ses propres souvenirs.
- [ ] Raccorder les souvenirs métier Hermes au service Kiara après inventaire.
  Toute reprise conserve l’origine ; les conflits sont présentés et aucun
  effacement silencieux n’est effectué.
- [ ] Après correction ou oubli, invalider index, contexte dérivé et sessions qui
  pourraient réinjecter l’ancienne valeur. Empêcher la consolidation de recréer
  le souvenir oublié depuis le même ancien échange.
- [x] Distinguer « oublier un souvenir » de « supprimer la discussion source ».
  Expliquer cette différence au moment utile et définir l’effet sur les copies
  dérivées et sauvegardes conservées ; ne pas promettre une purge rétroactive des
  archives chiffrées existantes.

**Validation :** commande écrite puis consultation orale, correction concurrente
sur deux appareils, redémarrage, EG2 indisponible, quota atteint, oubli suivi d’un
bilan et séparation de deux comptes et de deux projets.

## I3 — Agir en parlant

Premières actions : chercher/lire un passage, consulter les tâches, créer une note,
créer une tâche et suspendre/annuler une tâche désignée. Les rappels relèvent d’I4.

- [x] Réutiliser les recherches et écritures Kiara via I1, avec les mêmes contrôles
  depuis Hermes et la voix. Une cible manquante fait poser une question.
- [ ] Pour une note, afficher son projet et permettre de l’ouvrir après création.
  Pour un document existant, vérifier la révision et présenter les changements
  sensibles avant application, conformément au lot 9 du plan global.
- [x] Afficher progression et résultat durable dans la conversation ; à l’oral,
  lire une réponse courte utile, par exemple le titre et le résultat.
- [x] Conserver l’annulation pendant la recherche et la préparation. En cas
  d’échec de sauvegarde, garder la proposition et offrir une récupération.

**Validation :** mêmes effets depuis texte et voix, cible ambiguë, refus de droit,
double envoi, modification concurrente, interruption, arrêt du serveur et
consultation du résultat après reconnexion sans seconde création.

## I4 — Rappels et travaux récurrents

Parcours : « Rappelle-moi demain à 18 h de reprendre ce dossier »,
« Chaque lundi à 9 h, prépare le point sur ce projet », « Décale ce rappel ».

- [x] Étendre la file existante avec un rappel personnel sans projet obligatoire,
  distinct d’un travail d’analyse. Un rappel simple n’appelle ni Qwen ni Hermes.
- [x] Conserver instant UTC et fuseau choisi. Une récurrence à heure locale suit
  le calendrier, au lieu d’ajouter systématiquement 24 heures ; préciser la règle
  pour les heures absentes/doublées au changement d’heure.
- [ ] Présenter date comprise, heure, fuseau et prochaine occurrence. Clarifier
  les horaires ambigus ; permettre consulter, modifier, suspendre, supprimer et
  décaler sans chercher un identifiant technique.
- [x] Identifier chaque occurrence pour éviter les doublons et empêcher le
  chevauchement. Après arrêt : un rappel manqué est signalé une fois avec son heure
  prévue ; un rapport récurrent manqué n’est pas rejoué en rafale. Une écriture
  interrompue n’est pas rejouée automatiquement.
- [ ] Livrer I4a : boîte serveur, clients connectés et rattrapage existants ; tester
  la priorité des interactions humaines sur les analyses encore en attente.
- [ ] Livrer I4b : notifications Android hors application visible. Étudier alarme
  locale pour les rappels synchronisés et transport distant pour les résultats
  serveur ; vérifier permissions et limites système avant choix. Une alarme locale
  ne reçoit pas un nouveau résultat serveur sans transport.
- [ ] Définir les comportements appareil éteint, réseau absent, application forcée
  à l’arrêt, révocation et modification depuis un autre appareil. Vérifier
  l’invalidation des anciennes alarmes et le dédoublonnage avec la boîte serveur.
- [x] Les travaux récurrents n’obtiennent pas un droit général d’écriture ; une
  action qui demande validation reste en attente de l’utilisateur.

**Validation :** horloge contrôlée, passages été/hiver Europe/Paris, redémarrage,
maintenance à l’échéance, deux appareils, notifications refusées, révocation et
Android réel verrouillé/en veille. I4a ne valide pas I4b par substitution.

## I5 — Reprendre un projet avec un bilan fiable

Parcours : « Où en étions-nous ? », « Fais le point sur ce projet »,
« Cette décision a changé ».

- [ ] Ajouter une fiche par projet : décisions confirmées, tâches restantes,
  questions ouvertes et dernière étape. Chaque élément garde sources, révisions
  et date de mise à jour ; la fiche est un dérivé reconstructible.
- [x] Commencer à la demande. Séparer décision explicite, suggestion de l’assistant
  et information à confirmer ; ne pas transformer une réponse passée en fait ni
  écraser une correction manuelle par un résumé.
- [x] Lors d’une suppression, modification ou déplacement de source, invalider les
  éléments concernés avant leur prochaine utilisation, y compris pendant une
  génération concurrente. Signaler un bilan incomplet ou périmé.
- [ ] Ajouter ensuite une actualisation automatique facultative après une activité
  suffisante, avec regroupement des changements, quotas et budget de contexte.
  Vérifier l’absence d’aggravation de la latence avant activation.
- [ ] Présenter la fiche dans le projet et une synthèse orale courte, avec liens
  vers les passages et les tâches. Le bilan ne remplace pas l’historique.

**Validation :** décision corrigée, sources contradictoires, suppression pendant
calcul, projet archivé, souvenir oublié, absence de source, reconstruction après
restauration et concurrence avec un dialogue Qwen réel.

## I6 — Activer Kiara sans toucher l’écran

- [x] Évaluer un détecteur local dédié, sa licence, ses ressources et la possibilité
  d’un modèle personnalisé « Kiara ». Ne pas supposer ce modèle disponible ni
  faire tourner une transcription complète en permanence.
- [ ] Livrer d’abord Windows et Android avec application visible : activation
  facultative par appareil, retour sonore/visuel, délai d’attente et désactivation
  accessible. La détection reste distincte de l’écoute d’une conversation.
- [ ] Définir l’arbitrage du micro avec dictée et Low/Max. Tester casque,
  haut-parleur, Bluetooth, écho, interruption et reprise. Prévoir plusieurs
  appareils proches : un seul prend l’échange selon une règle explicite.
- [ ] Respecter micro coupé, appel système, refus de permission et raccrochage.
  Le détecteur ne transmet ni ne conserve l’audio avant activation ; l’affichage
  de l’écoute correspond à l’état réel du microphone.
- [ ] Traiter séparément Android en arrière-plan/verrouillé : rôle d’assistant
  système ou service selon les possibilités vérifiées, consommation et indicateur
  système. Déclarer les appareils/états pris en charge ; garder un raccourci
  accessible lorsque l’activation permanente n’est pas possible.

**Validation :** corpus français avec noms proches, faux déclenchements par heure,
taux d’activations manquées et délai d’ouverture ; essais humains en silence/avec
bruit, batterie Android, fermeture effective et comportement verrouillé. La partie
arrière-plan reste expérimentale tant que le matériel ne la valide pas.

## I7 — Joindre une image pendant le vocal

- [x] Commencer par une image ponctuelle choisie : photo/galerie Android, fichier
  ou capture de fenêtre/région Windows. Réutiliser les pièces jointes existantes.
- [x] Prévisualiser et permettre le retrait. Associer l’envoi à la question et au
  tour exacts ; changer de conversation, annuler ou raccrocher ne doit pas envoyer
  une ancienne capture dans la demande suivante.
- [x] Étendre et tester le comptage de contexte vocal pour les images ; le compteur
  actuel décrit le texte et ne démontre pas la prise en charge multimodale orale.
  Vérifier formats, poids, dimensions, capacités du modèle et limites mémoire.
- [x] Garder le texte de la question si capture, encodage, réseau ou vision échoue.
  Proposer de recommencer ou de poursuivre sans l’image.
- [x] Définir la conservation avant envoi : pièce jointe conservée dans l’historique
  selon les règles actuelles ; captures temporaires nettoyées. Aucun contenu
  d’image ne devient automatiquement un souvenir personnel.
- [ ] Mesurer la concurrence encodeur visuel/ASR Max si la P2200 est commune.
  Prévoir attente/capacité explicite sans déplacer silencieusement les moteurs
  sur un autre GPU. La première livraison ne nécessite pas de vidéo continue.

**Validation :** petite écriture française, erreur à l’écran fictive, image tournée,
trop lourde/corrompue, vision absente, refus caméra/capture, annulation, changement
de projet, restauration de l’historique et essai Android réel.

## Parcours, compatibilité et données

- Réutiliser `client-qwen/workspace.html`, `conversation.js`, `attachments.js` et
  les composants existants. Donner le même sens à « souvenir », « note », « tâche »,
  « rappel » et « bilan » sur Windows et Android.
- Garder la console pour politiques, quotas et diagnostics. Les actions
  personnelles restent dans les clients, sans navigation parallèle par fonction.
- Adapter Android via `client-android/mobile-ui/` et les couches natives ; générer
  les assets avec `client-android/scripts/Prepare-Assets.py`, sans édition manuelle.
- Appliquer `frontend-human-centered`, `ux-consistency-review` et
  `ux-writing-cleaner` aux parcours concernés. Pour les nouvelles surfaces
  significatives, appliquer `professional-ui-design` et `ux-visual-audit` selon
  [la procédure UX](maintenance/ux-ui/README.md).
- Vérifier chargement, vide, sauvegarde en échec, hors ligne, clavier, focus,
  lecteurs d’écran, clair/sombre, téléphone et tablette. Documenter les limites
  sans annoncer une conformité complète d’accessibilité.
- Négocier capacités et protocoles ; les anciens clients gardent leurs fonctions.
  Tester anciens clients/nouveau serveur et refus lisible d’une commande nouvelle
  si le serveur ne sait pas l’exécuter.
- Mettre à jour ensemble migrations, quotas, dossiers privés dérivés, indexation,
  sauvegardes et validateur de restauration. Tester une ancienne archive dans le
  nouveau schéma. Un retour de binaire ne doit pas ouvrir un schéma incompatible :
  le retour de données suit un point cohérent et préserve les écritures depuis
  la livraison.

## I8 — Valider et livrer par étapes

Pour chaque lot, conserver dans `maintenance/<date>-assistant-iN/` un rapport,
les versions/manifeste exacts, les contrôles, les preuves et leurs limites.

1. Développer avec des données fictives isolées et des commandes désactivables.
   Tester droits, transitions et pannes qui peuvent perdre ou doubler une donnée ;
   réutiliser les suites existantes plutôt que dupliquer leurs tests.
2. Exécuter les contrôles proportionnés de [RECONSTRUIRE-FRED.md](RECONSTRUIRE-FRED.md) :

   ```powershell
   & '.\Strata-src\.venv\Scripts\python.exe' maintenance/check_sources.py
   & '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s lanceur -v
   & '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s client-qwen -v
   & '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s client-voice -v
   & '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s client-android/tests -v
   npm.cmd --prefix client-qwen test
   npm.cmd --prefix client-qwen run ux:check
   & '.\Strata-src\.venv\Scripts\python.exe' client-android/scripts/Prepare-Assets.py --check
   ```

   Les suites ciblées servent pendant le développement ; lancer les régressions
   pertinentes avant livraison et les quatre suites Python avant publication
   commune. Examiner les avertissements UX sans suppression automatique.
3. Vérifier migrations et sauvegarde/restauration en environnement isolé :
   souvenirs corrigés, propositions, rappels, calendriers, résultats, bilans et
   pièces jointes. Les actions ne repartent pas toutes seules après restauration ;
   les rappels suivent la politique de rattrapage d’I4.
4. Faire les parcours Playwright avec captures et les tests natifs appropriés.
   Une simulation ne valide ni acoustique, ni caméra, ni arrière-plan Android.
   Documenter les appareils absents ; ne pas cocher ce qui n’a pas été essayé.
5. Construire en staging, vérifier signatures et manifestes, préparer anciennes
   distributions et retour de données, puis réaliser la sauvegarde chiffrée
   vérifiée avant mise en service selon la procédure du projet.
6. Activer progressivement sur un accès de test puis les appareils prévus.
   Comparer données, clés, processus Qwen et sauvegardes avant/après. Distinguer
   développé, testé, publié et activé dans le rapport.

**Critère final :** les six parcours fonctionnent sur les plateformes et états
annoncés, sans opérations dupliquées ; droits et sources restent corrects, les
erreurs offrent une récupération et aucune régression vocale inexpliquée n’est
établie. Toute limite matérielle reste visible dans le suivi.

## Suivi de la première intégration

Les cases cochées décrivent des exigences implémentées et vérifiées dans le
périmètre du rapport. Les cases restantes gardent les exigences partielles,
enrichissements et validations physiques ; elles ne signifient pas que le lot
entier est absent. Ne pas déduire une validation matérielle des tests simulés.

| Lot | Réalisé | Limites et suite |
| --- | --- | --- |
| I0 | Inventaire, état antérieur conservé, migration additive, corpus fictif et essais Qwen réel | Chaîne complète micro → son, séries froid/chaud et p95 à mesurer |
| I1 | Service commun, outil Hermes, commandes C: vocales, droits, révisions, journal atomique et dédoublonnage | Propositions sensibles génériques du lot 9 non ouvertes ; commandes présentes limitées au métier |
| I2 | Mémoire écrite/orale et UI commune, préférences globales explicites, correction, oubli, sessions invalidées | Masquage par tokens/source, sans garantie d’effacement sémantique de toute paraphrase ni purge des archives |
| I3 | Notes, lecture et création de tâches, pause/annulation, résultat vocal court et durable | Liens directs et propositions de modification de documents existants à compléter |
| I4 | Rappels sans inférence, fuseaux/récurrences, occurrences dédoublonnées, analyses programmées et boîte serveur | Relevé Android facultatif ≥ 15 min ; pas d’alarme exacte. Veille et batterie physiques à vérifier ; pause/reprise dédiée des rappels à enrichir |
| I5 | Bilan avec sources/version, synthèse à la demande, invalidation, actualisation facultative bornée | Concurrence prolongée à mesurer avant activation généralisée ; restitution enrichie/liens à compléter |
| I6 | Détecteur local dédié épinglé, phrase « Bonjour Kiara », micro arbitré, attribution à un appareil | Expérimental ; petit corpus synthétique uniquement. Pas d’activation Android verrouillé/arrière-plan ; réarmement après appel |
| I7 | Image choisie au bon tour, photo/galerie Android, région Windows, limites et réserve de contexte | Caméra/micro physiques, rotation, texte fin et concurrence encodeur/ASR Max à mesurer |
| I8 | Régressions, migration/restauration isolées, UI MCP, staging, signatures, sauvegarde vérifiée et publication | Mise à jour à installer sur appareils ; qualification matérielle et retour complet sur le terrain non revendiqués |

Preuves : [rapport et usage](maintenance/2026-10-25-assistant-integration/README.md),
[publication Windows](maintenance/2026-10-25-assistant-integration/production.json),
[publication Android](maintenance/2026-10-25-assistant-integration/android-publication.json),
[contrôles du serveur](maintenance/2026-10-25-assistant-integration/assistant-production.json).

Choix retenus : sherpa-onnx dédié et phrase complète expérimentale, JobScheduler
Android sans service externe, bilans de 12 000 caractères maximum avec regroupement
et intervalle minimum de cinq minutes, mémoire Kiara canonique et anciens fichiers
Hermes proposés à la reprise manuelle. Les actions sensibles ne sont pas ajoutées
implicitement au catalogue. Aucun service externe nouveau n’a été activé.

## Inspirations examinées

Reprendre les principes en réutilisant les composants Kiara. Une reprise de code
tiers nécessiterait une vérification de licence et de version.

- [Open WebUI — mémoire](https://docs.openwebui.com/features/chat-conversations/memory/)
  et [mode vocal](https://docs.openwebui.com/features/chat-conversations/chat-features/voice-mode/) :
  souvenirs gérables et images pendant la conversation.
- [LibreChat — mémoire](https://www.librechat.ai/docs/features/memory) et
  [conversations planifiées](https://www.librechat.ai/docs/features/scheduled_chats) :
  préférences contrôlables et travaux récurrents ; planification expérimentale.
- [Letta — mémoire et consolidation](https://docs.letta.com/configuration/memory) :
  bilan durable et actualisation de notes, sans réentraîner les poids de Qwen.
- [Home Assistant Assist](https://www.home-assistant.io/voice_control/) :
  actions vocales et activation locale, à adapter aux capacités vérifiées de Kiara.
