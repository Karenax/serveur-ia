# Connexions et conversation Windows 3.5.37

L'utilisateur constate des reconnexions WireGuard répétées et des réponses
interrompues également via Cloudflare. Un seul client est ouvert. Le poste qui
exécute les essais n'a pas de client Windows accessible sur ses ports locaux ;
les événements réseau de ce client distant ne sont donc pas disponibles ici.
Le serveur est chargé, Phonon prêt, et les logs Strata montrent plusieurs
calculs annulés avant le premier token. Ils ne suffisent pas à attribuer chaque
coupure historique au tunnel, au réseau physique ou à une interruption vocale.

## Défauts reproduits et corrections

- Le contrôle du catalogue gardait le verrou du bridge pendant toute l'attente
  réseau. Il utilise désormais son propre verrou non bloquant : l'annulation,
  l'audio et les autres requêtes restent possibles pendant ce contrôle.
- Une erreur secondaire invalidait immédiatement toute la connexion. Elle devient
  un avertissement ; trois contrôles consécutifs en échec sont nécessaires pour
  invalider une connexion auparavant fonctionnelle. Les essais sont espacés,
  sans changement d'adresse après un seul échec. Une réponse concurrente plus
  récente prévaut sur un ancien contrôle lent. Un flux réellement tronqué reste
  signalé comme incomplet. Les refus et révocations restent immédiats et un
  contrôle réussi tardivement ne peut pas les effacer.
- Le bridge WireGuard limitait toutes les requêtes au même groupe de quatre
  connexions. Les contrôles et annulations disposent désormais d'un groupe
  distinct, limité à deux connexions. La limite du groupe de données reste quatre.
  La documentation [Go Transport](https://pkg.go.dev/net/http#Transport) confirme
  que les ouvertures attendent lorsqu'une limite `MaxConnsPerHost` est atteinte.
- Le mode conversation raccrochait et annulait la génération dès que l'état
  connecté devenait faux. Il conserve maintenant le microphone et les phrases
  reconnues pendant une coupure ; les nouveaux envois attendent le retour de la
  connexion. Une perte de connexion n'entraîne pas de répétition automatique
  d'une génération partiellement reçue. Les vraies interruptions par l'utilisateur,
  le raccrochage explicite et les révocations restent effectifs.
- Une erreur de synthèse arrêtait aussi la génération du texte et pouvait le
  remplacer par « Réponse interrompue avant la fin de sa première phrase ».
  Elle interrompt maintenant la lecture concernée, affiche l'erreur et conserve
  le texte ainsi que le microphone. L'amputation du texte à la partie entendue
  est réservée à une vraie interruption vocale.
- La passerelle envoie une trame de maintien toutes les cinq secondes pendant
  les attentes silencieuses du modèle local en conversation. La voix fait de
  même pendant une synthèse silencieuse. Ces trames ne deviennent ni du texte
  ni du son et ne réinitialisent pas les limites de calcul/annulation serveur.
  Les [limites Cloudflare](https://developers.cloudflare.com/fundamentals/reference/connection-limits/)
  expliquent l'intérêt de maintenir les flux actifs ; elles ne prouvent pas
  l'origine des coupures courtes rapportées ici.

## Vérifications

`test_connection_resilience.py` vérifie les contrôles concurrents, l'espacement
des reprises, la conservation des modèles après un échec isolé, et la priorité
d'une révocation sur un contrôle tardif. `test_wireguard_resilience.py` utilise
deux vrais moteurs WireGuard avec des clés jetables et un relais UDP local :
quatre flux occupent les connexions de données, puis les contrôles/annulations
passent ; une seconde de perte UDP est récupérée avec un seul démarrage du bridge.
Ce test n'utilise ni les accès ni le serveur de production.

La suite UI ajoute une perte de connexion pendant une réponse, une phrase en
attente envoyée une seule fois au retour du réseau, une erreur de lecture sans
perte du texte ni du microphone, et une révocation qui ferme le microphone.
Les tests HTTP vérifient les trames de maintien avant les en-têtes du modèle et
pendant une synthèse silencieuse, ainsi que les annulations et révocations.
Les tests des mises à jour vérifient que le dossier unique et le retour arrière
introduits en 3.5.36 restent fonctionnels.

Les trames ASR et PCM de l'interface sont simulées. Aucun essai sur le microphone
physique du client, sa connexion WAN ou un smartphone n'est revendiqué. Les
preuves de livraison sont dans `exe-proof.json` et `production.json`.

La vérification finale du binaire passe 40 tests sans exclusion ; les six suites
UI partagées passent et le contrôle UX signale zéro avertissement. Le test Go
des connexions de contrôle passe également. Les 16 tests des transformations
de texte restent valides. Les 20 tests historiques de connexion ont été exécutés :
19 sont passés directement et le cas dont l'attente change avec le nouveau
comportement des erreurs secondaires a ensuite été adapté et revérifié.

## Reproduire et livrer

```powershell
& '.\client-qwen\Build-WireGuard.ps1'
& '.\client-qwen\Build-Client.ps1' -DistributionDirectory "$PWD\toolchain\releases-staging\windows-3.5.37" -SkipManifest
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/2026-10-23-connexions/verify.py
npm --prefix client-qwen test
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/check_sources.py
```

Après vérification, `activate.py` publie la mise à jour signée, reconditionne les
clients personnels et recharge uniquement la console en préservant Qwen, les
clés, les données et les réglages des sauvegardes. Examiner les preuves avant
toute relance d'une activation déjà démarrée. Le client distant doit appliquer
3.5.37 pour bénéficier des correctifs de reconnexion et de conversation.
