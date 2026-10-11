# Android 1.0.10 — validation du 12 octobre 2026

L’APK 1.0.10 (code 11) est compilée, signée, validée et publiée. Les téléchargements authentifiés et les accès conservés sont vérifiés dans la [preuve de livraison](delivery-validation.json).

- SHA-256 : `35a475887eac577461be85b13b6d1e6be5cc66d4a828a7dfdb65c47e7f9cc267`.
- Taille : 18 903 316 octets.
- Certificat inchangé : `40216ff897090b49b21e3cda66169b9fb7070e42dd2b8cb9ebe0f2c441997048` ; signatures v2/v3 et alignement 16 Ko vérifiés.

La sauvegarde Android accepte exactement les valeurs canoniques `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `ultra`, `on`. La préférence par modèle conserve notamment `max` après un changement de modèle et une réouverture. La liste affichée dépend des capacités annoncées : niveau réglable, activation/désactivation ou mode automatique sans override.

Les vérifications exécutées sur la Release signée et l’émulateur x86_64 sont consignées dans [android-release.json](android-release.json) :

- 36 contrôles de l’artefact, dont versions, certificat, assets communs, absence de profils personnels, signature et intégrité.
- Sauvegarde chiffrée des neuf valeurs et des choix par modèle ; limites de 512 modèles et 512 caractères ; 19 requêtes invalides refusées sans écriture.
- 15 combinaisons de raisonnement annoncées transmises exactement dans le contexte et le chat SSE par WireGuard authentifié, soit 30 POST ; deux niveaux non annoncés refusés sans déconnecter le client.
- Six groupes de contrôles du catalogue, du choix du modèle, de l’historique et de l’indisponibilité ; trois actions du correcteur direct ; contrôles natifs de la politique de mise à jour.
- Neuf contrôles de la vraie popup WebView : défilement et sélection, polling différé, réponse en vol, rafraîchissement tardif de la bibliothèque conservant le statut et les modes de réflexion. Les assets de cette QA sont identiques à ceux de la Release signée.
- Compilation finale Release/debug réussie. Le lint et les 13 tests de distribution ont été exécutés avant la dernière garde HTML du menu ; le code Java, les ressources natives et la distribution sont inchangés.

Les 23 ressources natives et ASR sont identiques octet pour octet à l’APK publiée 1.0.9. Le processus Qwen et son état chargé ont été vérifiés inchangés. Les trois fixtures isolées ont été arrêtées, leurs douze exports synthétiques supprimés et les quatre paquets d’instrumentation retirés. La démonstration locale et le port CDP ont été fermés. Aucun compte réel ni fichier de configuration de production n’a été modifié par ces tests.

Les appels des modèles externes utilisent une API synthétique isolée. L’inférence externe, le matériel ARM64, le parcours HTTPS authentifié et la reconnaissance acoustique ne sont pas remesurés ici.
