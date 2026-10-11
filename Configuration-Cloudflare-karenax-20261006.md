# Configuration Cloudflare — 6 octobre 2026

## État actuel

- Domaine actif chez Cloudflare. La résolution NS via 1.1.1.1 confirme louis.ns.cloudflare.com et zoe.ns.cloudflare.com.
- karenax.net et www.karenax.net pointent vers l’hébergement OVH 213.186.33.87, en mode DNS uniquement.
- Tunnel karenax-maison créé, connecté et configuré avec deux routes.
- nas.karenax.net → HTTPS 192.168.1.75:5001. Origin Server Name = nas.karenax.net, vérification du certificat maintenue.
- ia.karenax.net → HTTP 127.0.0.1:8766, passerelle authentifiée par les jetons personnels. La liaison locale est limitée à la boucle locale ; le tunnel Internet est chiffré.
- Aucun changement des redirections SFR ni du fonctionnement de WireGuard.

## Vérifications publiques

La résolution des deux sous-domaines via 1.1.1.1 retourne les adresses Cloudflare 104.21.93.114 et 172.67.209.66.

Des requêtes HTTPS avec ces adresses explicitement résolues, le nom de domaine correct et la validation TLS normale donnent :

| Accès | Résultat |
| --- | --- |
| https://nas.karenax.net/ | HTTP 200 ; validation TLS réussie |
| https://ia.karenax.net/v1/models sans jeton | HTTP 401 ; validation TLS réussie |
| NAS local avec le nom nas.karenax.net | HTTP 200 ; certificat Let’s Encrypt valide |

La résolution DNS habituelle de ce PC conservait encore des réponses négatives lors du premier test. Le fonctionnement du tunnel public est vérifié, mais les caches des réseaux et des postes peuvent retarder l’accès par le nom.

## Protection et confidentialité

- HTTPS obligatoire activé chez Cloudflare.
- Règle « NAS et IA - sans cache » active, action Bypass cache, expression : (http.host in {"nas.karenax.net" "ia.karenax.net"}).
- Authentification DSM conservée pour le NAS. Cloudflare Access n’est pas configuré.
- Authentification par jetons personnels conservée pour l’API IA.
- Cloudflare termine HTTPS et peut techniquement lire le trafic. Le propriétaire a explicitement accepté cette limite après explication. La mise en cache désactivée ne constitue pas une garantie d’absence de journalisation ou d’accès technique.

## DNSSEC

L’ancienne protection DNSSEC OVH a été désactivée pour la migration. Le premier changement des serveurs DNS a affiché une erreur « you are not authorized to update DS data », mais le changement des NS a effectivement été appliqué, puis le domaine a été activé chez Cloudflare.

DNSSEC a ensuite été activé chez Cloudflare. La clé publique et son DS ont été vérifiés par calcul SHA-256 avant publication. L’ajout chez OVH a été confirmé avec succès. Le DS est maintenant visible via le résolveur validant 1.1.1.1, et Cloudflare affiche « Success! karenax.net is protected with DNSSEC. ».

DS attendu : karenax.net. 3600 IN DS 2371 13 2 F49EF809F8363DE5725A7B499437FBEB959C70E588D4B36102B7E621761A456A

Ne pas réactiver le bouton DNSSEC pour les serveurs internes OVH : la zone autoritaire est maintenant Cloudflare. La protection repose sur le DS Cloudflare publié chez OVH.

## Connecteur Windows

- Binaire officiel cloudflared 2026.10.0, empreinte vérifiée contre la publication GitHub.
- Jeton enregistré hors du dépôt, dans un dossier à accès restreint ; absent de la ligne de commande et des rapports.
- Tâche Windows Karenax-Cloudflare-Tunnel, en cours d’exécution, lancée à l’ouverture de session, relancée toutes les minutes en cas d’échec.
- Le premier connecteur temporaire a été arrêté après vérification du connecteur de la tâche.
- Le tunnel dépend actuellement de ce serveur Windows, qui doit rester allumé. Il démarre avec la session de son propriétaire, pas avant connexion Windows.

