# Deux niveaux vocaux pour Kiara — recherche du 24 octobre 2026

**Suite à la décision de l’utilisateur : le PC et le serveur Kiara sont autorisés.**
Le sélecteur et les deux parcours sont maintenant implémentés dans les sources.
Voir [l’intégration et les validations](IMPLEMENTATION.md). Les sections ci-dessous
conservent les conclusions de l’étude préalable ; elles ne décrivent pas un
déploiement de Voxtral 3 ni une mesure de qualité acoustique.

## Proposition retenue pour évaluation

Conserver deux profils distincts dans la page Vocal : **Qualité : Low / Max**.
Low conserve le fonctionnement actuel ; Max doit améliorer l’écoute en direct et
la voix, tout en gardant Qwen, les documents, les sources et l’historique de Kiara.
La dictée du chat reste indépendante. Aucun de ces gains n’est encore mesuré dans
Kiara : cette étude ne constitue pas une intégration du second moteur.

| Profil | Écoute | Réponse | Lecture | Cible |
| --- | --- | --- | --- | --- |
| Low | Parakeet v3 int8 + Silero + Smart Turn, déjà présents | Qwen Kiara sur le serveur | Phonon/Tiphaine, déjà présent côté serveur | PC modestes, faible charge locale |
| Max, candidat principal | Voxtral Mini 4B Realtime 2602, streaming local | Même Qwen Kiara | Qwen3-TTS 1.7B CustomVoice local, à comparer à la voix actuelle | PC avec accélération et mémoire suffisantes, après mesure |

Low signifie ici léger. La supériorité systématique de Max en reconnaissance
française ne peut pas se déduire de la taille des modèles : comparer sur les mêmes
phrases, dans le bruit et avec les noms utilisés dans Kiara.

## Voxtral 3 : distinguer l’offre complète et les poids téléchargeables

