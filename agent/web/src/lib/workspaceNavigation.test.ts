import {describe, expect, it} from 'vitest';
import {parseWorkspaceRoute} from './workspaceNavigation';

describe('Liens directs vers les projets', () => {
  it('conserve le portefeuille et les signets existants', () => {
    expect(parseWorkspaceRoute('/agent/app/projects')).toEqual({page:'projects'});
    expect(parseWorkspaceRoute('/app/projects/p-1/pilotage')).toEqual({page:'project', projectId:'p-1', tab:'pilotage'});
    expect(parseWorkspaceRoute('/app/projects/p-1/cdc')).toEqual({page:'project', projectId:'p-1', tab:'cdc'});
  });

  it.each([
    ['vue-ensemble', 'pilotage'],
    ['pilotage', 'planification'],
    ['documents', 'documents'],
    ['reunions', 'reviews'],
  ])('ouvre %s dans la vue existante %s', (section, tab) => {
    expect(parseWorkspaceRoute('/agent/app/projets/p%2D1/' + section)).toEqual({page:'project', projectId:'p-1', tab});
  });

  it('ramène un identifiant invalide vers le portefeuille', () => {
    expect(parseWorkspaceRoute('/app/projets/%')).toEqual({page:'projects'});
    expect(parseWorkspaceRoute('/app/projets')).toEqual({page:'projects'});
  });
});
