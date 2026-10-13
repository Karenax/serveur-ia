# Corrections de l’audit — livraison du 12 octobre 2026

Les **sept défauts de l’audit sont corrigés**, les optimisations prévues sont
implantées et les nouvelles distributions sont publiées : **Windows/serveur
3.5.28**, **Android 1.0.11/code 12**. Branche de travail :
`codex/audit-corrections-20261012`, à partir de `ffe85204729db298ac83848e727e2b9aa10f5548`.

La console a été rechargée avec Qwen conservé. Les contrôles avant/après retrouvent
les mêmes processus du modèle, empreintes des données utilisateur, clés et réglages
d’accès, ainsi que la même programmation des sauvegardes. Les deux dossiers clients
sont prêts ; Hermes est disponible et EG2 est prêt, avec aucun passage en attente.
Une sauvegarde chiffrée a été créée et vérifiée avant **et** après publication.
La preuve sans valeurs de secrets est [production-corrections.json](production-corrections.json).

## Défauts corrigés

| Référence | Résultat et vérification |
| --- | --- |
| R01 | Initialisation et migrations SQLite communes aux espaces et exports clients. Les conversations de projet actives et archivées sont exportées, avec base individuelle intègre et sauvegarde reconnue. Un export défectueux ne bloque plus les autres clients. |
| R02 | Admission à la limite de messages, validation commune avant projection et conservation de l’historique valide. Une réponse trop volumineuse ou une erreur d’écriture produit un résultat récupérable pendant 30 jours, avec zone d’export Windows/Android et reprise après rechargement. Aucun texte n’est tronqué silencieusement. |
| R03 | Suppression des copies redondantes d’entrée/transcript, empreinte multimodale de continuité, comptage des profils et du journal natif dans les quotas, réservation avant admission et contrôle pendant l’exécution. Rétention de 24 h des résultats ordinaires, 30 jours des résultats à récupérer et sessions inactives suivies ; nettoyage et compaction au repos. Sauvegardes Hermes bornées à 144 Mio, incluant le journal natif d’idempotence. |
| R04 | Métadonnée de tour transportée par le véritable client MCP natif ; appels d’inférence privés et helpers de fournisseur liés au tour Fred. Les appels retardés d’un tour annulé sont refusés. Vérification HTTP synthétique, transport MCP réel et appels réels au Qwen chargé. |
| R05 | Transcript multimodal distinct de la projection textuelle. La reconstruction et l’empreinte de continuité tiennent compte des images. L’adaptation native corrige aussi la conversion en texte dans `/v1/runs` et transmet la capacité de vision du modèle sélectionné. Une ancienne image arrive réellement à la frontière du fournisseur HTTP. |
| R06 | Modification d’une mémoire facturée sur l’augmentation réelle de sa taille. Essais inchangé/réduction/augmentation près du quota réussis. |
| R07 | Apostrophe EG2 corrigée. Les 86 scripts passent l’analyse syntaxique sous PowerShell 7 et Windows PowerShell 5.1. Un ancien script de comparatif a également reçu un BOM UTF-8 pour corriger sa lecture sous 5.1, sans changer son contenu. |

Les scénarios ciblés sont dans `lanceur/test_audit_corrections.py` et les tests
natifs ajoutés dans `lanceur/test_hermes_models.py`. Les premières reproductions
demeurent dans le [rapport initial](RAPPORT-AUDIT.md), qui décrit l’état avant correction.

## Optimisations et entretien

- La lecture d’une sauvegarde utilise sa taille constatée au lieu d’allouer
  systématiquement la limite de 400 Mio. Les représentations temporaires de
  l’archive sont libérées avant vérification ; la restauration réutilise le paquet
  validé sans enveloppe chiffrée temporaire supplémentaire.
- Les exports utilisent des révisions par propriétaire, avec vérification
  d’intégrité toutes les cinq minutes. Les battements de bail du worker ne
  déclenchent plus un export. L’index EG2 relit les sources seulement après leur
  modification et préserve les vecteurs déjà disponibles.
- Android conserve uniquement l’APK vérifié en attente d’installation et nettoie
  les anciens APK/partiels gérés. Les fichiers étrangers et les liens sont préservés/refusés.
- Console, adaptateur privé, passerelle et client Windows partagent le même
  serveur HTTP borné et la validation JSON. Les connexions incomplètes ont un délai
  de 30 secondes et une limite de workers ; les flux SSE restent couverts.
- 29 imports inutilisés et six variables inutilisées ont été retirés. Les
  réexports de compatibilité restent explicites, le callback WinMM conserve sa
  signature native et le calcul scrypt factice hérité devient paresseux.
- Les cinq anciens générateurs sont conservés, neutralisés et indexés dans
  `maintenance/legacy-20261012`. Le contexte courant est court ; son historique
  complet est conservé dans un document distinct. Les versions ambiguës sont
  actualisées ou marquées historiques.
