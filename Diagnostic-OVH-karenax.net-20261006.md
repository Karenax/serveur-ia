# Vérification OVH de karenax.net — 6 octobre 2026

Audit effectué dans l'espace client OVH ouvert par l'utilisateur, sans modification des réglages. La résolution publique a également été vérifiée depuis le serveur. Les résultats distinguent l'enregistrement du domaine, l'hébergement web OVH et l'accès au PC qui exécute le modèle.

## Domaine et DNS

| Élément | Résultat observé |
| --- | --- |
| Domaine | Enregistré, état technique actif |
| Expiration | 11 octobre 2027, renouvellement automatique |
| Serveurs DNS | dns106.ovh.net et ns106.ovh.net |
| DNSSEC | Activé |
| Protection contre le transfert | Activée |
| A de karenax.net | 84.103.164.10, TTL 60 secondes |
| www.karenax.net | CNAME vers karenax.net |
| ftp.karenax.net | CNAME vers karenax.net |
| DynHost du domaine racine | 84.103.164.10 |
| IP publique actuelle du PC serveur | 84.103.164.10 |
| AAAA pour le domaine et www | Aucun dans les vingt entrées de la zone consultée |

La zone publique est résolue correctement et l'adresse configurée correspond actuellement à la connexion du serveur. La présence de DynHost confirme la configuration d'une adresse dynamique ; elle ne prouve pas que le logiciel chargé des mises à jour fonctionne lors d'un futur changement d'IP.

L'onglet « Redirection » représente le pointage vers l'IP et les CNAME. Il ne montre aucune redirection HTTP active vers une autre page web. Les anciens TXT `1|www.karenax.net`, `3|welcome` et `l|fr` sont toujours présents ; leur présence ne transforme pas le pointage actuel vers l'IP du PC en relais HTTPS OVH.

## Hébergement web OVH

| Élément | Résultat observé |
| --- | --- |
| Offre | Free hosting, service actif |
| IPv4 de l'hébergement | 213.186.33.87 |
| IPv6 de l'hébergement | 2001:41d0:1:1b00:213:186:33:87 |
| Site | Website-www, dossier racine www |
| Domaines rattachés | karenax.net, www.karenax.net, karenax.cluster014.ovh.net |
| Certificats SSL | Aucun résultat dans la liste |

Le diagnostic IPv4 d'OVH indique explicitement que karenax.net pointe vers 84.103.164.10 au lieu de l'adresse attendue pour cet hébergement, 213.186.33.87.

Cela est cohérent si le domaine doit désigner le PC à domicile. En revanche, le navigateur ne peut pas atteindre le contenu de l'hébergement OVH par ce pointage. Un éventuel certificat installé chez OVH ne sécuriserait pas automatiquement les services du PC.

## Messagerie : configuration DNS

Le MX public est `1 redirect.ovh.net`. Le SPF est bien publié en TXT : `v=spf1 include:mx.ovh.com ~all`. La zone contient les deux CNAME DKIM OVH, les noms de serveurs de messagerie et les enregistrements de configuration automatique. Aucun défaut évident n'a été identifié dans ces éléments. Aucun message n'a été envoyé et le fonctionnement réel des boîtes ou des redirections mail n'a pas été testé.

## Vérification complémentaire sur le PC

Les services de l'application écoutent sur 127.0.0.1:8080 et 127.0.0.1:8765. Aucun service TCP n'écoute localement sur les ports 80 ou 443. La requête HTTPS vers karenax.net expire ; HTTP renvoie une redirection vers `/login?page_ref=/`, dont le serveur d'origine n'a pas été identifié. Cette réponse ne confirme pas un accès à Fred.

Le domaine qui se résout correctement n'implique donc pas qu'un site HTTPS soit publié sur le PC. Le test dans un navigateur ne valide pas non plus le tunnel WireGuard, qui utilise un autre protocole.

## Suite conseillée pour l'accès à Fred

Préparer un accès HTTPS distinct, par exemple ia.karenax.net, via un tunnel permanent Cloudflare, et ajouter cette URL comme mode de connexion dans le client Fred. Conserver l'authentification personnelle et tester le streaming, la révocation et les longues périodes de lecture du contexte.

