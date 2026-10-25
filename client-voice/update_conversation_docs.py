"""Align current status after voice rollout; preserve historical validation reports."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
changes={
 'README.md':[
 ('Versions actuelles : serveur/Windows **3.5.20**','Versions actuelles : serveur/Windows **3.5.21**'),
 ('Le lot 7 est partiellement livré avec la dictée locale ; lecture orale et dialogue continu restent planifiés, ainsi que le tableau de bord complet du lot 5 et les lots 9 et 10.','Le lot 7 comprend la dictée Windows/Android et la conversation vocale Windows ; la conversation Android reste différée. Le tableau de bord complet du lot 5 et les lots 9 et 10 restent planifiés.')],
 'CONTEXTE-PROJET.md':[
 ('La refonte du tableau de bord du lot 5, la synthèse vocale du lot 7, les outils du lot 9 et l’intégration complète du lot 10 restent planifiés.','La refonte du tableau de bord du lot 5, les outils du lot 9 et l’intégration complète du lot 10 restent planifiés. La conversation du lot 7 est livrée dans Windows ; son extension Android est différée.'),
 ('Le lot 7 est partiellement livré : ASR intégré, TTS et dialogue continu planifiés.','Cette étude précède la livraison suivante : ASR Windows/Android et conversation Windows avec TTS CPU désormais livrés.'),
 ('Le lot 7 reste partiellement réalisé : la dictée ASR est achevée, TTS et dialogue vocal continu restent planifiés.','Cette livraison de dictée a ensuite été complétée par la conversation Windows 3.5.21 ; Android conserve le mode manuel.')],
 'client-voice/README.md':[
 ('Les réponses de Kiara restent écrites ; la synthèse vocale et les échanges vocaux continus restent à développer.','Ce mode Dictée conserve les réponses écrites. Windows ajoute un mode distinct de [conversation vocale](CONVERSATION-WINDOWS.md), avec envoi automatique et lecture des réponses.')],
 'PLAN-GLOBAL-SERVEUR-FRED.md':[
 ('Date : 10 octobre 2026.','Date : 11 octobre 2026.'),
 ('La refonte du tableau de bord du lot 5 et les lots 7, 9 et 10 restent planifiés.','La refonte du tableau de bord du lot 5 et les lots 9 et 10 restent planifiés ; le lot 7 comprend désormais la dictée Windows/Android et la conversation Windows.'),
 ('| Voix | Dictée locale Whisper Small intégrée aux clients Windows et Android ; audio traité sur l’appareil | Synthèse des réponses et dialogue vocal continu ; mesure sur téléphones physiques |','| Voix | Dictée locale Small Windows/Android ; conversation Windows avec Zipformer/Silero/Smart Turn local et Pocket TTS CPU serveur | Conversation Android différée ; mesures acoustiques humaines et téléphones physiques |'),
 ('le tableau de bord complet et la synthèse vocale restent planifiés ; la dictée locale est livrée.','le tableau de bord complet reste planifié ; la dictée locale et la conversation Windows sont livrées.'),
 ('Statut : **dictée locale ASR livrée le 11 octobre 2026 ; lecture et conversation vocale continue encore planifiées**.','Statut : **dictée locale Windows/Android et conversation Windows livrées le 11 octobre 2026 ; conversation Android différée**.'),
 ('Le plan initial de réception audio serveur ci-dessous concerne uniquement un éventuel repli futur ; il n’est plus requis pour l’ASR locale choisie. La synthèse des réponses reste à implanter après sélection d’un moteur.','Windows 3.5.21 utilise Zipformer FR progressif, Silero et Smart Turn localement ; Pocket TTS 3.3.0 français/Estelle sur CPU serveur, lecture progressive et interruption de la demande courante. [Guide](client-voice/CONVERSATION-WINDOWS.md), [preuves](preuves/conversation-windows-20261011/VALIDATION.md). Les projets, droits, sauvegardes et mémoire EG2 du chat existant sont conservés. Le microphone reste en mémoire dans Windows ; aucune API de réception audio n’est requise. Le plan initial ci-dessous reste une référence pour une éventuelle extension mobile ou un repli serveur, sans déclarer le lot 7 complet sur Android.')]
}
for name, replacements in changes.items():
    path=ROOT/name;text=path.read_text(encoding='utf-8')
    for old,new in replacements:
        if old not in text:
            if new in text:continue
            raise ValueError('Missing expected text: '+name+' '+old[:60])
        text=text.replace(old,new)
    path.write_text(text,encoding='utf-8')
print('Voice documentation aligned')
