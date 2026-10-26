# Kiara — plan d’amélioration issu de l’audit global

## Suite corrective du 26 octobre 2026

Les constats ci-dessous décrivent l’état initial de l’audit. Les corrections du produit, validations et limites sont suivies dans [le rapport des correctifs](<D:/Serveur IA/maintenance/2026-10-26-correctifs-audit-global/README.md>) et [leur bilan](<D:/Serveur IA/maintenance/2026-10-26-correctifs-audit-global/AVANCEMENT.md>). Les preuves historiques restent conservées.

Référence : [rapport détaillé](<D:/Serveur IA/audits/2026-10-25-global/RAPPORT.md>), état des 25–26 octobre 2026. Ce plan propose des travaux ; aucun correctif produit n’a été appliqué pendant l’audit.

## Ordre recommandé

### Lot 1 — Corriger les pertes de modification et rendre les annulations toujours possibles

**Constats F01, F02 — priorité P1.** À traiter avant d’ajouter de nouvelles commandes de l’assistant.

1. Faire converger les anciennes routes de mémoire et les nouvelles commandes vers les mêmes opérations métier.
2. Ajouter aux anciens parcours un contrôle de révision et une récupération du brouillon en cas de conflit.
3. Préserver l’annulation et l’oubli à quota plein ; réserver l’espace nécessaire à leur résultat durable.
4. Définir la rétention du journal de commandes sans permettre de rejouer une ancienne mutation.
5. Transformer les reproductions de l’audit en tests permanents du domaine et des deux interfaces.

**Terminé lorsque :** deux clients ne peuvent pas écraser silencieusement le même souvenir ; les parcours ancien/nouveau appliquent la même règle ; un rappel annulé à journal plein ou quota plein ne se déclenche plus ; les répétitions d’une commande restent idempotentes.

**Charge indicative :** quelques jours de travail, selon les contraintes de compatibilité des clients. Prévoir des changements séparés pour la concurrence mémoire et la saturation, chacun testable et réversible.

### Lot 2 — Actualiser les dépendances et rétablir une validation fiable des runtimes

**F03, F04, F05 — P2, à engager rapidement.** Peut être préparé indépendamment du lot 1 dans un environnement séparé.

1. Mettre à jour le parseur PDF dans le runtime concerné, puis les autres paquets signalés après examen de leurs avis.
2. Recompiler le pont avec une version Go corrigée, au moins 1.27.3 pour les avis de la branche 1.27 relevés à la date de l’audit.
3. Séparer environnement de construction et environnement d’exécution, ou formaliser leurs profils distincts.
4. Faire vérifier tous les environnements et produire un bilan agrégé même si le premier échoue.
5. Rejouer extraction, transports, voix et tests Hermes selon les composants modifiés ; renouveler signatures, manifestes et verrous.

**Terminé lorsque :** tous les verrous correspondent ; chaque avis restant possède une justification d’applicabilité documentée ; le binaire réellement distribué porte le runtime corrigé ; les tests passent ; le retour arrière est disponible.

**Charge :** petit à moyen par environnement. Ne pas remplacer en une seule opération tous les runtimes et moteurs, ce qui rendrait une régression difficile à attribuer.

### Lot 3 — Sécuriser le cycle de vie des données et du runtime Hermes

**F09, F10, F11, F13 — P2.** Stabiliser les comportements de reprise et les diagnostics.

1. Introduire une version de schéma et un registre de migrations, en conservant les lecteurs des sauvegardes supportées.
2. Distinguer une vraie ancienne génération de données d’un simple marqueur manquant ; tester cette distinction avant tout effacement.
3. Faire démarrer le runtime Hermes privé avec ses propres prérequis explicites, indépendamment de l’état de l’installation personnelle.
4. Renforcer le garde d’intention sur négations, citations et ambiguïtés, sans multiplier les confirmations pour les actions clairement demandées.
5. Ajouter des diagnostics bornés et expurgés aux échecs de workers, avec corrélation entre requête et composant.

**Terminé lorsque :** restauration et migration passent sur un jeu de générations historiques ; un marqueur absent n’efface pas silencieusement des données actuelles ; Hermes démarre sans bootstrap personnel ; les erreurs de workers deviennent explicables sans exposer le contenu utilisateur.

**Charge :** moyenne ; séparer migration de données, runtime et journalisation en changements distincts.

### Lot 4 — Consolider les frontières du code sans changer les usages

**F06, F07, F08, F12 — P2.** Réduction progressive de la dette.

