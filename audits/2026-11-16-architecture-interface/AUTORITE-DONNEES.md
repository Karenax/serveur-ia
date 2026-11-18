# Autorité des données — périmètre vérifié

17 novembre 2026 · Lecture des modèles et du pont de notes du dépôt courant.
Cette carte décrit les objets examinés, pas toutes les tables du projet. Elle
ne constitue pas une autorisation de supprimer des données ou des projections.

| Objet | Autorité et identifiants | Révision et représentation dérivée | Suppression et reconstruction |
|---|---|---|---|
| Projet de gestion | ERP `projects.id` ; titre, état et données de gestion dans le modèle ERP. | Identifiant distinct de celui de Brain ; `brain_links.project_id` associe explicitement `brain_project_id`. Le modèle ERP examiné n'expose pas de révision globale de projet. | Les conséquences complètes d'une suppression de projet sur les deux domaines restent à inventorier. Le code projet ou le nom ne remplacent pas le lien d'identifiants. |
| Projet de connaissances | Brain `projects.id` pour ses sources et connaissances ; le code est unique dans Brain. | Les deux projets peuvent avoir des identifiants distincts ; le lien ERP est utilisé par la projection de note. | Aucune reconstruction ni suppression transversale n'est déduite du seul code projet. |
| Note de projet enregistrée | ERP `project_notes.id` et `project_id` ; version courante dans `current_version_id`. Les versions sont dans `project_note_versions.id`. | Révision entière par note, empreinte SHA-256 et identifiant de commande ; la restauration crée une nouvelle révision à partir d'une version antérieure. Brain possède une source et des artefacts dérivés, pas la note éditable de référence. | Les anciennes versions sont conservées par les opérations de sauvegarde et de restauration examinées. La politique de suppression complète reste à définir et vérifier ; ne pas déduire qu'une source Brain est l'original. |
| Note personnelle enregistrée | ERP `personal_notes.id` et `owner_id`, lié à l'opérateur authentifié ; la version courante est identifiée par `current_version_id`. | Révisions dans `personal_note_versions`, commande idempotente par opérateur et images intégrées à la base dans `personal_note_images`, avec taille et empreinte. Une copie explicite vers un projet crée une note de projet distincte et conserve la note personnelle. | La sauvegarde coordonnée inclut la base ERP. Le contrôle ajouté le 18 novembre vérifie les versions, leurs liens d'images et les empreintes avant de qualifier une sauvegarde ou une restauration. La politique de suppression complète et les brouillons non enregistrés restent distincts de cette sauvegarde. |
| Événement de projection d'une note | ERP `note_evidence_outbox.id`, dérivé de l'identifiant de version ; une entrée au plus par version. | L'événement porte projet, note, version, révision et empreinte ; Brain enregistre un reçu idempotent du même identifiant et une liaison note/source. La projection attend un projet Brain lié, vérifie la version ERP et peut être reprise après interruption. | Une version devenue ancienne est marquée obsolète ; une source projetée n'est éligible comme version courante que si version, révision et empreinte correspondent encore à ERP. La suppression coordonnée et le réamorçage d'une projection déjà reçue restent à qualifier avant toute purge. |
| Source et artefacts de connaissance | Brain `sources.id` et `source_artifacts.id` ; chaque artefact référence sa source. Une note ERP projetée conserve les identifiants et l'empreinte de son origine dans ses métadonnées. | Les anciens artefacts texte de note sont marqués `superseded` lors de la projection d'une version plus récente ; l'index EG2 est une projection distincte. | Le modèle Brain déclare une cascade ORM des artefacts lors de la suppression d'une source ; les effets sur les originaux et les autres références dépendent des parcours et restent à examiner. |
| Séance, brouillon de séance et audio reçus | Brain `meeting_sessions.id`, versions de staging et fragments associés ; chaque fragment possède identifiant, piste, séquence, taille et empreinte. Une séance peut ne pas avoir de projet. | La séance et les segments ont leurs révisions ; l'attribution utilise des identifiants ERP et Brain explicites. Une note attribuée devient une note ERP, sans remplacer les données de séance. | La politique complète de rétention et de suppression des fragments et exports reste à inventorier. Un fragment présent seulement sur le poste n'est pas couvert par la sauvegarde du serveur. |
| Brouillon de conversation du client | Stockage chiffré local propre à l'appareil et à la fenêtre ; identifiants de brouillon et de projet. | Révision locale ; un fichier illisible est conservé, un brouillon orphelin est repris sous verrou. Ce stockage n'est pas une projection ERP ou Brain. | L'écriture explicite d'un brouillon nul supprime le fichier de la fenêtre correspondante. La sauvegarde serveur ne remplace pas la sauvegarde du profil local et de sa clé. |

