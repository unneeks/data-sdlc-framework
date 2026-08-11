import React, { useEffect, useState } from 'react';
import { Layers, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { fetchDeliveryTypes } from '../services/api';

export const DeliveryComparisonMatrix: React.FC = () => {
  const [comparisonData, setComparisonData] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      const types = await fetchDeliveryTypes();
      const mapped = types.map((t: any) => ({
        type: t.id,
        name: t.name,
        phases: t.phases_count || 5,
        tasks: t.tasks_count || 20,
        agents: t.default_agents?.length || 6,
        gates: 5, // Default gate count for UI
        evidence: 10, // Default evidence count
        risk: t.baseline_risk || 'MEDIUM'
      }));
      setComparisonData(mapped);
    }
    loadData();
  }, []);

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
