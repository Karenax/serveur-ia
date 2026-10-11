# Contexte de reprise — serveur Fred

Mise à jour : 12 octobre 2026.

## Objectif actuel

Dernière demande : laisser Hermes effectuer ses recherches web dans les conversations Fred. L’audit des deux derniers appels web retrouve un refus du droit Web du compte et l’ancien outil Brave Fred ; le profil Fred n’exposait pas les outils web natifs Hermes. La correction raccorde `web_search` et `web_extract` aux connexions du profil Hermes actif, sans dupliquer les secrets dans les profils Fred. Le droit Web du compte actuel est activé ; ses autres quotas restent conservés. Les appels sont liés au tour natif pour refuser ceux d’un message annulé, et les redirections privées sont filtrées. Les anciennes tâches Web restent sur leur moteur Brave/lecture d’URL, avec un libellé explicite dans la console. Livraison serveur effectuée après 151 tests réussis, avec recherche et lecture natives réelles validées. Qwen reste chargé, les clés/profils et la sélection des quatre modèles externes sont préservés. Les clients publiés Windows 3.5.27 et Android 1.0.10/code 11 conservent leur protocole et n’ont pas besoin d’une nouvelle installation pour cette correction serveur. Preuves : [recherche web native](preuves/nativeweb-fred-20261012/VALIDATION.md).

Demande précédente : vérifier le niveau de réflexion des messages Nemotron et
proposer seulement les réglages disponibles pour chaque modèle. L’audit en
lecture seule retrouve high pour les deux derniers envois, par correspondance
exacte des empreintes Fred ; max était silencieusement normalisé vers high.
Le Nemotron Ultra OpenRouter utilisé annonce medium/high, avec désactivation
facultative : le maximum disponible est high. La correction conserve les
efforts canoniques, contrôle les capacités du modèle et mémorise le choix par
modèle dans les clients Windows/Android. Les modèles à simple activation ont
Sans/Activée ; ceux sans réglage connu gardent le comportement automatique.
Livraison publiée : Windows/serveur 3.5.27, Android 1.0.10/code 11.
Preuves : `preuves/reasoning-models-20261011/`.

Demande précédente : sélectionner les modèles Hermes par fournisseur dans la
console admin, avec un bouton Tout désélectionner. Les cases par fournisseur
permettent notamment de retirer Nous Portal en une action. Ces contrôles
réutilisent exposed_models, passent en sélection manuelle et conservent les
droits de partage ; Qwen local reste disponible. La console sert les fichiers
actualisés sans redémarrage ni nouvelle compilation des clients.
Preuves : `preuves/provider-selector-20261011/`.

Demande précédente : corriger le catalogue et le défilement du sélecteur Hermes.
Fred lisait ~/.hermes au lieu du dossier natif Windows %LOCALAPPDATA%/hermes.
La correction suit le profil actif et masque les modèles externes indisponibles.
La console Clients → Modèles disponibles dans Hermes permet de proposer tous les
modèles utilisables ou une sélection explicite, avec recherche et défilement.
Le modèle reste associé à chaque conversation et à la voix Windows. Le partage
global vaut pour les comptes actuels et futurs ; les données restent séparées.
Les trois boutons du correcteur restent directement sur Qwen.
Livraison Windows/serveur 3.5.26 et Android 1.0.9/code 10. Preuves de correction :
`preuves/model-picker-fix-20261011/`. Le précédent diagnostic sur les connexions
OpenAI/Copilot concernait le mauvais dossier Hermes et est corrigé par cette
livraison. Le profil natif actuel est default avec serveur-perso et le Qwen local.
Le bon dossier contient aussi les connexions Nous Portal, OpenRouter et
ChatGPT/Codex ; elles sont partagées selon la politique globale autorisée.

Dernière correction : conversation vocale Windows arrêtée par la synchronisation automatique de l’historique après une réponse Hermes. La version 3.5.23 conserve la lecture et le microphone pendant cette synchronisation, attend avant le tour suivant et préserve la vraie interruption vocale. Les sept nouveaux scénarios, les dix scénarios avec WireGuard/voix CPU et seize tests Python passent. [Preuves de la correction](preuves/conversation-fix-20261011/VALIDATION.md).

Demande précédente du 11 octobre : intégration complète de Hermes pour toutes les conversations Windows/Android et création automatique de profils à chaque accès client. Hermes est activé et les clients signés Windows 3.5.22 / Android 1.0.6 code 7 ont été publiés. Les essais natifs avec le Qwen local et le contrôle authentifié du client existant passent ; une sauvegarde chiffrée réelle incluant Hermes est créée et vérifiée. La suite finale Hermes compte 59 tests réussis, avec 39 régressions sauvegarde/restauration et 73 régressions accès/espaces/appareils. Un profil par accès, une session par conversation et un projet natif Hermes par projet Fred ; les documents et recherches EG2 restent soumis aux droits Fred. Guide : [HERMES-FRED.md](lanceur/HERMES-FRED.md). Preuves : [validation](preuves/hermes-fred/VALIDATION.md). Les outils système sans isolation ne sont pas activés.

