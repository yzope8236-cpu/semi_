import React, { useEffect, useState } from 'react';
import { get, IngestFile, ValidationEvent } from '../lib/api';
import { Head } from './MissionControl';

export default function DataQuality() {
  const [files, setFiles] = useState<IngestFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<IngestFile>();
  const [events, setEvents] = useState<ValidationEvent[]>([]);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const f = await get<IngestFile[]>('v1/ingest/files?limit=100');
        setFiles(f);
      } catch (e) {
        console.error(e);
      } finally {
        setBusy(false);
      }
    };
    load();
  }, []);

  const selectFile = async (f: IngestFile) => {
    setSelectedFile(f);
    try {
      const evs = await get<ValidationEvent[]>(`v1/quality/files/${f.file_id}`);
      setEvents(evs);
    } catch (e) {
      console.error(e);
      setEvents([]);
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === 'validated') return <span style={{ color: 'var(--mint)' }}>✓ Validated</span>;
    if (status === 'requires_review') return <span style={{ color: 'var(--amber)' }}>⚠ Requires Review</span>;
    return <span style={{ color: 'var(--red)' }}>⊗ Invalid</span>;
  };

  if (busy) return <div className="loading">Loading data lineage…</div>;

  const hasMissingFar = events.some(e => e.code === 'MISSING_FAR');
  const hasMissingMir = events.some(e => e.code === 'MISSING_MIR');
  const hasMissingWir = events.some(e => e.code === 'MISSING_WIR');
  const mandatoryViolated = hasMissingFar || hasMissingMir || hasMissingWir;

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">PARSER STATUS & LINEAGE</p>
          <h1>Data Quality</h1>
        </div>
      </header>

      <section className="panel" style={{ marginBottom: '20px' }}>
        <Head title="Ingest Pipeline History" tag={`${files.length} FILES`} />
        
        <div style={{ overflowX: 'auto', marginTop: '15px' }}>
          <table className="data-table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                <th style={{ padding: '10px 0' }}>File Name</th>
                <th>Status</th>
                <th>Format</th>
                <th>Parser / Mapping</th>
                <th>SHA-256</th>
                <th style={{ minWidth: '74px' }}>Records</th>
                <th style={{ minWidth: '110px' }}>Validation Errors</th>
                <th style={{ minWidth: '150px' }}>Received At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {files.map(f => (
                <tr key={f.file_id} style={{ borderBottom: '1px solid #1a2944', background: selectedFile?.file_id === f.file_id ? 'rgba(74,237,196,0.05)' : 'transparent' }}>
                  <td style={{ padding: '10px 0', fontWeight: 'bold' }}>{f.file_name}</td>
                  <td>{getStatusBadge(f.status)}</td>
                  <td>{f.source_format}</td>
                  <td>{f.parser_version} / {f.mapping_version}</td>
                  <td title={f.sha256} style={{ fontFamily: 'DM Mono', maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.sha256}</td>
                  <td>{f.records_parsed.toLocaleString()}</td>
                  <td className={f.error_count > 0 ? 'bad' : 'ok'}>{f.error_count} {f.error_count === 0 ? '(none)' : ''}</td>
                  <td>{new Date(f.received_at).toLocaleString()}</td>
                  <td>
                    <button className="ghost" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => selectFile(f)}>Inspect</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {files.length === 0 && <p className="muted" style={{ padding: '20px 0', textAlign: 'center' }}>No ingested files found.</p>}
        </div>
      </section>

      {selectedFile && (
        <section className="grid lower">
          <article className="panel quality">
            <Head title="Mandatory Record Compliance" tag="FAR / MIR / WIR" />
            {!mandatoryViolated ? (
              <p style={{ marginTop: '15px' }} className="ok">✓ No mandatory-record violation reported.</p>
            ) : (
              <div style={{ marginTop: '15px' }}>
                <p><b className={!hasMissingFar ? 'ok' : 'bad'}>{!hasMissingFar ? '✓' : '⊗'}</b> FAR (File Attributes Record)</p>
                <p><b className={!hasMissingMir ? 'ok' : 'bad'}>{!hasMissingMir ? '✓' : '⊗'}</b> MIR (Master Information Record)</p>
                <p><b className={!hasMissingWir ? 'ok' : 'bad'}>{!hasMissingWir ? '✓' : '⊗'}</b> WIR (Wafer Information Record)</p>
              </div>
            )}
            
            <div style={{ marginTop: '20px', borderTop: '1px solid var(--line)', paddingTop: '15px' }}>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '12px', color: 'var(--mute)' }}>File Details</h4>
              <dl style={{ fontSize: '11px' }}>
                <dt>Tester ID</dt><dd>{selectedFile.tester_id || 'N/A'}</dd>
                <dt>Program</dt><dd>{selectedFile.program_name || 'N/A'}</dd>
                <dt>Lot ID</dt><dd>{selectedFile.lot_id || 'N/A'}</dd>
              </dl>
            </div>
          </article>

          <article className="panel">
            <Head title="Validation Events" tag={`${events.length} EVENTS`} />
            {events.length === 0 ? (
              <p className="muted" style={{ marginTop: '15px' }}>No quality findings or validation errors.</p>
            ) : (
              <div style={{ maxHeight: '300px', overflowY: 'auto', marginTop: '15px' }}>
                <table className="data-table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: '11px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--line)' }}>
                      <th style={{ padding: '5px 0' }}>Severity</th>
                      <th>Code</th>
                      <th>Message</th>
                      <th>Record #</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((e, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #1a2944' }}>
                        <td style={{ padding: '8px 0', color: e.severity === 'error' ? 'var(--red)' : 'var(--amber)' }}>{e.severity.toUpperCase()}</td>
                        <td style={{ fontFamily: 'DM Mono' }}>{e.code}</td>
                        <td>{e.message}</td>
                        <td>{e.record_number > 0 ? e.record_number : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        </section>
      )}
    </>
  );
}
