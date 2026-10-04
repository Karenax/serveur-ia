# Essai du mode normal : table ngram sur SSD C

Date : 2026-10-04T20:31:33.698360+00:00. Moteur 0.1.35 avec notre hybride P100, IQ4_XS, contexte 262 144, 15 workers, prefill 256, reserve VRAM 2 048 Mio, MTP actif.

Seule la table PLE passe de `--ple-io ram` a `--ple-io direct`, avec un chemin explicite vers C. Le binaire et les parametres de production sont conserves. Les checkpoints de conversation sont desactives pendant les deux benchmarks pour eviter la reutilisation du prompt.

| Sujet | Table RAM, tok/s | Table SSD, tok/s | Ecart |
|---|---:|---:|---:|
| Ciel | 29.07 | 29.18 | +0.4% |
| Fibonacci | 34.93 | 35.11 | +0.5% |
| Poesie fourmis | 27.68 | 27.78 | +0.4% |

Vitesses medianes de deux passages apres un passage de chauffe par sujet. Les reponses, temps, telemetries et journaux sont conserves dans `mesures`.

Les six reponses mesurees sont identiques a la reference RAM (SHA-256 du texte identique).

RAM du moteur au pic : **77.09 Gio en mode RAM, 50.32 Gio en mode SSD**, soit **26.77 Gio liberes**. RAM totale machine : 93.50 contre 67.44 Gio ; cette mesure depend aussi de Windows et des autres applications.

| Sujet | Premier passage RAM, tok/s | Premier passage SSD, tok/s | Lectures moteur premier passage SSD, Mio | Lectures passages repetes SSD, Mio |
|---|---:|---:|---:|---:|
| Ciel | 28.24 | 28.57 | 20.23 | 6.00, 0.36 |
| Fibonacci | 34.94 | 34.51 | 16.66 | 0.31, 0.31 |
| Poesie fourmis | 27.67 | 27.34 | 31.14 | 0.59, 0.59 |

Les lectures Windows incluent le pipe de commande et les lectures de maintien du SSD eveille. Les journaux confirment zero lecture de fichier pour les experts : ils restent en RAM ou en VRAM. Le premier passage de chaque sujet comporte les lignes ngram encore absentes du cache ; les sujets peuvent partager certaines lignes.

Le cache de lignes du mode direct reste actif, comme prevu par le moteur : 1 048 576 lignes, environ 94,1 Mio avec les cles, pour une table de 26,82 Gio. Les passages repetes peuvent largement reutiliser ces lignes. Ces trois prompts courts ne representent donc pas toutes les latences possibles sur du texte toujours nouveau ou un tres long contexte.

Verification : copie brute IQ4_NL, formes et nombre d'octets identiques, SHA-256 complet identique entre table originale et copie. Le lecteur utilise `FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED | FILE_FLAG_RANDOM_ACCESS` sur C. Inspection de la memoire : aucune allocation privee de la taille de la table complete.

VRAM au pic : 14.73 / 14.87 Gio. Temperatures maximales : 53 / 59 C. Masques de limitation des frequences : {'0': [0], '1': [0]}.

Production : retablie et prete, table en RAM, historique 6 et contexte 262 144. Empreintes des fichiers de production conserves : toutes identiques.

Verification physique de la table de production : 7,031,284 pages presentes et 7,031,284 pages verrouillees sur 7,031,284.

Copie de recherche de la table : `C:\Temp\Strata-ngram-recherche\iq4-xs-ple-iq4_nl.gguf` (26.82 Gio). Elle reste disponible pour reproduire le test ; le profil de production utilise sa table originale en RAM.
