# Utiliser l’assistant Kiara

Version publiée : **serveur/Windows 3.5.52**, **Android 1.0.23, code 24**.
Mettre le client à jour pour retrouver les nouvelles commandes et la rubrique
**Mémoire et rappels**. Sur Android, installer la mise à jour par-dessus
l’application existante pour conserver son profil et ses conversations.

## Choisir son espace

Dans **Mémoire et rappels**, choisir **Personnel** ou un projet. Les souvenirs,
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

## Créer une note ou une tâche en parlant

Ouvrir **Vocal** avec **Qwen local**, puis démarrer la conversation. Dans un
projet, demander « Crée une note avec ces points » ou « Crée une tâche pour
analyser ce dossier ». La note rejoint les documents du projet ; la tâche et son
résultat se retrouvent dans **Tâches**. Il est aussi possible de consulter les
tâches ou de demander la pause ou l’annulation d’une tâche clairement désignée.

Les commandes écrites et orales utilisent les mêmes données et droits. Une
opération déjà enregistrée ne peut pas être annulée simplement en raccrochant.
Les conversations écrites passent par Hermes ; le vocal utilise directement
Qwen local avec les commandes Kiara contrôlées.

## Programmer un rappel ou un compte rendu

Demander « Rappelle-moi demain à 18 heures de reprendre ce dossier » ou ouvrir
**Nouveau rappel ou compte rendu**. Vérifier date, heure, fuseau et répétition :
une fois, chaque jour, chaque semaine ou du lundi au vendredi.

**Me rappeler** fonctionne sans modèle et sans projet obligatoire.
**Préparer un compte rendu du projet** demande un projet et utilise la file
d’analyse du serveur. Les rappels à venir peuvent être modifiés ou annulés.
La pause/reprise dédiée d’un rappel reste à ajouter.

Le serveur doit fonctionner pour traiter l’échéance. Après un arrêt, un rappel
manqué est signalé une fois ; les comptes rendus retardés ne sont pas lancés en
rafale. Une heure locale ambiguë au changement d’heure doit être précisée ; une
heure récurrente absente au passage d’été est sautée.

Les alertes se retrouvent dans **Notifications**. Leur ouverture affiche le
rappel et son heure prévue. Sur Android, l’option **Relever les alertes même
lorsque Kiara est fermée** active des relevés facultatifs, avec autorisation des
notifications. Android gère leur exécution, avec un intervalle minimal de quinze
minutes : une heure précise n’est pas garantie. Sans réseau, téléphone éteint ou
application forcée à l’arrêt, retrouver les événements à la prochaine connexion.

## Reprendre un projet

Choisir un projet dans **Mémoire et rappels**. **Faire le point** retrouve ses
décisions confirmées, souvenirs, tâches, documents et discussions récentes.
**Préparer une synthèse** demande un résumé au modèle et laisse travailler le
serveur pendant que l’on poursuit sa navigation.

Vérifier les sources et distinguer une décision confirmée d’une proposition.
Un projet modifié rend sa synthèse précédente périmée. L’option **Actualiser la
synthèse après les changements du projet** est désactivée initialement ; elle
peut utiliser le modèle en arrière-plan et doit être activée selon les besoins.

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

Les tests logiciels, les paquets signés et leur publication sont documentés dans
le [rapport d’intégration](maintenance/2026-10-25-assistant-integration/README.md).
Les essais physiques micro/caméra, veille et batterie Android restent à réaliser.
Les temps de réponse peuvent rester longs ; aucune amélioration générale de
latence n’est annoncée. Le [plan de suivi](PLAN-INTEGRATION-ASSISTANT-KIARA.md)
conserve les compléments et validations encore nécessaires.
