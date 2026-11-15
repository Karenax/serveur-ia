import type {SessionQuestionProgress} from '../lib/meetingSessions';
import './async-activity.css';

export function MeetingQuestionProgress({status,readError=false,manualAvailable=true}:{status:SessionQuestionProgress|null;readError?:boolean;manualAvailable?:boolean}) {
  if(!status)return null;
  const pending=!readError&&status.state==='pending';
  const manual=manualAvailable?'Vous pouvez poser une question directement.':'Les réponses conservées restent disponibles.';
  const message=readError?'L’état de la réponse automatique reste à vérifier.':
    pending?(status.delayed?`La recherche automatique prend plus de temps. ${manual}`:'Recherche automatique d’une réponse en cours…'):
    status.state==='disabled'?`Réponses automatiques désactivées. ${manual}`:
    status.state==='failed'?`La réponse automatique n’a pas abouti. ${manual}`:
    status.state==='interrupted'?'La recherche automatique a été interrompue. Les réponses conservées restent disponibles.':
    status.state==='obsolete'?'La question a changé ; cette recherche concerne une ancienne version.':
    status.state==='unknown'?`L’état de cette recherche automatique n’est pas confirmé. ${manual}`:null;
  if(!message)return null;
  return <div className="meeting-studio-notice meeting-question-progress" role="status" aria-label="État des réponses automatiques" aria-busy={pending}>
    {pending&&<span className="async-activity-spinner" aria-hidden="true"/>}<span>{message}</span>
  </div>;
}
