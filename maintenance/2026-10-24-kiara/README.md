# Renommage en Kiara — 24 octobre 2026

L’application et l’assistante portent le nom **Kiara** dans les sources courantes :
interface partagée Windows/Android, console serveur, notifications Android,
intégrations OpenCode/Hermes, exports, métadonnées Windows et documentation.
Les consignes de conversation écrite et vocale donnent ce nom à l’assistante.
Le monogramme devient **K**, y compris les icônes Windows et Android.

## Compatibilité

- Les EXE clients gardent leurs noms : base `Accès serveur Fred.exe` et fichiers
  personnels `Accès serveur Fred VERSION - NOM.exe`. Le nom affiché du produit
  Windows est indépendant du nom du fichier.
- Les identifiants persistants restent stables : paquet Android `net.karenax.fred`,
  clés de signature existantes, profils, répertoires de données, préférences,
  formats de sauvegarde et de connexion, identifiants de modèles et protocoles.
  Aucun déplacement des données ni remplacement des secrets.
- Le nouvel APK est nommé `Acces-serveur-Kiara-Android.apk`. Le serveur peut encore
  distribuer l’ancien nom d’APK si le nouveau paquet n’a pas été publié.
- Les archives, preuves datées et chemins documentaires historiques gardent
  leurs noms. Les captures écrasées par les tests ont été rétablies.

## Construction et portée

Paquets préparés dans `toolchain/releases-staging/kiara-windows/` et
`toolchain/releases-staging/kiara-android/`, avec leurs manifestes de construction.
Leurs empreintes et la vérification des ressources sont dans [paquets.json](paquets.json).
Les versions de travail sont conservées : Windows/serveur 3.5.41, Android
1.0.13/code 14. Ces paquets ne sont pas publiés dans les distributions actives ;
la publication devra employer une version supérieure pour déclencher les mises
à jour automatiques des appareils déjà à cette version.

Le dépôt contenait déjà des modifications et d’autres travaux vocaux se
poursuivaient pendant cette intervention. Ils ont été préservés. Aucun redémarrage
de production, remplacement de distribution active ou reconditionnement des
EXE personnels n’a été effectué pour ce renommage.

## Vérifications

- Contrôle de syntaxe Python, JavaScript et PowerShell réussi.
- 37 tests Python Windows, 13 tests Python Android et 26 tests vocaux réussis.
- Suite serveur : 529 tests exécutés, 527 réussis au premier passage. Les deux
  échecs étaient des attentes de tests devenues obsolètes : une comparaison des
  messages qui ignorait la nouvelle identité système Kiara, et une comparaison
  avec l’ancien nom affiché par l’EXE encore publié. Les attentes ont été
  actualisées, avec vérification du paquet préparé pour le démarrage personnel.
  Les cinq contrôles concernés ont ensuite été rejoués ensemble avec succès.
  La suite complète n’a pas été relancée après ces corrections de tests.
- Six suites UI partagées réussies sur les interfaces Windows et Android.
- Parcours navigateur Android téléphone/tablette réussi ; titre Kiara et
  monogramme K vérifiés dans le DOM. Le contrôle attendait encore l’absence du
  menu API : le même échec a été reproduit sur HEAD, puis cette attente obsolète
  a été corrigée pour vérifier le maintien du menu existant.
- Contrôle UX réussi avec neuf avertissements de textes longs examinés ; aucune
  fonctionnalité ni information métier supprimée. Il ne constitue pas un audit
  complet d’accessibilité.
- APK compilé et signé avec les clés existantes, signatures v2/v3 vérifiées.
  Son manifeste compilé affiche « Accès serveur Kiara » et conserve le paquet
  `net.karenax.fred`.
- Auto-test de l’EXE réussi. Métadonnées Windows : produit et description
  « Accès serveur Kiara », `OriginalFilename` « Accès serveur Fred.exe ».
- Démarrage d’un EXE personnel issu du paquet préparé réussi, avec profil et
  manifeste signés uniquement dans un dossier de test isolé. Le test accepte
  `FRED_TEST_CLIENT_EXE` pour vérifier ce paquet sans publier de distribution.
- Ressources UI extraites des deux paquets comparées aux sources ; notices
  applicatives Kiara vérifiées. Les licences des composants tiers sont conservées.

Les journaux locaux et les empreintes des paquets sont dans
`toolchain/rename-kiara-before/`. Les validations n’utilisent pas de données privées
de production et ne testent pas un microphone humain.
