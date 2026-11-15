# L0 — Contrats de reprise et conservation des données

Objectif lancé le **5 octobre 2026**. Références :
[plan](28_XPILOT_PROJECT_PLAN.md), [suivi](29_XPILOT_EXECUTION.json),
[audit initial](27_XPILOT_PROJECT_AUDIT.md).

Ce contrat guide les lots suivants. Il ne décrit pas des colonnes ou des routes
déjà activées : celles-ci seront livrées progressivement dans L1 à L9.
Le lot L0 ajoute un outil de qualification hors runtime ; aucune migration de
production ni nouvelle fonction d'écran n'est activée par ce lot.

## 1. Identité et sources de vérité

| Objet | Vérité canonique | Invariant |
|---|---|---|
| Projet opérationnel | ERP `projects.id` | UUID stable ; l'évolution du titre/code ne change pas l'identifiant |
| Projet de connaissance | Brain `projects.id` | UUID distinct ; le code sert à rechercher, pas à joindre silencieusement |
| Liaison ERP/Brain | ERP `brain_links` | Liaison explicite, conservée ; ambiguïté signalée, aucune fusion automatique |
| Dates, tâches, livrables, équipe, états, versions | ERP | Une proposition IA ne remplace pas une décision validée |
| Sources, propositions, faits, mémoire et audio | Brain | Le rattachement projet est contrôlé ; preuves conservées |
| Documents gérés | Stockage local dédié + métadonnées ERP/Brain | Fichiers et bases se sauvegardent ensemble |
| Documents réseau | Chemin projet autorisé + empreinte/provenance | Lecture pour l'analyse ; écriture seulement par une commande explicite |
| Index EG2 | Projection de la connaissance | Reconstructibles ; jamais seuls détenteurs d'une date ou décision métier |
| XPilot externe | Source de référence en lecture | Aucune dépendance runtime à sa base ou à son serveur sur 8000 |

Le projet Brain peut déjà être réutilisé lors d'un import d'archive : ne pas
imposer rétroactivement une nouvelle unicité qui casserait ces liaisons. Toute
nouvelle relation respecte le périmètre de l'objet parent, même si le client
fournit un identifiant UUID existant dans un autre projet.

Les anomalies historiques sont diagnostiquées puis traitées explicitement.
Un code vide/dupliqué ou une différence ERP/Brain ne justifie ni suppression ni
réaffectation des mails. La création future refuse une nouvelle ambiguïté ;
elle ne rend pas inutilisables les projets hérités concernés.

## 2. Contrat d'identité pour L1

Conserver les colonnes actuelles, y compris les valeurs financières historiques,
sans les remettre dans les formulaires ou le moteur métier.

Extensions prévues, par migrations additives :

| Donnée | Convention |
|---|---|
| Client, agence, personne responsable | Référentiels à UUID ; conserver `client_name` comme valeur héritée/snapshot |
| BU, famille, typologie | Codes stables et libellés éditables ; référentiel léger dans Réglages |
| Description et références client/outillage | Champs texte bornés ; absence représentée explicitement |
| Offre et dossier affaire | Conserver les données/lien existants et la priorité du nom de dossier pour le code |
| Début et échéance prévue | Dates ISO `AAAA-MM-JJ` ; vide/null reste absence ; fin antérieure au début refusée |
| Clôture réelle | Distincte de l'échéance ; écrite par le workflow L9 |
| Standby et état | Conserver `active`, `paused`, `done`, `archived`, `cancelled` hérités ; adapter le workflow, sans réécriture massive |
| Membres | Relation projet/personne/rôle métier ; historique et archivage plutôt que suppression |

Ne pas mapper automatiquement `done` vers une clôture formelle : les conditions
de REX et d'archivage n'ont pas été vérifiées pour les anciens projets.
Le rôle métier (CAF, BE, qualité…) est distinct d'un droit de lecture/édition.

Agent utilise aujourd'hui une session locale ; le contrôle de session protège
les commandes HTTP. Les futures portées ERP doivent être vérifiées côté service,
y compris lors des appels internes, et alignées sur les ACL Brain. Un choix de
personne dans l'interface ne constitue pas une authentification multi-utilisateur.
L1 doit fixer et tester le contexte d'opérateur avant de livrer un mode lecteur
présenté comme protégé. Aucune logique de permissions uniquement dans React.

## 3. Contrats de services et d'interface

- Étendre les routes `/api/v1/projects/{id}` et les modules existants sans changer
  les UUID ni retirer leurs contrats historiques. Retourner les champs ajoutés
  sans exiger qu'un ancien client les envoie.
- Les sous-objets projet sont toujours lus/modifiés dans leur projet parent ;
  les référentiels globaux sont identifiés séparément.
- Commandes métier dédiées pour publication, approbation, gel, clôture,
  réouverture et signature. Le simple PATCH de statut ne contourne pas leurs
  conditions lorsqu'elles sont introduites.
- Champs d'édition futurs : numéro de révision ou version attendue ; conflit
  explicite sans écraser la dernière décision humaine.
- Les changements validés actualisent portefeuille, fiche, sélecteurs de
  classement, compteur et assistant ; conserver les corrections de glisser-déposer.
- Utiliser des listes paginées (50 par défaut, plafond défini par route), un
  chargement indépendant et des états vides/erreurs utiles.
- Les travaux longs passent dans des jobs durables ; progression avec total
  connu, sinon témoin indéterminé. Reprise idempotente, erreurs et retry visibles.
