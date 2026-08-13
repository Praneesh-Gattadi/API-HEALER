import React, { useState } from 'react';

const DiffViewer = ({ result, onApply, isLoading, isApplied }) => {
  const [acknowledged, setAcknowledged] = useState(false);

  if (!result) return null;

  const renderDiffLine = (line, idx) => {
    let bgColor = 'bg-transparent';
    let textColor = 'text-slate-300';
    
    if (line.startsWith('+') && !line.startsWith('+++')) {
      bgColor = 'bg-emerald-900/30';
      textColor = 'text-emerald-300';
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      bgColor = 'bg-rose-900/30';
      textColor = 'text-rose-300';
    } else if (line.startsWith('@@')) {
      bgColor = 'bg-indigo-900/20';
      textColor = 'text-indigo-300';
    }

    return (
      <div key={idx} className={`${bgColor} px-4 py-0.5 whitespace-pre font-mono text-sm ${textColor}`}>
        {line}
      </div>
    );
  };

  return (
    <div className="glass-panel p-6 animate-fade-in mt-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-slate-100">
          {isApplied ? 'Transformation Result' : 'Transformation Preview (Dry Run)'}
        </h2>
        {result.success ? (
          <span className="text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-3 py-1 rounded-full text-xs">
            Success
          </span>
        ) : (
          <span className="text-rose-400 bg-rose-400/10 border border-rose-400/20 px-3 py-1 rounded-full text-xs">
            Validation Failed
          </span>
        )}
      </div>

      {result.errors && result.errors.length > 0 && (
        <div className="mb-6 bg-rose-900/20 border border-rose-500/30 rounded-lg p-4">
          <h3 className="text-rose-400 font-medium mb-2 text-sm">Errors</h3>
          <ul className="list-disc list-inside text-rose-300/80 text-sm space-y-1">
            {result.errors.map((err, i) => <li key={i}>{err}</li>)}
          </ul>
        </div>
      )}

      {result.warnings && result.warnings.length > 0 && (
        <div className="mb-6 bg-amber-900/20 border border-amber-500/30 rounded-lg p-4">
          <h3 className="text-amber-400 font-medium mb-2 text-sm">Review Required (Skipped)</h3>
          <ul className="list-disc list-inside text-amber-300/80 text-sm space-y-1 font-mono">
            {result.warnings.map((w, i) => <li key={i}>{w.message}</li>)}
          </ul>
        </div>
      )}

      {result.changes && result.changes.length > 0 ? (
        <div className="space-y-6 mb-8">
          {result.changes.map((change, idx) => (
            <div key={idx} className="rounded-lg overflow-hidden border border-slate-700/50 bg-slate-900/80 shadow-inner">
              <div className="bg-slate-800/80 px-4 py-2 border-b border-slate-700/50 flex items-center justify-between">
                <span className="text-slate-300 font-mono text-sm">{change.file_path}</span>
              </div>
              <div className="overflow-x-auto py-2">
                {change.diff.split('\n').map((line, i) => renderDiffLine(line, i))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-slate-500 mb-8 border border-dashed border-slate-700/50 rounded-lg">
          No files were modified.
        </div>
      )}

      {!isApplied && result.success && (
        <div className="flex items-center justify-between pt-4 border-t border-slate-700/50">
          <label className="flex items-center gap-3 cursor-pointer group">
            <input 
              type="checkbox" 
              className="w-5 h-5 rounded border-slate-600 bg-slate-800 text-indigo-500 focus:ring-indigo-500/50 cursor-pointer"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
            />
            <span className="text-sm text-slate-300 group-hover:text-slate-200 transition-colors">
              I have reviewed these proposed changes and acknowledge they will modify my local repository.
            </span>
          </label>
          <button
            onClick={onApply}
            disabled={!acknowledged || isLoading}
            className="btn-danger"
          >
            {isLoading ? 'Applying...' : 'Apply Changes'}
          </button>
        </div>
      )}
    </div>
  );
};

export default DiffViewer;
