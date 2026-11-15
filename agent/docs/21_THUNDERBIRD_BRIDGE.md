# Liaison locale Thunderbird ↔ Agent

## Architecture

Thunderbird 153+ (157.0.1 observé sur le poste) charge la MailExtension
`agent-bridge@agent.local`. Elle échange exclusivement avec le serveur Agent
existant sur `http://127.0.0.1:8001/v1/thunderbird`. Aucun serveur supplémentaire,
aucun identifiant IMAP/SMTP recopié, aucun service de publication nécessaire.
Les API officielles `accounts`, `folders`, `messages` et `compose` sont utilisées.

Le pont est dans `app/routers/thunderbird.py`, le client dans
`extensions/thunderbird-agent/`, et le panneau React dans
`web/src/components/ThunderbirdPanel.tsx` (bouton Thunderbird de l’app Mails).

## Installation Windows

Dans Kiara 4.0.1, ouvrez **Agent → Mails → Options → Extension Thunderbird**
et cliquez sur **Installer l’extension**. Rouvrez Thunderbird pour que le
module soit chargé. Kiara prépare le paquet appairé pour le compte Windows
courant. Après l’installation initiale, chaque nouvelle version intégrée à
Kiara est préparée au démarrage de Kiara et chargée à la prochaine ouverture
de Thunderbird.

Dans la console serveur, ouvrez **Configurer Agent → Poste Thunderbird** et
sélectionnez l’accès Kiara utilisé sur le poste de travail. Cet accès doit
pouvoir modifier les données Agent. La liaison a sa propre autorisation et
les droits sur les projets restent ceux de l’accès sélectionné. Une
configuration automatisée peut définir `KIARA_AGENT_THUNDERBIRD_DEVICE` au
démarrage. Pour le parcours manuel, préparez le XPI sur le poste Windows
avec le même EXE personnalisé que celui utilisé pour importer le profil Tauri.

```powershell
python .\agent\scripts\install_thunderbird.py --kiara-profile-exe 'D:\Accès Kiara.exe'
```

Installer le XPI depuis le gestionnaire de modules Thunderbird. Garder Kiara
ouvert pendant la synchronisation. L’extension contacte le relais local sur le
port 17841 avec sa propre clé. Le XPI contient cette clé et reste sur le poste.

Pour une installation Agent autonome, utiliser la commande suivante.

```powershell
python scripts/install_thunderbird.py --install
```

Le script sauvegarde la base avant la migration additive, renseigne les
empreintes des mails existants, génère une clé d’appairage protégée par DPAPI
en base, puis crée `storage/thunderbird/agent-thunderbird.xpi`. Ce paquet local
contient la clé de ce poste et ne doit pas être publié ni commité. Sur un autre
hôte, définir `PB_THUNDERBIRD_TOKEN` avant de créer le paquet.

L’installation utilise la politique officielle `ExtensionSettings`, avec
`normal_installed` et une URL `file:///` vers le XPI. Les autres politiques sont
conservées, et une copie du fichier précédent est créée avant modification.
Thunderbird doit être fermé normalement puis rouvert. On peut aussi installer
le XPI depuis le gestionnaire de modules. Les mises à jour du programme peuvent
remplacer le répertoire `distribution` ; si l’installation initiale ne s’est pas
faite, relancer le script après la mise à jour.

L’extension devient persistante dans le profil. Thunderbird et Agent doivent
être ouverts pour l’échange. Vérifier `GET /v1/thunderbird/status` : version,
dernier contact et `connected`. Pour une installation existante, charger le XPI
0.2.0 depuis le gestionnaire de modules ; remplacer le paquet sur disque ne
garantit pas la mise à jour de la version déjà chargée.

## Source des mails et sélection centrale — 5 octobre 2026

