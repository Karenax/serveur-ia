import {afterEach,beforeEach,expect,it,vi} from 'vitest';

beforeEach(()=>{localStorage.clear();});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();vi.resetModules();});

it('rejoue la même commande après une coupure et un reçu encore absent',async()=>{
  const payloads:unknown[]=[];
  vi.stubGlobal('fetch',vi.fn(async (url:string,init?:RequestInit)=>{
    if(url==='/api/v1/session')return new Response(JSON.stringify({token:'fictif'}));
    if(url.endsWith('/commands/original'))return new Response(JSON.stringify({detail:'Commande introuvable dans cette séance'}),{status:404});
    if(url.endsWith('/finalize')){
      payloads.push(JSON.parse(String(init?.body)));
      if(payloads.length===1)throw new TypeError('Coupure réseau');
      return new Response(JSON.stringify({id:'sid',state:'completed'}));
    }
    throw new Error(`Appel inattendu ${url}`);
  }));
  const {meetingSessions}=await import('./meetingSessions');
  const original={command_id:'original',expected_revision:4};
  await expect(meetingSessions.command('sid','finalize',original)).rejects.toThrow('Coupure réseau');
  expect(JSON.parse(localStorage.getItem('agent.meeting-command.v1.sid.finalize')!)).toEqual(original);
  await expect(meetingSessions.command('sid','finalize',{command_id:'nouveau',expected_revision:5})).resolves.toMatchObject({state:'completed'});
  expect(payloads).toEqual([original,original]);
  expect(localStorage.getItem('agent.meeting-command.v1.sid.finalize')).toBeNull();
});

it('prépare une nouvelle commande après rejet explicite de révision et absence confirmée du reçu',async()=>{
  const payloads:unknown[]=[];
  vi.stubGlobal('fetch',vi.fn(async (url:string,init?:RequestInit)=>{
    if(url==='/api/v1/session')return new Response(JSON.stringify({token:'fictif'}));
    if(url.endsWith('/commands/original'))return new Response(JSON.stringify({detail:'Commande introuvable dans cette séance'}),{status:404});
    if(url.endsWith('/finalize')){
      payloads.push(JSON.parse(String(init?.body)));
      if(payloads.length===1)return new Response(JSON.stringify({detail:'La séance a changé ; conserver la saisie et recharger.'}),{status:409});
      return new Response(JSON.stringify({id:'sid',state:'completed'}));
    }
    throw new Error(`Appel inattendu ${url}`);
  }));
  const {meetingSessions}=await import('./meetingSessions');
  const original={command_id:'original',expected_revision:4},nouveau={command_id:'nouveau',expected_revision:5};
  await expect(meetingSessions.command('sid','finalize',original)).rejects.toThrow('La séance a changé');
  expect(localStorage.getItem('agent.meeting-command.v1.sid.finalize')).toBeNull();
  await meetingSessions.command('sid','finalize',nouveau);
  expect(payloads).toEqual([original,nouveau]);
});
