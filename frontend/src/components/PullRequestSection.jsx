import React from 'react';

const PullRequestSection = ({ transformResult, plan, repoRoot }) => {
  const isApplied = transformResult && transformResult.success;

  return (
    <div className="glass-panel p-6 animate-fade-in mt-6 border border-slate-700/60">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
            <span>🐙</span> GitHub Pull Request Integration
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Automated PR creation placeholder & developer review handoff
          </p>
        </div>
        <span className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-3 py-1 rounded-full text-xs font-medium">
          Integration Placeholder
        </span>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <span className="text-xs text-slate-500 font-mono block">Proposed Pull Request Title</span>
            <span className="text-sm font-semibold text-slate-200">
              {plan ? `fix(api): ${plan.summary}` : 'fix(api): automated CST migration for API contract update'}
            </span>
          </div>
          <span className={`text-xs px-2.5 py-1 rounded font-mono ${
            isApplied ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-400 border border-slate-700'
          }`}>
            {isApplied ? 'READY FOR PR' : 'AWAITING APPLY'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono text-slate-400">
          <div>
            <span className="text-slate-500 block">Target Repository:</span>
            <span className="text-slate-200">{repoRoot || 'demo/consumer_app'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Branch Strategy:</span>
            <span className="text-indigo-400">main ← fix/api-healer-migration</span>
          </div>
        </div>

        {/* Informational Banner */}
        <div className="p-3 bg-indigo-950/30 border border-indigo-500/20 rounded-lg text-xs text-indigo-300/80">
          ℹ️ Direct GitHub PR creation API is not exposed by the current backend. In production mode, API-Healer pushes the verified branch and opens a Pull Request automatically.
        </div>

        <div className="flex justify-end pt-2">
          <button
            disabled={!isApplied}
            onClick={() => alert('GitHub PR creation endpoint is an unexposed backend feature. Local source transformations were successfully applied.')}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed border border-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors flex items-center gap-2"
          >
            <span>🔗</span> Open Pull Request (Simulated)
          </button>
        </div>
      </div>
    </div>
  );
};

export default PullRequestSection;
