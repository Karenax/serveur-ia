# Activation du moteur Strata 0.1.45.3 — 19 octobre 2026

Activation demandée après la [comparaison des deux moteurs](../../recherche/strata-0.2.0-beta-20261019/RESULTATS.md).
Le paquet moteur officiel 0.1.45.3 provenant de Strata 0.2.0-beta est copié dans
`dependances/strata-0.1.45.3/engine-cuda12`. Les empreintes de tous les fichiers
du manifeste sont vérifiées avant activation. SHA-256 de `strata.exe` :
`c97c3e84228c928c46bb2727c1753cbfe76c31c3eb0a9edc7bdd3cd78871cac3`.

Seuls `exe` et les dossiers des DLL `lib_dirs` changent dans les profils de base
et de lancement. Les réglages courants, par défaut et derniers valides désignent
le nouveau moteur. Le chargement automatique et la reprise restent activés.
La console est redémarrée pour relire sa configuration de base ; le modèle est
ensuite lancé par son superviseur normal, avec sa protection RAM à 6 Gio.

Le serveur Python 0.1.43.1 corrigé localement est conservé, ainsi que tokenizer,
profil experts, poids, PLE, MTP et encodeur P2200 CUDA 12.4. Les paramètres de
contexte, cache, split et génération restent identiques. Le serveur amont nouveau
n'est pas déployé en raison des régressions du parseur constatées pendant les tests.
Le pilote reste inchangé ; l'exigence déclarée par le manifeste et les essais
réels sur le pilote présent sont détaillés dans le rapport de comparaison.

`deployer.py` conserve les fichiers précédents dans `avant/`, prépare les profils,
vérifie que le modèle est inactif, arrête la session et lance le nouveau moteur.
`demarrage.json` décrit la session lancée ; `verifier.py` produit `production.json`
après l'état prêt, un calcul réel et le contrôle des configurations persistantes,
de l'exécutable actif, des accès et des ports locaux.
La prélecture `Prelire-Experts.py` est une aide ponctuelle à ce rechargement,
sans modification du démarrage automatique.

Validation terminée : session `20261019-181749-673936`, moteur PID 20192,
état prêt après 475 s, réponse réelle `301` au calcul `143 + 158`.
Les huit tests `python -m unittest test_launcher -q` passent (52,9 s).
L'API annonce le modèle chargé et les images disponibles ; les ports modèle,
console, passerelle, Hermes et WireGuard écoutent. Les contrôles d'empreinte des
configurations d'accès, de voix, de Hermes et de WireGuard passent.
Les cinq profils ne changent que de chemin moteur et, pour les deux profils
complets, de dossiers DLL. Les réglages courants, par défaut et derniers valides
sont identiques. Ces contrôles locaux complètent les essais d'outils et de vision
réels de la campagne précédente ; aucun redémarrage Windows n'a été effectué.

Pour revenir à l'ancien moteur, arrêter la session via la console, restaurer les
cinq profils de `avant/` (`base-strata`, profil IQ4, réglages, défauts et derniers
valides), puis redémarrer la console avec `-PreserverEtatModele` et lancer le modèle.
Conserver le dossier `dependances/strata-0.1.43.1` : il contient aussi le serveur
Python et l'encodeur visuel encore utilisés par la nouvelle configuration.
