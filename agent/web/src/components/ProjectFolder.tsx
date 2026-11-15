/** The final numeric group is the dossier number, after any year in the code. */
export function ProjectFolder({code}: {code: string}) {
  const number = code.match(/\d+/g)?.pop()?.slice(0, 4) || "";
  return <svg className="workspace-project-folder" viewBox="0 0 48 38" aria-hidden="true" focusable="false">
    <path d="M3 8a4 4 0 0 1 4-4h11l5 5h18a4 4 0 0 1 4 4v19a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3z"/>
    <text x="24" y="26" textAnchor="middle">{number}</text>
  </svg>;
}
