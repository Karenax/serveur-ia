# Contexte courant — Agent 0.4.0

Mis à jour le 23 octobre 2026 pour la livraison des corrections de sécurité.
Ce document est un index de l'état courant ; les qualifications datées gardent
leur portée et ne deviennent pas des observations en direct.

## Produit et architecture

Projet canonique : `C:/Agent`. Un dépôt, un serveur Agent sur **8001** servant
Brain `/v1`, ERP `/api/v1` et React `web/dist`. XPilot sur **8000** est externe ;
aucun service sur 8002. Projets, CDC, CDC & BE, Revues, Atelier et Import Sage
restent conservés. Les règles de `AGENTS.md` préservent données et décisions.

SQLite Brain et ERP sont canoniques et reliés explicitement ; leurs commits ne
forment pas une transaction distribuée. Dans Kiara, l’index reconstructible EG2
sert la recherche sémantique et les citations. LiteRT est obsolète depuis le
14 novembre 2026. Les sauvegardes et restaurations excluent son ancien index.

## Portée et limites acceptées

- Réunions : capture, transcription, notes, relecture, publication et exports.
  Le direct est provisoire et exige une relecture humaine ; aucune garantie de
  transcription industrielle sans erreur. Les recettes matérielles historiques
  ne sont pas rejouées par les tests unitaires.
- Sources/mails : originaux, versions, preuves, classement assisté et HTML MIME
  isolé. Les images distantes nécessitent un choix explicite.
- Connaissance : `default` signifie retenue par défaut, `human` confirmation
  humaine. Les informations engageantes et preuves historiques sont à réexaminer.
  Une preuve remplacée n'autorise pas une ancienne information automatique à
  se présenter comme valeur actuelle. Les décisions humaines sont conservées.
- IA : génération et indexation distinctes ; téléchargé, chargé et résultat
  utile sont des observations différentes. HTTP réseau **conservé sur décision
  explicite du 22 octobre**, le correctif HTTPS étant mis de côté.
- Sécurité : opérateur local configuré, portée projet, jeton Host/Origin,
  contrôle de volume et en-têtes. Ce ne sont pas des comptes individuels ni
  une autorisation d'ouvrir le service au réseau.
- Sauvegarde : copie coordonnée hors ligne, vérification d'empreintes et de
  bases, restauration sur répertoire neuf. DPAPI dépend du compte Windows.

## Corrections et livraison

Le [suivi des 18 constats](docs/60_SECURITY_REMEDIATION.md) fait autorité pour
les correctifs de cet audit : exports sans écrasement, GET sans mutation,
contexte de preuve, dépendances corrigées, environnements propres, extraction
bornée, sauvegarde vérifiée, rétention sans suppression automatique.

La livraison Git du **23 octobre 2026** regroupe les sources validées, les
tests et la documentation ; les preuves privées restent hors du dépôt. Le résultat
global est de 2 954 tests réussis, 1 ignoré et 54 sous-tests réussis ; 185 tests
ciblés couvrent les finitions. Le frontend compte 1 004 tests réussis. Agent est
actif sur 127.0.0.1:8001, avec Brain/ERP `ok`, après sauvegarde vérifiée de 1 811
fichiers. Ces contrôles ne qualifient pas un nouveau microphone ou modèle IA.
Les décisions d'entreprise sur rétention, droits du poste et enregistrement
restent à formaliser ; aucune durée de purge ni licence n'est inventée.

## Ordre de lecture

1. [README](README.md), produit et architecture.
2. [Exploitation](README_BACKEND.md), installation verrouillée et reprise.
3. [Corrections de sécurité](docs/60_SECURITY_REMEDIATION.md), état courant.
4. [Architecture](docs/01_GLOBAL_ARCHITECTURE.md),
   [gouvernance](docs/08_SECURITY_GOVERNANCE.md),
   [mémoire EG2](docs/20_EG2_ENGINE.md),
   [réunions](docs/56_MEETING_START_GUIDE.md).
5. `manifest.json`, entrée `current_state` ; les clés historiques restent
   compatibles avec les outils et rapports de qualification.

Le [contexte antérieur complet](docs/history/PROJECT_CONTEXT_BEFORE_SECURITY_20261022.md)
et les anciens README/manifeste sont archivés sous `docs/history` sans suppression
de leur contenu. Les détails d'exécution et empreintes de cette étape sont dans
`logs/audit-remediation-20261022/`.
