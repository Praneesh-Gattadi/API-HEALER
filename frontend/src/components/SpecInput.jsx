import React, { useState } from 'react';

const SpecInput = ({ onSubmit, isLoading }) => {
  const [oldSpec, setOldSpec] = useState('');
  const [newSpec, setNewSpec] = useState('');
  const [repoRoot, setRepoRoot] = useState('');
  const [error, setError] = useState(null);

  const handleLoadExample = () => {
    const oldExample = {
      openapi: "3.0.0",
      paths: {
        "/users": {
          get: {
            parameters: [
              { name: "user_id", in: "query", required: true, schema: { type: "string" } }
            ],
            responses: {
              "200": {
                content: {
                  "application/json": {
                    schema: {
                      type: "object",
                      properties: { user_id: { type: "string" } }
                    }
                  }
                }
              }
            }
          }
        }
      }
    };

    const newExample = {
      openapi: "3.0.0",
      paths: {
        "/users": {
          get: {
            parameters: [
              { name: "id", in: "query", required: true, schema: { type: "string" } }
            ],
            responses: {
              "200": {
                content: {
                  "application/json": {
                    schema: {
                      type: "object",
                      properties: { id: { type: "string" } }
                    }
                  }
                }
              }
            }
          }
        }
      }
    };

    setOldSpec(JSON.stringify(oldExample, null, 2));
    setNewSpec(JSON.stringify(newExample, null, 2));
    setError(null);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(null);

    let parsedOld, parsedNew;
    try {
      parsedOld = JSON.parse(oldSpec);
    } catch (err) {
      setError("Invalid JSON in Old Specification");
      return;
    }

    try {
      parsedNew = JSON.parse(newSpec);
    } catch (err) {
      setError("Invalid JSON in New Specification");
      return;
    }

    if (!repoRoot.trim()) {
      setError("Repository Path is required");
      return;
    }

    onSubmit(parsedOld, parsedNew, repoRoot);
  };

  return (
    <div className="glass-panel p-6 animate-fade-in">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-slate-100">API Specifications</h2>
        <button 
          onClick={handleLoadExample}
          className="text-indigo-400 hover:text-indigo-300 text-sm font-medium transition-colors"
          type="button"
        >
          Load user_id → id Example
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/50 rounded-lg text-rose-400 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-300">Old OpenAPI (JSON)</label>
            <textarea
              className="input-field font-mono text-xs h-64 resize-y"
              value={oldSpec}
              onChange={(e) => setOldSpec(e.target.value)}
              placeholder='{ "openapi": "3.0.0", ... }'
            />
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-300">New OpenAPI (JSON)</label>
            <textarea
              className="input-field font-mono text-xs h-64 resize-y"
              value={newSpec}
              onChange={(e) => setNewSpec(e.target.value)}
              placeholder='{ "openapi": "3.0.0", ... }'
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-300">Target Repository Path (Local)</label>
          <input
            type="text"
            className="input-field"
            value={repoRoot}
            onChange={(e) => setRepoRoot(e.target.value)}
            placeholder="/absolute/path/to/repo/to/modify"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary w-full py-3 flex justify-center items-center gap-2"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Generating Migration Plan...
            </>
          ) : (
            "Analyze Diff & Generate Plan"
          )}
        </button>
      </form>
    </div>
  );
};

export default SpecInput;
