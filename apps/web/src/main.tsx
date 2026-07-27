import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Sidebar } from './components/Sidebar';
import MissionControl from './pages/MissionControl';
import IngestData from './pages/IngestData';
import WaferExplorer from './pages/WaferExplorer';
import FailureIntelligence from './pages/FailureIntelligence';
import YieldTrends from './pages/YieldTrends';
import AlertsCenter from './pages/AlertsCenter';
import DataQuality from './pages/DataQuality';
import Reports from './pages/Reports';
import { API_BASE } from './lib/api';
import './style.css';

function App() {
  const [page, setPage] = useState('Mission Control');
  const [toast, setToast] = useState('');
  const [navWaferId, setNavWaferId] = useState<string | undefined>(undefined);

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3500);
  };

  const seed = async () => {
    try {
      const x = await fetch(`${API_BASE}/v1/demo/seed`, { method: 'POST' });
      if (!x.ok) throw Error();
      notify('Demo lot ingested successfully. Refreshing view...');
      setTimeout(() => window.location.reload(), 1500);
    } catch {
      notify('Demo seed failed — check that API services are running.');
    }
  };

  const handleNavigateWithWafer = (waferId: string) => {
    setNavWaferId(waferId);
    // Let the Wafer Explorer pick up the new waferId via props on next render
  };

  const renderPage = () => {
    switch (page) {
      case 'Ingest Data':
        return <IngestData notify={notify} setPage={setPage} />;
      case 'Mission Control':
        return <MissionControl setPage={setPage} setWaferId={handleNavigateWithWafer} />;
      case 'Wafer Explorer':
        return (
          <WaferExplorer
            initialWaferId={navWaferId}
            setPage={setPage}
          />
        );
      case 'Failure Intelligence':
        return <FailureIntelligence setPage={setPage} />;
      case 'Yield Trends':
        return <YieldTrends />;
      case 'Alerts Center':
        return <AlertsCenter setPage={setPage} setWaferId={handleNavigateWithWafer} notify={notify} />;
      case 'Data Quality':
        return <DataQuality />;
      case 'Reports':
        return <Reports />;
      default:
        return <div>Page not found</div>;
    }
  };

  return (
    <div className="app">
      <Sidebar page={page} setPage={setPage} />
      <main>
        {/* We keep seed in header if it's Mission Control, else hide or provide a global button? 
            The requirements didn't ask for a global seed button, but the original UI had it on Mission Control. 
            We'll add a minimal global header if needed, but the pages have their own headers. 
            I'll add the seed button into the main area globally, or just top right. */}
        {page === 'Mission Control' && (
          <div style={{ position: 'absolute', top: '28px', right: '38px', zIndex: 10 }}>
            <button className="primary" onClick={seed}>Seed Demo</button>
          </div>
        )}
        {renderPage()}
      </main>
      {toast && (
        <div className="toast">
          {toast}
          <button onClick={() => setToast('')}>×</button>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
