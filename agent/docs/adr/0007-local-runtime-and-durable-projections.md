# ADR-0007 — Serveur local et projections reprenables

Statut : accepté dans la révision 0.3.0, 30 septembre 2026.

## Décision

Le pont ERP appelle les gestionnaires Brain dans le même processus et ouvre une
session SQL dédiée. Les appels HTTP vers le même pool de workers ne sont plus le
transport par défaut. Les deux bases et tous les modules hérités sont conservés.
Une validation canonique est commitée avant projection mémoire. La file SQL
stocke identifiants, hash, version, statut, erreur et référence externe. La reprise
et la reconstruction sont explicites ; elles ne modifient pas la vérité canonique.
Une suppression de projection externe exige sa confirmation, limitée au projet.
Les recherches de vérité lisent le canon ; l’evidence obsolète externe est bloquée.

## Conséquences

Les pannes de mémoire n’effacent pas une décision. Une interruption entre
l’indexation EG2 et l’enregistrement de sa référence canonique se reprend par la
file durable ; le hash du contenu et du profil rend le nouvel appel idempotent.
Les deux bases canoniques SQLite et l’index dérivé n’offrent pas de commit
distribué : les sauvegardes restent la référence de récupération, et l’index peut
être reconstruit depuis les sources canoniques classées.

Le serveur reste sur loopback avec protection de session locale, sans gestion
de comptes. Une sonde réelle d’indexation, rappel et nettoyage complète les
contrats de tests isolés ; une lecture de l’index local ne prouve pas la
disponibilité du serveur distant. Les règles de raisonnement désactivé du moteur
CDC sont conservées.
