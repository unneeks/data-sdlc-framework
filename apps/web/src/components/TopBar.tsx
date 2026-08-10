import React from 'react';
import { RefreshCw, Search, Bell } from 'lucide-react';

interface TopBarProps {
  onResetDemo: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onResetDemo }) => {
  return (
    <header className="sticky top-0 z-30 bg-slate-900/60 backdrop-blur-xl border-b border-slate-800/80 px-8 py-4 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <div className="flex items-center px-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm shadow-inner">
          <span className="text-slate-400 font-medium mr-2">Project:</span>
          <span className="text-white font-bold">Customer 360</span>
          <span className="mx-3 text-slate-700">|</span>
          <span className="text-slate-400 font-medium mr-2">Wave:</span>
          <span className="text-white font-bold">Lakehouse Migration</span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="hidden md:flex items-center bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 w-64">
          <Search className="w-4 h-4 text-slate-500 mr-2" />
          <input 
            type="text" 
            placeholder="Search twin, agents, or tasks..." 
            className="bg-transparent border-none outline-none text-xs text-white placeholder-slate-500 w-full"
          />
        </div>
        
        <button className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition">
          <Bell className="w-4 h-4" />
        </button>

        <button
          onClick={onResetDemo}
          className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/50 text-indigo-300 font-semibold text-sm transition"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Reset Demo</span>
        </button>
      </div>
    </header>
  );
};
