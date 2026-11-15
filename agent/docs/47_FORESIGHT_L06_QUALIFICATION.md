# L06 — Qualification de l’interface de séance

### L06 — Studio commun, responsive et lecture au bon repère — 16 octobre 2026

Le projet conserve ses revues et anciens comptes rendus, avec une entrée vers le même
Studio que Réunions. Le projet reste filtré dans `/app/meetings?project=…`, y compris
après rechargement. Les changements passent par la garde de navigation existante.

Les panneaux sont égaux lorsqu’ils tiennent côte à côte, sinon empilés et défilables.
L’intervalle fractionnaire entre670et671pixels est couvert. Les fenêtres1280,800,
671,670et320pixels sont contrôlées dans le navigateur ; le viewport initial est rétabli.

Le lecteur des fragments est dans Transcription, avec son historique, et non caché
dans Préparation. Le seek attend les métadonnées et garde le dernier repère demandé.
L’API audio prend en charge une plage d’octets avec206/Content-Range et signale416
hors fichier. Droits et empreinte des originaux sont vérifiés avant réponse partielle.
Sur un WAV de silence fictif, le navigateur décode10s et démarre réellement à2s.

59contrôles de navigation/projet et95contrôles du Studio passent. Les15nouveaux cas
HTTP passent ; les25contrats de séance restent couverts par17réussites acquises et
8cas rejoués après correction de leurs chemins temporaires Windows, sans nouveau
total global. TypeScript, Vite et Ruff passent. Les échecs initiaux sont conservés.

Les parcours réels sur copies privées vérifient création, brouillons riches et Markdown,
conversion explicite, correction de transcription sans changer le timecode et accès
à la même note depuis le projet. Les fonctions métier héritées sont conservées.
L06 est clos selon ses critères d’interface ; le plan permet l’audio importé avant L03.
Aucun nouvel essai matériel, ASR, GPU ou LLM : L02/L03/L09/L11/L12 restent ouverts.
Sauvegardes et conservation SQL vérifiées avant activation8001. Détail : domaine47.


## Correspondance des exigences

| Exigence d’origine | Preuve actuelle |
|---|---|
| Liste globale/projet et création | Entrée projet vers le même Studio, filtre dans l’URL conservé au rechargement ;59contrôles et création guidée réelle sur copie |
| Écran dans le shell et dispositions référencées | Captures du corpus fictif, panneaux égaux sur grand écran et empilement intrinsèque ; référence publique et adaptation Agent acceptées |
| Barre audio et choix des périphériques | Sélecteurs Windows réellement peuplés et démarrage explicite visible ; contrats NativeMeetingCapture inchangés réutilisés, aucun nouveau démarrage matériel |
| Notes/enrichissements et Chat/Synthèse/Transcription/Questions | 95contrôles actuels du Studio ; navigation clavier réelle Discussion→Synthèse→Questions ; états d’indisponibilité explicites sans modèle fictivement prêt |
| Lecture au timecode, copies et liens sources | Lecteur hors Préparation, WAV fictif décodé et lu à2s, seekable0–10 ; HTTP206 exact ; actions Copier et sources/version contrôlées par le Studio et ses contrats |
| Vues et brouillons | Brouillon riche conservé entre vues puis version2 sur copie ; accès projet retrouve la même note ; vrai Markdown conservé, conversion explicite et sauvegarde avec gras/négation |
| Richesse et absence de perte silencieuse | Tableau1250W conservé, Markdown refusé avec tableau ; NoteRichEditor inchangé et preuves acquises pour tableaux/images ; nouveau Markdown simple relu puis appliqué |
| Bibliothèque/Stats et métier accessibles | Menu stable, Sources/Stats réellement consultés ; ancien graphe et compteurs qualifiés dans le reçu L09/L11 ;29fonctions App conservées, seule ReviewsPanel reçoit un lien |
| Clavier, focus, redimensionnement, petite fenêtre | Focus réel sur onglets sélectionnés ;1280/800/671/670/320px sans débordement des panneaux ; défilement au lieu de compression ; viewport restauré |

## Portée, dépendances et réversibilité

Le texte original de L06 exige le contrat de capture L02 et autorise explicitement
le raccordement de L03 après une première recette avec audio importé. La répétition
physique complète n’est donc pas un critère supplémentaire de clôture de l’interface.
Elle demeure nécessaire aux lots matériels et à la recette globale selon leurs propres
critères. Cette clôture ne ferme aucun autre lot et ne change pas les exigences de L12.

La fidélité est évaluée sur les écrans publics et l’adaptation Agent acceptée. Aucune
parité privée Mac ou promesse à±2pixels. Les captures utilisent des données fictives ;
la lecture est celle d’un WAV de silence généré, pas une nouvelle capture ou une preuve
de qualité ASR. La génération est volontairement indisponible dans les fixtures ; ses
propositions, citations et états restent contrôlés par les contrats actuels du Studio
et les preuves réelles déjà qualifiées en L05/L07. Aucun modèle n’est chargé pour cette
recette. Les captures670/320 antérieures sont conservées avec les mesures finales.

Les revues héritées et tous les autres modules restent disponibles. L’audit TypeScript
constate29fonctions App avant/après, aucune supprimée, et seule ReviewsPanel modifiée
pour ajouter le lien au Studio. L’audit Python limite les changements de route à audio
et à son analyse de plage. Pas de nouveau schéma ni de réécriture de données métier.

La lecture utilise une seule plage HTTP ; les unités inconnues, syntaxes non traitées
et plages multiples sont ignorées au profit du GET complet. If-Range sans validateur
reçoit le fichier complet. La conversion de nombres décimaux très longs est bornée par
la taille réelle de la représentation, sans limite arbitraire de chiffres ajoutée.
Référence technique : [RFC9110, sections14.1–14.4](https://httpwg.org/specs/rfc9110.html#field.range).

Les actifs compilés précédents restent sur disque ; l’index HTML bascule après leur
sauvegarde, puis les fichiers servis sont comparés par empreinte. Les bases récentes
déjà restaurées sur copies sont réutilisées uniquement après comparaison exacte des
données non volatiles Brain/ERP avant/après. Aucun commit ni push.

## Preuves

- `logs/foresight-runtime/L06-interface-qualification-ROOT-20261016.json`
- `.ui-preview/l06-ui-20261016/browser-final.json` et `responsive-final.json`
- `.ui-preview/l06-ui-20261016/private-HTTP-SQL-result.json`
- `.ui-preview/q/l06-project-studio-20261016/frontend.xml`
- `.ui-preview/q/l06-studio-timecode-20261016/frontend.xml`
- `.ui-preview/q/session-audio-range-r1-20261016/results.xml`

![Studio à deux panneaux égaux](../.ui-preview/l06-ui-20261016/studio-final-deux-panneaux-egaux.jpg)
