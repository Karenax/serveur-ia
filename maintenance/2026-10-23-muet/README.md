# Microphone muet pendant une conversation Windows — 3.5.38

Le bouton `Muet` apparaît à côté de `Raccrocher` pendant une conversation.
Il se commande au clic ou au clavier et expose son état avec `aria-pressed`.
L'état « Microphone coupé » est confirmé seulement après la fermeture effective
du périphérique par le worker. Une erreur conserve l'état connu et permet de
réessayer. Les états en attente désactivent la bascule, sans bloquer le raccrochage.

La commande locale vérifie la session propriétaire et exige un booléen. Elle ne
s'applique qu'au mode conversation, pendant le chargement ou l'écoute. Une
commande pendant le chargement est conservée et transmise au worker avant
l'ouverture du microphone. Aucun son, fichier ou texte n'est envoyé au serveur
pour réaliser la bascule.

Le worker ferme le périphérique AEC sur le thread qui l'a ouvert et ne le lit
plus pendant la pause. Il conserve son modèle et sa session. La reprise ouvre
une nouvelle capture. Une phrase inachevée et ses résultats de décodage tardifs
sont abandonnés par un compteur de génération ; une nouvelle capture ne reprend
pas l'audio ancien. Les identifiants des tours restent monotones.

La bascule ne touche ni à la requête Qwen ni à la lecture de Phonon. Fred peut
terminer sa réponse pendant que le micro est coupé. Les transcriptions ne peuvent
alors plus interrompre Fred ni déclencher une nouvelle question ; les envois
en attente reprennent après réactivation. Le raccrochage et la révocation ferment
toujours la session. Chaque nouvelle conversation commence avec le micro actif.

La voix Tiphaine, validée par l'utilisateur, est déjà active sur le serveur ;
voir [les preuves de sélection et d'activation](../2026-10-23-tiphaine/README.md).
Le changement de voix seul ne demande pas de nouveau client. Le bouton `Muet`
nécessite l'EXE Windows 3.5.38.

## Vérification

Les tests du service vérifient propriété, booléens, état en attente et exclusion
du mode dictée. Le test du worker vérifie fermeture sur le thread propriétaire,
arrêt des lectures et reprise avec une nouvelle capture. Les tests UI vérifient
la bascule au clavier pendant une lecture, la conservation de cette lecture et
de la session, l'absence d'interruption par une transcription pendant la pause,
et un échec de commande qui ne déclare jamais le microphone fermé à tort.
Ces tests UI utilisent des trames ASR et audio simulées.

L'EXE compilé exécute aussi un vrai cycle natif : ouvrir, couper le microphone,
vérifier que le nombre d'échantillons reste fixe, réactiver puis fermer. Il ne
contacte pas Qwen et ne conserve aucun enregistrement. La qualité acoustique
d'un microphone humain n'est pas mesurée par ce contrôle.

```powershell
& '.\client-qwen\Build-Client.ps1' -DistributionDirectory "$PWD\toolchain\releases-staging\windows-3.5.38" -SkipManifest
# Exécuter via Python/subprocess pour attendre la sortie de l'EXE graphique.
& '.\Strata-src\.venv\Scripts\python.exe' -c "import subprocess; subprocess.run([r'toolchain/releases-staging/windows-3.5.38/Accès serveur Fred.exe','--self-test','--conversation-self-test','--result',r'toolchain/releases-staging/windows-3.5.38/native-mute.txt'],check=True,timeout=60)"
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/2026-10-23-muet/verify.py
npm --prefix client-qwen test
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/check_sources.py
```

`exe-proof.json` et `ui-proof.json` gardent les résultats. `activate.py` publie
le binaire signé et vérifie la disponibilité de Tiphaine ainsi que la conservation
de Qwen, des clés, des données et de la programmation des sauvegardes. Ne pas
relancer une activation déjà démarrée sans examiner ses preuves.
