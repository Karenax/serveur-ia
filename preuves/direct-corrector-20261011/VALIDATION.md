# Correcteur et reformulateur directs — 11 octobre 2026

Les trois boutons **Corriger**, **Reformuler professionnel** et **Reformuler amical** utilisent directement le Qwen local du serveur dans Windows **3.5.24** et Android **1.0.7, code 8**. Les conversations ordinaires et les tâches rédactionnelles continuent à utiliser Hermes.

## Fonctionnement

Les clients envoient le mode et le texte via la passerelle Fred authentifiée. Le serveur impose la consigne correspondante et désactive la réflexion, sans appeler Hermes, les outils, les documents ou la mémoire EG2. La génération conserve la file GPU partagée, les contrôles d’accès et l’affichage progressif.

Le texte source et le résultat restent enregistrés dans l’historique Fred. Ces corrections ne créent pas de tour durable Hermes et ne tentent pas de récupération d’agent après une coupure. Un résultat partiel est conservé ; le bouton Arrêter cible la demande et son compte. L’annulation couvre également l’attente, le prétraitement et une réponse réseau silencieuse, avec un reçu temporaire borné pour les annulations arrivant avant l’envoi.

## Vérifications

- [Interface Windows et Android](client-ui-validation.json) : les trois modes, l’affichage SSE progressif, l’annulation avec texte partiel, l’enregistrement/rechargement et la panne sans récupération Hermes passent. La fermeture Windows transmet le bon type d’annulation ; Android conserve aussi sa réponse JSON. Le chat ordinaire reste sur Hermes. Ces essais utilisent le vrai code d’interface et un transport HTTP synthétique isolé.
- [Vrai Qwen chargé](native-validation.json) : les trois modes donnent un texte complet sur un compte et une passerelle temporaires. Un substitut Hermes indisponible et un contexte documentaire qui échoue à tout appel ne sont jamais consultés. Premier texte en 2,34–2,48 secondes, réponse complète en 2,88–3,06 secondes pour le court texte synthétique ; il s’agit d’un essai ponctuel, pas d’un comparatif ni d’une garantie de délai.
- [Serveur et transport](backend-validation.json) : modes et paramètres imposés, absence de Hermes/EG2, accès, révocation, file partagée, annulation avant admission/headers et pendant le flux, SSE fragmenté/chunked et annulation globale avec un agent concurrent. Les tests existants couvrent aussi WireGuard réel, HTTPS, deux profils et l’EXE personnel.
- [Paquet Windows](windows-build-validation.json) : version PE et autotest, signature Ed25519 habituelle, compatibilité avec l’ancien updater, code d’interface/fermeture incorporé et 481 fichiers voix vérifiés. Les régressions Hermes d’interface, Android et les sept scénarios de conversation vocale passent. Les sept tests Python d’historique/distribution Windows passent.
- [Paquet et transport Android](ANDROID.md) : signature habituelle, version/code, alignement, assets et bibliothèques ASR préservés ; les trois modes passent par le proxy natif et le vrai tunnel WireGuard vers un serveur synthétique isolé.

## Livraison

Le [contrôle de publication](delivery-validation.json) vérifie les deux manifestes, les téléchargements authentifiés et leurs empreintes, le paquet Windows personnel, la nouvelle route de transformation et la disponibilité Hermes/voix. Les identités des processus Qwen, le modèle chargé, les accès, les réglages et la configuration Hermes sont conservés. Aucun message d’essai n’est ajouté à un historique utilisateur.

Les mises à jour sont proposées par **Réglages → Mises à jour** dans les deux applications. Les essais ne mettent à jour aucun poste utilisateur ; Android conserve sa confirmation d’installation. Les journaux et helpers détaillés restent dans le staging ignoré `toolchain/releases-staging/direct-corrector-20261011/`.
