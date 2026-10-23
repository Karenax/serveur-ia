# Corrections de l’audit UX — 22 octobre 2026

Les douze constats du [rapport initial](<D:/Serveur IA/audits/2026-10-22-ux/RAPPORT.md>) ont été traités dans les sources Windows, Android et console. Les ressources Android ont été régénérées par le script officiel. Les modifications préexistantes du dépôt ont été conservées.

## Corrections par constat

| Audit | Changement appliqué | Vérification |
| --- | --- | --- |
| UX-01 — Saisies non enregistrées | Brouillons de messages enregistrés dans les préférences chiffrées, état de sauvegarde et bouton de reprise en cas d’échec. Avertissement au rechargement pour les consignes non enregistrées et les réglages modifiés. La fermeture native Windows et la préparation des mises à jour sauvegardent les brouillons ; les saisies de mémoire/tâche encore en attente signalent leur état au mécanisme de fermeture. | Rechargement, panne injectée, annulation du départ, reprise par bouton, effacement puis rechargement. Garde de console testée dans le navigateur. |
| UX-02 — Mauvais contexte du brouillon | Un brouillon par identifiant de conversation. Une nouvelle conversation commence vide ; revenir à une conversation retrouve son texte. La suppression retire le brouillon correspondant ; l’annulation restaure aussi ce brouillon. | Scénarios Windows et HTML Android, avec rechargement et suppression/annulation. |
| UX-03 — Focus de navigation | Navigation latérale modale sur écran étroit, contenu arrière inerte, focus à l’ouverture, boucle Tab/Maj+Tab, fermeture par Échap, retour au bouton puis focus sur le titre de destination. Bouton de fermeture masqué sur bureau. Les flèches de la console parcourent aussi les rubriques ajoutées dynamiquement. | Tests à 390 et 768 px ; parcours réel des seize rubriques de console au clavier ; captures. |
| UX-04 — Suppression de mémoire | Confirmation citant le contenu avant suppression. Échec visible et texte conservé ; suppression réussie annoncée. | Annulation, refus serveur puis succès. |
| UX-05 — Contraste | Texte secondaire clair passé de `#73736d` à `#686862` dans les palettes partagées du client et de la console. | Mesures dans le navigateur : voir tableau ci-dessous. |
| UX-06 — Noms accessibles | Chaque mémoire existante dispose d’un label associé. La fenêtre de citation est reliée à son titre par `aria-labelledby`. | Labels calculés et fenêtre « Passage fictif » trouvée par son nom accessible. |
| UX-07 — État sélectionné | `aria-current` sur les destinations et rubriques du projet ; `aria-pressed` sur les filtres de tâches. Suppression de `aria-selected` sur les boutons sans rôle d’onglet. | Attributs vérifiés dans les scénarios et navigation réelle. |
| UX-08 — Contenu principal | Repère principal stable sur l’espace de travail, conversation interne exposée comme région nommée, lien « Aller au contenu » dans le client et la console. | Un seul repère principal actif dans Projets, y compris sur petit écran. |
| UX-09 — Envoi mobile | Emplacement réservé à droite pour Envoyer/Arrêter sous 620 px ; les options conservent leur place disponible, sans masquer projet, fichier ou réflexion. | Bouton Android de 44 × 44 px à x=324 sur une largeur de 390 px ; captures clair/sombre et tablette. |
| UX-10 — Mémoire supprimée encore visible | Mise à jour par identifiant des lignes de mémoire. Les champs en cours d’édition survivent aux actualisations. Une action de suppression réussie retire immédiatement sa ligne et replace le focus sur la nouvelle saisie. | Rafraîchissement pendant une modification, sauvegarde, suppression et vérification du focus. |
| UX-11 — Lisibilité | Aides de documents, textes de contexte, légendes, état de sauvegarde et informations secondaires ciblées relevés à 11 px ; certaines aides et actions de console passent à 12 px sur téléphone. Densité métier conservée. | Captures bureau/téléphone/tablette. Agrandissement système sur appareil physique non testé. |
| UX-12 — Cohérence des textes | Titres de console alignés sur les noms de navigation, badge « Accès personnel », explication de connexion indépendante du transport, pluriels des nouveaux résultats corrigés. L’aide tactile Android était déjà adaptée par la génération et a été conservée. | Lecture des sources assemblées, titres réellement affichés, captures. |

## Protection des brouillons

Les messages en préparation utilisent le stockage chiffré déjà employé par les préférences : DPAPI sur Windows, stockage sécurisé Android. Aucun texte de brouillon n’est ajouté au localStorage.

