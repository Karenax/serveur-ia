# Contexte de reprise — serveur Fred

Mise à jour : 14 octobre 2026.

État réseau et moteurs recoupé le 13 octobre : [vérification du contexte](maintenance/2026-10-13-contexte/verification.json). La [publication du 14 octobre](maintenance/2026-10-14-opencode/production-corrections.json) confirme Windows/serveur 3.5.29, Qwen toujours chargé avec les mêmes processus, Hermes disponible, données, clés et programmation des sauvegardes conservées. Les connexions réelles WireGuard sur `.41` et HTTPS passent avec cinq modèles accessibles.

## Travaux livrés

L’utilisateur a demandé une revue approfondie du projet, puis toutes les corrections et améliorations identifiées. L’audit de référence examine le commit `ffe85204729db298ac83848e727e2b9aa10f5548`. Les corrections sont développées sur `codex/audit-corrections-20261012` : export des conversations de projet, limites de l’historique Hermes et export de récupération, stockage/quota/rétention Hermes, identité des tours MCP/inférence, anciennes images, quota différentiel des mémoires et syntaxe PowerShell.

L’audit a été livré en Windows/serveur 3.5.28 et Android 1.0.11/code 12. Le rapport final de correction, les tests et la preuve de mise en service se trouvent dans [audits/2026-10-12](audits/2026-10-12/). Le correctif Windows/serveur **3.5.29** du 14 octobre est désormais publié ; Android reste en **1.0.11/code 12**.

Le 14 octobre, l’ajout OpenCode 2 a été corrigé après le signalement « fournisseur présent mais aucun modèle ». OpenCode 2 masque par défaut les modèles personnalisés sans date de publication ; Fred active maintenant uniquement le modèle ajouté dans les préférences du sélecteur Desktop. Si OpenCode est ouvert, Fred demande de le fermer et de refaire l’ajout pour ne pas écraser son cache. La configuration JSONC prioritaire est également choisie lorsque JSON et JSONC coexistent. Sur le client : mettre Fred à jour en **3.5.29**, fermer OpenCode, refaire **Ajouter à OpenCode 2**, puis rouvrir OpenCode. Le nouvel EXE, les préférences, la règle du sélecteur et une requête OpenCode ont été vérifiés avec **2.0.22 et 2.0.29**, en environnement temporaire ; 28 tests Python et cinq suites d’interface passent. Voir [la validation et les limites](maintenance/2026-10-14-opencode/README.md). Le poste client distant reste à actualiser par son utilisateur.

Le 13 octobre, la connexion WireGuard sur le réseau local a été réparée : les anciens profils indiquaient `192.168.1.40`, tandis que l’adresse du serveur est `192.168.1.41`, désormais configurée en IP fixe dans Windows. La préparation des EXE et le téléchargement des profils Android actualisent désormais les routes locales, sans changer les clés. L’EXE personnel disponible dans la console a été régénéré. Pour un client déjà installé, utiliser `192.168.1.41:51820` dans les réglages WireGuard ou récupérer l’EXE corrigé. WireGuard et HTTPS ont été vérifiés avec le client réel ; 40 tests passent. Preuves : [audits/2026-10-13-wireguard](audits/2026-10-13-wireguard/).

La consigne finale du 13 octobre conserve **192.168.1.41** : l’utilisateur adapte la redirection de port de la box à `.41`. Ne pas remettre les profils sur `.40`, occupée par un appareil Espressif. La tentative précédente de retour à `.40` a été rejetée par la détection de conflit de Windows puis annulée. Le script de configuration fixe a été relancé en administrateur et a réussi à **12 h 51 (Europe/Paris)** : `.41`, masque `/24`, passerelle et DNS `192.168.1.1`, DHCP IPv4 désactivé et configuration persistante. Preuves : [maintenance/2026-10-13-ip-fixe/verification.json](maintenance/2026-10-13-ip-fixe/verification.json). Les profils, WireGuard, HTTPS Cloudflare, les processus Qwen chargés et les clés ont été vérifiés après application.

## Fonctionnement actuel

