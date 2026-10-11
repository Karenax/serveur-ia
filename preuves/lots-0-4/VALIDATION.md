# Livraison des cinq premiers lots — serveur Fred

Date : 10 octobre 2026. Périmètre autorisé : **lots 0, 1, 2, 3 et 4** du plan global, qui commence à 0. **Les cinq lots sont achevés, validés et mis en service.** La suite complète de **191 tests** réussit ; les sources restent identiques pendant son exécution.

## Résultats et preuves

| Lot | Résultat livré | Preuves |
| --- | --- | --- |
| 0 | Inventaire sans secrets, limites, identité de serveur et génération, extensions compatibles des API et migrations des accès | [Inventaire réel et accès préservés](production-validation.json), tests de compatibilité et de synchronisation dans la suite finale |
| 1 | Archives chiffrées complètes, manifeste, publication atomique, catalogue vérifié, anciennes archives lisibles, paquet distinct des signatures | [38 tests sauvegarde/restauration](backup-tests.log), [volume et empreintes](backup-volume.json), [11 tests signatures](signatures-tests.log), [paquet réel vérifié](signatures-recovery-verified.json) |
| 2 | Planification persistante, rattrapage, conservation 7/4/6, DPAPI, deuxième copie et reprises après erreur | [Tests isolés](backup-tests.log), [planification activée](production-validation.json), [parcours de console](console/INDEX.md) |
| 3 | Aperçu et confirmation, maintenance, point de retour, reprise après coupure, retour après panne, génération et reprise explicite des clients | [10 tests de restauration](restoration-final.log), [2 tests clients Windows](restoration-client-final.log), [restauration réelle via navigateur](console/maintenance-backend-ui.json), journaux Android ci-dessous |
| 4 | Fiches PC/téléphone/tablette, propriétaire/version/activité, profil Android direct, suspension/expiration, remplacement, archivage, révocation durable et interruption des flux | [17 tests serveur](device-tests-final.log), [32 scénarios navigateur](console/INDEX.md), [livraison des clients](client-delivery-evidence.json) |

Les comptes, documents, phrases et clés des tests sont synthétiques. Les essais de restauration utilisent un stockage jetable. La mise en service a créé des archives des données existantes et vérifié leur déchiffrement ; aucune restauration de test n’a remplacé les données réelles.

## Mise en service réelle

[production-validation.json](production-validation.json), complété par le [contrôle final des fichiers et du service](delivery-final-check.json), établit les résultats suivants :

- Console serveur **3.5.17**, binaire Windows signé par le manifeste existant et empreinte vérifiée.
- Sauvegardes automatiques activées **quotidiennement à 03 h**, heure du serveur, dans `D:\Serveur IA\lanceur\sauvegardes`, conservation **7 quotidiennes / 4 hebdomadaires / 6 mensuelles**.
- Première prochaine échéance : **11 octobre 2026 à 03 h, Europe/Paris**. L’exécution de cette échéance future n’est pas revendiquée ; le déclenchement, le rattrapage et la conservation ont été exécutés avec horloges de test.
- Archive initiale de **497 983 octets**, créée et vérifiée par relecture/déchiffrement. Le rapport conserve son chemin, sa date, son empreinte SHA-256 et les comptes du contenu.
- Processus du modèle **8200 et 14628**, mêmes dates de création avant/après, santé `loaded=true`. Les empreintes des réglages, des accès, du coffre WireGuard et de la clé Windows préexistants sont identiques.
- Deuxième destination laissée vide selon le choix du demandeur. Les essais de copie utilisent des dossiers isolés ; aucun NAS physique n’est revendiqué.
- Phrase forte dans un fichier Windows privé, secret automatique DPAPI. Leur valeur est absente des preuves. Les chemins de données privées et `.fredkeys` sont exclus de Git ; les [droits Windows vérifiés](permissions-privees.json) ne donnent aucun accès supplémentaire à ces fichiers.

Le paquet séparé `lanceur/sauvegardes/signatures-fred.fredkeys` a été exporté puis déchiffré indépendamment pour vérifier la clé Android et la graine Windows : [export](signatures-recovery-export.json), [vérification](signatures-recovery-verified.json). Son certificat Android correspond à celui de l’APK livré. Il ne s’importe pas comme une sauvegarde du serveur ; voir le [guide des signatures](../../lanceur/RECUPERATION-SIGNATURES.md).

## Console et restauration

[console/INDEX.md](console/INDEX.md) relie **32 scénarios réussis** et **15 captures relues**, dont **16 scénarios avec le vrai Controller** et la cryptographie réelle. Les empreintes des réglages, de l’historique et de l’original sont identiques après restauration ; la génération change. Une panne de retour est injectée uniquement dans le processus jetable : accès bloqués, stockage réparé, retour relancé avec succès. Aucune route de débogage n’est ajoutée au serveur livré.

Les tests Python couvrent les requêtes administratives arrivées avant la maintenance mais terminées pendant celle-ci ([preuve HTTP](admin-maintenance-concurrency.log)), la reprise sans doublon du worker après un travail web lent ([5 tests](worker-lifecycle-tests.log), [diagnostic et empreintes](worker-lifecycle-validation.json)), et la sauvegarde après restauration laissant un EXE orphelin. Un sous-ensemble intermédiaire de **70 tests** passe ([journal](worker-lifecycle-final.log)) ; les 5 tests du worker ont ensuite été rejoués sur ses sources finales. Ils couvrent également la corruption, mauvaise phrase, disque plein, manifeste invalide, échéance manquée, copie secondaire indisponible, conservation, point de retour, révocations postérieures à l’archive et serveur d’origine différente. Un processus enfant est réellement arrêté avec `os._exit(47)` après journalisation et modification ; un Controller neuf récupère l’état avant ouverture de SQLite.

