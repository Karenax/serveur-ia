# Contexte vocal 16k et latence du parcours réel — 23 octobre 2026

La mesure du modèle seul sous-estimait le délai du client : le véritable appel
oral ajoutait six extraits de mémoire. `gateway-before.json` mesure 7,609 secondes
avant le premier texte via la passerelle authentifiée locale, contre 2,2–2,5 s sur
deux demandes courtes adressées directement au modèle lors de l'essai précédent.
Le premier PCM de Phonon arrive en 0,026 s. Ces parcours et prompts diffèrent : la
comparaison indique où rechercher le délai, pas un benchmark causal contrôlé.

L'utilisateur a demandé un plafond de contexte vocal de 16k. La version Windows
et serveur 3.5.41 applique **16 384 tokens au total**, dont 512 réservés à la sortie
et 15 872 disponibles pour l'entrée. Strata compte les messages avec son véritable
tokenizer et le même template, réflexion désactivée. Les messages système gardent
leur ordre, comme dans la requête OpenAI textuelle. Aucun calcul du modèle n'est
lancé par ce comptage.

Si nécessaire, les échanges utilisateur/assistant les plus anciens sont retirés
de la seule requête, par groupes complets. La question actuelle, les consignes et
les références restent intactes. L'historique local et serveur reste complet.
Si ces éléments indispensables dépassent déjà le plafond, une erreur conseille
de raccourcir ou de passer à l'écrit. Aucun dépassement silencieux n'est autorisé.

Le plafond concerne la requête vocale ; il ne réduit pas la capacité globale du
moteur, ne recharge pas Qwen et ne libère pas à lui seul un éventuel cache GPU
préalloué. Les conversations écrites conservent leur contexte long. Une petite
requête n'utilisait pas automatiquement 260k tokens auparavant : le plafond de 16k
ne peut accélérer cette petite requête à lui seul.

## Autres attentes corrigées

- Les références de mémoire ne sont plus sérialisées deux fois dans le prompt
  (`text` et `passage`) avec des métadonnées redondantes. Leurs textes et citations
  complets restent disponibles dans les sources de l'interface.
- La conversation déjà présente dans les messages n'est pas rappelée une seconde
  fois depuis l'index. L'exclusion normalise les UUID et respecte propriétaire et
  projet ; les autres conversations et mémoires restent disponibles.
- Les références variables sont placées près de la nouvelle question. Les
  consignes stables et l'historique précédent peuvent ainsi conserver leur préfixe
  pour le cache du moteur, au lieu d'être précédés de références différentes à
  chaque demande. Les avertissements sur les sources non fiables restent aussi
  dans les consignes système stables.
- Un index vide ne déclenche plus un calcul d'embedding inutile.
- Le comptage de contexte écrit est suspendu pendant l'appel. L'interface affiche
  le plafond vocal et le compte réellement communiqué par le serveur, puis
  rétablit la jauge écrite après raccrochage.

## Vérifications

`test_voice_context.py` couvre la réserve de sortie, la conservation des consignes
et de la question actuelle, le retrait d'échanges entiers et l'absence de mutation
de l'historique. `test_voice_conversation.py` vérifie le plafond via HTTP réel,
l'accès au projet et les annulations/révocations. `test_knowledge.py` vérifie
l'exclusion de la discussion courante, la présence des autres sources et les
droits. Les tests workspace existants sont rejoués sur données fictives.

Les six suites UI partagées vérifient aussi l'affichage vocal 16k et le compte
reçu, le raisonnement masqué, la reprise à l'écrit et les historiques distincts.
Les ressources Android sont régénérées ; aucun nouvel APK n'est publié ici.

`verify.py` valide l'EXE construit, les sources embarquées, les 16 tests de mise à
jour et les rapports des 57 tests backend. `activate.py` publie avec la clé de
signature existante et vérifie données, clés, sauvegardes et processus Qwen.
Les résultats de mesures après publication figurent dans `gateway-after-*.json`.
Le script emploie uniquement une demande fictive, ne crée pas de compte ni
d'historique, ne sauvegarde aucun texte de réponse ni secret et n'ouvre pas de
second tunnel WireGuard. Il ne mesure pas le microphone ou la lecture navigateur.

## Résultats après publication

Le premier essai passe par HTTPS Cloudflare, avec les en-têtes du client et sans
proxy système. Il mesure 6,384 s avant le premier texte, avec **1 014 tokens**
d'entrée, six sources et le plafond confirmé de 16 384 tokens. Le premier PCM
arrive en 0,179 s. Le modèle et le traitement de son prompt restent donc une
source importante de délai, même largement sous 16k. Le plafond ne suffit pas à
garantir une réponse orale en moins de cinq secondes.

La répétition de la même question en boucle locale, après cet essai, mesure
1,744 s avant le texte et 0,026 s avant le PCM. Cet essai est réchauffé et ne
doit pas être présenté comme la latence d'une nouvelle question via Cloudflare.
Le cache du modèle, le contenu de l'historique et les références retrouvées
expliquent une partie de la variabilité possible. La comparaison entre les deux
transports ne permet pas d'attribuer leur différence au réseau.

Le moteur conserve son contexte global de 262 144 tokens, ses poids et ses
processus chargés. Ses réglages n'ont pas été modifiés pendant ces mesures.
La réduction de la latence à froid du modèle reste à traiter séparément d'un
plafond de contexte ; aucun changement de modèle ni redémarrage de Qwen n'a été
effectué. Les 73 tests techniques, les six suites UI et le contrôle de sources
sont réussis ; les données, clés et sauvegardes ont été vérifiées préservées.