## Éléments restant à terminer

- Les certificats gratuits OVH sont affichés Actif pour karenax.net et www.karenax.net (expiration 4 janvier 2027). Après un délai de déploiement, karenax.net répond HTTP 200 avec validation TLS normale sur 213.186.33.87. Le certificat www.karenax.net est actif dans OVH mais son déploiement effectif présente encore un certificat ne couvrant pas ce nom au dernier test ; il reste à confirmer.
- Le certificat NAS est importé et affecté à DSM ; son renouvellement automatique reste à configurer avant expiration le 4 janvier 2027.
- Installer la version personnelle 3.5.3 sur le PC distant pour disposer du choix WireGuard / HTTPS. Les deux EXE personnels ont été préparés dans lanceur/clients, avec leurs clés existantes conservées.

Sources : [fonctionnement du déchiffrement Cloudflare](https://developers.cloudflare.com/data-localization/regional-services/), [DNSSEC OVH](https://docs.ovhcloud.com/fr/guides/web-cloud/domains/dns-dnssec), [paramètres du tunnel](https://developers.cloudflare.com/tunnel/advanced/origin-parameters/).


## Client Fred 3.5.3 — choix de connexion disponible

Dans Réglages → Connexion : choisir WireGuard · VPN ou HTTPS · Cloudflare, puis Appliquer la connexion. WireGuard reste le mode initial et son bouton Automatique conserve la sélection des adresses locales / Internet. Aucun repli silencieux vers Cloudflare n’est ajouté.

Le mode HTTPS utilise exclusivement https://ia.karenax.net, avec la vérification normale du certificat, les paramètres de proxy Windows et les jetons personnels existants. Les redirections HTTP sont refusées pour éviter de transmettre le jeton à une autre origine. Le choix est enregistré dans les réglages DPAPI ; les conversations, la clé API locale pour Hermes / OpenCode et les mises à jour restent compatibles.

Le User-Agent identifie le logiciel AccesServeurFred/3.5.3 : la signature Python-urllib par défaut provoquait un blocage Cloudflare 1010, résolu sans modifier les protections de la zone.

Vérifications :
- 46 tests Python couverts ; les 3 échecs initiaux liés à un contrôle TLS de test et aux anciens binaires ont été refaits avec succès après correction et compilation. Les contrôles WireGuard, accès révoqués, historiques, signature et retour de mise à jour passent.
- Les deux EXE personnels 3.5.3 ont réussi leur auto-test avec profil intégré.
- Analyse syntaxique JavaScript et tests de collage / sélection explicite des modes réussis.
- Test réel avec un EXE personnel : HTTPS connecté, protocole 3, zéro tunnel WireGuard démarré.
- Manifeste de mise à jour 3.5.3 récupéré par HTTPS et signature vérifiée avec la clé épinglée du profil.
- Passerelle rechargée après vérification de l’absence de générations et de tâches en cours, avec préservation de l’état du modèle. Le processus modèle 17404 est resté lancé depuis 08:27:48 ; WireGuard est en fonctionnement sur UDP 51820.

Les EXE préparés sont lanceur/clients/0402a094eeb03bdc.exe (Client Windows) et lanceur/clients/8ab49467b5ff732e.exe (Client Windows 2). Chacun conserve son propre accès. Une ancienne version bloquée sur WireGuard au travail doit recevoir son nouvel EXE pour pouvoir sélectionner HTTPS ; elle ne peut pas utiliser ce nouveau mode avant mise à jour.


## Noms des EXE corrigés

Les téléchargements incluent maintenant la version réelle du profil et le nom du client : « Accès serveur Fred v3.5.3 - Client Windows.exe » et « Accès serveur Fred v3.5.3 - Client Windows 2.exe ». Des copies identiques sont disponibles dans lanceur/clients sous ces noms. Les identifiants internes restent utilisés par le stockage ; ni les clés ni le contenu des EXE ne sont modifiés. Le nom et le SHA-256 des deux téléchargements ont été vérifiés sur la passerelle rechargée.
