# Intégration de l’assistant Kiara — 25 octobre 2026

Première version intégrée et publiée : **serveur/Windows 3.5.52**, **Android
1.0.23, code 24**. Les six axes du plan disposent maintenant de code commun et de
parcours clients. Les essais physiques restant à faire sont distingués ci-dessous.
Les modifications déjà présentes dans le dépôt ont été conservées.

## Utilisation

Le [guide commun de l’assistant](../../GUIDE-ASSISTANT-KIARA.md) rassemble les
parcours Windows/Android. Le présent document conserve les décisions techniques,
preuves de livraison et limites de validation.

- Ouvrir **Mémoire et rappels** dans le client mis à jour. Choisir **Personnel** ou
  un projet pour consulter, ajouter, corriger ou oublier un souvenir. Une préférence
  personnelle peut être explicitement appliquée à tous les projets.
- Dans une discussion écrite ou orale, demander par exemple « Retiens que je
  préfère les réponses courtes », « Quels sont mes rappels ? », « Crée une note
  dans ce projet » ou « Rappelle-moi demain à 18 heures de reprendre ce dossier ».
  Les changements sont confirmés après enregistrement. Une cible ambiguë ou une
  date invalide nécessite une précision.
- Programmer un rappel simple ou un compte rendu de projet, avec fuseau et
  répétition quotidienne, hebdomadaire ou du lundi au vendredi. Le serveur doit
  fonctionner pour traiter l’échéance ; le rappel simple n’utilise aucun modèle.
  L’alerte ouvre le texte du rappel et son heure prévue.
- Choisir un projet pour consulter son bilan ou **Préparer une synthèse**.
  L’actualisation automatique est facultative et désactivée initialement.
- Pendant le vocal, choisir une image, une photo Android ou une zone d’écran
  Windows. Vérifier la prévisualisation puis poser la question. L’image choisie
  est jointe à ce tour et conservée dans la discussion, sans devenir un souvenir.
- Dans les réglages vocaux, essayer **Attendre « Bonjour Kiara »**. L’essai est
  local, facultatif et limité à l’application visible. Après un appel, réactiver
  l’attente si nécessaire. Le bouton de conversation reste disponible.

Android propose séparément les relevés d’alertes hors application : autorisation
des notifications et activation explicite requises. Android gère la cadence, au
minimum quinze minutes, et peut différer l’exécution en veille. Il ne s’agit pas
d’une alarme exacte. Sans réseau, téléphone éteint ou application forcée à l’arrêt,
aucune livraison immédiate n’est promise ; la boîte serveur permet le rattrapage.
Le mot d’appel s’arrête lorsque l’application passe en arrière-plan.

## Données et commandes

`lanceur/assistant_commands.py` porte le catalogue partagé. Hermes appelle
`fred_assistant` ; le parcours vocal direct conserve R:/W: et ajoute C: pour une
commande structurée. Une réponse courante continue à être diffusée sans nouvelle
classification séparée. Le JSON d’une commande n’est jamais lu à haute voix.

Le serveur fixe compte et projet. Révisions, annulation, droits et quotas sont
vérifiés avant validation ; effet métier et résultat dédoublonné sont enregistrés
dans la même transaction SQLite. Le journal conserve au maximum 5 000 écritures
par compte, puis refuse une nouvelle commande avec un message de maintenance.
La vérification de l’intention actuelle complète les consignes du modèle ; elle
ne constitue pas une preuve générale de compréhension de toute phrase française.
Aucun nouvel outil libre de fichiers, terminal ou action externe n’est exposé.

Les tables additives `assistant_items` et `assistant_commands` complètent les
souvenirs, documents et tâches existants. Exports privés, quotas et sauvegardes
les incluent ; le validateur accepte les archives du schéma antérieur et leur
ajoute les nouvelles tables. Les tests restaurent dans des bases temporaires.

Les souvenirs natifs Hermes et son profil utilisateur automatique sont désactivés
au profit du stockage Kiara. Les anciens fichiers restent consultables pour une
reprise manuelle ; aucune fusion ou suppression silencieuse n’est effectuée.
Lors de cette livraison, l’archive de référence ne contenait aucun ancien fichier
de mémoire Hermes. Une correction ou un oubli change la génération des sessions
et masque les anciens passages correspondants dans le contexte et la recherche.
Ce filtrage repose sur les tokens et la demande source enregistrée : ce n’est pas
un effacement sémantique de toute paraphrase. Historique et archives conservées
ne sont pas effacés rétroactivement.

Le bilan distingue souvenirs et décisions confirmées, tâches, documents et
discussions. La synthèse produite reste un dérivé du modèle, à vérifier avec ses
sources. Une empreinte des versions et de la génération mémoire empêche de
réutiliser une synthèse devenue périmée, même si la source change pendant le
calcul. Les synthèses facultatives utilisent la file existante, un prompt borné
à 12 000 caractères, un regroupement des changements et un intervalle minimum
de cinq minutes. Leur concurrence prolongée avec un dialogue réel reste à mesurer
avant activation généralisée.

