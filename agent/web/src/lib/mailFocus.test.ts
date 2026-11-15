import {it,expect} from 'vitest';
import {rankProjects,focusPercent,folderDigits} from './mailFocus';
it('ordonne les candidats connus sans inventer de probabilité pour les autres',()=>{
  const ranked=rankProjects([{id:'a',code:'A',name:'A'},{id:'b',code:'B',name:'B'},{id:'c',code:'C',name:'C'}],{target_project_id:'a',confidence:.3,candidates:[{project_id:'b',score:.9}]});
  expect(ranked.map(p=>p.id)).toEqual(['b','a','c']);
  expect(ranked[2].score).toBeNull();
  expect(focusPercent(.999)).toBe('99.9 %');
  expect(focusPercent(null)).toBe('— %');
  expect(folderDigits('AIRB26LTH0205-A')).toBe('0205');
});
