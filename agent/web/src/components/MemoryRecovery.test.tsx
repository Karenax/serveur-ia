import {act,render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {afterEach,describe,it,expect,vi} from 'vitest';
import {MemoryRecovery} from './MemoryRecovery';
import {request} from '../lib/http';
vi.mock('../lib/http',()=>({request:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});
const idle={running:false,total:0,processed:0,indexed:0,failed:0,remaining_failed:3,error:null};
describe('Memory recovery',()=>{
  it('starts retry without blocking and displays progress',async()=>{
    vi.mocked(request).mockResolvedValueOnce(idle).mockResolvedValueOnce({...idle,running:true,total:3,processed:1,indexed:1});
    render(<MemoryRecovery/>);
    await screen.findByText('3 indexation(s) en échec');
    fireEvent.click(screen.getByRole('button',{name:'Reprendre les indexations en échec'}));
    await screen.findByText(/1 \/ 3 traitées/);
    expect(screen.getByRole('button',{name:'Reprise en cours…'}).hasAttribute('disabled')).toBe(true);
    expect(request).toHaveBeenCalledWith('/v1/settings/memory/recovery',{method:'POST'},10000);
  });
  it('does not offer retry when no failures remain',async()=>{
    vi.mocked(request).mockResolvedValue({...idle,remaining_failed:0});
    render(<MemoryRecovery/>);
    await screen.findByText('Aucune indexation en échec');
    expect(screen.getByText('Options de reprise').closest('details')).toHaveProperty('open',false);
    fireEvent.click(screen.getByText('Options de reprise'));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Reprendre les indexations en échec'}).hasAttribute('disabled')).toBe(true));
  });
  it('keeps progress and errors visible while options are closed',async()=>{
    vi.mocked(request).mockResolvedValue({...idle,running:true,total:3,processed:1,indexed:1,error:'Serveur de recherche indisponible'});
    render(<MemoryRecovery/>);
    expect(await screen.findByRole('alert')).toHaveProperty('textContent','Serveur de recherche indisponible');
    expect(screen.getByText('Options de reprise').closest('details')).toHaveProperty('open',false);
    expect(screen.getByRole('progressbar',{name:'Avancement de la reprise mémoire'})).toHaveProperty('value',1);
    expect(screen.getByRole('button',{name:'Reprise en cours…'}).hasAttribute('disabled')).toBe(true);
  });
  it('suspend les lectures hors de la vue et reprend sans envoyer de commande',async()=>{
    vi.useFakeTimers();let hidden=false;vi.spyOn(document,'hidden','get').mockImplementation(()=>hidden);
    vi.mocked(request).mockResolvedValue(idle);
    const view=render(<MemoryRecovery active/>);
    try{
      await act(async()=>{});expect(request).toHaveBeenCalledTimes(1);
      view.rerender(<MemoryRecovery active={false}/>);
      await act(async()=>{await vi.advanceTimersByTimeAsync(9000);});expect(request).toHaveBeenCalledTimes(1);
      view.rerender(<MemoryRecovery active/>);await act(async()=>{});expect(request).toHaveBeenCalledTimes(2);
      hidden=true;act(()=>document.dispatchEvent(new Event('visibilitychange')));
      await act(async()=>{await vi.advanceTimersByTimeAsync(9000);});expect(request).toHaveBeenCalledTimes(2);
      hidden=false;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});expect(request).toHaveBeenCalledTimes(3);
      expect(vi.mocked(request).mock.calls.every(call=>call[1]?.method!=='POST')).toBe(true);
    }finally{view.unmount();vi.useRealTimers();vi.restoreAllMocks();}
  });
  it('ne remplace pas une reprise demandée par une ancienne lecture retardée',async()=>{
    vi.useFakeTimers();let finishRead!:(value:typeof idle)=>void,finishPost!:(value:typeof idle)=>void;
    const running={...idle,running:true,total:3,processed:1,indexed:1};
    vi.mocked(request).mockResolvedValueOnce(idle).mockReturnValueOnce(new Promise(resolve=>{finishRead=resolve;}))
      .mockReturnValueOnce(new Promise(resolve=>{finishPost=resolve;})).mockResolvedValue(running);
    const view=render(<MemoryRecovery/>);
    try{
      await act(async()=>{});await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
      fireEvent.click(screen.getByRole('button',{name:'Reprendre les indexations en échec'}));
      await act(async()=>{finishPost(running);});
      await act(async()=>{finishRead(idle);});
      expect(screen.getByText(/1 \/ 3 traitées/)).toBeTruthy();
      expect(screen.getByRole('button',{name:'Reprise en cours…'})).toBeTruthy();
    }finally{view.unmount();vi.useRealTimers();}
  });
  it('laisse aboutir une reprise déjà demandée pendant que la rubrique est masquée',async()=>{
    vi.useFakeTimers();let finishPost!:(value:typeof idle)=>void;
    const running={...idle,running:true,total:3,processed:1,indexed:1};
    vi.mocked(request).mockResolvedValueOnce(idle).mockReturnValueOnce(new Promise(resolve=>{finishPost=resolve;})).mockResolvedValue(running);
    const view=render(<MemoryRecovery active/>);
    try{
      await act(async()=>{});
      fireEvent.click(screen.getByRole('button',{name:'Reprendre les indexations en échec'}));
      view.rerender(<MemoryRecovery active={false}/>);
      await act(async()=>{await vi.advanceTimersByTimeAsync(9000);});
      expect(request).toHaveBeenCalledTimes(2);
      await act(async()=>{finishPost(running);});
      expect(screen.getByText(/1 \/ 3 traitées/)).toBeTruthy();
      view.rerender(<MemoryRecovery active/>);await act(async()=>{});
      expect(screen.getByText(/1 \/ 3 traitées/)).toBeTruthy();
      expect(vi.mocked(request).mock.calls.filter(call=>call[1]?.method==='POST')).toHaveLength(1);
    }finally{view.unmount();vi.useRealTimers();}
  });
});