Les écritures sont limitées aux conversations modifiées, afin qu’une fenêtre n’efface pas les brouillons d’autres conversations enregistrés par une autre fenêtre. Une valeur vide supprime le brouillon concerné. Les validateurs Windows/Android bornent le contenu ; un dépassement reste une erreur visible et ne remplace pas silencieusement les données précédentes.

L’enregistrement est différé de 350 ms après saisie. Une sauvegarde non confirmée déclenche un avertissement au départ et permet une nouvelle tentative. Une interruption brutale du processus pendant ce délai reste distincte d’une fermeture normale.

Les consignes de projet conservent leur bouton d’enregistrement explicite : le navigateur avertit si elles ne sont pas enregistrées. Le mécanisme natif Windows existant continue de les enregistrer à la fermeture. Il n’a pas été remplacé par une sauvegarde silencieuse sur chaque frappe.

## Contrastes mesurés

Les couleurs proviennent des variables calculées dans le navigateur. Mesure du texte secondaire sur les trois fonds du client :

| Thème | Navigation | Fond surélevé/compteur | Fond principal |
| --- | --- | --- | --- |
| Clair | 5,23:1 | 4,91:1 | 5,61:1 |
| Sombre | 6,14:1 | 4,60:1 | 5,69:1 |

Ces mesures concernent les couples de couleurs indiqués. Elles ne constituent pas une certification de tous les contrastes ou une déclaration de conformité WCAG complète.

## Tests exécutés

- **6 suites UI réussies** via `npm.cmd --prefix client-qwen test`, avec la nouvelle suite [test_ux_recovery_ui.cjs](<D:/Serveur IA/client-qwen/test_ux_recovery_ui.cjs>). Les scénarios couvrent Windows et le véritable HTML Android généré.
- **24 tests Python client réussis**, dont les préférences chiffrées et la validation des brouillons. Vérification supplémentaire de la limite cumulée quand deux écritures séparées dépasseraient la capacité totale.
- **13 tests Python des outils Android réussis.**
- **20 contrôles du catalogue Hermes réussis**, avec données synthétiques.
- **Compilation Java Android debug réussie** avec Gradle hors ligne. Aucun APK de production installé.
- **Contrôle des sources réussi** : 248 sources Python, 67 scripts JavaScript et 93 scripts PowerShell sur chaque moteur disponible.
- **Ressources Android à jour**, vérifiées par `Prepare-Assets.py --check`.
- **Contrôle UX exécuté** : trois avertissements de textes longs de la console relus et conservés ; ces informations préexistaient et restent utiles. Aucune exclusion ajoutée.
- Contrôle des espaces sur les fichiers de cette correction, avec prise en compte des fins de ligne CRLF.

Les logs des suites sont dans ce dossier. Les mesures de navigateur sont conservées dans `browser-validation.json`.

## Preuves visuelles

- [Conversation Android — téléphone clair](<D:/Serveur IA/audits/2026-10-22-ux/corrections/android-chat-390-light.png>)
- [Conversation Android — tablette sombre](<D:/Serveur IA/audits/2026-10-22-ux/corrections/android-chat-768-dark.png>)
- [Reprise d’un brouillon après erreur](<D:/Serveur IA/audits/2026-10-22-ux/corrections/windows-draft-retry.png>)
- [Mémoire et actions](<D:/Serveur IA/audits/2026-10-22-ux/corrections/windows-memory.png>)
- [Navigation ouverte au clavier](<D:/Serveur IA/audits/2026-10-22-ux/corrections/windows-sidebar-focus.png>)
- [Console — téléphone](<D:/Serveur IA/audits/2026-10-22-ux/corrections/console-launch-390.png>)
- [Console — carte réseau avec données fictives](<D:/Serveur IA/audits/2026-10-22-ux/corrections/console-network-1440.png>)

## Portée de livraison et limites

Les corrections sont appliquées aux sources locales et aux ressources Android générées. Aucun EXE signé ni APK de production n’a été republié ; aucun redémarrage du serveur Qwen, changement de réseau ou migration de données de production n’a été réalisé.

Les vérifications visuelles utilisent Chrome et des fixtures locales. Les appels de lecture de la carte réseau ont été remplacés par un état synthétique pour les captures conservées ; aucune commande de réseau n’a été exécutée. Les interfaces natives Windows/Android, TalkBack/NVDA, le toucher réel, le clavier logiciel réel et les fermetures système sur appareil physique restent à vérifier. Les garde-fous de fermeture native ont été intégrés dans les chemins existants et contrôlés en source ; leur exécution physique n’est pas revendiquée.

