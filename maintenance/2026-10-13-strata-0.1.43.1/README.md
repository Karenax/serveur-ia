# Flash-Next / Strata 0.1.43.1

Changement demandé par l'utilisateur le 13 octobre 2026 après comparaison des moteurs. Distribution officielle identique à celle mesurée, copiée dans `D:/Serveur IA/dependances/strata-0.1.43.1` pour éviter les dépendances aux dossiers d'essai. Aucun changement des kernels.

Profil conservé : deux P100 dans le même ordre UUID, split 24, préfill 2048, 15 workers, contexte 262144, MTP 3 / seuil 0.5, cache historique 8 / intervalle 160000, PLE direct, conversation-cache-mib 0, split MTP batch activé. Tail skip, adapt overlap et part CPU préfill désactivés. Le bénéfice individuel du flag batch n'a pas été isolé par un test témoin.

Le serveur Python reçoit `STRATA_ENGINE_READY_S=3600` avant l'import, pour ne pas interrompre les lectures à froid à 900 s. Le lanceur historique lit maintenant le cwd de la configuration. Réglages courants, réglages par défaut, derniers réglages valides et les deux configurations de base pointent sur cette distribution. Le nom API et le port 8080 restent identiques.

La bascule a rencontré une reprise automatique des anciens derniers réglages valides après reconnexion de la console. Cette reprise a été arrêtée ; les derniers réglages valides ont été alignés avant le lancement définitif. `production.json` prouve le moteur réellement exécuté et une réponse 301 à 43 × 7. Les huit tests du lanceur passent ; l'attente historique de cache désactivé a été actualisée pour ce profil.

La prélecture séquentielle complète a aussi provoqué une pression mémoire transitoire pendant la copie des experts : la protection RAM a arrêté cette tentative. Le lancement final s'effectue après la fin de la prélecture, sans processus de prélecture parallèle. Cette prélecture n'est pas intégrée au démarrage automatique.

## Retour arrière

La sauvegarde `avant/` contient les configurations, réglages et scripts précédents. Depuis la console, arrêter le modèle, puis fermer uniquement la console locale. Restaurer `avant/lanceur/base-strata.json`, `avant/strata-iq4-p100-hybride.json`, `avant/lanceur/reglages.json`, `avant/lanceur/reglages-par-defaut.json` et `avant/lanceur/derniers-reglages-valides.json` vers leurs chemins correspondants sous `D:/Serveur IA`. Relancer `Start-Interface-Qwen.ps1 -SansNavigateur` : le moteur précédent est toujours présent dans `strata-build-p100`. Ne pas restaurer l'ancien pointeur session, qui désigne des processus terminés. Les scripts `runtime.py` et `Start-Strata-IQ4-P100.ps1` sauvegardés peuvent également être restaurés si nécessaire.

Le rapport comparatif d'origine est `recherche/strata-0.1.43.1-20261013/mesures/20261013-092456/RAPPORT.md`. Le gain médian mesuré de décodage est 15.4 %, avec les réserves thermiques détaillées dans ce rapport ; ce déploiement ne constitue pas une nouvelle mesure de vitesse.
