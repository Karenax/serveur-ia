# Page Vocal — 24 octobre 2026

## Résultat

Nouvelle entrée Vocal dans le client Windows. Le chat conserve Dicter ; démarrage,
raccrochage et coupure du micro sont dans Vocal. La même conversation, ses projets,
son historique et ses sources sont conservés. Ouvrir le chat pendant un appel laisse
le microphone actif et affiche un accès Vocal en cours. Le passage de l’application
en arrière-plan conserve son comportement existant d’arrêt automatique.

Réglages : interruptions vocales opt-in, volume de sortie (0–100), animation ;
informations de contexte sous Informations vocales. Les préférences sont validées
et conservées dans le stockage chiffré existant. Les erreurs d’enregistrement ont
un message et une action Réessayer. Aucun faux sélecteur de périphérique : le moteur
utilise les périphériques Windows ; la synthèse et sa voix restent côté serveur.

## Recherche et choix visuel

Références primaires consultées le 24 octobre 2026 :

| Piste | Référence | Évaluation pour Kiara |
| --- | --- | --- |
| Orbe organique | [ElevenLabs Orb](https://ui.elevenlabs.io/docs/components/orb) | États de l’assistant et niveau audio ; bon point central pour un appel. Son implémentation React/Three.js ne correspond pas au client sans framework. |
| Barres, grille, radial, onde, aura | [LiveKit Audio visualizer](https://docs.livekit.io/frontends/agents-ui/audio-visualizer/prebuilt/) et [visualiseurs personnalisés](https://docs.livekit.io/frontends/agents-ui/audio-visualizer/custom/) | Bonne distinction écoute/préparation/parole. Le radial convient à une page centrée ; les barres conviennent surtout aux espaces compacts. |
| Personnage et animations par états | [Rive State Machines](https://github.com/rive-app/help-center/blob/master/runtimes/state-machines.md) | Transitions contrôlables, mais nécessite un personnage, ses animations et un moteur supplémentaire. Aucun personnage existant dans Kiara. |

Choix de conception : un orbe abstrait dessiné en SVG, sans dépendance ni service
externe. Trois contours organiques évoquent une présence et bougent différemment
selon l’état. Les textes restent l’indication principale ; la couleur ne porte
jamais seule l’information. Variables clair/sombre et typographie Kiara conservées.
Ce choix est une adaptation au produit, pas une supériorité universelle démontrée.

La lecture utilise un GainNode pour le volume et un AnalyserNode pour mesurer
le niveau réellement diffusé. La réaction à la voix utilisateur repose sur l’état
de transcription native : aucun niveau de microphone non fourni n’est inventé.
Le calcul visuel est limité à environ 30 images/s et arrêté hors de la page, sans
appel, en arrière-plan, lorsque l’animation est décochée ou en mouvements réduits.

## Vérifications

- Six suites partagées via `npm.cmd --prefix client-qwen test` : réussies
  (Windows et fixtures Android). Les neuf avertissements UX proviennent de textes
  longs dans les sources de console déjà modifiées avant cette tâche.
- Suite de conversation étendue : parcours séparé, dictée conservée, brouillon
  non effacé, retour au chat, reprise de Vocal, microphone clavier, volume réellement
  appliqué, persistance après reload, transcription affichée, état de préparation,
  mesure de sortie, désactivation du mouvement et préférence système.
- Variante `node client-qwen/test_conversation_ui.cjs --web-events` : sources
  consultables depuis Vocal, interruption, reprise, erreurs de lecture et de
  raccrochage, synchronisation lente, réseau et révocation.
- Huit tests Python de préférences : réussis, dont types et bornes des nouveaux
  réglages, chiffrement et préservation des préférences existantes.
- `maintenance/check_sources.py` : 287 sources Python, 67 sources/scripts JavaScript,
  93 scripts PowerShell sous chacun des deux moteurs : réussis.

## Vérification visuelle Playwright MCP

Fixture HTTP locale issue de `node client-qwen/test_conversation_ui.cjs --preview`.
Compte, conversation, reconnaissance, réponses et PCM fictifs ; aucune écriture
en production, aucun microphone matériel. Le point `/__fixture` existe uniquement
dans ce serveur de test et seulement avec `--preview`.

Captures examinées : bureau 1440×900, téléphone 390×844, tablette 768×1024 ; thèmes
clair et sombre. Pas de débordement horizontal constaté. Commandes par Espace,
focus du micro après confirmation, navigation chat/Vocal, noms accessibles,
fieldset/legend et textes de statut examinés. Les scénarios automatisés complètent
les interactions de cette session.

Contrastes des styles calculés contre le fond de page : texte 15,54:1 en clair,
13,77:1 en sombre ; texte secondaire/statut 5,61:1 et 5,69:1 ; raccrochage 5,89:1
et 7,64:1. Ces mesures ciblées ne constituent pas un audit WCAG complet.

| Niveau | Constat | Correction et revérification |
| --- | --- | --- |
| P1 | Le bouton de micro perdait le focus pendant sa désactivation asynchrone. | Restauration si l’utilisateur n’a pas déplacé le focus ; Espace coupe puis réactive le micro sans refocalisation manuelle. Test de non-régression ajouté. |
| P1 | Le premier branchement de Voir les sources enregistrait la liste sans ouvrir le panneau. | Réutilisation du gestionnaire d’ouverture existant ; la variante web-events exige le panneau visible. |
| P2 | Statut de préparation redondant avec le titre et état d’écoute trop technique. | Le détail indique quand l’écoute reprend et si le micro est actif. Les données de contexte sont dans Informations vocales. |

Preuves : `bureau-ecoute.png`, `bureau-vous-parlez.png`, `bureau-preparation.png`,
`bureau-parole.png`, `telephone.png`, `tablette-sombre.png`. Les captures initiales
montrent des versions intermédiaires et ne sont pas les preuves du résultat final.

Limites : pas d’essai acoustique, d’appareil Android ou de WebView Windows physique ;
pas de téléchargement des modèles ni de vérification visuelle complète de leur
installation. Pas de conformité WCAG globale annoncée. Les EXE installés et les
distributions signées n’ont pas été remplacés ; une reconstruction Windows est
nécessaire pour diffuser ces sources. Les changements en cours sont préservés.