**Réglages → Mails** propose Thunderbird ou dossier EML. Le mode Thunderbird
présente les comptes et les dossiers accessibles, avec recherche et cases à
cocher. Filtrer un compte ou rechercher un nom ne désélectionne pas les dossiers
masqués. La réception sert de sélection initiale ; Réception et Envoyés peuvent
être combinés. Indésirables, corbeille et brouillons sont exclus du catalogue.

`mail.source`, `mail.thunderbird_folder_ids`, `mail.auto_scan` et
`mail.scan_interval_minutes` sont conservés dans les réglages Brain existants.
La liaison 0.2.0 reçoit `mail_config` à chaque heartbeat (environ 30 secondes),
adopte les dossiers et adapte son alarme à l’intervalle choisi (1–1440 minutes).
En mode EML, elle conserve sa présence et ses commandes de brouillons, mais
cesse les imports. Le scanner serveur ne parcourt les EML qu’en mode dossier.
Les fichiers exportés ne sont donc pas nécessaires en mode Thunderbird.

**Synchroniser maintenant** enregistre la sélection puis crée une commande
durable, même si l’automatisme est désactivé. Thunderbird fermé : la demande
attend sa prochaine ouverture ; les mails déjà importés restent consultables.
Le bouton de synchronisation de Mails suit également cette source. Le panneau
Thunderbird et les options de l’extension conservent la sélection centrale.

Un changement de source ou de sélection ne supprime aucune donnée, ni le
chemin EML précédent. Une liste vide suspend les transferts ; `null` conserve
la sélection initiale de l’extension. Le serveur refuse les imports d’une autre
source, d’un dossier désélectionné ou automatiques lorsque l’option est coupée.
Une commande manuelle en cours autorise l’import malgré cette dernière option.
Ces protections fonctionnent aussi avec la liaison 0.1.0 ; l’application de
l’intervalle et le compteur précis nécessitent 0.2.0.

## Transfert et dédoublonnage

Les en-têtes des messages éligibles non encore transférés sont recensés par
pages dans les dossiers sélectionnés. La progression affiche **traités / total**
pour ce passage. Les messages complets sont récupérés par `messages.getRaw`,
puis envoyés au serveur local, au maximum 100 par passage ; le reliquat est
signalé et repris au passage suivant. Le compteur est recalculé à chaque passage.
Avec l’automatisme désactivé, demander un nouveau passage pour le reliquat.
Un mail en erreur n’est pas marqué transmis ; une coupure arrête le passage.

L’import ne lance pas le LLM dans le pont et ne valide aucun classement.
Le moteur de tri Agent prend ensuite le relais avec validation humaine.
L’empreinte MIME évite de réimporter les anciens exports sous une autre
représentation. La migration renseigne aussi les empreintes des mails écartés ;
elles subsistent après purge et empêchent leur réapparition automatique.

## Brouillons et réponses

Dans Mails → Thunderbird, choisir l’expéditeur, saisir destinataires, objet,
texte et pièces jointes (20 Mio cumulés), puis créer le brouillon ou ouvrir la
fenêtre Thunderbird. « Préparer une réponse » depuis le lecteur utilise le
Message-ID du mail source ; l’extension retrouve le message dans le compte de
l’identité choisie et utilise `compose.beginReply`, préservant le fil.
Si le message n’est pas retrouvé, la commande échoue explicitement.

Les nouveaux brouillons utilisent `messages.saveMessage` (Thunderbird 153+).
Une réponse sauvegardée utilise `compose.saveMessage`. L’envoi se fait ensuite
dans Thunderbird ; la version 0.1 n’expose aucune commande d’envoi et ne demande
ni `messages.send` ni `compose.send`.

Les commandes sont stockées dans `ThunderbirdJob`, avec états queued/running/
done/failed/uncertain. Une commande est réclamée une seule fois. Un journal
local permet de renvoyer un résultat après une coupure, sans refaire le brouillon.
Une interruption avant confirmation laisse un résultat incertain plutôt que
de créer automatiquement un doublon. Le contenu de la commande est effacé
après résultat ; le brouillon vit dans Thunderbird.

## API et authentification

