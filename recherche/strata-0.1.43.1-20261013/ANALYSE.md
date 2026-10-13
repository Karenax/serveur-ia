# Strata et nouveaux essais P100 — 13 octobre 2026

## Conclusion

La version à comparer est **0.1.43.1**, publiée le 12 octobre, plutôt que 0.1.43. Notre production utilise encore le moteur 0.1.35 personnalisé. Le paquet officiel CUDA 12 inclut `sm_60` ; `strata.exe --version` renvoie bien 0.1.43.1.

**Le Qwen 27B ne fonctionne pas avec cette version de Strata.** Le GGUF local Huihui déclare `general.architecture=qwen35`, 65 couches et une dimension cachée de 5120. Le garde d'architecture du dernier Strata exige `qwen4exp`, 48 couches et 2560. Pour refaire les mesures du 27B après amélioration de la ventilation, reprendre Café/llama.cpp, tensor + MTP 2, puis comparer sans MTP. Les anciens 31,82/34,74 tokens/s étaient obtenus avec refroidissement entre les réponses, et ne prouvent pas le débit continu.

## Ce que les mises à jour changent pour Flash-Next

| Évolution | Intérêt pour nos deux P100 sous Windows |
|---|---|
| 0.1.42 : suppression d'une faible partie des experts manquants dans certaines fenêtres de vérification | Candidat pour la génération ; change légèrement les réponses. Commencer avec `STRATA_ROUTE_TAIL_SKIP=0`, puis mesurer `=7` séparément et vérifier l'activation dans les journaux. |
| 0.1.42 : calibration de la part PCIe | Notre `--pcie-frac 0` explicite conserve le calcul CPU des experts manquants. Les gains de la nouvelle sélection automatique ne s'appliquent donc pas à la référence. |
| 0.1.43 : assistance de la seconde carte au traitement des prompts courts | `STRATA_PREFILL_HELP=1` est pertinent pour le partage de couches ; vérifier son activation avec notre profil. Les mesures publiées sont sur RTX 3090 et ne prédisent pas notre gain. Les arrondis peuvent changer. |
| Traitement groupé du KV du brouillon sur la seconde carte | `STRATA_SPLIT_MTP_BATCH=1` peut améliorer les longs prompts. Contrôler si le moteur accepte le mode avec notre stockage KV ; comparer aussi génération et acceptation MTP. |
| Réduction des poids dupliqués par carte | `STRATA_STAGE_TRIM=1`, déjà disponible avant ces dernières versions, peut libérer de la VRAM pour les experts. Notre partage explicite 24/24 permet de l'essayer. Le placement CPU/GPU et les réponses peuvent changer. |
| 0.1.43.1 : maintien des lectures PLE directes, corrections du watchdog Windows | Pertinent pour nos longs documents et notre table PLE sur SSD. Évite un basculement automatique vers mmap susceptible de provoquer des lectures froides très lentes. Ce correctif ne garantit pas de récupérer toute la régression observée en 0.1.41. |
| 0.1.43.1 : pipeline du batch sur deux cartes | À réserver à une campagne de requêtes concurrentes ; le correctif ne promet aucun gain pour notre mesure séquentielle. |
| Recouvrement adaptatif | Off par défaut en 0.1.43.1. Le chemin documenté concerne une carte seule et l'adaptation active ; notre partage de couches avec `--adapt-every 0` ne constitue pas un test utile de cette option. |

Le gain de streaming Windows annoncé par le projet concerne des experts servis depuis les GGUF. Notre complément résidant en RAM rend ce chiffre peu représentatif. Le mode FP16 forcé `STRATA_BF16_TC=2` reste un candidat P100 : le chemin officiel standard élargit les projections BF16 vers FP32 sur Pascal. Ce mode avait déjà été mesuré en 0.1.41 et ne résolvait pas la régression du grand dossier.

