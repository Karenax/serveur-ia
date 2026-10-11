# Plan — sauvegardes automatiques et gestion des appareils

Date : 10 octobre 2026. Statut : lots globaux **0 à 4 achevés, validés et mis en service** — 191 tests de régression réussis et preuves liées ci-dessous. Les spécifications ci-dessous conservent le détail du plan initial.

Programmation réelle : tous les jours à 03 h, conservation 7 jours / 4 semaines / 6 mois, dossier serveur `D:\Serveur IA\lanceur\sauvegardes`, deuxième copie désactivée selon le choix du demandeur. Voir le [guide](lanceur/SAUVEGARDES-APPAREILS.md), la [récupération des signatures](lanceur/RECUPERATION-SIGNATURES.md) et les [preuves](preuves/lots-0-4/VALIDATION.md).

## Objectif et périmètre

Ajouter ces deux fonctions à la console d’administration locale de Fred. Le serveur exécute les sauvegardes, leur vérification, leur conservation et les restaurations. Aucun téléphone ou PC client n’est nécessaire pour déclencher une sauvegarde programmée.

La gestion des autorisations et des appareils se fait aussi sur le serveur. Les clients transmettent uniquement les informations nécessaires à leur identification et continuent leur synchronisation normale. Une donnée qui n’a jamais été envoyée au serveur ne peut pas être sauvegardée par celui-ci.

Ce document détaille les sauvegardes et appareils. Le périmètre demandé comprend désormais aussi les messages vocaux, la recherche documentaire avec sources, les notifications, le tableau de bord et les outils de l’assistant. Le plan de référence pour l’ensemble et l’ordre de réalisation est [PLAN-GLOBAL-SERVEUR-FRED.md](PLAN-GLOBAL-SERVEUR-FRED.md). Les numéros de lots ci-dessous désignent le détail de ce sous-plan ; sa validation accompagne les lots du plan global.

## Base existante, vérifiée dans le code

- `lanceur/operations.py` : sauvegarde manuelle chiffrée `.qwenbackup`, phrase secrète, restauration validée et sauvegarde de retour.
- `lanceur/workspace.py` : base SQLite contenant historiques, projets, documents originaux, mémoire, tâches et politiques ; instantané avec l’API de sauvegarde SQLite et contrôle d’intégrité à la restauration.
- `lanceur/app.py` et `lanceur/web/` : rubrique Sauvegardes, création/restauration manuelles ; rubrique Clients avec création, renommage, suspension, expiration, révocation et suppression.
- `lanceur/remote.py`, `accounts.py`, `wireguard_access.py` : accès personnels, sessions, dernières connexions, annulation des travaux et retrait des pairs WireGuard.
- Aujourd’hui, une identité d’accès possède son espace de données. Il n’existe pas encore de séparation générale entre une personne et ses différents appareils.

Réutiliser ces mécanismes. Ne pas créer un second stockage des conversations ni une seconde liste d’autorisations.

## Lot 1 — sauvegardes fiables et inventaire

### Contenu

Inclure les conversations et préférences déjà synchronisées, projets, documents et originaux, mémoire, tâches, quotas, comptes, réglages du serveur, accès et secrets nécessaires à leur restauration. Inventorier les fichiers réellement utilisés : compléter notamment les réglages du dernier lancement valide et la configuration utile actuellement absente de la liste de sauvegarde.

Inventorier séparément les secrets de distribution des clients, dont la clé de signature Android : proposer un lot de récupération chiffré si l’objectif est de reconstruire et mettre à jour les clients après perte du serveur. Ne pas aspirer tout le dossier `toolchain`.

Exclure par défaut les modèles volumineux, caches, environnements de compilation, journaux temporaires et sauvegardes elles-mêmes. Le manifeste indique ce qui est inclus, exclu et requis pour remettre le serveur en service.

### Moteur