- Les événements IA et les sorties métier portent source, version, empreinte,
  date et décision humaine. Une modification de source invalide ses analyses
  dérivées, sans supprimer les artefacts précédemment émis.

Le menu latéral nommé est conservé. Les groupes de la fiche projet sont ceux
du plan 28 ; pas de retour au dock, au curseur de largeur d'assistant ou aux
boutons de portefeuille précédemment retirés.

## 4. Migrations et archives

Une migration additive ajoute tables/colonnes/index ; elle ne retire ni ligne,
ni ancienne colonne, ni donnée financière. Pour une valeur initiale, utiliser
une valeur neutre ou un mapping vérifié. Ne pas inventer dates, responsable,
signature, preuve ou état de clôture.

Avant activation :

1. Sauvegarde globale coordonnée **hors ligne**, avec le mécanisme existant
   `scripts/agent_backup.py` ; arrêt identifié du seul Agent 8001.
2. Capture des bases sauvegardées, puis migration sur copies.
3. Comparaison de toutes les lignes/colonnes/valeurs préexistantes, recette
   des archives et des fichiers, puis retour à une copie d'état précédent.
4. Activation du lot qualifié et vérification santé des deux bases.

Le contrôle strict fourni par L0 s'applique aux migrations additives. Les
transformations de données intentionnelles éventuelles doivent disposer d'un
contrat et d'une recette distincts ; elles ne sont jamais rendues invisibles
par une liste générale de tables ignorées.

Les archives projet actuelles **version 2** restent importables. Dès que des
référentiels partagés sont introduits, étendre l'export pour inclure uniquement
les références effectivement utilisées. Si le format change, versionner son
contrat et conserver le lecteur ancien. Rejeter les références ambiguës ou
hors projet, ne pas importer toute une table globale depuis un JSON.
Les relations parent/enfant et auto-références sont restaurées dans un ordre
valide ; tous les nouveaux fichiers métier sont inclus dans les sauvegardes.

La restauration globale utilise un **nouveau répertoire** et conserve le
référentiel de départ. Le remapping des chemins gérés et l'interruption des jobs
restaurés sont des transformations déjà prévues et testées par ce service,
pas une migration additive à masquer dans le contrôle L0.

## 5. Outil de contrôle livré

`backend/app/services/migration_guard.py` et
`scripts/project_migration_check.py` sont indépendants du runtime : pas
d'import de configuration initialisant des bases, pas de migration automatique.
Les chemins sont obligatoires et les bases sont ouvertes en lecture seule.
Un chemin absent est refusé sans créer de SQLite vide.

```powershell
python scripts/project_migration_check.py preflight --erp C:/Copies/erp/minipilot.db --brain C:/Copies/brain/project_brain.db --output C:/Recette/preflight.json
python scripts/project_migration_check.py capture --database C:/Copies/erp/minipilot.db --output C:/Recette/erp-before.json
# Appliquer la migration uniquement à la copie de recette.
python scripts/project_migration_check.py compare --before C:/Recette/erp-before.json --database C:/Copies/erp/minipilot.db --output C:/Recette/erp-after.json
```

Le dossier des copies/rapports doit être adapté au poste. Le rapport de capture
contient les empreintes des identités et cellules, sans contenu brut. La comparaison
accepte nouvelles colonnes/tables/lignes et détecte table/colonne/ligne absente,
identité modifiée et valeur préexistante changée. Les types, blobs, valeurs nulles
et chaînes vides sont distingués ; identités composites et tables héritées sans
clé primaire sont couvertes. Un échec de conservation produit un code de sortie 1.
Le rapport exige un nouveau fichier et ne peut remplacer une base ou un rapport.

Le préflight signale doublons de codes, codes vides, liens cassés, différences
de codes liés et violations de clés étrangères. Il n'écrit aucune correction.
Chaque capture est cohérente dans une transaction par base ; deux captures
pendant l'exploitation ne remplacent pas une sauvegarde globale coordonnée.

## 6. Qualification L0

- Préflight en lecture seule sur les bases actuelles : **10 projets ERP,
  10 Brain, 9 projets ERP liés** ; un projet ERP reste sans liaison explicite.
  **0 code dupliqué/vide, 0 liaison cassée, 0 différence de code lié,
  0 violation de clé étrangère** observés lors de cette passe.
- Répétition sur copies des sauvegardes du 5 octobre : ajout d'une colonne de
  recette et d'une table de recette, puis récupération depuis les originaux
  inchangés vers de nouveaux fichiers.
- Conservation vérifiée : **10 308 lignes / 84 413 cellules** (Brain : 9 859 /
  78 625 ; ERP : 449 / 5 788). Aucune valeur antérieure perdue ou changée.
- Les preuves locales sont dans `.ui-preview/xpilot-l0/`, ignorées par Git ;
  ce sont des rapports de recette, pas des données à distribuer.
- Tests ciblés : ajout de schéma, perte/modification de ligne ou colonne,
  valeurs financières héritées, blob, identité composite, null/vide,
  alias SQLite rowid et diagnostic sans modification.
- La suite globale couvre également les archives projet et la sauvegarde
  complète/restauration existantes. Résultats finaux dans le suivi JSON.

L0 ne modifie pas les bases réelles et ne nécessite pas de redémarrage. Le lot
suivant est L1 : étendre l'identité projet et l'équipe, sur cette fondation.