Le traitement des rappels utilise un thread distinct des analyses. Les occurrences
et notifications sont validées ensemble. L’échec d’une occurrence, notamment le
quota saturé d’un compte, n’empêche pas les rappels des autres comptes ; cette
isolation a été ajoutée puis revérifiée avant le dernier rechargement serveur.
Les répétitions suivent le calendrier
du fuseau ; une heure locale ambiguë doit être précisée avec décalage UTC. Une
heure future absente au passage d’été est sautée. Le rattrapage signale une
échéance manquée une seule fois et évite une rafale de rapports retardés.

## Mot d’appel et images

Le détecteur dédié utilise **sherpa-onnx 1.13.8** et environ 5,5 Mo de modèles
int8. Références, tailles, empreintes et phrase figurent dans
`client-voice/wakeword-models.json`. L’AAR Android est épinglé et vérifié ; les
licences sherpa-onnx, ONNX Runtime et Kotlin sont incluses. L’attente ne lance pas
une transcription complète et ne transmet pas d’audio au serveur. Une attribution
serveur par compte limite à un appareil les activations rapprochées. Le micro
du détecteur est fermé avant l’ouverture du vocal.

**Limite acoustique :** le petit modèle est chinois/anglais, adapté phonétiquement
à la phrase française complète « Bonjour Kiara ». Le nom seul n’a pas donné de
résultat satisfaisant. Quatre échantillons synthétiques donnent une activation
sur la phrase attendue et aucune sur trois autres phrases ; Android reproduit
les trois cas de son test JNI. Cela ne valide ni accents, bruit ambiant, taux de
fausses activations par heure, écho ou autonomie. L’option reste expérimentale,
désactivée et sans prise en charge Android verrouillé/arrière-plan.

La capture Windows est déclenchée par le bouton, avec sélection d’une région et
annulation par Échap. Seul le recadrage choisi est transmis ; l’image complète
reste temporaire en mémoire locale. Android utilise l’application photo du
téléphone et un fournisseur de fichier temporaire borné au dossier de captures.
Les profils et chemins arbitraires restent inaccessibles par cette voie.
Les images sont redimensionnées à 2 048 pixels maximum, encodées en JPEG et
limitées à 2 Mo après traitement. Le contexte vocal réserve conservativement
1 024 tokens par image, car le compteur texte de l’encodeur actif ne les comptait
pas. Une capture tardive après raccrochage ne rejoint pas la question suivante.

## Vérifications et preuves

| Vérification | Résultat et portée |
| --- | --- |
| Régression serveur | 563 tests réussis dans `server-final-tests.log`, puis contrôles ciblés après les dernières corrections |
| Assistant partagé et HTTP vocal | 17 tests réussis, dont annulation, droits, reprise, révisions, oubli, rappel sans modèle, rappel pendant analyse lente et compte saturé n’empêchant pas les alertes d’un autre compte |
| Outils Hermes | 17 tests réussis ; commande écrite, même effet canonique et répétition sans doublon |
| Workspace et contexte visuel | 28 + 5 tests ciblés réussis |
| Client Windows Python | 87 tests réussis, dont recadrage avec une image fictive |
| Moteur vocal Python | 38 tests réussis |
| Livraison Android Python | 13 tests réussis |
| Interface commune | 15 suites réussies, Windows et Android, puis scénario assistant rejoué après les derniers ajustements |
| Android natif | Lint, compilation et instrumentation API 36 réussis : détecteur JNI, isolation du fournisseur photo, inscription/annulation JobScheduler |
| Binaires | EXE de base et personnel : self-test réussi ; détecteur du worker Windows livré vérifié sur quatre fichiers fictifs ; ressources finales comparées aux sources ; APK signé, deux ABI JNI, empreintes vérifiées |
| Production | Catalogue authentifié, lecture de l’assistant, tables et désactivation de la mémoire native Hermes vérifiés sans écriture métier de test |

Les validations natives Android utilisent un émulateur isolé et des enregistrements
fictifs. Elles ne remplacent pas un téléphone réel, son application caméra, son
micro, ses restrictions de veille ou une mesure de batterie.

`windows-packaged-wakeword.json` vérifie aussi le worker réellement incorporé dans
l’EXE Windows. Le banc normalise les WAV synthétiques à 16 kHz, comme la capture
de production : l’essai initial en 24 kHz exigeait SciPy, volontairement exclu du
paquet public. Après correction du banc, les quatre résultats correspondent à
l’attendu, sans ouverture du microphone ni modification du binaire publié.

