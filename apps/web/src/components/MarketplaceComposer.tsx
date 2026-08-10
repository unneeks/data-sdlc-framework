import React from 'react';
import { Agent } from '../services/api';
import { Cpu, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  agents: Agent[];
}

export const MarketplaceComposer: React.FC<Props> = ({ agents }) => {
  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 text-indigo-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/20">
            <Cpu className="w-4 h-4" />
            <span>Context-Aware Agent Ecosystem</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Workforce Composer</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Agents implement organizational <strong className="text-white">Engineering Roles</strong>. They are certified based on technical accuracy, deterministic capabilities, and compliance conformance.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent, idx) => (
          <motion.div 
            key={agent.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            whileHover={{ y: -5 }}
            className="glass-panel p-6 rounded-3xl relative overflow-hidden group border border-slate-800"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition duration-500" />
            
            <div className="relative z-10 space-y-5">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <span className="text-[10px] font-bold px-2 py-1 rounded bg-slate-800 text-indigo-400 uppercase tracking-widest border border-slate-700">
                    {agent.engineering_role}
                  </span>
                  <h3 className="text-xl font-bold text-white pt-2 leading-tight">{agent.name}</h3>
                  <div className="text-xs text-slate-500 font-mono">v{agent.version}</div>
                </div>

                <div className="text-right flex flex-col items-end">
                  <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-black tracking-widest uppercase shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>{(agent.trust_score * 100).toFixed(0)}% Trust</span>
                  </div>
                  <div className="text-[9px] text-slate-500 uppercase tracking-widest mt-2">{agent.certification_status}</div>
                </div>
              </div>

              <p className="text-sm text-slate-300 leading-relaxed min-h-[60px]">{agent.description}</p>

              <div className="space-y-3 pt-4 border-t border-slate-800/80">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Activated Core Capabilities:</div>
                <div className="flex flex-wrap gap-2">
                  {agent.skills.map((skill, idx) => (
                    <span key={idx} className="text-[10px] font-mono bg-slate-900/80 px-2.5 py-1 rounded-md border border-slate-700 text-slate-300">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
