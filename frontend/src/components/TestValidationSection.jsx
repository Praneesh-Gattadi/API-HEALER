import React from 'react';

const TestValidationSection = ({ transformResult }) => {
  return (
    <div className="glass-panel p-6 animate-fade-in mt-6 border border-slate-700/60">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
            <span>🛡️</span> Validation & Code Integrity
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            LibCST AST syntax validation, transformation safety checks & test runner status
          </p>
        </div>
        <div>
          {transformResult ? (
            transformResult.success ? (
              <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-3 py-1 rounded-full text-xs font-semibold">
                ✅ CST Validation Passed
              </span>
            ) : (
              <span className="bg-rose-500/20 text-rose-300 border border-rose-500/40 px-3 py-1 rounded-full text-xs font-semibold">
                ❌ CST Validation Failed
              </span>
            )
          ) : (
            <span className="bg-slate-800 text-slate-400 border border-slate-700 px-3 py-1 rounded-full text-xs font-medium">
              ⏳ Awaiting Transformation Run
            </span>
          )}
        </div>
      </div>

      {/* Validation Checks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-200">LibCST AST Syntax Parsing</span>
            <span className="text-xs text-emerald-400 font-mono">100% Strict</span>
          </div>
          <p className="text-xs text-slate-400">
            Ensures modified Python code parses into valid CST nodes before filesystem write.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-200">Format & Comment Preservation</span>
            <span className="text-xs text-indigo-400 font-mono">Guaranteed</span>
          </div>
          <p className="text-xs text-slate-400">
            Prevents arbitrary LLM code rewrites by restricting mutations strictly toLibCST visitors.
          </p>
        </div>
      </div>

      {/* Warnings & Errors from Backend */}
      {transformResult && (
        <div className="space-y-4 mb-6">
          {transformResult.errors && transformResult.errors.length > 0 && (
            <div className="bg-rose-950/40 border border-rose-500/40 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-rose-300 mb-2">Validation Errors</h3>
              <ul className="list-disc list-inside text-xs text-rose-400 space-y-1 font-mono">
                {transformResult.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {transformResult.warnings && transformResult.warnings.length > 0 && (
            <div className="bg-amber-950/40 border border-amber-500/40 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-amber-300 mb-2">Skipped / Review Required Items</h3>
              <ul className="list-disc list-inside text-xs text-amber-400 space-y-1 font-mono">
                {transformResult.warnings.map((w, i) => (
                  <li key={i}>{w.message}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Repository Test Suite Capability Status */}
      <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-lg flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Automated Repository Test Runner
            </span>
            <span className="bg-slate-800 text-slate-400 border border-slate-700 text-[10px] px-2 py-0.5 rounded">
              Backend Capability Status: Unavailable
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Automated test execution (running pytest/unittest in consumer environment) is not exposed by the current backend API. Code transformation safety is guaranteed via AST parsing validation.
          </p>
        </div>
      </div>
    </div>
  );
};

export default TestValidationSection;
