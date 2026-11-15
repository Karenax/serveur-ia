# Lancer une réunion et obtenir son compte rendu

Dans Agent sur le port 8001, ouvrir **Réunions**, puis **Nouvelle séance**.
Choisir le projet de la séance ; une séance sans projet peut être enregistrée,
puis rattachée depuis sa préparation avant de publier son compte rendu.

## Enregistrer

1. Choisir la source audio : **En salle · microphone**, **À distance · son du PC**
   ou **À distance · son du PC + ma voix**.
2. Ouvrir **Périphériques** pour choisir explicitement le microphone et la
   sortie sonore utilisés. Le son du PC correspond au mix de cette sortie :
   les autres applications qui y diffusent du son peuvent aussi être captées.
3. Cliquer **Démarrer la réunion**. Vérifier l’état d’enregistrement et le
   compteur. Le microphone s’ouvre seulement au démarrage demandé.
4. Utiliser **Pause**, puis **Reprendre** si nécessaire. Pour finir, cliquer
   **Arrêter et conserver** et attendre la confirmation de conservation.

L’audio natif est conservé en Ogg/Opus compressé. Changer de page ne remplace
pas l’arrêt : le contrôle global de la capture reste disponible. En cas de
retrait de périphérique, l’interruption est signalée et les fragments déjà
sauvegardés restent conservés.

## Relire et produire le compte rendu

Ouvrir **Transcription**. Le texte du direct est **provisoire**. Après arrêt,
la transcription complète peut être lancée avec **Transcrire et séparer les
voix** dans la partie audio. Si des fragments restent en attente, le Studio
propose aussi **Transcrire l’audio conservé**. Ces traitements utilisent les
fichiers sauvegardés et n’ouvrent pas de microphone.

Corriger le texte et les noms d’interlocuteurs ; ne pas attribuer une identité
sur la seule proposition du moteur. Utiliser **Enregistrer les corrections**,
puis **Valider la transcription**. Dans **Compte rendu**, cliquer **Préparer le compte rendu**,
relire son contenu et ses sources, puis **Valider et enregistrer le compte rendu**.
La publication doit correspondre à la révision de transcription validée.
La création de tâches à partir des actions reste une commande explicite.

## Limites acceptées

Le 22 octobre 2026, l’utilisateur a accepté la livraison avec transcription
directe provisoire, relecture humaine obligatoire et limites documentées.
Le bruit peut déformer un terme technique ; des paroles simultanées peuvent
faire perdre une négation ou une réserve. Vérifier particulièrement les valeurs,
unités, engagements et refus avant publication. Le délai du direct dépend du
profil et du poste ; les résultats mesurés figurent dans
[Direct CPU](51_FORESIGHT_DIRECT_CPU.md).

**Réglages → Autres réglages → Réunions et transcription** présente les moteurs
et le calcul du direct. Le CPU reste le choix conservé ; le GPU est une option
en essai. La disponibilité d’un moteur ne garantit pas une transcription exacte.
La capture et la transcription sont distinctes de la génération du compte rendu.

La chaîne capture → STT CPU → EG2 → Gemma a été vérifiée hors ligne sur des
phrases fictives avec coupure réelle. Au retour du serveur réseau, le modèle
de génération local est déchargé. Les imports Google Drive sont exclus de la
livraison à la demande de l’utilisateur ; le test physique de disque plein est
également exclu. La gestion des erreurs et la conservation des fragments restent actives.
