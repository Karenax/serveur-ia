# Première version du client Linux — 1er novembre 2026

**Mise à jour :** ce rapport décrit le premier paquet sans vocal. La révision 2
ajoute la dictée et la conversation vocale : voir [VOCAL.md](VOCAL.md) et le
[guide actuel](../../client-linux/README.md). Son archive porte le suffixe `-vocal`.

Cible demandée : Ubuntu/Debian sur PC 64 bits. Paquet construit :
`client-linux/dist/Kiara-linux-amd64-3.5.55.tar.gz` (environ 4,4 Mo).
Le [guide d’installation](../../client-linux/README.md) décrit les prérequis
Ubuntu 24.04+/Debian 13, le premier lancement et les limites.

## Changements

- Sources du chat de bureau, projets/documents, correcteur, historiques et API
  locale conservés ; fenêtre Qt/PySide6 sous Linux.
- Bridge WireGuard compilé en ELF x86_64 avec Go 1.27.3 et modules vérifiés.
  Aucun adaptateur système ni droit administrateur demandé.
- Import borné du profil d’un EXE personnel existant, sans l’exécuter ; stockage
  chiffré Fernet dans XDG, clé dans Secret Service, sans repli en clair.
- Verrouillage POSIX ajouté aux primitives partagées ; mutex Windows conservé.
- Modules vocaux Windows non proposés ; explication visible dans le client Linux.
  Mises à jour manuelles, sans installation d’un EXE Windows.
- Constructeur avec sélection explicite des sources et manifeste SHA-256.
  Aucun accès, modèle, historique ou clé privée dans la distribution.

## Vérifications effectuées depuis Windows

- 104 tests Python du client réussis, dont huit propres à l’adaptation Linux :
  import tronqué/invalide, chiffrement, corruption, clé absente, isolation des
  accès, blocage des mises à jour Windows et des installations vocales, contrôle
  des autorisations sur le vrai serveur HTTP local.
- Test Chromium dédié Linux réussi : réponse en streaming simulée, brouillon
  enregistré, thème système, mises à jour manuelles, avertissement HTTPS conservé,
  aucune requête vocale ni erreur JavaScript. Capture produite sous
  `toolchain/test-results/ui/2026-11-01T18-53-06-111Z-5daf39/linux/chat.png`.
- Suite complète `npm --prefix client-qwen test` réussie : 17 suites partagées
  Windows, Android et Linux, puis le contrôle UX prévu par le projet.
- Contrôle des sources réussi : 489 sources Python, 91 scripts JavaScript et
  94 scripts PowerShell analysés par chacun des deux interpréteurs.
- `npm --prefix client-qwen run ux:check` réussi ; trois avertissements de longueur
  déjà présents dans la console serveur, hors périmètre. Contrôle explicite du
  nouveau script Linux : aucun avertissement.
- Contenu du paquet vérifié : 54 empreintes, architecture ELF x86_64,
  permissions des exécutables et fins de ligne du lanceur. Résultat dans
  [package-validation.json](package-validation.json).

Les journaux des suites sont dans `toolchain/test-results/linux-client-regression.txt`
et `toolchain/test-results/linux-client-ui-regression.txt`.

## Validation restante

Ce poste ne possède pas de Linux exécutable. La fenêtre Qt, le vrai trousseau
Secret Service, les verrous POSIX et les échanges WireGuard sur Linux n’ont pas
été exécutés nativement. Les essais navigateur utilisent des données fictives et
ne constituent pas cette validation. Exécuter `./start.sh --self-test`, puis
essayer les parcours du guide avec un accès de test avant diffusion générale.
La dictée, la conversation vocale, le mot d’appel, Max et la sélection d’une
zone d’écran restent indisponibles dans cette première version.

La production et les clients personnels existants n’ont pas été remplacés.