L’utilisateur a autorisé le développement complet des cinq premiers lots du plan global, avec preuves : **lots 0, 1, 2, 3 et 4**. Le plan commence à 0. Il a choisi « Sauvegarde sur le serveur pour commencer » ; aucune destination NAS n’est activée. Il a ensuite demandé les **lots 6 et 8 en parallèle** et l’explication du lot 9, désormais livrés. **Whisper Small multilingue local** est livré sur Windows et Android. Demande précédente : intégrer la conversation vocale complète **uniquement dans Windows**, après la fin de l’autre chat Codex intégrant EG2 et la mémoire. Cette attente a été respectée : « Évaluer le dépôt Talorys » était terminé avant toute modification de cette intégration. La conversation Windows est livrée en 3.5.21 ; Android conserve la dictée manuelle ; les mises à jour automatiques, Hermes puis le correcteur direct puis le sélecteur portent la version actuelle à 1.0.10/code 11.

Ces cinq premiers lots sont **achevés, validés et en service** : 191 tests de régression réussis, 32 scénarios de console, essais Android natifs sur émulateurs téléphone et tablette. Les empreintes des sources sont identiques avant/après cette suite complète. Les lots **6 et 8 sont achevés, validés et en service** : **246 tests de régression réussis en 354,218 s**, 27 scénarios navigateur sans exception JavaScript et essais Android téléphone/tablette sur émulateurs. Les binaires Windows et Android publiés correspondent aux sources vérifiées ; modèle, données, accès et programmation des sauvegardes ont été préservés. La refonte du tableau de bord du lot 5 et les extensions des lots 9/10 restent planifiées. Hermes fournit désormais les outils Fred contrôlés. La conversation du lot 7 est livrée dans Windows ; son extension Android est différée. Le socle minimal d’événements nécessaire aux notifications est intégré, sans déclarer le lot 5 complet.

## Documents de référence

- `PLAN-GLOBAL-SERVEUR-FRED.md` : périmètre complet, lots 0 à 10, dépendances, livrables et validations ; référence principale pour la suite.
- `PLAN-INTEGRATION-HERMES-FRED.md` : architecture et lots H0 à H6 pour les conversations traitées par Hermes et le provisionnement automatique de profils ; code implanté, validation native réelle réussie et clients publiés.
- `PLAN-SAUVEGARDES-APPAREILS.md` : détail complémentaire des deux premières fonctions, désormais rattaché au plan global.
- `client-android/README.md` et `client-android/VALIDATION.md` : installation, fonctionnement et résultats de la livraison Android actuelle.
- `lanceur/SAUVEGARDES-APPAREILS.md` : fonctionnement des nouveaux écrans, programmation et restauration.
- `lanceur/RECUPERATION-SIGNATURES.md` : paquet chiffré indépendant des clés Android et Windows.
- `preuves/lots-0-4/VALIDATION.md` : index des preuves finales, journaux, captures et limites.
- `preuves/lots-6-8/recherche/LISEZ-MOI.md` et `validation.json` : recherche, fidélité des références, migrations et mesures isolées.
- `preuves/lots-6-8/notifications/INDEX.md` : stockage, contrats HTTP et console des notifications.
- `lanceur/RECHERCHE-NOTIFICATIONS.md` : mode d’emploi des passages cités et des boîtes.
- `preuves/lots-6-8/VALIDATION.md` et `delivery-final-check.json` : livraison finale, binaires publiés, scénarios Windows/Android et préservation des données.
- `recherche/voix-20261011/ETUDE-ASR-CLIENTS.md` : comparaison des ASR embarquées françaises, sources officielles, intégration proposée et essais nécessaires.
- `recherche/voix-20261011/ANNEXE-VOIX-SERVEUR.md` : ressources constatées, synthèse française CPU et limites des systèmes de conversation vocale.

## Décisions du demandeur et règles de fonctionnement

- Sauvegardes automatiques, conservation et restauration côté serveur, dans la console d’administration.
- Gestion et révocation des appareils côté serveur, dans la même console.
- Orientation vocale initiale : microphone et lecture sur les clients, transcription/synthèse et droits côté serveur. Le 11 octobre, l’utilisateur demande d’étudier l’ASR directement dans les clients ; l’alternative transcription locale → texte envoyé à Qwen est documentée. Le demandeur a retenu Whisper Small multilingue local ; cette dictée est désormais implantée dans les deux clients. Droits, historique et sauvegardes restent côté serveur.
- Notifications : événements et boîte persistante côté serveur, annonces dans la console et les clients ouverts, rattrapage à la reconnexion. Android ajoute permission système et ouverture du résultat au clic. Le réveil d’une app totalement arrêtée reste un sous-lot distinct ; aucun fournisseur de push externe n’est configuré.
- Réutiliser le stockage et les fonctions existants. Protéger les données actuelles et les profils distribués.
- Une identité/clé API/pair WireGuard par appareil. Pas de fusion automatique des espaces entre appareils d’une même personne.
- Sauvegardes actives chaque jour à 03 h, heure du serveur, conservation 7 jours / 4 semaines / 6 mois, destination `D:\Serveur IA\lanceur\sauvegardes`. Deuxième copie disponible, laissée vide selon le choix du demandeur.
- Les changements métier/externe proposés par l’assistant devront faire l’objet d’une validation explicite ciblée ; pas de terminal général exposé aux clients.

