# Android 1.0.14 — compilation et publication

L'APK signé est publié dans :
`D:\Serveur IA\client-android\dist\Acces-serveur-Kiara-Android.apk`.

- Version **1.0.14**, code **15**, application `net.karenax.fred`.
- Taille : **18 911 508 octets**, environ 19 Mo.
- SHA-256 : `07da0eaaaff9560ea4e892c42045b97b46d640c3ca7203c05263400de51c9ac5`.
- Même certificat que la version 1.0.13 :
  `40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`.
- Identité de l'application et fichiers de clé de signature conservés :
  installation par-dessus la version actuelle possible, sans désinstallation.
- Aucun profil personnel, clé d'accès ou modèle Max Windows embarqué.

Les sources Android courantes et l'interface partagée ont été régénérées avec
les outils existants. Treize tests de livraison, le test navigateur Android
(téléphone/tablette), la vérification des assets et licences passent.
`assembleRelease` et `lintRelease` réussissent ; lint signale zéro erreur et
cinq avertissements. Signatures APK v2/v3 et alignement vérifiés. Aucun appareil
Android n'était connecté : l'installation physique n'a pas été testée.

La passerelle publie la version 1.0.14 ; le téléchargement authentifié complet
a été relu et son empreinte vérifiée. Aucun redémarrage du serveur n'a été
nécessaire. Les fichiers précédents sont conservés dans
`toolchain/releases-staging/android-1.0.14/previous/`.

Preuves : `publication.json`, `signature.txt`, `previous-signature.txt`,
`badging.txt` et le manifeste de construction dans `client-android/dist/`.
