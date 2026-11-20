# Contexte de reprise — serveur Kiara

Mise à jour du 20 novembre 2026.

**Kiara 4.0.22** a été vérifiée en production le 20 novembre pour **Windows et
le web privé**. Dans Documents, la recherche groupée couvre huit types actifs.
La 4.0.21 est le point de retour documenté.
[Bascule 4.0.22](audits/2026-11-15-fusion-kiara/BASCULE.md#livraison-kiara-4022)
Le lanceur Kiara supervise le service Projets et son catalogue de 11 projets.
Conversations réunit le composeur, l’historique et l’assistant de projet, avec
les brouillons et le mode éphémère. Projets propose la fiche à quatre rubriques
dans le style Kiara. Le superviseur autonome a été retiré du dépôt.

Le canal Windows utilise un manifeste Ed25519 et un installateur sans
Authenticode. La **3.5.63** reste la
référence du canal classique. Les paquets Linux et Android ont leur propre
qualification et suivent un calendrier distinct.

La livraison 4.0.9 a ajouté **Notes** à l’accueil et à la navigation, avec un carnet
personnel, les notes des projets actifs et le collage direct d’images. Elle
regroupe aussi les corrections récentes du portail, des réunions et des
sauvegardes. Le catalogue de 11 projets et les deux entrées HTTPS ont été vérifiés
après la bascule. [Livraison du 18 novembre](audits/2026-11-15-fusion-kiara/BASCULE.md#livraison-windows-et-web-du-18-novembre-2026)

Depuis le 18 novembre 2026, les travaux d’interface ciblent le bureau Windows
et le web privé. L’audit couvre aussi le client Tauri Linux et son candidat de
recette. Les essais bureau se font en 720p, 1080p et WQHD. Android est mis de
côté jusqu’à sa reprise explicite. Voir les [consignes UX](maintenance/ux-ui/README.md)
et le [suivi de l’audit](audits/2026-11-16-architecture-interface/AVANCEMENT.md).
L’[audit de cohérence](audits/2026-11-18-coherence-interface/RAPPORT.md) documente
les réglages, la navigation et les notes.

L’[analyse du circuit de l’information](analyses/2026-11-19-workflow-information-kiara.html)
décrit l’entrée des sources, leur indexation par EG2 et leur utilisation par Qwen.

Le dépôt de travail est `D:\Serveur IA`. Utiliser **D:** pour les constructions,
caches, fichiers temporaires et recettes. **E:** est réservé aux archives et aux
preuves conservées. Tant que les accès à E: sont suspendus, conserver aussi
les nouvelles preuves sur D:. Voir [l’architecture](ARCHITECTURE-ACTUELLE.md#projets-et-conversations)
et [la publication avec retour arrière](audits/2026-11-15-fusion-kiara/BASCULE.md).

Les versions et décisions antérieures figurent dans l’historique [d’octobre et novembre 2026](HISTORIQUE-PROJET-OCTOBRE-NOVEMBRE-2026.md).