## Architecture constatée

Workspace : `D:\Serveur IA`, Windows/PowerShell. Console locale sur `127.0.0.1:8765`. Serveur Python, modèle Qwen/Strata, deux Tesla P100 ; passerelle et WireGuard Go intégrés.

`backups.py` porte le catalogue, les archives chiffrées vérifiées, DPAPI, la planification, le rattrapage, la conservation et les copies secondaires. `restoration.py` porte vérification, confirmation à usage unique, maintenance, point de retour, journal durable et récupération après panne. `operations.py` intègre les services au processus de la console.

`workspace.py` conserve SQLite, projets, originaux, mémoire, tâches et historiques. `server_state.py` ajoute inventaire, identité stable d’installation et génération de synchronisation ; aucune fusion d’espaces ni changement des clés existantes. `devices.py` conserve les révocations dans un registre privé qui ne revient pas dans le temps. `remote.py`, `accounts.py`, `wireguard_access.py` gèrent accès, sessions, déclarations minimales, annulation et pairs. `maintenance.js/.css` complètent la console locale.

Contrats ajoutés : API d’administration `/api/backups/*`, `/api/maintenance`, `/api/inventory`, `/api/devices/*` ; profil Android direct protégé par token dans l’en-tête ; `POST /v1/device` authentifié et sans attribution de droits ; historique avec génération et refus 409 après restauration pour un ancien état. Les clients récents conservent une copie chiffrée locale avant reprise explicitement confirmée.

La recherche documentaire, la recherche web, les tâches, les mesures RAM/GPU et le diagnostic restent en place. Les outils hôte MCP restent désactivés sur la passerelle.

## Lots 6 et 8 achevés et en service

`workspace.py` améliore la recherche FTS5 par couverture des termes utiles puis BM25. Les filtres propriétaire/projet/document s’appliquent avant la limite de candidats. Les documents exposent état d’indexation, nombre de passages et version indexée. Chaque référence porte un identifiant opaque, document, extrait littéral, version et page réelle lorsqu’elle existe. `source_get` consulte le passage après contrôle des droits et signale source actuelle, modifiée ou indisponible ; l’extrait de la version utilisée est conservé. TXT, Markdown, DOCX et notes n’obtiennent aucun numéro de page inventé. Les résultats de tâches conservent leurs sources, même après suppression du document courant.

Les références entrent dans les quotas et sauvegardes existants ; leur catalogue est dédupliqué et borné à 2 000 par propriétaire et 12 000 au total. Les migrations reconnaissent les anciens schémas exacts et reconstruisent un index FTS périmé à partir des passages actuels. Les limites 2 Mo/fichier, 500 000 caractères extraits, 20 Mo/propriétaire par défaut et 128 Mo global sont conservées. L’OCR reste optionnel et non implanté. La recherche sémantique EG2 a été ajoutée le 11 octobre 2026, voir ci-dessous.

`notifications.py` conserve la boîte, les identifiants et séquences persistantes, lectures, préférences, abonnements et reçus dans la même base SQLite. Les notifications de tâche terminée/échouée et de document indexé utilisent la transaction de l’événement. Les alertes sauvegarde/copie/stockage/restauration sont réservées à l’administration. Conservation : 90 jours, 1 000 événements par accès, 20 000 au total. Les lectures et la suppression des éléments expirés se synchronisent ; après restauration, la génération renouvelle les curseurs et la déduplication. Révoquer un accès retire ses abonnements et reçus et refuse la consultation.

Une tâche interrompue au redémarrage devient échouée avec son événement et sa notification dans la même transaction ; aucune inférence n’est rejouée automatiquement. Les relances ont un compteur durable sauvegardé, indépendant de l’horloge et de la purge du journal : chaque tentative reçoit sa propre notification. Une ancienne exécution annulée ne peut pas conclure la nouvelle tentative.

La console expose sa boîte administrative. Windows et Android exposent une boîte privée, l’ouverture de la tâche ou du document ciblé et les préférences. Android ajoute les annonces système lorsque le client est ouvert/connecté, une demande explicite de permission et un contenu générique discret par défaut ; aucun extrait de document ou conversation n’est publié sur l’écran verrouillé. La boîte continue de fonctionner si la permission système est refusée. L’app totalement arrêtée récupère les éléments à sa reconnexion, sans promesse de réveil hors ligne.

