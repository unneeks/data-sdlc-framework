import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Database, FileJson, Layers, Search, ChevronRight } from 'lucide-react';
import metamodelData from '../data/metamodel.json';

const ENTITIES = Object.keys(metamodelData).map(key => ({
  id: key,
  name: key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
  category: 'Metamodel Registry',
  data: (metamodelData as any)[key]
})).sort((a, b) => a.name.localeCompare(b.name));

export const MetamodelExplorer: React.FC = () => {
  const [search, setSearch] = useState('');
  const [selectedEntity, setSelectedEntity] = useState(ENTITIES[0]);

  const filteredEntities = ENTITIES.filter(e => 
    e.name.toLowerCase().includes(search.toLowerCase()) || 
    e.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col space-y-6">
      
      <div className="flex justify-between items-end">
        <div>
           <div className="inline-flex items-center space-x-2 text-indigo-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/20 mb-2">
             <Database className="w-4 h-4" />
             <span>Core Schema</span>
           </div>
           <h2 className="text-3xl font-extrabold text-white">Metamodel Explorer</h2>
           <p className="text-slate-400 mt-1">Drill down into the fundamental entities of the Agentic Data Engineering ecosystem.</p>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-6 overflow-hidden">
        
        {/* Left Pane: List */}
        <div className="glass-panel p-4 rounded-3xl border-slate-700/50 flex flex-col h-full overflow-hidden">
           <div className="relative mb-4">
             <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
             <input
               type="text"
               value={search}
               onChange={(e) => setSearch(e.target.value)}
               placeholder="Search entities..."
               className="w-full bg-slate-900 border border-slate-700 rounded-xl py-2 pl-9 pr-4 text-sm text-white focus:outline-none focus:border-indigo-500 transition"
             />
           </div>
           
           <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2 pr-2">
             {filteredEntities.map((entity) => (
               <button
                 key={entity.id}
                 onClick={() => setSelectedEntity(entity)}
                 className={`w-full text-left p-4 rounded-2xl transition flex items-center justify-between group ${
                   selectedEntity.id === entity.id 
                     ? 'bg-indigo-600 border border-indigo-500 shadow-lg shadow-indigo-900/50' 
                     : 'bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:border-slate-700'
                 }`}
               >
                 <div>
                   <h3 className={`font-bold ${selectedEntity.id === entity.id ? 'text-white' : 'text-slate-300 group-hover:text-white'}`}>
                     {entity.name}
                   </h3>
                   <span className={`text-[10px] font-mono uppercase tracking-wider ${selectedEntity.id === entity.id ? 'text-indigo-200' : 'text-slate-500'}`}>
                     {entity.category}
                   </span>
                 </div>
                 <ChevronRight className={`w-5 h-5 ${selectedEntity.id === entity.id ? 'text-white' : 'text-slate-600'}`} />
               </button>
             ))}
           </div>
        </div>

        {/* Right Pane: Details */}
        <div className="md:col-span-2 glass-panel p-6 rounded-3xl border-slate-700/50 flex flex-col h-full overflow-hidden">
           {selectedEntity ? (
             <motion.div 
               key={selectedEntity.id}
               initial={{ opacity: 0, y: 10 }}
               animate={{ opacity: 1, y: 0 }}
               className="h-full flex flex-col"
             >
                <div className="mb-6 pb-6 border-b border-slate-800 flex justify-between items-start">
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-2">{selectedEntity.name}</h2>
                    <p className="text-slate-400">Source: metamodel-registry/{selectedEntity.id}.yaml</p>
                  </div>
                  <div className="px-3 py-1 rounded bg-slate-900 border border-slate-800 text-xs font-mono text-slate-500">
                    Schema Definition
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar relative">
                  <div className="absolute top-4 right-4 text-slate-600"><FileJson className="w-6 h-6" /></div>
                  <pre className="bg-slate-950 p-6 rounded-2xl border border-slate-800 text-sm font-mono text-indigo-300 whitespace-pre-wrap leading-relaxed h-full overflow-y-auto">
{JSON.stringify(selectedEntity.data, null, 2)}
                  </pre>
                </div>
             </motion.div>
           ) : (
             <div className="flex-1 flex flex-col items-center justify-center text-slate-500">
                <Layers className="w-12 h-12 mb-4 opacity-20" />
                <p>Select an entity to view its schema</p>
             </div>
           )}
        </div>

      </div>
    </div>
  );
};
