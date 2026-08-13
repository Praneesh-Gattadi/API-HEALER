import React from 'react';

function App() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          API-Healer: LLM-Assisted CST Agent for API Migrations
        </h1>
        <p className="mt-2 text-gray-600">
          A hackathon project for automated API migrations
        </p>
      </header>

      <main>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* These will be populated as we implement features */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">API Diff Detection</h2>
            <p className="text-gray-600">
              Upload old and new OpenAPI specifications to detect breaking changes
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Structured Migration Instructions</h2>
            <p className="text-gray-600">
              LLM-generated deterministic migration plans for consumer code
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">LibCST Transformation</h2>
            <p className="text-gray-600">
              Deterministic code modifications preserving formatting and comments
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;