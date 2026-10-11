# Mises à jour Android — 11 octobre 2026

Livraison : **1.0.5, code 6**, APK signé dans
`client-android/dist/Acces-serveur-Fred-Android.apk`. Le manifeste de publication
est `client-android/dist/release.json`.

Le client recherche les mises à jour pendant son utilisation, télécharge les
nouvelles versions dans son stockage privé et propose **Installer la mise à
jour**. Android garde la confirmation finale. Les anciennes versions doivent
recevoir manuellement cette première mise à jour.

## Vérifications

- Compilation Release réussie ; 13 tests Python de livraison réussis ; signatures
  APK v2/v3 et alignement 16 Ko vérifiés par le script de compilation.
- Trois tests serveur isolés réussis : manifeste et invalidation du cache,
  authentification/révocation/refus d’un fichier altéré, téléchargement par un vrai
  tunnel WireGuard avec les listes de routes client et serveur.
- Essais navigateur téléphone/tablette réussis : contrôles existants, nouveau
  bandeau d’installation, sauvegarde avant installation, blocage en cas
  d’historique indisponible et absence du bouton Réessayer la réponse.
- Contrôles natifs réussis sur les deux émulateurs Android 16 : bornes du manifeste,
  taille/empreinte, identité du paquet, certificat différent, version identique
  et retour vers une ancienne version refusés.
- Parcours natif complet sur les deux émulateurs : téléchargement d’un APK signé
  de test **1.0.6/code 7** par un serveur et un pair WireGuard isolés, vérification
  de l’APK, lecture par le fournisseur d’URI, refus d’écriture et ouverture de
  l’installateur. Les fichiers XML contiennent **Do you want to update this app?**
  avec les boutons **Cancel** et **Update**. La confirmation a été annulée ; la
  version future de test n’a jamais été publiée sur le serveur réel.
- La console et ses moteurs auxiliaires ont été rechargés. Les processus du
  modèle, leurs dates de création, les clés d’accès et les réglages ont été
  comparés avant et après et sont conservés.
- Le manifeste et les octets de l’APK publié ont été vérifiés via la passerelle
  authentifiée locale, puis via **HTTPS public**, avec l’identification du client
  Android et sans suivre de redirection.

Les résultats figurent dans `android-release.json`, `production-validation.json`,
le journal de compilation et les journaux/XML des deux émulateurs. Aucun secret
d’accès n’est inclus dans ces preuves. La tablette physique de l’utilisateur
n’était pas connectée par USB ; son installation n’a pas été effectuée.

## Reproduire les essais

Depuis la racine : compiler avec `client-android/Build-Android.ps1`, exécuter
`client-android/scripts/Test-Assets.cjs --browser`, puis
`python -m unittest discover -s lanceur -p test_android_updates.py -v`.
Les dépendances Python/Playwright et l’environnement Android sont ceux du projet.

`client-android/tests/Build-Update-Fixture.ps1` prépare séparément l’APK futur et
une instrumentation signée pour l’application Release. `update_fixture.py`
expose ce paquet dans une passerelle isolée, accessible aux émulateurs à travers
`10.0.2.2`. Le profil synthétique est conservé seulement dans le dossier privé
de test sous `toolchain`, exclu de Git. Les paramètres de test sont explicites ;
aucun profil personnel n’est nécessaire.
