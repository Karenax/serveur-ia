# Strata 0.2.3.1 — intérêt pour Fred, 23 octobre 2026

## Référence
Fred configure le moteur officiel 0.1.45.3 CUDA 12 et le serveur Python 0.1.43.1 corrigé (lanceur/base-strata.json). Deux P100 pour le texte, P2200 pour la vision, modèle Flash-Next Uncensored IQ4_XS, 15 workers, réserve VRAM explicite 2048 Mio, cache conversations explicite 30720 Mio / 20 slots.

Dernière publication vérifiée par le connecteur GitHub : https://github.com/Niko1221/Strata/releases/tag/v0.2.3.1 ; publiée le 23 octobre à 15:45 heure de Paris. Application 0.2.3, moteur 0.1.48 ; le correctif 0.2.3.1 ne change que Control (installation), pas le moteur.

## Reprises proposées
1. Évaluer séparément le moteur 0.1.48 CUDA 12 avec les réglages actuels ; aucun gain IQ4_XS / deux P100 mesuré ici.
2. Revoir les corrections du serveur pour appels d'outils, retry après logits non finis, cache et paramètres API ; conserver les exigences des tests locaux.
3. Tester le batch multi-utilisateur si nécessaire : la version 0.2.1 change le regroupement de batch sur exactement deux NVIDIA. Les gains publiés portent sur deux A4000 ; certaines configurations riches en experts CPU régressent. Aucun bénéfice annoncé pour une requête seule.
4. Gyro : piste distincte de changement de quantification. La note 0.2.2 annonce environ +30 % de génération Gyro-S sur une P100 par rapport à son ancien chemin Gyro. Ce n'est pas +30 % pour notre IQ4_XS.
5. DFlash2 : option expérimentale manuelle du terminal 0.2.3 ; auto conserve MTP, aucun GPU n'a gagné partout. Pas de motif établi de remplacer notre MTP.
6. Réserve VRAM et cache automatique : nos nombres explicites empêchent de profiter automatiquement de leurs nouveaux défauts. Ne pas les réduire sans mesure.
7. Pool NUMA scindé : Linux uniquement ; pas de reprise directe pour notre Windows.

## Contrôle réel du parseur
Source officielle serve/frontend.py du tag v0.2.3.1 copiée dans serve/. Les deux modules de tests Fred sont copiés sans modification depuis dependances/strata-0.1.43.1/source/serve.
Exécution des seuls cas sans serveur HTTP : 16 méthodes ; référence Fred OK, amont 64 échecs en comptant les sous-cas, aucune erreur d'import dans cette sélection. Le journal parser-only-tests.log contient les détails. Ces résultats couvrent les booléens typés, JSON encapsulé dans XML, délimiteurs littéraux et champs requis avant émission, pas tous les outils possibles.
La première tentative parser-tests.log inclut trois tests HTTP non exécutables avec la seule copie du frontend ; elle est conservée comme diagnostic et exclue de la comparaison finale.
Aucun moteur lancé, modèle rechargé ni configuration de production modifiée. Aucune mesure de vitesse locale nouvelle.

Sources : notes officielles v0.2.1, v0.2.2, v0.2.3, v0.2.3.1 conservées dans ce dossier ; bilan précédent recherche/strata-0.2.0-beta-20261019/RESULTATS.md et activation maintenance/2026-10-19-strata-0.1.45.3/README.md.

