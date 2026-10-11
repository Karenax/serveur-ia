# Réflexion par modèle — audit du 11 et correction du 12 octobre 2026

## Audit des envois

Les deux derniers envois Nemotron du 11 octobre, à **23:49:29** et **23:50:54**
(heure de Paris), ont été acceptés par Fred avec **high**. Les empreintes
durables correspondent exactement à cette valeur, après reconstitution de
l’historique et de la réflexion conservée. Le précédent envoi à 23:48:35
correspond à **none**. Aucun texte des messages ni jeton n’est copié dans
la [preuve de l’audit](recent-messages-audit.json).

Fred transformait silencieusement `max` et `xhigh` en `high`, et `minimal`
en `none`. Le modèle utilisé est **nvidia/nemotron-3-ultra-550b-a55b:free**,
via OpenRouter. Son [catalogue officiel](https://openrouter.ai/api/v1/models)
annonce une réflexion facultative avec les efforts **medium** et **high**.
Le niveau le plus fort disponible est donc **high**, sans niveau `max`.

L’empreinte prouve la valeur acceptée par Fred. Le corps HTTP original envoyé
au fournisseur n’était pas conservé ; la transmission exacte est vérifiée
séparément avec le runtime natif et un fournisseur HTTP synthétique.

## Correction

Le serveur expose les réglages connus et utilisables de chaque modèle et de
sa route fournisseur : efforts précis, simple activation, ou fonctionnement
automatique sans override. Il ne déduit plus quatre niveaux génériques du seul
fait qu’un modèle puisse réfléchir. Les niveaux incompatibles sont refusés
avant l’admission Hermes, y compris dans le calcul de contexte.

Les clients affichent cette liste et mémorisent leur choix par modèle dans
leurs préférences chiffrées. Ils conservent les valeurs canoniques exactes et
n’envoient aucun niveau si le modèle n’annonce aucun réglage. Le choix du tour
est capturé avant la sauvegarde asynchrone de l’historique. La conversation
vocale Windows suit le même parcours ; le correcteur reste direct sur Qwen.
Les anciens champs de préférence restent compatibles.

Les rafraîchissements de la bibliothèque ne modifient plus le widget modèle
pendant son utilisation : statut, options et niveaux attendent la fin du choix.
Le poll Windows de la conversation vocale pouvait demander ces rafraîchissements
même hors conversation active. Une régression reproduit la mutation, et la
même version sans cette seule garde échoue au contrôle.

`on` est envoyé à Hermes sous forme de `reasoning: {enabled: true}`, sans effort
inventé. `max` reste exact pour un modèle qui l’annonce. `ultra` peut être
conservé comme préférence canonique, mais n’est pas proposé sur les routes
de ce runtime qui le réduisent à `max`. Le profil NVIDIA direct n’annonce
aucun contrôle, car sa version native ne transmet pas d’override de réflexion.

## Vérifications

La [preuve backend](backend-validation.json) consigne **100 tests réussis** :
découverte, contrôle par modèle, transport, isolation, restauration, Qwen
et correcteur. Le pipeline Hermes complet transmet `max` jusqu’au corps HTTP
d’un fournisseur local synthétique. Le parseur API, le profil OpenRouter et le
SDK natifs transmettent exactement les trois modes Nemotron et le mode activé.
Aucune nouvelle inférence cloud ni modification de l’historique de production
n’est utilisée pour ces tests.

La [preuve des clients](client-ui-validation.json) valide les niveaux exacts,
les choix par modèle, les contrôles forcés, les erreurs, les préférences DPAPI
et le menu Windows/Android. Elle distingue les vérifications de réflexion et
du sélecteur faites sur la dernière garde des scénarios vocaux et correcteur
passés juste avant cette garde ciblée. [Régression sans garde](model-widget-baseline.json).

La [popup Android native](android-webview-picker.json) passe neuf contrôles,
dont une modification tardive des capacités pendant un redraw de bibliothèque.
La popup, le défilement, les nœuds et les niveaux restent inchangés jusqu’à
la fermeture du choix.

La [preuve Android](android-release.json) consigne 36 contrôles de l’APK signé,
les préférences chiffrées, 19 refus atomiques et 15 combinaisons transmises
dans le contexte et le chat SSE, soit 30 POST via WireGuard réel. Les ressources
ASR et JNI restent identiques bit à bit à la version 1.0.9.
[Rapport Android](ANDROID.md).

Windows est vérifié avec les sources réellement embarquées, ses 481 fichiers
natifs, son manifeste Ed25519, l’autocontrôle et une fenêtre compilée.
[Build](windows-build-validation.json), [fenêtre](windows-native-window.json).

Les captures [Windows](reasoning-windows.png) et [Android](reasoning-android.png)
utilisent des catalogues synthétiques pour vérifier les différents contrôles
et le retour à la ligne de huit niveaux. Elles ne représentent pas les trois
choix du Nemotron de production.

## Livraison

Windows/serveur **3.5.27** et Android **1.0.10/code 11** sont publiés le 12 octobre.
Les téléchargements authentifiés correspondent aux paquets signés vérifiés.
Le catalogue de production propose exactement les trois choix du Nemotron et
refuse `max` dans une requête de contexte, avant toute inférence. Qwen conserve
son processus chargé ; accès, réglages, partage et sélection de modèles sont
conservés. L’agent et la voix sont prêts. Ces contrôles ne créent aucun message
de production. [Preuve de livraison](delivery-validation.json).
