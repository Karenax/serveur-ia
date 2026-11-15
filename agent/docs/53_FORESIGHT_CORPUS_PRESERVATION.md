# Direct CPU : corpus complet et conservation actuelle

Évaluation du16octobre2026. Les12WAV fictifs restant à qualifier sont traités par
le vrai chemin fragments→admission→Whisper medium CPU→segments/événements SQL.
Les3phrases propres déjà réussies sont réutilisées après contrôle du même profil,
des poids/configuration et du code ; seule la sélection du répertoire par défaut
diffère, avec le répertoire medium identique explicitement imposé dans les essais.
Les annotations ne sont jamais transmises au décodeur.

Le corpus conserve15extraits :12propres SAPI français industriel, bruit blanc
12dB, bande téléphonique8k et chevauchement synthétique de deux phrases prononcées
par la même voix. Ce chevauchement n’est pas une vraie réunion multivoix ni une
qualification de diarisation. Aucun microphone, GPU, LLM ou téléchargement.

## Résultat et limite utile

| Mesure | Résultat |
|---|---|
| Conservation/rejeu des12nouveaux fragments |12terminés,12événements, reçus identiques au rejeu, pas de réécriture ou doublon |
| Horodatages | Toutes les bornes de segments dans leur fragment et sur l’horloge de piste |
| Temps réel du pilote |151,18s ; premier passage25,87s, suivants8,95–12,48s |
| Fermeture | Worker terminé naturellement avec code0, lecteur fermé, poids/configuration et sources inchangés |
| Motifs critiques gelés |32/35correspondances après normalisation de format documentée |
| Analyse métier des écarts | Un écart bénin de pluriel et deux erreurs réelles ;33/35faits conservés au sens métier sur ce corpus |

Le pluriel « hors taxes » devient « hors taxe », sans transformer le sens hors
taxes. Ce cas reste en échec dans le score gelé32/35 ; aucune correction du texte
ou du résultat brut n’est appliquée pour améliorer son score.

Deux défauts réels restent : avec bruit, **consignation** devient **conciliation** ;
dans le mélange de voix, la clause « le client n’accepte pas l’option automatique »
disparaît. Les négations, réserves, dates, montants et mesures des12phrases propres
restent conservés au sens métier. Cela ne justifie aucune promesse universelle.

Le direct reste **disponible en essai**, avec relecture. La qualité industrielle
et la latence visible restent non qualifiées ; L03 n’est pas clos par ce pilote.
La mesure ci-dessus porte sur le service, pas sur un P95 d’apparition dans le DOM.
Le parcours de transcription complète puis CR relu reste actif. Aucun nouvel
essai identique n’est nécessaire pour constater ces deux mêmes défauts.

Le normaliseur a été gelé avant l’exécution, vérifié contre les35annotations de
référence. Il corrige les doubles échappements de frontières de mots et les
variantes de présentation (accents/casse, apostrophes, espaces chiffre/unité,
mm², €, °C, tr/min). Le corpus et les motifs d’origine sont conservés. Les mots,
valeurs, négations ou engagements manquants ne sont jamais ajoutés au résultat.

## Sauvegardes et différences de données

Des snapshots frais de Brain/ERP/EG2 sont pris en lecture seule dans le dossier
protégé de sauvegarde, puis restaurés dans des copies neuves. Les trois
integrity_check/quick_check réussissent et les trois contrôles de clés étrangères
renvoient zéro anomalie. Les ACL des nouvelles sauvegardes ne donnent aucun accès
aux groupes Tous, Utilisateurs ou Utilisateurs authentifiés. La sauvegarde
intégrale initiale14,7Go reste conservée ; aucun rehash intégral frais n’est annoncé.

Sur91tables comparées au dernier état vérifié,89sont exactes. Le contrôle strict
global reste enregistré comme faux : deux journaux dérivés ont évolué. Leur
classification séparée démontre :

- milestone_inputs :32nouvelles entrées de traitement (10artefacts Brain et
  22pièces jointes) ; aucun ID supprimé ; un état failed→completed, sans changer
  son contenu, sa preuve ou son identité. Les projets/sources/artefacts et les
  neuf originaux EML associés sont vérifiés par identité et SHA256.
- project_knowledge_analyses : deux messages d’erreur de délai45s et leurs dates
  de reprise changent ; statut, curseur, snapshot, contenu de travail et rapport
  restent inchangés. Ces deux services écrivains sont inchangés depuis le dernier
  global réussi ; l’origine est inférée de la provenance et des chemins du code,
  sans attribution à un utilisateur humain.

Notes, décisions, validations, données métier et identifiants contrôlés restent
conservés. Les réglages Brain sont exactement identiques, sans valeur secrète
affichée. Aucun retour de sauvegarde sur la production et aucune suppression.
T15 est maintenant clos avec le passage backend terminé et conservé ci-dessous.