À la livraison des lots 6/8, versions publiées et vérifiées : **serveur/Windows 3.5.18**, **Android 1.0.2, code 3**. EXE et APK signés avec les clés existantes, ressources incorporées identiques aux sources finales, mise à jour Android 1.0.1 → 1.0.2 conservant profil et conversation sur les deux émulateurs. Les versions précédentes sont conservées sous `toolchain/releases-staging/*-before-lots6-8/`.

## Lot 9 : plan initial et outils Hermes livrés

Hermes fournit désormais les recherches, la lecture de sources et le calcul dans le périmètre Fred. Les actions externes et outils système libres restent différés. Le plan initial ci-dessous décrit leur future ouverture.

Ce lot permettra à l’assistant d’utiliser des fonctions serveur précises : rechercher des documents, lire une page publique ou préparer un brouillon. Pour modifier quelque chose, il présentera d’abord la cible, le contenu proposé et l’effet attendu ; l’utilisateur autorisé devra valider cette proposition avant son exécution. Exemple : « Mets le budget à 2 500 € » prépare la modification visible du document Budget ; le clic sur « Valider la modification » autorise seulement cette révision. Si quelqu’un modifie le document entre-temps, une nouvelle proposition est nécessaire. L’accord expirera, ne pourra pas être rejoué et n’ouvrira aucun accès général au terminal. Les connecteurs de messagerie/calendrier restent des extensions séparées à demander explicitement.

## Étude vocale du 11 octobre 2026

Recherche uniquement, sans installation, téléchargement de poids ni changement des services ou des binaires. Première comparaison proposée : Whisper.cpp avec base multilingue pour la dictée et Sherpa-ONNX avec Zipformer FR INT8 pour le texte progressif ; Vosk small FR comme option compacte, Canary 180M comme comparaison intermédiaire. Parakeet v3, Nemotron 3.5 et Qwen3-ASR 0.6B disposent aussi de voies ONNX embarquées françaises, mais leurs fichiers de 640–941 Mio imposent des essais sur appareils adaptés. Moonshine n’a pas de modèle ASR français actuel. Android local natif dépend d’API 31+, du fournisseur et des langues installées. Picovoice Cheetah/Leopard traite l’audio localement mais exige une AccessKey validée en ligne ; conditions commerciales sur devis.

L’intégration garde l’audio de dictée sur l’appareil et transmet le texte confirmé par le chat existant. Dictée hors connexion après installation ne signifie pas réponse Qwen hors connexion. Pour lire les réponses, Pocket TTS français CPU et Piper SIWIS sont les premiers candidats serveur à mesurer. Les P100 actuelles sont presque pleines ; ne pas changer les environnements Qwen ni promettre FP16/INT8 avec CTranslate2 sur Pascal 6.0. Windows a été mesuré sur ce PC ; Android a été mesuré sur émulateurs, sans mesure de batterie ni essai sur téléphone physique. Cette étude précède la livraison suivante : ASR Windows/Android et conversation Windows avec TTS CPU désormais livrés.

## Android déjà livré

- APK signé : `client-android/dist/Acces-serveur-Fred-Android.apk`, package `net.karenax.fred`, version **1.0.10**, code 11, Android 8+ ARM64/x86_64, téléphone et tablette. Les trois modes du correcteur passent par Qwen direct ; les conversations gardent Hermes, avec réflexion réglable selon le modèle.
- Import `.fred-android` ou EXE personnel ; choix explicite HTTPS/WireGuard ; moteur WireGuard intégré.
- Profil, historique et préférences chiffrés localement avec Android Keystore ; synchronisation avec le serveur.
- Compilation et tests sur émulateurs Android 16 téléphone/tablette réussis ; tunnel réel et données synthétiques, transport HTTPS public vérifié sans accès réel. Voir le rapport pour la portée exacte. Validation sur appareil physique encore nécessaire.
- Clé de signature persistante sous `toolchain/android-signing/`, hors Git : la conserver pour les mises à jour. Ne pas copier de secrets dans ce contexte.
- Profil Android direct disponible dans **Appareils** ; conservé chiffré sur le serveur et téléchargé avec autorisation administrateur. L’import de l’EXE personnel reste possible.
- Après restauration : génération incompatible détectée ; reprise explicite et copie précédente rechiffrée avec le bon nom de fichier, pour préserver l’authentification AES-GCM. Tests natifs sur les deux émulateurs réussis.

## Livraison et exploitation actuelles

