---
name: ux-writing-cleaner
description: Auditer ou réécrire les textes visibles du frontend Fred, lors de leur création ou modification, en conservant les informations métier, les erreurs et les libellés accessibles.
---

# Nettoyer les textes de l'interface

Relever les chaînes réellement affichées dans le parcours : titres, sous-titres,
descriptions, boutons, tooltips, notifications, erreurs, états vides, labels et
chargements. Inclure les chaînes JavaScript injectées, pas seulement le HTML.
Ne pas traiter les logs, clés de traduction ou données utilisateur comme du texte UI.

Classer chaque texte examiné :

| Catégorie | Action |
| --- | --- |
| Essentiel à l'action, au métier, à la sécurité ou à la récupération | Conserver |
| Utile mais trop long | Simplifier en gardant le sens |
| Technique et sans utilité pour le public de l'écran | Déplacer vers diagnostic/admin |
| Redondant ou inutile | Supprimer |

Exemples : « Cliquez ici pour créer un nouveau projet dans votre espace de travail »
→ « Nouveau projet » ; « Le processus de sauvegarde des données s'est terminé avec
succès » → « Enregistré ». « HTTP 200 / SYNC_COMPLETED » → « À jour » uniquement si
la synchronisation intéresse l'utilisateur et si cet état correspond à la réalité.

Garder la même action et le même nom dans le bouton, la confirmation et les écrans
voisins. Employer le français courant et la casse des phrases ; préserver les noms
de produits et termes techniques indispensables aux paramètres concernés.

Une erreur doit dire ce qui a échoué et permettre une action : ne jamais masquer
silencieusement un enregistrement raté ou une perte de données. Conserver les labels
visibles de formulaires, noms accessibles, annonces de statut et détails utiles.
Ne pas remplacer un label par un placeholder ou une icône seule sans nom accessible.

Pour un audit, rendre un tableau fichier:ligne, texte, catégorie et proposition.
Modifier uniquement le périmètre demandé. Vérifier les usages et tests concernés,
les largeurs étroites et les états d'erreur. Le contrôle `maintenance/ux_check.py`
aide au repérage ; ses avertissements ne constituent pas un jugement éditorial.
