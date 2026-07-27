import React, { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import { get, Wafer, WaferComparison } from '../lib/api';
import { Head } from './MissionControl';

export default function YieldTrends() {
  const [wafers, setWafers] = useState<Wafer[]>([]);
  const [busy, setBusy] = useState(true);
  
  const [waferA, setWaferA] = useState<string>('');
  const [waferB, setWaferB] = useState<string>('');
  const [comparison, setComparison] = useState<WaferComparison | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const w = await get<Wafer[]>('v1/wafers');
        setWafers(w);
        if (w.length >= 2) {
          setWaferA(w[0].wafer_id);
          setWaferB(w[1].wafer_id);
        } else if (w.length === 1) {
          setWaferA(w[0].wafer_id);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setBusy(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    if (waferA && waferB && waferA !== waferB) {
      get<WaferComparison>(`v1/analytics/wafer-comparison?left=${waferA}&right=${waferB}`)
        .then(setComparison)
        .catch(e => {
          console.error(e);
          setComparison(null);
        });
    } else {
      setComparison(null);
    }
  }, [waferA, waferB]);

  if (busy) return <div className="loading">Loading yield trends…</div>;
  if (wafers.length === 0) return <section className="empty"><h2>No trend data</h2><p>Seed demo data first.</p></section>;

  const sortedWafers = [...wafers].sort((a,b) => b.yield_pct - a.yield_pct);
  const best = sortedWafers[0];
  const worst = sortedWafers[sortedWafers.length - 1];

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">SYNTHETIC FIXTURE COMPARISON SET</p>
          <h1>Yield Trends & Comparison</h1>
        </div>
      </header>

      <section className="grid">
        <article className="panel chart">
          <Head title="Fleet Yield Comparison" tag="BEST VS WORST" />
          <Plot
            data={[{
              x: sortedWafers.map(x => x.wafer_id),
              y: sortedWafers.map(x => x.yield_pct),
              type: 'bar',
              marker: { 
                color: sortedWafers.map(x => x.wafer_id === best.wafer_id ? '#4aedc4' : x.wafer_id === worst.wafer_id ? '#ff6b6b' : '#32527b')
              }
            }]}
            layout={{
              height: 245,
              margin: { l: 42, r: 15, t: 10, b: 55 },
              paper_bgcolor: 'transparent',
              plot_bgcolor: 'transparent',
              font: { color: '#92a2bb' },
              yaxis: { range: [0, 100], ticksuffix: '%', gridcolor: '#233652' },
              xaxis: { gridcolor: '#233652' }
            }}
            config={{ displayModeBar: false }}
          />
        </article>

        <article className="panel insight">
          <h3>Baseline Summary</h3>
          <p>Analysis of production runs across synthetic fixtures.</p>
          <div>
            <b className="mint">{best?.yield_pct}%</b><span>Best Yield ({best?.wafer_id})</span>
            <b className="red" style={{ marginTop: '10px', display: 'inline-block' }}>{worst?.yield_pct}%</b><span>Worst Yield ({worst?.wafer_id})</span>
          </div>
          <div style={{ marginTop: '15px', color: 'var(--mute)' }}>
            Max Yield Delta: {(best?.yield_pct - worst?.yield_pct).toFixed(2)}%
          </div>
        </article>
      </section>

      <section className="panel" style={{ marginTop: '20px' }}>
        <Head title="Wafer Comparison" tag="SIDE-BY-SIDE" />
        
        {wafers.length < 2 ? (
          <p className="muted">Fewer than two wafers exist. Comparison requires multiple wafers.</p>
        ) : (
          <>
            <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
              <div style={{ flex: 1 }}>
                <h4>Wafer A (Baseline)</h4>
                <select value={waferA} onChange={e => setWaferA(e.target.value)} style={{ padding: '8px', width: '100%', background: '#0d182b', color: 'white', border: '1px solid var(--line)', borderRadius: '6px' }}>
                  {wafers.map(w => <option key={`A-${w.wafer_id}`} value={w.wafer_id}>{w.lot_id} - {w.wafer_id}</option>)}
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <h4>Wafer B (Comparison)</h4>
                <select value={waferB} onChange={e => setWaferB(e.target.value)} style={{ padding: '8px', width: '100%', background: '#0d182b', color: 'white', border: '1px solid var(--line)', borderRadius: '6px' }}>
                  {wafers.map(w => <option key={`B-${w.wafer_id}`} value={w.wafer_id}>{w.lot_id} - {w.wafer_id}</option>)}
                </select>
              </div>
            </div>

            {waferA === waferB ? (
              <p className="muted">Select two different wafers to compare.</p>
            ) : comparison ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div>
                  <h3 style={{ marginBottom: '10px' }}>Metric Deltas</h3>
                  <table className="data-table" style={{ width: '100%', textAlign: 'left' }}>
                    <thead><tr><th>Metric</th><th>Wafer A</th><th>Wafer B</th><th>Delta</th></tr></thead>
                    <tbody>
                      <tr>
                        <td>Yield</td>
                        <td>{comparison.left_summary.yield_pct}%</td>
                        <td>{comparison.right_summary.yield_pct}%</td>
                        <td style={{ color: comparison.yield_delta_pct > 0 ? '#ff6b6b' : '#4aedc4' }}>
                          {(comparison.right_summary.yield_pct - comparison.left_summary.yield_pct).toFixed(2)}%
                        </td>
                      </tr>
                      <tr>
                        <td>DPPM</td>
                        <td>{comparison.left_summary.dppm}</td>
                        <td>{comparison.right_summary.dppm}</td>
                        <td style={{ color: comparison.dppm_delta < 0 ? '#ff6b6b' : '#4aedc4' }}>
                          {comparison.dppm_delta > 0 ? '+' : ''}{-comparison.dppm_delta}
                        </td>
                      </tr>
                      <tr>
                        <td>Failed Dies</td>
                        <td>{comparison.left_summary.fail_count}</td>
                        <td>{comparison.right_summary.fail_count}</td>
                        <td style={{ color: comparison.fail_delta < 0 ? '#ff6b6b' : '#4aedc4' }}>
                          {comparison.fail_delta > 0 ? '+' : ''}{-comparison.fail_delta}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div>
                  <h3 style={{ marginBottom: '10px' }}>Delta Chart</h3>
                  <Plot
                    data={[
                      { name: 'Yield %', x: ['Wafer A', 'Wafer B'], y: [comparison.left_summary.yield_pct, comparison.right_summary.yield_pct], type: 'bar', marker: { color: ['#32527b', '#4aedc4'] } }
                    ]}
                    layout={{ height: 180, margin: { l: 40, r: 10, t: 10, b: 30 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, yaxis: { range: [0, 100], gridcolor: '#233652' } }}
                    config={{ displayModeBar: false }}
                  />
                </div>
              </div>
            ) : (
              <p className="loading">Comparing wafers...</p>
            )}
          </>
        )}
      </section>
    </>
  );
}