- Dernière livraison publiée : serveur et client Windows **3.5.27** ; APK Android **1.0.10**, code 11. Manifeste Windows Ed25519 et signature APK vérifiés ; clés existantes conservées. La réflexion suit les capacités du modèle et le choix est mémorisé par modèle ; max incompatible est refusé sans rabattement vers high. Le menu reste stable pendant les redraws et les polls vocaux. Le correcteur reste direct, les téléchargements authentifiés sont vérifiés et Qwen reste chargé ; politique de partage et sélection admin conservées. Preuves : `preuves/reasoning-models-20261011/`.
- Console rechargée avec `Start-Interface-Qwen.ps1 -SansNavigateur -PreserverEtatModele`. Les processus Strata 8200 et 14628 et leurs dates de création sont inchangés ; le modèle reste chargé.
- Archives initiales chiffrées créées et vérifiées sur les données actuelles. État réel et empreintes de cette livraison : `preuves/lots-6-8/production-validation.json`. L’état historique des lots 0–4 reste conservé dans leur propre rapport. Aucune restauration exécutée sur les données de production.
- Phrase forte privée : `lanceur/sauvegardes/phrase-recuperation.txt`, dossier Windows protégé. Ne jamais recopier sa valeur dans ce contexte, Git, journaux ou messages. Secret automatique distinct protégé par DPAPI.
- Paquet privé indépendant `lanceur/sauvegardes/signatures-fred.fredkeys` créé et vérifié : clé Android existante et mot de passe, graine Windows. Voir le guide pour conserver une copie indépendante et récupérer sur une autre machine.
- Sauvegardes, secrets DPAPI et registre `securite/` exclus de Git. Les preuves ne contiennent que des métadonnées, données synthétiques et empreintes publiques.

## Ordre de réalisation et statut

0. Inventaire, migrations, contrats communs — achevé et validé.
1. Sauvegarde complète et catalogue — achevé et validé.
2. Planification, conservation, seconde copie — achevé, validé et activé.
3. Restauration guidée, reprise, synchronisation après restauration — achevé et validé.
4. Appareils et profil Android direct — achevé et validé.
5. Tableau de bord consolidé — planifié ; socle minimal d’événements intégré pour le lot 8.
6. Recherche documentaire et sources — achevé, validé et en service, Windows et Android.
7. Voix — dictée Windows/Android livrée ; conversation et synthèse Windows livrées. Conversation Android différée ; essais acoustiques humains à approfondir.
8. Notifications et livraison aux appareils — achevé, validé et en service en mode connecté avec rattrapage.
9. Outils serveur avec validation des actions — expliqué, planifié ; implantation non demandée.
10. Intégration, récupération et livraison globale — planifié.

La demande de terminer les **lots 6 et 8 en parallèle**, avec preuves, compilation et mise en service, est achevée. Le lot 9 a été expliqué. Le lot 7 a ensuite été autorisé pour la dictée Windows/Android et la conversation Windows. Les lots 5 complet, 9 et 10 restent planifiés.

## Preuves finales

- `preuves/lots-0-4/regressions-final.json` et `.log` : 191 tests réussis, 529,918 s, sources inchangées.
- `preuves/lots-0-4/production-validation.json` et `delivery-final-check.json` : première archive vérifiée, programmation active, fichiers publiés et modèle préservé.
- `preuves/lots-0-4/console/INDEX.md` : 32 scénarios réussis, dont 16 avec le vrai Controller ; 15 captures relues, aucune erreur JavaScript.
- `preuves/lots-0-4/client-delivery-evidence.json` : Windows 3.5.17 et Android 1.0.1 signés, essais natifs téléphone/tablette sur émulateurs, limites physiques documentées.

## Preuves finales des lots 6 et 8

- `preuves/lots-6-8/VALIDATION.md` : index des preuves, modes d’emploi et limites de la livraison.
- `preuves/lots-6-8/regressions-final.json` et `.log` : **246 tests réussis en 354,218 s**, deux groupes isolés, toutes les empreintes produit et tests inchangées. Les suites ciblées ci-dessous sont incluses dans ces 246 tests ; leurs nombres ne doivent pas être additionnés à ce total.
- `preuves/lots-6-8/recherche/validation.json` et `tests.log` : **94 tests réussis en 154,080 s**, sources finales inchangées. Questions contrôlées : 5/5 au rang 1 avec réponse dans l’extrait exact. Document de 460 075 caractères : 288 passages, indexation 32,60 ms, recherche 9,22 ms. PDF réel de deux pages : extraction 294,92 ms et citation page 2. Mesures propres à ce corpus et à ce poste.
- `preuves/lots-6-8/notifications/notifications-tests.json`, `worker-recovery-tests.json` et `source-access-fence-tests.json` : respectivement **28**, **11** et **5** tests réussis ; stockage/HTTP, reprise après panne/relances et contrôle des droits avant émission des sources et appel au moteur.
- `preuves/lots-6-8/notifications/notifications-ui.json` : **11 scénarios console**, quatre captures relues, aucune exception JavaScript.
- `preuves/lots-6-8/client-ui/client-lots6-8-ui.json` : **16 scénarios**, vrai backend isolé et WireGuard UDP compilé, neuf captures relues, aucune exception JavaScript. Expiration d’un reçu et changement de génération entre pages couverts.
- `preuves/lots-6-8/windows-release.json` : Windows 3.5.18, autotest réussi, quatre ressources incorporées identiques aux sources finales. Manifeste signé vérifié avec la clé existante.
- `preuves/lots-6-8/android/delivery.json` et `VALIDATION.md` : APK 1.0.2/code 3 signé, quatre suites natives, deux tunnels UDP réels et **26 contrôles WebView**. Permission refusée/accordée, canaux silencieux/standard, rattrapage, clic système, mise à jour conservant profil et conversation sur les deux émulateurs. Les captures Release après mise à jour sont relues.
- `preuves/lots-6-8/production-validation.json` et `delivery-final-check.json` : fichiers publiés vérifiés, nouvelle archive chiffrée vérifiée, modèle chargé et processus identiques, données et réglages préexistants préservés, sauvegardes à 03 h inchangées, maintenance inactive. Aucun secret n’est recopié dans ces preuves.

