import React from 'react';

const RepositoriesView = ({ providers, onCheckProvider }) => {
  return (
    <div className="space-y-8 animate-fade-in">
      <div className="glass-panel p-6 border border-slate-800">
        <h2 className="text-xl font-semibold text-slate-100 mb-2 flex items-center gap-2">
          <span>📁</span> Monitored Consumer Repositories
        </h2>
        <p className="text-sm text-slate-400">
          Consumer Python codebases monitored by API-Healer for contract breaking change impacts.
        </p>
      </div>

      <div className="glass-panel p-6 border border-slate-800">
        {providers.length === 0 ? (
          <div className="p-12 text-center border border-dashed border-slate-800 rounded-xl">
            <p className="text-slate-400 text-sm">No consumer repositories registered yet.</p>
            <p className="text-slate-500 text-xs mt-1">Register a provider in the Dashboard tab to monitor a local repository.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {providers.map((p) => (
              <div key={p.id} className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <h3 className="text-base font-bold text-slate-100 font-mono">{p.repository_path}</h3>
                    <span className="bg-slate-800 text-slate-300 border border-slate-700 px-2.5 py-0.5 rounded text-xs">
                      Default Branch: main
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-xs text-slate-400 font-mono">
                    <p><span className="text-slate-500">Provider:</span> <span className="text-indigo-300">{p.name}</span></p>
                    <p><span className="text-slate-500">Spec URL:</span> {p.spec_url}</p>
                    <p><span className="text-slate-500">Baseline Snapshot:</span> {p.last_processed_snapshot_id || 'None'}</p>
                    <p><span className="text-slate-500">Status:</span> <span className="text-slate-200">{p.status}</span></p>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <button
                    onClick={() => onCheckProvider(p)}
                    className="px-4 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold transition-colors"
                  >
                    Check Provider Status
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RepositoriesView;
