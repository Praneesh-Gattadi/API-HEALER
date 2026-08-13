import React, { useState } from 'react';
import { generateMigrationPlan, applyTransformation, getSnapshotSpec } from './api/client';
import SpecInput from './components/SpecInput';
import PlanViewer from './components/PlanViewer';
import DiffViewer from './components/DiffViewer';
import ProviderDashboard from './components/ProviderDashboard';

function App() {
  const [activeTab, setActiveTab] = useState('MANUAL'); // MANUAL, MONITORING
  const [step, setStep] = useState('INPUT'); // INPUT, PLAN, DRY_RUN, APPLIED
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [repoRoot, setRepoRoot] = useState('');
  const [plan, setPlan] = useState(null);
  const [transformResult, setTransformResult] = useState(null);
  const [activeProviderId, setActiveProviderId] = useState(null);

  const handleError = (err) => {
    console.error(err);
    if (err.response?.data?.detail) {
      setError(typeof err.response.data.detail === 'string'
        ? err.response.data.detail
        : JSON.stringify(err.response.data.detail));
    } else {
      setError(err.message || 'An unexpected error occurred');
    }
    setIsLoading(false);
  };

  const handleGeneratePlan = async (oldSpec, newSpec, root, providerId = null) => {
    setIsLoading(true);
    setError(null);
    setRepoRoot(root);
    setActiveProviderId(providerId);
    try {
      const generatedPlan = await generateMigrationPlan(oldSpec, newSpec);
      setPlan(generatedPlan);
      setStep('PLAN');
      if (providerId) {
        setActiveTab('MANUAL');
      }
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMigrationRequired = async (provider) => {
    setIsLoading(true);
    setError(null);
    try {
      const oldSpec = await getSnapshotSpec(provider.id, provider.last_processed_snapshot_id);
      const newSpec = await getSnapshotSpec(provider.id, provider.pending_snapshot_id);
      await handleGeneratePlan(oldSpec, newSpec, provider.repository_path, provider.id);
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDryRun = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await applyTransformation(plan, repoRoot, true, activeProviderId);
      setTransformResult(result);
      setStep('DRY_RUN');
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApply = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await applyTransformation(plan, repoRoot, false, activeProviderId);
      setTransformResult(result);
      setStep('APPLIED');
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setStep('INPUT');
    setPlan(null);
    setTransformResult(null);
    setError(null);
    setActiveProviderId(null);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 p-4 md:p-8 font-sans bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-800 via-slate-900 to-black">
      <div className="max-w-5xl mx-auto">
        <header className="mb-8 text-center animate-fade-in-down">
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-sm font-medium mb-4">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
            Phase 5 Complete
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400 tracking-tight">
            API-Healer
          </h1>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            Deterministic Code Transformation Engine & Provider Monitor
          </p>
        </header>

        <div className="flex justify-center mb-8">
          <div className="bg-slate-800 p-1 rounded-lg inline-flex">
            <button
              onClick={() => setActiveTab('MANUAL')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'MANUAL' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Manual Migration
            </button>
            <button
              onClick={() => setActiveTab('MONITORING')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'MONITORING' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Automated Monitoring
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-8 p-4 bg-rose-500/10 border border-rose-500/50 rounded-xl text-rose-400 shadow-lg animate-shake">
            <span className="font-medium">Error: {error}</span>
          </div>
        )}

        {activeTab === 'MONITORING' ? (
          <ProviderDashboard onMigrationRequired={handleMigrationRequired} />
        ) : (
          <>
            <div className="space-y-2 mb-8 flex justify-center">
              <div className="flex items-center gap-2 text-xs font-medium">
                <span className={`px-3 py-1 rounded-full border ${step === 'INPUT' ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>1. Input</span>
                <span className="text-slate-700">→</span>
                <span className={`px-3 py-1 rounded-full border ${step === 'PLAN' ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>2. Plan Ready</span>
                <span className="text-slate-700">→</span>
                <span className={`px-3 py-1 rounded-full border ${step === 'DRY_RUN' ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>3. Dry Run Preview</span>
                <span className="text-slate-700">→</span>
                <span className={`px-3 py-1 rounded-full border ${step === 'APPLIED' ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>4. Applied</span>
              </div>
            </div>

            {step === 'INPUT' && (
              <SpecInput onSubmit={handleGeneratePlan} isLoading={isLoading} />
            )}

            {(step === 'PLAN' || step === 'DRY_RUN' || step === 'APPLIED') && (
              <PlanViewer
                plan={plan}
                onDryRun={handleDryRun}
                isLoading={isLoading && step === 'PLAN'}
              />
            )}

            {(step === 'DRY_RUN' || step === 'APPLIED') && (
              <DiffViewer
                result={transformResult}
                onApply={handleApply}
                isLoading={isLoading && step === 'DRY_RUN'}
                isApplied={step === 'APPLIED'}
              />
            )}

            {step !== 'INPUT' && (
              <div className="mt-12 text-center">
                <button
                  onClick={handleReset}
                  className="text-slate-500 hover:text-slate-300 text-sm transition-colors"
                >
                  Start Over
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;