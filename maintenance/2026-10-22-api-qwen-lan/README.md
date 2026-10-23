# API Qwen sur le réseau local

Activée le 22 octobre 2026 à la demande de l’utilisateur : accès direct au seul moteur Qwen, sans authentification, pour les applications compatibles OpenAI.

| Paramètre | Valeur |
| --- | --- |
| Adresse de base OpenAI | `http://192.168.1.41:8080/v1` |
| Modèle | `qwen3.8-flash-next-iq4-xs` |
| Clé API | Aucune ; `local` si l’application exige une valeur |
| Réseau autorisé | `192.168.1.0/24` |

Le catalogue est disponible sur `GET /v1/models` et les conversations sur `POST /v1/chat/completions`, y compris en streaming. Le catalogue contient uniquement le Qwen chargé, sans les fournisseurs Hermes/Fred. Les clients Fred Windows/Android conservent leurs transports existants.

Windows redirige uniquement `192.168.1.41:8080` vers `127.0.0.1:8080` avec `netsh interface portproxy`. Il s’agit de l’API native du moteur Strata/Qwen. Le processus du modèle (PID 1968 lors de l’installation), ses réglages et son écoute loopback n’ont pas été modifiés. Aucune relance du modèle ou de Fred n’a été nécessaire.

La règle de pare-feu `Qwen-API-LAN-TCP-8080` autorise le TCP entrant sur cette seule adresse et ce seul port depuis `192.168.1.0/24`. Elle s’applique à tous les profils Windows, car l’interface Ethernet actuelle est classée Public. La redirection et la règle sont persistantes ; le service Windows `iphlpsvc` est démarré et en démarrage automatique. Ne pas rediriger ce port depuis la box : cet accès est destiné au LAN sans authentification.

`Configurer-Qwen-LAN.ps1` réapplique la configuration de façon idempotente. Exécuté en administrateur avec `-Retirer`, il retire uniquement cette redirection et sa règle de pare-feu. Il conserve le moteur et le service Windows.

Validation : `installation.json` rapporte la configuration installée ; `avant.json` conserve l’écoute d’origine. `verifier.py` a découvert l’unique modèle puis effectué une vraie conversation en streaming, sans en-tête Authorization, via l’adresse LAN. Réponse `OK`, marqueur `[DONE]` reçu, résultat dans `verification.json`. L’écoute du moteur conserve le PID 1968 après l’installation. Aucun autre appareil n’a été piloté ; la réception depuis un appareil distant reste à confirmer sur cet appareil.

## Commande dans la console serveur

Dans **API et réseau → Qwen sur le réseau local**, les paramètres actuels sont affichés avec **Copier les paramètres** et **Copier l’adresse locale de Qwen**. **Couper l’accès local** retire la redirection et sa règle de pare-feu ; **Activer l’accès local** les rétablit, avec la même restriction au sous-réseau. Windows demande une validation administrateur pour chaque changement. Le modèle reste chargé et ses réglages ne sont pas modifiés. L’état choisi est persistant dans Windows.

La console lit la redirection, la règle de pare-feu et l’écoute Windows réelles. Elle distingue un accès coupé, une configuration incomplète, un modèle indisponible et une validation Windows en attente. En cas d’annulation ou d’échec, elle conserve l’état observé et affiche une erreur permettant de réessayer. Les anciens paramètres d’écoute du moteur restent disponibles sous **Réglages du moteur au prochain lancement**.

Le contrôle est implémenté dans `lanceur/local_network.py` et `lanceur/Configurer-Qwen-LAN.ps1`, appelé uniquement par la commande protégée de la console `/api/local-network`. Une page d’origine étrangère ou sans jeton de console ne peut pas déclencher la modification. Le statut de la commande est conservé dans `lanceur/qwen-lan-action.json` ; les anciennes preuves d’installation ne servent pas à décider si le mode est actif.

Validation de l’interface : douze tests Python ciblés, trois tests des frontières de sécurité de la console, syntaxe Python/JavaScript et PowerShell 5.1/7 vérifiée. Test navigateur avec états et commandes simulés : actif, coupé, attente, validation annulée, état indisponible et Qwen indisponible ; copie réelle dans le presse-papiers, focus clavier et largeur 390 px vérifiés. Captures et résultats sous `interface/`. Le contrôle UX signale trois textes longs préexistants hors du bloc ajouté, sans suppression de contenu. `interface-production.json` confirme le chargement dans la console et la conservation des processus Qwen, clés, données, sauvegardes et réglages Phonon.

Limite de la vérification native : l’essai via la vraie commande a demandé une coupure, mais la validation administrateur Windows a été annulée. `switch-production.json` conserve ce résultat non réussi et confirme que l’accès est resté actif. Aucune coupure/réactivation Windows réussie n’est revendiquée pour ce nouvel essai ; les comportements de commande sont couverts par les tests isolés. Il n’y a pas eu de nouvelle tentative d’élévation après cette annulation.
