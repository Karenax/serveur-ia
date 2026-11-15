import { type ReactNode } from "react";

/** Markdown de conversation rendu en éléments React : aucun HTML généré par l’IA. */
export function ChatMarkdown({ text, references = [], onReference }: {
  text: string;
  references?: string[];
  onReference?: (reference: string) => void;
}) {
  const known = new Set(references);
  const inline = (content: string): ReactNode[] => {
    const pattern = /\*\*[^*\n]+\*\*|__[^_\n]+__|`[^`\n]+`|\[(?:[VP]\d+)(?:\s*,\s*[VP]\d+)*\]|\[[^\]\n]+\]\([^\)\n]+\)|\*[^*\n]+\*/g;
    const nodes: ReactNode[] = [];
    let start = 0;
    for (const match of content.matchAll(pattern)) {
      const index = match.index!;
      if (index > start) nodes.push(content.slice(start, index));
      const token = match[0];
      if (token.startsWith("**") || token.startsWith("__")) {
        nodes.push(<strong key={index}>{inline(token.slice(2, -2))}</strong>);
      } else if (token.startsWith("`")) {
        nodes.push(<code key={index}>{token.slice(1, -1)}</code>);
      } else if (/^\[[VP]\d+/.test(token)) {
        const refs = token.slice(1, -1).split(",").map((r) => r.trim());
        nodes.push(<span key={index} className="chat-inline-citations">{refs.map((ref) =>
          known.has(ref) && onReference
            ? <button key={ref} type="button" className={`chat-reference ${ref.startsWith("V") ? "validated" : "proposed"}`}
                aria-label={`Voir la source ${ref}`} onClick={() => onReference(ref)}>{ref}</button>
            : <span key={ref}>[{ref}]</span>,
        )}</span>);
      } else if (token.startsWith("[")) {
        const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token)!;
        nodes.push(/^https?:\/\//i.test(link[2])
          ? <a key={index} href={link[2]} target="_blank" rel="noopener noreferrer">{link[1]}</a>
          : token);
      } else {
        nodes.push(<em key={index}>{token.slice(1, -1)}</em>);
      }
      start = index + token.length;
    }
    if (start < content.length) nodes.push(content.slice(start));
    return nodes;
  };

  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const listItem = (line: string) => /^(\s*)([-*+]|\d+[.)])\s+(.+)$/.exec(line);
  let cursor = 0;
  const list = (indent: number, ordered: boolean): ReactNode => {
    const items: ReactNode[] = [];
    const key = cursor;
    while (cursor < lines.length) {
      const match = listItem(lines[cursor]);
      if (!match || match[1].length !== indent || /^\d/.test(match[2]) !== ordered) break;
      const itemKey = cursor++;
      const content: ReactNode[] = [<span key="text">{inline(match[3])}</span>];
      while (cursor < lines.length) {
        const child = listItem(lines[cursor]);
        if (child && child[1].length > indent) {
          content.push(list(child[1].length, /^\d/.test(child[2])));
        } else if (!child && lines[cursor].trim() && /^\s+/.test(lines[cursor]) &&
                   lines[cursor].search(/\S/) > indent) {
          content.push(<span key={cursor}> {inline(lines[cursor++].trim())}</span>);
        } else if (!lines[cursor].trim() && listItem(lines[cursor + 1] || "")) {
          cursor++;
        } else break;
      }
      items.push(<li key={itemKey}>{content}</li>);
    }
    return ordered ? <ol key={key}>{items}</ol> : <ul key={key}>{items}</ul>;
  };

  const blocks: ReactNode[] = [];
  while (cursor < lines.length) {
    const key = cursor;
    const line = lines[cursor];
    if (!line.trim()) { cursor++; continue; }
    if (/^\s*```/.test(line)) {
      const code: string[] = [];
      cursor++;
      while (cursor < lines.length && !/^\s*```/.test(lines[cursor])) code.push(lines[cursor++]);
      if (cursor < lines.length) cursor++;
      blocks.push(<pre key={key}><code>{code.join("\n")}</code></pre>);
    } else if (/^#{1,6}\s+/.test(line)) {
      cursor++;
      blocks.push(<h4 key={key}>{inline(line.replace(/^#{1,6}\s+/, ""))}</h4>);
    } else if (listItem(line)) {
      const match = listItem(line)!;
      blocks.push(list(match[1].length, /^\d/.test(match[2])));
    } else if (/^>\s?/.test(line)) {
      const quote: string[] = [];
      while (cursor < lines.length && /^>\s?/.test(lines[cursor])) quote.push(lines[cursor++].replace(/^>\s?/, ""));
      blocks.push(<blockquote key={key}>{inline(quote.join(" "))}</blockquote>);
    } else {
      const paragraph: string[] = [];
      while (cursor < lines.length && lines[cursor].trim() && !listItem(lines[cursor]) &&
             !/^(#{1,6}\s|\s*```|>)/.test(lines[cursor])) paragraph.push(lines[cursor++]);
      blocks.push(<p key={key}>{inline(paragraph.join(" "))}</p>);
    }
  }
  return <div className="chat-markdown">{blocks}</div>;
}