## Contrat de passage des notes

1. La commande ERP écrit une version et prépare son événement dans la même
   transaction lorsque l'outbox est installée ; une ancienne installation sans
   cette table ne la crée pas implicitement pendant l'enregistrement.
2. Le port de lecture vérifie que projet, note, version, révision et empreinte
   concordent avant de fournir la projection. Il distingue une version courante
   d'une version dépassée.
3. Brain écrit source, artefact, liaison et reçu avant l'acquittement ERP. Un
   reçu déjà présent avec la même empreinte rend le rejeu idempotent ; une
   empreinte différente est refusée. Un projet non lié reste en attente.
4. Les essais de coupure et de rejeu cités dans [AVANCEMENT.md](AVANCEMENT.md)
   portent sur des bases de test. Ils ne prouvent pas qu'une purge, un changement
   de liaison ou une restauration partielle des deux bases soit sans conséquence.

### Changement de lien de projet — 18 novembre

Les lectures qui utilisent `is_current_evidence` comparent désormais le projet
réel de la source Brain avec le lien ERP actuel, en plus de contrôler la version,
la révision et l'empreinte de la note. Après suppression ou modification du lien,
la copie reste conservée mais ne constitue plus une preuve courante dans l'ancien
projet. Les interfaces et services ne passant pas par ce contrôle ne sont pas
qualifiés par ce changement.

Lorsqu'une nouvelle version est enregistrée après un changement de lien, sa
projection crée ou retrouve une source propre au nouveau projet. L'ancienne
source, ses artefacts et les reçus restent en place. En cas de retour au projet
initial, la source existante est réutilisée ; une source incompatible ou une
liaison partiellement restaurée est refusée pour éviter un écrasement. Sur bases
fictives, les interruptions avant validation Brain et après validation mais avant
acquittement ERP sont reprises sans perte ni duplication des sources.

Une reprise périodique par lots recherche également les versions déjà confirmées
dont le projet lié a changé, sans créer de version ERP ni modifier leur reçu. Elle
réutilise une copie compatible ou en crée une distincte, et recommence sa lecture
après redémarrage ; elle fonctionne lorsque le traitement de fond des notes est
activé. Un lien changé pendant l'opération est corrigé lors d'un passage suivant ;
entre-temps, le contrôle de lien écarte la copie qui ne correspond plus au projet.
Les essais sur bases fictives couvrent l'interruption, la concurrence et plusieurs
incohérences refusées. Ils ne constituent pas une qualification générale de toutes
les restaurations partielles ni d'une coupure électrique. Aucun déplacement ou
effacement de données n'a été fait.

Sources : [modèles ERP des notes](../../agent/backend/app/project_note_models.py),
[projets et liaison ERP](../../agent/backend/app/models.py),
[outbox](../../agent/backend/app/services/note_evidence_outbox.py),
[port de projection](../../agent/backend/app/services/note_projection_port.py),
[pont Brain](../../agent/app/services/note_evidence_bridge.py),
[modèles Brain](../../agent/app/models.py),
[modèles de séance](../../agent/app/meeting_session_models.py),
[brouillons locaux](../../client-qwen/draft_store.py) et
[modèle de domaine](../../agent/docs/02_DOMAIN_MODEL.md).
