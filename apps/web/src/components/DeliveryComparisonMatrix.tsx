import React from 'react';
import { Layers, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

export const DeliveryComparisonMatrix: React.FC = () => {
  const comparisonData = [
    { type: 'DATA_PLATFORM_MIGRATION', name: 'Data Platform Migration', phases: 9, tasks: 42, agents: 10, gates: 8, evidence: 21, risk: 'HIGH' },
    { type: 'DATA_PRODUCT_NEW', name: 'New Data Product', phases: 8, tasks: 37, agents: 11, gates: 7, evidence: 19, risk: 'MEDIUM' },
    { type: 'REGULATORY_POLICY_CHANGE', name: 'Regulatory Policy Change', phases: 5, tasks: 20, agents: 6, gates: 5, evidence: 15, risk: 'HIGH' },
    { type: 'NEW_DATA_SOURCE_ONBOARDING', name: 'New Source Onboarding', phases: 6, tasks: 22, agents: 7, gates: 5, evidence: 12, risk: 'MEDIUM' },
    { type: 'DATA_PRODUCT_AMENDMENT', name: 'Data Product Amendment', phases: 5, tasks: 18, agents: 6, gates: 4, evidence: 10, risk: 'MEDIUM' },
    { type: 'DATA_PRODUCT_DEFECT', name: 'Defect / Remediation', phases: 4, tasks: 12, agents: 5, gates: 3, evidence: 8, risk: 'LOW' },
  ];

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 text-indigo-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/20">
            <Layers className="w-4 h-4" />
            <span>Metamodel Tangibility</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Delivery Type Blueprint Matrix</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Inspect how different delivery types configure phases, tasks, agent workforces, approval gates, and evidence requirements.
          </p>
        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel rounded-3xl overflow-hidden border border-slate-800"
      >
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900/90 text-[10px] text-slate-500 font-bold uppercase tracking-widest border-b border-slate-800/80">
              <tr>
                <th className="p-6">Delivery Type</th>
                <th className="p-6 text-center">Phases</th>
                <th className="p-6 text-center">Tasks</th>
                <th className="p-6 text-center">Agents</th>
                <th className="p-6 text-center">Gates</th>
                <th className="p-6 text-center">Evidence</th>
                <th className="p-6 text-center">Baseline Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {comparisonData.map((row, idx) => (
                <motion.tr 
                  key={row.type} 
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="hover:bg-indigo-500/5 transition-colors group cursor-default"
                >
                  <td className="p-6">
                    <div className="font-bold text-white text-base group-hover:text-indigo-300 transition-colors">{row.name}</div>
                    <div className="text-slate-500 font-mono text-[10px] mt-1">{row.type}</div>
                  </td>
                  <td className="p-6 text-center text-slate-300 font-bold">{row.phases}</td>
                  <td className="p-6 text-center text-slate-300 font-bold">{row.tasks}</td>
                  <td className="p-6 text-center text-indigo-400 font-black">{row.agents}</td>
                  <td className="p-6 text-center text-amber-400 font-black">{row.gates}</td>
                  <td className="p-6 text-center text-emerald-400 font-black">{row.evidence}</td>
                  <td className="p-6 text-center">
                    <span className={`px-3 py-1.5 rounded-lg font-black text-[10px] tracking-widest uppercase inline-block border ${
                      row.risk === 'HIGH' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 
                      row.risk === 'LOW' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                      'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}>
                      {row.risk}
                    </span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
};
