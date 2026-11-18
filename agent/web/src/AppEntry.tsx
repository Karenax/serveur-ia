import {Suspense, useCallback, useEffect, useRef, useState} from 'react';
import {agentLocation} from './lib/agentRoutes';
import {api, type PortfolioRow} from './lib/api';
import {retryableLazy} from './lib/retryableLazy';
import {WorkspaceShell, type ProjectWorkspaceProps, type ProjectCreateProps, type MailPanelProps} from './components/WorkspaceShell';
import {LoadingState} from './components/Ui';
import './styles.css';
import './project-workspace.css';
import './project-cdc-analysis.css';
import './cdc-review.css';
import './minipilot.css';
import './workspace-shell.css';

// All four destinations use the same module. Once its alternate address has
// recovered, new views must reuse it instead of the browser-cached failed URL.
let recoveredMain = false;
const loadMain = ():Promise<typeof import('./App')> => recoveredMain
  ? import('./App?kiara-retry=1') as unknown as Promise<typeof import('./App')>
  : import('./App');
const retryMain = async ():Promise<typeof import('./App')> => {
  const module = await import('./App?kiara-retry=1') as unknown as typeof import('./App');
  recoveredMain = true;
  return module;
};
const ProjectView = retryableLazy(
  () => loadMain().then(module => ({default:module.ProjectWindow})),
  () => retryMain().then(module => ({default:module.ProjectWindow})));
const MailView = retryableLazy(
  () => loadMain().then(module => ({default:module.MailApp})),
  () => retryMain().then(module => ({default:module.MailApp})));
const CreateView = retryableLazy(
  () => loadMain().then(module => ({default:module.ScanImport})),
  () => retryMain().then(module => ({default:module.ScanImport})));
const SageView = retryableLazy(
  () => loadMain().then(module => ({default:module.SagePanel})),
  () => retryMain().then(module => ({default:module.SagePanel})));

function ProjectPanel(props: ProjectWorkspaceProps) {return <Suspense fallback={<LoadingState label="Chargement du projet"/>}><ProjectView {...props}/></Suspense>;}
function MailPanel(props: MailPanelProps) {return <Suspense fallback={<LoadingState label="Chargement des mails"/>}><MailView {...props}/></Suspense>;}
function CreatePanel(props: ProjectCreateProps) {return <Suspense fallback={<LoadingState label="Chargement de la création"/>}><CreateView {...props}/></Suspense>;}
function ImportsPanel() {return <Suspense fallback={<LoadingState label="Chargement des imports"/>}><SageView/></Suspense>;}

function validPortfolio(value: unknown): value is PortfolioRow[] {
  if (!Array.isArray(value)) return false;
  const ids = new Set<string>();
  const textFields = ['status','client_name','jalon_en_cours','jalon_echeance','taches','correction_label','remaining_mode','brain_project_id','brain_code'];
  const numberFields = ['avancement','raf','en_retard','corrections','initial_hours','consumed_hours','overrun_hours','unconfirmed','open_points'];
  return value.every(row => {
    if (!row || typeof row !== 'object' || Array.isArray(row) ||
        typeof row.id !== 'string' || !row.id || ids.has(row.id) ||
        typeof row.code !== 'string' || typeof row.title !== 'string') return false;
    ids.add(row.id);
    return textFields.every(key => row[key] == null || typeof row[key] === 'string') &&
      numberFields.every(key => row[key] == null || (typeof row[key] === 'number' && Number.isFinite(row[key])));
  });
}

export function App() {
  const [rows, setRows] = useState<PortfolioRow[] | null>(null);
  const [error, setError] = useState("");
  const loadGeneration = useRef(0);
  const [canCreateProject, setCanCreateProject] = useState(false);
  useEffect(() => {
    let active = true;
    const refreshPermissions = () => {
      void api.session().then(({operator}) => {
        if (active) setCanCreateProject(operator.role !== 'reader' && operator.project_ids === null);
      }).catch(() => { if (active) setCanCreateProject(false); });
    };
    refreshPermissions();
    window.addEventListener('focus', refreshPermissions);
    return () => { active = false; window.removeEventListener('focus', refreshPermissions); };
  }, []);


  const load = useCallback(async (quiet = false) => {
    const generation=++loadGeneration.current;
    try {
      setError("");
      const result=await (quiet === true ? api.portfolio(true) : api.portfolio());
      if(generation===loadGeneration.current){
        if(!validPortfolio(result))throw new Error('Réponse du portefeuille invalide. Les projets déjà affichés sont conservés.');
        setRows(result);
      }
    } catch (e: any) {
      if(generation===loadGeneration.current)setError(String(e.message || e));
    }
  }, []);
  useEffect(() => {
    load();
    const refreshVisible = () => {if(!document.hidden)void load(true);};
    const timer = window.setInterval(() => {
      if (/^\/app\/?$|^\/app\/(projects|projets|mail)\/?$/.test(agentLocation(window.location.pathname)))refreshVisible();
    }, 10_000);
    window.addEventListener("focus",refreshVisible);
    document.addEventListener("visibilitychange",refreshVisible);
    return()=>{loadGeneration.current++;window.clearInterval(timer);window.removeEventListener("focus",refreshVisible);document.removeEventListener("visibilitychange",refreshVisible);};
  }, [load]);

  return <WorkspaceShell canCreateProject={canCreateProject} rows={rows ?? []} portfolioLoading={!rows && !error} portfolioUnavailable={!rows && !!error} reload={load} error={error} ProjectPanel={ProjectPanel}
    MailPanel={MailPanel} CreatePanel={CreatePanel} SagePanel={ImportsPanel} />;
}