## Points de vigilance utiles à la reprise

- Une sauvegarde serveur couvre les données déjà synchronisées ; elle ne récupère pas un brouillon qui n’a jamais quitté un client.
- La révocation survit aux restaurations. La génération empêche la réinjection silencieuse d’un cache client ; Windows 3.5.18 et Android 1.0.2 permettent la reprise explicite. Sur une autre installation, les accès restaurés sont suspendus.
- Le démarrage actuel dépend d’une session Windows ouverte ; un service avant connexion n’est pas installé par ce plan.
- La passerelle WireGuard borne actuellement les requêtes à 2 Mo : prévoir une stratégie bornée pour les transferts audio.
- Le mode livré par le lot 8 est la livraison connectée avec rattrapage. Le serveur ne peut pas réveiller une app Android totalement arrêtée avec cette seule boîte ; push ou service persistant reste une décision distincte, sans fournisseur externe activé.
- Les moteurs Whisper Small et EmbeddingGemma 2 ont été choisis et mesurés ; les autres extensions vocales restent conditionnées à leurs propres mesures de ressources et vérifications.
- La deuxième copie est testée sur dossiers isolés, avec erreurs et nouvelles tentatives ; aucun NAS physique n’a été activé ou validé. Le fonctionnement avant ouverture de session Windows n’est pas installé.
- Format en mémoire borné : stockage global 128 Mio, SQLite restaurable 256 Mio, archive 400 Mio. Huit DOCX/16 Mio testés : sauvegarde 1,67 s, verrous 0,16 s, restauration 6,34 s, pic mémoire 398 Mio. Ne pas extrapoler ces mesures au volume maximal.
- Préserver les modifications locales déjà présentes dans le dépôt, notamment les modules lanceur et la mise à jour du client Windows. Ne pas remettre à zéro le workspace.
- Les tests utilisent des identités et documents synthétiques. La mise en service a ajouté la planification, les archives et les fichiers privés de sécurité ; les empreintes des accès, réglages et clés préexistants sont identiques avant/après.

## Dictée Small livrée le 11 octobre 2026

- Windows 3.5.20 et Android 1.0.3, code 4 : Whisper.cpp 1.9.5, Small multilingue complet, français, CPU uniquement (au plus quatre threads). Le modèle public optionnel fait 487 601 967 octets ; URL/révision/SHA-256 fixés dans `client-voice/model.json`. Modèle installé et vérifié sur ce PC ; installation depuis l’application sur les autres appareils.
- Interface : Dicter, texte provisoire, Terminer la dictée, correction puis Envoyer. Silence de 1,5 s = fin de phrase, microphone encore ouvert. Aucun envoi automatique. Deux minutes maximum ; Annuler restaure le brouillon. Envoi et changements de conversation bloqués pendant la dictée.
- Audio en mémoire, aucun fichier audio en production, aucune transmission au serveur. La fermeture et le passage en arrière-plan libèrent le microphone ; le contexte est déchargé après finalisation/annulation. Les textes deviennent des conversations sauvegardées après l’envoi habituel.
- Moteur commun dans `client-voice/`, service WinMM `client-qwen/local_voice.py`, JNI/AudioRecord `client-android/.../LocalVoice.java`, interface commune `client-qwen/voice.js`. Android debug utilise `net.karenax.fred.voiceqa`, séparé de l’application signée. Les licences complètes, y compris llamafile, sont incorporées aux paquets.
- Preuves et limites : [validation Small](preuves/voix-small-20261011/VALIDATION.md), [guide](client-voice/README.md). 246 tests de régression passent ; les contrôles de livraison ciblés couvrent les derniers ajustements de présentation/version. Transcription française native, silence, annulation, capture, véritable refus de permission et passage en arrière-plan éprouvés. Téléchargement Android réel interrompu, repris et vérifié.
- Sur ce PC, le premier aperçu apparaît vers trois secondes et le moteur ajoute environ 648 Mio au pic de RAM mesuré. Sur les émulateurs, une phrase de 10,05 s demande environ 60–62 s de calcul cumulé ; la dictée de 30,15 s montre du texte avant la fin, avec environ 99 s de calcul cumulé. Aucun téléphone physique n’a été mesuré : ne pas garantir le temps réel avec Small.
- Qwen/Strata, GPU, accès, clés, données logiques et programmation des sauvegardes conservés. Cette livraison de dictée a ensuite été complétée par la conversation Windows 3.5.21 ; Android conserve le mode manuel.

