import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {AsyncDownloadLink,downloadFilename} from './AsyncDownloadLink';
import {getActivitySnapshot} from '../lib/asyncActivity';

const deferred=<T,>()=>{let resolve!:(value:T)=>void;const promise=new Promise<T>(done=>{resolve=done;});return {promise,resolve};};
const create=vi.fn(),revoke=vi.fn(),fetchFile=vi.fn();
const preventNavigation=(event:Event)=>event.preventDefault();
const response=(blob:()=>Promise<Blob>,disposition='attachment; filename="source.pdf"')=>({ok:true,headers:new Headers({'content-disposition':disposition}),blob}) as Response;
beforeEach(()=>{
  create.mockReset().mockReturnValue('blob:agent-file');revoke.mockReset();fetchFile.mockReset();
  vi.stubGlobal('URL',class extends URL{static createObjectURL=create;static revokeObjectURL=revoke;});
  vi.stubGlobal('fetch',fetchFile);vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
  document.addEventListener('click',preventNavigation);
});
afterEach(()=>{cleanup();expect(getActivitySnapshot()).toBeNull();document.removeEventListener('click',preventNavigation);vi.restoreAllMocks();vi.unstubAllGlobals();vi.useRealTimers();});

it('attend le Blob complet, bloque le doubleclic et conserve les octets reçus pour l’enregistrement manuel',async()=>{
  const body=deferred<Blob>();fetchFile.mockResolvedValue(response(()=>body.promise,"attachment; filename*=UTF-8''Compte%20rendu%20%C3%A9t%C3%A9.zip"));
  const view=render(<AsyncDownloadLink href="/api/v1/meeting-sessions/s1/export">Exporter la séance</AsyncDownloadLink>);
  const link=screen.getByRole('link',{name:'Exporter la séance'});fireEvent.click(link);fireEvent.click(link);
  expect(fetchFile).toHaveBeenCalledOnce();expect(link.getAttribute('href')).toBe('/api/v1/meeting-sessions/s1/export');
  expect(fetchFile.mock.calls[0][1]).toMatchObject({method:'GET',credentials:'same-origin',signal:expect.any(AbortSignal)});
  expect(getActivitySnapshot()).not.toBeNull();expect(create).not.toHaveBeenCalled();
  await act(async()=>{body.resolve(new Blob(['Archive fictive']));});
  const manual=await screen.findByRole('link',{name:'Enregistrer le fichier préparé'});
  expect(manual.getAttribute('href')).toBe('blob:agent-file');expect(manual.getAttribute('download')).toBe('Compte rendu été.zip');
  expect(getActivitySnapshot()).toBeNull();expect(revoke).not.toHaveBeenCalled();
  view.unmount();expect(revoke).toHaveBeenCalledWith('blob:agent-file');
});

it('ferme l’attente, affiche le refus HTTP et permet une nouvelle préparation sans prétendre à une sauvegarde OS',async()=>{
  fetchFile.mockResolvedValueOnce({ok:false,status:404,json:async()=>({detail:'Original indisponible'})});
  const view=render(<AsyncDownloadLink href="/v1/sources/s1/raw" filename="original.eml">Original</AsyncDownloadLink>);
  fireEvent.click(screen.getByRole('link',{name:'Original'}));
  expect((await screen.findByRole('alert')).textContent).toBe('Original indisponible');expect(getActivitySnapshot()).toBeNull();
  fetchFile.mockResolvedValueOnce(response(async()=>new Blob(['Mail fictif']),''));
  vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{throw new Error('Téléchargement automatique bloqué');});
  fireEvent.click(screen.getByRole('link',{name:'Original'}));
  const manual=await screen.findByRole('link',{name:'Enregistrer le fichier préparé'});expect(manual.getAttribute('download')).toBe('original.eml');
  expect(screen.queryByRole('alert')).toBeNull();expect(screen.getByText(/Octets reçus, prêt à enregistrer/)).toBeTruthy();
  view.rerender(<AsyncDownloadLink href="/v1/sources/s2/raw">Autre original</AsyncDownloadLink>);
  expect(revoke).toHaveBeenCalledWith('blob:agent-file');expect(screen.queryByRole('link',{name:'Enregistrer le fichier préparé'})).toBeNull();
});

