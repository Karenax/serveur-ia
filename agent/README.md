# Agent — connaissance projet et ERP local

Agent aide le chargé d'affaires à exploiter les documents, mails et réunions de
ses projets, puis à piloter CDC, bureau d'études, planning, atelier et livrables.
Les informations gardent leurs preuves et les décisions humaines restent distinctes
des propositions et informations retenues par défaut.

## Tri automatique des mails — 4 novembre 2026

À chaque passage automatique des mails, Agent reprend aussi les suggestions
déjà analysées qui atteignent le seuil de classement (75 % par défaut), avant
l'import et toute nouvelle analyse IA. Les décisions humaines et les cas
ambigus restent protégés, sur le serveur unique Agent 8001.

## Assistant projet — 2 novembre 2026

« Conversation éphémère » est cochée par défaut : les échanges restent en mémoire
dans l'interface, sans lecture ni enregistrement de l'historique local. Décocher
l'option démarre une nouvelle discussion enregistrée ; les anciens historiques
restent disponibles. Les citations de sources ouvrent un lecteur dans Agent,
avec la présentation HTML originale des mails, plutôt que les données JSON.
Voir [le parcours et sa recette](docs/24_UI_UX_REDESIGN.md).

Depuis le 4 novembre, les deux cases de l'assistant sont regroupées sur une
même ligne au-dessus du choix du projet, sans paragraphe explicatif.

## Pièces jointes des mails — 4 novembre 2026

Les pièces jointes des mails classés sont désormais extraites avant leur
indexation EG2 dans le projet du mail : PDF, DOCX, XLSX/XLSM, PPTX, texte,
calendriers et documents lisibles des ZIP. Les PDF scannés et images passent
par l’OCR Windows disponible sur le PC. Nom, empreinte, page, feuille et
mail d’origine restent attachés aux preuves. Les originaux et décisions de
classement sont conservés ; les fichiers illisibles ou non pris en charge
gardent un état explicite. Voir [le pipeline](docs/04_INGESTION_PIPELINES.md).

## Accès IA Kiara — 4 novembre 2026

