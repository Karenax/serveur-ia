# Réparation WireGuard sur le réseau local — 13 octobre 2026

Le signalement concerne des clients sur le même réseau que le serveur. L’adresse actuelle est `192.168.1.41/24`, attribuée par DHCP ; les profils distribués contenaient encore `192.168.1.40:51820`. Cette ancienne adresse répond maintenant depuis un autre équipement. La clé publique du serveur, l’adresse du tunnel et les autorisations des clients correspondent toujours aux profils personnels.

## Correction appliquée

- `lanceur/releases.py` actualise les routes locales pendant la préparation des EXE, même lorsque la version du binaire ne change pas.
- `lanceur/wireguard_access.py` actualise ces routes lors du téléchargement d’un profil Android, sans modifier son coffre chiffré.
- L’EXE personnel actif dans `lanceur/clients` a été préparé avec `192.168.1.41:51820`. Sa clé API et ses trois clés WireGuard restent identiques. La copie précédente est sauvegardée dans le répertoire privé ignoré par Git `toolchain/releases-staging/pre-wireguard-lan-20261013`.
- La console a été rechargée en préservant les deux processus Qwen et leurs enfants. Les empreintes des fichiers de clés, des réglages et des données utilisateurs sont identiques avant et après.

Les copies déjà présentes sur les postes clients ne peuvent pas être remplacées depuis ce serveur. Elles peuvent se reconnecter immédiatement en choisissant `192.168.1.41:51820` dans leurs réglages WireGuard. Le nouvel EXE distribué utilise cette adresse automatiquement sur le réseau local ; une adresse saisie manuellement reste prioritaire.

## Validation

`python -m unittest test_improvements test_devices test_remote -v` : **40 tests réussis**, en 166,993 s. Les tests de distribution reproduisent un changement de route locale et vérifient la conservation des clés, l’absence de modification du coffre Android, la préparation répétée et le retour à la version précédente. Les tests du transport couvrent le tunnel UDP chiffré réel, les accès simultanés, la révocation et la diffusion des réponses.

Vérification effective après rechargement, avec l’accès personnel existant :

- Le client Windows choisit la nouvelle route locale pour un poste appartenant au réseau `192.168.1.0/24`.
- La négociation WireGuard réussit et les cinq modèles sont accessibles.
- L’historique est accessible : HTTP 200, 55 538 octets. Les vérifications précédentes couvrent aussi `/v1/status`, `/v1/device` et `/v1/workspace`.
- HTTPS Cloudflare fonctionne avec le client Windows : état `ready`, cinq modèles.
- L’EXE personnel corrigé réussit `--self-test --with-profile`.
- Ruff passe pour les deux modules serveur modifiés, règles F401/F841/F821.

Les preuves JSON ne contiennent aucune clé privée ni contenu de conversation : `profiles-after.json`, `service-after.json`, `lan-after.json` et `final-verification.json`.

Une redirection UPnP a été essayée pendant le diagnostic initial, puis supprimée après confirmation que le problème concernait le réseau local. La configuration de la box a été rétablie ; les tentatives d’accès à l’adresse publique depuis le LAN ne constituent pas un test depuis Internet. Preuves : `forwarding.json` et `forwarding-reverted.json`.

## Adresse à stabiliser

Le serveur utilise encore DHCP. Réserver son adresse dans la box évite un prochain changement ; la documentation existante `lanceur/LISEZ-MOI.txt` décrit déjà cette étape. La préparation des profils remet maintenant les routes locales à jour lorsqu’une telle modification survient.
