import React, { useEffect, useState, useMemo } from 'react';
import { get, Conclusion } from '../lib/api';
import { Head } from './MissionControl';

interface Props {
  setPage: (page: string) => void;
  setWaferId: (waferId: string) => void;
  notify: (msg: string) => void;
}

export default function AlertsCenter({ setPage, setWaferId, notify }: Props) {
  const [conclusions, setConclusions] = useState<Conclusion[]>([]);
  const [busy, setBusy] = useState(true);
  
  const [activeCategory, setActiveCategory] = useState<string>('ALL');
  const [acknowledged, setAcknowledged] = useState<Set<string>>(new Set());

  useEffect(() => {
    const load = async () => {
      setBusy(true);
      try {
        const c = await get<Conclusion[]>('v1/analytics/conclusions');
        setConclusions(c);
      } catch (e) {
        console.error(e);
      } finally {
        setBusy(false);
      }
    };
    load();
  }, []);

  const ackAlert = (id: string) => {
    setAcknowledged(prev => new Set(prev).add(id));
    notify('Acknowledged locally — persistence integration pending.');
  };

  const filteredConclusions = useMemo(() => {
    return conclusions.filter(c => {
      if (activeCategory === 'ALL') return true;
      return c.category.toUpperCase() === activeCategory;
    });
  }, [conclusions, activeCategory]);

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">YIELD DEVIATIONS</p>
          <h1>Alerts & Conclusions Center</h1>
        </div>
        <div className="actions" style={{ flexDirection: 'row', alignItems: 'center', gap: '15px' }}>
          <button className="ghost" onClick={() => setActiveCategory(activeCategory)}>↻ Refresh</button>
        </div>
      </header>

      <section className="panel" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button className={activeCategory === 'ALL' ? 'ghost active-toggle' : 'ghost'} onClick={() => setActiveCategory('ALL')}>All</button>
          <button className={activeCategory === 'YIELD' ? 'ghost active-toggle' : 'ghost'} onClick={() => setActiveCategory('YIELD')}>Yield</button>
          <button className={activeCategory === 'SPATIAL' ? 'ghost active-toggle' : 'ghost'} onClick={() => setActiveCategory('SPATIAL')}>Spatial</button>
          <button className={activeCategory === 'TEST' ? 'ghost active-toggle' : 'ghost'} onClick={() => setActiveCategory('TEST')}>Test</button>
          <button className={activeCategory === 'RETEST' ? 'ghost active-toggle' : 'ghost'} onClick={() => setActiveCategory('RETEST')}>Retest</button>
          <button className={activeCategory === 'SITE' ? 'ghost active-toggle' : 'ghost'} onClick={() => setActiveCategory('SITE')}>Site</button>
        </div>
      </section>

      {busy ? <div className="loading">Loading conclusions…</div> : (
        <section className="panel">
          <Head title="Active Conclusions" tag={`${filteredConclusions.length} INSIGHTS`} />
          
          <table className="data-table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', marginTop: '15px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                <th style={{ padding: '10px 0' }}>Wafer ID</th>
                <th>Category</th>
                <th>Title</th>
                <th>Severity</th>
                <th>Action</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredConclusions.map((c, idx) => {
                const uniqueId = `${c.affected_wafer}-${c.title}`;
                const isAck = acknowledged.has(uniqueId);
                return (
                  <tr key={idx} style={{ borderBottom: '1px solid #1a2944', opacity: isAck ? 0.6 : 1 }}>
                    <td style={{ padding: '12px 0', fontWeight: 'bold' }}>{c.affected_wafer}</td>
                    <td style={{ textTransform: 'uppercase', fontSize: '11px', color: 'var(--mute)' }}>{c.category}</td>
                    <td>
                      <div><strong>{c.title}</strong></div>
                      <div style={{ fontSize: '11px', color: 'var(--mute)', marginTop: '4px' }}>{c.message} {c.evidence}</div>
                    </td>
                    <td>
                      <span style={{ padding: '3px 6px', borderRadius: '4px', background: c.severity === 'critical' ? '#ff6b6b33' : c.severity === 'warning' ? '#f0a50033' : '#4aedc433', color: c.severity === 'critical' ? 'var(--red)' : c.severity === 'warning' ? 'var(--amber)' : 'var(--mint)', fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase' }}>
                        {c.severity}
                      </span>
                    </td>
                    <td style={{ fontStyle: 'italic', fontSize: '11px' }}>{c.recommended_action}</td>
                    <td>{isAck ? 'Acknowledged' : 'Open'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '5px' }}>
                        {!isAck && <button className="ghost" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => ackAlert(uniqueId)}>Acknowledge</button>}
                        <button className="primary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => { setWaferId(c.affected_wafer); setPage('Wafer Explorer'); }}>Investigate</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {filteredConclusions.length === 0 && (
            <p className="muted" style={{ padding: '20px 0', textAlign: 'center' }}>No conclusions found for the current criteria.</p>
          )}
        </section>
      )}
    </>
  );
}