[Voxtral 3](https://mistral.ai/news/voxtral-3/) combine des modèles de transcription,
un modèle de dialogue et une synthèse expressive dans un SDK d’agent vocal.
Mistral propose une API et un déploiement sur infrastructure privée en contactant
son équipe. Les sources examinées ne fournissent pas de paquet public complet
Voxtral 3 prêt à embarquer dans un EXE Windows. Ne pas présenter le modèle ouvert
2602 comme étant Voxtral 3. Remplacer le modèle de dialogue par celui de Mistral
n’est pas nécessaire pour l’objectif de Kiara.

## Voie locale accessible

[Voxtral Mini 4B Realtime 2602](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602)
est une reconnaissance vocale en streaming, sous Apache 2.0, comprenant le français.
Mistral recommande un délai de transcription de 480 ms ; ce délai n’inclut ni la
fin de tour, ni Qwen, ni la synthèse, ni le réseau. Le déploiement BF16 documenté
demande un GPU d’au moins 16 Go. Ce chiffre ne représente pas la mémoire cumulée
d’une conversation avec plusieurs modèles.

Une [démo WebGPU publiée par Mistral](https://huggingface.co/spaces/mistralai/Voxtral-Mini-4B-Realtime-WebGPU)
montre une autre voie locale : Transformers.js et les poids ONNX q4f16. Son code
exige WebGPU et `shader-f16`. L’encodeur, les embeddings et le décodeur quantifiés
totalisent environ **2,84 Go décimaux de poids**, calculés à partir des fichiers
de la révision inspectée. Les caches, buffers et le moteur augmentent la mémoire
nécessaire. Un téléchargement de cette taille ne prouve ni la consommation mémoire
totale ni la fluidité sur un PC donné. Le WebView Windows doit être testé, même si
Chrome fonctionne sur le même appareil.

[Qwen3-TTS 1.7B CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)
est un candidat pour la seconde partie de Max : français, synthèse en streaming et
contrôle de style documentés, poids sous Apache 2.0. Le choix de la voix et la
prononciation française demandent une écoute comparative. La variante 0.6B peut
servir de candidat plus léger si le couple complet ne tient pas dans le budget
du PC. Aucun chiffre de latence publié par le fabricant n’est repris comme une
mesure sur Kiara.

Autre piste d’écoute : [Qwen3-ASR 0.6B/1.7B](https://github.com/QwenLM/Qwen3-ASR),
français et poids publics. À conserver comme alternative de benchmark, sans
multiplier les profils visibles avant d’avoir mesuré leur intérêt.

## Contraintes concrètes

Le runtime [vLLM actuel](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/index.html)
demande Linux et, pour NVIDIA, une compute capability d’au moins 7.5. Windows
n’est pas pris en charge nativement. Il ne convient donc pas comme dépendance
embarquée transparente dans le client Windows existant. Le backend WebGPU ou un
worker natif indépendant mérite un prototype avant tout choix définitif.

La [synthèse Voxtral 4B TTS 2603](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603)
est une autre option, mais sa fiche indique des poids sous CC BY-NC 4.0 et un GPU
d’au moins 16 Go pour la voie BF16 documentée. Elle n’est pas retenue comme choix
par défaut pour un client redistribuable sans examiner les conditions applicables.

Sur la machine du projet, inspection en lecture seule : Threadripper Pro 3955WX,
128 Go de RAM, Quadro P2200 5 Go/CC 6.1 et deux Tesla P100 16 Go/CC 6.0. Au moment
de l’inspection, chaque P100 n’avait qu’environ 1,7–1,9 Go libres. Ce ne sont pas
les caractéristiques des PC des utilisateurs. Ces GPU ne satisfont pas le minimum
du runtime vLLM actuel ; aucune conclusion universelle sur les autres backends ne
doit en être tirée. Aucune charge, décharge de modèle ou modification de runtime
n’a été effectuée.

## Comportement du sélecteur

Dans Vocal, afficher deux choix Low et Max avec une courte description et le
résultat du test local. Garder le choix manuel et l’enregistrer par PC. Changer
de profil entre deux appels, afin de préserver une phrase ou une réponse en cours.
Un profil non installé propose son installation et son volume de téléchargement.
Un profil non compatible explique pourquoi ; il ne doit pas sembler actif en
utilisant silencieusement le moteur Low.

Le test de compatibilité doit charger le vrai moteur sélectionné et traiter un
échantillon fictif : capacité et disponibilité mémoire, temps de chargement,
transcription plus rapide que le son entrant, délai avant le premier son et débit
de synthèse. Mesurer les deux composants en charge conjointe. Définir ensuite les
seuils produit et une marge mémoire ; ne pas classer les appareils uniquement
d’après une marque de GPU, sa mémoire totale ou sa quantité de RAM.

## Intégration envisagée

- Conserver `conversation_service.py` comme propriétaire de la session et du micro.
  Choisir un worker par profil sans modifier les ACK, l’annulation ni le mute.
- Échanger le même format de transcriptions avec `conversation.js` ; conserver
  les appels Qwen et la recherche web existante.
- Choisir la lecture locale Max ou la lecture serveur Low au niveau de la session.
  Une panne doit être visible et permettre un retour explicite vers Low.
- Préparer les runtimes, modèles et licences dans des dossiers séparés, avec
  révisions et empreintes, sans ajouter ces dépendances à Strata ou Phonon.
- Vérifier profils installés/non installés, changement pendant un appel, manque
  de mémoire, réparation, annulation, interruptions, dictée et sauvegarde.

Il reste à préciser si le traitement vocal Max doit être exécuté exclusivement
sur chaque PC ou peut être déporté sur le serveur Kiara. Cette décision change le
transport de l’audio, les installations à distribuer et le budget matériel. La
question a été présentée dans le chat ; aucun service audio extérieur n’a été activé.

## Révisions inspectées et limites

- Démo WebGPU Mistral : `46348b09402e5f6c906010c92ebe95f3884c23cb`,
  dépendance déclarée `@huggingface/transformers` `4.0.0-next.7`.
- [Poids ONNX](https://huggingface.co/onnx-community/Voxtral-Mini-4B-Realtime-2602-ONNX) :
  `db34633130c460bd650644fc18dc90710d9f3e38`.
- Qwen3-TTS 1.7B CustomVoice : `0c0e3051f131929182e2c023b9537f8b1c68adfe`.

Recherche documentaire, lecture des sources publiques et inspection matérielle
réalisées. Aucun poids téléchargé, benchmark d’inférence, écoute comparative,
installation, modification du sélecteur de l’application ou déploiement réalisé
dans cette étude. Le moteur Low et la page Vocal précédemment implémentés sont
préservés.
