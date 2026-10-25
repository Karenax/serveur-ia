# Applications, expériences et preuves

Le fonctionnement actuel est décrit dans [CONTEXTE-PROJET.md](CONTEXTE-PROJET.md).
Les sources utilisées par les builds sont `lanceur`, `client-qwen`, `client-android`
et `client-voice`. Le moteur de production est Strata officiel **0.1.45.3**,
dans `dependances/strata-0.1.45.3/engine-cuda12`, avec le serveur Python corrigé
et l’encodeur conservés dans `dependances/strata-0.1.43.1`.
Les dossiers d’expérimentation conservent des travaux
datés ; ils ne définissent pas la configuration de production.

| Emplacement | Rôle |
| --- | --- |
| `dependances/` | Strata 0.1.45.3 en production, serveur Python 0.1.43.1 corrigé conservé ; références des moteurs historiques et leurs patchs |
| [Guide de l’assistant](GUIDE-ASSISTANT-KIARA.md) | Utilisation de la mémoire, des actions vocales, rappels, bilans, images et activation expérimentale |
| [Intégration du 25 octobre](maintenance/2026-10-25-assistant-integration/README.md) | Serveur/Windows 3.5.52, Android 1.0.23/code 24 ; tests, publication, sauvegarde et limites matérielles |
| `recherche/` | Sources adaptées, protocoles et résultats d’exploration des moteurs |
| `comparatifs/` | Mesures de configurations, à lire avec leurs versions et matériels |
| `preuves/` | Validations des livraisons antérieures, fixtures et captures |
| `audits/2026-10-12/` | Audit initial, corrections, regressions, volumes et publication |
| `audits/2026-10-13-wireguard/` | Correction des profils LAN, tests de connexion et conservation des clés |
| `maintenance/2026-10-13-ip-fixe/` | Configuration Windows persistante sur 192.168.1.41 et validation WireGuard/HTTPS |
| `maintenance/2026-10-13-strata-0.1.43.1/` | Mise en service du moteur officiel, réglages, sauvegarde précédente et retour arrière |
| `maintenance/2026-10-13-contexte/` | État des services et configurations recoupé lors de la mise à jour du contexte |
| `maintenance/legacy-20261012/` | Anciens générateurs déplacés et neutralisés par le suffixe `.txt` |
| `HISTORIQUE-PROJET-AVANT-AUDIT-20261012.md` | Ancien contexte complet ; décisions et chronologie conservées |

Les preuves Hermes, voix, EG2 et des lots 0–4/6–8 restent des références de validation.
Leurs numéros de versions décrivent la livraison testée à l’époque. Ils ne remplacent
pas la version actuelle du contexte et des manifestes. Les expérimentations GPU
restent traçables ; aucune suppression générale n’a été appliquée à leurs résultats.
