# Architecture par défaut — 31 octobre 2026

Configuration enregistrée à la demande de l'utilisateur après la fin naturelle
de sa génération. Les anciens profils sont sauvegardés dans `avant/`.

**Profil actuel après optimisation VRAM : KV INT8, préfill 2048, cache d'experts
primaire limité à une entrée, MTP 3.** Le contexte 262144 et les quatre rôles GPU
ci-dessous sont conservés. Le [rapport d'optimisation](../optimisation-vram-20261031/README.md)
contient les comparaisons, les limites de cohabitation et la sauvegarde du profil
trois GPU FP16 précédent. `status.json` référence le service actuel vérifié.
Les réglages FP16 et mesures ci-dessous décrivent le basculement initial avant
cette optimisation.

| Carte | Rôle |
| --- | --- |
| RTX 3080 10 Gio, UUID GPU-c7ec5bca-5502-9e99-2ede-30270b7bde2f | CUDA0 : couches denses, états et MTP |
| P100 16 Gio, UUID GPU-a39f1b57-5a26-b53d-e943-44ef8042a438 | CUDA1 : experts distants |
| P100 16 Gio, UUID GPU-486d5352-582e-2880-78bf-3dec4688e142 | CUDA2 : experts distants |
| P2200 5 Gio, UUID GPU-97ca6406-8625-b829-b053-191c238ff046 | Encodeur d'image séparé |

## Réglages persistants

Moteur officiel Strata 0.1.54 CUDA 12.9, pilote NVIDIA 581.80 sur les quatre GPU.
Le moteur permanent est `F:/Kiara/moteurs/strata-0.1.54-cuda12/strata.exe` ; tous
les fichiers correspondent par SHA-256 au paquet officiel déjà vérifié pendant
les benchmarks. `engine-copy.json` conserve cette comparaison ; l'origine et
les empreintes sont dans `../latest-engine.json`. Le serveur Python corrigé et
l'encodeur P2200 existants sont conservés.

Le modèle IQ4_XS utilise ses trois shards à la racine de F:, et la table Ngram/PLE
est `F:/iq4-xs-ple-iq4_nl.gguf`, lue directement. Les packs auxiliaires et le MTP
restent sur D:.

- Contexte maximal : 262144 tokens, KV FP16.
- `--kv-resident 20480` : KV complet dans 6 Gio de RAM verrouillée, fenêtre de
  20480 cellules par couche d'attention en VRAM. Le contexte entièrement en VRAM
  échoue à allouer ses états sur la 3080 de 10 Gio.
- Réserve VRAM du GPU principal : 1600 Mio. Avec 2048 Mio et ce contexte, le
  dimensionnement automatique laisse zéro place au cache d'experts primaire,
  ce qui empêche l'activation des experts distants. L'essai à 1536 Mio réussit,
  mais déclenche un avertissement sous 1024 Mio libres ; la valeur finale suit
  la recommandation du moteur et laisse un peu plus de marge.
- `--expert-cache auto`, `--expert-cache-device1 auto`,
  `--expert-cache-device2 auto`, `--remote-expert-opt`, sans layer split.
- Préfill 2048, 15 workers CPU, MTP activé (`--spec 3`, seuil 0,5).
- Huit sauvegardes de prompt ; cache de conversation de 30720 Mio et 20 slots.
- Autochargement et reprise automatique conservés dans `lanceur/exploitation.json`.

Le lanceur accepte les deux architectures : deux GPU partagent les couches ;
avec trois GPU, le premier calcule les couches denses et les deux suivants les
experts distants. La conversion est conservée après sauvegarde/relecture et ne
réintroduit pas un layer split dans le profil à trois GPU. La P2200 reste hors
de cette liste et dispose de son UUID dans le bloc `vision`.

Les experts CPU restent verrouillés. Sur l'essai à contexte maximal, CUDA refuse
le verrouillage CUDA de leur complément (30,68 Gio à réserve 1536, environ
30,74 Gio à réserve 1600) ; le moteur utilise alors `VirtualLock`. Le garde Kiara valide ce verrouillage
Windows avant d'accepter les requêtes. Le calcul ne se rabat pas sur des experts
paginables ou lus depuis le disque.

## Validation et limites

`../rtx3080-ctx262144-defaut-262k-kv20480-res1536/` conserve la validation isolée
du profil complet, caches et vision activés : calcul 301 et reconnaissance de
VISION 47, cercle rouge, carré bleu. Les quatre cartes participent effectivement.

Après enregistrement, la console est redémarrée pour recharger le code et le
profil, puis le modèle est lancé par son API habituelle. `production-image.json`
conserve le test image sur le service géré ; `context-streaming.json` vérifie une
requête dépassant les 20480 cellules résidentes. La capacité configurée est
262144 ; ces tests ne constituent pas un stress test avec un prompt de 262144 tokens.

Les gains de +56 % en génération et environ +95 % en préfill du comparatif
initial concernent le contexte 8192 sans cache de prompt. Ils ne sont pas une
mesure de débit de ce profil à grand contexte et KV partiellement en RAM.

Le lanceur passe neuf tests, dont le roundtrip du profil trois GPU et le retour
au profil deux GPU. La console affiche les quatre cartes ; l'affichage a été
vérifié à 1280 et 390 pixels. Les trois avertissements ux:check concernent des
paragraphes préexistants non modifiés.

Validation finale du service géré à réserve 1600 : image reconnue correctement
en 4,968 s ; prompt de 27646 tokens traité en 48,454 s avec restitution correcte
de JARDIN-5832 et zéro token de cache réutilisé. Le journal confirme 31479 Mio
d'experts verrouillés par VirtualLock, 1145 Mio de VRAM libres après chargement
et aucun avertissement de faible VRAM durant cette validation. La session finale
est `lanceur/sessions/20261031-101051-123863`, état `pret`. `status.json` conserve
les empreintes des profils, la cohérence des réglages et l'autochargement actif.
Les rapports de l'essai précédent à réserve 1536 sont dans `validation-res1536/`.

## Retour au profil précédent

Quand le modèle est inactif, l'arrêter depuis la console. Restaurer depuis `avant/`
les deux profils de base et les fichiers de réglages courants, par défaut et
derniers valides, puis redémarrer la console et relancer le modèle. Ne pas
restaurer le pointeur de session historique ni ses PID. Le code du lanceur reste
compatible avec l'ancien profil à deux P100 et le moteur 0.1.45.3 est conservé.
