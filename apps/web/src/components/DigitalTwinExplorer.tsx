import React, { useState } from 'react';
import { GitBranch, Database, Cpu, FileCode, CheckSquare, Layers, Code2, Link as LinkIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const DigitalTwinExplorer: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'technical' | 'delivery'>('technical');

  const technicalNodes = [
    { id: 'salesforce_ingest.py', type: 'Pipeline', platform: 'Dataflow', status: 'CHANGED', layer: 'ingestion' },
    { id: 'lakehouse_raw.customer', type: 'Target Asset', platform: 'BigLake', status: 'REDIRECTED', layer: 'storage' },
    { id: 'stg_customers.sql', type: 'dbt Model', platform: 'BigQuery', status: 'IMPACTED', layer: 'transform' },
    { id: 'customer_360.sql', type: 'dbt Model', platform: 'BigQuery', status: 'IMPACTED', layer: 'mart' }
  ];

  const deliveryNodes = [
    { phase: 'Phase 1: Architecture', task: 'Feasibility Analysis', contract: 'CONTRACT-001', gate: 'Architecture Gate', status: 'PASSED' },
    { phase: 'Phase 2: Design', task: 'Schema Design', contract: 'CONTRACT-002', gate: 'Tech Spec Gate', status: 'PASSED' },
    { phase: 'Phase 4: Development', task: 'Endpoint Mod', contract: 'CONTRACT-004', gate: 'Code Review Gate', status: 'PASSED' },
    { phase: 'Phase 5: Testing', task: 'Data Parity Run', contract: 'CONTRACT-005', gate: 'Reconciliation Gate', status: 'FAILED' },
  ];

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 text-indigo-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/20">
            <GitBranch className="w-4 h-4" />
            <span>Dual-Twin Modeling Engine</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Project Digital Twin</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Bridging <strong className="text-white">Technical Reality</strong> (Code, Lineage, Infrastructure) and <strong className="text-white">Delivery Reality</strong> (Tasks, Contracts, Gates) into a unified graph.
          </p>
        </div>

        <div className="flex p-1.5 bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-700 shadow-xl">
          <button
            onClick={() => setActiveSubTab('technical')}
            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${
              activeSubTab === 'technical' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            Technical Twin
          </button>
          <button
            onClick={() => setActiveSubTab('delivery')}
            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${
              activeSubTab === 'delivery' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            Delivery Twin
          </button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {activeSubTab === 'technical' ? (
          <motion.div
            key="technical"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            className="glass-panel p-10 rounded-3xl relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5 pointer-events-none" />
            
            <div className="flex flex-col md:flex-row items-center justify-between gap-12 relative z-10">
              {technicalNodes.map((node, idx) => (
                <React.Fragment key={node.id}>
                  <div className="relative group w-full md:w-64">
                    <div className={`absolute -inset-0.5 rounded-2xl blur opacity-30 group-hover:opacity-100 transition duration-500 ${
                      node.status === 'CHANGED' ? 'bg-amber-500' : 
                      node.status === 'REDIRECTED' ? 'bg-cyan-500' : 'bg-indigo-500'
                    }`} />
                    <div className="relative p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-600 transition flex flex-col items-center text-center space-y-4">
                      <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center border border-slate-700">
                        {node.layer === 'ingestion' ? <Code2 className="w-6 h-6 text-amber-400" /> :
                         node.layer === 'storage' ? <Database className="w-6 h-6 text-cyan-400" /> :
                         <Layers className="w-6 h-6 text-indigo-400" />}
                      </div>
                      
                      <div className="space-y-1">
                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{node.type} • {node.platform}</div>
                        <div className="text-sm font-bold text-white font-mono break-all">{node.id}</div>
                      </div>

                      <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-widest ${
                        node.status === 'CHANGED' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        node.status === 'REDIRECTED' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 
                        'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                      }`}>
                        {node.status}
                      </span>
                    </div>
                  </div>

                  {idx < technicalNodes.length - 1 && (
                    <div className="hidden md:flex flex-col items-center text-slate-600 shrink-0">
                      <LinkIcon className="w-5 h-5 mb-1" />
                      <div className="w-16 h-[1px] bg-slate-700 border-t border-dashed" />
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="delivery"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
          >
            {deliveryNodes.map((item, idx) => (
              <div key={idx} className="glass-panel p-6 rounded-3xl flex flex-col justify-between space-y-6 relative group overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-bl-full pointer-events-none" />
                
                <div className="space-y-4">
                  <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest px-2 py-1 bg-indigo-500/10 rounded-md border border-indigo-500/20">
                    {item.phase}
                  </span>
                  
                  <h4 className="text-xl font-bold text-white leading-tight">{item.task}</h4>
                  
                  <div className="flex items-center space-x-2 text-xs font-mono text-slate-500">
                    <CheckSquare className="w-3.5 h-3.5" />
                    <span>{item.contract}</span>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-[10px] text-slate-400 uppercase font-bold">{item.gate}</span>
                  <span className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-widest ${
                    item.status === 'PASSED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]' :
                    'bg-rose-500/10 text-rose-400 border border-rose-500/30 shadow-[0_0_10px_rgba(244,63,94,0.2)]'
                  }`}>
                    {item.status}
                  </span>
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