Pièces : `v/direct-6fd409695678/result.json`,
`.ui-preview/l03-corpus-current-20261016/rubric.json`,
`.ui-preview/recipes-current-20261016/canonical-preservation-classified.json` et
`.ui-preview/backups/L12-current-integrity-5c6e20968f8f40e38070fae8469c55d7/preservation.json`.
Neuf lots et onze recettes sont clos après consolidation ci-dessous. L02/L03/L11/L12 restent ouverts.


### Consolidation T12/T15 — 16 octobre 2026

T15 est clos : le passage backend courant termine avec 2680 réussites, 1 ignoré
(dossier Infomaniak-IA absent), 54 sous-tests réussis et quatre avertissements.
Les 457 sources Python restent identiques. Les avertissements sont conservés :
dépréciation TestClient, deux décodages de sortie de helpers Windows et un
SAWarning de fixture. Les assertions de jonction sont effectivement réussies.
Les sauvegardes/restaurations privées et la classification des deux journaux
dérivés expliquent les écarts ; données et validations métier sont conservées.
Le frontend conserve son global 960/94 fichiers antérieur au correctif T05,
complété par les contrôles ciblés et TypeScript/Vite déjà acquis, sans addition.

T12 est clos dans la configuration observée, par preuves complémentaires des
quatre résultats du plan : heure réelle small CPU/int8/4 threads + LLM réseau
(1440 fragments acquittés et traités), priorité réellement concurrente du
planificateur, puis file SQL actuelle et affichage réel du retard. Sur 28 WAV
fictifs acquittés, 24 restent admis et 4 sont conservés hors direct ; la vue
affiche les deux pistes et l'ancienneté réelle. Le dernier contrôle n'exécute
aucun modèle. Ce verdict ne qualifie ni une heure medium CPU, ni un P95 DOM,
ni 15 réponses utiles pendant l'heure, ni la capture matérielle restante.
L03 et L12 restent ouverts. Aucun nouveau cycle d'une heure ni global backend
n'est nécessaire tant que leurs chemins restent inchangés.

Pièces : `logs/foresight-runtime/T12-T15-current-consolidation-ROOT-20261016.json`
et `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r23.json`.


### Décodage complet comparé sur les erreurs restantes — 16 octobre 2026

Un court comparatif CPU medium reprend exactement les paramètres du batch
(beam5, VAD, français, sans contexte précédent), sur les deux WAV dégradés en
échec et un témoin1250W/350lux. Il termine en41,913s, sortie0,6/8faits corrects.
Le témoin numérique reste exact ; « conciliation » et l'omission de la réserve
du client persistent. Les annotations ne sont utilisées qu'après décodage.
Le modèle et les457sources produit/tests/scripts restent inchangés. Le direct
conserve son profil ; aucune nouvelle boucle sur ces mêmes réglages n'est utile.

Le modèle turbo présent n'est pas relancé : la comparaison historique documente
déjà sa difficulté sur ce type de chevauchement ; son ancien reçu brut de corpus
est absent et n'est donc pas utilisé pour revendiquer une qualification actuelle.
Les résultats medium bruts restent conservés ; aucun mot n'est corrigé ou ajouté
automatiquement d'après la référence. L03 reste ouvert, CR avec relecture actif.
Pièce : `logs/foresight-runtime/L03-complete-decoder-comparison-ROOT-20261016.json`.


### Recherche et préparation qualifiées ; lexique non généralisé — 16 octobre 2026

La recherche unifiée est vérifiée sur trois sources fictives privées avec le vrai
encodeur réseau déjà chargé : « retard livraison » retrouve le décalage de trois
semaines par le seul sens ; les mots éclairage/350lux et la référence choisie
retrouvent la bonne fiche. La référence exacte exclut les voisins. L'index reste
identique par SHA pendant les trois recherches, les trois Sources restent
conservées et aucune connaissance validée n'est créée. Les15contrats applicables
du global backend restent acquis sur sources inchangées, sans nouvelle suite.

La préparation privée termine puis relit son état dans une nouvelle session SQL,
se réouvre et garde transcription/proactif/enrichissement désactivés. Le lecteur
ne peut pas la modifier. Les9contrôles UI acquis sont reliés à leurs sources
inchangées ; la sauvegarde et le bloc de préparation restent identiques au
préimage qualifié. Les diagnostics distinguent installation, chargement et
réponse réelle, y compris l'échec et la reprise, sans déduire une qualification
matérielle d'un modèle présent.

F16 et F20 sont clos selon leurs fonctions du plan.16fonctions sur25,9lots sur13
et11recettes sur17 sont clos. L02/L03/L11/L12 restent ouverts.

Le comparatif CPU de lexique dure28,94s sur trois WAV connus et un silence
fictif existant : consignation corrigée dans le bruit, témoin1250W/350lux exact
et silence sans texte ; dans le chevauchement, la réserve client reste omise et
« commande manuelle » disparaît aussi. Il s'agit d'un essai de développement,
pas d'une validation aveugle. Aucune promotion de profil : les défauts anciens
et le nouveau résultat défavorable restent conservés. Aucun microphone, LLM,
GPU, téléchargement ou donnée métier dans cet essai CPU ; il n'a modifié aucun
poids, réglage ou source produit. Aucun autre essai identique à relancer.
