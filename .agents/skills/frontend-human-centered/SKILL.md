---
name: frontend-human-centered
description: Concevoir une interface ou modifier un parcours Kiara pour ses utilisateurs finaux, en préservant le langage métier, les usages fréquents et les conventions existantes.
---

# Concevoir pour l'utilisateur final

Avant de modifier l'écran, identifier son public, son objectif, l'action fréquente
et les informations nécessaires à une décision. Déduire ces éléments du parcours
et des sources ; clarifier uniquement un manque qui change réellement le résultat.

- Réutiliser l'organisation, les composants et variables de l'écran voisin. Dans
  Kiara, consulter `client-qwen/ui.css`, `client-qwen/workspace.html`,
  `client-android/mobile-ui/` ou `lanceur/web/interface.css` selon la surface.
- Donner la priorité à l'action habituelle et à une navigation prévisible. Organiser
  l'information pour le repérage et la comparaison ; conserver la densité utile.
- Chaque texte visible doit aider à agir, comprendre un résultat ou décider.
  Employer des verbes courts, le vocabulaire métier et des explications contextuelles.
- Ne pas exposer les mécanismes internes : logs, IDs opaques, états backend et codes
  API vont dans le diagnostic. Une adresse ou clé API peut rester nécessaire dans
  l'écran API ; un état de connexion peut être essentiel dans une application réseau.
- Ne pas ajouter de composants, cartes, badges, illustrations ou animations sans
  fonction concrète. Une application de travail doit permettre le travail récurrent.
- Conserver les données métier, avertissements de sécurité, erreurs, moyens de
  récupération et informations utiles même si l'écran paraît moins minimaliste.

Relire le parcours comme un utilisateur : sait-il quoi faire, ce qui s'est passé et
comment récupérer une erreur, sans comprendre le logiciel ? Si des textes changent,
appliquer `ux-writing-cleaner`. Pour une page ou refonte importante, effectuer
`ux-visual-audit`. Pour une retouche limitée, vérifier seulement son impact.

Adaptation concise de la [guidance frontend officielle OpenAI](https://developers.openai.com/api/docs/guides/frontend-prompt),
consultée le 22 octobre 2026 ; elle ne remplace pas les conventions de Kiara.
