# Exercice réel de ux-writing-cleaner — 22 octobre 2026

Skill lu et appliqué par Codex à des cas de contrôle et à un texte existant.
Les propositions ci-dessous ne sont pas appliquées à l'application. Il s'agit d'un
test manuel du comportement éditorial, distinct de la découverte technique du skill.

| Entrée et contexte | Classe | Résultat proposé |
| --- | --- | --- |
| Bouton « Cliquez ici pour créer un nouveau projet dans votre espace de travail » (cas de contrôle) | Utile mais trop long | Nouveau projet |
| Toast « Le processus de sauvegarde des données s'est terminé avec succès » (cas de contrôle) | Utile mais trop long | Enregistré |
| « Statut du backend : HTTP 200 / SYNC_COMPLETED » dans un écran métier sans besoin de statut (cas de contrôle) | Technique | Déplacer vers le diagnostic ; ne pas ajouter un statut gratuit |
| « Échec de l'enregistrement. Votre brouillon est conservé. Réessayer. » (cas de contrôle) | Essentiel | Conserver l'erreur, la préservation du brouillon et la récupération |
| Label visible « Nom du projet » et nom accessible du bouton Fermer (cas de contrôle) | Essentiel | Conserver, même si l'icône est compréhensible visuellement |
| Sous-titre « Votre espace de travail » immédiatement sous un titre identique (cas de contrôle) | Redondant | Supprimer le doublon seulement |
| `lanceur/web/index.html:46`, avertissement réel de 194 caractères sur les versions signées et la migration depuis 2.0 | Essentiel, formulation améliorable | Garder les deux voies de mise à jour et la distinction 2.0/3.0 ; aucune suppression automatique malgré la longueur |

Proposition pour le dernier cas : « Versions signées et vérifiées. Depuis la version
3.0, utilisez Mettre à jour. Pour la première migration depuis 2.0, redistribuez les
EXE personnels. » Le contexte d'administration justifie ici le terme EXE.

Résultat : les quatre classes sont exercées ; informations de migration, erreurs,
récupération et accessibilité préservées. Aucun fichier applicatif modifié.