- Ajouter `lanceur/backups.py` ; conserver `Operations` comme point d’intégration et la lecture des anciennes archives.
- Instantané cohérent des fichiers et de SQLite, verrouillage bref pour la collecte, chiffrement et copie en arrière-plan. Une sauvegarde ordinaire ne décharge pas le modèle.
- Nouveau format versionné : manifeste, version applicative et schéma, date, taille, inventaire et empreintes ; archive chiffrée et authentifiée avec les dépendances déjà présentes.
- Réduire les copies en mémoire du format JSON/base64 actuel ; fixer des limites adaptées et tester les volumes supérieurs aux limites actuelles de restauration.
- Écriture temporaire, vidage des buffers, publication atomique et vérification par relecture avant de déclarer le succès. Aucun secret dans le catalogue ou les journaux.
- Un seul travail de sauvegarde/restauration à la fois ; état persistant, progression et détection d’un travail interrompu au redémarrage.
- Dossiers privés et accès administrateur local uniquement, avec les protections existantes de la console.

Livrable : sauvegarde manuelle complète, catalogue consultable, vérification et compatibilité avec les archives existantes.

## Lot 2 — programmation et conservation

Dans Sauvegardes, ajouter activation, fréquence, heure, destination, conservation, espace disponible et bouton « Sauvegarder maintenant ».

Valeurs proposées : une sauvegarde quotidienne à 03 h, conserver 7 quotidiennes, 4 hebdomadaires et 6 mensuelles. Paramètres modifiables ; les sauvegardes précédant une restauration bénéficient d’une conservation distincte.

- Planificateur serveur persistant, indépendant du navigateur et des clients ; déclenchement au démarrage lorsqu’une échéance a été manquée, sans accumulation de travaux.
- Phrase de récupération saisie une fois ; secret d’automatisation protégé par Windows DPAPI sous le compte d’exécution. La phrase de récupération permet aussi une restauration sur un autre serveur.
- Archivage local et copie facultative sur un second disque ou un partage NAS configuré. Une copie sur le même disque aide à réparer une erreur, mais ne protège pas de la panne de ce disque.
- Si la copie secondaire échoue : afficher « sauvegarde locale réussie, copie secondaire en échec », puis réessayer. Ne pas déclarer l’ensemble réussi.
- Nettoyage uniquement des archives finalisées et vérifiées, après un nouveau succès. Ne jamais supprimer le dernier point valide pour faire place à une sauvegarde qui pourrait échouer.
- Afficher dernière réussite, prochaine échéance, erreurs, archives présentes et emplacement de chaque copie. Limiter l’activité disque et éviter les travaux concurrents.

Le planificateur fonctionne lorsque le processus serveur tourne. L’ouverture de session Windows est encore requise par le démarrage actuel : installer un service Windows est un lot distinct si un démarrage avant connexion est demandé, avec migration explicite des secrets DPAPI.

## Lot 3 — restauration guidée

Remplacer la saisie obligatoire d’un chemin par la sélection d’une archive du catalogue ; conserver un import d’archive extérieure dans un emplacement contrôlé côté serveur.

Parcours : choisir → déchiffrer et vérifier → afficher date, contenu et effets → confirmer → restaurer → contrôler le résultat.

- Première version : restauration complète. La restauration d’un seul document ou d’un seul utilisateur sera un complément ultérieur, pour éviter une fusion incomplète des accès et des données.
- Validation complète avant mutation, espace disponible suffisant et point de retour automatique obligatoire.
- Passage en maintenance : refuser les nouvelles écritures, suspendre les tâches et les relances automatiques, terminer ou annuler proprement les travaux actifs, puis arrêter le modèle et les accès nécessaires. L’utilisateur confirme cette interruption dans l’assistant de restauration.
- Journal persistant de restauration et fichiers préparés à l’avance : après une panne ou coupure de courant, terminer l’opération ou revenir au point précédent avant d’accepter des clients. Le retour actuel sur exception doit être étendu aux interruptions du processus.
- Invalider les sessions. Garder l’accès distant désactivé jusqu’au contrôle et à la réactivation explicite. Ne pas relancer automatiquement les tâches restaurées.
- Conserver les révocations intervenues depuis la sauvegarde. Prévoir un registre de révocations indépendant du retour des données dans le temps.
- Sur une nouvelle machine sans registre de révocations récent : maintenir tous les accès restaurés désactivés jusqu’à leur validation par l’administrateur ; une vieille archive seule ne peut pas prouver l’état actuel des autorisations.
- Faire évoluer le protocole de synchronisation avec un identifiant de génération serveur : après restauration, un client ancien doit resynchroniser explicitement et préserver sa copie locale, sans réinjecter silencieusement un historique plus récent ni écraser les données restaurées.

