# Validation de la mémoire EG2 — 11 octobre 2026

**Installée, activée et vérifiée sur le serveur Fred.** EG2 fonctionne dans un processus CPU indépendant de Qwen/Strata. Les données et identités actuelles sont conservées ; aucun nouveau binaire client n’est nécessaire pour l’ajout de contexte et le retour des sources.

## Contrôles

| Contrôle | Résultat | Preuve |
| --- | --- | --- |
| Régression complète pendant le développement | 257 tests réussis en 513,054 s | [Journal](regression.txt) |
| Contrôles ciblés après les derniers ajustements | 12 tests mémoire, 10 restauration, 5 contrôle des sources pendant le flux ; 2 tests de transport du chat | [Tests mémoire](../../lanceur/test_knowledge.py), [transport](../../lanceur/test_knowledge_transport.py) |
| Vrai modèle EG2 hors ligne, CPU | Six reformulations françaises : passage attendu classé premier à chaque fois ; séparation des bases ; contexte exact ; arrêt du processus ; repli lexical | [Mesures](real-model.json) |
| Console dans Chrome, données synthétiques | Huit scénarios réussis, aucune erreur JavaScript : navigation, activation, souvenir personnel, recherche isolée, arrêt et contrôle du jeton | [Résultats](console-validation.json), [capture](console-memoire.png) |
| Mise en service | Moteur prêt ; 36 passages hors projet indexés, aucun passage en attente, aucun plafond atteint | [État réel](production-validation.json) |
| Conservation de l’existant | PID/création des processus Qwen identiques ; empreintes des historiques/projets/documents/souvenirs/tâches inchangées ; accès, réglages et programmation des sauvegardes identiques | [Comparaison](production-validation.json) |
| Sauvegardes | Archives chiffrées vérifiées avant et après ; souvenirs personnels et exclusions inclus dans la base originale | [Archives et inventaires](production-validation.json) |

Le passage complet de régression précède quelques ajustements finaux ; ces ajustements sont couverts par les contrôles ciblés puis les essais de modèle et de console. Les tests utilisent des identités et textes synthétiques. La production a uniquement été lue pour constater ses données et calculer leurs empreintes ; aucun projet ou souvenir de test n’y a été ajouté et aucune restauration destructive n’y a été exécutée.

## Isolation et cycle de vie

Le filtrage par propriétaire et projet précède le classement. Les sources sont revérifiées dans la base originale : documents modifiés/supprimés, conversation déplacée/archivée/supprimée, identité étrangère et projet inexistant ne sont pas rappelés. Une discussion supprimée sur le serveur ne revient pas depuis une copie ancienne de l’historique client. Réflexions internes et réponses interrompues sont exclues. L’indexation incrémentale réutilise les vecteurs des anciens messages inchangés.

Les souvenirs personnels entrent dans les quotas et dans la sauvegarde. Les anciens schémas sont migrés et les références du cache sont réinitialisées après restauration. La désactivation EG2 conserve la recherche lexicale et la génération ; les tests HTTP vérifient que les sources et le contexte de mémoire arrivent via le contrat de chat existant.

## Mesures et portée

Modèle officiel `google/embeddinggemma-2`, révision `914f7f89142e33e77833254d9c9b90c3cef7303b`, texte uniquement. Sentence Transformers 6.1.0, Transformers 5.19.0, PyTorch 2.14.1 ; environnement isolé et vérification des dépendances réussie. Float32, vecteurs normalisés de 768 dimensions, deux threads CPU, 271 002 624 paramètres actifs.

Sur les huit courts passages synthétiques : chargement d’environ 14 s, huit passages indexés en 0,75 s, RAM du véritable processus autour de 1,63 Gio. La latence des passages longs en production est supérieure. Le budget logique du cache est 64 Mio, avec 16 000 passages globalement et 4 000 par accès ; ces plafonds n’ont pas été éprouvés à volume maximal. Les sauvegardes et les données restent locales et privées. L’impact sur le débit d’une génération Qwen simultanée n’a pas été mesuré.

Guide d’exploitation : [Mémoire et connaissances](../../lanceur/MEMOIRE-EG2.md).