API interface Agent (session locale habituelle pour les POST) :
- `GET /v1/thunderbird/status` : présence, catalogue et dernières commandes ;
- `POST /v1/thunderbird/sync` : `{folder_ids: [...]}` ;
- `POST /v1/thunderbird/drafts` : to/cc/subject/body/identity_id,
  reply_source_id optionnel, open_window, pièces jointes base64.

API extension (clé persistante `X-Agent-Thunderbird-Token`) :
- `POST /v1/thunderbird/bridge/heartbeat` : retourne `mail_config` ;
- `POST /v1/thunderbird/bridge/configure` : sélection centrale et commande manuelle ;
- `POST /v1/thunderbird/bridge/import` : multipart File/account_id/folder_id ;
- `POST /v1/thunderbird/bridge/jobs/claim` ;
- `POST /v1/thunderbird/bridge/jobs/{id}/result`.

Les origines moz-extension sont autorisées uniquement sur ces routes de pont,
avec prévol CORS dédié et clé obligatoire. Elles n’obtiennent aucun accès
aux autres commandes Agent. La clé n’est pas exposée dans `/v1/settings`.
Les données des mails reçus ne sont jamais interprétées comme commandes.

## Vérifications

```powershell
python -m pytest tests/test_thunderbird.py tests/test_mail_sources.py -q
node --test extensions/thunderbird-agent/core.test.cjs extensions/thunderbird-agent/background.test.cjs
python -m pytest tests/ -q
ruff check app backend/app tests scripts/install_thunderbird.py
```

Tests : portée de l’appairage, prévol, doublons malgré les en-têtes Thunderbird,
exclusion des mails écartés, import sans appel IA ni auto-validation, commandes
durables sans double réclamation, installation préservant les autres politiques.
La vérification sur le poste doit compléter ces tests par un heartbeat réel et
un brouillon explicitement créé dans Thunderbird.

### Qualification sur le poste — 2 octobre 2026

- Extension 0.1.0 présente dans le profil : active, ni désactivée par l’utilisateur
  ni par l’application ; Thunderbird mis à jour en 157.0.1 au premier redémarrage.
- Heartbeat réel reçu : 2 comptes et 874 dossiers accessibles.
- Premier passage sur INBOX : 3 imports, 9 doublons, 0 erreur.
- Brouillon de vérification demandé depuis Agent avec une pièce jointe texte ;
  commande terminée et présence du sujet et de `verification-agent.txt` vérifiée
  dans le stockage Drafts de Thunderbird. Aucun envoi déclenché. Sur ce poste,
  `messages.saveMessage` a retourné un tableau de descripteurs vide malgré la
  sauvegarde effective ; le contenu du dossier a servi de preuve complémentaire.
- 91 tests Python passés, 1 ignoré ; 13 tests React et 4 tests client Node passés ;
  Ruff propre et compilation TypeScript/Vite réussie.

Références : [API messages](https://webextension-api.thunderbird.net/en/latest/messages.html),
[API compose](https://webextension-api.thunderbird.net/en/latest/compose.html),
[politiques d’installation](https://thunderbird.github.io/policy-templates/templates/release/#extensionsettings).

### Qualification du sélecteur — 5 octobre 2026

- 160 tests Python passés, 1 ignoré ; 87 tests React et 7 tests Node passés ;
  Ruff et compilation TypeScript/Vite réussis.
- Parcours visuel vérifié avec des comptes fictifs : recherche sans perte de
  sélection, retour EML avec chemin conservé, enregistrement de l’intervalle et
  persistance après rechargement.
- API et interface activées sur 8001 avec les dossiers Thunderbird précédents ;
  automatisme précédent conservé. Deux sauvegardes SQLite intègres et 2 760
  identifiants existants conservés ; aucun mail supprimé.
- Paquet 0.2.0 appairé préparé localement. La version chargée au dernier statut
  reste 0.1.0 ; l’installation native de la mise à jour attend confirmation.