Le LLM peut utiliser le relais OpenAI local Kiara (`http://127.0.0.1:17841`,
modèle `fred-qwen`). EG2 prend en charge la même clé protégée Windows lorsque
son serveur est exactement celui du LLM ; elle n'est pas envoyée à un autre
serveur. Le modèle Kiara est `google/embeddinggemma-2`, en 768 dimensions et
lots de huit textes maximum. La reprise des pièces jointes utilise des lots
de huit après un test synthétique de huit passages en 5,33 secondes ; revenir
à deux si des passages dépassent la coupure du relais observée à 30 secondes.
Les appels EG2 passent un par
un dans la file IA commune, avec jusqu'à dix minutes par lot, attente comprise,
et reprise temporisée sur 429/503. Garder Accès serveur Kiara ouvert. Le passage à Kiara
réutilise les 20 322 vecteurs existants après contrôle de compatibilité sur
263 passages ; l'ancien index est conservé. Une reconstruction reste nécessaire
si le modèle produit un espace vectoriel différent.
Voir [le canal d'embeddings](docs/36_EMBEDDING_CHANNEL.md).

## Suivi du système et réglages — 4 novembre 2026

Le popup de travail en cours apparaît après deux secondes sur les opérations
longues suivies. Les erreurs restent affichées dans les écrans concernés.

Le popup **État du système** regroupe les connexions et le suivi des mails
(synchronisation, analyse, indexation, dernières activités et accès aux
traitements). Le bloc redondant de la barre latérale est retiré ; les erreurs
des mails restent signalées dans le bouton du popup.

Les lectures d'état sont espacées : une minute pour les services, 30 secondes
pour les mails, sans relance rapprochée au retour dans la fenêtre. Les sondes
réelles des services sont mises en cache cinq minutes. Les délais courts passent
à 20 secondes ; une panne de lecture doit se répéter trois fois avant de
remplacer un état connu. Les tests IA manuels restent prioritaires.
Le modèle hors ligne attend au moins deux minutes d'indisponibilité et une
validation dans un popup : **Passer hors ligne** ou **Attendre la connexion**.
Attendre ne charge aucun modèle et ne répète pas le popup pour la même panne ;
le choix reste disponible dans **État du système**. Le retour confirmé du
serveur annule l'autorisation et réarme le choix pour une nouvelle panne.

La navigation principale conserve **Accueil, Projets, Mails et Réunions**.
**Réglages**, en bas de la barre latérale, regroupe aussi **Sources,
Informations, Suivi des analyses et Connexions & imports**, sous forme d'onglets
au même niveau que Général, Mails, Clients et équipe et Apparence.

## État courant — livraison du 23 octobre 2026

Les corrections de sécurité sont suivies dans
[le bilan des 18 constats](docs/60_SECURITY_REMEDIATION.md). La livraison Git du
23 octobre regroupe les sources validées et la documentation. Les correctifs sont activés sur **8001**, avec
Brain et ERP conformes au contrôle de santé ; le bilan distingue la suite
globale des tests ciblés effectués après les finitions.

Le passage des moteurs IA en HTTPS est **écarté à la demande de l'utilisateur**.
Leurs connexions HTTP sont conservées, avec cette limite de confidentialité.
La transcription directe reste provisoire et exige une relecture humaine ; la
qualification historique n'est pas une garantie d'absence d'erreur.

## Une application, un serveur

- Agent écoute sur **127.0.0.1:8001**. FastAPI sert l'interface React construite
  dans `web/dist`, les routes Brain `/v1` et ERP `/api/v1`.
- Brain conserve sources, propositions, informations retenues et provenances
  dans `project_brain.db`. L'ERP conserve ses données dans
  `MINIPILOT_HOME/minipilot.db`, par défaut sous le profil Windows.
- Les liens entre projets sont explicites. La recherche sémantique utilise
  l’index EG2, un dérivé reconstruisible des données SQLite. Le moteur local
  LiteRT est obsolète.
- XPilot sur **8000** reste externe. Il n'y a pas de service sur 8002.
- Projets, CDC, CDC & BE, Revues, Atelier et Import Sage restent dans ce dépôt.

## Fonctions métier

| Rubrique | Usage |
|---|---|
| Projets et vue d'ensemble | Identité projet, échéances, actions et contexte explicite |
| CDC & BE | Documents client, exigences, preuves, revue et transfert versionné |
| Planning et Atelier | Jalons, tâches, charge, achats, pointage et nomenclature |
| Documents | Livrables, versions, notes, modèles et publications |
| Mails et Sources | Import choisi, classement, HTML MIME sûr, originaux et versions |
| Réunions | Capture, transcription, notes, relecture, comptes rendus et exports |
| Informations et assistant | Recherche avec droits, preuves et réserves de contexte |
| Maintenance | Suivi des traitements, sauvegardes, vérification et reprise |

Dans **Informations**, le filtre **À réexaminer seulement** signale les preuves
historiques et les valeurs à confirmer. Il ne déclasse aucune donnée.
**Confirmer après relecture** n'est proposé que pour une preuve actuelle unique.
Les comptes rendus se téléchargent sans écraser de fichier sur le serveur.

## Démarrer et vérifier

Après installation du profil verrouillé dans `.venv`, utiliser `start-agent.cmd`
ou `start-agent-task.cmd`. Le lanceur privilégie l'environnement propre à Agent,
reste sur loopback et n'hérite pas du contournement de test `AGENT_TESTING`.

```powershell
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m ruff check app backend/app tests scripts
npm --prefix web test -- --maxWorkers=4
npm --prefix web run ux:check
```

Installer les dépendances JavaScript avec **pnpm 11.18.0** et
`pnpm --dir web install --frozen-lockfile`. Le `node_modules` d'Agent est
indépendant du dossier historique MiniPilot.

La procédure complète se trouve dans [README_BACKEND](README_BACKEND.md).
La sauvegarde globale se fait hors ligne ; les restaurations utilisent un
répertoire neuf. Ne jamais supprimer une donnée, une preuve ou un module pour
simplifier l'interface ou gagner de la place sans décision explicite.

## Documents faisant autorité

- [Contexte courant](PROJECT_CONTEXT.md) : portée et frontières des garanties.
- [Architecture](docs/01_GLOBAL_ARCHITECTURE.md) et
  [modèle de domaine](docs/02_DOMAIN_MODEL.md).
- [Sécurité et gouvernance](docs/08_SECURITY_GOVERNANCE.md) ;
  [correctifs du 22 octobre](docs/60_SECURITY_REMEDIATION.md).
- [Moteur CDC](docs/17_CDC_ENGINE.md), [mails](docs/18_MAIL_TRIAGE.md),
  [mémoire EG2](docs/20_EG2_ENGINE.md), [réunions](docs/56_MEETING_START_GUIDE.md).
- [Qualité UX](docs/57_UX_QUALITY_SYSTEM.md),
  [audit UX](docs/58_UX_AUDIT_20261022.md),
  [corrections UX](docs/59_UX_CORRECTIONS_20261022.md).
- `manifest.json` conserve les contrats et preuves historiques ; son entrée
  `current_state` pointe vers le bilan courant.

Les anciens README détaillés et leur historique de recettes sont conservés
**intégralement**, avec empreintes dans les preuves de livraison :
[README antérieur](docs/history/README_BEFORE_SECURITY_20261022.md),
[guide backend antérieur](docs/history/README_BACKEND_BEFORE_SECURITY_20261022.md),
[contexte antérieur](docs/history/PROJECT_CONTEXT_BEFORE_SECURITY_20261022.md),
[manifeste antérieur](docs/history/manifest_BEFORE_SECURITY_20261022.json).
