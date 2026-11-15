export type RankedProject = {id:string;code:string;name:string;score:number|null};
export function rankProjects(projects:{id:string;code:string;name:string}[],entry?:{target_project_id:string|null;confidence:number;candidates?:{project_id:string;score:number}[]}) {
  const scores=new Map<string,number>();
  for(const candidate of entry?.candidates||[])if(Number.isFinite(candidate.score))scores.set(candidate.project_id,Math.max(0,Math.min(1,candidate.score)));
  if(entry?.target_project_id)scores.set(entry.target_project_id,Math.max(scores.get(entry.target_project_id)||0,entry.confidence));
  return projects.map(project=>({...project,score:scores.get(project.id)??null})).sort((a,b)=>(b.score??-1)-(a.score??-1)||a.code.localeCompare(b.code));
}
export const focusPercent=(score:number|null|undefined)=>score==null?"— %":`${score===1?100:Math.min(99.9,Math.round(score*1000)/10)} %`;
export const folderDigits=(code:string)=>code.match(/LTH(\d{4})/i)?.[1]||code.match(/\d{4}(?!.*\d{4})/)?.[0]||"";
