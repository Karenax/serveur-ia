# Derniers correctifs Strata activés — 16 octobre 2026

À la demande explicite de l'utilisateur, le service Strata a été arrêté puis relancé par l'API de sa console propriétaire. La console elle-même n'a pas été redémarrée. Le moteur était au repos avant l'opération.

Le nouveau serveur charge le parseur comprenant les deux correctifs : booléens selon le schéma des outils, puis objets JSON dans les enveloppes XML et vérification des champs obligatoires. L'empreinte de la source correspond exactement au correctif préparé et validé par 367 tests dans `2026-10-16-outils-mixtes`. Le serveur Python et le moteur ont été remplacés ; les paramètres persistants et les configurations d'accès ont les mêmes empreintes avant et après.

## Vérifications après redémarrage

- Modèle chargé, vision active, file vide après les essais.
- **20 emplacements de conversations sauvegardées**, budget global **30 720 Mio / 30 Gio**, réserve RAM **6 Gio** confirmés par l'API.
- Trois conversations synthétiques d'environ 3 k tokens alternées et restaurées : retours en **0,89–1,92 s**, 7 ou 29 tokens relus, réponse A identique à la référence. Trois restaurations réussies.
- Deux appels d'outils sur le vrai modèle : `background: true` sans streaming puis `background: false` en streaming, avec `marker: "True"` conservé comme texte. Aucun outil retourné n'a été exécuté.
- Les cas fautifs XML/JSON et champs manquants ont été reproduits de façon déterministe dans la suite HTTP à moteur simulé avant cette activation. Les essais réels ci-dessus vérifient l'intégration et ne prétendent pas forcer le modèle à générer un format fautif.
- Console, Hermes, passerelle et WireGuard disponibles ; paramètres et accès conservés.

Preuves : `avant.json`, `arret.json`, `demarrage.json`, `verification-finale.json`, `validation-cache/mesures.json`, `validation-outils-live.json`.

Une prélecture séquentielle en lecture seule a parcouru les 60,94 Gio d'experts avant la relance, en **155,38 s**, sans arrêt pour pression RAM. Un passage ciblé sur les couches 40–47 a également été effectué pendant le chargement, en **35,10 s**. Ces actions restent ponctuelles, sans intégration au démarrage automatique. Le gain isolé n'a pas été mesuré.

Chargement et validation CUDA après le lancement : **260 secondes**. La protection mémoire a réduit une fois les pages temporaires du seul moteur en chargement. Les réglages d'effort de réflexion n'ont pas été changés ; l'utilisateur peut maintenant comparer medium et low dans OpenCode.
