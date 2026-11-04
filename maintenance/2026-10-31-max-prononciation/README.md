# Prononciation en conversation Max — analyse du 31 octobre 2026

**Mise à jour après réception de la phrase « Léa posa le plateau… » : cause
reproduite et isolée dans le programme installé.** Voir
[DIAGNOSTIC-LEA.md](DIAGNOSTIC-LEA.md). Le diagnostic initial ci-dessous précédait
cet exemple précis et testait le modèle Python plutôt que son entrée dans
l’exécutable Windows ; ses conclusions provisoires sont dépassées par ce test.

Signalement : Max exécuté sur le PC du client, carte indiquée par l’utilisateur
comme une Radeon 7800 XT ; débit satisfaisant, certains mots semblent prononcés
dans une autre langue. Aucun mot exact ni enregistrement de l’incident fourni.

## Conclusion et niveau de certitude

Le complément actuel examiné utilise bien **Phonon 40m français Q8, Tiphaine,
ptts 0.4.1**, avec `lang='fr'`. Il n’y a pas de détection automatique de langue
dans ce chemin de synthèse. La reconnaissance Whisper utilise le GPU choisi ;
la synthèse Phonon s’effectue sur CPU. Changer de GPU ne modifie donc pas la langue
de cette voix.

Cela vérifie les sources et le complément disponible sur ce poste d’analyse,
**pas la version effectivement installée sur le PC Radeon de l’utilisateur**.
Un ancien complément Qwen3-TTS reste une possibilité à éliminer sur ce PC.

L’hypothèse d’une difficulté du synthétiseur sur certains mots ou leur contexte
est compatible avec le signalement. La cause précise de l’incident n’est pas
démontrée sans une phrase concernée et la version du complément client.

## Essais effectués

`inspect_segments.cjs` extrait les fonctions réelles `plain` et `splitSpeech`
du client, puis simule l’arrivée progressive du texte, caractère par caractère.
`segments.json` conserve le texte source, le texte nettoyé et les fragments
effectivement envoyés à la synthèse.

`probe.py` vérifie les empreintes de tous les fichiers `tts/` contre l’inventaire
du complément `vocal-rt-de5e67a320a06b1f`, puis exécute le vrai moteur Max Phonon
avec ces fichiers. Il enregistre les WAV et les retranscrit avec Whisper Turbo
sur CPU. Aucun microphone, historique utilisateur, service ou paramètre de
production n’a été utilisé ou modifié.

**7 textes fictifs, 11 sorties audio, 47,76 secondes de son.** Les variantes
comparent la phrase entière au découpage de conversation et, pour le Markdown,
le texte nettoyé au texte sans espaces ajoutés. Résultats détaillés dans
`results.json` ; les fichiers WAV permettent une écoute humaine ultérieure.

| Cas | Observation automatique | Interprétation |
| --- | --- | --- |
| Français courant | Texte correctement retranscrit, entier et découpé | Pas de défaut général de français sur cet exemple |
| Kiara / Windows / AMD Radeon RX 7800 XT | Kiara retranscrit Chiara ; référence GPU mal retranscrite | Alerte sur noms et références ; une différence orthographique ne prouve pas une mauvaise prononciation |
| Date, heure, M. Dupont | Contenu correctement retranscrit | Pas d’erreur établie sur ce cas |
| « Les poules du couvent couvent » | Retranscription anormale en phrase entière, correcte après découpage | Sensibilité possible au contexte ; écoute humaine nécessaire pour qualifier les phonèmes |
| Markdown et apostrophes | Le nettoyage transforme `L’**assistant**` en `L’ assistant` | Modification du texte confirmée ; aucune amélioration de retranscription démontrée en retirant ces espaces |
| 12,50 € et 5 % | Montant correctement retranscrit | Normalisation française des euros présente |
| cœur, œufs, écureuils, géraniums | Contenu correctement retranscrit, entier et découpé | Pas de perte générale des accents ou ligatures observée |

Sur les deux extraits Markdown très courts, Whisper répète la phrase dans sa
retranscription. Cela ne permet pas de conclure à une répétition dans l’audio
synthétisé : la transcription automatique est aussi une source d’erreur.

## Points de vigilance dans le parcours

- `client-voice/max_phonon.py` force le français, choisit Tiphaine et transmet le
  texte au moteur. La langue de normalisation est correcte dans ce code.
- `client-qwen/conversation.js`, fonction `splitSpeech`, coupe aussi aux virgules,
  points-virgules et deux-points à partir de 36 caractères pour le premier fragment,
  puis 100 ; une coupure supplémentaire intervient au-delà de 280 caractères.
  Chaque fragment est synthétisé indépendamment. Le contexte et la prosodie
  peuvent donc varier, sans qu’une langue étrangère ait été sélectionnée.
- `plain` remplace les marqueurs de mise en forme par des espaces. Cela peut
  séparer une élision ou un mot formaté ; c’est une piste à tester sur les mots
  effectivement signalés, pas une cause acoustique démontrée par ce corpus.
- Les anciens essais de livraison incluaient surtout fonctionnement, latence et
  trois phrases ordinaires. Ils n’établissent pas la qualité de prononciation
  sur les mots rares, homographes, noms propres et sigles.

## Suite ciblée proposée

1. Relever une ou deux phrases exactes mal prononcées et vérifier le moteur/version
   réellement installé sur le PC concerné.
2. Comparer leur audio avec et sans découpage, puis avec et sans nettoyage Markdown.
3. Si le défaut persiste sur une phrase intacte, comparer une autre voix française
   et les réglages de synthèse avant de remplacer le moteur ou le complément.

Aucun correctif applicatif, changement de modèle ou mise à jour du client n’a
été appliqué dans cette analyse.

## Références primaires

- [Fiche Phonon 40m français](https://huggingface.co/gradium/phonon-40m-fr) :
  modèle français, rôle de `lang`, limites pour les autres langues et la prosodie.
- [Normalisation du runtime 0.4.1](https://github.com/gradium-ai/xn-ptts/blob/v0.4.1/ptts/src/preprocess.rs).
- [Version 0.5.0](https://github.com/gradium-ai/xn-ptts/releases/tag/v0.5.0) :
  modification de la fenêtre d’attention du décodeur audio. Cette note ne prouve
  pas qu’une mise à jour corrigerait les mots concernés.

Rejouer depuis la racine :

```powershell
node maintenance/2026-10-31-max-prononciation/inspect_segments.cjs
& './toolchain/phonon-server-python/Scripts/python.exe' maintenance/2026-10-31-max-prononciation/probe.py
```
