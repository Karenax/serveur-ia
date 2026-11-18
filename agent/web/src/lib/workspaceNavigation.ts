import { agentLocation, agentPath } from './agentRoutes';
export const projectTabs = ["pilotage", "cdc", "planification", "atelier", "reviews", "documents", "connaissance"] as const;
export type ProjectTab = typeof projectTabs[number];
export const projectTabLabels: Record<ProjectTab, string> = {
  pilotage: "Vue d’ensemble", cdc: "CDC & BE", planification: "Planning", atelier: "Atelier",
  reviews: "Réunions & revues", documents: "Documents", connaissance: "Informations",
};
export const workspacePages = ["home", "projects", "notes", "mail", "meetings", "activity", "sources", "stats", "preparation", "knowledge", "search", "jobs", "imports", "settings", "create"] as const;
export const projectSections = [
  {slug:"vue-ensemble", tab:"pilotage", label:"Vue d’ensemble"},
  {slug:"pilotage", tab:"planification", label:"Pilotage"},
  {slug:"documents", tab:"documents", label:"Documents"},
  {slug:"reunions", tab:"reviews", label:"Réunions"},
] as const;

export function projectSection(tab: ProjectTab) {
  if (tab === "cdc" || tab === "atelier") return "planification";
  return tab === "connaissance" ? "documents" : tab;
}

export type WorkspacePage = typeof workspacePages[number];
export type WorkspaceRoute = {page: WorkspacePage | "project"; projectId?: string; tab?: ProjectTab};

export function parseWorkspaceRoute(path: string, search = ''): WorkspaceRoute {
  const parts = agentLocation(path).replace(/^\/app\/?/, "").split("/").filter(Boolean);
  const projectList = parts[0] === "projects" || parts[0] === "projets";
  if (projectList && parts[1]) {
    let id: string;
    try { id = decodeURIComponent(parts[1]); } catch { return {page:"projects"}; }
    if (!/^[A-Za-z0-9_-]+$/.test(id)) return {page:"projects"};
    const tab = parts[0] === "projets"
      ? ((projectTabs.includes(parts[3] as ProjectTab) && projectSections.find(section => section.slug === parts[2])?.tab === projectSection(parts[3] as ProjectTab))
        ? parts[3] as ProjectTab : projectSections.find(section => section.slug === parts[2])?.tab ?? "pilotage")
      : (projectTabs.includes(parts[2] as ProjectTab) ? parts[2] as ProjectTab : "pilotage");
    return {page:"project", projectId:id, tab};
  }
  if (projectList) return {page:"projects"};
  const alias = parts[0] === "mails" ? "mail" : parts[0] === "reunions" ? "meetings" : parts[0] === "activite" ? "activity" : undefined;
  const page = alias ?? (workspacePages.includes(parts[0] as WorkspacePage) ? parts[0] as WorkspacePage : "home");
  const projectId=page==='meetings'?new URLSearchParams(search).get('project'):null;
  return {page,...(projectId?{projectId}:{})};
}

export function workspacePath(route: WorkspaceRoute) {
  if (route.page === "project" && route.projectId) {
    const tab = route.tab || "pilotage";
    const section = projectSections.find(item => item.tab === projectSection(tab))!;
    const subview = section.tab === tab ? "" : `/${tab}`;
    return agentPath(`/app/projets/${encodeURIComponent(route.projectId)}/${section.slug}${subview}`);
  }
  return agentPath(`/app/${route.page === "home" ? "" : route.page === "projects" ? "projets" : route.page === "activity" ? "activite" : route.page}${route.page==='meetings'&&route.projectId?`?project=${encodeURIComponent(route.projectId)}`:''}`);
}

export function routeKey(route: WorkspaceRoute) {
  if (route.page === "settings" || route.page === "stats" || route.page === "preparation") return "settings";
  return route.page === "project" ? `project:${route.projectId}` : route.page;
}