## Mémoire EG2 livrée le 11 octobre 2026

- Demande autorisée : deux moteurs pilotés par le backend, Qwen/Strata pour la génération et EmbeddingGemma 2 pour la mémoire ; connaissances par projet et conversations hors projet séparées. L’intégration est installée et activée sur ce serveur.
- EG2 officiel `google/embeddinggemma-2`, révision `914f7f89142e33e77833254d9c9b90c3cef7303b` ; Sentence Transformers 6.1.0 / Transformers 5.19.0 / PyTorch 2.14.1 dans `toolchain/eg2-python`. Poids dans `toolchain/eg2-model`. Texte seul, float32, CPU, deux threads, 768 dimensions, calcul hors ligne ; aucun composant ajouté à l’environnement Strata.
- `embedding_worker.py`, `embeddings.py` et `knowledge.py` séparent moteur, supervision et index reconstructible. Le processus mémoire suit son parent et possède un garde-fou de RAM à 4 Gio. Le réglage `eg2_enabled` est conservé dans la base originale. La console possède la rubrique **Mémoire et connaissances**, activation/arrêt/reconstruction, souvenirs personnels et recherche par espace.
- Données sources : documents et souvenirs du projet, discussions canoniques et historiques clients synchronisés ; hors projet, seules les conversations et mémoires personnelles du même accès. Identités et projets filtrés avant classement, sources originales revérifiées avant usage. Archives, suppressions/déplacements, réponses interrompues et réflexions internes exclues. Les anciens messages inchangés gardent leurs vecteurs. Une ancienne réponse de l’assistant n’est pas un souvenir confirmé.
- `personal_memories` et `knowledge_exclusions` sont ajoutées à SQLite et incluses dans les sauvegardes chiffrées. Le cache `connaissances-cache.sqlite3` est reconstructible et vidé après restauration. Migrations des archives antérieures validées. Limites : 16 000 passages globaux, 4 000 par accès, budget logique 64 Mio ; 50 souvenirs personnels par accès. Repli lexical si EG2 est arrêté ou indisponible.
- Contrat Windows/Android conservé : le backend enrichit le contexte et retourne les sources via les interfaces existantes. Aucun binaire client reconstruit pour cette extension. Les espaces restent liés à l’identité d’accès existante, sans fusion automatique entre appareils possédant des accès distincts.
- Validation : 257 tests de régression pendant le développement, contrôles ciblés finaux (12 mémoire, 10 restauration, 5 droits en cours de flux, 2 transport chat), six reformulations françaises avec le vrai modèle et huit scénarios console. EG2 prêt, 36 passages hors projet indexés. Qwen et ses processus chargés, empreintes des données/accès/réglages et programmation des sauvegardes conservés ; archives avant/après vérifiées.
- Mesure sur courts textes : environ 14 s de chargement, 1,63 Gio de RAM, huit passages en 0,75 s. Ne pas extrapoler aux textes longs ou à une génération Qwen simultanée. [Guide](lanceur/MEMOIRE-EG2.md) et [preuves](preuves/eg2-20261011/VALIDATION.md).

## Dossiers par client — livraison du 11 octobre 2026

