# Progression du chargement dans la console serveur

L’indicateur apparaît au-dessus des onglets pendant le chargement, puis devient
une confirmation compacte lorsque le modèle est prêt. Il distingue la lecture
des fichiers, la préparation des GPU, la copie des experts en RAM et la validation.

Pendant la copie RAM, la barre utilise les Go réellement annoncés par Strata,
avec le nombre de couches comme solution de repli si le volume total n’apparaît
plus dans le journal. Le pourcentage concerne cette étape, pas une estimation
du chargement complet. Le temps écoulé reste affiché. La progression est mise
à jour par blocs, à la fréquence des annonces du moteur ; aucun pourcentage ni
délai restant n’est inventé entre ces annonces. Les étapes sans compteur ont une
barre indéterminée ; une erreur interrompt l’animation et affiche sa cause.

Le code utilise `/api/state` et les journaux déjà fournis par la console.
Les trois ressources statiques modifiées sont servies immédiatement : recharger
la page suffit, sans redémarrer la console, le modèle ou Hermes.

Validation : `node lanceur/web/tests/model_loading_ui.cjs` et vérification de
syntaxe JavaScript. Le test utilise les vrais fichiers de l’interface et des
états de chargement simulés dans le navigateur, à partir du format des journaux
réels. Navigation HTTP en lecture seule, aucun lancement de modèle. Vérification
du pourcentage, des étapes, de la validation, des erreurs, de l’état prêt/arrêté,
de l’accessibilité et du mode mouvement réduit, à 1440 et 390 pixels.

Preuves : `validation.json`, `chargement-desktop.png`, `chargement-mobile.png`.
Cette intervention n’envoie aucune commande de lancement ou d’arrêt aux services.
