import React, { useEffect, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import { get, Wafer, Die, Spatial, TestResult, Conclusion, WaferSummary, API_BASE } from '../lib/api';
import { Head } from './MissionControl';

interface Props {
  initialWaferId?: string;
  setPage: (page: string) => void;
}

export default function WaferExplorer({ initialWaferId, setPage }: Props) {
  const [wafers, setWafers] = useState<Wafer[]>([]);
  const [selectedWaferId, setSelectedWaferId] = useState<string>();
  const [dies, setDies] = useState<Die[]>([]);
  const [spatial, setSpatial] = useState<Spatial>();
  const [selectedDie, setSelectedDie] = useState<Die>();
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [busy, setBusy] = useState(true);
  const [fetchError, setFetchError] = useState<{ message: string; url?: string } | null>(null);

  // New analytics states
  const [activeTab, setActiveTab] = useState<'SPATIAL' | 'TESTS' | 'SITES' | 'RETESTS'>('SPATIAL');
  const [summary, setSummary] = useState<WaferSummary>();
  const [tests, setTests] = useState<any[]>([]);
  const [sites, setSites] = useState<any[]>([]);
  const [retests, setRetests] = useState<any>();
  const [conclusions, setConclusions] = useState<Conclusion[]>([]);

  // Filters and modes
  const [filterMode, setFilterMode] = useState<'ALL' | 'PASS' | 'FAIL' | 'RETEST'>('ALL');
  const [hwBinFilter, setHwBinFilter] = useState<string>('ALL');
  const [colorMode, setColorMode] = useState<'PASS_FAIL' | 'HW_BIN' | 'RETEST'>('PASS_FAIL');

  useEffect(() => {
    const loadWafers = async () => {
      try {
        const w = await get<Wafer[]>('v1/wafers');
        setWafers(w);
        if (w.length > 0) {
          const target = w.find(x => x.wafer_id === initialWaferId) || w[0];
          setSelectedWaferId(target.wafer_id);
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
    if (!selectedWaferId) return;

    const fetchWaferData = async () => {
      setSelectedDie(undefined);
      setTestResults([]);
      setFetchError(null);
      try {
        const [mapRes, spatialRes, testsRes, sumRes, sitesRes, retestsRes, conclusionsRes] = await Promise.all([
          fetch(`${API_BASE}/v1/wafers/${selectedWaferId}/map`),
          fetch(`${API_BASE}/v1/analytics/spatial/${selectedWaferId}`),
          fetch(`${API_BASE}/v1/analytics/wafers/${selectedWaferId}/tests`),
          fetch(`${API_BASE}/v1/analytics/wafers/${selectedWaferId}/summary`),
          fetch(`${API_BASE}/v1/analytics/wafers/${selectedWaferId}/sites`),
          fetch(`${API_BASE}/v1/analytics/wafers/${selectedWaferId}/retests`),
          fetch(`${API_BASE}/v1/analytics/conclusions`)
        ]);

        if (!mapRes.ok) throw { message: await mapRes.text(), url: mapRes.url };
        if (!spatialRes.ok) throw { message: await spatialRes.text(), url: spatialRes.url };
        if (!testsRes.ok) throw { message: await testsRes.text(), url: testsRes.url };

        const mapResponse = await mapRes.json();
        const spatialResponse = await spatialRes.json();
        const testResponse = await testsRes.json();
        
        console.log("Wafer map response", mapResponse);
        console.log("Spatial response", spatialResponse);
        
        setDies(mapResponse.dies);
        setSpatial(spatialResponse);
        setTests(testResponse);

        if (sumRes.ok) setSummary(await sumRes.json());
        if (sitesRes.ok) setSites(await sitesRes.json());
        if (retestsRes.ok) setRetests(await retestsRes.json());
        if (conclusionsRes.ok) {
          const c = await conclusionsRes.json();
          setConclusions(c.filter((x: any) => x.affected_wafer === selectedWaferId));
        }
      } catch (e: any) {
        setFetchError({ message: e.message || 'Unknown error', url: e.url || 'API' });
      }
    };

    fetchWaferData();
  }, [selectedWaferId]);

  const selectDie = async (d: Die) => {
    setSelectedDie(d);
    setTestResults([]);
    try {
      const res = await get<{ device: Die; test_results: TestResult[] }>(`v1/devices/${d.device_id}`);
      setTestResults(res.test_results);
    } catch (e) {
      console.error(e);
    }
  };

  const bounds = useMemo(() => dies.length ? {
    minX: Math.min(...dies.map(d => d.x_coord)),
    maxX: Math.max(...dies.map(d => d.x_coord)),
    minY: Math.min(...dies.map(d => d.y_coord)),
    maxY: Math.max(...dies.map(d => d.y_coord))
  } : null, [dies]);

  const hwBins = useMemo(() => Array.from(new Set(dies.map(d => d.hardware_bin))).sort(), [dies]);

  const filteredDies = useMemo(() => {
    return dies.filter(d => {
      if (filterMode === 'PASS' && !d.passed) return false;
      if (filterMode === 'FAIL' && d.passed) return false;
      if (filterMode === 'RETEST' && d.retest_count === 0) return false;
      if (hwBinFilter !== 'ALL' && d.hardware_bin.toString() !== hwBinFilter) return false;
      return true;
    });
  }, [dies, filterMode, hwBinFilter]);

  if (busy) return <div className="loading">Loading wafer data…</div>;
  if (wafers.length === 0) return <section className="empty"><h2>No wafer data</h2><p>Seed demo data first.</p></section>;

  const getDieColorClass = (d: Die) => {
    if (colorMode === 'PASS_FAIL') return d.passed ? 'pass' : 'fail';
    if (colorMode === 'RETEST') return d.retest_count > 0 ? 'amber' : 'pass';
    if (colorMode === 'HW_BIN') return `hwbin hwbin-${d.hardware_bin % 8}`;
    return '';
  };

  const selectedWafer = wafers.find(w => w.wafer_id === selectedWaferId);

  return (
    <>
      <div style={{ marginBottom: '20px', color: 'var(--mute)' }}>
        <small>Production / {selectedWafer?.lot_id} / {selectedWaferId}</small>
      </div>

      <section className="panel wafer">
        <Head title="Wafer Explorer" tag={selectedWaferId || ''} />
        
        <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', flexWrap: 'wrap' }}>
          <select value={selectedWaferId} onChange={(e) => {
            setSelectedWaferId(e.target.value);
          }} style={{ padding: '8px', background: '#0d182b', color: 'white', border: '1px solid var(--line)', borderRadius: '6px' }}>
            {wafers.map(w => <option key={w.wafer_id} value={w.wafer_id}>{w.lot_id} - {w.wafer_id}</option>)}
          </select>
        </div>

        {fetchError && (
          <div style={{ padding: '20px', background: '#ff6b6b33', border: '1px solid var(--red)', borderRadius: '6px', marginBottom: '20px' }}>
            <h3 style={{ color: 'var(--red)', margin: '0 0 10px 0' }}>API Request Failed</h3>
            <p style={{ margin: '0 0 5px 0' }}><strong>URL:</strong> {fetchError.url}</p>
            <p style={{ margin: '0 0 15px 0' }}><strong>Error:</strong> {fetchError.message}</p>
            <button className="primary" onClick={() => setSelectedWaferId(selectedWaferId)}>Retry</button>
          </div>
        )}

        {!fetchError && conclusions.length > 0 && (
          <div style={{ marginBottom: '20px', padding: '15px', background: 'rgba(245, 166, 35, 0.1)', borderLeft: '3px solid #f5a623', borderRadius: '4px' }}>
            <strong style={{ color: '#f5a623', display: 'block', marginBottom: '5px' }}>Engineering Insight</strong>
            {conclusions.map((c, idx) => (
              <p key={idx} style={{ margin: 0, fontSize: '0.9rem' }}>{c.message} {c.evidence} {c.recommended_action}</p>
            ))}
          </div>
        )}

        <div className="tabs" style={{ display: 'flex', gap: '20px', borderBottom: '1px solid var(--line)', marginBottom: '20px' }}>
          {['SPATIAL', 'TESTS', 'SITES', 'RETESTS'].map(t => (
            <button key={t} className={`tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t as any)}
              style={{ background: 'none', border: 'none', color: activeTab === t ? '#fff' : 'var(--mute)', paddingBottom: '10px', borderBottom: activeTab === t ? '2px solid #4aedc4' : '2px solid transparent', cursor: 'pointer' }}>
              {t === 'SPATIAL' ? 'Spatial Map' : t === 'TESTS' ? 'Test Distribution' : t === 'SITES' ? 'Site Analysis' : 'Retest Analysis'}
            </button>
          ))}
        </div>

        {activeTab === 'SPATIAL' && (
          <>
            <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', flexWrap: 'wrap' }}>
              <select value={filterMode} onChange={e => setFilterMode(e.target.value as any)} style={{ padding: '8px', background: '#0d182b', color: 'white', border: '1px solid var(--line)', borderRadius: '6px' }}>
                <option value="ALL">All Dies</option>
                <option value="PASS">Pass Only</option>
                <option value="FAIL">Fail Only</option>
                <option value="RETEST">Retested Only</option>
              </select>

              <select value={hwBinFilter} onChange={e => setHwBinFilter(e.target.value)} style={{ padding: '8px', background: '#0d182b', color: 'white', border: '1px solid var(--line)', borderRadius: '6px' }}>
                <option value="ALL">All HW Bins</option>
                {hwBins.map(b => <option key={b} value={b.toString()}>HW Bin {b}</option>)}
              </select>

              <div style={{ marginLeft: 'auto', display: 'flex', gap: '10px' }}>
                <button className={colorMode === 'PASS_FAIL' ? 'ghost active-toggle' : 'ghost'} onClick={() => setColorMode('PASS_FAIL')}>Pass/Fail</button>
                <button className={colorMode === 'HW_BIN' ? 'ghost active-toggle' : 'ghost'} onClick={() => setColorMode('HW_BIN')}>HW Bin</button>
                <button className={colorMode === 'RETEST' ? 'ghost active-toggle' : 'ghost'} onClick={() => setColorMode('RETEST')}>Retest</button>
              </div>
            </div>

            <div className="wafer-body">
              <div className="insight" style={{ alignSelf: 'flex-start' }}>
                <h3>Spatial failure pattern</h3>
                <p>{spatial?.interpretation || (selectedWaferId ? (fetchError ? 'Analysis unavailable due to error' : 'Loading analysis...') : 'Select wafer for analysis')}</p>
                <div>
                  <b className="bad">{spatial ? spatial.failed_dies : '-'}</b><span>Failed dies</span>
                  <b className="amber">{spatial ? spatial.edge_failure_share_pct : '-'}%</b><span>Near edge</span>
                </div>
              </div>

              <div className="disc">
                <div className="notch" />
                {filteredDies.map(d => {
                  const left = bounds ? ((d.x_coord - bounds.minX) / (bounds.maxX - bounds.minX || 1)) * 82 + 9 : 50;
                  const top = bounds ? ((d.y_coord - bounds.minY) / (bounds.maxY - bounds.minY || 1)) * 82 + 9 : 50;
                  return (
                    <button
                      aria-label={`Die ${d.device_id}`}
                      onClick={() => selectDie(d)}
                      className={`die ${getDieColorClass(d)} ${selectedDie?.device_id === d.device_id ? 'chosen' : ''}`}
                      style={{ left: `${left}%`, top: `${top}%` }}
                      key={d.device_id}
                      title={`X:${d.x_coord} Y:${d.y_coord} | ${d.passed ? 'PASS' : 'FAIL'} | Bin ${d.hardware_bin}`}
                    />
                  );
                })}
              </div>

              {selectedDie && (
                <div className="insight device-drawer" style={{ alignSelf: 'flex-start', maxHeight: '500px', overflowY: 'auto' }}>
                  <h3>Device Detail</h3>
                  <dl>
                    <dt>Coordinate</dt><dd>X={selectedDie.x_coord}, Y={selectedDie.y_coord}</dd>
                    <dt>Site</dt><dd>{selectedDie.site}</dd>
                    <dt>HW Bin</dt><dd>{selectedDie.hardware_bin}</dd>
                    <dt>Retest Count</dt><dd>{selectedDie.retest_count}</dd>
                    <dt>Result</dt><dd className={selectedDie.passed ? 'ok' : 'bad'}>{selectedDie.passed ? 'PASS' : 'FAIL'}</dd>
                  </dl>

                  {testResults.length > 0 && (
                    <div style={{ marginTop: '15px' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '12px' }}>Test Results</h4>
                      <table className="data-table" style={{ width: '100%', fontSize: '10px', textAlign: 'left' }}>
                        <thead><tr><th>Test</th><th>Value</th><th>Limits</th><th>S</th></tr></thead>
                        <tbody>
                          {testResults.map((tr, idx) => (
                            <tr key={idx} style={{ color: tr.passed ? 'inherit' : 'var(--red)' }}>
                              <td title={tr.test_name}>{tr.test_num}</td>
                              <td>{tr.measured_value !== null ? tr.measured_value.toFixed(2) : '-'}</td>
                              <td>{tr.lower_limit ?? ''}-{tr.upper_limit ?? ''}</td>
                              <td>{tr.passed ? 'P' : 'F'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {activeTab === 'TESTS' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {tests.length === 0 ? (
              <p className="muted">No sufficient data in this selected fixture.</p>
            ) : (
              <>
                <div>
                  <h3 style={{ marginBottom: '10px' }}>Test Failure Pareto</h3>
                  <Plot
                    data={[{
                      x: tests.map(t => t.test_name),
                      y: tests.map(t => t.fail_count),
                      type: 'bar',
                      marker: { color: '#ff6b6b' }
                    }]}
                    layout={{ height: 300, margin: { l: 40, r: 10, t: 10, b: 50 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, xaxis: { gridcolor: '#233652' }, yaxis: { gridcolor: '#233652' } }}
                    config={{ displayModeBar: false }}
                  />
                </div>
                <div>
                  <h3 style={{ marginBottom: '10px' }}>Measurement vs Limits</h3>
                  <Plot
                    data={[
                      {
                        name: 'Average Value',
                        x: tests.map(t => t.test_name),
                        y: tests.map(t => t.average_value),
                        type: 'scatter',
                        mode: 'markers',
                        marker: { color: '#4aedc4', size: 10 }
                      },
                      {
                        name: 'Upper Limit',
                        x: tests.map(t => t.test_name),
                        y: tests.map(t => t.upper_limit),
                        type: 'scatter',
                        mode: 'markers',
                        marker: { color: '#ff6b6b', symbol: 'line-ew-open', size: 12 }
                      },
                      {
                        name: 'Lower Limit',
                        x: tests.map(t => t.test_name),
                        y: tests.map(t => t.lower_limit),
                        type: 'scatter',
                        mode: 'markers',
                        marker: { color: '#f5a623', symbol: 'line-ew-open', size: 12 }
                      }
                    ]}
                    layout={{ height: 350, margin: { l: 40, r: 10, t: 10, b: 50 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, xaxis: { gridcolor: '#233652' }, yaxis: { gridcolor: '#233652' } }}
                    config={{ displayModeBar: false }}
                  />
                </div>
                <div>
                  <h3 style={{ marginBottom: '10px' }}>Failure Rate</h3>
                  <Plot
                    data={[{
                      x: tests.map(t => t.test_name),
                      y: tests.map(t => t.failure_rate),
                      type: 'bar',
                      marker: { color: '#f5a623' }
                    }]}
                    layout={{ height: 300, margin: { l: 40, r: 10, t: 10, b: 50 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, yaxis: { ticksuffix: '%', gridcolor: '#233652' }, xaxis: { gridcolor: '#233652' } }}
                    config={{ displayModeBar: false }}
                  />
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'SITES' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {sites.length === 0 ? (
              <p className="muted">No sufficient data in this selected fixture.</p>
            ) : (
              <>
                <div>
                  <h3 style={{ marginBottom: '10px' }}>Site Yield Comparison</h3>
                  <Plot
                    data={[{
                      x: sites.map(s => `Site ${s.site}`),
                      y: sites.map(s => s.yield_pct),
                      type: 'bar',
                      marker: { color: '#4aedc4' }
                    }]}
                    layout={{ height: 300, margin: { l: 40, r: 10, t: 10, b: 50 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, yaxis: { range: [0, 100], ticksuffix: '%', gridcolor: '#233652' } }}
                    config={{ displayModeBar: false }}
                  />
                </div>
                <table className="data-table" style={{ width: '100%', textAlign: 'left' }}>
                  <thead><tr><th>Site</th><th>Tested Dies</th><th>Failed Dies</th><th>Yield</th><th>Top HW Bin</th></tr></thead>
                  <tbody>
                    {sites.map(s => (
                      <tr key={s.site}>
                        <td>{s.site}</td><td>{s.tested_dies}</td><td style={{ color: s.failed_dies > 0 ? '#ff6b6b' : 'inherit' }}>{s.failed_dies}</td><td>{s.yield_pct}%</td><td>{s.top_hardware_bin}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>
        )}

        {activeTab === 'RETESTS' && (
          <div>
            {!retests || retests.total_attempts === 0 ? (
              <p className="muted">No sufficient data in this selected fixture.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                  <div className="insight" style={{ flex: 1 }}>
                    <h3>Retest Summary</h3>
                    <dl>
                      <dt>Physical Devices</dt><dd>{retests.physical_devices}</dd>
                      <dt>Total Attempts</dt><dd>{retests.total_attempts}</dd>
                      <dt>Retested Devices</dt><dd>{retests.retested_devices}</dd>
                      <dt>Recovery Rate</dt><dd>{retests.recovery_rate_pct}%</dd>
                    </dl>
                  </div>
                  <div style={{ flex: 1 }}>
                    <Plot
                      data={[
                        { name: 'First Pass', x: ['First Attempt', 'Final Result'], y: [retests.first_attempt_pass_count, retests.final_pass_count], type: 'bar', marker: { color: '#4aedc4' } }
                      ]}
                      layout={{ height: 250, margin: { l: 40, r: 10, t: 10, b: 40 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#92a2bb' }, yaxis: { gridcolor: '#233652' } }}
                      config={{ displayModeBar: false }}
                    />
                  </div>
                </div>
                <div>
                  <h3 style={{ marginBottom: '10px' }}>Attempt History Table</h3>
                  <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                    <table className="data-table" style={{ width: '100%', textAlign: 'left' }}>
                      <thead><tr><th>Device ID</th><th>X, Y</th><th>Retest Index</th><th>Bin</th><th>Result</th></tr></thead>
                      <tbody>
                        {retests.history.map((h: any) => (
                          <tr key={h.device_id}>
                            <td>{h.device_id}</td><td>{h.x_coord}, {h.y_coord}</td><td>{h.retest_count}</td><td>{h.hardware_bin}</td>
                            <td style={{ color: h.passed ? '#4aedc4' : '#ff6b6b' }}>{h.passed ? 'PASS' : 'FAIL'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

      </section>
    </>
  );
}
