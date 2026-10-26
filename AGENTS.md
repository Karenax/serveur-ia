# Instructions du projet Kiara

Préserver les modifications en cours. Les conventions et commandes de reconstruction
existantes sont décrites dans `RECONSTRUIRE-FRED.md` ; les contrôles de sources sont
dans `maintenance/check_sources.py` et les tests UI partagés dans `client-qwen`.

## UX/UI — Règles permanentes

Toute interface nouvelle ou significativement modifiée doit être conçue pour son
utilisateur final, pas pour un développeur.

- Employer le langage métier et des libellés courts ; chaque texte doit aider à agir,
  comprendre ou décider. Éviter les longues explications sans besoin réel.
- Garder logs, codes internes, identifiants techniques et états backend dans les
  diagnostics ou l'administration. Conserver les informations techniques utiles au
  public d'un écran explicitement technique (API, connexion, administration).
- Préserver les informations métier, avertissements, erreurs de sauvegarde et moyens
  de récupération. Ne pas sacrifier une fonctionnalité pour l'esthétique.
- Réutiliser les composants, variables CSS, typographie et conventions existants.
  Éviter décoration gratuite et multiplication artificielle des cartes et boutons.
- Favoriser navigation stable, actions fréquentes et interactions directes ; conserver
  la densité fonctionnelle nécessaire sur ordinateur, téléphone et tablette.
- Vérifier erreurs, états vide/chargement, clavier, focus et accessibilité pertinente
  WCAG 2.2 AA ; ne pas annoncer une conformité complète sans vérification suffisante.

Charger seulement les skills utiles à la tâche depuis `.agents/skills/` :

| Situation | Skill |
| --- | --- |
| Interface nouvelle ou parcours modifié | `frontend-human-centered` |
| Texte visible créé ou modifié | `ux-writing-cleaner` |
| Design significativement modifié | `professional-ui-design`, puis `frontend-design` si utile |
| Nouvelle page, refonte, modification visuelle importante | `ux-visual-audit` |
| Cohérence entre écrans ou changement transversal | `ux-consistency-review` |
| Audit de bonnes pratiques | `web-design-guidelines` |

Les consignes esthétiques amont doivent être adaptées à Kiara : interface de travail,
conventions existantes et français courant, sans hero marketing ni changement de
police imposé. Le métier et la demande de l'utilisateur priment sur les préférences
génériques des skills. Ne pas charger tous les skills à chaque conversation.

Mode normal : vérification proportionnée, contrôles existants et `npm --prefix
client-qwen run ux:check` pour les sources UI touchées. Une petite correction sans
impact visuel ne déclenche pas un audit complet. Les suspicions du script restent des
avertissements à examiner, jamais une raison de supprimer automatiquement du contenu.

Sur « audit UX complet », appliquer `ux-visual-audit` et parcourir les écrans
accessibles ; rapport avec preuves et classement P0 (action critique impossible/perte
de données), P1 (ergonomie/accessibilité importante), P2 (texte/cohérence/hiérarchie),
P3 (finition). Proposer les corrections, effectuer celles demandées puis revérifier.
Employer des données fictives ; ne pas modifier la production pour tester. Documenter
les écrans inaccessibles et les limites, sans inventer de validation visuelle.

Procédures, portée, installation et commandes : `maintenance/ux-ui/README.md`.