Les contrôles de sources passent. `npm --prefix client-qwen test` inclut
`ux:check` : neuf avertissements de texte existants dans la console ont été
examinés et conservés ; aucune suppression automatique. Les cinq verrous Python
sont intacts et les versions attendues correspondent. Le contrôle strict signale
toutefois cinq paquets de construction PyInstaller supplémentaires déjà présents
dans Strata ; les quatre autres runtimes correspondent exactement. Voir
`runtime-inventory.json`. Ces outils n’ont pas été désinstallés ni les verrous
réécrits pour masquer cet écart.

Trois essais directs sur le Qwen réellement chargé ont donné le protocole attendu
(discussion, ajout mémoire, liste de rappels), sans exécuter ces commandes sur
les données de production. Les premiers textes ont pris **30,17 s / 5,81 s /
1,69 s** ; l’image bleue fictive a été correctement décrite, premier texte en
**40,19 s**. Voir `live-inference.json` et `vision-live.json`. Ces essais ne sont
ni un p95, ni une mesure bout en bout du microphone au haut-parleur. Les longues
attentes existantes restent à diagnostiquer ; aucune amélioration générale de
latence n’est revendiquée.

## Vérification visuelle ciblée

Parcours réel sur fixture HTTP locale, données fictives, outils Playwright MCP :
navigation **Mémoire et rappels**, arbre accessible, formulaire et Tab, focus
visible, largeurs 390 × 844, 768 × 1024 et 1 440 × 900, thèmes clair et sombre.
Les captures `ui/mcp-*-final.png` ont été ouvertes et examinées. Les suites
partagées couvrent aussi vide, succès, échec avec conservation du brouillon,
nouvel essai avec même identité, changement d’espace et restitution du focus.

| Niveau | Constat et correction |
| --- | --- |
| P1 corrigé | Contours des champs trop discrets sur le nouveau formulaire : variable de contraste existante réutilisée ; focus clavier visible revérifié |
| P2 corrigé | Après retrait d’un élément, focus restitué sur Actualiser ; informations et erreurs conservées dans le statut annoncé |
| P2 corrigé | Formulaires repliables pour garder une page lisible sur téléphone ; pas de débordement horizontal dans les trois formats |
| P3 corrigé | Captures de test stabilisées après la transition du tiroir ; état réel examiné au lieu d’une animation intermédiaire |

Aucun P0 observé dans ce périmètre. Ce contrôle ne constitue pas un audit complet
de l’application ni une déclaration globale de conformité WCAG. Lecteur d’écran,
capture réelle du bureau, appareil photo et acoustique sur matériel utilisateur
n’ont pas été testés.

## Livraison et récupération

`delivery-preparation.json` atteste la sauvegarde chiffrée vérifiée avant
publication et le contenu des paquets. `publication.json`, `production.json`,
`android-publication.json` et `assistant-production.json` attestent : signatures
et téléchargements vérifiés, ancien certificat Android conservé, accès personnel
Windows reconditionné sans changer ses secrets, processus Qwen et programmation
des sauvegardes conservés. Dix tables métier ont été comparées à l’archive
chiffrée d’avant livraison, y compris les souvenirs personnels : elles sont
identiques. Seule la passerelle a été redémarrée. La voix serveur est restée
désactivée conformément au réglage antérieur ; aucun téléchargement Max
automatique n’a été déclenché.

Les anciens paquets sont conservés sous
`toolchain/releases-staging/windows-3.5.52/previous` et
`toolchain/releases-staging/android-1.0.23/previous`. L’archive chiffrée vérifiée
est identifiée par son empreinte dans le rapport de préparation. Les nouveaux
clients sont proposés par la mise à jour existante ; leur installation sur les
appareils physiques n’a pas été forcée.

Le retour doit traiter ensemble sources, binaires et données. Une ancienne
passerelle ne doit pas écrire dans le nouveau schéma sans validation. Avant un
retour, arrêter les nouvelles actions, sauvegarder les écritures postérieures,
préserver les révocations actuelles et utiliser la restauration guidée sur un
point cohérent. Ne pas restaurer aveuglément l’archive antérieure sur des données
ayant changé. Les rappels simples déjà échus et les tâches d’analyse ne doivent
pas repartir en rafale.

## Reconstituer et poursuivre

Préparer les ressources épinglées si elles sont absentes :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/2026-10-25-assistant-integration/prepare_wakeword.py --download
```

Les scripts de construction ordinaires les vérifient ensuite sans téléchargement
implicite. Voir `RECONSTRUIRE-FRED.md` et les manifestes de staging. Ne pas relancer
les scripts de publication après une livraison réussie sans examiner leurs preuves.

Restent nécessaires avant de qualifier tous les critères du plan : essais humains
microphone/caméra Windows et téléphone/tablette, détection française en bruit et
autonomie, livraison des alertes en veille réelle, concurrence prolongée des
synthèses avec les moteurs vocaux, mesures complètes de latence. L’activation
Android verrouillé n’est pas fournie. Les propositions sensibles génériques du
lot 9 restent distinctes de ces commandes métier réversibles. Les cases non
cochées du plan conservent ces exigences et les enrichissements non livrés.
