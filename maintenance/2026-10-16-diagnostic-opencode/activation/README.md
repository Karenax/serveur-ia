# Cache de plusieurs conversations — activé et mesuré

Le 16 octobre 2026, le cache de conversations Strata 0.1.43.1 a été activé sur les deux Tesla P100, avec le plafond demandé de **30 Gio (30 720 Mio)** et quatre emplacements de conversations sauvegardées. La réserve minimale avant sauvegarde/restauration est de 6 Gio de RAM disponible. Le plafond concerne le cache de conversations, pas toute la RAM du moteur et des experts.

Les deux profils persistants, `lanceur/base-strata.json` et `strata-iq4-p100-hybride.json`, portent ces options. Les réglages de contexte, préfill, MTP, experts et checkpoints n'ont pas été changés. Le lanceur conserve les options du profil de base lors des prochains démarrages. Les profils antérieurs sont sauvegardés dans ce dossier.

## Mesures réelles

Les requêtes passent directement par l'API Strata de production. Trois conversations synthétiques distinctes sont alternées : A, continuation de référence A, B, C, retour à A, puis continuations de B et C. Les réponses demandées sont volontairement très courtes pour isoler le coût de lecture et de restauration du contexte.

| Taille du contexte | Lecture initiale complète, réponse incluse | Retour après alternance, réponse incluse | Tokens réutilisés au retour |
| --- | --- | --- | --- |
| Environ 8 k tokens | 22,69 à 29,30 s | 1,02 à 1,99 s | 99,64 à 99,92 % |
| Environ 32–33 k tokens | 95,09 à 136,84 s | 1,17 à 2,05 s | 99,91 à 99,98 % |

Sur le test long :

- A : 33 109 tokens réutilisés sur 33 116 ; seulement 7 tokens relus.
- B : 31 967 sur 31 996 ; 29 tokens relus.
- C : 32 527 sur 32 556 ; 29 tokens relus.
- La réponse A est identique à la réponse de référence obtenue avant l'alternance. B et C retrouvent leurs sujets respectifs (« Navigation », « Rubrique botanique »), sans mélange des dossiers.
- Cache occupé à la fin : **5,66 Gio**, comprenant aussi des états du premier test ; plafond configuré : 30 Gio.
- Minimum de RAM disponible échantillonné chaque seconde pendant le test long : **55,09 Gio** ; dernière vérification : **54,93 Gio**.
- Six restaurations réussies sur les deux essais. Deux évictions d'anciens états lors du passage au test long, par limite d'emplacements. Aucune limite de 30 Gio n'a été atteinte ; le remplissage jusqu'au plafond n'a pas été testé.

Ces mesures vérifient la conservation effective des contextes après alternance. Elles ne constituent pas un nouveau chronométrage de l'audit OpenCode entier, ni une promesse d'égaler DeepSeek en trois minutes. Les changements du début des messages et l'éviction d'une conversation peuvent encore imposer une relecture.

Preuves : [petit test](mesures.json), [test long](charge-32k/mesures.json), [état final](verification-finale.json). Les JSON contiennent les compteurs moteur, les durées, les réponses synthétiques et les relevés RAM ; aucun historique utilisateur n'y est recopié. Les métriques globales contiennent aussi l'appel de validation CUDA.

## Chargement et protection RAM

Le redémarrage a été effectué par la console propriétaire. Chargement et validation terminés en **792,8 secondes** (13 min 13 s). Une vérification par empreintes confirme la conservation des configurations d'accès, WireGuard, fournisseurs Hermes et démarrage/sauvegardes.

Un défaut de détection de processus a été corrigé dans `lanceur/startup_memory.py` : le serveur Python réel peut être un descendant du lanceur `.venv`, à cause du redirecteur Windows. La recherche parcourt maintenant les descendants et vérifie l'appartenance du moteur avant et après la relecture de son identité. Le chemin exact du moteur, son heure de création et l'identité du serveur restent contrôlés. Huit tests passent, dont les cas de redirecteur et de PID d'ancêtre réutilisé.

La réduction ponctuelle des pages du seul moteur en cours de chargement a fait passer la RAM disponible de 17,36 à 64,02 Gio. Elle n'est pas périodique et n'a pas été exécutée pendant les tests d'inférence. Le superviseur actif avait déjà importé l'ancienne fonction : l'intervention unique corrigée est donc enregistrée séparément dans `reduction-pages-chargement.json`, et l'ancien champ `startup_memory_reclaim` du journal de démarrage indique encore le premier essai ignoré.

À la fin : moteur chargé, file vide, images actives, Hermes, passerelle et WireGuard disponibles.

## Reproduction

Depuis la racine du projet, utiliser le Python du projet :

```powershell
& './Strata-src/.venv/Scripts/python.exe' maintenance/2026-10-16-diagnostic-opencode/mesurer_cache.py
& './Strata-src/.venv/Scripts/python.exe' maintenance/2026-10-16-diagnostic-opencode/mesurer_cache.py --large
```

Les scripts refusent d'écraser les mesures existantes. Archiver les résultats précédents avant un nouvel essai. `activer_cache.py` conserve aussi ses preuves et refuse une nouvelle activation aveugle ; il ne doit pas être relancé pour simplement refaire des mesures.
