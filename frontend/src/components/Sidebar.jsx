import React from 'react';

const Sidebar = ({ activeTab, setActiveTab }) => {
  const navItems = [
    { id: 'DASHBOARD', label: 'Dashboard', icon: '📊', description: 'Overview & Monitored Providers' },
    { id: 'API_CHANGES', label: 'API Changes', icon: '⚡', description: 'Detected Spec Differences' },
    { id: 'MIGRATIONS', label: 'Migrations', icon: '🔄', description: 'Plan, CST Diff & Apply' },
    { id: 'REPOSITORIES', label: 'Repositories', icon: '📁', description: 'Monitored Consumer Codebases' },
  ];

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col justify-between p-4 shrink-0 min-h-screen">
      <div>
        {/* Brand Header */}
        <div className="mb-8 px-3 pt-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
              AH
            </div>
            <div>
              <h1 className="font-extrabold text-lg tracking-tight text-white leading-tight">API-Healer</h1>
              <p className="text-[11px] text-slate-400 font-medium tracking-wide">Automated API Migration</p>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <span className="text-base">{item.icon}</span>
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Branding */}
      <div className="pt-4 border-t border-slate-800/80 px-3 space-y-1">
        <div className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          AI Undergrads
        </div>
        <div className="text-[10px] font-mono text-indigo-400">
          DEMUX 3.0 Hackathon
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
