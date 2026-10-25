# Diffusion Windows 3.5.42 — 24 octobre 2026

**La version 3.5.42 est publiée et sa mise à jour signée est disponible.**
Le client actif a été reconditionné avec ses clés et son profil existants.
Les clients déjà ouverts peuvent utiliser leur bouton de mise à jour ; aucune
fermeture forcée ni installation automatique du complément Max n'a été imposée.
Android conserve sa version actuelle.

## Contenu

- Parcours Vocal Low / Max et installation optionnelle proposée sur AMD/NVIDIA.
- Taille et espace disque annoncés avant confirmation, progression, annulation
  et relance, contrôle de signature et d'empreintes, test de fluidité.
- Moteur Max séparé : Parakeet progressif, Qwen3-TTS quantifié et streaming,
  préparation des phrases suivantes pendant la lecture, interruptions et mesures.
- Low et la dictée restent sur leur fonctionnement existant.

## Publication vérifiée

| Élément | Résultat |
| --- | --- |
| Version client et passerelle | 3.5.42 |
| EXE de base | 94 477 345 octets |
| SHA-256 | `822b7da41ba5b4445c92795c4fde3cb73d7dc605c00b5c4cea6d1fa80a0d9999` |
| Signature | Ed25519, clé de mise à jour existante |
| Client personnel actif préparé | 1, identité et clés conservées |
| Complément Max | `vulkan-q4-62db5a83ab69c6c7`, 46 151 015 octets hors modèles |
| Modèles Max | Téléchargements séparés, environ 1,9 Go avec Low déjà installé, 2,6 Go sur un PC neuf |

Une sauvegarde manuelle chiffrée, protégée et vérifiée a été créée avant la
publication ; sa seconde copie NAS est confirmée. Les anciens fichiers de
distribution restent dans `toolchain/releases-staging/windows-3.5.42/previous/`
et le retour des EXE personnels utilise l'archive gérée par `releases.py`.
Un ancien EXE 3.5.15 non associé à un profil actif a été conservé intact.

La passerelle et la console ont été rechargées en préservant les processus Qwen
chargés. Les signatures des deux téléchargements ont été vérifiées sur les flux
réellement servis par l'API, pas seulement sur les fichiers locaux. Le téléchargement
du complément exige l'authentification. La mémoire GPU insuffisante du serveur
reste un refus explicite de Max ; la disponibilité du complément à télécharger
ne signifie pas que le moteur Max est qualifié sur le serveur.

Contrôles après mise en service :

- Même identité des processus Qwen, mêmes clés et réglages d'accès.
- Mêmes empreintes logiques des historiques, projets, documents, souvenirs et tâches.
- Programmation des sauvegardes conservée ; voix Tiphaine et Hermes prêts.
- Version et manifeste 3.5.42 servis et vérifiés.
- EXE de base et EXE personnel : auto-tests natifs réussis sans capture du micro.
- Dix tests de mise à jour/signature avec le nouveau binaire réussis, dont
  remplacement, conservation du profil, refus d'un binaire altéré et retour arrière.
- Six tests de disposition/récupération de l'updater réussis.

Les preuves sont `publication.json`, `production.json` et `avant-livraison.json`.
Le [rapport du complément](../2026-10-24-max-optionnel/README.md) détaille ses
mesures, les tests UI et les limites de qualification matérielle.
