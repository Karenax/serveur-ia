# Corrections de l'audit du 22 octobre 2026

Ce document est le suivi courant des 18 constats de l'audit. Le rapport initial
et les preuves privées restent dans `logs/project-audit-20261022/`. Les preuves
de correction sont dans `logs/audit-remediation-20261022/`. Un état de code ne
constitue pas une qualification matérielle ou une publication Git.

## Décision de périmètre

**A02 — HTTPS écarté explicitement par l'utilisateur le 22 octobre 2026.**
Les adresses HTTP des moteurs sont conservées. Le canal applicatif réseau reste
sans chiffrement ; aucun remplacement d'URL ni certificat inventé. Cette
exception ne s'applique pas aux autres correctifs.

## État des corrections

| Constat | Changement | Qualification courante |
|---|---|---|
| A01 Dépendances Python | Versions corrigées ; environnement `.venv` Agent ; verrous avec empreintes | Versions corrigées installées ; audits des verrous et des trois environnements réels sans avis connu |
| A02 Transport IA | HTTP conservé sur décision explicite | Écarté par l'utilisateur |
| A03 Chemin d'export | Aucune écriture disque lors du GET ; nom de téléchargement indépendant du code projet | Régression traversée de chemin réussie |
| A04 Écrasement d'export | Identité réunion + empreinte de contenu ; téléchargement sans fichier serveur partagé | Deux réunions et rejeu préservés |
| A05 Contexte périmé | Ancienne information automatique exclue du contexte actuel ; historique humain conservé avec réserve ; état déjà périmé signalé | Régressions de contexte réussies |
| A06 Capacité disque | Alerte anticipée à 10 Gio ; réserve de 2 Gio avant imports/sauvegardes ; inventaire sans suppression | Refus 507 avant écriture testé ; aucune purge |
| A07 Consultation lecteur | Liens hérités présentés sans écriture ; liens réels initialisés à la création du projet | Non-mutation du GET et refus lecteur testés |
| A08 Corps HTTP | Comptage ASGI des octets lus, avec ou sans Content-Length et pendant le multipart | Flux et erreurs de parseur ramenés à 413 |
| A09 En-têtes | CSP, refus d'intégration dans une page tierce, nosniff, référent et cache ; exceptions d'inline limitées aux interfaces héritées | Tests HTTP et navigateur réussis, y compris mail HTML, images sur choix explicite, interfaces héritées et Swagger |
| A10 Outillage JS | Vite/Vitest corrigés ; source-map-js corrigé dans la configuration pnpm 11 ; audits CI | Aucun avis npm connu dans le verrou final |
| A11 Reproductibilité | `.venv` dédiée ; `web/node_modules` propre ; ancienne jonction conservée ; profils audio/multimodal transitifs verrouillés | Profils installés audités ; Pillow 13.0.0 et pip 26.2.2 ; arrêt réel du superviseur en environnement virtuel testé |
| A12 Extraction | Processus documentaire limité à 90 s et 1 Gio ; budget OCR par page et document ; annulation coopérative avec reçus conservés | Rendu PDF réel, limites de temps et annulation sans publication partielle testés |
| A13 Sauvegarde | Vérification automatique après création, empreintes en flux, contrôles des bases, commande verify sans restauration | Recette fictive et sauvegarde complète de 1 805 fichiers restaurées ; bases intègres ; santé de la copie conforme sans workers |
| A14 Informations engageantes | Liste « À réexaminer seulement », motifs explicites, confirmation après relecture sur preuve actuelle unique, acteur serveur audité | Tests de confirmation, contradictions et annulation réussis |
| A15 Contexte documentaire | README, backend et contexte courant compacts ; originaux conservés intégralement dans docs/history ; manifeste compatible | Archivage contrôlé par empreinte |
| A16 Livraison | CI allongée, codes de sortie conservés, audits des trois profils Python et du frontend | Suite globale réussie, finitions vérifiées séparément ; sources finales sauvegardées ; livraison Git du 23 octobre 2026 |
| A17 Identité locale | Lanceur normal neutralise AGENT_TESTING ; décisions auditées avec opérateur serveur ; confirmation non usurpable par actor | Rôles et périmètres testés ; comptes individuels requis avant tout futur partage réseau |
| A18 Confidentialité/rétention | Secrets de toutes les sections masqués ; journaux expurgés ; données actives et captures privées exclues de Git ; inventaire sans purge | Tests de masquage réussis ; durées, habilitations du poste et règles d'enregistrement à décider par l'entreprise |

