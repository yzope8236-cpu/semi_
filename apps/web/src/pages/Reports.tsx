import React, { useEffect, useState } from 'react';
import { get, Overview, Wafer, Failure, IngestFile, Conclusion } from '../lib/api';
import { Head } from './MissionControl';

export default function Reports() {
  const [overview, setOverview] = useState<Overview>();
  const [wafers, setWafers] = useState<Wafer[]>([]);
  const [failures, setFailures] = useState<Failure[]>([]);
  const [files, setFiles] = useState<IngestFile[]>([]);
  const [conclusions, setConclusions] = useState<Conclusion[]>([]);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [o, w, f, file_list, c] = await Promise.all([
          get<Overview>('v1/dashboard/overview'),
          get<Wafer[]>('v1/wafers'),
          get<Failure[]>('v1/analytics/failures'),
          get<IngestFile[]>('v1/ingest/files?limit=10'),
          get<Conclusion[]>('v1/analytics/conclusions')
        ]);
        setOverview(o);
        setWafers(w);
        setFailures(f);
        setFiles(file_list);
        setConclusions(c);
      } catch (e) {
        console.error(e);
      } finally {
        setBusy(false);
      }
    };
    load();
  }, []);

  const exportCsv = () => {
    let content = 'Report Generated: ' + new Date().toISOString() + '\n\n';
    
    content += 'YIELD SUMMARY\n';
    content += 'Lot ID,Yield %,Devices Tested\n';
    overview?.trend.forEach(t => {
      content += `"${t.lot_id}",${t.yield_pct},${t.devices}\n`;
    });
    
    content += '\nWAFER FAILURE REPORT\n';
    content += 'Wafer ID,Lot ID,Yield %,Tested,Failed\n';
    wafers.forEach(w => {
      content += `"${w.wafer_id}","${w.lot_id}",${w.yield_pct},${w.devices},${w.failed}\n`;
    });

    content += '\nFAILURE ATTRIBUTION\n';
    content += 'Test Name,Pin,Failures,Failure Rate %\n';
    failures.forEach(f => {
      content += `"${f.test_name}","${f.pin_name || ''}",${f.failures},${f.failure_rate}\n`;
    });

    content += '\nENGINEERING CONCLUSIONS\n';
    content += 'Severity,Category,Wafer,Title,Evidence,Recommendation\n';
    conclusions.forEach(c => {
      content += `"${c.severity}","${c.category}","${c.affected_wafer}","${c.title}","${c.evidence}","${c.recommended_action}"\n`;
    });

    const encodedUri = encodeURI('data:text/csv;charset=utf-8,' + content);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `yieldscope_report_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const printReport = () => {
    window.print();
  };

  if (busy) return <div className="loading">Generating reports…</div>;

  return (
    <div className="reports-container">
      <header className="no-print">
        <div>
          <p className="eyebrow">INTELLIGENCE EXPORT</p>
          <h1>Reports & Recommendations</h1>
        </div>
        <div className="actions" style={{ flexDirection: 'row' }}>
          <button className="ghost" onClick={exportCsv}>Export CSV</button>
          <button className="primary" onClick={printReport}>Print / Save PDF</button>
        </div>
      </header>

      <div style={{ marginBottom: '20px', color: 'var(--mute)', fontSize: '11px' }}>
        <strong>Report Metadata: </strong> Generated at {new Date().toLocaleString()} | Source: YieldScope API | Data is live.
      </div>

      <section className="grid">
        <article className="panel" style={{ gridColumn: '1 / -1' }}>
          <Head title="Actionable Engineering Conclusions" tag={`${conclusions.length} RECOMMENDATIONS`} />
          <table className="data-table" style={{ width: '100%', textAlign: 'left', marginTop: '10px', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                <th>Wafer</th>
                <th>Severity</th>
                <th>Category</th>
                <th>Finding</th>
                <th>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {conclusions.map((c, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #1a2944' }}>
                  <td style={{ padding: '8px 0', fontWeight: 'bold' }}>{c.affected_wafer}</td>
                  <td>
                    <span style={{ padding: '2px 4px', borderRadius: '4px', background: c.severity === 'critical' ? '#ff6b6b33' : c.severity === 'warning' ? '#f0a50033' : '#4aedc433', color: c.severity === 'critical' ? 'var(--red)' : c.severity === 'warning' ? 'var(--amber)' : 'var(--mint)', fontSize: '10px', textTransform: 'uppercase' }}>
                      {c.severity}
                    </span>
                  </td>
                  <td style={{ textTransform: 'uppercase', color: 'var(--mute)', fontSize: '10px' }}>{c.category}</td>
                  <td><strong>{c.title}</strong><br/><span style={{ color: 'var(--mute)' }}>{c.evidence}</span></td>
                  <td style={{ fontStyle: 'italic' }}>{c.recommended_action}</td>
                </tr>
              ))}
              {conclusions.length === 0 && <tr><td colSpan={5} style={{ padding: '10px 0', color: 'var(--mute)' }}>No conclusions currently available.</td></tr>}
            </tbody>
          </table>
        </article>

        <article className="panel">
          <Head title="Wafer Failure Report" tag="WAFER AGGREGATION" />
          <table className="data-table" style={{ width: '100%', textAlign: 'left', marginTop: '10px', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                <th>Wafer ID</th>
                <th>Yield</th>
                <th>Failures</th>
              </tr>
            </thead>
            <tbody>
              {wafers.slice(0, 8).map(w => (
                <tr key={w.wafer_id} style={{ borderBottom: '1px solid #1a2944' }}>
                  <td style={{ padding: '8px 0' }}>{w.wafer_id}</td>
                  <td className={w.yield_pct >= 95 ? 'ok' : 'bad'}>{w.yield_pct}%</td>
                  <td>{w.failed.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="panel">
          <Head title="Failure Attribution Report" tag="TOP DEFECTS" />
          <table className="data-table" style={{ width: '100%', textAlign: 'left', marginTop: '10px', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                <th>Test</th>
                <th>Failures</th>
                <th>Rate</th>
              </tr>
            </thead>
            <tbody>
              {failures.slice(0, 8).map((f, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #1a2944' }}>
                  <td style={{ padding: '8px 0' }}>{f.test_name}</td>
                  <td className="bad">{f.failures}</td>
                  <td>{f.failure_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>
    </div>
  );
}
