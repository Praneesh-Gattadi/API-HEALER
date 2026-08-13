import React, { useState, useEffect } from 'react';
import { generateMigrationPlan, applyTransformation, getSnapshotSpec, listProviders, checkProviderUpdates } from './api/client';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import ApiChangesView from './components/ApiChangesView';
import MigrationsView from './components/MigrationsView';
import RepositoriesView from './components/RepositoriesView';

function App() {
  const [activeTab, setActiveTab] = useState('DASHBOARD'); // DASHBOARD, API_CHANGES, MIGRATIONS, REPOSITORIES
  const [step, setStep] = useState('INPUT'); // INPUT, PLAN, DRY_RUN, APPLIED
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [providers, setProviders] = useState([]);
  const [repoRoot, setRepoRoot] = useState('');
  const [plan, setPlan] = useState(null);
  const [transformResult, setTransformResult] = useState(null);
  const [activeProviderId, setActiveProviderId] = useState(null);

  const loadProvidersList = async () => {
    try {
      const data = await listProviders();
      setProviders(data);
    } catch (err) {
      console.error('Failed to load providers:', err);
    }
  };

  useEffect(() => {
    loadProvidersList();
    const interval = setInterval(loadProvidersList, 10000);
    return () => clearInterval(interval);
  }, []);

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

  const handleGeneratePlan = async (oldSpec, newSpec, root = '', providerId = null) => {
    setIsLoading(true);
    setError(null);
    setRepoRoot(root);
    setActiveProviderId(providerId);
    try {
      const generatedPlan = await generateMigrationPlan(oldSpec, newSpec);
      setPlan(generatedPlan);
      setStep('PLAN');
      setActiveTab('MIGRATIONS');
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

  const handleCheckProviderFromRepoView = async (provider) => {
    setIsLoading(true);
    setError(null);
    try {
      const decision = await checkProviderUpdates(provider.id);
      await loadProvidersList();
      if (decision.status === 'MIGRATION_REQUIRED') {
        await handleMigrationRequired(provider);
      } else {
        alert(`Check complete for ${provider.name}.\nStatus: ${decision.status}\nReason: ${decision.reason}`);
      }
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
      await loadProvidersList();
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
    <div className="flex min-h-screen bg-slate-900 text-slate-100 font-sans bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-800 via-slate-900 to-black">
      {/* Sidebar Navigation */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 p-4 md:p-8 overflow-y-auto">
        <Header activeTab={activeTab} />

        <main className="flex-1">
          {activeTab === 'DASHBOARD' && (
            <DashboardView
              providers={providers}
              onMigrationRequired={handleMigrationRequired}
              onSelectTab={setActiveTab}
            />
          )}

          {activeTab === 'API_CHANGES' && (
            <ApiChangesView
              onGeneratePlanFromDiff={(oldSpec, newSpec) => handleGeneratePlan(oldSpec, newSpec, 'demo/consumer_app')}
            />
          )}

          {activeTab === 'MIGRATIONS' && (
            <MigrationsView
              step={step}
              plan={plan}
              transformResult={transformResult}
              isLoading={isLoading}
              error={error}
              repoRoot={repoRoot}
              providerId={activeProviderId}
              provider={providers.find(p => p.id === activeProviderId)}
              onGeneratePlan={handleGeneratePlan}
              onDryRun={handleDryRun}
              onApply={handleApply}
              onReset={handleReset}
            />
          )}

          {activeTab === 'REPOSITORIES' && (
            <RepositoriesView
              providers={providers}
              onCheckProvider={handleCheckProviderFromRepoView}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;