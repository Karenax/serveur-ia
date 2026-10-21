# Correctifs de l’audit — 21 octobre 2026

L’utilisateur a autorisé les corrections et choisi `\\DS218\home\Sauvegarde\Serveur IA` comme destination indépendante. Ce dossier conserve les scripts, journaux et preuves de l’intervention. Les versions livrées sont **serveur/Windows 3.5.31** et **Android 1.0.12, code 13**. Le résultat de mise en service est attesté par `production-apres.json` ; les empreintes des paquets figurent dans `artefacts.json` et `publication.json`.

## Corrections apportées

| Point de l’audit | Traitement |
| --- | --- |
| A01 — permissions locales | ACL du projet limitées au compte Windows propriétaire, SYSTEM et Administrateurs. Console réservée au même compte Windows par vérification du propriétaire du socket TCP avant lecture HTTP. Identité introuvable ou autre compte : refus 403. |
| A02 — certificats racines | Certifi 2026.10.19 installé dans les runtimes concernés. |
| A03 — dépendances | pypdf 6.19.0, Pillow 13.0.0 et autres versions corrigées installés ; runtime Hermes privé créé pour Fred avec dépendances compatibles. Vérification OSV des versions effectivement résolues. |
| A04 — sauvegarde indépendante | Seconde copie chiffrée activée sur le NAS fourni ; archive copiée et restaurée dans un répertoire privé isolé. Archive chiffrée séparée des clés de signature Windows/Android copiée sur le NAS. Aucune rotation des clés. |
| A05 — ressources Android | Assets régénérés depuis les sources courantes, vérifiés et embarqués dans l’APK signé. |
| A06 — worker EG2 | Serveur HTTP borné à huit requêtes simultanées, délai de lecture de quinze secondes et corps JSON limité à 64 Kio. Régression testée par connexion incomplète, saturation et récupération de capacité. |
| A07 — reconstruction | Cinq verrous de versions transitives avec empreintes SHA-256 des distributions PyPI et vérification de concordance des runtimes. Inventaires de construction corrigés pour tenir compte de la résolution réelle des paquets locaux avant les paquets hérités. Sources privées Hermes conservées sous forme de patch avec commit de base. |
| A08 — documentation | README, contexte de reprise et reconstruction actualisés ; Strata de production 0.1.45.3 documenté avec son serveur Python corrigé distinct. |
| A09 — scripts historiques | **Erratum : les deux scripts étaient syntaxiquement valides pour Python.** Ruff interprétait mal une affectation `match=` précédée d’un point-virgule. Séparation des instructions, retrait d’un import inutilisé et ajout de ces deux scripts au contrôle syntaxique. Le rapport d’audit a été corrigé. |

Les modifications préexistantes du 19 octobre et les paramètres utilisateur sont préservés. Les binaires de moteur, poids et paramètres du modèle ne sont pas remplacés par cette intervention. Les changements restent consultables sur la branche locale `codex/correctifs-audit-20261021`, sans commit ni publication distante ; l’arbre de travail conserve aussi les travaux antérieurs. Les verrous et empreintes de construction améliorent la traçabilité, mais une référence Git unique de l’ensemble de cet arbre reste à constituer après revue des travaux préexistants. Les archives de travail, téléchargements tiers et clés privées ne sont pas ajoutés au suivi Git par cette intervention.

## Dépendances et Hermes

`dependances/verrous/` contient les cinq fichiers de versions et empreintes ainsi que leur manifeste. `maintenance/verrous_runtime.py check` compare les environnements installés aux verrous. Le runtime principal hérite de paquets du poste : les versions retenues sont celles résolues par Python, et non une occurrence homonyme masquée dans un autre `site-packages`. Les outils globaux de Codex n’ont pas été modifiés.

Le runtime privé de Fred est situé sous `%LOCALAPPDATA%/Fred/runtime-security/hermes-20261021`, sur SSD pour éviter les lenteurs d’import constatées sur le disque du projet. Le pointeur validé reste sous `toolchain/hermes-security-runtime/runtime.json`. Le code de sélection refuse un chemin hors des emplacements privés attendus. La source et le runtime personnels de Hermes restent intacts. Le clone privé est basé sur `79651b71bd56efd76d06f3de1df64dde09b58ff3` ; `hermes-security.patch` conserve l’adaptation des dépendances. Le paquet navigateur incompatible avec Pillow corrigé est omis : les outils navigateur et les autres outils hôte restent désactivés dans Fred.

Le contrôle OSV final a interrogé **223 couples paquet/version**, sans avis affectant ces versions publiques (`osv-apres.json`). Ce résultat ne garantit pas l’absence de vulnérabilités inconnues. Le paquet local `hermes-agent` déclare `0.0.0`, donc ses alertes sont examinées sur le code : les neuf commits correctifs identifiés sont présents dans la base. L’avis restant `GHSA-pmqc-57g8-c22c` concerne le webhook Feishu, non configuré et non exposé par Fred ; il n’est pas présenté comme corrigé en amont. Voir `hermes-avis-source.json`.

