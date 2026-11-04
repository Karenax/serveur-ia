# Publication Windows 3.5.58 et audit documentaire — 4 novembre 2026

Windows **3.5.58 est publié**. Le client 3.5.57 du 3 novembre à 09 h 53
ne contenait pas les changements de `client.py`, `ui.css`, `ui.js` et
`workspace.html` enregistrés ensuite vers 17 h. Cette livraison reconstruit le
client avec les sources actuelles, notamment le retrait des tâches et des
synthèses programmées. Les rappels et le bilan consultable restent disponibles.

Les utilisateurs peuvent ouvrir **Réglages → Mises à jour**, vérifier les mises
à jour puis installer le client. La publication rend la mise à jour disponible ;
elle ne ferme pas les applications déjà ouvertes sur les postes distants.
Les quatre EXE personnels actifs ont été reconditionnés et testés avec leurs
profils, en préservant les accès et les clés. L’ancien EXE inactif n’est pas
reconditionné. Distribuer uniquement les EXE personnels de la console.

## Vérifications de livraison

- 104 tests Python du client et 18 suites UI réussis.
- Contrôle final des sources : 519 fichiers Python, 94 scripts JavaScript extraits ou
  autonomes, 98 scripts PowerShell vérifiés par chacun des deux interpréteurs.
- Contrôle UX réussi avec cinq avertissements de textes longs dans la console,
  examinés : explications des accès personnels, de WireGuard, des mises à jour et
  de l’isolation de la mémoire. Leurs informations restent utiles ; aucun texte
  n’a été supprimé sur la seule base de sa longueur.
- Auto-test natif du binaire de base et des quatre EXE personnels.
- Comparaison des onze ressources UI embarquées aux sources, du bytecode réel
  de `client.py`, de la version gelée et du pont WireGuard.
- Signature Ed25519 et téléchargement authentifié complet vérifiés depuis la
  passerelle de production : **115 434 004 octets**, SHA-256
  `d1c75a9b9f28af1149d115c4746f54d3dfa75f05b1c2756325abbfbcb3711613`.
- Sauvegarde chiffrée vérifiée avant publication et deuxième copie sur le NAS.
  Données utilisateur, clés, accès, réglages, programmation des sauvegardes et
  processus Qwen chargés conservés. Redémarrage de la console par la procédure
  existante avec préservation du modèle.

Preuves : `production.json`, `publication.json`, `frozen-validation.json`,
`sauvegarde-avant.json`, `avant-livraison.json`, les quatre
`personal-self-test-*.txt` et les journaux de ce dossier. Le manifeste est dans
`toolchain/releases-staging/windows-3.5.58/build-manifest.json` à la racine du dépôt.
La distribution précédente est conservée dans `previous/` et le mécanisme de
retour des clients personnels reste disponible.

## Audit documentaire

L’audit porte sur les **24 documents** courants et plans listés dans
`documentation-check.json`. Il confronte les guides aux identités partagées,
manifestes Windows et Android, sources du client, profil GPU de production et
configuration des sauvegardes lue dans la console. Il conserve les dates,
versions et mesures des rapports historiques.

Écarts corrigés :

- Versions courantes divergentes : 3.5.52, 3.5.53 ou 3.5.55 selon le guide,
  Android encore annoncé en 1.0.23/code 24. Les références de publication sont
  maintenant 3.5.58 et 1.0.25/code 26 ; les versions minimales de fonctions
  historiques restent inchangées.
- Moteur de production encore annoncé en Strata 0.1.45.3 : références alignées
  sur 0.1.56 CUDA 12.9, RTX 4080, deux P100 et DFlash2.
- Fonctions retirées encore proposées : tâches et comptes rendus programmés.
  Guides corrigés et plans annotés pour distinguer leur périmètre historique.
- Guide vocal : panneau des échanges écrits actuel, voix Tiphaine et
  téléchargement Windows d’environ 680 Mo. Le guide client inclut aussi
  l’intégration Codex ajoutée en 3.5.57.
- Deuxième copie de sauvegarde annoncée désactivée : configuration NAS actuelle
  documentée, sans modifier la programmation.
- Ancien guide racine et ancien profil serveur identifiés comme historiques ;
  instructions de connexion et de construction serveur actualisées.

Le script `audit_documentation.py` vérifie les cibles des liens locaux et la
présence de la version courante dans les références principales. Ses résultats
sont dans `documentation-check.json` ; il peut être rejoué en lecture des sources
et réécrit uniquement ce rapport.

## Limites conservées

L’APK **Android 1.0.25/code 26 du 26 octobre** n’est pas reconstruit ici. Plusieurs
sources d’interface ont changé depuis son manifeste : leurs modifications ne
sont pas encore distribuées dans cet APK. Ses anciennes actions de tâches ou
synthèses peuvent rester visibles alors que le serveur les a retirées. Cette
limite est signalée dans les guides ; les rappels restent pris en charge.

L’archive Linux et le pack Max publié restent inchangés. La reconstruction du
worker Low embarqué dans Windows ne publie pas un nouveau pack Max.
Les tests navigateur utilisent des données fictives ; cette livraison n’effectue
pas une nouvelle qualification physique micro/caméra, Android ou Linux.
L’audit ne vérifie pas les URL externes ni les ancres Markdown, et ne réécrit pas
les preuves historiques.

`publish.py prepare` et `publish.py publish` ont déjà été exécutés ; ne pas les
relancer sur cette livraison. `publish.py verify` vérifie la version servie et
les invariants enregistrés, tant que les données n’ont pas changé depuis
l’instantané initial. `publish.py check` vérifie le contenu de l’EXE de staging.
