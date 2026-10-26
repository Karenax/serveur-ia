# Certificat NAS préparé — 6 octobre 2026

Un certificat public Let's Encrypt pour **nas.karenax.net** a été obtenu par validation DNS chez OVH. La chaîne de confiance a été vérifiée avec le magasin Windows, et la correspondance entre certificat et clé privée a été vérifiée.

| Vérification | Résultat |
| --- | --- |
| Nom couvert (SAN) | nas.karenax.net |
| Émetteur | Let's Encrypt YR2 |
| Expiration | 4 janvier 2027, 10:08:21, heure de Paris |
| Confiance Windows | Oui, aucun défaut de chaîne signalé |
| Correspondance de la clé privée | Oui |
| Empreinte SHA-1 du certificat | F988CBFA1EA6167391B45D1448EB4B9A2EF0600A |
| Import dans DSM | Confirmé par la capture fournie |
| Renouvellement automatique | À configurer |

## Fichiers pour l'import Synology

Dossier privé, conservé hors du dépôt du serveur :

`C:\Users\karen\AppData\Local\Karenax-ACME\State\Import-NAS`

| Champ de l'import Synology | Fichier |
| --- | --- |
| Clé privée | cle-privee.pem |
| Certificat | certificat.pem |
| Certificat intermédiaire | chaine.pem |

Les fichiers héritent des droits restreints du dossier d'état ACME : utilisateur courant, SYSTEM et administrateurs. La clé privée n'a pas été affichée dans les sorties ni copiée dans le dépôt.

Dans DSM, ajouter un nouveau certificat en choisissant l'import, puis affecter ce certificat au service DSM après vérification des affectations existantes. Conserver les anciens certificats lors de cette opération. Une fois importé, contrôler le certificat réellement servi par le NAS pour le nom nas.karenax.net.

L'URL utilisant directement 192.168.1.75 n'est pas couverte. L'accès sans avertissement nécessite nas.karenax.net, une résolution DNS adaptée et le certificat affecté au service HTTPS. HTTPS est déjà actif sur le NAS au port 5001.

## État de la connexion distante

La zone Cloudflare est préparée mais reste en attente d'activation. Le formulaire de création du tunnel karenax-maison est préparé. Aucun jeton du tunnel n'a encore été créé, et les routes nas.karenax.net et ia.karenax.net ne sont pas publiées.

Le connecteur officiel cloudflared 2026.10.0 est téléchargé dans C:\Users\karen\AppData\Local\Karenax-Cloudflare\bin\cloudflared.exe. Son SHA-256 correspond à la valeur publiée par GitHub et sa commande de version fonctionne. Aucun service ni tunnel n'est démarré.

L'origine prévue pour l'IA est la passerelle authentifiée 127.0.0.1:8766. L'origine NAS prévue est HTTPS sur 192.168.1.75:5001 avec le nom de certificat nas.karenax.net. Prévoir une restriction Cloudflare Access pour DSM avant sa publication, et conserver les jetons personnels Fred pour l'API IA.

Les clics Computer Use dans Chrome restent en échec faute de géométrie de capture. La session DSM et ses réglages sont lisibles par l'arbre d'accessibilité ; l'ouverture manuelle de l'onglet Certificat a été demandée.

Sources : [import de certificats Synology](https://kb.synology.com/index.php/en-uk/DSM/help/DSM/AdminCenter/connection_certificate?version=7), [validation DNS Posh-ACME](https://poshac.me/docs/v4/Guides/Custom-Challenge-Validation/), [connecteur Cloudflare](https://developers.cloudflare.com/tunnel/downloads/).

## Vérifications supplémentaires

La capture native reste en échec après réinitialisation de la session Computer Use : aucun clic DSM n'a été effectué. Le certificat a ensuite été importé par le propriétaire ; son affectation au service DSM reste à effectuer.

Le TXT temporaire _acme-challenge.nas.karenax.net a été supprimé chez OVH après validation. Son absence a été contrôlée sur les deux serveurs DNS autoritaires OVH.

La box SFR a été inspectée : les redirections existantes comprennent 5000 et 5001 vers 192.168.1.75, ainsi que WireGuard 51820 vers le serveur IA. Aucun réglage de box n'a été modifié. Le tunnel sortant et la validation DNS du certificat n'exigent pas de nouvelles redirections.

Chez OVH, les deux domaines karenax.net et www.karenax.net sont sélectionnés dans le formulaire d'activation gratuite SSL Let's Encrypt. L'activation n'a pas été lancée : le DNS public pointe encore vers l'adresse du domicile, et le NAS met encore à jour le DynHost OVH de karenax.net.

Les confirmations requises par l'outil navigateur pour créer le connecteur persistant Cloudflare et désactiver temporairement DNSSEC ont été demandées. Aucun changement des serveurs DNS, de DNSSEC, ni de publication des services n'a été effectué sans ces confirmations.


## Certificat importé par le propriétaire

La capture fournie confirme la présence de nas.karenax.net, expirant le 4 janvier 2027. Le certificat synology reste indiqué comme certificat par défaut.

Un contrôle TLS réel de 192.168.1.75:5001 avec le nom serveur nas.karenax.net confirme que DSM sert encore le certificat CN=synology, signé par Synology Inc. CA, empreinte FC20665BFBE9C768514E20113D48802C8D97256E. La validation est refusée pour nom incorrect et chaîne non approuvée ; aucune validation TLS n’a été désactivée.

Prochaine étape : dans Certificat → Paramètres, affecter nas.karenax.net au service utilisé par DSM, puis vérifier à nouveau le certificat réellement servi. La configuration des autres services doit être préservée.

## Affectation DSM vérifiée après confirmation utilisateur

Le propriétaire a affecté nas.karenax.net à « Paramètres système par défaut » puis confirmé la validation.

La connexion TLS réelle à 192.168.1.75:5001, avec nas.karenax.net comme nom de serveur, réussit sans exception ni désactivation de validation. Le certificat servi est CN=nas.karenax.net, empreinte F988CBFA1EA6167391B45D1448EB4B9A2EF0600A, expiration 2027-01-04 09:08:21 UTC. Il correspond au certificat Let’s Encrypt préparé.

L’import et l’affectation DSM sont donc terminés. La résolution publique et le tunnel Cloudflare restent à activer. Le renouvellement automatique reste à configurer.