Livrable : récupération compréhensible depuis la console, avec état final, contrôle des données et point de retour identifiable.

## Lot 4 — gestion des appareils

Faire évoluer « Clients & accès » avec une vue Appareils et une fiche par appareil.

Afficher : nom choisi, catégorie PC/téléphone/tablette, propriétaire ou libellé administratif, version cliente, date de création, dernière activité, statut autorisé/suspendu/révoqué/expiré, état de connexion estimé et accès aux espaces associés.

- Une clé API et un pair WireGuard distincts par appareil ; compatibilité avec les profils déjà distribués.
- Au premier lot, conserver chaque espace sous son identité actuelle. Le regroupement visuel par personne ne fusionne pas ses historiques. Le partage d’un espace entre plusieurs appareils nécessitera ensuite une migration explicite personne/appareils.
- Migrer les accès existants sans changer leurs clés : type « non renseigné » tant que l’administrateur ou le client ne l’a pas indiqué.
- Ajouter une déclaration cliente minimale, authentifiée, pour type et version. La dernière activité est horodatée par le serveur ; le type/version déclarés ne donnent aucun droit supplémentaire. Ne pas utiliser l’adresse IP ou un identifiant matériel comme preuve d’identité.
- Actions : ajouter, renommer, suspendre/réactiver, régler l’expiration, révoquer définitivement, remplacer un appareil et archiver sa fiche sans effacer ses données.
- Création Android : générer directement un fichier `.fred-android` depuis la console, sans devoir préparer un EXE Windows. Prévoir son téléchargement privé et un accès propre au nouvel appareil.
- Lors d’une révocation : refuser immédiatement l’API HTTPS et WireGuard, invalider les sessions, arrêter les flux et travaux actifs concernés, retirer le pair du moteur WireGuard et enregistrer durablement l’action.
- Afficher clairement que la révocation coupe l’accès au serveur ; elle n’efface pas les données déjà présentes sur un appareil hors ligne.
- Journal des actions administratives sans clés, mots de passe ou contenu des conversations.

Livrable : un appareil perdu peut être neutralisé depuis la console, tandis que les autres continuent à fonctionner et que ses données restent récupérables côté serveur.

## Lot 5 — validation et livraison

Tout d’abord utiliser des données synthétiques et des répertoires isolés.

Tests sauvegardes : serveur actif, écritures concurrentes, original de document et préférences, mauvais mot de passe, archive tronquée/corrompue, disque plein, destination NAS absente, échéance manquée, conservation et coupure à chaque étape de restauration.

Tests récupération : comparaison des données avant/après, ancienne archive, schéma incompatible, restauration sur une installation propre avec phrase de récupération, impossibilité de réactiver un accès révoqué, client hors ligne revenant après restauration et absence de reprise automatique des tâches.

Tests appareils : profils existants conservés, import Android direct, accès HTTPS et WireGuard, suspension/réactivation, révocation pendant un flux et après redémarrage, aucun effet sur les autres appareils, absence d’accès utilisateur aux fonctions d’administration.

Vérifier les parcours de la console et la synchronisation des clients Windows/Android. Livrer documentation, tests et résultats de récupération. Avant activation réelle, créer et vérifier un point de retour du serveur actuel ; les essais n’utilisent pas une restauration destructive sur les données de production.

## Ordre de réalisation

1. Inventaire et moteur de sauvegarde fiable.
2. Planification, catalogue et conservation dans la console.
3. Maintenance, restauration guidée et protection de la synchronisation.
4. Vue Appareils, création de profil Android et révocation complète.
5. Essais de récupération, validation clients et activation des paramètres choisis.

Critère de fin : sauvegarde automatique vérifiée sans intervention d’un client, restauration complète éprouvée sur une installation isolée, et révocation d’un appareil effective sur les deux transports sans perturber les autres.
