# Android 1.0.17 — ancien message de connexion affiché en rouge

La bannière rouge centrale provenait d’une réponse provisoire du client natif :
`503`, code `connecting`, message « Connexion au serveur IA… ».
Au démarrage, `ClientBackend.state()` peut déclencher la recherche de mise à jour
pendant que le chat demande les modèles. `Remote.check()` diffère son contrôle
si une requête native est déjà active ; aucun catalogue n’est encore disponible.
La route des modèles renvoie alors cet état provisoire.

Le chat traitait cette réponse comme une erreur rouge. Le code `connecting`
n’appartient pas aux erreurs de connexion suivies par `networkBanner` : une
connexion réussie ultérieure ne supprimait donc pas ce message.

Le traitement Android reconnaît maintenant les codes provisoires `connecting`
et `connection_check_pending` comme une progression normale, présentée dans
l’état de connexion. Il conserve toute erreur déjà affichée qui demande une
action, notamment l’échec d’une sauvegarde. Les erreurs réseau, révocations et
autres erreurs continuent de passer par le traitement partagé existant.
Le fonctionnement Windows n’est pas modifié.

## Vérifications

- `Test-Assets.cjs --browser` reproduit au démarrage la réponse native 503
  `connecting`, puis une connexion réussie : aucune bannière rouge résiduelle.
- Un échec de sauvegarde reste visible pendant cet état provisoire et après
  la connexion. Une révocation reste visible ; une reconnexion confirmée efface
  son propre message réseau. Les autres parcours Android de la suite passent.
- `test_refresh_stability.cjs --android` : focus, brouillon, sélection et
  défilement conservés ; aucune reconstruction des listes et messages inchangés.
- Build Release ARM64/x86_64 et treize tests de livraison : succès.
- Contrôle des sources : 327 Python, 70 JavaScript et 93 PowerShell dans les
  deux moteurs. Contrôle UX : neuf avertissements de console préexistants.

APK 1.0.17/code 18 signé avec la clé existante. Sa publication et le téléchargement
authentifié sont vérifiés dans `android-publication.json`. Installer par-dessus
la version actuelle. Aucun appareil Android physique n’a été utilisé pour ce
correctif d’affichage ; la reproduction utilise la vraie interface générée et
une réponse HTTP conforme au contrat natif.
