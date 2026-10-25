# Interruption facultative et délai de réponse — 23 octobre 2026

Windows 3.5.40 ajoute la case « Autoriser les interruptions vocales » à proximité
des commandes de conversation. Elle est décochée par défaut. Son choix est
mémorisé dans les préférences locales chiffrées du PC, avec validation booléenne.
Muet et Raccrocher conservent leur fonctionnement.

Le choix du raisonnement est masqué pendant l'appel et réapparaît au raccrochage
avec son niveau écrit précédent. La conversation conserve la réflexion désactivée
dans la requête client et sur le serveur ; les délais ci-dessous sont déjà mesurés
sans raisonnement.

Lorsque la case est décochée, les transcriptions provisoires et finales reçues
pendant le calcul ou la lecture ne déclenchent ni annulation, ni message suivant.
Les identifiants des prises de parole entendues pendant la réponse sont retenus
pour rejeter aussi leurs transcriptions finales tardives. Une courte marge de
350 ms après le son couvre la fin de lecture et la détection de parole retardée.
L'utilisateur peut ensuite poser sa prochaine question normalement.
Une sauvegarde d'historique qui se poursuit après la fin du son ne bloque pas la
réception de cette question : elle reste en attente et part une seule fois lorsque
l'enregistrement est confirmé.

Quand la case est cochée, les interruptions restent possibles. Une transcription
finale isolée doit désormais confirmer une parole, comme la transcription
provisoire : plusieurs mots, ou une commande telle que « stop » ou « attends ».
L'ancienne branche finale annulait systématiquement la réponse en cours.

## Où passe l'attente ?

`measure_model.py` utilise le modèle déjà chargé, sans ouvrir d'historique ni
modifier les réglages. Deux demandes fictives via Strata local donnent :

| Mesure | Demande 1 | Demande 2 |
| --- | ---: | ---: |
| Premier texte Qwen | 2,214 s | 2,480 s |
| Première phrase complète | 2,510 s | 2,697 s |
| Réponse complète | 2,801 s | 3,231 s |

Le modèle chargé est `qwen3.8-flash-next-iq4-xs`. Il contribue donc nettement au
délai, même avec réflexion désactivée. Ces deux demandes courtes ne mesurent ni
le transport du client, ni son historique réel, ni sa recherche documentaire.
Elles ne démontrent pas qu'un autre modèle serait globalement préférable.

L'essai Phonon natif précédent avec Tiphaine avait mesuré un premier son en
0,110 s (`../2026-10-23-tiphaine/native-validation.json`). Cette mesure ne comprend
pas le réseau. Phonon et la voix Tiphaine restent les seuls utilisés pour la
synthèse de la conversation Windows.

`measure_asr.py` fournit une phrase synthétique en temps réel, sans microphone.
Sur ce poste, le texte final apparaît 2,001 s après la dernière tranche sonore
avec les anciens délais, contre 1,401 s avec les nouveaux ; le texte complet
reconnu reste identique. Il s'agit d'un seul échantillon, dans un ordre fixe, avec
des effets possibles de chauffe et de charge. Ce résultat n'est pas un benchmark
représentatif des accents, bruits, pauses humaines ou PC clients.

## Réductions du délai

- La première vérification de fin de phrase passe de 850 à 650 ms de silence
  confirmé. Le repli passe de 2,5 à 1,6 s si Smart Turn n'est pas convaincu.
  Les pauses longues peuvent donc terminer une intervention plus tôt. La dictée
  manuelle conserve son délai et son envoi explicite.
- La lecture peut commencer sur un premier groupe de mots sans ponctuation :
  après 600 ms de texte disponible, ou vers 80 caractères. Les mots en cours
  restent dans le tampon et le reste suit en phrases. Cela évite d'attendre une
  longue première phrase entière. Les blocs de code ouverts restent exclus.

Ces réductions ne garantissent pas un délai précis de bout en bout. Elles
conservent la sauvegarde avant envoi, les erreurs de réseau et les reprises.

## Vérifications et livraison

La suite `test_conversation_ui.cjs` couvre calcul, audio réellement planifié,
bruit, transcription tardive, reprise d'écoute, interruption activée, choix
persistant dans les deux sens, lecture avant ponctuation, Muet, reconnexion et
révocation. Le transport ASR et les trames audio y sont simulés. La capture
`windows-interruptions-desactivees.png` contient uniquement des données fictives.

`verify.py` vérifie l'EXE, les préférences chiffrées, les mises à jour, les commandes
vocales, le microphone simulé et la reconnaissance réelle du worker compilé sur
une phrase synthétique. Les preuves de publication sont produites par
`activate.py` : clé de signature existante, copie de retour arrière, sauvegarde
chiffrée vérifiée, données, clés et processus Qwen préservés.

Les ressources Android partagées sont régénérées et leurs parcours vérifiés ;
le mode conversation de ce fichier reste spécifique à Windows. Aucun nouvel
APK ni nouveau moteur vocal n'est publié dans cette livraison.
