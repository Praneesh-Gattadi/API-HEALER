import React from 'react';
import ProviderDashboard from './ProviderDashboard';

const DashboardView = ({ providers, onMigrationRequired, onSelectTab, activeMigration }) => {
  const totalProviders = providers.length;
  const pendingMigrations = providers.filter(p => p.status === 'MIGRATION_REQUIRED').length;
  const initializedProviders = providers.filter(p => p.status === 'INITIALIZED').length;
  const unchangedProviders = providers.filter(p => p.status === 'UNCHANGED').length;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Monitored Providers</span>
            <span>📡</span>
          </div>
          <div className="text-3xl font-extrabold text-white tracking-tight">{totalProviders}</div>
          <p className="text-[11px] text-slate-500 mt-1">{initializedProviders} initialized baselines</p>
        </div>

        <div className="glass-panel p-5 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Pending Migrations</span>
            <span>🚨</span>
          </div>
          <div className="text-3xl font-extrabold text-rose-400 tracking-tight">{pendingMigrations}</div>
          <p className="text-[11px] text-slate-500 mt-1">Requires consumer code healing</p>
        </div>

        <div className="glass-panel p-5 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Up to Date</span>
            <span>✅</span>
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 tracking-tight">{unchangedProviders}</div>
          <p className="text-[11px] text-slate-500 mt-1">No structural diffs detected</p>
        </div>

        <div className="glass-panel p-5 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>MVP Target Field</span>
            <span>🎯</span>
          </div>
          <div className="text-xl font-bold font-mono text-indigo-400 tracking-tight">user_id → id</div>
          <p className="text-[11px] text-slate-500 mt-1">LibCST AST keyword/arg rename</p>
        </div>
      </div>

      {/* Hero Section: Active Migration Story */}
      <div className="glass-panel p-6 border-l-4 border-l-indigo-500 border border-slate-700/60 shadow-2xl relative overflow-hidden">
        <div className="absolute -right-12 -bottom-12 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold">
              <span>⚡</span> Active MVP Migration Scenario
            </div>

            <h2 className="text-2xl font-extrabold text-white tracking-tight">
              API Field Rename: <span className="font-mono text-rose-300">user_id</span> → <span className="font-mono text-emerald-300">id</span>
            </h2>

            <p className="text-sm text-slate-300 leading-relaxed">
              API-Healer monitors upstream OpenAPI contracts, detects breaking field renames, runs AST-level consumer impact analysis via LibCST, and safely updates Python codebases preserving formatting and comments.
            </p>

            <div className="flex flex-wrap gap-4 text-xs font-mono text-slate-400 pt-1">
              <span>Target Repo: <span className="text-slate-200">demo/consumer_app</span></span>
              <span>•</span>
              <span>Engine: <span className="text-indigo-300">LibCST CST Visitor</span></span>
              <span>•</span>
              <span>Planner: <span className="text-cyan-300">Gemini / Fallback</span></span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row md:flex-col gap-3 shrink-0">
            <button
              onClick={() => onSelectTab('MIGRATIONS')}
              className="btn-primary py-3 px-6 text-sm font-semibold flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30"
            >
              <span>🚀</span> Launch Migration Workspace
            </button>
            <button
              onClick={() => onSelectTab('API_CHANGES')}
              className="btn-secondary py-2.5 px-4 text-xs font-medium text-center"
            >
              Inspect OpenAPI Diffs
            </button>
          </div>
        </div>
      </div>

      {/* Monitored Providers Component */}
      <ProviderDashboard onMigrationRequired={onMigrationRequired} />
    </div>
  );
};

export default DashboardView;
