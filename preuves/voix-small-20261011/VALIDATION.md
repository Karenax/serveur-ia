# Dictée locale Whisper Small — livraison du 11 octobre 2026

**Livré : Windows / console 3.5.20 et Android 1.0.3 (code 4).** Le moteur
Whisper.cpp 1.9.5 utilise Small multilingue complet, avec le français forcé,
sur le CPU du client. Les paquets et leurs empreintes sont vérifiés dans
[delivery-final.json](delivery-final.json). Le [guide utilisateur et technique](../../client-voice/README.md)
décrit l’installation et l’architecture.

La dictée locale est réalisée. La lecture orale des réponses et le dialogue vocal
continu ne sont pas livrés ; le lot 7 reste partiellement réalisé.

## Fin de parole et envoi

1. Installer la dictée une fois sur chaque appareil, puis choisir **Dicter**.
2. Parler : les aperçus peuvent évoluer pendant la reconnaissance.
3. Choisir **Terminer la dictée** : le micro ferme, la dernière transcription se termine.
4. Corriger le texte, puis choisir **Envoyer** pour obtenir la réponse de Fred.

Une pause de 1,5 seconde clôt une phrase, sans terminer la session ni envoyer de
message. La durée de capture est limitée à deux minutes. Annuler restaure le
brouillon précédent. En arrière-plan Android ferme le micro et finalise le texte.
Pendant la capture et la finalisation, l’envoi et le changement de conversation
sont bloqués. Le texte non envoyé reste un brouillon dans le champ de saisie.

L’audio est traité en mémoire, sans fichier ni transfert au serveur. Seul le texte
confirmé rejoint le transport de chat existant. Internet est nécessaire pour
installer le modèle public ; la dictée peut ensuite fonctionner hors connexion.
La réponse Qwen nécessite toujours la connexion au serveur.

## Paquets publiés

| Paquet | Version | Octets | SHA-256 |
| --- | --- | ---: | --- |
| `client-qwen/dist/Accès serveur Fred.exe` | 3.5.20 | 31 969 815 | `529f21aa22d14076e228f650d03e87751850641c0bd17aa52d80a9c3e83dea2d` |
| `client-android/dist/Acces-serveur-Fred-Android.apk` | 1.0.3 / 4 | 18 886 932 | `18cfee473417fd2b178e2db500aefa0dfd873f4ea6d652a5af63d33854263f90` |

Windows : manifeste de mise à jour signé et vérifié avec la clé existante ; test
du chargement et de l’arrêt de Small depuis l’exécutable empaqueté réussi.
[Rapport Windows](windows-release.json), [test du paquet](windows-exe-self-test.txt).
Les profils personnels continuent d’être fournis par la console habituelle.

Android : signature vérifiée, certificat SHA-256
`40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048`,
identité de production conservée. Installation finale avec `adb install -r` sur
les deux émulateurs : première date d’installation conservée et APK installé
identique octet pour octet au paquet publié. Aucun désinstallateur utilisé.
[Signature](android-signature.log), [mise à jour signée](android-signed-upgrade.json).

Le modèle est téléchargé séparément : **487 601 967 octets** (environ 488 Mo),
SHA-256 `1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b`.
Il est déjà installé et vérifié sur ce PC. Sur Android, le téléchargement HTTPS
réel a été interrompu à 1 389 524 octets, repris et vérifié jusqu’au modèle complet.
[Preuve de téléchargement](android-real-install.json), [spécification épinglée](../../client-voice/model.json).

Les bibliothèques ASR ARM64 et x86_64 finales sont identiques entre les APK debug
et release. Tous leurs segments ELF LOAD ont un alignement d’au moins 16 Ko.
Le paquet debug utilise l’identité séparée `net.karenax.fred.voiceqa`.
[Empreintes natives](android-release.json), [alignement ELF](android-elf-alignment.json),
[code réellement installé pour les essais](android-installed-code-check.json).
Les notices MIT de Whisper.cpp, ggml, du modèle et de llamafile sont incluses.

## Essais et mesures

L’entrée est une voix française synthétique Microsoft Hortense Desktop. Le test
de 10,05 secondes produit le texte suivant sur Windows et les deux émulateurs :

> Bonjour Fred. Je souhaite préparer une réunion demain matin. Ajoute les documents
> du projet et résume les décisions importantes.

| Environnement | Chargement | Calcul de transcription cumulé | Mémoire observée | Aperçu pendant la capture |
| --- | ---: | ---: | --- | --- |
| Windows, Threadripper 3955WX, 4 threads CPU | 0,453 s | 7,875 s pour 10,05 s d’audio | RSS 24 → 704 → 30 Mo ; environ 648 Mio supplémentaires au pic | Premier aperçu à 3 s, second à 7 s |
| Émulateur téléphone API 36, x86_64, 4 threads | 2,362 s | 61,952 s pour 10,05 s d’audio | PSS chargé 597 485 Ko, après libération 147 150 Ko | Aucun avant la fin de cet enregistrement court |
| Émulateur tablette API 36, x86_64, 4 threads | 0,885 s | 60,569 s pour 10,05 s d’audio | PSS chargé 590 874 Ko, après libération 111 118 Ko | Aucun avant la fin de cet enregistrement court |
| Émulateur téléphone, enregistrement long | 1,440 s | 99,040 s pour 30,15 s d’audio | PSS chargé 598 704 Ko, après libération 149 452 Ko | Oui ; texte final avec une répétition à une frontière de segment |