- Réseau du PC : IP fixe persistante `192.168.1.41/24`, DHCP IPv4 désactivé, passerelle et DNS `192.168.1.1`. Les profils WireGuard utilisent `192.168.1.41:51820` sur le LAN. L’utilisateur adapte la redirection UDP 51820 de la box à `.41` ; cette règle n’a pas été vérifiée depuis un réseau extérieur.
- Chat Strata direct avec le modèle local : [http://127.0.0.1:8080/](http://127.0.0.1:8080/), également accessible par **Ouvrir le chat** dans la console Fred. Console : [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Ces deux interfaces écoutent uniquement sur le PC serveur, en loopback.
- Passerelle Fred `127.0.0.1:8766`, accessible aux clients via WireGuard UDP 51820 ou [HTTPS Cloudflare](https://ia.karenax.net). Les connexions WireGuard sur le LAN et HTTPS ont été validées après passage en IP fixe.
- Qwen/Strata sur les deux Tesla P100 ; modèle API `qwen3.8-flash-next-iq4-xs`, chargé, contexte 262 144 tokens. La configuration active annonce `images=false`. Le modèle chargé doit être préservé pendant une mise à jour de la console.
- Flash-Next IQ4_XS utilise Strata officiel **0.1.43.1** dans `dependances/strata-0.1.43.1`, dont l’empreinte du moteur actif correspond à la preuve de déploiement. Profil : préfill 2048, 15 workers, MTP 3 / seuil 0,5, split 24, cache historique 8/160000, `STRATA_SPLIT_MTP_BATCH=1`, PLE direct, cache de conversation 0 Mio. Le délai de chargement du serveur est 3600 s pour la lecture à froid des experts. Les réglages courants, par défaut et derniers valides sont identiques. Chargement automatique et reprise automatique sont activés. Voir [la mise en service](maintenance/2026-10-13-strata-0.1.43.1/README.md) et `production.json` ; sauvegarde précédente dans `avant/`, ancien moteur `strata-build-p100` conservé. La prélecture expérimentale n’est pas intégrée au démarrage automatique.
- Conversations et tâches rédactionnelles confiées à Hermes ; Qwen local et modèles du profil natif actif autorisés par la console. Les trois actions du correcteur restent directes sur Qwen.
- Hermes possède sa racine `lanceur/hermes-fred`, ses profils par accès et ses sessions par conversation. API native `127.0.0.1:8643`, adaptateur privé `127.0.0.1:8768`. Outils documentaires, mémoire, calcul et outils web natifs limités au compte/projet/tour autorisé ; outils hôte libres désactivés.
- SQLite constitue l’autorité. Les dossiers `lanceur/donnees-clients` sont des copies privées actualisées par propriétaire et vérifiées périodiquement. EG2 fonctionne sur CPU avec périmètres de mémoire séparés.
- Windows : dictée Whisper Small et conversation vocale complète. Android : dictée manuelle Small, téléphone/tablette, téléchargement automatique des mises à jour et confirmation native d’installation.
- Sauvegardes chiffrées quotidiennes à 03 h, conservation 7/4/6, destination serveur. Aucune destination NAS configurée. Comptes, clés, historiques, profils et programmation doivent être préservés.

## Décisions conservées et travail ultérieur

Les lots 0 à 4, 6 et 8 sont livrés ; le lot 7 couvre dictée Windows/Android et conversation Windows. La refonte complète du tableau de bord (lot 5), conversation Android, extensions des lots 9/10, OCR et réveil Android arrêté restent à développer sur demande. L’audit ne constitue pas une autorisation d’activer des outils système libres ou de nouveaux services externes.

Le partage des fournisseurs existants suit `hermes-models.json`. Les secrets restent hors Git et les connexions personnelles Hermes restent dans leur magasin natif. Ne pas régénérer les clés de signature Windows/Android ni celles de WireGuard pendant une reconstruction.

## Références

- [Audit initial](audits/2026-10-12/RAPPORT-AUDIT.md) et [validation des corrections](audits/2026-10-12/VALIDATION-CORRECTIONS.md).
- [Réparation WireGuard](audits/2026-10-13-wireguard/VALIDATION.md), [IP fixe](maintenance/2026-10-13-ip-fixe/README.md) et [vérification actuelle](maintenance/2026-10-13-contexte/verification.json).
- [Strata 0.1.43.1 en production](maintenance/2026-10-13-strata-0.1.43.1/README.md).
- [Correctif OpenCode 2 et livraison Windows 3.5.29](maintenance/2026-10-14-opencode/README.md).
- [Reconstruction et tests](RECONSTRUIRE-FRED.md), [références des moteurs](dependances/README.md), [index des archives](ARCHIVES-ET-PREUVES.md).
- [Plan global](PLAN-GLOBAL-SERVEUR-FRED.md), [guide Hermes](lanceur/HERMES-FRED.md), [sauvegardes/appareils](lanceur/SAUVEGARDES-APPAREILS.md), [EG2](lanceur/MEMOIRE-EG2.md), [Android](client-android/README.md).
- [Historique des décisions et livraisons](HISTORIQUE-PROJET-AVANT-AUDIT-20261012.md). Les longues étapes historiques ont été conservées dans ce fichier.
