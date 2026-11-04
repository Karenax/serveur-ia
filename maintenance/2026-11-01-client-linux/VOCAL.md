# Client vocal Linux — révision 2

Correctif d’affichage : `markdown.js` était omis de la liste des ressources
Linux. Son absence interrompait la construction de la réponse HTTP du chat,
ce qui affichait `ERR_EMPTY_RESPONSE` dans Qt. Il est désormais inclus dans
l’archive et son manifeste. Une ressource absente ou mal encodée renvoie aussi
une erreur explicite de réinstallation. Archive reconstruite sans nouveaux tests.

Correctif d’installation : l’option `--only-binary=:all:` bloquait `proxy_tools`,
dépendance de pywebview disponible uniquement en sources sur PyPI. L’installateur
autorise maintenant les sources pour ce seul paquet, épinglé à 0.1.0, et conserve
les paquets binaires pour les autres dépendances. Les erreurs pip restent visibles
et sont suivies d’un message de reprise sans trace Python. Archive reconstruite ;
aucun nouveau test exécuté, conformément à la demande de l’utilisateur.

La livraison `Kiara-linux-amd64-3.5.55-vocal.tar.gz` ajoute le vocal au premier
paquet Linux. La version applicative reste celle des sources partagées ;
`linux_revision: 2` distingue cette livraison dans son manifeste.

## Fonctionnement

- La dictée et le vocal Low réutilisent le vrai `ConversationService`, le worker
  de reconnaissance et les modèles Parakeet v3/Silero/Smart Turn. Cache partagé
  dans le dossier XDG de Kiara, modèles vérifiés avant ouverture du microphone.
- Sous Linux, le worker démarre avec le Python du paquet. Il lance `parec` pour
  recevoir du PCM mono 16 kHz depuis PipeWire/PulseAudio. Aucun fichier audio
  temporaire, adaptateur Windows ou Wine n’est utilisé.
- La conversation transmet le texte reconnu par l’accès Kiara existant et lit
  les trames PCM de synthèse du serveur avec le même lecteur Web Audio.
- Pendant la réponse, la capture Linux se ferme et les reconnaissances tardives
  sont abandonnées ; elle reprend après la lecture et sa courte marge de fin.
  L’interruption par parole est désactivée. Couper le micro garde la session,
  ferme la capture et attend sa confirmation. Raccrocher termine le worker.
- Max est proposé sur le serveur Kiara ; le sélecteur Linux ne propose pas le
  complément local Windows. Les routes serveur et la détection de parole
  existantes sont conservées. En Max, le son est transmis au serveur ; le Low
  et la dictée conservent la reconnaissance sur le PC.
- Le petit modèle public épinglé du mot d’appel est embarqué et vérifié pendant
  la construction. Le caractère expérimental du mot d’appel français est conservé.

Le [guide](../../client-linux/README.md) indique les dépendances, l’installation,
le téléchargement initial des modèles et les contrôles à exécuter sur Linux.
Le premier paquet sans vocal reste disponible pour conserver la trace et le retour.

## Validation

Les tests Python du client et des workers, les tests de navigateur partagés,
le contrôle des sources et le contrôle UX sont exécutés depuis Windows. Journaux :

- `toolchain/test-results/linux-vocal-client-regression.txt` : 104 tests client.
- `toolchain/test-results/linux-vocal-worker-regression.txt` : 46 tests worker,
  dont PCM fragmenté, capture absente/déconnectée, attente bornée et fermeture
  forcée du processus, ainsi que pause/reprise/mute du worker en mode Linux simulé.
- `toolchain/test-results/linux-vocal-ui-regression.txt` : tests partagés,
  dont le parcours Linux avec reconnaissance et PCM synthétiques. Le test vérifie
  un échange Low, la lecture, l’écoute suspendue/reprise, mute/unmute, Max serveur,
  le raccrochage, les brouillons et les options Windows rendues indisponibles.
- `toolchain/test-results/linux-vocal-recognition-fixture.txt` : vraie inférence
  Parakeet sur un WAV public de test synthétisé localement, sans microphone :
  phrase française de 6,88 s reconnue, environ 1 s de calcul dans cette exécution.
  Ce résultat mesure le moteur installé sous Windows, pas ses performances Linux.

Les ressources Android ont été régénérées via `Prepare-Assets.py` après examen
de leur diff : seuls les changements des sources partagées de ce travail étaient
à propager. Le contrôle `--check` réussit. Les fichiers de production n’ont pas
été remplacés. La terminologie des commandes et la navigation du vocal sont les
mêmes que sous Windows ; les différences Linux sont limitées au système audio,
à l’écoute alternée, aux mises à jour manuelles et au traitement Max sur le serveur.

## Limites de la preuve

Aucun Linux exécutable n’est installé sur le poste de construction. Les tests de
capture et du parcours oral utilisent des périphériques ou réponses synthétiques.
Ils ne valident donc ni le périphérique réel, ni PipeWire/PulseAudio, ni la fenêtre
Qt sur un bureau Linux. À la demande de l’utilisateur, les vérifications ont été
arrêtées et aucun essai matériel Linux n’a été entrepris ; la suite complète UI
relancée pour cette révision a été interrompue avant sa fin. Les résultats déjà
obtenus restent conservés dans les journaux. Si une validation est souhaitée
ultérieurement sur le PC cible, exécuter `./start.sh --audio-self-test`,
installer les modèles puis essayer une conversation, couper/réactiver le micro et
raccrocher. Le contrôle `./start.sh --self-test --conversation-self-test` vérifie
également les transitions du microphone avec le moteur installé.

La sélection d’une zone d’écran et le complément Max local ne sont pas portés.
Les images enregistrées restent joignables dans le vocal. Les paquets sont
identifiés par leurs empreintes ; aucune signature de publication Linux n’est ajoutée.
