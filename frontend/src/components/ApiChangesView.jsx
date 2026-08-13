import React, { useState } from 'react';
import { calculateDiff } from '../api/client';

const ApiChangesView = ({ onGeneratePlanFromDiff }) => {
  const [oldSpecJson, setOldSpecJson] = useState(JSON.stringify({
    openapi: "3.0.0",
    info: { title: "Demo API", version: "1.0.0" },
    paths: {
      "/api/v1/users": {
        get: {
          parameters: [{ name: "user_id", in: "query", required: true, schema: { type: "string" } }],
          responses: { "200": { description: "User details", content: { "application/json": { schema: { type: "object", properties: { user_id: { type: "string" } } } } } } }
        }
      }
    }
  }, null, 2));

  const [newSpecJson, setNewSpecJson] = useState(JSON.stringify({
    openapi: "3.0.0",
    info: { title: "Demo API", version: "2.0.0" },
    paths: {
      "/api/v1/users": {
        get: {
          parameters: [{ name: "id", in: "query", required: true, schema: { type: "string" } }],
          responses: { "200": { description: "User details", content: { "application/json": { schema: { type: "object", properties: { id: { type: "string" } } } } } } }
        }
      }
    }
  }, null, 2));

  const [diffResult, setDiffResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCalculateDiff = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const oldParsed = JSON.parse(oldSpecJson);
      const newParsed = JSON.parse(newSpecJson);
      const result = await calculateDiff(oldParsed, newParsed);
      setDiffResult(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to calculate OpenAPI spec diff');
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'BREAKING':
        return <span className="bg-rose-500/20 text-rose-300 border border-rose-500/40 px-2.5 py-0.5 rounded text-[11px] font-semibold">BREAKING CHANGE</span>;
      case 'WARNING':
        return <span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2.5 py-0.5 rounded text-[11px] font-semibold">WARNING</span>;
      default:
        return <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-2.5 py-0.5 rounded text-[11px] font-semibold">INFO</span>;
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Overview Header */}
      <div className="glass-panel p-6 border border-slate-800">
        <h2 className="text-xl font-semibold text-slate-100 mb-2 flex items-center gap-2">
          <span>⚡</span> OpenAPI Contract Change Detection
        </h2>
        <p className="text-sm text-slate-400">
          Compare OpenAPI JSON/YAML specifications to detect property renames, field removals, and endpoint changes.
        </p>

        {error && (
          <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/50 rounded-lg text-rose-400 text-sm">
            {error}
          </div>
        )}

        {/* JSON Specs Editors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1 font-mono">Baseline OpenAPI Spec (Old)</label>
            <textarea
              rows={8}
              value={oldSpecJson}
              onChange={(e) => setOldSpecJson(e.target.value)}
              className="input-field font-mono text-xs"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1 font-mono">Target OpenAPI Spec (New)</label>
            <textarea
              rows={8}
              value={newSpecJson}
              onChange={(e) => setNewSpecJson(e.target.value)}
              className="input-field font-mono text-xs"
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={handleCalculateDiff}
            disabled={isLoading}
            className="btn-primary py-2.5 px-6 text-sm font-semibold flex items-center gap-2"
          >
            {isLoading ? 'Comparing Specs...' : 'Calculate OpenAPI Contract Diff'}
          </button>
        </div>
      </div>

      {/* Diff Results List */}
      {diffResult && (
        <div className="glass-panel p-6 border border-slate-800 animate-fade-in">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold text-slate-100">Detected Contract Changes</h3>
              <p className="text-xs text-slate-400 mt-0.5">{diffResult.changes.length} structural changes identified</p>
            </div>
            {onGeneratePlanFromDiff && (
              <button
                onClick={() => onGeneratePlanFromDiff(JSON.parse(oldSpecJson), JSON.parse(newSpecJson))}
                className="btn-primary py-2 px-4 text-xs font-medium"
              >
                Generate Migration Plan →
              </button>
            )}
          </div>

          {diffResult.changes.length === 0 ? (
            <div className="p-8 text-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-sm">
              No structural API changes detected.
            </div>
          ) : (
            <div className="space-y-4">
              {diffResult.changes.map((change, idx) => (
                <div key={idx} className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 font-mono text-xs">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getSeverityBadge(change.severity)}
                      <span className="text-indigo-400 font-semibold">{change.type}</span>
                    </div>
                    <span className="text-slate-500">{change.path}</span>
                  </div>
                  <p className="text-slate-300 font-sans text-xs mb-3">{change.description}</p>
                  
                  {(change.old_value || change.new_value) && (
                    <div className="bg-slate-950 p-2.5 rounded border border-slate-800 flex items-center gap-4 text-xs">
                      {change.old_value && <span className="text-rose-400">Old: {change.old_value}</span>}
                      {change.old_value && change.new_value && <span className="text-slate-600">→</span>}
                      {change.new_value && <span className="text-emerald-400">New: {change.new_value}</span>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ApiChangesView;