Les résultats globaux, les finitions et l’activation sont distingués dans la
section de clôture. Les décisions d’entreprise encore ouvertes restent explicites.

## Contrats conservés

- Un seul projet, un serveur Agent sur 8001 ; XPilot 8000 reste externe.
- Brain et ERP restent canoniques ; aucune suppression/reclassification de
  données actives, aucun déclassement collectif ni remplacement de validation humaine.
- GET `/api/v1/projects/{pid}/meetings/{mid}/export` conserve sa réponse JSON
  avec `markdown` et `file`. `file` est désormais un **nom de téléchargement**,
  pas un chemin créé sur le serveur. `filename`, `sha256` et `download_url`
  complètent la réponse ; le frontend télécharge réellement le fichier.
- GET `/api/v1/projects/{pid}/meetings/{mid}/markdown` renvoie le document en
  pièce jointe, sans écriture disque. Les anciens fichiers exportés restent présents.
- Les liens requis absents d'un ancien projet sont des lignes de présentation
  dont l'identifiant commence par `missing:`. Ils ne désignent pas un fichier
  configuré ; leur enregistrement explicite crée de vrais liens.
- Une ancienne information automatique peut rester visible dans Informations
  et ses preuves ; elle ne devient pas une valeur courante de l'assistant.
  Une décision humaine historique reste accessible avec sa réserve.

## Parcours de relecture

Dans **Informations**, cocher **À réexaminer seulement**. Les motifs se lisent
sous **À réexaminer** : preuve remplacée/indisponible, valeurs concurrentes ou
information engageante retenue par défaut. Cette liste n'affirme pas que chaque
information est fausse.

**Confirmer après relecture** exige une preuve actuelle et une valeur unique
pour le sujet. L'utilisateur accepte explicitement la confirmation ; la valeur
et les sources ne changent pas. L'identité de l'opérateur configuré est inscrite
dans l'audit, même si le client déclare un autre nom. Une contradiction doit
d'abord être résolue par un choix métier explicite ; aucune valeur concurrente
n'est supprimée automatiquement.

La capture native conserve ses propres budgets de journal et de secours :
l'alerte de 10 Gio et la réserve des imports ne sont pas une garantie de place
pour douze heures de capture. Un seuil disque ne réserve pas de blocs au niveau
du système et ne protège pas contre les écritures d'autres applications.

## Extraction et reprise

PDF, Office et extraction de bibliothèque passent par un enfant Python sans
démarrage de base ou moteur IA. Windows applique un Job Object avec limite de
mémoire et fermeture des descendants ; le parent impose le délai. Les originaux
sont conservés si l'extraction échoue. L'IPC est bornée à 16 Mio de résultat.

OCR : rendu de page 60 s maximum, reconnaissance 90 s par appel, budget de
document de 15 minutes. **Annuler la reconnaissance** demande l'arrêt entre les
pages ; une page déjà engagée peut aller jusqu'à son délai. Les reçus des pages
terminées restent réutilisables. La publication canonique n'intervient qu'après
une extraction complète et une nouvelle vérification de la version source.

Pillow 13.0.0 est déclaré dans le profil de rendu PDF ; les anciens rendus et
leurs profils ne sont pas réécrits. L'index multimodal canonique observé avant
activation contient des entrées texte et **aucune entrée PDF** : aucune
reconstruction de PDF existant n'est nécessaire pour ce changement de profil.
Les entrées texte et l'index EG2 réseau sont préservés.

## Rappel local et outillage

Le repli SQL lit les artefacts par lots de 400 sources au lieu d'une requête
par source. Les égalités de score conservent l'ordre des sources antérieur.
Sur **1 000 sources fictives**, sept passages comparent exactement résultats,
classement et citations : 1 001 requêtes SELECT deviennent 4 ; médiane observée
345 ms avant, 65 ms après. Il s'agit d'une recette synthétique, pas d'un P95
contractuel sur le corpus réel. Aucun modèle ni index actif n'a été utilisé.
La preuve est `recall-benchmark-result.json` dans le dossier privé de correction.

