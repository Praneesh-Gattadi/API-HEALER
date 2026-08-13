import React from 'react';
import SpecInput from './SpecInput';
import PlanViewer from './PlanViewer';
import DiffViewer from './DiffViewer';
import TestValidationSection from './TestValidationSection';
import PullRequestSection from './PullRequestSection';

const MigrationsView = ({
  step,
  plan,
  transformResult,
  isLoading,
  error,
  repoRoot,
  onGeneratePlan,
  onDryRun,
  onApply,
  onReset,
}) => {
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Stepper Progress Header */}
      <div className="glass-panel p-4 border border-slate-800 flex justify-center">
        <div className="flex items-center gap-2 text-xs font-medium font-mono">
          <span className={`px-3 py-1 rounded-full border ${step === 'INPUT' ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300 font-bold' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>
            1. Input Specs
          </span>
          <span className="text-slate-700">→</span>
          <span className={`px-3 py-1 rounded-full border ${step === 'PLAN' ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300 font-bold' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>
            2. Migration Plan Ready
          </span>
          <span className="text-slate-700">→</span>
          <span className={`px-3 py-1 rounded-full border ${step === 'DRY_RUN' ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300 font-bold' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>
            3. Dry Run CST Preview
          </span>
          <span className="text-slate-700">→</span>
          <span className={`px-3 py-1 rounded-full border ${step === 'APPLIED' ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 font-bold' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>
            4. Transformation Applied
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/50 rounded-xl text-rose-400 text-sm animate-shake">
          <span className="font-semibold">Error: </span>{error}
        </div>
      )}

      {/* Step 1: Input Specs */}
      {step === 'INPUT' && (
        <SpecInput onSubmit={onGeneratePlan} isLoading={isLoading} />
      )}

      {/* Step 2: Migration Plan Viewer */}
      {(step === 'PLAN' || step === 'DRY_RUN' || step === 'APPLIED') && (
        <PlanViewer
          plan={plan}
          onDryRun={onDryRun}
          isLoading={isLoading && step === 'PLAN'}
        />
      )}

      {/* Step 3: CST Code Diff Viewer */}
      {(step === 'DRY_RUN' || step === 'APPLIED') && (
        <DiffViewer
          result={transformResult}
          onApply={onApply}
          isLoading={isLoading && step === 'DRY_RUN'}
          isApplied={step === 'APPLIED'}
        />
      )}

      {/* Validation & PR Sections (Rendered during Dry Run / Applied) */}
      {(step === 'DRY_RUN' || step === 'APPLIED') && (
        <div className="space-y-6">
          <TestValidationSection transformResult={transformResult} />
          <PullRequestSection transformResult={transformResult} plan={plan} repoRoot={repoRoot} />
        </div>
      )}

      {step !== 'INPUT' && (
        <div className="pt-6 text-center border-t border-slate-800">
          <button
            onClick={onReset}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors font-mono"
          >
            ← Start New Migration Task
          </button>
        </div>
      )}
    </div>
  );
};

export default MigrationsView;
