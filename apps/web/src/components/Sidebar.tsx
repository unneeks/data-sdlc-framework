import { LayoutGrid, Layers, GitBranch, Cpu, Play, RefreshCw, ShieldCheck, Terminal, Briefcase, Database, Wrench, Network } from 'lucide-react';
import { motion } from 'framer-motion';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'project_onboarding', label: 'Project Discovery', icon: Briefcase },
    { id: 'onboarding', label: 'Delivery Intent', icon: LayoutGrid },
    { id: 'metamodel', label: 'Metamodel Explorer', icon: Database },
    { id: 'agents', label: 'Agent Explorer', icon: Cpu },
    { id: 'skills', label: 'Skills Explorer', icon: Wrench },
    { id: 'comparison', label: 'Blueprint Comparison', icon: Layers },
    { id: 'twin', label: 'Digital Twin Explorer', icon: GitBranch },
    { id: 'sdlc', label: 'Hero Demo (SDLC)', icon: Play },
    { id: 'impact', label: 'Impact & RCA', icon: RefreshCw },
    { id: 'gate', label: 'Gate & Approval', icon: ShieldCheck },
    { id: 'live-incident', label: 'Live Incident (API)', icon: Play },
    { id: 'live-gate', label: 'Live Gate (API)', icon: ShieldCheck },
    { id: 'cli', label: 'CLI Integrations', icon: Terminal },
    { id: 'project-graph', label: 'Simulated Project Graph', icon: Network },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/60 backdrop-blur-2xl flex flex-col h-screen sticky top-0 flex-shrink-0 z-40">
      <div className="p-5 flex items-center space-x-3 border-b border-slate-800/80">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center glow-blue shrink-0">
          <Layers className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="font-extrabold text-sm text-white tracking-tight leading-tight">
            Agentic Data<br />Engineering
          </h1>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1.5 custom-scrollbar">
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3 px-3">Ecosystem Views</div>
        
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all relative group overflow-hidden ${
                isActive 
                  ? 'text-white' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              {isActive && (
                <motion.div 
                  layoutId="active-tab-indicator"
                  className="absolute inset-0 bg-indigo-600/20 border border-indigo-500/40 rounded-xl"
                  initial={false}
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              
              <Icon className={`w-4 h-4 relative z-10 transition-colors ${isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-400'}`} />
              <span className="relative z-10">{tab.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800/80">
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 flex items-center space-x-3">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <div className="text-xs font-semibold text-emerald-400">System Online</div>
        </div>
      </div>
    </aside>
  );
};
