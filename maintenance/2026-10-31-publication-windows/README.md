# Mise à jour Windows Kiara 3.5.55 — 31 octobre 2026

Publication demandée par l’utilisateur après les changements du mode Max et
de la page de conversation vocale.

## Changements livrés

- Choix et mémorisation du dossier de téléchargement Max sur le PC.
- Correction de l’encodage des commandes envoyées aux compléments Windows :
  les accents, cédilles et apostrophes françaises restent intacts, y compris
  avec le complément Max déjà installé. Aucun nouveau téléchargement des
  modèles n’est nécessaire pour ce correctif client.
- Retrait du bouton « Ouvrir le chat » dans Vocal ; échanges écrits dans un
  panneau ouvrable à droite de l’animation, sous celle-ci sur petit écran.

## Publication vérifiée

`production.json` confirme la version **3.5.55** réellement servie par le serveur,
la vérification de sa signature et le téléchargement authentifié complet :
115 410 978 octets, SHA-256
`a785bf1d8a90ed166ea6a93a18fa59d58dca61c2d82e934b095f0a9801fc9d92`.

Un client personnel actif a été préparé et testé avec son profil. Les accès
et clés existants sont conservés. Les empreintes des données utilisateur,
réglages et clés et la programmation des sauvegardes sont identiques avant
et après. Les deux processus Qwen chargés sont préservés. Seule l’interface
serveur et sa passerelle ont été redémarrées avec la procédure existante.

La sauvegarde chiffrée préalable est vérifiée et copiée sur le NAS
(`sauvegarde-avant.json`). L’ancienne distribution est conservée dans `previous/` ;
le reconditionnement existant conserve aussi le retour des EXE personnels.

Android et le pack Max publié restent inchangés. La correction côté réception
dans `worker_protocol.py` sera incluse lors d’une prochaine reconstruction du
pack ; la correction côté client livrée ici protège déjà les packs existants.

## Vérifications

- Construction par `Build-Client.ps1`, dans un dossier de staging propre à 3.5.55.
- Auto-test natif de l’EXE de base et de l’EXE personnel avec son profil.
- `check_frozen.py` compare le JavaScript et le CSS embarqués aux sources,
  vérifie la version et le choix de dossier, puis exécute le writer extrait
  de l’archive Python de l’EXE : la phrase de Léa reste intacte en UTF-8,
  CP1252 et CP850 (`frozen-validation.json`).
- Tests UI complets et vérifications visuelles du panneau, décrits dans
  `maintenance/2026-10-31-vocal-panneau/README.md`.
- Tests d’encodage, runtime vocal, protocole et emplacement de mise à jour.
- Manifeste de construction dans
  `toolchain/releases-staging/windows-3.5.55/build-manifest.json`.

Les utilisateurs peuvent ouvrir **Mises à jour**, cliquer sur **Vérifier les
mises à jour**, puis **Mettre à jour le client**. Cette publication rend la
version disponible ; elle ne force pas la fermeture des clients en cours.

Les scripts `publish.py --prepare` et `publish.py` ont déjà été exécutés :
ne pas les relancer sans examiner les preuves. `publish.py --verify` permet
de rejouer les vérifications en lecture.
