# Utiliser l’assistant Kiara

Pour Windows et le web privé, ce guide prend **Kiara 4.0.8** comme référence.
Les indications Android ci-dessous concernent les versions antérieures à la
qualification finale de l’interface commune. Une mise à jour Android s’installe
par-dessus l’application existante pour conserver le profil et les conversations.

Les tâches, comptes rendus programmés et synthèses automatiques ont été retirés
du serveur et du client Windows. Les rappels et **Faire le point** restent
disponibles. L’APK Android publié le 26 octobre peut encore afficher les anciennes
actions : elles ne sont plus prises en charge par le serveur. Leurs retraits
d’interface sont dans les sources Android, en attente d’un nouvel APK.

## Ouvrir Projets et Conversations dans Kiara

Télécharger **Kiara 4.0.8 pour Windows** depuis la console serveur. Le code de
connexion est disponible dans **Clients & accès**. Ouvrir **Projets** pour voir
le portefeuille autorisé et la fiche à quatre rubriques. Utiliser **Conversations**
pour retrouver l’historique, reprendre un brouillon ou choisir un projet avant
d’envoyer un message. Le mode éphémère permet un échange sans conservation dans
l’historique.

- **Mails.** Les nouveaux messages Thunderbird arrivent via la liaison du poste associé. Classer les propositions dans **À classer**. Après un rejet, retrouver le message dans **Options → Dossier → Mails rejetés**. Depuis un mail classé, **Détails du mail → Préparer une réponse** crée un brouillon dans Thunderbird.
- **Réunions.** Capturer le microphone ou la sortie système dans le Studio, arrêter la capture, puis relire la transcription et le compte rendu avant de publier.
- **Assistant.** Choisir un projet et ouvrir les citations pour consulter les sources. **Arrêter la réponse** interrompt la demande dès la recherche des sources.

[Architecture et validations de Kiara](ARCHITECTURE-ACTUELLE.md#projets-et-conversations)

## Choisir son espace

Sous Windows, ouvrir **Réglages → Mémoire et rappels**, puis choisir
**Personnel** ou un projet. Les souvenirs,
rappels et commandes concernent cet espace. Pour une demande dans le chat ou en
parlant, choisir le projet de la conversation avant l’envoi. Les données de deux
accès personnels restent séparées, même si leurs appareils appartiennent à la
même personne.

## Retenir, corriger ou oublier

Demander « Retiens que je préfère les réponses courtes » ou « Qu’as-tu retenu ? ».
Pour corriger ou oublier, désigner précisément le souvenir ; Kiara doit demander
une précision si plusieurs cibles conviennent. La confirmation suit
l’enregistrement, pas une simple promesse dans la réponse.

La rubrique **Souvenirs** permet aussi de consulter, modifier et oublier une
information directement. Pour appliquer une préférence à tous ses projets,
choisir **Personnel**, le type **Préférence**, puis cocher **Appliquer cette
préférence à tous mes projets**. Ce choix n’ouvre pas l’historique personnel aux
autres projets.

Oublier un souvenir ne supprime pas la discussion source ni les anciennes
sauvegardes chiffrées. Kiara masque les anciens passages correspondants dans son
contexte ; ce filtrage ne garantit pas l’effacement de toute paraphrase. Les
anciens fichiers de mémoire Hermes, s’il en existe, restent proposés à la
consultation pour une reprise manuelle.

## Créer une note en parlant

Ouvrir **Vocal** avec **Qwen local**, puis démarrer la conversation. Dans un
projet, demander « Crée une note avec ces points ». La note rejoint les documents
du projet.

Les commandes écrites et orales utilisent les mêmes données et droits. Une
opération déjà enregistrée ne peut pas être annulée simplement en raccrochant.
Les conversations écrites passent par Hermes ; le vocal utilise directement
Qwen local avec les commandes Kiara contrôlées.

## Programmer un rappel

Demander « Rappelle-moi demain à 18 heures de reprendre ce dossier » ou ouvrir
**Nouveau rappel**. Vérifier date, heure, fuseau et répétition :
une fois, chaque jour, chaque semaine ou du lundi au vendredi.

**Me rappeler** fonctionne sans modèle et sans projet obligatoire. Les rappels
à venir peuvent être modifiés ou annulés. Le serveur doit fonctionner pour
traiter l’échéance. Un rappel manqué est signalé une fois. Les répétitions suivent
le calendrier local et le fuseau choisi.

Les alertes se retrouvent dans **Notifications**. Leur ouverture affiche le
rappel et son heure prévue. Sur Android, l’option **Relever les alertes même
lorsque Kiara est fermée** active des relevés facultatifs, avec autorisation des
notifications. Android gère leur exécution, avec un intervalle minimal de quinze
minutes : une heure précise n’est pas garantie. Sans réseau, téléphone éteint ou
application forcée à l’arrêt, retrouver les événements à la prochaine connexion.

## Reprendre un projet

Choisir un projet dans **Réglages → Mémoire et rappels**. **Faire le point** retrouve ses
décisions confirmées, souvenirs, documents et discussions récentes.
Vérifier les sources et distinguer une décision confirmée d’une proposition.

## Joindre une image au vocal

Dans **Vocal**, utiliser **Choisir une image**, **Prendre une photo** sur Android
ou **Choisir une capture** sur Windows. Sur Windows, sélectionner une région du
bureau ; Échap annule la sélection. Vérifier la prévisualisation avant de poser
la prochaine question. **Retirer l’image** permet de poursuivre sans elle.

L’image est jointe à ce tour et conservée dans la discussion. Elle ne devient pas
automatiquement un souvenir. Raccrocher ou changer de conversation empêche une
ancienne capture de rejoindre la question suivante. Le modèle doit accepter les
images ; la reconnaissance visuelle peut allonger le temps de réponse.

## Essayer « Bonjour Kiara »

Dans les réglages vocaux, cocher **Attendre « Bonjour Kiara » sur cet appareil**.
La détection est locale et garde le microphone actif jusqu’à l’appel ou à l’arrêt.
Elle est distincte de la conversation. Après un appel, réactiver l’attente si
nécessaire. Le bouton de démarrage manuel reste disponible.

Cette fonction est **expérimentale**, désactivée initialement et limitée à
l’application visible. Le nom « Kiara » seul n’est pas la phrase prévue. Le
passage en arrière-plan arrête la détection ; l’activation Android verrouillé
n’est pas fournie. Les essais synthétiques ne remplacent pas une vérification
avec sa voix, son microphone et le bruit de la pièce.

## Vérifications et limites

Les vérifications de la 4.0.8 sont documentées dans la
[bascule Windows et web privé](audits/2026-11-15-fusion-kiara/BASCULE.md).
Les essais de l’introduction des outils de l’assistant sont dans le
[rapport historique](maintenance/2026-10-25-assistant-integration/README.md).
Les essais physiques micro/caméra, veille et batterie Android restent à réaliser.
Les temps de réponse peuvent rester longs ; aucune amélioration générale de
latence n’est annoncée. Le [plan de suivi](PLAN-INTEGRATION-ASSISTANT-KIARA.md)
conserve les compléments et validations encore nécessaires.
