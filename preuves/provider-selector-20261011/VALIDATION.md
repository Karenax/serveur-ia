# Choix par fournisseur dans la console admin — 11 octobre 2026

Dans **Clients → Modèles disponibles dans Hermes**, les cases par fournisseur
sélectionnent ou retirent en une action tous les modèles utilisables du groupe.
Décocher **Nous Portal** conserve les modèles choisis des autres fournisseurs.
Un état intermédiaire et un compteur indiquent une sélection partielle.

Le bouton **Tout désélectionner** enregistre une sélection externe vide, y
compris les anciens choix temporairement hors ligne. Qwen local reste proposé
aux clients. Le partage global ou individuel des abonnements reste conservé.

Les deux contrôles utilisent la sélection explicite existante `exposed_models` :
ils passent du mode automatique au mode manuel. Une recherche ne limite pas
leur portée. Les commandes sont désactivées pendant l’enregistrement ; une
erreur de sauvegarde affiche un message puis relit le réglage du serveur.
Réactiver **Proposer tous les modèles utilisables de Hermes** rétablit le mode
automatique, y compris pour les futurs modèles.

Les **20 contrôles navigateur passent**, dont sept nouveaux scénarios pour les
fournisseurs et la remise à zéro. La [preuve](console-provider-ui.json) utilise des fournisseurs,
comptes et réponses synthétiques avec tous les scripts réels de la console.
Ils vérifient les actions par groupe, la sélection partielle, la remise à zéro,
les autres choix et droits conservés, les recherches et les erreurs de sauvegarde.

La [vérification en service](live-console-validation.json) confirme que les
fichiers JavaScript et CSS mis à jour sont servis sans cache. Le catalogue client
correspond à la politique existante ; cette vérification en lecture seule ne
change pas la sélection de production. Qwen conserve son processus chargé.

La console lit ces fichiers à chaque requête : actualiser sa page suffit.
Cette modification ne nécessite pas de redémarrage ni de nouveaux clients ;
Windows **3.5.26** et Android **1.0.9/code 10** restent les versions publiées.
