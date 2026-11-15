import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
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
});
