/* Icônes originales du bureau MiniPilot, style macOS redessiné maison.
   - Glyph : icônes de trait (24x24, stroke courant), pour barre de menus,
     barre latérale Finder, barre d'outils.
   - AppIcon : tuiles applicatives (48x48, dégradés + glyphe simple),
     pour dock, Launchpad et fichiers du bureau. */

export function Glyph({ d, size = 18, sw = 1.7 }: { d: string | string[]; size?: number; sw?: number }) {
  const paths = Array.isArray(d) ? d : [d];
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={sw}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths.map((p, i) =>
        p.startsWith("<") ? (
          <g key={i} dangerouslySetInnerHTML={{ __html: p }} />
        ) : (
          <path key={i} d={p} />
        ),
      )}
    </svg>
  );
}

const GRID4 = [
  '<rect x="3" y="3" width="7" height="7" rx="1"/>',
  '<rect x="14" y="3" width="7" height="7" rx="1"/>',
  '<rect x="3" y="14" width="7" height="7" rx="1"/>',
  '<rect x="14" y="14" width="7" height="7" rx="1"/>',
];

export const P = {
  grid: GRID4,
  list: ["M4 6h16M4 12h16M4 18h16"],
  folder: ["M3 6V4h7l2 3h9v13H3z"],
  note: ["M6 3h12v18H6zM9 8h6M9 12h6M9 16h4"],
  download: ["M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"],
  trash: ["M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7"],
  chevL: ["m14 5-7 7 7 7"],
  chevR: ["m9 5 7 7-7 7"],
  search: ["<circle cx=\"10\" cy=\"10\" r=\"6.5\"/>", "m15 15 5 5"],
  openExt: ["M14 3h7v7M21 3 10 14M10 3H3v18h18v-7"],
  exportUp: ["M12 15V2m-4 4 4-4 4 4M5 10v11h14V10"],
  tiling: GRID4,
  sync: ["M20 10a8 8 0 1 0-1 8M20 3v7h-7"],
  ctrlCenter: [
    '<rect x="2" y="4" width="20" height="6" rx="3"/>',
    '<rect x="2" y="14" width="20" height="6" rx="3"/>',
    '<circle cx="7" cy="7" r="2" fill="currentColor"/>',
    '<circle cx="17" cy="17" r="2" fill="currentColor"/>',
  ],
  cloud: ["M5 18a5 5 0 0 1 0-10 7 7 0 0 1 13-1 5.5 5.5 0 0 1 1 11z"],
  clock: ['<circle cx="12" cy="12" r="9"/>', "M12 7v5l3 2"],
  alert: [
    "M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
    "M12 9v4M12 17h.01",
  ],
  check: ["M20 6 9 17l-5-5"],
  // Menus d'options / filtres : icônes filaires discrètes (voir <Icon>).
  more: [
    '<circle cx="5" cy="12" r="1.6" fill="currentColor" stroke="none"/>',
    '<circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none"/>',
    '<circle cx="19" cy="12" r="1.6" fill="currentColor" stroke="none"/>',
  ],
  sliders: [
    "M3 7h18M3 17h18",
    '<circle cx="9" cy="7" r="2.2" fill="var(--surface, #fff)"/>',
    '<circle cx="15" cy="17" r="2.2" fill="var(--surface, #fff)"/>',
  ],
  filter: ["M3 5h18l-7 8v6l-4 2v-8z"],
};

/** Icône filaire discrète référencée par son nom (menus d'options et de filtres). */
export function Icon({ name, size = 16 }: { name: keyof typeof P; size?: number }) {
  return <Glyph d={P[name]} size={size} />;
}

/* ── Tuiles applicatives ─────────────────────────────────────────── */

function Tile({
  size = 50,
  defs,
  body,
}: {
  size?: number;
  defs: React.ReactNode;
  body: React.ReactNode;
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <defs>{defs}</defs>
      <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#tile-shadow)" />
      {body}
    </svg>
  );
}

