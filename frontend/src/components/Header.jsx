import React, { useEffect, useState } from 'react';
import { checkBackendHealth } from '../api/client';

const Header = ({ activeTab }) => {
  const [isConnected, setIsConnected] = useState(null);

  const verifyConnection = async () => {
    const status = await checkBackendHealth();
    setIsConnected(status);
  };

  useEffect(() => {
    verifyConnection();
    const interval = setInterval(verifyConnection, 10000);
    return () => clearInterval(interval);
  }, []);

  const getTabTitle = () => {
    switch (activeTab) {
      case 'DASHBOARD':
        return { title: 'Dashboard Overview', subtitle: 'Real-time API provider monitoring and consumer impact analysis' };
      case 'API_CHANGES':
        return { title: 'Detected API Changes', subtitle: 'OpenAPI contract diffs, severity badges, and field mapping' };
      case 'MIGRATIONS':
        return { title: 'Migration Workspace', subtitle: 'Structured plans, LibCST dry runs, CST validation & PR preview' };
      case 'REPOSITORIES':
        return { title: 'Monitored Repositories', subtitle: 'Consumer Python codebases linked to API provider baselines' };
      default:
        return { title: 'Control Panel', subtitle: 'LLM-Assisted CST Agent for Automated API Migrations' };
    }
  };

  const { title, subtitle } = getTabTitle();

  return (
    <header className="mb-6 pb-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h2 className="text-2xl font-bold text-slate-100 tracking-tight">{title}</h2>
        <p className="text-sm text-slate-400 mt-1">{subtitle}</p>
      </div>

      <div className="flex items-center gap-3">
        {isConnected === null ? (
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700 text-slate-400 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span>
            Checking Backend...
          </span>
        ) : isConnected ? (
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-medium shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            ● Backend Connected
          </span>
        ) : (
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-medium shadow-sm">
            <span className="w-2 h-2 rounded-full bg-rose-500"></span>
            ● Backend Disconnected
          </span>
        )}
      </div>
    </header>
  );
};

export default Header;