Ces durées de calcul sont celles rapportées par le moteur ; elles ne sont pas un
engagement de délai après le bouton Terminer. Windows a été testé sur le PC réel.
**Aucun téléphone ou tablette physique n’a été connecté ni mesuré. Small ne garantit
pas le temps réel sur Android.** Les émulateurs sans AVX pénalisent ce test et ne
prédisent pas la vitesse ARM64 d’un appareil réel. La qualité générale, les accents,
le bruit et la batterie restent à mesurer sur appareils physiques.

[Mesures Windows](windows-native-results.json), [téléphone](android-phone-voice.log),
[tablette](android-tablet-voice.log), [enregistrement long](android-phone-long-voice.log).
Le test Windows vérifie également un silence sans texte inventé, une annulation
et l’ouverture/fermeture du microphone WinMM. Sur Android, AudioRecord a été ouvert
et fermé par le passage réel en arrière-plan ; le refus de permission système a
été essayé sur la tablette, sans ouverture du microphone.

| Vérification | Résultat | Preuve |
| --- | --- | --- |
| Régressions serveur complètes | 246 tests, OK, 473,786 s | [Journal](regressions.log) |
| Contrôles de livraison finale, comptes, appareils, démarrage Windows | 15 tests, OK, 59,125 s | [Journal](delivery-targeted-tests.log) |
| Service local Windows, intégrité, reprise, sessions, erreur micro | 8 tests, OK | [Journal](service-tests.log) |
| Routes HTTP locales, autorisation, origine, aucun appel distant ASR | 3 tests, OK | [Journal](http-tests.log) |
| Contrôles Python Android | 13 tests, OK | [Journal](android-python-tests.log) |
| Interface commune : brouillon, aperçu, Terminer, Annuler, erreur, tailles | 6 scénarios, aucune exception JavaScript | [Rapport](browser/voice-ui.json) |
| Interface Android native finale téléphone et tablette | Pas de débordement ni erreur JS ; boutons tactiles et libellés contrôlés | [Téléphone](android-phone-ui.log), [tablette](android-tablet-ui.log) |
| Synthèse des paquets finaux et empreintes sources | PASS | [Rapport](delivery-final.json) |

La suite de 246 tests a été exécutée après finalisation des moteurs et contrôleurs,
avant le dernier ajustement CSS de largeur des boutons et la version Windows
3.5.20. Après ces changements, les 15 tests ciblés, les six scénarios navigateur,
les essais visuels Android et les contrôles des paquets reconstruits ont été
exécutés. Les bibliothèques natives utilisées pour les mesures correspondent
toujours aux paquets finaux. Le premier passage de régression avait révélé un
encodage altéré et un ancien manifeste de livraison ; ils ont été corrigés avant
le passage complet réussi. Son journal initial est conservé.

Captures de l’interface finale : [téléphone](emulator-5554-voice-ui.png),
[microphone actif](emulator-5554-microphone-listening.png),
[tablette](emulator-5556-voice-ui.png).

## Préservation du serveur

Les processus Qwen/Strata PID 8200 et 14628 gardent leur date de création.
Leur santé et le modèle chargé ont été contrôlés après publication. Seule la
console a été relancée avec conservation de l’état du modèle. Les empreintes
des accès, réglages et secrets protégés, les lignes logiques des données utilisateur
et la programmation des sauvegardes sont identiques avant/après. La sauvegarde
serveur reste quotidienne à 03:00, rétention 7/4/6, sans seconde destination.
Les Tesla P100 et les environnements Qwen n’ont pas été modifiés.
[Comparaison après publication](production-after.json), [état avant](production-before.json).

## Reproduction

Depuis la racine du dépôt avec le Python existant :

```powershell
& 'Strata-src/.venv/Scripts/python.exe' -X utf8 client-voice/test_service.py
& 'Strata-src/.venv/Scripts/python.exe' -X utf8 client-voice/test_http.py
& 'Strata-src/.venv/Scripts/python.exe' -X utf8 preuves/voix-small-20261011/test_native_windows.py
node lanceur/web/tests/voice_ui.mjs
```

Le script [finalize_delivery.py](finalize_delivery.py) vérifie les empreintes,
le code QA installé et l’alignement ELF, puis réinstalle les APK finaux avec `-r`
sur les deux émulateurs de test. Il nécessite ces émulateurs déjà démarrés et
leurs applications QA présentes. Les journaux de compilation Windows et Android
sont conservés dans ce dossier. Aucun essai ne doit lire la phrase de récupération
des sauvegardes ni modifier les environnements du modèle serveur.
