# Récupération séparée des clés de signature

Les archives du serveur contiennent déjà la graine Ed25519 utilisée pour signer les mises à jour Windows. La clé Android est conservée séparément dans `toolchain/android-signing/fred-client.p12`. Son fichier `password.dpapi` dépend du compte Windows : copier uniquement ces deux fichiers ne garantit pas une récupération sur une autre machine.

L’outil `recovery_signing.py` prépare un paquet **portable chiffré `.fredkeys`** contenant la clé Android existante, son mot de passe et, sur demande, la graine Windows. Il vérifie le certificat, l’alias `fred-client`, la correspondance entre clé et certificat, le manifeste et le chiffrement avant publication. Il ne crée ni ne remplace de clé de signature.

Depuis la racine du projet, avec la phrase privée préparée pour les sauvegardes :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' '.\lanceur\recovery_signing.py' export `
  --phrase-file 'D:\Serveur IA\lanceur\sauvegardes\phrase-recuperation.txt' `
  --output 'D:\Serveur IA\lanceur\sauvegardes\signatures-fred.fredkeys' `
  --windows-home 'D:\Serveur IA\lanceur'
```

La clé Android vient par défaut de `toolchain/android-signing/`. Pour une autre installation, préciser `--android-dir CHEMIN`. Omettre `--windows-home` pour exporter uniquement Android. Le fichier de sortie doit avoir un chemin absolu ; un fichier existant n’est jamais écrasé.

Vérification indépendante :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' '.\lanceur\recovery_signing.py' verify `
  --phrase-file 'D:\Serveur IA\lanceur\sauvegardes\phrase-recuperation.txt' `
  --file 'D:\Serveur IA\lanceur\sauvegardes\signatures-fred.fredkeys'
```

La sortie contient uniquement les chemins chiffrés, tailles, empreintes SHA-256 et clés **publiques**. Aucun mot de passe ni clé privée n’est affiché ou ajouté au catalogue de sauvegardes. Les limites sont de 4 Mio pour le PKCS12, 12 Mio pour le paquet chiffré et 128 Kio pour chaque entrée DPAPI.

Conserver une copie du paquet sur un support indépendant et la phrase de récupération séparément. Ce paquet couvre les signatures des clients ; il **ne se restaure pas dans la console comme une sauvegarde du serveur**. L’outil fournit export et vérification. Une remise en place des clés doit être faite dans un dossier privé sur la machine cible, après vérification des empreintes et reprotection du mot de passe Android avec le compte Windows cible ; aucune importation automatique ni écrasement de clés n’est exécuté par cet outil.

Tests : `python -m unittest test_recovery_signing -v` depuis `lanceur/`. Les essais créent leurs propres clés temporaires, y compris un vrai fichier PowerShell `ConvertFrom-SecureString`, et couvrent récupération, corruption, phrase incorrecte, limites, publication atomique, absence d’écrasement et confidentialité des sorties.
