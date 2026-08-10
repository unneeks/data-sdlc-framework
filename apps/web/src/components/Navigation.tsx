import React from 'react';
import { Layers, Terminal, ShieldCheck, Play, RefreshCw, Cpu, GitBranch, LayoutGrid } from 'lucide-react';

interface NavigationProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  demoState: { current_step: number; total_steps: number; step_details: any };
  onResetDemo: () => void;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  setActiveTab,
  demoState,
  onResetDemo
}) => {
  const tabs = [
    { id: 'onboarding', label: '1. Delivery Intent', icon: LayoutGrid },
    { id: 'comparison', label: '2. Blueprint Comparison', icon: Layers },
    { id: 'twin', label: '3. Digital Twin Explorer', icon: GitBranch },
    { id: 'marketplace', label: '4. Workforce Composer', icon: Cpu },
    { id: 'sdlc', label: '5. Hero Demo (SDLC)', icon: Play },
    { id: 'impact', label: '6. Impact & RCA', icon: RefreshCw },
    { id: 'gate', label: '7. Gate & Approval', icon: ShieldCheck },
    { id: 'cli', label: '8. CLI Integrations', icon: Terminal },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center glow-blue">
            <Layers className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-tight leading-tight">
              Agentic Data Engineering System
            </h1>
            <p className="text-xs text-slate-400 font-medium">Digital Engineering Twin & Continuous Delivery Platform</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="hidden lg:flex items-center px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse mr-2"></span>
            <span className="text-slate-300 font-medium">Project: Customer 360</span>
            <span className="mx-2 text-slate-600">|</span>
            <span className="text-slate-400">Wave: Lakehouse Migration</span>
          </div>

          <button
            onClick={onResetDemo}
            className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-lg shadow-indigo-600/30 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset Demo Mode</span>
          </button>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="max-w-7xl mx-auto px-4 flex space-x-1 overflow-x-auto no-scrollbar border-t border-slate-800/60 pt-1 pb-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/40 glow-blue'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
};