- Les tests navigateur utilisent un module et navigateur configurables, avec
  dépendance Playwright épinglée et lockfile. Chaque build produit un manifeste
  des sources, outils et dépendances réellement employés. L’archive de sources
  comprend les nouveaux modules, sources natives, contrats et références des moteurs.

## Résultats des vérifications

| Vérification | Résultat |
| --- | --- |
| Suite Python serveur complète | **440 tests réussis**, 715,142 s, incluant les neuf premiers scénarios de correction |
| Régressions finales sauvegarde/restauration/Hermes | **127 tests réussis**, 270,076 s, sur les corrections finales |
| Rétention, migration et erreur de projection | **46 tests réussis**, 41,935 s |
| Invalidation, exports, EG2 et worker | **38 tests réussis**, 46,669 s |
| Client Windows Python | **17 tests réussis** |
| Voix Python | **20 tests réussis** |
| Outils de livraison Android Python | **13 tests réussis**, pendant le build |
| Scénarios nouveaux | **14** : 12 scénarios transversaux et deux à la frontière native fournisseur/MCP ; tous réussis |
| JavaScript | **8 suites réussies**, dont cinq suites navigateur sur les sources Windows/Android et trois suites serveur |
| Syntaxe courante | **166 Python**, **60 JavaScript**, **86 PowerShell sur chacun des deux moteurs**, tous réussis |
| Ruff sur applications et utilitaires actuels | **101 fichiers**, zéro F401/F841/F821 ; les tests et archives sont distingués de ce périmètre |
| Android `lintDebug` et compilations debug/instrumentation | Réussis ; aucun nouvel échec de lint |
| Android natif sur émulateur API 36 | Politique de manifeste/intégrité/signature/version et conservation du cache réussies |
| Windows compilé | Ressources communes exactes, module HTTP partagé inclus ; auto-tests WireGuard, dictée et conversation vocale réussis |
| APK release | Signature vérifiée, ressources communes exactes, absence de profils/DPAPI personnels |
| Hermes/Qwen natifs réels | Quatre tours terminés ; calcul MCP, reprise de session, transcript d’outil, isolation des accès, projet natif, recherche documentaire, sources et création automatique de profil réussis |
| Publication | Manifestes vérifiés, EXE personnel reconditionné avec son accès conservé, deux dossiers clients prêts, données et clés inchangées |

Les passages réexécutés se recouvrent : les compteurs des différentes suites ne
doivent pas être additionnés comme des tests distincts. Les 481 tests préexistants
et les 14 nouveaux scénarios ont été couverts. Les journaux `corrections-*.log`
contiennent les exécutions ; JSON de synthèse, manifestes et preuves de publication
sont conservés dans ce dossier.

La validation native réelle est dans [corrections-native-qwen.json](corrections-native-qwen.json).
Les ressources et workers compilés sont vérifiés dans
[artifacts-verification.json](artifacts-verification.json). Les contrôles statiques
sont dans [corrections-ruff-active.json](corrections-ruff-active.json).

## Mesures de volume

Le test réaliste de 16 Mio de documents mesure désormais environ **219 Mio** de
RAM supplémentaire maximale contre environ **395 Mio** pendant l’audit initial,
soit une réduction proche de **45 %**. Les empreintes des originaux restaurés correspondent.

| Documents originaux | Archive chiffrée | Sauvegarde | Restauration | Pic de RAM supplémentaire |
| --- | --- | --- | --- | --- |
| 16 Mio, 8 documents | 30 251 923 octets | 1,719 s | 5,016 s | 229 306 368 octets |
| 64 Mio, 32 documents | 119 906 279 octets | 5,110 s | 14,687 s | 908 161 024 octets |
| 120 Mio, 60 documents | 224 502 847 octets | 8,766 s | 15,515 s | 1 699 262 464 octets |

120 Mio d’originaux laisse de la place pour le texte, les index et les métadonnées
dans la limite globale de 128 Mio de données facturées. Les jeux sont synthétiques,
isolés et composés d’originaux DOCX valides ; la conservation est vérifiée par SHA-256.
Le format portable compatible avec les anciennes sauvegardes demeure monolithique :
les gros volumes gardent un coût de mémoire visible. Ces mesures n’extrapolent pas
la performance à d’autres données ou machines.

## Distribution et suite

Les versions publiées sont servies depuis `client-qwen/dist` et `client-android/dist`.
Les distributions précédentes restent dans `toolchain/releases-staging/pre-audit-20261012`
et l’ancien EXE personnel possède son archive de retour habituelle. Les paquets et
manifestes de construction de cette livraison figurent aussi dans `distribution/`.
Les clients existants récupèrent leur mise à jour par les mécanismes habituels ;
Android conserve sa confirmation native d’installation.

La préparation d’un autre poste est décrite dans [RECONSTRUIRE-FRED.md](../../RECONSTRUIRE-FRED.md).
Les essais Android de cette correction ont été effectués sur émulateur ; aucun
téléphone physique n’était connecté. Cet audit ne certifie pas l’intégralité du
code tiers, des poids ni les vulnérabilités publiées des dépendances.
