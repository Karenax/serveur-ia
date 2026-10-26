# Essai Bolt sur CPU — interrompu à la demande de l’utilisateur

Les deux modèles ont été téléchargés dans `D:/modèle` et vérifiés par SHA-256.
Les références, révisions et empreintes sont conservées dans `downloads.json`.
Le moteur CPU dédié est llama.cpp b11854 (8e5a58df8), sous
`toolchain/llama-bolt-b11854-cpu`. Aucun changement de configuration Kiara.

Les tests CPU ont été arrêtés à la demande de l’utilisateur, ainsi que le serveur
de test sur le port local 8099. Aucun serveur Bolt n’est laissé chargé. Les
processus Qwen 24820 et vision 8764 sont conservés. Voir `stopped.json`.

## Mesures conservées

Threadripper PRO 3955WX, 16 threads, CPU uniquement, contexte 8192, chargement en
RAM sans lecture paresseuse. Modèle réchauffé, cache de prompt désactivé.
Les trois prompts fictifs contiennent réellement 281, 907 et 3437 tokens ; deux
répétitions et 128 tokens générés par demande, EOS ignoré pour ces mesures fixes.
Ces sorties forcées ne sont pas des conversations ordinaires.

Sans DFlash : environ 100–109 tokens/s de préremplissage et 14,8–15,5 tokens/s
de génération. Le prompt de 907 tokens demande 8,51 s de préremplissage. Deux
questions courtes de 63/76 tokens commencent en 0,89/0,99 s et se terminent en
2,19/2,34 s. La mémoire de travail observée atteint environ 5,58 Gio.

Avec DFlash : compatibilité du Q4 XL confirmée sur les premiers essais. Le débit
varie selon le prompt : environ 19 tokens/s sur 281 tokens d’entrée, mais le
premier essai à 907 tokens descend à 12,2 tokens/s. Le préremplissage reste autour
de 100–107 tokens/s. La suite DFlash est partielle et ne constitue pas une mesure
complète sur les trois tailles. Aucun gain général ne peut être conclu.

`results.json` / `results.csv` résument uniquement les demandes terminées et
enregistrées. Les JSON par variante et les logs conservent les détails.
Le contrôle `maintenance/check_sources.py` a réussi pendant la préparation.

Limites : pas de microphone, reconnaissance vocale, synthèse, transport client,
mémoire Kiara ni décision de recherche dans ces chronométrages. Aucune nouvelle
mesure Qwen n’a été lancée ; ses performances historiques ne sont pas un essai
comparatif contrôlé avec les mêmes prompts.
