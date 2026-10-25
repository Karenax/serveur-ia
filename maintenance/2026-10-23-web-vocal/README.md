# Recherche web pendant la conversation vocale — 23 octobre 2026

**Historique :** le déclenchement explicite décrit ici a été remplacé le 24 octobre
par une [interprétation sémantique locale](../2026-10-24-web-vocal/README.md).

Le serveur reconnaît les demandes explicites telles que « Cherche sur Internet… »,
« Vérifie sur le web… » et « Fais une recherche web… ». Il appelle les fonctions
`web_search` et `web_extract` de l’installation Hermes déjà configurée. Aucun run
agent, modèle distant ou ancien réglage Brave Fred n’est nécessaire. Qwen local
reste responsable de la réponse et le client continue sa lecture progressive.
Le correcteur et les conversations écrites gardent leurs parcours existants.

Le raccordement est côté serveur et fonctionne avec le client Windows 3.5.41
déjà publié. Les événements de progression et Sources existants sont réutilisés ;
aucune reconstruction ni publication de client n’est nécessaire.

## Périmètre et limites

- Déclenchement explicite en français ; aucune classification automatique des
  questions récentes. Une question ordinaire ne lance pas de requête web.
- Seule la question actuelle, au maximum 2 000 caractères, part vers la recherche.
  Les documents et les anciens échanges ne sont pas envoyés au moteur web.
- Trois résultats au maximum, puis lecture des deux premiers liens publics.
  Les extraits lus sont limités à 4 000 caractères par page ; une page inaccessible
  conserve seulement son extrait de recherche, identifié comme tel.
- Le droit Web vient de la politique du compte Fred, pas des réglages Brave des
  anciennes tâches. Retrait du droit, suspension, révocation, restauration,
  annulation et déconnexion interrompent les appels et empêchent leur livraison.
- Le résultat est propre à la requête HTTP et au propriétaire authentifié.
  Aucun état de résultat global ni cache intercompte n’est ajouté.
- Les validations natives d’URL, DNS et redirection sont conservées ; les résultats
  publics sont filtrés une seconde fois. Les contenus externes restent des données
  non fiables comme instructions.
- Le contexte est recompté après l’ajout des passages et respecte le plafond de
  16 384 tokens, avec 512 réservés à la sortie. L’historique enregistré est inchangé.
- Les liens apparaissent dans Sources pour la réponse en cours. Ils ne sont pas
  ajoutés à un nouveau schéma d’historique vocal persistant dans cette livraison.
- Les erreurs techniques des fournisseurs restent masquées ; Qwen reçoit un état
  explicite en cas d’échec ou de recherche sans résultat.

## Vérifications

`lanceur/test_voice_web.py` couvre demandes positives et négatives, isolation de la
question actuelle, recherche/lecture puis une seule génération Qwen, URLs privées,
échecs et absence de résultats, droits, annulation, révocation et changement de
permission pendant la génération. Les suites voix, contexte, correcteur et web
natif existantes sont également exécutées.

`validate_native.py` crée un compte et une passerelle temporaires, appelle les
vrais services web et le Qwen déjà chargé, sans écrire dans les comptes ni les
historiques de production. Le premier texte a été obtenu en 26,313 s sur une
question publique fictive ; 2 021 tokens d’entrée et 512 réservés à la sortie.
Deux pages ont été lues. Ce seul essai ne constitue pas un benchmark et ne mesure
ni le microphone, ni la reconnaissance, ni la lecture audio dans le navigateur.

`activate.py` redémarre uniquement Fred avec conservation des processus Qwen,
contrôle les empreintes des données et clés ainsi que la programmation des
sauvegardes, puis vérifie les services. `verify_production.py` effectue une demande
fictive sur la passerelle authentifiée existante et valide une synthèse Phonon,
sans écrire de conversation ni de nouvel accès de production.

Activation effectuée sur le serveur 3.5.41. Les 83 tests backend, le parcours vocal
du navigateur avec progression web et bouton Sources, les contrôles syntaxiques
et le contrôle UX ont réussi. L’essai sur la passerelle active a fourni trois
sources, dont une page lue, avec un premier texte à 23,078 s. Phonon a ensuite
fourni son premier PCM en 0,109 s sur une phrase fictive distincte. Aucun run
Hermes n’a été créé ; processus Qwen, données, clés, client signé et programmation
des sauvegardes sont conservés. Ces délais ne mesurent pas la chaîne microphone
et lecture utilisateur complète.
