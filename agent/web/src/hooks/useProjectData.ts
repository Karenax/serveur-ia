import { useEffect, useRef, useState } from 'react';
import { api, type CdcItem, type CdcSource, type Meeting, type ProjectDetail } from '../lib/api';

export function useProjectData(projectId: string, reloadRows: () => Promise<void> | void) {
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [items, setItems] = useState<CdcItem[]>([]);
  const [sources, setSources] = useState<CdcSource[]>([]);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const refresh = async () => {
    const request = ++generation.current;
    try {
      setError("");
      const [project, cdcItems, cdcSources, reviews] = await Promise.all([
        api.detail(projectId), api.cdcItems(projectId), api.cdcSources(projectId), api.meetings(projectId),
      ]);
      if (request !== generation.current) return false;
      const objectRows = (value: unknown) => Array.isArray(value) && value.every(row => row !== null && typeof row === 'object' && !Array.isArray(row));
      if (!project || typeof project !== 'object' || project.id !== projectId ||
          !objectRows(project.tasks) || !objectRows(project.milestones) || !objectRows(project.deliverables) ||
          !objectRows(cdcItems) || !objectRows(cdcSources) || !objectRows(reviews) ||
          project.tasks.some(task => typeof task.id !== 'string' || typeof task.title !== 'string' ||
            typeof task.status !== 'string' || (task.due_date != null && typeof task.due_date !== 'string'))) {
        throw new Error('Réponse du projet invalide. Les données et saisies affichées sont conservées.');
      }
      setDetail(project); setItems(cdcItems); setSources(cdcSources); setMeetings(reviews);
      await reloadRows();
      return true;
    } catch (e: unknown) {
      if (request === generation.current) setError(e instanceof Error ? e.message : String(e));
      return false;
    }
  };
  useEffect(() => {
    setDetail(null); setItems([]); setSources([]); setMeetings([]);
    void refresh();
    return () => {generation.current += 1;};
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);
  return { detail, items, sources, meetings, error, refresh };
}
