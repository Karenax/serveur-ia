# Sélecteur Hermes — livraison du 11 octobre 2026

Windows/serveur **3.5.25** et Android **1.0.8/code 9** sont publiés. Le serveur
annonce les mises à jour et fournit les deux fichiers après authentification.
Les téléchargements correspondent aux empreintes des paquets validés ; le
certificat Android et la clé publique de signature Windows sont conservés.

Le champ **Modèle de cette conversation** apparaît dans les deux clients.
Le choix est conservé dans l'historique chiffré et synchronisé, transmis au chat
et au contexte, et utilisé par la conversation vocale Windows. Un modèle retiré
ou indisponible exige un autre choix explicite. Les trois boutons du correcteur
restent directement sur Qwen.

Le partage global des connexions Hermes est activé pour les comptes Fred actuels
et futurs, selon la décision de l'utilisateur. Les abonnements et quotas sont
communs ; sessions, projets et mémoires des comptes restent séparés. Les clients
reçoivent uniquement les métadonnées publiques des modèles. Les jetons de
renouvellement restent dans le magasin Hermes central ; les clés d'exécution
sont fournies au processus natif par le broker privé après contrôle du compte,
du modèle et de la demande active.

## Connexions réelles sur ce PC

Qwen reste chargé et utilisable. Hermes ne possède aucune connexion OpenAI/Codex
active découverte sur ce PC. Copilot annonce **51 modèles**, mais sa connexion
est **indisponible** : l'échange du jeton API répond HTTP 403 et aucun modèle
n'est activé dans le sélecteur natif. Deux essais courts et isolés avec
GPT-5-mini ont reçu HTTP 400, « The requested model is not supported. ».
Le code conserve ce catalogue avec `available=false`, affiche la connexion
indisponible et refuse le jeton GitHub de secours. Aucun login ni abonnement
n'a été ajouté ou modifié pendant ce travail.

Le diagnostic est dans [provider-connection-validation.json](provider-connection-validation.json).
L'utilisation effective d'un fournisseur externe demande une connexion
opérationnelle dans Hermes ; le catalogue est ensuite redécouvert. Une session
dans une autre application du PC ne constitue pas à elle seule cet accès.

## Contrôles réalisés

| Parcours | Résultat et preuve |
| --- | --- |
| Backend et profils Hermes | 21 tests dédiés et 36 régressions passent : isolation, révocation, sélection, historique, découverte native froide, broker, helper et accès simultanés. [Preuve](backend-validation.json) |
| Cloud natif en fixture | Vraie passerelle Hermes, clients SDK et auxiliaires Chat/Responses avec endpoint HTTP synthétique ; Qwen interdit, modèle exact et clés privées vérifiés. Inclus dans les tests backend |
| OAuth Codex | 7 tests SDK avec jetons fictifs : principal, auxiliaire asynchrone, streaming, rotation compte/région et URL officielles. La passerelle native conserve profils et reprise avec le bootstrap Fred. Aucun appel OpenAI réel. [Preuve](codex-compatibility-validation.json) |
| API Fred | 29 tests : catalogue authentifié, contexte distant estimé, refus des modèles non autorisés, vision, console admin, correcteur direct, annulation et révocation. [Preuve](gateway-validation.json) |
| Accès et Windows publié | 20 régressions passent avec le nouvel EXE : démarrage personnel, tunnel WireGuard réel, flux, reconnexion, catalogue legacy et révocation. [Preuve](remote-release-validation.json) |
| Clients | Interface Windows/Android, modèle par conversation, reconnexion, absence de substitution, capacités, contexte et 7 scénarios vocaux ; 23 tests Python d'historique et de transport. [Preuve](client-ui-validation.json) |
| Console de partage | 7 contrôles navigateur : jeton admin, partage global et individuel, erreurs, quotas communs et fournisseur indisponible. [Preuve](console-sharing-ui.json) |
| Android signé | 29 contrôles avec Release installé sur émulateur : catalogue, stockage chiffré, tunnel WireGuard, contexte/chat, SSE, correcteur et mise à jour. Ressources ASR et natives inchangées. [Rapport](ANDROID.md) |
| Windows compilé | Version PE, signature Ed25519, compatibilité de l'ancien updater, sources embarquées et 481 fichiers natifs vérifiés ; autocontrôle et vraie fenêtre compilée passent. [Build](windows-build-validation.json), [fenêtre](windows-native-window.json) |
| Qwen et outils réels | 4 tours synthétiques terminés : calcul, continuation avec historique d'outils, séparation du compte B, recherche documentaire et source. Création automatique de profil et projet natif vérifiée. [Preuve](native-qwen-validation.json) |
| Publication | Versions annoncées, paquet Windows personnel régénéré, téléchargements authentifiés et partage global vérifiés ; processus Qwen, réglages et clés existants préservés. [Preuve](delivery-validation.json) |

Les captures [Windows](selector-windows.png) et [Android](selector-android.png)
utilisent un catalogue synthétique pour vérifier l'interface. Les essais
fournisseurs n'ont utilisé aucun historique de production. Android a été testé
sur émulateur x86_64 ; les essais acoustiques et physiques ARM64 n'ont pas été
refaits pour cette modification.

La première tentative de publication s'est arrêtée pendant l'attente d'un
processus déjà terminé. La console a été relancée, l'attente corrigée, puis la
publication et ses contrôles ont réussi. Le modèle Qwen est resté chargé.