Sources : [0.1.42](https://github.com/Niko1221/Strata/releases/tag/v0.1.42), [0.1.43](https://github.com/Niko1221/Strata/releases/tag/v0.1.43), [0.1.43.1](https://github.com/Niko1221/Strata/releases/tag/v0.1.43.1), sources du tag téléchargées dans `source/Strata-0.1.43.1`, notamment `docs/DETAILS.md`, `docs/MULTI_GPU.md`, `include/strata/artifact/gguf_reader.hpp` et `src/prefill/gemm.cu`.

## Campagne proposée

1. Mesurer la production actuelle le même jour, sous la nouvelle ventilation : prompts courts répétés, extraction exacte à environ 1 534 / 5 950 / 23 614 tokens, puis plusieurs générations consécutives pour établir le débit soutenu.
2. Mesurer 0.1.43.1 `reference` avec les mêmes fichiers IQ4_XS, deux P100 24/24, 15 workers, prefill 2048, contexte 262144, KV FP16, MTP 3/0,5, PLE direct, sans réutilisation du prompt.
3. Comparer individuellement `defaults` (tail skip 7), `fp16`, `trim`, `help`, `mtp-batch`. Ne combiner que les options qui ont effectivement gagné. Répéter les candidats gagnants et la référence dans un ordre alterné pour limiter l'effet de température et de cache disque.
4. Pour le 27B, campagne distincte avec Café : même GGUF Q4_K_M et brouillon Q4_0, contexte 4096, température 0, seed 42, thinking/cache désactivés, mêmes deux prompts historiques. Répéter tensor + MTP 2, mesurer plusieurs minutes sans pause de refroidissement, puis sans MTP. Aucun changement de quantification dans cette comparaison.

Relever toutes les 2–3 secondes, séparément pour chaque P100 : température, fréquences SM/mémoire, puissance, utilisation, VRAM et indicateurs de limitation thermique. Séparer lecture du prompt, délai jusqu'au premier texte et génération. Ne pas déduire la réussite du refroidissement des seules températures au repos : elles sont actuellement proches de 43–45 °C.

Les essais historiques 0.1.41 avaient une génération médiane +14 %, mais un délai au premier texte passant de 69,54 à 83,83 s sur le grand dossier. La campagne ventilation maximale du 10 octobre a été arrêtée à la demande de l'utilisateur pendant la référence, pour chauffe persistante ; elle ne constitue pas une comparaison complète.

Conserver les critères précédents : toutes les vérifications exactes correctes, génération au moins à 97 % de la référence, lecture au moins à 95 % de la référence pour **chaque** taille de document. Ajouter une condition de comparaison thermique valide et distinguer JSON strict / JSON récupéré dans des clôtures Markdown. Une simple réponse explicative non vide n'est pas une validation générale de qualité.

## Préparation réalisée, limites

Paquet `strata-windows-x64-cuda12.zip` vérifié SHA-256 : `19e2a210b425d31d75450795f32ecc77b5f33aa95ddbd9c0f156d2faca266fe2`. Métadonnées officielles sauvegardées dans `validation/release.json`. CUDA 12.9, architecture 60 présente dans `engine-cuda12/BUILD.json` ; exécution de la commande de version réussie avec les DLL du dossier de test précédent.

Six configurations et `Start-Test.ps1` sont préparés et vérifiés sans chargement GPU. Ils réutilisent les modèles, le tokenizer et l'environnement Python déjà présents, écoutent seulement sur 127.0.0.1:8081, et refusent de charger un second modèle lorsque Strata tourne déjà. Exemple de vérification : `./Start-Test.ps1 -Profil reference -VerifierSeulement`.

La préparation initiale n'avait effectué aucune inférence. **Les essais ont ensuite été réalisés sur les deux modèles** : voir [le rapport consolidé](mesures/20261013-092456/RAPPORT.md), avec le complément MTP 4K dans `mesures/20261013-110242`. La session réellement active du 12 octobre a été sauvegardée avant chaque interruption et reprise avec contrôle des empreintes et une réponse calculée correcte. La console a été reconnectée au moteur chargé et la relance automatique est conservée. Aucun nouveau moteur n'a été adopté en production.

Résultats courts, médianes de trois réponses avec refroidissement : Flash-Next actuel 30,1 / 33,7 tokens/s ; 0.1.43.1 profil MTP groupé demandé 35,2 / 38,9 ; 27B MTP 2 en contexte 4096 : 30,8 / 35,8 ; 27B sans MTP tensor : 18,5 / 18,5. Le profil officiel sans option a dépassé le délai de chargement avant inférence ; il n'a donc pas fourni de contrôle isolant l'effet du MTP groupé. Les profils trim, FP16, help et defaults ne sont pas mesurés dans cette campagne.

La ventilation reste limitante : sur quatre réponses consécutives de 512 tokens, le 27B MTP atteint la limitation thermique à 79 °C après environ 77 secondes ; le débit de cette autre charge passe d'environ 28 à 26 tokens/s. Ces chiffres ne doivent pas être attribués intégralement à la chauffe par comparaison avec les prompts courts, puisque le texte généré diffère ; la baisse entre les réponses de la série coïncide avec la limitation enregistrée. Le grand dossier 27B est également affecté par la chauffe. Les limites et les mesures brutes sont détaillées dans le rapport.