1. À partir des opérations unifiées au lot 1, extraire un service métier par domaine : mémoire, rappels, documents, conversations.
2. Réduire les handlers à la validation du protocole, l’appel au service et la traduction des réponses.
3. Rendre explicites les modules partagés au lieu d’importer des fichiers clients depuis le serveur par `sys.path`.
4. Introduire des capacités de plateforme pour l’interface ; remplacer les substitutions fragiles une par une.
5. Instrumenter contention SQLite et snapshots ; optimiser uniquement les chemins dont le coût est établi.
6. Formater les fichiers touchés dans des changements séparés des modifications métier.

**Terminé lorsque :** une règle métier n’a qu’une implémentation ; Windows et Android passent les mêmes contrats ; les anciens protocoles sont des adaptateurs ; les mesures montrent que les rafraîchissements et quotas restent acceptables au volume cible.

**Charge :** grande et fractionnable. Une succession de petites extractions est préférable à un déplacement global de fichiers suivi d’une longue stabilisation.

### Lot 5 — Rendre la livraison, les preuves et le support plus simples

**F14, F15, F16, F17 — P2/P3.** À intégrer au fil des lots précédents.

1. Un point d’entrée pour la validation complète, avec résultats par composant.
2. Tous les tests écrivent dans un dossier de résultats de leur exécution ; aucune preuve historique suivie n’est modifiée.
3. Un manifeste par livrable et un manifeste du déploiement global.
4. Une matrice des versions actuelles : moteur, serveur Python, Hermes, packs vocaux, clients, schéma, runtimes.
5. Une liste explicite des compatibilités anciennes encore supportées et de leurs conditions de retrait.
6. Un essai de reconstruction et de restauration sur un environnement distinct, avec les secrets transmis par la procédure prévue.
7. Un index de documentation courante et un index historique ; déplacement contrôlé des outils ponctuels.

**Terminé lorsque :** on peut identifier précisément ce qui est exécuté, reconstruire un livrable, retrouver ses tests et décider si un ancien composant peut être retiré sans lire plusieurs dossiers historiques.

## Backlog traçable

| ID | Priorité | Décision | Dépendance principale | Effort |
|---|---|---|---|---|
| F01 | P1 | Unifier les écritures de mémoire et les révisions | Aucune | Moyen |
| F02 | P1 | Garantir annulation/oubli en saturation | Politique d’idempotence | Moyen |
| F03 | P2 | Corriger les dépendances Python concernées | Tests de chaque runtime | Petit–moyen |
| F04 | P2 | Recompiler et distribuer le pont Go corrigé | Procédure de signature | Petit–moyen |
| F05 | P2 | Séparer et vérifier construction/exécution | Inventaire des usages de PyInstaller | Petit–moyen |
| F06 | P2 | Découper les responsabilités de la passerelle et de Workspace | F01 comme premier domaine | Grand, progressif |
| F07 | P2 | Déclarer les modules partagés et leurs dépendances | Contrats stables | Moyen–grand |
| F08 | P2 | Remplacer les substitutions UI par des capacités explicites | Tests partagés maintenus | Moyen–grand |
| F09 | P2 | Versionner les migrations et protéger la récupération | Corpus de sauvegardes anciennes | Moyen |
| F10 | P2 | Découpler le runtime Hermes privé du bootstrap personnel | Dépendances privées explicites | Moyen |
| F11 | P2 | Renforcer le contrôle d’intention | Corpus français d’ambiguïtés | Moyen |
| F12 | P2 | Mesurer puis réduire contention et recalculs | Volumes cibles définis | Moyen |
| F13 | P2 | Rendre les erreurs de workers diagnosticables | Politique de filtrage des données | Moyen |
| F14 | P2 | Manifester les livrables et isoler le déploiement | Reconstruction propre | Moyen–grand |
| F15 | P2 | Validation agrégée et preuves sans effets de bord | Répertoire commun de résultats | Petit–moyen |
| F16 | P3 | Isoler puis retirer les générations vocales inutilisées | Inventaire des packs distribués | Moyen |
| F17 | P3 | Clarifier documentation et scripts ponctuels | Matrice des versions courantes | Petit–moyen |

Les efforts sont des ordres de grandeur relatifs, pas des engagements de calendrier. Le lot 1 apporte le gain utilisateur le plus immédiat ; les lots 2 et 3 réduisent les risques ; les lots 4 et 5 rendent les prochaines évolutions plus prévisibles.

## Critères à conserver à chaque livraison

- Aucun écrasement silencieux d’un brouillon ou d’une modification concurrente.
- Révocation et annulation restent possibles sous charge et en saturation.
- Propriétaire et projet sont vérifiés au niveau de l’opération métier.
- Les données canoniques ont un propriétaire, une version et un chemin de récupération documentés.
- Les contrôles existants passent, les avertissements sont examinés et les échecs ne sont pas masqués.
- Chaque livrable est relié à ses sources, runtimes, signatures et preuves.
- Toute suppression de compatibilité est justifiée par les versions réellement supportées.