## Sauvegarde et conservation des données

La fréquence quotidienne à 03:00 et les rétentions 7/4/6 existantes sont conservées. La copie NAS a été comparée par empreinte puis déchiffrée et restaurée dans un environnement temporaire privé, sans lancer de service. Les empreintes logiques des historiques, projets, documents, mémoires et conversations correspondent. Les accès distants sont désactivés dans cet environnement restauré, comme prévu par le mécanisme de restauration. Preuve : `restauration-nas.json`.

L’archive de signatures `fred-signatures-20261021.fredkeys` est chiffrée avec le mécanisme de récupération existant et copiée sur le NAS. La phrase de récupération n’est inscrite ni dans ces preuves ni à côté de l’archive. La restauration des clés n’a pas été appliquée à la production. Le certificat Android publié est comparé au certificat existant (`signatures-nas.json`, `artefacts.json`). Une nouvelle sauvegarde protégée après livraison et sa copie NAS sont vérifiées par empreinte et authentification du contenu chiffré (`sauvegarde-apres.json`).

Les fichiers sensibles et paramètres sont contrôlés par empreinte avant/après ; les lignes utilisateur SQLite sont contrôlées logiquement pour distinguer les données des verrous et métadonnées de fonctionnement. La console est relancée seule pour charger les correctifs ; les processus et ancêtres du modèle chargé sont explicitement préservés. Une vraie inférence avec image WebP valide le décodeur Pillow corrigé dans le même processus Qwen (`vision.json`).

## Validation

- Applications Windows et Android reconstruites par leurs scripts habituels ; APK signé avec la clé existante. Paquets archivés avant remplacement et manifestes de livraison vérifiés.
- Windows : démarrage de l’EXE avec profil synthétique, test audio PCM silencieux et comparaison de cinq ressources embarquées aux sources. Aucun profil personnel dans l’APK. Preuve : `artefacts.json`.
- Test réel de mise à jour Windows, conservation du profil, rejet des altérations et retour arrière : `test-update-final.txt`.
- Suites complémentaires : 19 tests Windows, 20 tests voix et 13 tests Android réussis ; cinq suites d’interface web réussies. Journaux `tests-windows.txt`, `tests-voix.txt`, `tests-android.txt`, `tests-ui.txt`.
- **530 cas Python distincts validés au total**, en tenant compte des deux reprises ciblées. Suite serveur : 478 cas exécutés, 476 réussis initialement et deux échecs dus au décalage de livraison (ancien EXE et manifeste encore en 3.5.30). Les deux cas passent après publication de 3.5.31 : `tests-livraison-publiee.txt`. Le journal complet initial `tests-serveur-ssd.txt` conserve ces échecs, sans les masquer. Le premier passage sur disque mécanique a été interrompu pour lenteur d’E/S ; les répertoires temporaires des tests ont été déplacés sur SSD, sans changer les cas ni la racine de production.
- Syntaxe : 220 fichiers Python, 61 fragments/fichiers JavaScript, 91 scripts PowerShell sous les deux moteurs. Preuve : `syntaxe-finale.json`. Ruff : aucune erreur de classe F dans les correctifs et scripts concernés (`ruff-final.txt`).
- Android `lintDebug` : zéro erreur, cinq avertissements préexistants ; journal `lint-android.txt` et rapport sous `client-android/app/build/reports/`.
- La mise en service et la disponibilité effective de Qwen, de la vision, de Hermes privé, de la recherche et de la politique NAS sont vérifiées par `livrer.py verify` et consignées dans `production-apres.json`. Les catalogues et le manifeste Windows 3.5.31 sont lus avec un accès personnel existant par WireGuard et HTTPS avec vérification TLS : `acces-apres.json`.

## Limites et entretien

L’isolation d’un autre compte Windows est testée par simulation du propriétaire TCP et refus avant lecture HTTP ; aucune session interactive d’un deuxième compte Windows n’a été créée. Aucun essai sur téléphone physique n’a été effectué. Les administrateurs Windows conservent leur pouvoir d’administration du poste. Les dépendances devront être revérifiées lors des mises à jour ; les verrous et manifestes permettent de détecter une dérive, sans promettre une compilation binaire identique d’une machine à l’autre.

Le contrôle automatique a rejeté la suppression récursive de `toolchain/audit-nas-restore-zwjznfa4` avec le motif **« blocked by policy »**. Ce répertoire temporaire d’un premier essai de restauration est resté protégé et aucun contournement de cette interdiction n’a été effectué. Il n’exécute aucun service et ne bloque pas les corrections.
