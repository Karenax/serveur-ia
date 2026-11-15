"""Long fictional engineering dossiers; score actual evidence, not document identity."""
from __future__ import annotations

from functools import lru_cache
import re


def corpus():
    # Gold answers are fixed here before any model call. IDs are absent from queries.
    facts = [
        ('A01', 'La note de conception indice B autorisait le support S235 peint sur la passerelle extérieure. Cette recommandation est archivée et ne constitue plus une instruction de fabrication.', 'ancienne version'),
        ('A02', 'La décision finale indice D impose un support inox 316L sur la passerelle exposée aux embruns. Le S235 peint est explicitement interdit à cet emplacement, même après retouche de peinture.', 'version applicable'),
        ('A03', 'Le couloir humide utilise la rampe LUMA alimentée en 24 V continu avec enveloppe IP65. Cette rampe ordinaire ne possède aucune certification pour une atmosphère explosive.', 'éclairage humide'),
        ('A04', 'Dans le local de mélange SOLV-X, seul le luminaire certifié EX42 est accepté. Le classement ATEX de cette zone exclut la rampe LUMA, malgré son enveloppe IP65.', 'exclusion ATEX'),
        ('A05', 'La pompe HYDRA délivre 240 litres par minute d’eau propre à six bars. Son moteur est prévu pour le transfert hydraulique et aucun usage pneumatique n’est autorisé.', 'eau'),
        ('A06', 'Le compresseur AERO délivre 240 litres par minute d’air à huit bars. La purge hebdomadaire des condensats est obligatoire ; cette machine ne transfère pas d’eau.', 'air'),
        ('A07', 'Le dossier commercial initial annonçait une livraison le 12 décembre 2026 pour la commande ZETA-731. Cette date a été remplacée par un accord signé et ne doit plus être communiquée.', 'date ancienne'),
        ('A08', 'L’accord signé du 3 octobre fixe la livraison de ZETA-731 au 19 janvier 2027. Il remplace l’annonce du 12 décembre ; la revue technique reste programmée le 12 décembre 2026.', 'date contractuelle'),
        ('A09', 'La vente de l’affaire ZETA représente 160000 euros HT. Le coût prévisionnel total est de 120000 euros HT, comprenant les achats, l’atelier et les essais. Ces montants sont validés au comité.', 'marge'),
        ('A10', 'L’enveloppe de 40000 euros concerne uniquement les achats de l’affaire OMEGA. Elle ne représente ni une marge ni un prix de vente ; ces deux données restent à définir.', 'budget distinct'),
        ('A11', 'L’avenant AV17 ajoute deux sondes et une plus-value de 2400 euros HT. Le délai augmente de quatre jours ouvrés. La mise en fabrication nécessite un accord écrit du client.', 'avenant condition'),
        ('A12', 'Le courriel du client refuse de lancer AV17 avant validation de son budget. Aucun accord écrit n’est enregistré au 7 octobre ; les travaux supplémentaires restent donc suspendus.', 'avenant statut'),
        ('A13', 'Le plan ELEC-K9 indice F déplace le bornier X18 et remplace l’indice E pour la fabrication. Les impressions de l’indice E doivent être retirées du poste avant câblage.', 'plan courant'),
        ('A14', 'Le compte rendu de l’indice E plaçait X18 à gauche du coffret. Cette implantation historique est conservée pour traçabilité ; elle n’est plus applicable après diffusion de l’indice F.', 'plan obsolète'),
        ('A15', 'La réception usine FAT du coffret K9 contrôle les entrées et sorties automate, les arrêts d’urgence et le repérage des bornes. Elle précède l’emballage et l’expédition.', 'FAT'),
        ('A16', 'La réception sur site SAT vérifie les échanges avec le réseau du client et le fonctionnement de la ligne assemblée. Le SAT intervient après installation et ne remplace pas le FAT atelier.', 'SAT'),
        ('A17', 'Le certificat matière du lot M74 identifie un inox 316L conforme à la commande de la passerelle. La traçabilité exige de joindre ce certificat au dossier de livraison du support.', 'certificat'),
        ('A18', 'Le lot M75 est un acier carbone S235 réservé aux supports intérieurs secs. Son certificat ne peut pas justifier la conformité matière de la passerelle extérieure exposée aux embruns.', 'certificat exclu'),
        ('A19', 'L’essai d’étanchéité du circuit HYDRA utilise de l’eau à neuf bars pendant trente minutes. La pression de service demeure six bars ; il est interdit de confondre ces deux valeurs.', 'pression essai'),
        ('A20', 'Le relevé de réception hydraulique constate une fuite sur le raccord R8 après dix minutes à neuf bars. La réserve reste ouverte et interdit l’expédition du circuit HYDRA.', 'réserve'),
        ('A21', 'La procédure qualité exige un nouvel essai d’étanchéité concluant et la signature du responsable qualité pour lever la réserve du raccord R8. Une photographie de la réparation seule ne suffit pas.', 'levée réserve'),
        ('A22', 'Le procès verbal provisoire du 9 octobre mentionne un remplacement du joint R8 mais aucun nouvel essai signé. La réserve hydraulique demeure ouverte malgré la réparation mécanique réalisée.', 'réparation insuffisante'),
        ('A23', 'Le protocole de sauvegarde impose une copie quotidienne de la configuration automate sur le serveur de l’atelier. La restauration mensuelle doit être vérifiée avec un équipement de test.', 'sauvegarde'),
        ('A24', 'Les comptes de maintenance sont individuels et expirent après trente jours. Le compte partagé SERVICE est désactivé et ne doit pas servir à la réception sur site.', 'accès'),
    ]
    tasks = [
        ('version', 'Quel matériau est finalement autorisé pour la passerelle extérieure exposée aux embruns ?', ['A02'], 'Inox 316L ; S235 interdit.'),
        ('exclusion', 'Peut-on utiliser LUMA dans le local de solvants grâce à son IP65 ?', ['A04', 'A03'], 'Non : IP65 ne vaut pas certification ATEX ; EX42 requis.'),
        ('fluide', 'Quelle machine fournit de l’air à 240 litres par minute et comment l’entretenir ?', ['A06'], 'AERO, huit bars, purge hebdomadaire.'),
        ('fluide', 'Quel équipement transfère de l’eau à six bars sans usage pneumatique ?', ['A05'], 'HYDRA.'),
        ('version', 'Quelle date de livraison doit-on désormais annoncer pour ZETA-731 ?', ['A08'], '19 janvier 2027.'),
        ('dates', 'Does the technical review date also correspond to the current delivery date of ZETA-731?', ['A08'], 'No: review 12 December 2026; delivery 19 January 2027.'),
        ('calcul', 'Calcule la marge brute de ZETA en euros et en pourcentage du prix de vente.', ['A09'], '40000 euros et 25 %.'),
        ('exclusion', 'Les 40000 euros de OMEGA correspondent-ils à une marge brute validée ?', ['A10'], 'Non, plafond achats ; marge non définie.'),
        ('preuves multiples', 'Peut-on lancer les deux sondes supplémentaires et quel serait leur impact financier et délai ?', ['A11', 'A12'], 'Non sans accord ; +2400 euros HT et quatre jours ouvrés.'),
        ('version', 'Quel indice du plan ELEC-K9 faut-il distribuer aux câbleurs pour déplacer X18 ?', ['A13'], 'Indice F, retire indice E.'),
        ('séquence', 'Quels contrôles faut-il faire avant expédition du coffret et lesquels seulement après installation ?', ['A15', 'A16'], 'FAT E/S, arrêts, repérage ; SAT réseau et ligne.'),
        ('preuves multiples', 'Quel certificat démontre la matière exigée pour la passerelle marine ?', ['A02', 'A17'], 'M74 inox316L ; exigence indice D.'),
        ('exclusion', 'Le certificat M75 permet-il de valider la passerelle extérieure ?', ['A18', 'A02'], 'Non, M75 S235 intérieur ; 316L requis.'),
        ('valeurs proches', 'Quelle pression et quelle durée utiliser pour éprouver le circuit d’eau, distinctes du service ?', ['A19'], 'Neuf bars trente minutes ; service six bars.'),
        ('preuves multiples', 'Peut-on expédier HYDRA après le remplacement du joint R8 ?', ['A20', 'A21', 'A22'], 'Non, réserve ouverte ; nouvel essai concluant signé manquant.'),
        ('preuves multiples', 'What evidence is still missing to release the hydraulic leak reservation after repair?', ['A21', 'A22'], 'Successful repeated leak test and quality signature.'),
        ('procédure', 'Comment assurer que la configuration automate sauvegardée est effectivement récupérable ?', ['A23'], 'Copie quotidienne et restauration mensuelle sur équipement test.'),
        ('exclusion', 'Peut-on se connecter avec SERVICE lors de la réception sur site ?', ['A24'], 'Non, comptes individuels expirant après trente jours.'),
        ('version', 'Pourquoi ne faut-il pas reprendre la recommandation S235 de la première note ?', ['A01', 'A02'], 'Indice B archivé, décision D inox316L.'),
        ('dates', 'Pourquoi le commercial ne doit-il plus promettre une livraison en décembre ?', ['A07', 'A08'], 'Ancienne date remplacée par accord signé janvier.'),
        ('preuves multiples', 'Le dossier de contrôle du support livré doit réunir quelle exigence et quel justificatif ?', ['A02', 'A17'], 'Décision D316L et certificatM74.'),
        ('séquence', 'Are workshop acceptance checks enough to validate the installed production line?', ['A15', 'A16'], 'No: SAT network and assembled line also required.'),
        ('exclusion', 'Une photo du joint neuf suffit-elle à clore la réserve qualité ?', ['A21'], 'Non, essai concluant et signature.'),
        ('version', 'Est-ce que le déplacement X18 décrit dans le compte rendu ancien reste applicable ?', ['A14', 'A13'], 'Non, utiliser indice F.'),
    ]
    titles = ['Conception et revue des exigences', 'Décisions et échanges contractuels', 'Fabrication et approvisionnement',
              'Contrôles et réception', 'Maintenance et exploitation', 'Historique et traitement des réserves']
    documents, passages = [], []
    for d, title in enumerate(titles):
        rows = []
        for section in range(8):
            # Mix topics across dossiers, place gold near beginning/middle/end.
            for p in range(2):
                n = d * 16 + section * 2 + p
                text = (f'Au chapitre {section + 1} du dossier {title}, le suivi du sous-ensemble U{n:03} '
                        f'porte sur la préparation des opérations et le contrôle des interfaces. Le responsable consigne '
                        f'une durée prévisionnelle de {15 + n % 17} heures et une enveloppe de {310 + n * 13} euros '
                        f'pour les outillages de ce sous-ensemble. La liste de contrôle prévoit le relevé des dimensions, '
                        f'la vérification du repérage et une revue des connexions avant fermeture. Le document de travail '
                        f'W{n:03} conserve les observations atelier. Toute anomalie doit être inscrite au registre avec '
                        f'une photographie, une date et le nom de l’opérateur. La simple présence d’un composant en stock '
                        f'ne constitue pas une autorisation de montage. Le coordinateur vérifie la disponibilité des '
                        f'pièces et organise la reprise avant la prochaine réunion. Ces mesures concernent exclusivement '
                        f'U{n:03}, sans modifier les décisions signées ni lever les réserves d’autres équipements.')
                words = text.split()
                for part, offset in enumerate(range(0, len(words), 50)):
                    rows.append((f'N{n * 3 + part:03}', ' '.join(words[offset:offset + 50])))
            if section in (0, 2, 5, 7):
                f = facts[d + (0, 6, 12, 18)[(0, 2, 5, 7).index(section)]]
                rows.append((f[0], f[1]))
        doc_id = f'D{d + 1}'
        texts = []
        for ident, body in rows:
            # Marker is an audit identifier; never present in a query.
            text = f'[PREUVE:{ident}] {body}'
            texts.append(text)
            passages.append({'id': ident, 'doc_id': doc_id, 'text': text})
        documents.append({'id': doc_id, 'title': title, 'text': '\n\n'.join(texts)})
    queries = [{'category': category, 'query': query, 'expected': expected, 'answer': answer}
               for category, query, expected, answer in tasks]
    return documents, passages, queries


