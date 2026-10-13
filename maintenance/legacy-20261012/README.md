# Générateurs historiques archivés le 12 octobre 2026

Ces fichiers gardent les anciennes transformations de l’interface et de livraison.
Le suffixe `.txt` empêche leur exécution accidentelle. Ils n’entrent plus dans la
construction des applications actuelles.

| Ancienne source | Usage historique |
| --- | --- |
| `lanceur/deploy_v2.py` | Publication de la génération 2 |
| `lanceur/refondre_interface.py` | Réécriture ponctuelle de l’interface |
| `lanceur/integrate_workspace_assets.py` | Injection initiale des ressources des espaces |
| `lanceur/finalize_workspace_sources.py` | Finalisation des sources des espaces |
| `client-qwen/ui-syntax-check.js` | Ancienne copie manuelle du JavaScript du chat |

Les constructions actuelles sont `client-qwen/Build-Client.ps1` et
`client-android/Build-Android.ps1`. Les tests JavaScript lisent directement les
sources communes. Aucun de ces anciens générateurs n’était appelé par les scripts
actuels ; la référence résiduelle dans l’archive de sources a été retirée.
