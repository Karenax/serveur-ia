# Max : prononciation française — 25 octobre 2026

Le client utilisait Qwen3-TTS CustomVoice avec `speaker=serena`, même avec
`language=french`. Serena est un profil dont la langue native est le chinois :
https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice

Le complément Max passe à Qwen3-TTS **Base 1.7B Q4_K_M**, avec une référence
fr-FR stable et sa transcription. Il ne sélectionne plus un profil chinois,
anglais ou japonais. La référence est un échantillon synthétique français déjà
produit localement avec le préréglage Tiphaine de Phonon. Sa provenance, ses
versions et les licences des sources sont livrées dans `voices/fr-fr/NOTICE.txt`
et `reference.json`. Aucun enregistrement utilisateur n'est distribué.

La synthèse Max reste entièrement assurée par Qwen3-TTS. Phonon n'est pas chargé
pour Max. Le moteur calcule une fois les latents de référence puis les réutilise
pour les différentes phrases, avec libération à la fermeture. Une référence
manquante, corrompue ou un ancien modèle provoque une erreur explicite, sans
retour implicite à Serena. La préparation du moteur Python historique utilise
également Base et le même conditionnement français.

Le runtime signé passe à l'API 5, révision `vulkan-q4-550bf7639ad29caf`.
Windows 3.5.50 propose « Mettre à jour Max » pour les compléments précédents,
tout en laissant une installation existante utilisable. Les critères GPU, la
sélection AMD/NVIDIA et le maintien de Max après un test lent sont conservés.

## Téléchargement et migration

Le modèle de synthèse change ; le codec et les modèles de reconnaissance restent
réutilisables. Pour une installation précédente complète, la mise à jour annonce
**1 265 686 849 octets** à télécharger et **1 327 064 912 octets** réutilisés.
Le client conserve la demande de téléchargement avec affichage de la taille.
Aucun téléchargement de modèle n'est ajouté à l'EXE de base.

Le modèle Base est épinglé au dépôt Serveurperso/Qwen3-TTS-GGUF, commit
`b7ee2e8c7459c3bea99da23e3d178125a7d1713c`, fichier
`qwen-talker-1.7b-base-Q4_K_M.gguf`, SHA-256
`ea393ebaf2167ea23ce9fc18b093822851358a950d7075cd47ab4f6ce23e887d`.

Après mise à jour Windows : **Vocal → Réglages → Max → Mettre à jour Max**.
Une installation serveur distincte nécessite aussi la mise à jour de son
complément avec `client-voice/prepare_max_pack.py --server --download` ; son moteur
n'a pas été rechargé automatiquement. Low et la voix serveur désactivée restent
dans leur état précédent. Android ne propose pas Max et ne nécessite pas de
nouvelle APK pour ce correctif.

## Vérifications

- 85 tests Python client, 35 tests vocal et 5 tests serveur Max passent.
- Les scénarios UI Max et installation passent : taille avant téléchargement,
  annulation, reprise, choix explicite malgré un benchmark lent, stockage,
  suppression et protection pendant un appel.
- Le test de migration vérifie qu'un ancien modèle CustomVoice n'est pas repris
  depuis le cache comme modèle Base. Les poids Low restent indépendants.
- Le paquet final signé a été installé dans un dossier de test, puis ses deux
  exécutables ASR/TTS ont été lancés : génération PCM et transcription réelles,
  fermeture propre et déchargement des processus. Voir `pack-validation.json`.
- Deux échantillons français sont correctement retranscrits, à la ponctuation
  près : `french-1.wav`, `french-2.wav`, `transcriptions.json`.
- Les tests ABI vérifient les paramètres français, l'absence de speaker imposé,
  la réutilisation des latents et leur libération unique ; les références invalides
  sont rejetées.
- Contrôles de sources passants ; contrôle UX avec les 9 avertissements existants
  de textes longs de la console, sans nouveau parcours visuel.

Les essais audio réels ont utilisé le CPU de ce serveur, sans déplacer Qwen vers
un autre GPU. Ils vérifient la génération et l'intelligibilité, pas une note
subjective d'accent ni les performances d'une RX 7800 XT distante. L'échantillon
permet à l'utilisateur d'apprécier la voix. Le premier chargement comprend
l'extraction de la référence ; les phrases suivantes réutilisent son résultat.

La distribution précédente est conservée dans `previous-pack/`. Les preuves de
publication et de préservation des processus, accès et données sont enregistrées
dans `pack-publication.json`, `publication.json` et `production.json`.

La compilation Windows a produit l'EXE attendu. La collecte initiale de
l'inventaire a dépassé le délai de lancement de `java -version` ; cette commande
puis `maintenance/build_manifest.py` ont été relancées avec succès, sans nouvelle
compilation ni modification du binaire. Preuve : `build-manifest-retry.log`.

Au redémarrage du relais, le premier contrôle de disponibilité a échoué. Une
relance de `Start-Interface-Qwen.ps1 -SansNavigateur -PreserverEtatModele` a
confirmé le service disponible ; la vérification de livraison a ensuite été
reprise sans republier les fichiers. `delivery-verification.log` et
`production.json` confirment versions, signatures, téléchargements complets,
processus Qwen, accès et données préservés. Aucun worker Max de test ne reste
chargé.