def evidence_ids(text):
    return re.findall(r'\[PREUVE:(A\d{2}|N\d{3})\]', text)


@lru_cache(maxsize=1)
def proof_texts():
    return {p['id']: ' '.join(p['text'].split()) for p in corpus()[1]}


def complete_ids(text):
    normalized = ' '.join(text.split())
    lookup = proof_texts()
    return {ident for ident in evidence_ids(text) if lookup.get(ident, '\0') in normalized}


def evaluate(query, texts, seconds):
    ids = list(dict.fromkeys(ident for text in texts for ident in evidence_ids(text)))
    expected = set(query['expected'])
    first_ids = complete_ids(texts[0]) if texts else set()
    at_5 = complete_ids('\n\n'.join(texts[:5]))
    at_10 = complete_ids('\n\n'.join(texts[:10]))
    context = '\n\n'.join(texts[:10])
    in_context = complete_ids(context)
    return {**query, 'retrieved': ids, 'texts': texts, 'seconds': seconds,
            'first_correct': bool(expected & first_ids),
            'any_at_5': bool(expected & at_5),
            'all_at_5': expected <= at_5, 'all_at_10': expected <= at_10,
            'coverage_at_5': len(expected & at_5) / len(expected),
            'all_at_context': expected <= in_context,
            'coverage_at_context': len(expected & in_context) / len(expected),
            'context_chars': len(context), 'complete_at_5': sorted(at_5), 'complete_all': sorted(at_10)}


def metrics(rows):
    return {key: sum(row[key] for row in rows) / len(rows)
            for key in ('first_correct', 'any_at_5', 'all_at_5', 'all_at_10', 'coverage_at_5',
                        'all_at_context', 'coverage_at_context', 'context_chars', 'seconds')}
