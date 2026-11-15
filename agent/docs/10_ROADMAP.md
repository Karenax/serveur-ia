# Roadmap et périmètre autorisé

## État actuel — 11 octobre 2026

Agent est le projet unique, actif sur 8001. Le canon SQLite, les modules ERP hérités, les sources et décisions sont conservés. La mémoire EG2 remplace le moteur précédent : index local reconstructible, embeddings distants et génération par le LLM configuré. La migration réelle et ses limites sont documentées dans [20_EG2_ENGINE.md](20_EG2_ENGINE.md).

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [périmètre projet](28_XPILOT_PROJECT_PLAN.md) et [suivi](29_XPILOT_EXECUTION.json).

## Priorité d'exploitation

- maintenir les contrôles de portée projet, de provenance et de validation ;
- surveiller la file persistante EG2 et reprendre les échecs sans toucher au canon ;
- distinguer santé locale de l'index, test réel du serveur distant et qualité des réponses ;
- conserver des sauvegardes avant les opérations sur les bases ;
- qualifier un changement de profil avant reconstruction ;
- corriger les régressions connues selon leur domaine, notamment l'échec de classement mail signalé dans [09_TEST_STRATEGY.md](09_TEST_STRATEGY.md).

Le choix de production EG2 est validé. Il n'y a pas de nouvelle sélection de moteur ni de campagne de benchmarks à relancer automatiquement. Des tests supplémentaires doivent résoudre une question concrète, avec corpus fixe et mesure de toute la boucle si la pertinence des réponses est en jeu.

## Capacités présentes à entretenir

Le canon métier comprend projets, contacts, sources, artefacts, connaissances, propositions, provenance, décisions et audit. Les informations admissibles de sources résolues peuvent être retenues par défaut ; leur mode de validation reste visible et les confirmations humaines sont protégées.

La mémoire indexe les preuves, lit les connaissances actives dans SQL, contrôle les sources au rappel et permet purge/reconstruction. Les files de reprise, la recherche et le contexte du chat font partie de ce fonctionnement. L'enrichissement métier par LLM reste distinct de l'indexation EG2.

Les parcours e-mail, documents, CDC, Revues et audio déjà présents restent dans Agent. Une interface ou un moteur installé ne prouve pas sa disponibilité opérationnelle : la transcription, la diarisation et les accès réseau se qualifient séparément.

## Extensions conditionnées à une demande

La réduction de périmètre décidée le 7 octobre prévaut sur le plan initial. CDC et BE existants sont conservés et vérifiés ; ils ne déclenchent pas une nouvelle réécriture. Les extensions de signatures, nomenclatures/BOM, charge/ressources, collaboration, calendrier, qualité, retour d'expérience et clôture restent différées. Les capacités historiques correspondantes, lorsqu'elles existent, ne sont pas supprimées.

Les objectifs suivants constituent une vision future, sans autorisation de les démarrer automatiquement :

- capture téléphonique et enrichissement du pipeline audio commun ;
- OCR, compréhension de tableaux et schémas selon les besoins documentaires ;
- événements/webhooks et façade MCP contrôlée par les droits métier ;
- échanges avec XPilot externe, en préservant son port 8000 ;
- métadonnées CAO/3D, aperçus et liens aux exigences ;
- toute nouvelle infrastructure de stockage ou d'authentification réseau.

Chaque extension exige un besoin explicite, une qualification adaptée et la conservation des modules et données existants. La présence de ces objectifs dans la documentation n'est ni une promesse de livraison ni une instruction d'exécution.
