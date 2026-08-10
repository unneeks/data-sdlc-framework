import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Cpu, Database, FileText, CheckCircle2, Search, X, Activity, Wrench, BarChart, BookOpen, Clock } from 'lucide-react';
import metamodelData from '../data/metamodel.json';

// Deterministic telemetry generator based on string hash
const generateTelemetry = (id: string) => {
  const hash = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return {
    invocationsPerDay: 10 + (hash % 200),
    successRatio: 85 + (hash % 15),
    trustScore: 80 + (hash % 20),
    avgExecutionTime: `${(hash % 5) + 1}m ${(hash % 60)}s`
  };
};

const AGENTS = (metamodelData.agents as any).agents.map((a: any) => ({
  id: a.key,
  name: a.name,
  role: a.role_key,
  description: a.mission || 'Autonomous Marketplace Agent',
  metrics: generateTelemetry(a.key),
  linkedEntities: ['Agent', a.role_key, ...(a.capabilities || [])],
  skills: a.skills || [],
  tools: a.tools || [],
  tasks: a.delivery?.supported_tasks || ['Autonomous Execution'],
  references: a.knowledge_packs || []
}));

export const AgentExplorer: React.FC = () => {
  const [search, setSearch] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<any>(null);

  const filteredAgents = AGENTS.filter(a => a.name.toLowerCase().includes(search.toLowerCase()) || a.role.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="h-full flex flex-col space-y-6">
      
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
           <div className="inline-flex items-center space-x-2 text-emerald-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-emerald-500/10 rounded-full border border-emerald-500/20 mb-2">
             <Cpu className="w-4 h-4" />
             <span>Marketplace Catalogue</span>
           </div>
           <h2 className="text-3xl font-extrabold text-white">Agent Explorer</h2>
           <p className="text-slate-400 mt-1">Explore the certified autonomous workforce and their operational telemetry.</p>
        </div>
        <div className="relative w-64">
           <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
           <input
             type="text"
             value={search}
             onChange={(e) => setSearch(e.target.value)}
             placeholder="Search agents or roles..."
             className="w-full bg-slate-900 border border-slate-700 rounded-xl py-2 pl-9 pr-4 text-sm text-white focus:outline-none focus:border-emerald-500 transition"
           />
        </div>
      </div>

      {/* Agents Grid */}
      <div className="flex-1 overflow-y-auto custom-scrollbar grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-6">
        <AnimatePresence>
          {filteredAgents.map((agent) => (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              whileHover={{ scale: 1.02 }}
              onClick={() => setSelectedAgent(agent)}
              className="glass-panel p-6 rounded-3xl border-slate-700/50 cursor-pointer hover:border-emerald-500/50 transition group flex flex-col"
            >
              <div className="flex justify-between items-start mb-4">
                 <div className="p-3 bg-slate-900 rounded-2xl border border-slate-800 group-hover:bg-emerald-500/10 group-hover:border-emerald-500/30 transition">
                    <Cpu className="w-6 h-6 text-emerald-400" />
                 </div>
                 <div className="flex items-center space-x-1 bg-emerald-500/10 px-2 py-1 rounded text-xs font-bold text-emerald-400 border border-emerald-500/20">
                    <ShieldCheck className="w-3 h-3" />
                    <span>{agent.metrics.trustScore}% Trust</span>
                 </div>
              </div>
              <h3 className="text-lg font-bold text-white mb-1 group-hover:text-emerald-300 transition">{agent.name}</h3>
              <p className="text-xs font-mono text-slate-500 mb-4">{agent.role}</p>
              
              <div className="mt-auto grid grid-cols-2 gap-2 pt-4 border-t border-slate-800">
                 <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                    <span className="block text-[9px] text-slate-500 uppercase tracking-widest font-bold">Invocations</span>
                    <span className="text-sm font-mono text-white">{agent.metrics.invocationsPerDay}/day</span>
                 </div>
                 <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                    <span className="block text-[9px] text-slate-500 uppercase tracking-widest font-bold">Success</span>
                    <span className="text-sm font-mono text-white">{agent.metrics.successRatio}%</span>
                 </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Drill-down Modal */}
      <AnimatePresence>
        {selectedAgent && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40"
              onClick={() => setSelectedAgent(null)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-full md:max-w-5xl max-h-[90vh] bg-slate-900 border border-emerald-500/20 rounded-3xl shadow-2xl z-50 flex flex-col overflow-hidden"
            >
              {/* Header */}
              <div className="p-6 border-b border-emerald-500/20 bg-emerald-500/5 flex justify-between items-center shrink-0">
                <div className="flex items-center space-x-4">
                  <div className="p-3 bg-emerald-500/20 rounded-2xl border border-emerald-500/30">
                    <Cpu className="w-8 h-8 text-emerald-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-1">{selectedAgent.name}</h2>
                    <div className="flex items-center space-x-3 text-sm">
                      <span className="text-emerald-400 font-mono">{selectedAgent.id}</span>
                      <span className="text-slate-500">•</span>
                      <span className="text-slate-300">Role: {selectedAgent.role}</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedAgent(null)}
                  className="p-2 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white transition"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Body */}
              <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
                
                {/* Telemetry Row */}
                <div className="grid grid-cols-4 gap-4 mb-8">
                  {[
                    { label: 'Trust Score', value: `${selectedAgent.metrics.trustScore}%`, icon: ShieldCheck, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
                    { label: 'Invocations', value: `${selectedAgent.metrics.invocationsPerDay}/day`, icon: Activity, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
                    { label: 'Success Ratio', value: `${selectedAgent.metrics.successRatio}%`, icon: CheckCircle2, color: 'text-amber-400', bg: 'bg-amber-500/10' },
                    { label: 'Avg Runtime', value: selectedAgent.metrics.avgExecutionTime, icon: Clock, color: 'text-rose-400', bg: 'bg-rose-500/10' },
                  ].map((stat, i) => (
                    <div key={i} className="p-4 bg-slate-950 rounded-2xl border border-slate-800 flex items-center space-x-4">
                      <div className={`p-2 rounded-xl ${stat.bg} border border-slate-700/50`}>
                        <stat.icon className={`w-5 h-5 ${stat.color}`} />
                      </div>
                      <div>
                        <span className="block text-xl font-bold text-white">{stat.value}</span>
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{stat.label}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                   
                   {/* Left Column */}
                   <div className="space-y-6">
                     <div>
                       <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                         <Database className="w-4 h-4" /> <span>Linked Metamodel Entities</span>
                       </h3>
                       <div className="flex flex-wrap gap-2">
                         {selectedAgent.linkedEntities.map((entity: string, i: number) => (
                           <span key={i} className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 font-mono">
                             {entity}
                           </span>
                         ))}
                       </div>
                     </div>

                     <div>
                       <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                         <Wrench className="w-4 h-4" /> <span>Composed Skills & Tools</span>
                       </h3>
                       <div className="space-y-3">
                         <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                           <span className="text-xs text-slate-500 mb-2 block">SKILLS</span>
                           <div className="flex flex-wrap gap-2">
                             {selectedAgent.skills.map((skill: string, i: number) => (
                               <span key={i} className="px-2 py-1 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded text-xs font-mono">
                                 {skill}
                               </span>
                             ))}
                           </div>
                         </div>
                         <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                           <span className="text-xs text-slate-500 mb-2 block">TOOLS</span>
                           <div className="flex flex-wrap gap-2">
                             {selectedAgent.tools.map((tool: string, i: number) => (
                               <span key={i} className="px-2 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded text-xs font-mono">
                                 {tool}
                               </span>
                             ))}
                           </div>
                         </div>
                       </div>
                     </div>
                   </div>

                   {/* Right Column */}
                   <div className="space-y-6">
                     <div>
                       <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                         <CheckCircle2 className="w-4 h-4" /> <span>Expected Tasks</span>
                       </h3>
                       <ul className="space-y-2">
                         {selectedAgent.tasks.map((task: string, i: number) => (
                           <li key={i} className="flex items-center space-x-3 text-sm text-slate-300 bg-slate-800/30 p-3 rounded-lg border border-slate-700/50">
                             <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                             <span>{task}</span>
                           </li>
                         ))}
                       </ul>
                     </div>

                     <div>
                       <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                         <BookOpen className="w-4 h-4" /> <span>Configured References</span>
                       </h3>
                       <ul className="space-y-2">
                         {selectedAgent.references.map((ref: string, i: number) => (
                           <li key={i} className="flex items-center space-x-3 text-sm text-slate-300 bg-slate-800/30 p-3 rounded-lg border border-slate-700/50">
                             <FileText className="w-4 h-4 text-slate-500" />
                             <span>{ref}</span>
                           </li>
                         ))}
                       </ul>
                     </div>
                   </div>

                </div>

              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};
