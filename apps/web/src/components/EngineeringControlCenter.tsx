import React from 'react';
import { Activity, GitPullRequest, ShieldCheck, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';

export const EngineeringControlCenter: React.FC = () => {
  const stats = [
    { label: "Project Health", value: "98.4%", sub: "Stable Architecture", color: "emerald" },
    { label: "Agent Workforce Health", value: "95.2%", sub: "8 Active Certified Agents", color: "indigo" },
    { label: "Delivery Readiness", value: "85%", sub: "1 Gate Blocked", color: "amber" },
    { label: "Open Change Requests", value: "1 Active", sub: "CR-2026-8942", color: "cyan" },
  ];

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 text-indigo-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/20">
            <Activity className="w-4 h-4" />
            <span>Continuous Operation</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Engineering Control Center</h2>
          <p className="text-slate-400 text-sm max-w-xl">
            Live operational monitoring of project health, agent workforce performance, and open delivery gates.
          </p>
        </div>

        <div className="flex items-center space-x-3 px-4 py-2 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-widest">
          <div className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </div>
          <span>Ecosystem Active</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className={`relative group p-6 rounded-3xl glass-panel-interactive overflow-hidden border border-${stat.color}-500/20`}
          >
            <div className={`absolute top-0 right-0 w-32 h-32 bg-${stat.color}-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:bg-${stat.color}-500/20 transition duration-500`} />
            
            <div className="relative z-10 space-y-4">
              <span className="text-xs text-slate-400 font-bold uppercase tracking-widest">{stat.label}</span>
              
              <div className={`text-4xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-br from-white to-${stat.color}-400`}>
                {stat.value}
              </div>
              
              <div className={`text-xs font-semibold text-${stat.color}-400 px-3 py-1.5 bg-${stat.color}-500/10 rounded-lg inline-block border border-${stat.color}-500/20`}>
                {stat.sub}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
