from deployer import ROOT, OUT, read

assert read(OUT / 'production.json')['version'] == '0.1.45.3'
p = ROOT / 'CONTEXTE-PROJET.md'
s = p.read_text(encoding='utf-8-sig')
s = s.replace('**La production est remise sur 0.1.43.1**, modèle chargé et calcul réel vérifié, configurations et console conservées, port de test fermé. Aucune migration de production ni mise à jour de pilote. Le moteur nouveau reste isolé dans le dossier de recherche ; les limites de validation et l’exigence de pilote déclarée par son manifeste sont documentées dans le rapport.',
              'Après ces tests, la production avait été remise sur 0.1.43.1. **À la demande suivante de l’utilisateur, le moteur 0.1.45.3 est maintenant actif et enregistré par défaut**, avec chargement automatique et reprise activés. Le serveur Python 0.1.43.1 corrigé, les poids et l’encodeur P2200 sont conservés. Voir [la mise en service et sa preuve](maintenance/2026-10-19-strata-0.1.45.3/README.md). Les limites de validation et l’exigence de pilote déclarée par le manifeste restent documentées dans le rapport ; le pilote est inchangé.')
s = s.replace('**Dernière activation :** [redémarrage Strata', '**Activation des correctifs du 16 octobre :** [redémarrage Strata', 1)
s = s.replace('Flash-Next IQ4_XS utilise Strata officiel **0.1.43.1** dans `dependances/strata-0.1.43.1`,',
              'Flash-Next IQ4_XS utilise le moteur Strata officiel **0.1.45.3** dans `dependances/strata-0.1.45.3/engine-cuda12`, avec le serveur Python 0.1.43.1 corrigé conservé dans `dependances/strata-0.1.43.1/source`,')
s = s.replace('Voir [la mise en service](maintenance/2026-10-13-strata-0.1.43.1/README.md) et `production.json` ; sauvegarde précédente dans `avant/`, ancien moteur `strata-build-p100` conservé.',
              'Voir [la mise en service](maintenance/2026-10-19-strata-0.1.45.3/README.md) et son `production.json` ; sauvegarde précédente dans `avant/`, moteurs 0.1.43.1 et `strata-build-p100` conservés.')
s = s.replace('- [Strata 0.1.43.1 en production](maintenance/2026-10-13-strata-0.1.43.1/README.md).',
              '- [Strata 0.1.45.3 en production](maintenance/2026-10-19-strata-0.1.45.3/README.md).')
p.write_text(s, encoding='utf-8')
p = ROOT / 'dependances/README.md'
s = p.read_text(encoding='utf-8-sig')
s = s.replace('# Moteurs tiers\n', '# Moteurs tiers\n\nDepuis le 19 octobre 2026, le moteur actif et enregistré par défaut est **Strata 0.1.45.3**, dans `strata-0.1.45.3/engine-cuda12/`, issu du paquet officiel Strata 0.2.0-beta. Les DLL CUDA sont colocalisées avec le moteur. Le serveur Python corrigé, le tokenizer, le profil experts et l’encodeur P2200 restent sous `strata-0.1.43.1/` ; ce dossier est toujours indispensable. Voir [activation, empreinte, preuve et retour arrière](../maintenance/2026-10-19-strata-0.1.45.3/README.md).\n', 1)
s = s.replace('Depuis le 13 octobre 2026, le moteur de production Flash-Next est', 'Le 13 octobre 2026, le moteur de production Flash-Next est devenu')
s = s.replace('Pour celle-ci, suivre [le guide de mise en service](../maintenance/2026-10-13-strata-0.1.43.1/README.md)', 'Pour celle-ci, suivre [le guide de mise en service](../maintenance/2026-10-19-strata-0.1.45.3/README.md)')
s = s.replace('La vérification du contexte du 13 octobre confirme que le processus actif exécute ce binaire.', 'La preuve actuelle décrit le chemin et l’empreinte du processus réellement actif.')
p.write_text(s, encoding='utf-8')
p = ROOT / 'RECONSTRUIRE-FRED.md'
s = p.read_text(encoding='utf-8-sig').replace('**0.1.43.1**, avec sa source serveur, sous `dependances/strata-0.1.43.1` : suivre\n   [sa configuration de production](maintenance/2026-10-13-strata-0.1.43.1/README.md).',
    '**0.1.45.3**, sous `dependances/strata-0.1.45.3/engine-cuda12`, avec le serveur\n   Python corrigé conservé sous `dependances/strata-0.1.43.1/source` : suivre\n   [sa configuration de production](maintenance/2026-10-19-strata-0.1.45.3/README.md).')
p.write_text(s, encoding='utf-8')
print('Contexte, dépendances et guide de reconstruction actualisés.')
