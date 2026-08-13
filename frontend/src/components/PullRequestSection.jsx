import React, { useState } from 'react';
import { createPullRequest } from '../api/client';

const PullRequestSection = ({ transformResult, plan, repoRoot, providerId, provider }) => {
  const [isCreating, setIsCreating] = useState(false);
  const [prResult, setPrResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const isApplied = transformResult && transformResult.success;
  const targetRepo = provider?.github_repo || (provider ? `${provider.name} (Local)` : (repoRoot || 'demo/consumer_app'));

  const handleCreatePR = async () => {
    if (!isApplied) return;
    setIsCreating(true);
    setErrorMsg(null);
    setPrResult(null);

    try {
      const filesToCommit = transformResult?.changes?.map(c => c.file_path) || [];
      const title = plan ? `fix(api): ${plan.summary}` : 'fix(api): automated CST migration for API contract update';
      const body = plan
        ? `### API-Healer Automated Migration Report\n\n- **Summary:** ${plan.summary}\n- **Risk Level:** ${plan.risk_level}\n- **Transformation:** LibCST AST static modification\n- **Validation:** Native Python AST syntax safety validated successfully.\n- **Human Review:** Required before merging.`
        : `### API-Healer Automated Migration Report\n\nAutomated CST source transformation applied cleanly.`;

      const result = await createPullRequest({
        providerId: providerId || provider?.id,
        repositoryPath: repoRoot || provider?.repository_path,
        githubRepo: provider?.github_repo || null,
        baseBranch: 'main',
        title,
        body,
        filesToCommit,
      });

      setPrResult(result);
      if (!result.success && result.status !== 'NOT_CONFIGURED') {
        setErrorMsg(result.message);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to communicate with backend Pull Request service';
      setErrorMsg(msg);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="glass-panel p-6 animate-fade-in mt-6 border border-slate-700/60 shadow-xl">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
            <span>🐙</span> GitHub Pull Request Integration
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Automated PR creation endpoint & developer review handoff
          </p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium border ${
          prResult?.success
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
            : isApplied
            ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
            : 'bg-slate-800 text-slate-400 border-slate-700'
        }`}>
          {prResult?.success ? 'PR CREATED' : isApplied ? 'READY FOR PR' : 'AWAITING APPLY'}
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
            {isApplied ? 'AST VALIDATED' : 'STEP 4 REQUIRED'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono text-slate-400">
          <div>
            <span className="text-slate-500 block">Target Repository:</span>
            <span className="text-slate-200">{targetRepo}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Branch Strategy:</span>
            <span className="text-indigo-400">main ← fix/api-healer-migration-xxxx</span>
          </div>
        </div>

        {/* NOT_CONFIGURED Informational Notice */}
        {prResult && !prResult.success && prResult.status === 'NOT_CONFIGURED' && (
          <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-300 space-y-1">
            <div className="font-semibold flex items-center gap-1.5">
              <span>⚠️</span> GitHub Integration Not Configured on Server
            </div>
            <p className="text-amber-200/80 leading-relaxed">
              Set the <code className="bg-amber-950 px-1.5 py-0.5 rounded border border-amber-500/30 text-amber-300 font-mono">GITHUB_TOKEN</code> environment variable on the FastAPI backend server to enable automated branch creation and Pull Request publishing.
            </p>
          </div>
        )}

        {/* Error Notice */}
        {errorMsg && (
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 space-y-1">
            <div className="font-semibold flex items-center gap-1.5">
              <span>❌</span> Pull Request Creation Failed
            </div>
            <p className="text-rose-200/80 font-mono leading-relaxed">{errorMsg}</p>
          </div>
        )}

        {/* Success Notice & Live Link */}
        {prResult && prResult.success && (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-300 space-y-3 animate-fade-in">
            <div className="flex items-center justify-between">
              <div className="font-bold text-sm flex items-center gap-2">
                <span>🎉</span> GitHub Pull Request #{prResult.pr_number} Created!
              </div>
              <span className="font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded text-[11px]">
                {prResult.commit_sha ? `Commit: ${prResult.commit_sha.substring(0, 7)}` : 'PR Active'}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-emerald-200/80 font-mono text-[11px]">
              <div>Repository: <span className="text-emerald-100 font-semibold">{prResult.repository}</span></div>
              <div>Branch: <span className="text-indigo-300 font-semibold">{prResult.head_branch}</span></div>
            </div>
            {prResult.pr_url && (
              <div className="pt-2">
                <a
                  href={prResult.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors shadow-lg shadow-emerald-600/30"
                >
                  <span>🔗</span> Open Pull Request #{prResult.pr_number} on GitHub →
                </a>
              </div>
            )}
          </div>
        )}

        {/* Action Bar */}
        {(!prResult || !prResult.success) && (
          <div className="flex justify-end pt-2">
            <button
              disabled={!isApplied || isCreating}
              onClick={handleCreatePR}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white border border-indigo-400/30 rounded-lg text-xs font-semibold transition-all shadow-md shadow-indigo-600/20 flex items-center gap-2"
            >
              {isCreating ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating Pull Request...
                </>
              ) : (
                <>
                  <span>🐙</span> {errorMsg ? 'Retry Pull Request Creation' : 'Create Pull Request'}
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PullRequestSection;
