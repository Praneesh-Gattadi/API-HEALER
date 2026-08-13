import React from 'react';

const PlanViewer = ({ plan, onDryRun, isLoading }) => {
  if (!plan) return null;

  const getRiskColor = (level) => {
    switch (level.toUpperCase()) {
      case 'HIGH': return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      case 'MEDIUM': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'LOW': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getActionTypeColor = (type) => {
    if (type.includes('remove') || type === 'review_required') return 'text-rose-400 bg-rose-400/10 border-rose-400/20';
    if (type.includes('rename') || type.includes('update')) return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
    return 'text-indigo-400 bg-indigo-400/10 border-indigo-400/20';
  };

  return (
    <div className="glass-panel p-6 animate-fade-in mt-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-100 flex items-center gap-3">
            Migration Plan Ready
            <span className={`text-xs px-2 py-1 rounded-full border ${getRiskColor(plan.risk_level)}`}>
              {plan.risk_level} RISK
            </span>
          </h2>
          <p className="text-slate-400 mt-2 text-sm">{plan.summary}</p>
        </div>
        <div className="text-right">
          <p className="text-slate-400 text-sm">{plan.actions.length} Actions Proposed</p>
        </div>
      </div>

      <div className="space-y-4 mb-8">
        {plan.actions.map((action, idx) => (
          <div key={idx} className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-mono px-2 py-1 rounded border ${getActionTypeColor(action.action_type)}`}>
                    {action.action_type}
                  </span>
                  <span className="text-slate-300 font-medium text-sm">{action.description}</span>
                </div>
                
                <div className="text-xs text-slate-500 grid grid-cols-2 gap-x-8 gap-y-1 mt-2">
                  <p><span className="text-slate-600">Path:</span> <span className="font-mono">{action.affected_path}</span></p>
                  {action.old_name && <p><span className="text-slate-600">Old:</span> <span className="font-mono text-rose-300">{action.old_name}</span></p>}
                  {action.new_name && <p><span className="text-slate-600">New:</span> <span className="font-mono text-emerald-300">{action.new_name}</span></p>}
                </div>
                
                <p className="text-xs text-slate-400 mt-2 bg-slate-800/50 p-2 rounded border border-slate-700/30">
                  <span className="text-slate-500">Rationale: </span>{action.rationale}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end pt-4 border-t border-slate-700/50">
        <button
          onClick={onDryRun}
          disabled={isLoading}
          className="btn-primary flex items-center gap-2"
        >
          {isLoading ? 'Running preview...' : 'Preview Changes / Dry Run'}
        </button>
      </div>
    </div>
  );
};

export default PlanViewer;
