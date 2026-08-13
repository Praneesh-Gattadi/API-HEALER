import React, { useState, useEffect } from 'react';
import { registerProvider, checkProviderUpdates, listProviders } from '../api/client';

const ProviderDashboard = ({ onMigrationRequired }) => {
  const [providers, setProviders] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
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

  const handleCheck = async (provider) => {
    setIsLoading(true);
    setError(null);
    try {
      const decision = await checkProviderUpdates(provider.id);
      await loadProviders();
      if (decision.status === 'MIGRATION_REQUIRED') {
        onMigrationRequired(provider, decision);
      } else {
        alert(`Check complete. Status: ${decision.status}\nReason: ${decision.reason}`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="glass-panel p-6">
        <h2 className="text-xl font-semibold text-slate-100 mb-6">Register API Provider</h2>
        {error && (
          <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/50 rounded-lg text-rose-400 text-sm">
            {error}
          </div>
        )}
        <form onSubmit={handleRegister} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Provider Name</label>
              <input type="text" className="input-field" value={name} onChange={e => setName(e.target.value)} required placeholder="e.g. Acme API" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">OpenAPI Spec URL</label>
              <input type="url" className="input-field" value={specUrl} onChange={e => setSpecUrl(e.target.value)} required placeholder="https://api.acme.com/openapi.json" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Local Repository Path</label>
            <input type="text" className="input-field" value={repoPath} onChange={e => setRepoPath(e.target.value)} required placeholder="/absolute/path/to/repo" />
          </div>
          <button type="submit" disabled={isLoading} className="btn-primary w-full py-2">
            {isLoading ? 'Registering...' : 'Register Provider'}
          </button>
        </form>
      </div>

      <div className="glass-panel p-6">
        <h2 className="text-xl font-semibold text-slate-100 mb-6">Monitored Providers</h2>
        {providers.length === 0 ? (
          <p className="text-slate-400 text-sm text-center">No providers registered yet.</p>
        ) : (
          <div className="space-y-4">
            {providers.map(p => (
              <div key={p.id} className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-4 flex justify-between items-center">
                <div>
                  <h3 className="text-lg font-medium text-slate-200">{p.name}</h3>
                  <p className="text-xs text-slate-400 font-mono mt-1">{p.spec_url}</p>
                  <p className="text-xs text-slate-400 mt-1">Status: <span className="text-indigo-400">{p.status}</span></p>
                </div>
                <button 
                  onClick={() => handleCheck(p)} 
                  disabled={isLoading}
                  className="px-4 py-2 bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 border border-indigo-500/30 rounded-lg transition-colors text-sm font-medium"
                >
                  {p.status === 'MIGRATION_REQUIRED' ? 'Resume Migration' : 'Check for Updates'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProviderDashboard;
