# Catalogue Hermes et sélecteur — correction du 11 octobre 2026

Windows/serveur **3.5.26** et Android **1.0.9/code 10** corrigent le catalogue
et le choix du modèle. Le serveur conserve le partage des connexions Hermes
avec les comptes Fred actuels et futurs, selon la décision de l’utilisateur.
Les historiques restent séparés et les trois actions du correcteur restent
directement sur Qwen.

## Correction du catalogue

La version précédente forçait `~/.hermes`. Le runtime Hermes installé utilise
`%LOCALAPPDATA%\hermes` sous Windows. Fred résout désormais ce dossier et son
profil actif avec les fonctions natives Hermes. Le diagnostic précédent sur
l’absence d’accès OpenAI décrivait le mauvais magasin de connexions.

Le profil actif actuel est `default`, avec `serveur-perso` et
`qwen3.8-flash-next-iq4-xs` comme modèle principal. Le bon magasin contient
également **61 modèles Nous Portal**, **59 OpenRouter** et **14 ChatGPT/Codex**
utilisables selon le catalogue natif, soit **134 modèles partagés**. La connexion
Copilot incomplète et les modèles refusés par cette version de Hermes sont
masqués dans les clients. Un Qwen qui pointe vers le même moteur local est
réutilisé avec le parcours Fred existant, pour conserver sa réservation GPU.

Dans **Clients → Modèles disponibles dans Hermes**, la console affiche le
profil et les modèles utilisables. Elle propose tous ces modèles automatiquement
ou permet une sélection explicite, avec recherche et liste défilante. Retirer
un modèle retire aussi son autorisation dans le serveur et le broker. Les
choix temporairement hors ligne restent enregistrés. La politique est incluse
dans les sauvegardes chiffrées. Aucune clé fournisseur n’est envoyée aux clients.

## Correction du menu

Les options du sélecteur sont conservées pendant les actualisations. Un nouveau
catalogue attend la fin du choix au lieu de reconstruire la liste ouverte.
Les modèles indisponibles sont retirés, sauf le choix d’une ancienne conversation
qui reste explicitement indisponible jusqu’à un autre choix de l’utilisateur.

Le test natif Android a aussi identifié la fermeture du dialogue provoquée par
des changements d’accessibilité ou de statut pendant une sélection. Le polling
du catalogue est désormais suspendu tant que le menu est ouvert, puis repris
à sa fermeture. Une réponse réseau déjà en cours attend également cette
fermeture avant de modifier l’interface. L’état de chargement est porté par
le statut adjacent. La liste conserve ainsi son défilement et son choix.

## Vérifications

| Parcours | Résultat |
| --- | --- |
| Catalogue, droits et profils | 27 tests dédiés et 36 régressions passent : profil actif natif, source stable des credentials, filtrage, choix admin, révocation, Qwen unique et sauvegarde/restauration chiffrée. [Preuve](catalogue-validation.json) |
| API et correcteur | 30 tests passent : catalogue authentifié, choix et contexte cloud, console authentifiée, correcteur direct et droits pendant les coupures. [Preuve](gateway-validation.json) |
| Isolation | 19 tests comptes/inférence/conversations passent. [Preuve](gateway-validation.json) |
| Clients communs | Listes de 120 modèles Windows/Android, choix clavier, polling, chargement, historique et 7 scénarios vocaux réussis. [Preuve](client-ui-validation.json) |
| Console admin | 13 contrôles navigateur passent : partage global/individuel, sélection des modèles, recherche, défilement, erreurs et actualisation immédiate. [Preuve](console-sharing-ui.json) |
| Android natif | 8 contrôles dans la WebView sur émulateur passent : 121 options, cinq actualisations différées, quatre défilements tactiles, choix natif, reprise après fermeture et réponse réseau déjà en cours. [Preuve](android-webview-picker.json) |
| APK signé | 31 contrôles passent : version et certificat conservé, signatures v2/v3, alignement 16K, ressources natives identiques, interface commune exacte, installation de la mise à jour et parcours modèles/correcteur. [Preuve](android-release.json) |
| Windows compilé | Sources embarquées, signature Ed25519, version PE, compatibilité updater et 481 fichiers natifs vérifiés ; autocontrôle et vraie fenêtre compilée passent. [Build](windows-build-validation.json), [fenêtre](windows-native-window.json) |

Un unique échange natif réel a utilisé **gpt-6-luna** via l’abonnement
ChatGPT/Codex et a répondu exactement **OK**. Le compte, le profil et l’historique
étaient temporaires ; Qwen et les outils étaient désactivés pour ce test.
Le broker et le SDK Codex ont donc été éprouvés avec la connexion réelle.
[Preuve du catalogue et de l’échange natif](catalogue-validation.json).
Les autres modèles sont ceux découverts par le catalogue natif Hermes ; ils
n’ont pas tous fait l’objet d’un appel d’inférence.

Les captures [Windows](selector-windows.png) et [Android](selector-android.png)
utilisent des catalogues synthétiques. Les contrôles Android natifs sont faits
sur émulateur x86_64 ; aucun nouvel essai physique ARM64 ou acoustique n’est
revendiqué pour cette correction.

## Publication

Windows/serveur **3.5.26** et Android **1.0.9/code 10** sont publiés sur ce serveur.
Les deux téléchargements authentifiés correspondent exactement aux fichiers
signés validés. Le catalogue client contient **134 modèles externes utilisables**
et Qwen local, conformément à la sélection de la console. Le partage global
est actif ; l’agent et la voix sont prêts. Qwen reste chargé avec les mêmes
processus, et les accès et réglages sont conservés.
[Contrôles de livraison](delivery-validation.json).
