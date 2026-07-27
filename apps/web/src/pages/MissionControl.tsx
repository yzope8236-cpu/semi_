import React, { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import { get, Overview, Failure, Alert, Conclusion } from '../lib/api';

export function Kpi({ label, value, icon, tone = '' }: { label: string; value: string; icon: string; tone?: string }) {
  return (
    <article className={`kpi ${tone}`}>
      <span>{icon}</span>
      <small>{label}</small>
      <strong>{value}</strong>
      <i>Live analytics</i>
    </article>
  );
}

export function Head({ title, tag }: { title: string; tag: string }) {
  return (
    <div className="head">
      <h2>{title}</h2>
      <span>{tag}</span>
    </div>
  );
}

interface Props {
  setPage: (page: string) => void;
  setWaferId?: (waferId: string) => void;
}

export default function MissionControl({ setPage, setWaferId }: Props) {
  const [overview, setOverview] = useState<Overview>();
  const [failures, setFailures] = useState<Failure[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [conclusions, setConclusions] = useState<Conclusion[]>([]);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [o, f, a, c] = await Promise.all([
          get<Overview>('v1/dashboard/overview'),
          get<Failure[]>('v1/analytics/failures'),
          get<Alert[]>('v1/analytics/alerts?threshold=95'),
          get<Conclusion[]>('v1/analytics/conclusions')
        ]);
        setOverview(o);
        setFailures(f);
        setAlerts(a);
        setConclusions(c);
      } catch (e) {
        console.error(e);
      } finally {
        setBusy(false);
      }
    };
    load();
  }, []);

  if (busy) return <div className="loading">Loading semiconductor intelligence…</div>;
  if (!overview?.kpis) return <section className="empty"><h2>No tester data loaded</h2><p>Upload an ATDF file or seed the built-in demonstration lot.</p></section>;

  const k = overview.kpis;
  const yieldColor = (k.yield_pct ?? 0) >= 95 ? 'mint' : 'red';
  const baselineConclusion = conclusions.find(c => c.category === 'yield' && c.severity === 'info');
  const criticalWafer = conclusions.find(c => c.severity === 'critical' && c.category === 'yield');

  return (
    <>
      <section className="hero panel">
        <div>
          <p className="eyebrow">LIVE PRODUCTION HEALTH</p>
          <h2>Yield is {Math.max(0, 95 - k.yield_pct).toFixed(2)}% below target</h2>
          <p>
            {conclusions.length > 0 ? `Evidence suggests ${conclusions.length} investigation areas across the fleet.` : 'Fleet is currently operating within expected parameters.'} Investigate critical wafers before release.
          </p>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="primary" onClick={() => setPage('Wafer Explorer')}>Wafer Explorer</button>
            <button className="ghost" onClick={() => setPage('Yield Trends')}>Fleet Comparisons</button>
            <button className="ghost" onClick={() => setPage('Failure Intelligence')}>Investigate Failures</button>
          </div>
        </div>
        <div className={`gauge ${yieldColor}`} style={{ '--p': `${k.yield_pct * 3.6}deg` } as React.CSSProperties}>
          <div>
            <strong>{k.yield_pct}%</strong>
            <small>FLEET YIELD<br />TARGET 95%</small>
          </div>
        </div>
      </section>

      <section className="kpis">
        <Kpi label="TESTED DIES" value={k.devices.toLocaleString()} icon="▦" />
        <Kpi label="FLEET YIELD" value={`${k.yield_pct}%`} tone={yieldColor} icon="◉" />
        <Kpi label="FAILED DIES" value={k.failed.toLocaleString()} tone="red" icon="⊗" />
        <Kpi label="DPPM" value={Math.round((k.failed * 1000000) / (k.devices || 1)).toLocaleString()} tone="red" icon="↗" />
        <Kpi label="AVG TEST TIME" value={`${k.avg_test_ms} ms`} tone="violet" icon="◷" />
        <Kpi label="CONCLUSIONS" value={conclusions.length.toString()} tone="amber" icon="⚡" />
      </section>

      <section className="grid">
        <article className="panel chart">
          <Head title="Fleet comparisons" tag="BASELINE VS WORST" />
          {baselineConclusion ? (
            <div style={{ marginTop: '15px' }}>
              <p className="muted">{baselineConclusion.message} {baselineConclusion.evidence}</p>
              <Plot
                data={[
                  {
                    x: ['Best Wafer', 'Worst Wafer'],
                    y: [
                      // Extracting numbers from the evidence string "Yield delta is X%"
                      // Or we can just plot the overall trend. Since we don't have the exact yields isolated here without string parsing,
                      // we'll use the trend data to show highest/lowest.
                      Math.max(...overview.trend.map(t => t.yield_pct)),
                      Math.min(...overview.trend.map(t => t.yield_pct))
                    ],
                    type: 'bar',
                    marker: { color: ['#4aedc4', '#ff6b6b'] }
                  }
                ]}
                layout={{
                  height: 180, margin: { l: 40, r: 10, t: 10, b: 30 },
                  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
                  font: { color: '#92a2bb' },
                  yaxis: { range: [0, 100], ticksuffix: '%', gridcolor: '#233652' }
                }}
                config={{ displayModeBar: false }}
              />
            </div>
          ) : (
            <p className="muted">No yield baseline deviations found.</p>
          )}
        </article>

        <article className="panel">
          <Head title="Engineering conclusions" tag={`${conclusions.length} FINDINGS`} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px', overflowY: 'auto', maxHeight: '250px' }}>
            {conclusions.slice(0, 5).map((c, i) => (
              <div key={i} className={`alert ${c.severity === 'critical' ? 'critical' : c.severity}`} style={{ borderLeft: `3px solid ${c.severity === 'critical' ? '#ff6b6b' : c.severity === 'warning' ? '#f5a623' : '#4aedc4'}`, paddingLeft: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <strong style={{ color: '#fff' }}>{c.title}</strong>
                  <small style={{ color: '#92a2bb', textTransform: 'uppercase' }}>{c.category}</small>
                </div>
                <p style={{ margin: '5px 0' }}>{c.message} <br/><span style={{ color: '#92a2bb' }}>{c.evidence}</span></p>
                <div style={{ display: 'flex', gap: '10px', marginTop: '5px' }}>
                  <button className="ghost" style={{ padding: '2px 8px', fontSize: '0.8rem' }} onClick={() => {
                    if (setWaferId) setWaferId(c.affected_wafer);
                    setPage(c.category === 'test' ? 'Failure Intelligence' : 'Wafer Explorer');
                  }}>Investigate {c.affected_wafer}</button>
                </div>
              </div>
            ))}
            {conclusions.length === 0 && <p className="muted">No engineering conclusions available.</p>}
          </div>
        </article>
      </section>

      <section className="grid lower">
        <article className="panel">
          <Head title="Critical wafers" tag={criticalWafer ? "1 IDENTIFIED" : "NONE"} />
          {criticalWafer ? (
             <div className="alert" style={{ borderLeft: '3px solid #ff6b6b', paddingLeft: '10px' }}>
               <strong style={{ color: '#ff6b6b' }}>⚠ {criticalWafer.affected_wafer}</strong>
               <p>{criticalWafer.affected_lot} · {criticalWafer.evidence}</p>
               <button onClick={() => {
                 if (setWaferId) setWaferId(criticalWafer.affected_wafer);
                 setPage('Wafer Explorer');
               }}>Explore Spatial Map</button>
             </div>
          ) : (
            <p className="muted">No critical yield loss wafers detected.</p>
          )}
        </article>
        
        <article className="panel chart">
          <Head title="Yield trend" tag="LOT HISTORY" />
          <Plot
            data={[{
              x: overview.trend.map(x => x.lot_id),
              y: overview.trend.map(x => x.yield_pct),
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#4aedc4', width: 3 },
              fill: 'tozeroy',
              fillcolor: 'rgba(74,237,196,.12)'
            }]}
            layout={{
              height: 180,
              margin: { l: 42, r: 15, t: 10, b: 35 },
              paper_bgcolor: 'transparent',
              plot_bgcolor: 'transparent',
              font: { color: '#92a2bb' },
              yaxis: { range: [0, 100], ticksuffix: '%', gridcolor: '#233652' },
              xaxis: { gridcolor: '#233652' }
            }}
            config={{ displayModeBar: false }}
          />
        </article>
      </section>
    </>
  );
}
