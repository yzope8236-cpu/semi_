import React from 'react';

export const nav = [
  'Mission Control',
  'Wafer Explorer',
  'Failure Intelligence',
  'Yield Trends',
  'Alerts Center',
  'Data Quality',
  'Reports'
];

interface SidebarProps {
  page: string;
  setPage: (p: string) => void;
}

export function Sidebar({ page, setPage }: SidebarProps) {
  return (
    <aside>
      <div className="brand">
        <span className="chip">◇</span>
        <b>YieldScope</b>
        <small>SEMICONDUCTOR INTELLIGENCE</small>
      </div>
      <nav>
        {nav.map(x => (
          <button
            className={page === x ? 'active' : ''}
            onClick={() => setPage(x)}
            key={x}
          >
            <i>{x === 'Mission Control' ? '◎' : x === 'Wafer Explorer' ? '◉' : '◇'}</i>
            {x}
          </button>
        ))}
      </nav>
      <div className="pipeline">
        <span>● Pipeline Operational</span>
        <small>✓ ClickHouse &nbsp; ✓ FastAPI &nbsp; ✓ Spring</small>
      </div>
    </aside>
  );
}
