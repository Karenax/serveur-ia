# Applications, expériences et preuves

Le fonctionnement actuel est décrit dans [CONTEXTE-PROJET.md](CONTEXTE-PROJET.md).
Les sources utilisées par les builds sont `lanceur`, `client-qwen`, `client-android`
et `client-voice`. Le moteur de production et sa source serveur se trouvent dans
`dependances/strata-0.1.43.1`. Les dossiers d’expérimentation conservent des travaux
datés ; ils ne définissent pas la configuration de production.

| Emplacement | Rôle |
| --- | --- |
| `dependances/` | Distribution Strata 0.1.43.1 en production ; références des six dépôts de moteurs historiques et leurs patchs |
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
