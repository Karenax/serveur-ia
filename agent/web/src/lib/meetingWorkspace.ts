import { agentPath } from './agentRoutes';
export const MEETING_WORKSPACE_EVENT='agent-open-meetings-workspace';
export const meetingWorkspaceHref=(projectId:string)=>agentPath(`/app/meetings?project=${encodeURIComponent(projectId)}`);
export function requestMeetingWorkspace(projectId:string){
  return !window.dispatchEvent(new CustomEvent(MEETING_WORKSPACE_EVENT,{detail:{projectId},cancelable:true}));
}
