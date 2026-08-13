import React, { useState, useEffect } from 'react';
import { registerProvider, checkProviderUpdates, listProviders } from '../api/client';

const ProviderDashboard = ({ onMigrationRequired }) => {
  const [providers, setProviders] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastDecisions, setLastDecisions] = useState({});

  // Registration form state
  const [name, setName] = useState('');
  const [specUrl, setSpecUrl] = useState('');
  const [repoPath, setRepoPath] = useState('');

  const loadProviders = async () => {
    try {
      const data = await listProviders();
      setProviders(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await registerProvider(name, specUrl, repoPath);
      await loadProviders();
      setName('');
      setSpecUrl('');
      setRepoPath('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fillDemoPreset = (type) => {
    setName(type === 'A' ? 'Demo API (Affected Consumer)' : 'Demo API (Unused Breaking)');
    setSpecUrl('http://localhost:8080/demo/v1.json');
    setRepoPath(window.location.origin.includes('localhost') ? 'demo/consumer_app' : 'demo/consumer_app');
  };

  const handleCheck = async (provider) => {
    setIsLoading(true);
    setError(null);
    try {
      const decision = await checkProviderUpdates(provider.id);
      setLastDecisions(prev => ({ ...prev, [provider.id]: decision }));
      await loadProviders();
      if (decision.status === 'MIGRATION_REQUIRED') {
        onMigrationRequired(provider, decision);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'MIGRATION_REQUIRED':
        return <span className="bg-rose-500/20 text-rose-300 border border-rose-500/40 px-3 py-1 rounded-full text-xs font-semibold animate-pulse">MIGRATION REQUIRED</span>;
      case 'NO_MIGRATION_REQUIRED':
        return <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-3 py-1 rounded-full text-xs font-semibold">NO MIGRATION REQUIRED (No Consumer Impact)</span>;
      case 'REVIEW_REQUIRED':
        return <span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 px-3 py-1 rounded-full text-xs font-semibold">REVIEW REQUIRED</span>;
      case 'UNCHANGED':
        return <span className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 px-3 py-1 rounded-full text-xs font-medium">UNCHANGED</span>;
      case 'INITIALIZED':
        return <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-3 py-1 rounded-full text-xs font-medium">INITIALIZED (Baseline Set)</span>;
      case 'CHECK_FAILED':
        return <span className="bg-rose-900/30 text-rose-400 border border-rose-800 px-3 py-1 rounded-full text-xs font-medium">CHECK FAILED</span>;
      default:
        return <span className="bg-slate-700 text-slate-300 px-3 py-1 rounded-full text-xs font-medium">{status}</span>;
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Registration Panel */}
      <div className="glass-panel p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-slate-100">Register API Provider</h2>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => fillDemoPreset('A')}
              className="text-xs bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/30 px-3 py-1.5 rounded-lg transition-colors"
            >
              + Quick Demo Preset
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/50 rounded-lg text-rose-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Provider Name</label>
              <input type="text" className="input-field" value={name} onChange={e => setName(e.target.value)} required placeholder="e.g. Payment & User Service" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">OpenAPI Spec URL</label>
              <input type="url" className="input-field" value={specUrl} onChange={e => setSpecUrl(e.target.value)} required placeholder="http://localhost:8080/demo/v1.json" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Local Consumer Repository Path</label>
            <input type="text" className="input-field" value={repoPath} onChange={e => setRepoPath(e.target.value)} required placeholder="demo/consumer_app" />
          </div>
          <button type="submit" disabled={isLoading} className="btn-primary w-full py-2.5 font-medium">
            {isLoading ? 'Registering...' : 'Register Monitored Provider'}
          </button>
        </form>
      </div>

      {/* Monitored Providers Panel */}
      <div className="glass-panel p-6">
        <h2 className="text-xl font-semibold text-slate-100 mb-6">Monitored API Providers</h2>
        {providers.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-slate-700/50 rounded-xl">
            <p className="text-slate-400 text-sm">No providers registered yet.</p>
            <p className="text-slate-500 text-xs mt-1">Use the "Quick Demo Preset" above to load hackathon fixtures.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {providers.map(p => {
              const decision = lastDecisions[p.id];
              return (
                <div key={p.id} className="bg-slate-900/70 border border-slate-700/60 rounded-xl p-5 shadow-inner">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-bold text-slate-100">{p.name}</h3>
                        {getStatusBadge(p.status)}
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-xs text-slate-400 font-mono">
                        <p><span className="text-slate-500">Spec:</span> {p.spec_url}</p>
                        <p><span className="text-slate-500">Repo:</span> {p.repository_path}</p>
                        <p><span className="text-slate-500">Baseline ID:</span> {p.last_processed_snapshot_id || 'None'}</p>
                        {p.pending_snapshot_id && (
                          <p><span className="text-amber-400">Pending Migration ID:</span> {p.pending_snapshot_id}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <button 
                        onClick={() => handleCheck(p)} 
                        disabled={isLoading}
                        className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all shadow-md ${
                          p.status === 'MIGRATION_REQUIRED' 
                            ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/20 animate-pulse' 
                            : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20'
                        }`}
                      >
                        {isLoading ? 'Checking...' : p.status === 'MIGRATION_REQUIRED' ? 'Generate & Apply Migration' : 'Check for Provider Release'}
                      </button>
                    </div>
                  </div>

                  {decision && (
                    <div className="mt-4 pt-3 border-t border-slate-800 text-xs">
                      <span className="text-slate-400 font-medium">Latest Decision Rationale: </span>
                      <span className="text-slate-200">{decision.reason}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProviderDashboard;
