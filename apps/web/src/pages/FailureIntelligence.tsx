import React, { useEffect, useState, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { get, Failure, Conclusion, Wafer, WaferSummary } from '../lib/api';
import { Head } from './MissionControl';

interface Props {
  setPage: (page: string) => void;
  initialWaferId?: string;
}

export default function FailureIntelligence({ setPage, initialWaferId }: Props) {
  const [wafers, setWafers] = useState<Wafer[]>([]);
  const [selectedWafer, setSelectedWafer] = useState<string>('');
  
  const [conclusions, setConclusions] = useState<Conclusion[]>([]);
  const [tests, setTests] = useState<any[]>([]);
  const [sites, setSites] = useState<any[]>([]);
  const [summary, setSummary] = useState<WaferSummary>();
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    const loadWafers = async () => {
      try {
        const w = await get<Wafer[]>('v1/wafers');
        setWafers(w);
        if (w.length > 0) {
          const target = w.find(x => x.wafer_id === initialWaferId) || w[0];
          setSelectedWafer(target.wafer_id);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setBusy(false);
      }
    };
    loadWafers();
  }, [initialWaferId]);

  useEffect(() => {
    if (!selectedWafer) return;
    const loadData = async () => {
      try {
        const [c, t, s, sum] = await Promise.all([
          get<Conclusion[]>('v1/analytics/conclusions'),
          get<any[]>(`v1/analytics/wafers/${selectedWafer}/tests`),
          get<any[]>(`v1/analytics/wafers/${selectedWafer}/sites`),
          get<WaferSummary>(`v1/analytics/wafers/${selectedWafer}/summary`)
        ]);
        setConclusions(c.filter(x => x.affected_wafer === selectedWafer && (x.category === 'test' || x.category === 'bin' || x.category === 'site')));
        setTests(t);
        setSites(s);
        setSummary(sum);
      } catch (e) {
        console.error(e);
      }
    };
    loadData();
  }, [selectedWafer]);

  if (busy) return <div className="loading">Loading failure intelligence…</div>;
  if (wafers.length === 0) return <section className="empty"><h2>No data</h2><p>Seed demo data first.</p></section>;

  const failedTests = tests.filter(t => t.fail_count > 0).sort((a,b) => b.fail_count - a.fail_count);

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">ROOT CAUSE ANALYSIS</p>
          <h1>Failure Intelligence</h1>
        </div>
        <div className="actions" style={{ flexDirection: 'row' }}>
          <select value={selectedWafer} onChange={e => setSelectedWafer(e.target.value)} style={{ padding: '8px', background: '#0d182b', color: 'white', border: '1px solid var(--line)', borderRadius: '6px' }}>
            {wafers.map(w => <option key={w.wafer_id} value={w.wafer_id}>{w.lot_id} - {w.wafer_id}</option>)}
          </select>
          <button className="primary" onClick={() => setPage('Wafer Explorer')}>Investigate in Wafer Explorer</button>
        </div>
      </header>

      {conclusions.length > 0 && (
        <section className="panel" style={{ marginBottom: '20px', background: 'rgba(245, 166, 35, 0.1)', borderLeft: '3px solid #f5a623' }}>
          <Head title="Candidate Investigation Areas" tag={`${conclusions.length} FINDINGS`} />
          <div style={{ marginTop: '10px' }}>
            {conclusions.map((c, i) => (
              <div key={i} style={{ marginBottom: '10px' }}>
                <strong style={{ color: '#f5a623' }}>{c.title}</strong>
                <p style={{ margin: '5px 0', fontSize: '0.9rem' }}>{c.message} <span style={{ color: 'var(--mute)' }}>{c.evidence}</span></p>
                <i style={{ fontSize: '0.85rem', color: '#4aedc4' }}>{c.recommended_action}</i>
              </div>
            ))}
          </div>
        </section>
      )}

      {failedTests.length === 0 ? (
        <section className="panel"><p className="muted">No sufficient data or no failures in this selected fixture.</p></section>
      ) : (
        <section className="grid">
          <article className="panel chart">
            <Head title="Test Failure Pareto" tag="BY COUNT" />
            <Plot
              data={[{
                x: failedTests.map(t => t.test_name),
                y: failedTests.map(t => t.fail_count),
                type: 'bar',
                marker: { color: '#ff6b6b' }
              }]}
              layout={{ height: 250, margin: { l: 40, r: 10, t: 10, b: 60 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, xaxis: { gridcolor: '#233652' }, yaxis: { gridcolor: '#233652' } }}
              config={{ displayModeBar: false }}
            />
          </article>

          <article className="panel chart">
            <Head title="Test Value Distribution vs Limits" tag="TOP FAILURES" />
            <Plot
              data={failedTests.slice(0, 5).map(t => ({
                x: [t.test_name],
                y: [t.average_value],
                type: 'box',
                name: t.test_name,
                boxpoints: 'all',
                jitter: 0.3,
                pointpos: -1.8,
                marker: { color: '#4aedc4' },
                error_y: { type: 'data', symmetric: false, array: [t.maximum_value - t.average_value], arrayminus: [t.average_value - t.minimum_value], color: '#f5a623', visible: true }
              }))}
              layout={{ height: 250, margin: { l: 40, r: 10, t: 10, b: 60 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, showlegend: false, xaxis: { gridcolor: '#233652' }, yaxis: { gridcolor: '#233652' } }}
              config={{ displayModeBar: false }}
            />
          </article>

          <article className="panel chart">
            <Head title="Hardware Bin Distribution" tag="FINAL BINS" />
            {summary && summary.hardware_bin_distribution.length > 0 ? (
              <Plot
                data={[{
                  labels: summary.hardware_bin_distribution.map(b => `Bin ${b.bin}`),
                  values: summary.hardware_bin_distribution.map(b => b.count),
                  type: 'pie',
                  marker: { colors: ['#4aedc4', '#32527b', '#ff6b6b', '#f5a623', '#a371f7'] },
                  textinfo: 'label+percent',
                  hole: 0.4
                }]}
                layout={{ height: 250, margin: { l: 10, r: 10, t: 10, b: 10 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, showlegend: false }}
                config={{ displayModeBar: false }}
              />
            ) : (
              <p className="muted">No bin data available.</p>
            )}
          </article>

          <article className="panel chart">
            <Head title="Site Failure Comparison" tag="FAILED DIES" />
            {sites.length > 0 ? (
              <Plot
                data={[{
                  x: sites.map(s => `Site ${s.site}`),
                  y: sites.map(s => s.failed_dies),
                  type: 'bar',
                  marker: { color: '#ff6b6b' }
                }]}
                layout={{ height: 250, margin: { l: 40, r: 10, t: 10, b: 40 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, yaxis: { gridcolor: '#233652' } }}
                config={{ displayModeBar: false }}
              />
            ) : (
              <p className="muted">No site data available.</p>
            )}
          </article>
        </section>
      )}
    </>
  );
}
