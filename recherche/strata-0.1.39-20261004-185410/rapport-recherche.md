Essais Strata sur 2 Tesla P100 et Threadripper PRO 3955WX

Rapport genere le 2026-10-04T21:12:51.382459+02:00.

Meme modele IQ4_XS, memes trois fragments GGUF lus depuis C:\Temp, meme tokenizer et meme MTP. Contexte configure a 262 144 tokens. Les entrees mesurees font 26 a 46 tokens : ces chiffres ne mesurent pas le traitement d'un prompt de 262 144 tokens.

Un passage de chauffe puis deux repetitions par sujet, temperature 0, graine 42, cache de prompt desactive. Les valeurs sont les medianes de generation en tokens/s. Le nombre de tokens de sortie varie pour la poesie ; il est conserve dans les mesures.

| Mode | Ciel | Fibonacci | Poesie | RSS moteur (Gio) | RSS table externe (Gio) | RAM machine utilisee (Gio) |
|---|---:|---:|---:|---:|---:|---:|
| 0.1.35 + notre hybride | 29,1 | 34,9 | 27,7 | 77,1 | 0,0 | 93,5 |
| 0.1.39 Git, experts mmap | 12,5 | 9,1 | 17,1 | 55,9 | 26,9 | 98,9 |
| 0.1.39 Git, tous les experts RAM, reserve 2 Go | 29,9 | 34,7 | 27,1 | 63,4 | 26,8 | 105,4 |
| 0.1.39 + notre hybride | 29,6 | 35,3 | 26,6 | 77,1 | 0,0 | 93,6 |

La table ngram/PLE de 26,822 Gio a ete entierement verrouillee en RAM pendant les inferences. Pour le code Git intact, un processus externe tient les pages partagees du meme GGUF avec VirtualLock ; QueryWorkingSetEx a verifie 7 031 284 pages verrouillees. Strata lit ces pages avec son option standard --ple-io mmap. Pour nos deux modes hybrides, le moteur assure lui-meme le verrouillage Windows avec --ple-io ram.

Ne pas additionner les deux colonnes RSS comme une mesure exacte de RAM physique : les deux processus partagent certaines pages. La colonne RAM machine vient directement de Windows et inclut le systeme et les autres applications. Les maxima concernent les repetitions mesurees.

Le code Git est le tag [v0.1.39](https://github.com/Niko1221/Strata/releases/tag/v0.1.39), commit 6f32ec070f23ced9f50e704d854d775da52591ab, sans modification de source. Le mode officiel qui charge tous les experts a d'abord ete essaye avec les reglages automatiques : 5 des 6 mesures ont termine, puis le moteur a manque de VRAM en creant un graphe CUDA. La serie exploitable est une nouvelle execution avec l'option officielle --vram-reserve-mib 2048. Les autres options automatiques restent celles de Git.

Notre variante conserve le partage 24/24 couches, les experts manquants calcules sur le CPU en RAM, la reserve GPU de 2 048 MiB, le prefill 256, sans emprunt de cache, pcie-frac 0, adapt-every 0, spec 3 / spec-min-p 0.5 et 15 travailleurs CPU. Elle conserve les chemins AVX2 amont et notre conversion BF16 vers FP16 pour le prefill P100. Le patch integral est adaptations-v0.1.39.patch.

| Mode | VRAM P100 1 / 2 (Gio) | Temperature max 1 / 2 (C) | Masques de ralentissement |
|---|---:|---:|---|
| 0.1.35 + notre hybride | 14,7 / 14,9 | 54 / 60 | {'0': [0], '1': [0]} |
| 0.1.39 Git, experts mmap | 15,8 / 15,9 | 54 / 59 | {'0': [0], '1': [0]} |
| 0.1.39 Git, tous les experts RAM, reserve 2 Go | 14,5 / 14,6 | 57 / 64 | {'0': [0], '1': [0]} |
| 0.1.39 + notre hybride | 14,7 / 14,9 | 55 / 60 | {'0': [0], '1': [0]} |

Variation du nouveau mode hybride par rapport au moteur precedent, au meme contexte : ciel +1.7%, fibonacci +1.1%, fourmis -3.9%.

Ces ecarts ne montrent pas de gain decisif sur nos trois requetes courtes. Le mode Git avec tous les experts en RAM atteint des vitesses proches, en occupant environ 12 Gio de plus sur la machine. Les nouveaux chemins de prefill long et les requetes paralleles ne sont pas evalues dans cette serie.

Verification physique de la table privee (adapte) apres les mesures : 7031284 pages presentes et 7031284 pages verrouillees sur 7031284. 

Verification physique de la table privee (reference-production) apres les mesures : 7031284 pages presentes et 7031284 pages verrouillees sur 7031284. 

Production retablie et validee sur le moteur original : contexte 262 144, historique 6 emplacements, port 8080, interface sur 8765. Les empreintes du moteur et des fichiers de reglages correspondent aux sauvegardes initiales.

Table ngram de production verifiee apres remise en service : 7031284 pages verrouillees sur 7031284.

Les sorties texte, requetes, reponses JSON, journaux par requete et telemetrie CPU/RAM/GPU sont conserves dans chaque sous-dossier mesures. Les essais interrompus ou echoues sont conserves mais exclus des medianes ci-dessus. Aucun de ces essais ne remplace le moteur ou les parametres de production.

Reference Windows : https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtuallock
Version amont : https://github.com/Niko1221/Strata/releases/tag/v0.1.39
P100 experimental : https://github.com/Niko1221/Strata/blob/v0.1.39/docs/OLDER_GPUS.md