function Shadow() {
  return (
    <linearGradient id="tile-shadow" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stopColor="#000" stopOpacity="0.25" />
      <stop offset="1" stopColor="#000" stopOpacity="0" />
    </linearGradient>
  );
}

type IconProps = { size?: number };

export const AppIcon = {
  launchpad: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-launch" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#8e8e93" />
            <stop offset="1" stopColor="#48484a" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-launch)" />
          {[10, 21].map((y) =>
            [10, 21, 32].map((x) => (
              <rect key={`${x}-${y}`} x={x} y={y} width="7" height="7" rx="1.6" fill="#fff" opacity="0.92" />
            )),
          )}
        </>
      }
    />
  ),
  finder: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-find-a" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#5ac8fa" />
            <stop offset="1" stopColor="#0a84ff" />
          </linearGradient>
          <linearGradient id="ti-find-b" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0a84ff" />
            <stop offset="1" stopColor="#0040dd" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-find-a)" />
          <path d="M24 1h12a10 10 0 0 1 10 10v26a10 10 0 0 1-10 10H24z" fill="url(#ti-find-b)" />
          <rect x="23" y="6" width="2" height="36" fill="#0a3069" opacity="0.55" />
          <rect x="12" y="15" width="3.4" height="9" rx="1.7" fill="#062a63" />
          <rect x="32.6" y="15" width="3.4" height="9" rx="1.7" fill="#062a63" />
          <path d="M13 31c3 3 17 3 22-1" stroke="#062a63" strokeWidth="2.4" fill="none" strokeLinecap="round" />
        </>
      }
    />
  ),
  folder: ({ size = 55 }: IconProps) => (
    <svg width={size} height={(size * 48) / 55} viewBox="0 0 55 48" aria-hidden="true">
      <defs>
        <linearGradient id="ti-folder" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7cc4ff" />
          <stop offset="1" stopColor="#0a84ff" />
        </linearGradient>
      </defs>
      <path d="M2 8a4 4 0 0 1 4-4h12l5 7h26a4 4 0 0 1 4 4v25a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4z" fill="url(#ti-folder)" />
      <path d="M2 15h51v25a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4z" fill="#fff" opacity="0.22" />
    </svg>
  ),
  disk: ({ size = 54 }: IconProps) => (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <defs>
        <linearGradient id="ti-disk" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e5e5ea" />
          <stop offset="1" stopColor="#8e8e93" />
        </linearGradient>
      </defs>
      <rect x="4" y="6" width="40" height="36" rx="5" fill="url(#ti-disk)" stroke="#636366" />
      <rect x="10" y="12" width="28" height="16" rx="2" fill="#48484a" />
      <rect x="10" y="32" width="28" height="4" rx="2" fill="#636366" />
    </svg>
  ),
  compass: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-comp" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#4a4a4e" />
            <stop offset="1" stopColor="#1c1c1e" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-comp)" />
          <circle cx="24" cy="24" r="15" fill="#f2f2f7" />
          <path d="M30 18 26 26l-8 4 4-8z" fill="#ff3b30" />
          <path d="M30 18l-4 8-4-4z" fill="#fff" opacity="0.85" />
          <circle cx="24" cy="24" r="2.4" fill="#1c1c1e" />
        </>
      }
    />
  ),
  calendar: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="#f2f2f7" />
          <path d="M1 12a10 10 0 0 1 10-10h26a10 10 0 0 1 10 10v4H1z" fill="#ff3b30" />
          <rect x="11" y="6" width="4" height="10" rx="2" fill="#8e8e93" />
          <rect x="33" y="6" width="4" height="10" rx="2" fill="#8e8e93" />
          <text x="24" y="38" textAnchor="middle" fontSize="20" fontWeight="700" fill="#1c1c1e" fontFamily="inherit">
            17
          </text>
        </>
      }
    />
  ),
  docs: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-docs" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#5ac8fa" />
            <stop offset="1" stopColor="#0a64ff" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-docs)" />
          <rect x="12" y="10" width="24" height="6" rx="3" fill="#fff" opacity="0.95" />
          <rect x="12" y="19" width="24" height="6" rx="3" fill="#fff" opacity="0.7" />
          <rect x="12" y="28" width="16" height="6" rx="3" fill="#fff" opacity="0.5" />
        </>
      }
    />
  ),
  lab: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-lab" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#bf5af2" />
            <stop offset="1" stopColor="#5e5ce6" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-lab)" />
          <path d="M20 8h8v12l8 14H12z" fill="none" stroke="#fff" strokeWidth="3" strokeLinejoin="round" />
          <path d="M17 30h14l-2.5 4h-9z" fill="#fff" opacity="0.9" />
        </>
      }
    />
  ),
  chart: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-chart" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#30b0c7" />
            <stop offset="1" stopColor="#0a84ff" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-chart)" />
          <rect x="11" y="24" width="6" height="12" rx="2" fill="#fff" />
          <rect x="21" y="17" width="6" height="19" rx="2" fill="#fff" opacity="0.85" />
          <rect x="31" y="11" width="6" height="25" rx="2" fill="#fff" opacity="0.7" />
        </>
      }
    />
  ),
  flag: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-flag" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#ff9f0a" />
            <stop offset="1" stopColor="#ff6b00" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-flag)" />
          <rect x="13" y="8" width="3" height="32" rx="1.5" fill="#fff" />
          <path d="M16 9h18l-5 7 5 7H16z" fill="#fff" />
        </>
      }
    />
  ),
  tasks: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-tasks" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#4cd964" />
            <stop offset="1" stopColor="#248a3d" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-tasks)" />
          <circle cx="24" cy="24" r="13" fill="#fff" />
          <path d="M18 24.5 22.5 29 30 19" stroke="#248a3d" strokeWidth="3.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </>
      }
    />
  ),
  box: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-box" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#d98e4a" />
            <stop offset="1" stopColor="#8a4b12" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-box)" />
          <path d="M10 17 24 10l14 7v14l-14 7-14-7z" fill="#f5deb3" />
          <path d="M10 17l14 7 14-7M24 24v14" stroke="#8a4b12" strokeWidth="2" fill="none" />
        </>
      }
    />
  ),
  bom: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-bom" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#ffd60a" />
            <stop offset="1" stopColor="#ff9f0a" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-bom)" />
          <circle cx="24" cy="24" r="9" fill="none" stroke="#fff" strokeWidth="4" />
          <circle cx="24" cy="24" r="3" fill="#fff" />
          {[0, 45, 90, 135].map((a) => (
            <rect key={a} x="22" y="9" width="4" height="7" rx="2" fill="#fff" transform={`rotate(${a} 24 24)`} />
          ))}
        </>
      }
    />
  ),
  chat: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-chat" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#4cd964" />
            <stop offset="1" stopColor="#0a9d58" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-chat)" />
          <path d="M10 12h28v18H24l-7 7v-7h-7z" fill="#fff" transform="translate(-2 -1) scale(0.92)" />
        </>
      }
    />
  ),
  mail: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-mail" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#ffb340" />
            <stop offset="1" stopColor="#e8590c" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-mail)" />
          <rect x="10" y="15" width="28" height="19" rx="3" fill="#fff" />
          <path d="M11 17l13 9 13-9" stroke="#e8590c" strokeWidth="2.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </>
      }
    />
  ),
  clock: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="#1c1c1e" />
          <circle cx="24" cy="24" r="15" fill="#f2f2f7" />
          <path d="M24 16v8l6 3" stroke="#1c1c1e" strokeWidth="2.6" fill="none" strokeLinecap="round" />
        </>
      }
    />
  ),
  cart: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-cart" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#64d2ff" />
            <stop offset="1" stopColor="#0a84ff" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-cart)" />
          <path d="M10 12h4l3 14h15l4-11H15" stroke="#fff" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="19" cy="33" r="2.6" fill="#fff" />
          <circle cx="30" cy="33" r="2.6" fill="#fff" />
        </>
      }
    />
  ),
  sales: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-sales" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#30d158" />
            <stop offset="1" stopColor="#0a7d3b" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-sales)" />
          <rect x="8" y="15" width="32" height="18" rx="3" fill="#fff" opacity="0.92" />
          <circle cx="24" cy="24" r="5.5" fill="none" stroke="#0a7d3b" strokeWidth="2.4" />
          <path d="M22 21.5c-1.6.7-1.6 4.3 0 5M26 21.5c1.6.7 1.6 4.3 0 5" stroke="#0a7d3b" strokeWidth="1.8" fill="none" strokeLinecap="round" />
        </>
      }
    />
  ),
  import: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-imp" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#5e5ce6" />
            <stop offset="1" stopColor="#3634a3" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-imp)" />
          <path d="M24 10v16m-7-7 7 7 7-7" stroke="#fff" strokeWidth="3.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M12 33h24" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" />
        </>
      }
    />
  ),
  settings: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-set" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#c7c7cc" />
            <stop offset="1" stopColor="#636366" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-set)" />
          <circle cx="24" cy="24" r="8" fill="none" stroke="#fff" strokeWidth="4" />
          <circle cx="24" cy="24" r="3" fill="#fff" />
          {[0, 60, 120, 180, 240, 300].map((a) => (
            <rect key={a} x="22" y="10" width="4" height="7" rx="2" fill="#fff" transform={`rotate(${a} 24 24)`} />
          ))}
        </>
      }
    />
  ),
  trash: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-trash" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#e5e5ea" />
            <stop offset="1" stopColor="#8e8e93" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-trash)" />
          <path d="M15 17h18M20 17v-3h8v3M17 17l1.4 16h11.2L31 17M21 21v9M27 21v9" stroke="#48484a" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </>
      }
    />
  ),
  notes: ({ size = 55 }: IconProps) => (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <rect x="6" y="4" width="36" height="40" rx="4" fill="#fff" />
      <path d="M6 8a4 4 0 0 1 4-4h28a4 4 0 0 1 4 4v6H6z" fill="#ffd60a" />
      <rect x="12" y="20" width="24" height="2.6" rx="1.3" fill="#c7c7cc" />
      <rect x="12" y="26" width="24" height="2.6" rx="1.3" fill="#c7c7cc" />
      <rect x="12" y="32" width="16" height="2.6" rx="1.3" fill="#c7c7cc" />
    </svg>
  ),
  textedit: ({ size = 55 }: IconProps) => (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <rect x="10" y="3" width="28" height="42" rx="2" fill="#fff" stroke="#c7c7cc" />
      <rect x="15" y="10" width="18" height="2.6" rx="1.3" fill="#48484a" />
      <rect x="15" y="16" width="18" height="2.2" rx="1.1" fill="#aeaeb2" />
      <rect x="15" y="21" width="18" height="2.2" rx="1.1" fill="#aeaeb2" />
      <rect x="15" y="26" width="12" height="2.2" rx="1.1" fill="#aeaeb2" />
    </svg>
  ),
  newdoc: ({ size = 50 }: IconProps) => (
    <Tile
      size={size}
      defs={
        <>
          <Shadow />
          <linearGradient id="ti-new" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#f2f2f7" />
            <stop offset="1" stopColor="#c7c7cc" />
          </linearGradient>
        </>
      }
      body={
        <>
          <rect x="1" y="1" width="46" height="46" rx="11" fill="url(#ti-new)" />
          <circle cx="24" cy="24" r="11" fill="#30d158" />
          <path d="M24 18v12M18 24h12" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
        </>
      }
    />
  ),
};
