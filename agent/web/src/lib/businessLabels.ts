export const kindLabels: Record<string, string> = {
  function: 'Fonction', constraint: 'Contrainte', requirement: 'Exigence', data: 'Donnée',
  interface: 'Interface', open_point: 'Point ouvert', fact: 'Fait', action: 'Action',
  risk: 'Risque', decision: 'Décision', milestone: 'Échéance', summary: 'Compte rendu',
};
export const kindLabel = (value: string) => kindLabels[value.toLowerCase()] || value;
