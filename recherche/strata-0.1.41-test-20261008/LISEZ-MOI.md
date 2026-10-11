# Version de test Strata 0.1.41 pour nos deux P100

Version préparée et testée le 8 octobre 2026 dans un dossier indépendant. **Les deux variantes 0.1.41 testées sont refusées pour la production** : génération plus rapide, mais lecture du grand document plus lente. Voir [RESULTATS.md](RESULTATS.md) et les mesures brutes. Le moteur actuel 0.1.35 est repris sur le port 8080 après les essais ; sa vérification finale figure dans `validation/production-retablie.json`.

Le paquet officiel `strata-windows-x64-cuda12.zip` de 0.1.41 est vérifié par SHA-256 : `646ded0105aa5213a75e16621d559670d09dac26b5c720c9fd651ca83bdf14ec`. `BUILD.json` confirme CUDA 12.9 et l'architecture sm_60. Les DLL NVIDIA 12.9 et les dépendances Python sont installées uniquement dans `.venv/` de ce dossier ; aucune installation du pilote ni modification de l'environnement de production.

Les sources du serveur sont le tag 0.1.41, commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`. Le moteur est le binaire officiel, sans réapplication de notre ancien patch. Le modèle IQ4_XS, les experts MTP et la table PLE sur SSD sont réutilisés depuis leurs chemins actuels, sans conversion. Une copie locale du tokenizer et du profil des experts accompagne le test.

| Profil | Réglage |
|---|---|
| `reference` | Hybride officiel : deux P100, partage 24/24, misses sur CPU, 15 workers, prefill 2 048, contexte 262 144, réserve GPU 2 048 Mio, MTP 3 / 0,5, PLE direct sur SSD. Checkpoints 8 / 160 000 ; parking de conversations désactivé comme dans les métriques de production. |
| `trim` | Même configuration, avec `--trim-stage-weights` pour charger les poids denses des seules couches de chaque carte. |
| `pipeline` | Même configuration que `reference`, avec `--pipeline-windows 2`. Sans `trim`, pour mesurer une seule modification. |
| `benchmark` | Même configuration que `reference`, avec le cache de prompt désactivé pour éviter sa réutilisation pendant les mesures. |
| `fp16` | Même configuration que `reference`, avec `STRATA_BF16_TC=2` et `STRATA_PREFILL_BF16X2=0` pour tester le chemin FP16 déjà présent dans le moteur officiel. |

Tous les profils écoutent seulement sur **127.0.0.1:8081**, avec leurs propres journaux. Les variables de notre ancien patch P100 sont retirées. L'aide CPU au prefill est explicitement désactivée pour commencer par une référence comparable ; le calcul des experts manquants sur CPU pendant la génération reste actif via `--pcie-frac 0`.

Le mode officiel `--resident-cpu-experts` demande le complément entier en RAM, mais ne lui applique pas seul le verrouillage strict de notre patch. Les métriques des essais montrent zéro blob expert lu sur disque pendant les requêtes. Le moteur officiel utilise FP32 pour ses projections BF16 sur P100, alors que notre variante utilise FP16 ; le profil `fp16` a aussi été mesuré.

Pour vérifier les fichiers, le moteur et le tokenizer sans démarrer le serveur :

```powershell
& 'D:\Serveur IA\recherche\strata-0.1.41-test-20261008\Start-Test.ps1' -VerifierSeulement
```

Pour un futur lancement lorsque les cartes et la RAM seront disponibles :

```powershell
& 'D:\Serveur IA\recherche\strata-0.1.41-test-20261008\Start-Test.ps1' -Profil reference
```

Le script `Start-Test.ps1` **n'arrête jamais le serveur actuel**. Il refuse de lancer le test si le moteur de production fonctionne, si le port 8081 est occupé, si une P100 dispose de moins de 14 000 Mio de VRAM libre, ou si moins de 65 Gio de RAM sont disponibles. Changer de port ne rend pas possible un second chargement du modèle complet sur ces deux cartes. `Piloter-Essai.py` effectue, lui, un arrêt temporaire autorisé de la production et sa reprise automatique en fin d'essai. Il exige une référence complète, utilise des dossiers de mesures neufs, et ne doit pas être relancé sans préparer une nouvelle campagne.

Pour arrêter uniquement un serveur démarré par ce lanceur :

```powershell
& 'D:\Serveur IA\recherche\strata-0.1.41-test-20261008\Stop-Test.ps1'
```

L'arrêt vérifie que le PID enregistré utilise bien la configuration de ce dossier, puis limite l'action à ce processus et ses descendants.

Validation : le paquet, l'exécution de `strata.exe --version`, les cinq profils, les chemins du modèle et la compatibilité du tokenizer sont vérifiés par `Verifier-Test.py`. Le refus de lancement pendant le fonctionnement de la production est testé. Les résultats des 51 tests Python du serveur sont dans `validation/tests-serveur.txt`. `validation/production-apres.json` concerne uniquement la préparation ; la reprise après inférence est contrôlée dans `validation/production-retablie.json`.

**L'inférence sur GPU a été mesurée** : neuf requêtes par profil après une chauffe pour notre moteur actuel, la version officielle et le profil FP16. Calculs et extraction de code : sept vérifications exactes réussies par profil. Les deux réponses explicatives servent à mesurer le débit, pas à établir une qualité générale. `trim` et `pipeline` restent des pistes non mesurées. Les fichiers du moteur et les réglages de production sont comparés à leurs empreintes d'avant l'essai.
