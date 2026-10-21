# Strata 0.2.0-beta : éléments utiles pour Fred

Les essais réels demandés après cette analyse sont consignés dans [RESULTATS.md](RESULTATS.md). Le moteur 0.1.43.1 a été remis en production à leur issue.

Analyse du 19 octobre 2026. Aucun redémarrage, installation ou changement de configuration de production.

## Périmètre et preuves

- Dépôt : https://github.com/Niko1221/Strata
- Publication : https://github.com/Niko1221/Strata/releases/tag/v0.2.0-beta, publiée le 19 octobre à 15 h 52, heure de Paris.
- Tag analysé : commit `3d1fb48090e8f2cefc22d7b5845fb7f5b71f33fa`, moteur 0.1.45.3.
- Main observée : `3fa1b524d7700206c5267a6b64926021b0963dc8`. Les 17 fichiers différents du tag portent sur documentation, images et moniteur portable/tests ; le parseur serve/frontend.py est identique.
- Référence locale : distribution 0.1.43.1 avec correctifs Fred, profil IQ4_XS, deux P100 visibles pour le moteur texte, vision séparée P2200.
- Sources téléchargées dans source/. Notes officielles des versions conservées à côté de ce rapport.

## Priorités de reprise

### 1. Évaluer le moteur CUDA 12 et ses réglages P100

Le nouveau moteur applique sept réglages quand toutes les cartes visibles sont sm_60 : ADAPT_NOWAIT=1, ADAPT_LAG=2, SIDE_MIXER=2, FUSE_WAIT=2, B6_MMVQ_ROWS=1, FUSE_DECODE=1 et GR_UP75=1 (préfixe STRATA_). Une valeur utilisateur explicite reste prioritaire. Le code vérifie les cartes visibles dans src/program/generate.cpp, puis applique src/core/nv_defaults.cpp.

Les auteurs mesurent 36,56 -> 41,76 tokens/s (+14,2 %, huit paires) sur une P100 16 Go avec IQ3_XXS et indiquent des sorties identiques dans leurs tests. Ce chiffre ne mesure ni notre IQ4_XS, ni notre split à deux P100, ni notre profil qui désactive l'adaptation. Aucun gain local n'est établi. STRATA_SM60_PERF=0 fournit le témoin de comparaison.

Conserver CUDA 12 : CUDA 13 ne cible plus Pascal. Notre masque CUDA_VISIBLE_DEVICES limite déjà le moteur texte aux deux P100 ; conserver cette séparation avec la P2200.

### 2. Conserver et porter les correctifs locaux des outils

Les modules locaux serve/test_tool_boolean_types.py et serve/test_tool_hybrid_arguments.py ont été copiés dans la seule copie de recherche puis exécutés avec unittest, sans moteur réel, sur les parseurs et les serveurs HTTP simulés des tests.

- Référence corrigée : 19 tests, OK (regressions-reference.log).
- Nouveau tag officiel : 19 tests, 76 échecs en comptant les sous-cas (regressions-outils.log).
- Défauts couverts : booléens textuels, enveloppes XML contenant du JSON et des délimiteurs littéraux, validation des clés obligatoires avant émission des appels, streaming et sérialisation OpenAI/Anthropic.
- git apply --check échoue pour les deux patchs du 16 octobre : adaptation manuelle nécessaire au nouveau frontend.

Ces échecs portent sur les exigences particulières vérifiées par nos tests ; ils ne signifient pas que tous les appels d'outils amont échouent. Ils suffisent à écarter un remplacement intégral sans portage.

### 3. Reprendre les corrections cache/images et API

Depuis 0.1.44, l'identité d'une image dans l'historique repose sur son hash et sa grille plutôt que ses embeddings flottants, pour éviter de perdre le cache de conversation ; confirmation dans serve/server.py, notamment autour de la ligne 4407. Pertinent pour Fred avec images et alternance de conversations. À vérifier réellement après intégration.

Les notes 0.1.44.1 et 0.1.45 corrigent reasoning_effort sur Responses et le sens explicite de false ; la lecture du paramètre configuré apparaît dans serve/responses.py. À couvrir sur chaque route utilisée par Fred, surtout pour la voix et le correcteur sans réflexion.

0.1.45 corrige aussi la compatibilité des GGUF Uncensored dont attention.compress_ratios est entièrement nul. Utile à conserver avec notre famille de fichiers, sans prétendre que notre modèle actuel souffre de ce défaut.

### 4. Étudier les mises à jour vérifiées comme amélioration du lanceur

Le dépôt introduit des paquets moteur indépendants, un flux de mise à jour signé Ed25519, vérification des fichiers, test de démarrage avant bascule et retour arrière. Modèle intéressant pour les futures mises à jour Fred ; l'adoption exige de gérer séparément nos correctifs Python locaux.

Le nouvel agent de bureau, le terminal et leurs connecteurs recouvrent plusieurs fonctions déjà assurées par Fred/Hermes. Pas de besoin établi de les installer pour obtenir les corrections moteur/serveur.

## Points à garder explicites

- Vision : le nouvel automatisme préfère le CPU pour une carte de moins de 24 Go. Notre encodeur est déjà isolé sur la P2200 ; préserver son exécutable CUDA 12.4, son UUID et ses 1024 tokens plutôt que régénérer aveuglément la configuration.
- Conversations : préserver 20 emplacements / 30720 Mio, réserve RAM 6144 Mio, contexte et fichiers de modèles.
- Concurrence : les chiffres élevés de débit concernent d'autres modèles/cartes ou des experts entièrement en VRAM. Aucun motif de modifier immédiatement parallel sur notre installation.
- Les gains de lecture SSD/page cache Linux ne se transposent pas à Windows et au HDD D:.
- STRATA_Q8_SM60=1 ajoute des copies Q8 en VRAM et change l'ordre numérique : expérience distincte, pas un réglage gratuit pour notre profil.
- Le dépôt documente STRATA_STAGE_PIN comme expérimental avec un cas de corruption, et STRATA_SLOT_CKPT_MOVE comme faisant échouer un test de réutilisation : ne pas les intégrer au profil de référence.

## Proposition

Préparer une distribution 0.1.45.3 CUDA 12 séparée, porter les deux correctifs d'outils puis refaire les tests ciblés et la suite serveur. Ensuite seulement programmer un essai réel contre 0.1.43.1 : mêmes fichiers, prompts, paramètres, split et conditions thermiques ; mesurer préfill, décodage, retours sur conversations et images, sans supposer le gain annoncé par l'amont. La bascule et le rechargement du modèle ne font pas partie de cette analyse.
