import type { PortfolioRow } from "./api";

export type MailProject = {id:string; code:string; name:string};
const folded = (code:string) => code.trim().toUpperCase();

/** Keep ERP projects selectable before their first knowledge-engine attachment. */
export function mailProjects(portfolio:PortfolioRow[], brain:MailProject[]):MailProject[] {
  const targets:MailProject[] = [];
  const represented = new Set<string>();
  for (const project of portfolio) {
    const matches = project.code.trim() ? brain.filter(p=>folded(p.code)===folded(project.code)) : [];
    const id = project.brain_project_id || (matches.length===1 ? matches[0].id : `erp:${project.id}`);
    if (represented.has(id)) continue;
    represented.add(id);
    targets.push({id,code:project.code,name:project.title});
  }
  for (const project of brain) if (!represented.has(project.id)) targets.push(project);
  return targets;
}
