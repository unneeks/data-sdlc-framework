import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Database, FileText, CheckCircle2, Search, X, Wrench, BookOpen, GitMerge, AlertTriangle, Layers } from 'lucide-react';
import { fetchSkills } from '../services/api';

export const SkillsExplorer: React.FC = () => {
  const [search, setSearch] = useState('');
  const [selectedSkill, setSelectedSkill] = useState<any>(null);
  const [skills, setSkills] = useState<any[]>([]);

  useEffect(() => {
    async function loadSkills() {
      const apiSkills = await fetchSkills();
      setSkills(apiSkills);
    }
    loadSkills();
  }, []);

  const filteredSkills = skills.filter(s => s.name.toLowerCase().includes(search.toLowerCase()) || s.id.toLowerCase().includes(search.toLowerCase()));

  const getRiskColor = (risk: string) => {
    switch (risk.toUpperCase()) {
      case 'HIGH': return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      case 'MEDIUM': return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      default: return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
           <div className="inline-flex items-center space-x-2 text-indigo-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/20 mb-2">
             <Wrench className="w-4 h-4" />
             <span>Marketplace Catalogue</span>
           </div>
           <h2 className="text-3xl font-extrabold text-white">Skills Explorer</h2>
           <p className="text-slate-400 mt-1">Explore reusable, independently testable units of agent capability.</p>
        </div>
        <div className="relative w-64">
           <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
           <input
             type="text"
             value={search}
             onChange={(e) => setSearch(e.target.value)}
             placeholder="Search skills..."
             className="w-full bg-slate-900 border border-slate-700 rounded-xl py-2 pl-9 pr-4 text-sm text-white focus:outline-none focus:border-indigo-500 transition"
           />
        </div>
      </div>

      {/* Skills Grid */}
      <div className="flex-1 overflow-y-auto custom-scrollbar grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 pb-6">
        <AnimatePresence>
          {filteredSkills.map((skill) => (
            <motion.div
              key={skill.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              whileHover={{ scale: 1.02 }}
              onClick={() => setSelectedSkill(skill)}
              className="glass-panel p-6 rounded-3xl border-slate-700/50 cursor-pointer hover:border-indigo-500/50 transition group flex flex-col"
            >
              <div className="flex justify-between items-start mb-4">
                 <div className="p-3 bg-slate-900 rounded-2xl border border-slate-800 group-hover:bg-indigo-500/10 group-hover:border-indigo-500/30 transition">
                    <Wrench className="w-6 h-6 text-indigo-400" />
                 </div>
                 <div className={`flex items-center space-x-1 px-2 py-1 rounded text-xs font-bold border ${getRiskColor(skill.riskLevel)}`}>
                    <AlertTriangle className="w-3 h-3" />
                    <span>{skill.riskLevel} RISK</span>
                 </div>
              </div>
              <h3 className="text-lg font-bold text-white mb-1 group-hover:text-indigo-300 transition">{skill.name}</h3>
              <p className="text-xs font-mono text-slate-500 mb-4">{skill.id}</p>
              
              <div className="mt-auto grid grid-cols-2 gap-2 pt-4 border-t border-slate-800">
                 <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                    <span className="block text-[9px] text-slate-500 uppercase tracking-widest font-bold">Dependencies</span>
                    <span className="text-sm font-mono text-white">{skill.dependencies.length}</span>
                 </div>
                 <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                    <span className="block text-[9px] text-slate-500 uppercase tracking-widest font-bold">Tools Req</span>
                    <span className="text-sm font-mono text-white">{skill.requiredTools.length}</span>
                 </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Drill-down Modal */}
      <AnimatePresence>
        {selectedSkill && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40"
              onClick={() => setSelectedSkill(null)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed top-8 bottom-8 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-5xl bg-slate-900 border border-indigo-500/20 rounded-3xl shadow-2xl z-50 flex flex-col overflow-hidden"
            >
              {/* Header */}
              <div className="p-6 border-b border-indigo-500/20 bg-indigo-500/5 flex justify-between items-center shrink-0">
                <div className="flex items-center space-x-4">
                  <div className="p-3 bg-indigo-500/20 rounded-2xl border border-indigo-500/30">
                    <Wrench className="w-8 h-8 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-1">{selectedSkill.name}</h2>
                    <div className="flex items-center space-x-3 text-sm">
                      <span className="text-indigo-400 font-mono">{selectedSkill.id}</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedSkill(null)}
                  className="p-2 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white transition"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Body */}
              <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
                
                <div className="grid grid-cols-4 gap-4 mb-8">
                  {[
                    { label: 'Risk Level', value: selectedSkill.riskLevel, icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-500/10' },
                    { label: 'Execution', value: selectedSkill.deterministic ? 'Deterministic' : 'Non-Deterministic', icon: ShieldCheck, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
                    { label: 'Dependencies', value: selectedSkill.dependencies.length.toString(), icon: GitMerge, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
                    { label: 'Discharges', value: `${selectedSkill.dischargesChecklist.length} Items`, icon: CheckCircle2, color: 'text-rose-400', bg: 'bg-rose-500/10' },
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
                         <GitMerge className="w-4 h-4" /> <span>Skill Dependencies</span>
                       </h3>
                       {selectedSkill.dependencies.length > 0 ? (
                         <div className="flex flex-wrap gap-2">
                           {selectedSkill.dependencies.map((dep: string, i: number) => (
                             <span key={i} className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 font-mono">
                               {dep}
                             </span>
                           ))}
                         </div>
                       ) : (
                         <div className="text-sm text-slate-500 italic p-3 bg-slate-900 rounded-lg border border-slate-800">No dependencies</div>
                       )}
                     </div>

                     <div>
                       <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                         <Wrench className="w-4 h-4" /> <span>Required Tools & Knowledge</span>
                       </h3>
                       <div className="space-y-3">
                         <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                           <span className="text-xs text-slate-500 mb-2 block">TOOLS</span>
                           {selectedSkill.requiredTools.length > 0 ? (
                             <div className="flex flex-wrap gap-2">
                               {selectedSkill.requiredTools.map((tool: string, i: number) => (
                                 <span key={i} className="px-2 py-1 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded text-xs font-mono">
                                   {tool}
                                 </span>
                               ))}
                             </div>
                           ) : <span className="text-xs text-slate-500">None</span>}
                         </div>
                         <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                           <span className="text-xs text-slate-500 mb-2 block">KNOWLEDGE PACKS</span>
                           {selectedSkill.requiredKnowledge.length > 0 ? (
                             <div className="flex flex-wrap gap-2">
                               {selectedSkill.requiredKnowledge.map((kp: string, i: number) => (
                                 <span key={i} className="px-2 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded text-xs font-mono">
                                   {kp}
                                 </span>
                               ))}
                             </div>
                           ) : <span className="text-xs text-slate-500">None</span>}
                         </div>
                       </div>
                     </div>
                   </div>

                   {/* Right Column */}
                   <div className="space-y-6">
                     <div>
                       <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                         <Layers className="w-4 h-4" /> <span>Declared Outputs</span>
                       </h3>
                       {selectedSkill.outputs.length > 0 ? (
                         <ul className="space-y-2">
                           {selectedSkill.outputs.map((out: string, i: number) => (
                             <li key={i} className="flex items-center space-x-3 text-sm text-slate-300 bg-slate-800/30 p-3 rounded-lg border border-slate-700/50">
                               <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                               <span className="font-mono break-words">{out}</span>
                             </li>
                           ))}
                         </ul>
                       ) : (
                         <div className="text-sm text-slate-500 italic p-3 bg-slate-900 rounded-lg border border-slate-800">No explicit outputs defined</div>
                       )}
                     </div>

                     <div>
                       <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                         <CheckCircle2 className="w-4 h-4" /> <span>Discharges Checklist Items</span>
                       </h3>
                       {selectedSkill.dischargesChecklist.length > 0 ? (
                         <ul className="space-y-2">
                           {selectedSkill.dischargesChecklist.map((item: string, i: number) => (
                             <li key={i} className="flex items-center space-x-3 text-sm text-slate-300 bg-slate-800/30 p-3 rounded-lg border border-slate-700/50">
                               <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                               <span className="font-mono">{item}</span>
                             </li>
                           ))}
                         </ul>
                       ) : (
                         <div className="text-sm text-slate-500 italic p-3 bg-slate-900 rounded-lg border border-slate-800">Does not discharge checklists</div>
                       )}
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
