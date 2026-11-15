import {afterEach,expect,it,vi} from 'vitest';
import {MEETING_WORKSPACE_EVENT,meetingWorkspaceHref,requestMeetingWorkspace} from './meetingWorkspace';
import {parseWorkspaceRoute,workspacePath} from './workspaceNavigation';

afterEach(()=>vi.restoreAllMocks());
it('conserve le projet dans le chemin partagé après rechargement et historique',()=>{
  const href=meetingWorkspaceHref('projet/a?b');
  expect(href).toBe('/app/meetings?project=projet%2Fa%3Fb');
  const url=new URL(href,'http://agent.test');
  const route=parseWorkspaceRoute(url.pathname,url.search);
  expect(route).toEqual({page:'meetings',projectId:'projet/a?b'});
  expect(workspacePath(route)).toBe(href);
  expect(parseWorkspaceRoute('/app/meetings')).toEqual({page:'meetings'});
});
it('laisse le lien normal fonctionner sans récepteur et respecte une prise en charge gardée',()=>{
  expect(requestMeetingWorkspace('p1')).toBe(false);
  const receive=(event:Event)=>{
    expect((event as CustomEvent).detail.projectId).toBe('p1');
    event.preventDefault();
  };
  window.addEventListener(MEETING_WORKSPACE_EVENT,receive);
  try{expect(requestMeetingWorkspace('p1')).toBe(true);}
  finally{window.removeEventListener(MEETING_WORKSPACE_EVENT,receive);}
});
