# Agent — liaison Thunderbird

MailExtension locale pour Thunderbird 153+, intégrée au projet Agent.

- Import RFC822 avec pièces jointes vers le serveur Agent :8001.
- Choix de dossiers, synchronisation par lots et reprise toutes les 5 minutes.
- Création de brouillons et ouverture de réponses dans Thunderbird.
- Pas d’envoi automatique ; l’utilisateur envoie depuis Thunderbird.

Depuis la racine du dépôt :

```powershell
python scripts/install_thunderbird.py --install
```

Fermer puis rouvrir Thunderbird. Le script fabrique un XPI appairé dans
`storage/thunderbird/`, hors Git ; ne pas diffuser ce paquet contenant la clé
locale. Le XPI est aussi installable depuis le gestionnaire des extensions.

Dans Agent → Mails → Thunderbird, vérifier « Connecté à Agent », choisir les
dossiers ou préparer un brouillon. Le clic sur le bouton de barre d’outils
Thunderbird demande une synchronisation des dossiers déjà sélectionnés.

Architecture, API, installation et tests : [docs/21_THUNDERBIRD_BRIDGE.md](../../docs/21_THUNDERBIRD_BRIDGE.md).