it('annule sur changement de source et à la fermeture, sans téléchargement ni indicateur tardif',async()=>{
  const pending=deferred<Response>();fetchFile.mockReturnValueOnce(pending.promise);
  const view=render(<AsyncDownloadLink href="/v1/sources/s1/raw">Original</AsyncDownloadLink>);
  fireEvent.click(screen.getByRole('link',{name:'Original'}));const firstSignal=fetchFile.mock.calls[0][1].signal as AbortSignal;
  view.rerender(<AsyncDownloadLink href="/v1/sources/s2/raw">Autre original</AsyncDownloadLink>);
  expect(firstSignal.aborted).toBe(true);expect(getActivitySnapshot()).toBeNull();
  await act(async()=>{pending.resolve(response(async()=>new Blob(['Ancienne source'])));});expect(create).not.toHaveBeenCalled();
  const body=deferred<Blob>();fetchFile.mockResolvedValueOnce(response(()=>body.promise));
  fireEvent.click(screen.getByRole('link',{name:'Autre original'}));const signal=fetchFile.mock.calls[1][1].signal as AbortSignal;
  await act(async()=>{await Promise.resolve();});view.unmount();expect(signal.aborted).toBe(true);expect(getActivitySnapshot()).toBeNull();
  await act(async()=>{body.resolve(new Blob(['Source quittée']));});expect(create).not.toHaveBeenCalled();
});

it('borne la préparation à six minutes même si le transport ignore l’annulation',async()=>{
  vi.useFakeTimers();const pending=deferred<Response>();fetchFile.mockReturnValue(pending.promise);
  render(<AsyncDownloadLink href="/v1/sources/s1/raw">Original</AsyncDownloadLink>);fireEvent.click(screen.getByRole('link',{name:'Original'}));
  const signal=fetchFile.mock.calls[0][1].signal as AbortSignal;
  await act(async()=>{await vi.advanceTimersByTimeAsync(360_000);});
  expect(signal.aborted).toBe(true);expect(screen.getByRole('alert').textContent).toMatch(/a expiré/);expect(getActivitySnapshot()).toBeNull();
  await act(async()=>{pending.resolve(response(async()=>new Blob(['Trop tard'])));});expect(create).not.toHaveBeenCalled();
});

it('préserve les clics modifiés et liens externes, et garde les noms UTF8 ou ordinaires',async()=>{
  const view=render(<AsyncDownloadLink href="/v1/sources/s1/raw">Original</AsyncDownloadLink>);
  for(const option of [{ctrlKey:true},{metaKey:true},{shiftKey:true},{altKey:true},{button:1}])fireEvent.click(screen.getByRole('link',{name:'Original'}),option);
  view.rerender(<AsyncDownloadLink href="https://example.com/original">Source externe</AsyncDownloadLink>);fireEvent.click(screen.getByRole('link',{name:'Source externe'}));
  await waitFor(()=>expect(fetchFile).not.toHaveBeenCalled());expect(getActivitySnapshot()).toBeNull();
  expect(downloadFilename("attachment; filename*=UTF-8''rapport%20%C3%A9t%C3%A9.pdf",'repli.bin')).toBe('rapport été.pdf');
  expect(downloadFilename('attachment; filename="notice technique.docx"','repli.bin')).toBe('notice technique.docx');
  expect(downloadFilename("attachment; filename*=UTF-8''%ZZ; filename=notice.pdf",'repli.bin')).toBe('notice.pdf');
  expect(downloadFilename(null,'dossier/original.eml')).toBe('original.eml');
});
