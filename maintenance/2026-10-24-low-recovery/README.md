# Rétablissement du mode Low Phonon

À la demande de l’utilisateur, le mode Low reprend la boucle de conversation
et la lecture Phonon livrées en **3.5.39**, commit `75e8eb8`. Les fonctions de
réception des phrases, découpage de la réponse et lecture SSE Phonon sont
reprises de cette version. Les empreintes des blocs d’origine sont conservées
dans `restored-controller.json`. Les raccordements à la page Vocal, au volume
et au pont Android sont conservés. Le traitement Max reste distinct.

Les moteurs de reconnaissance Parakeet/Whisper et leurs modèles ne sont pas
changés. Le serveur conserve Phonon et la voix Tiphaine. La recherche web vocale
et ses sources restent raccordées ; aucun changement du routage serveur n’est
nécessaire pour la restauration du parcours Low.

## Régression reproduite

Les filtres ajoutés après la version stable pouvaient acquitter puis ignorer
une réponse reconnue pendant le calcul ou la lecture précédente. Une réponse
courte comme « Oui » était alors perdue, même si la reconnaissance fonctionnait.
Le test `--pre-restore-low` reproduit ce blocage : la seconde phrase est
acquittée, mais aucune seconde demande n’arrive au modèle. La boucle Low
restaurée transmet cette réponse et déclenche à nouveau Phonon.

Low reprend ainsi sa conversation continue, son interruption après reconnaissance
et son filtre d’écho d’origine. L’option et les filtres avancés restent propres
à Max. Sur Android, l’annulation d’écho native est utilisée lorsqu’elle est
disponible ; sinon le microphone se ferme pendant la lecture. Les commandes
muet/réactivation et raccrochage restent présentes.

## Vérifications et limites

- **Moteurs réels**, sans microphone : deux phrases françaises successives
  injectées en temps réel. Parakeet : deux transcriptions finales, environ
  24,4 s avec chargement et silences. Whisper Small : deux transcriptions finales,
  environ 22,4 s. Traces complètes : `parakeet.json` et `whisper.json`.
- **Interface Windows et Android** : les sorties de ces moteurs alimentent
  le parcours Low avec modèle et PCM simulés. Première phrase, réponse immédiate
  d’un mot, deux lectures Phonon, historique, muet, arrière-plan, reprise après
  erreur et sources web : succès.
- **Contrôle négatif** : sans délégation à la boucle classique, le scénario
  de réponse immédiate échoue comme attendu (`low-pre-restore-control.log`).
- **Max** : sa suite complète garde la gestion avancée des interruptions,
  tampons, annulations, préférences et erreurs. Les huit suites UI partagées
  passent. Le test Android complet conserve l’import, les sauvegardes, le chat
  et le correcteur. Le correctif du bandeau rouge de connexion reste présent.
- **Sources et livraison** : contrôles de sources et UX, treize tests Android,
  signatures existantes et vérification des téléchargements authentifiés.

Les traces de reconnaissance proviennent de vrais moteurs sur ce poste, mais
le son est injecté depuis un WAV public de test. Les tests de parcours utilisent
un serveur de test isolé. Ils ne constituent pas une validation acoustique des
microphones ou haut-parleurs des appareils de l’utilisateur, qui restent
inaccessibles ici. Le ralentissement intermittent signalé en dictée n’a pas
été reproduit avec ces deux phrases ; aucune modification de dictée n’est faite.

## Livraison

Windows **3.5.44** et Android **1.0.18/code 19**. Les clés et profils existants
sont conservés, les anciennes distributions restent dans le staging. La
publication utilise la sauvegarde chiffrée vérifiée et préserve les processus
Qwen. Les preuves finales sont `production.json` et `android-publication.json`.