## Clients livrés

| Client | Version et fichier | SHA-256 |
| --- | --- | --- |
| Windows | **3.5.17**, `client-qwen/dist/Accès serveur Fred.exe`, 25 590 937 octets | `307f5e3bcce5e31617606c56e034636026707c16d4a26ccfd1316927a4d78738` |
| Android | **1.0.1**, code **2**, `client-android/dist/Acces-serveur-Fred-Android.apk`, 8 493 381 octets | `a0cdb80a49c892f38b647aaa6d300398cac53b1eee64727636594f0fb9bf5751` |

Les clés de signature sont conservées. Certificat Android SHA-256 : `40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`.

- Windows : [construction finale](windows-3.5.17-build.log), [autotest compilé final](windows-3.5.17-selftest-compatibility.txt). Le comportement préexistant est conservé : les requêtes API de suivi ne bloquent pas la préparation de mise à jour et le client ferme après vérification ([test de compatibilité](windows-update-compatibility-final.log)). Le changement d’adresse reste refusé pendant les requêtes actives. La suite finale rejoue remplacement vérifié, profil, retour de version et démarrage sur le binaire publié.
- Android : [construction signée et 13 tests de livraison](android-1.0.1-build-final.log), [Debug, instrumentation et lint Release](android-1.0.1-debug-lint.log).
- Natifs téléphone / tablette : [stockage et reprise téléphone](lots-core-5554.log), [tablette](lots-core-5556.log), [WireGuard UDP et SSE téléphone](lots-udp-5554.log), [tablette](lots-udp-5556.log), [déclarations reçues par le serveur isolé](android-device-fixture-counts.json).
- Release Android installé séparément, code 2 et `DEBUGGABLE` absent, mode démonstration ignoré : [téléphone](lots-release-5554.log), [tablette](lots-release-5556.log), [capture téléphone](lots-release-5554.png), [capture tablette](lots-release-5556.png).

Les tests natifs utilisent les classes de production avec instrumentation Debug et des fixtures isolées. Le Release signé est installé et contrôlé séparément. Android 8+ ARM64/x86_64 ; émulateurs Android 16 x86_64 utilisés pour les essais. ARM64 physique et conversation HTTPS avec un compte autorisé restent à vérifier ; 32 bits exclu. L’ancienne validation Android 1.0.0 est conservée comme historique, distincte des résultats actuels.

## Ressources et limites mesurées

[backup-volume.json](backup-volume.json) porte sur **8 DOCX valides de 2 Mio**, soit **16 Mio d’originaux**, avec comparaison SHA-256 après restauration :

| Mesure | Résultat |
| --- | ---: |
| Archive chiffrée | 30 084 327 octets |
| Création et vérification | 1,672 s |
| Instantané sous verrous | 0,157 s |
| Restauration | 6,343 s |
| Pic mémoire du processus | 417 533 952 octets, environ 398 Mio |
| Originaux identiques | 8 / 8 |

Le format traite le contenu en mémoire. Limites explicites : document original 2 Mio, stockage par propriétaire 20 Mio, stockage global 128 Mio, SQLite restaurable 256 Mio, archive chiffrée 400 Mio, requête WireGuard 2 Mio. Le volume maximal et un NAS réel ne sont pas mesurés. La console serveur doit fonctionner pour exécuter l’échéance ; le démarrage avant ouverture de session n’est pas installé dans ces lots.

## Régression finale et reproduction

La suite complète finale est lancée avec :

```powershell
$env:PYTHONUTF8='1'
& '.\Strata-src\.venv\Scripts\python.exe' '.\lanceur\validate_maintenance.py'
```

Résultat final : **191 tests réussis, aucun échec ni erreur**, en **529,918 s** (runner : **530,562 s**). Les SHA-256 des sources avant/après sont identiques. Voir le [journal complet](regressions-final.log) et le [résultat avec empreintes](regressions-final.json). Ce passage utilise les binaires publiés et les sources finales. Les journaux des cycles ayant révélé les défauts restent des diagnostics historiques.

Le [contrôle documentaire indépendant](documentation-audit.json) confirme les liens locaux, les empreintes des binaires et captures, ainsi que la concordance des journaux et nombres de tests. Le [contrôle de livraison](delivery-final-check.json) vérifie les fichiers publiés, le manifeste, la planification et les accès préservés.

Les runners navigateur sont dans `lanceur/web/tests/`, le protocole et les chemins de Node/Python dans [console/INDEX.md](console/INDEX.md). La sauvegarde/restauration isolée se rejoue avec `lanceur/validate_backups.py`, les signatures avec `python -m unittest test_recovery_signing -v` depuis `lanceur/`. Ces commandes de test n’appliquent aucune restauration sur la production.

Pour l’usage courant : [mode d’emploi](../../lanceur/SAUVEGARDES-APPAREILS.md). Les lots 5 à 10 sont conservés dans le [plan global](../../PLAN-GLOBAL-SERVEUR-FRED.md), sans être annoncés comme livrés.