- Demande : regrouper les informations de chaque client dans un dossier serveur spécifique et indiquer les chemins dans la console. En service sous `lanceur/donnees-clients/<identifiant-client>/`, deux dossiers initiaux vérifiés.
- `client_storage.py` publie une base individuelle `donnees.sqlite3` et des fichiers lisibles : fiche/configuration, historique, conversations, projets, textes et originaux des documents, souvenirs, tâches, notifications et références. Un profil personnel disponible est copié sous DPAPI, sans jetons ni clés privées dans les JSON. Les dossiers sont protégés comme les autres répertoires privés de Fred et exclus de Git.
- Organisation par identité d’accès stable : renommer conserve le chemin ; archiver/révoquer conserve les données. Les modifications validées déclenchent une mise à jour, complétée par un contrôle périodique. Manifeste d’empreintes, écriture atomique des fichiers, réparation d’un export manquant/altéré, refus des jonctions et d’un instantané commencé avant une restauration. Les fichiers manuels sont préservés.
- La base commune `espaces-prives/espaces.sqlite3` reste la source transactionnelle du backend et des sauvegardes. Les dossiers individuels sont des représentations synchronisées, pas une migration vers des bases opérationnelles indépendantes ; aucune modification manuelle n’est réinjectée. Les paramètres exclusivement locaux aux appareils et binaires restent à leurs emplacements actuels. Les sauvegardes couvrent les originaux et permettent la reconstruction des dossiers après restauration.
- Console : chemins complets et copie dans Clients/Appareils, racine et dossier sélectionné dans Espaces et fichiers ; mise à jour manuelle authentifiée. Le serveur en service charge la dernière version du module ; Qwen, données, accès, réglages et programmation des sauvegardes conservés, EG2 prêt et voix serveur existante prête.
- Neuf tests ciblés et sept scénarios Chrome passent. La régression exécute 268 tests : 267 réussis au premier passage, un timeout du contrôle de démarrage de l’EXE repasse en 15,438 s au retest isolé. Cause précise du timeout non établie, résultat original conservé. Le dossier d’essai `lanceur/tmpaxzsojxu` reste présent après refus automatique du nettoyage ; son processus est arrêté. [Guide](lanceur/DOSSIERS-CLIENTS.md), [preuves](preuves/dossiers-clients-20261011/VALIDATION.md).

## Conversation Windows livrée le 11 octobre 2026

- Autorisation précédente : conversation complète Windows seulement, après la fin du chat « Évaluer le dépôt Talorys » intégrant EG2/mémoire. Attente respectée avant le début de l’implantation. Android conserve son APK 1.0.3/code 4 ; aucune recompilation Android.
- Serveur/client Windows **3.5.21** : manifeste Ed25519 vérifié et binaire publié. Client : microphone/DSP Windows pour l’écho et le bruit, Zipformer FR INT8 Sherpa-ONNX 1.13.8, Silero VAD, Smart Turn v3.2 CPU. Six modèles optionnels publics, environ 138 Mo, révisions et SHA-256 fixés. Modèles installés et vérifiés sur ce PC ; installation/réparation depuis les autres clients Windows.
- Serveur : Pocket TTS 3.3.0 français, voix Estelle, CPU quatre threads, un traitement simultané, cache public hors ligne. Aucun clonage. Attribution Kyutai et licence CC-BY-4.0 des poids conservées. Environnement dédié `toolchain/voice-server-python`, distinct de Strata et d’EG2 ; compilation client dans `toolchain/conversation-client-python`.
- Conversation : bouton explicite, fin de tour vers 550 ms de silence si Smart Turn valide, borne de quatre secondes si hésitation ; envoi automatique via le chat existant, lecture progressive, reprise de parole qui coupe l’audio et annule uniquement la demande courante. Raccrocher/arrière-plan ferme le microphone. Tour limité à trente secondes ; session quinze minutes. Dictée Small manuelle toujours disponible séparément.
- Audio microphone seulement en mémoire sur Windows ; texte envoyé à Qwen avec les mêmes paramètres/projets et droits, contexte EG2 conservé. Réponses audio transitoires. Historique interrompu limité aux segments entièrement lus ; découpage au mot près non implanté. Activation TTS dans Démarrage et surveillance, persistée dans `voix.json`, incluse et validée dans les sauvegardes/restaurations ; une restauration ferme le moteur.
- Preuves : dix scénarios navigateur, dont véritable transport WireGuard et Pocket TTS CPU, envoi automatique, lecture avant la fin du LLM, interruption contrôlée, arrêt et redémarrage depuis la console ; neuf tests service, six tests HTTP d’accès/révocation/limites, onze tests restauration, huit tests de dictée Small et trois HTTP Small, six scénarios Small. Exécutable empaqueté et capture microphone réelle vérifiés. 276 tests de régression globale réussis en 538.208 s, dans [la validation](preuves/conversation-windows-20261011/VALIDATION.md).
- Mesures sur fixtures : aperçu ASR à 0,8 s d’audio, 10,05 s d’audio calculées en 1,43 s ; moteur client environ 249 Mio de RAM ; premier fragment TTS environ 0,17 s, mémoire TTS environ 859 Mio. Les erreurs grammaticales de la fixture ASR sont conservées dans les preuves. Ces chiffres excluent la génération Qwen et ne garantissent pas la latence complète ou la précision générale. Qualité acoustique/barge-in avec voix humaine dans la pièce non mesurée.
- Mise en service : voix prête, EG2 prêt et 36 passages indexés, aucune attente d’indexation ; Qwen chargé, mêmes PID/créations 8200 et 14628. Empreintes des données logiques, accès, réglages, secrets protégés et APK Android conservées. Programmation des sauvegardes conservée ; nouvelle archive chiffrée vérifiée. [Guide](client-voice/CONVERSATION-WINDOWS.md), [preuve de production](preuves/conversation-windows-20261011/production-validation.json).
