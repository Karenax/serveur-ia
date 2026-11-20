# Comparatifs historiques Huihui sur P100

Les quatre variantes `Comparer-Huihui*.ps1.txt` conservent les scripts d'essai archivés le 18 novembre 2026. Le suffixe `.txt` suit la convention utilisée pour les autres scripts historiques du dépôt.

Ces scripts calculaient leurs chemins depuis la racine du dépôt et pouvaient arrêter le moteur de leur banc d'essai avant de le relancer. Ils dépendaient d'un ancien interpréteur Python et des binaires du banc P100. Leur contenu est conservé à l'identique. Les résultats de mesure restent dans [comparatifs](../../comparatifs).

Les références et limites de la recherche d'appelants figurent dans l'[inventaire des scripts](../../audits/2026-11-16-architecture-interface/INVENTAIRE-SCRIPTS.md). Si un ancien appelant doit être repris, utiliser une copie isolée reproduisant ses chemins avant de remettre le nom d'origine au script concerné.