Ne pas remplacer immédiatement l'adresse A du domaine par celle d'OVH : cela ferait atteindre le site OVH et pourrait casser les clients WireGuard qui utilisent actuellement karenax.net comme adresse du serveur.

Une migration des serveurs DNS vers Cloudflare doit conserver les enregistrements mail et traiter DNSSEC et DynHost ensemble. Si OVH n'est plus le fournisseur DNS faisant autorité, les mises à jour DynHost chez OVH ne mettront plus à jour la zone publique devenue gérée chez Cloudflare. Prévoir le remplacement de la mise à jour dynamique ou une autre organisation des noms avant cette migration.

Le contenu éventuel du dossier web OVH et le port entrant de la box n'ont pas été modifiés ni audités. Le diagnostic ne démontre pas un filtrage propre au réseau de l'entreprise.

## Préparation Cloudflare réalisée

Une zone Cloudflare gratuite a été créée et reste **en attente d'activation**. Les serveurs DNS publics OVH n'ont pas été remplacés et DNSSEC reste activé chez OVH.

- Les A `karenax.net` et `www.karenax.net` sont enregistrés dans la zone Cloudflare avec `213.186.33.87`, en mode DNS only.
- Les enregistrements de messagerie importés sont conservés en DNS only. Les deux CNAME DKIM et le SRV `_autodiscover._tcp` manquants lors du scan ont été ajoutés.
- La liste Cloudflare contient 19 enregistrements, dont le MX de www obtenu par le scan de l'ancien CNAME. L'édition IMAPS confirme priorité 0, poids 0, port 993 et cible ssl0.ovh.net.
- Serveurs DNS attribués : `louis.ns.cloudflare.com` et `zoe.ns.cloudflare.com`.
- Capture de vérification : `Cloudflare-DNS-prepares-20261006.png`.

La migration nécessite une désactivation temporaire de DNSSEC OVH, puis la nouvelle délégation DNS, avant de rétablir DNSSEC avec les données Cloudflare. Cette réduction temporaire de protection demande une confirmation à l'étape concernée selon la politique de contrôle du navigateur.

Le NAS Synology indiqué par l'utilisateur est à `192.168.1.75`, avec DSM sur HTTPS port 5001. Le contrôle du navigateur a rejeté son accès et interdit le contournement par un autre navigateur ou une autre technique. La configuration DSM doit donc être réalisée manuellement par l'utilisateur. Aucun réglage du NAS ni de la box n'a été modifié.

Les routes `nas.karenax.net` et `ia.karenax.net` ne sont pas encore publiées. L'origine IA prévue est la passerelle authentifiée `127.0.0.1:8766`, et non le port du modèle ni le lanceur administratif. Aucun connecteur Cloudflare ou nouveau jeton d'accès n'a encore été créé. Le client Fred doit encore recevoir et tester son mode HTTPS. La configuration n'est donc pas opérationnelle à ce stade.

### Session DSM ouverte manuellement dans Chrome

Après connexion manuelle par l'utilisateur, Computer Use Windows retrouve la session DSM déjà ouverte dans Chrome, sans interstitiel ni authentification à effectuer. L'interface identifie le NAS comme **DS218**, à `192.168.1.75`.

La lecture de l'arbre d'accessibilité et la saisie dans la recherche DSM fonctionnent. Les captures Chrome échouent (`FrameArrived timed out`, puis `window capture timed out`) et le clic sur « Accès externe » échoue avec `coordinate input geometry is unavailable`. La recherche « DDNS » est préparée et affiche le résultat « Accès externe > DDNS » ; un clic manuel a été demandé pour permettre la lecture de la configuration. Aucun réglage réseau du NAS n'a été changé.

La page DDNS ouverte manuellement confirme une entrée OVH : nom d'hôte `karenax.net`, adresse externe `84.103.164.10`, statut **Normal**, dernière mise à jour indiquée le 5 octobre 2026 à 16:55. La capture reste en échec après ce changement de page. L'ouverture manuelle de la fenêtre Modifier est demandée pour préparer le déplacement du DynHost vers un nom distinct du site web.