Un avis supplémentaire OpenTelemetry a été trouvé lors du contrôle de livraison.
`opentelemetry-api` est verrouillé à **1.45.1**, avec empreintes, dans les profils
principal et de développement. Référence amont :
[limitation du parsing tracestate](https://github.com/open-telemetry/opentelemetry-python/security/advisories/GHSA-xcq7-p3pf-p88h).
Les installateurs `pip` des deux environnements optionnels étaient également
signalés vulnérables ; ils sont maintenant verrouillés et installés en **26.2.2**.
Le contrôle final des verrous principal, audio, multimodal et développement,
puis des paquets réellement installés dans les trois environnements, ne remonte
aucun avis connu. Cela décrit les registres consultés à cette date,
pas une garantie d'absence de toute vulnérabilité future ou inconnue.

## Conservation, droits et enregistrement

| Catégorie | Règle technique en place | Décision organisationnelle restante |
|---|---|---|
| Bases, originaux, validations | Conservation ; sauvegarde avant opération sensible | Durée liée aux contrats et obligations internes |
| Audio/transcription | Conservation et relecture ; aucune capture sans action | Information des participants et durée applicable |
| Secrets | API publique masquée ; DPAPI sous Windows ; journaux expurgés | Gestion des postes et renouvellement des accès |
| Journaux/captures de recette | Rotation applicative ; inventaire de volumes | Rétention et emplacement des preuves uniques |
| Sauvegardes | Empreintes, vérification automatique, restauration sur copie | Perte de travail et délai de reprise acceptables, copie externe |
| Accès partagé | Loopback, jeton, opérateur et projets | Comptes individuels et droits avant exposition réseau |

Les dossiers `storage/`, `.playwright-mcp/` et `v/` sont exclus de Git pour
éviter une publication accidentelle des originaux, audios, captures et bases de
recette. Aucun de leurs fichiers n’était suivi ; ils restent sur disque et les
données actives restent couvertes par la sauvegarde applicative.

Aucune durée de suppression n'est inventée. Le nouvel inventaire ne supprime,
ne déplace et ne désigne automatiquement aucun fichier comme jetable.
BitLocker, les ACL de tous les dossiers et la conformité juridique ne sont pas
certifiés par ces changements applicatifs. Les règles internes doivent être
validées par les responsables compétents.

## Validation et clôture

| Vérification | Résultat courant | Preuve privée |
|---|---|---|
| Frontend complet après mise à jour des dépendances | **1 004 tests, 96 fichiers réussis** | `frontend-full-final.log` |
| Dernier alignement visuel et parcours modifiés | **43 tests réussis** | `frontend-release-targeted.log`, `sources-ocr-final.log` |
| Sécurité, chat, contexte historique et annulation OCR | **48 tests réussis** | `logging-context-final.log` |
| Droits, ordre du contexte et citations de l'assistant | **36 tests réussis** | `recall-context-final.log` |
| PDF réel, recherche et sauvegarde portable | **55 tests réussis** | `targeted-fourth.log` |
| Backend global | **2 954 réussis, 1 ignoré, 54 sous-tests réussis ; 58 min 16 s** | `backend-full-final.log` |
| État final après OpenTelemetry et finitions | **184 tests ciblés réussis**, puis **1 test** après la garde de clé NULL | `backend-release-targeted.log`, `projection-empty-source-final.log` |
| Ruff incluant les scripts, TypeScript et compilation isolée | Réussis ; bundle JS environ 1,10 Mo non compressé | `ruff-release.log`, `typescript-release.log`, `build-release-final.log` |
| Qualité UX et extensions | 6 tests UX et 9 tests d'extensions réussis ; 61 avertissements heuristiques sur 121 fichiers à relire | `ux-tests.log`, `extensions-final.log`, `ux-check.log` |
| Vulnérabilités des verrous | Aucun avis connu sur les trois profils Python, le développement et le frontend | `locked-audit-complete-final.log`, `main-installed-audit-final.log`, `optional-installed-audit-final.log`, `pip-audit-dev-final.log`, `pnpm-audit-final.json` |
| Navigateur réel | Recette fictive 1440×900 et 390×844 ; clavier, confirmation annulée, mail HTML, images sur choix explicite, Swagger et interface héritée conformes | `browser-review.json`, captures citées |
| Restauration | Fictive réussie ; sauvegarde complète existante de **1 805 fichiers** restaurée en 61 s, bases intègres et `/health` conforme sur la copie | `restore-fictitious-result.json`, `restore-existing-backup-result.json`, `restored-health.json` |
| Nouvel environnement virtuel et superviseur | Le serveur fictif est fermé avec son superviseur ; aucun listener orphelin observé | `runtime-venv-probe-result.json` |
| Conservation avant activation | Aucun identifiant initial manquant ; nouvelles sources arrivées pendant le travail ; intégrité et clés étrangères conformes | `preservation-before-activation.json` |
| Sauvegarde avant activation | **1 811 fichiers vérifiés**, bases et empreintes conformes, Agent arrêté | `backup-before-activation/backup.json`, marqueur `storage/backup-status.json` |
| Activation canonique | **Agent actif sur 127.0.0.1:8001, zéro relance**, Brain/ERP `ok`, filtre de relecture disponible | `active-health-final.json` |
| Bundle servi | Assets identiques par SHA-256 ; HTML identique après normalisation des retours de ligne par la route existante | `frontend-activation.json`, `active-health-final.json` |
| Journaux réels | Secret fictif expurgé des sorties du lanceur et du fichier applicatif | `active-log-redaction.json` |
| Conservation après activation | **Aucun identifiant initial supprimé**, bases intègres et clés étrangères conformes | `preservation-final.json` |

Les preuves sont sous `logs/audit-remediation-20261022/`, exclu de Git. La
sauvegarde complète restaurée ci-dessus est celle du 22 octobre à 00 h 28 ; ses
compteurs décrivent cette copie datée, pas l'état actif du soir.

La collecte complète du nouvel environnement découvre tous les tests ; NumPy
et pytest-asyncio, auparavant fournis par l'environnement global, sont maintenant
déclarés dans le profil de développement. Une première suite globale a été
interrompue pour aligner le profil PDF sur le correctif Pillow ; elle ne vaut
pas validation globale.

Pendant la suite globale suivante, trois finitions ont été ajoutées : distinction
entre preuve déjà historique et changement pendant la réponse, masquage des
flux console, conservation des égalités de classement lors du rappel par lots.
Après la suite globale, OpenTelemetry 1.45.1 a été installé et **184 tests**
ont été rejoués avec ces versions finales. L’avertissement SQLAlchemy sur une
clé source NULL a ensuite été corrigé sans changer l’état produit ; le test de
triage qui le déclenchait a été rejoué avec succès. Il reste l’avertissement de
dépréciation TestClient/httpx. La suite globale n’a pas été répétée après ces
finitions ; ses résultats et ceux des contrôles finaux gardent leur portée.

La sauvegarde coordonnée fraîche est conservée dans
`logs/audit-remediation-20261022/backup-before-activation` (22 octobre, **19 h 53**,
heure de Paris). Elle a été vérifiée automatiquement avant activation. La
restauration complète de recette porte sur la sauvegarde datée plus ancienne,
comme indiqué ci-dessus. Aucun ancien asset, original, modèle ou historique
n’a été supprimé lors de l’activation.

Les sources finales et leur carte SHA-256 sont conservées dans
`release-sources.zip` et `release-source-hashes.json` dans le même dossier privé.
Cette copie identifie l’arbre local testé et activé sans créer de commit Git.

La livraison Git du 23 octobre reprend ces sources sans changement applicatif
depuis la qualification ; seuls les documents de suivi de livraison sont mis
à jour. Les fichiers de compilation intermédiaires et copies de récupération
restent conservés localement, hors du commit. L'historique Git identifie le
commit livré ; les bases, sauvegardes et preuves privées restent exclues.

Ces contrôles ne qualifient pas un microphone, une inférence IA réelle, une
restauration sur un autre compte Windows, un lecteur d'écran ni une conformité
WCAG ou juridique. Les réglages IA HTTP sont conservés. Les sources et leurs
empreintes finales permettront d'identifier exactement l'état livré localement.
