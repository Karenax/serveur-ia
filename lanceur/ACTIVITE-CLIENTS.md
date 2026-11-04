# Activité des clients

La rubrique **Clients & accès → Activité des clients** présente les connexions
et le temps connecté estimé, par jour sur 28 jours ou par semaine sur 8 semaines.
Le sélecteur **Graphique** permet de tracer l’une ou l’autre mesure. Le tableau
détaille les résultats par accès personnel et conserve le nom des accès supprimés.
Les données du graphique sont aussi disponibles dans un tableau dépliable.

Une connexion commence au premier contact authentifié d’un accès, puis après une
interruption de plus de 5 minutes. Les requêtes de surveillance d’une application
ouverte font partie de cette présence. La durée additionne les intervalles entre
contacts d’une même session ; elle n’ajoute pas 5 minutes à sa fin et ne compte pas
les longues absences. Ce n’est ni un temps de travail humain, ni une mesure du temps
de calcul GPU. Plusieurs copies du même accès ne sont pas distinguées.

Le suivi est indépendant du transport : les clients Windows, Android et Linux
qui passent par la passerelle Kiara sont comptés, en WireGuard comme en HTTPS.
L’API réseau locale sans authentification, les appels directs au moteur et les
visites de la console serveur ne sont pas des connexions de clients personnels.
Les accès refusés ne sont pas comptés.

Le fuseau est Europe/Paris si la base de fuseaux du runtime est disponible ; à
défaut, le fuseau local du serveur est utilisé et indiqué dans le panneau.
Les durées sont réparties entre les jours aux passages de minuit. Les semaines
commencent le lundi ; la semaine en cours est partielle. La présence récente
correspond à un contact depuis moins de 2 minutes, pas à la preuve d’un socket
toujours ouvert.

## Conservation et fonctionnement

Le fichier `activite-clients.json` est conservé sous `KIARA_DATA_DIR` (par défaut
dans `lanceur`), exclu de Git. Il contient seulement les identifiants d’accès, des
dates, compteurs et durées. Aucun contenu de conversation, adresse IP, token ou
audio n’est enregistré. Les agrégats sont purgés au-delà de 180 jours lors des
enregistrements ou de la consultation. Une erreur de lecture conserve le fichier
original et désactive les nouveaux enregistrements de ce suivi ; une erreur de
disque est signalée dans le panneau sans interdire les connexions des clients.

Les écritures sont atomiques et regroupées à 30 secondes au plus fréquent.
Un arrêt brutal peut perdre jusqu’à environ 30 secondes d’observations. Le fichier
est indépendant des configurations d’accès et n’est pas ajouté aux archives de
sauvegarde existantes ; sa conservation séparée permet de garder ces statistiques.

L’historique commence à l’activation de cette version. Les anciens fichiers de
dernier contact ne permettent pas de reconstruire des sessions passées ; aucune
activité antérieure n’est inventée. Aucune mise à jour des clients n’est nécessaire.

## Mise en service et portée

Les changements Python nécessitent le redémarrage de la **console serveur** ;
recharger seulement le navigateur ne charge pas le nouveau suivi côté serveur.
Prévoir cette opération hors conversation en cours, la passerelle clients étant
hébergée par le même processus. Le modèle Qwen n’a pas besoin d’être reconstruit.
Le panneau propose un message de reprise tant que la nouvelle API est absente.

L’API `/api/clients/activity?period=day` (ou `week`) reste sur l’interface locale
et exige le jeton de la console. Le graphique s’actualise toutes les 15 secondes
quand la rubrique est visible ; **Actualiser** permet une lecture immédiate.

Conformément à la demande de ne pas lancer de tests, aucun scénario fonctionnel,
aucune capture Playwright et aucune modification de production pour essai ne sont
réalisés. Les contrôles de syntaxe et le contrôle statique UX sont distincts d’une
validation visuelle, d’une validation fonctionnelle ou d’une conformité WCAG.
