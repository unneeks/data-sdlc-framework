import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle2, AlertTriangle, AlertCircle, Search, Layers, FileText, Target, Crosshair, ListChecks, ShieldAlert, BarChart } from 'lucide-react';

// Data Models
type RAGStatus = 'GREEN' | 'AMBER' | 'RED';

interface DeliveryActivity {
  id: string;
  name: string;
  status: RAGStatus;
  input: string[];
  tasks: string[];
  outputs: string[];
  scope: string;
  artifacts: { name: string; reliability: 'RELIABLE' | 'PARTIAL' | 'MISSING' }[];
  risks: string[];
  qualityMetrics: string[];
}

interface DeliveryPhase {
  id: string;
  name: string;
  activities: DeliveryActivity[];
}

// Generate Mock Data based on the screenshot
const generateMockData = (): DeliveryPhase[] => {
  const getRAG = (id: string): RAGStatus => {
    // Deterministic mock based on ID
    const hash = id.split('.').reduce((acc, val) => acc + parseInt(val), 0);
    if (hash % 3 === 0) return 'RED';
    if (hash % 2 === 0) return 'AMBER';
    return 'GREEN';
  };

  const createActivity = (id: string, name: string): DeliveryActivity => {
    const status = getRAG(id);
    
    // Determine artifact reliability based on RAG status
    let artifactReliability: 'RELIABLE' | 'PARTIAL' | 'MISSING' = 'RELIABLE';
    if (status === 'AMBER') artifactReliability = 'PARTIAL';
    if (status === 'RED') artifactReliability = 'MISSING';

    return {
      id,
      name,
      status,
      input: [`${name} Input Document`, 'Business Requirements', 'Architecture Guidelines'],
      tasks: [`Review current state for ${name}`, `Identify gaps for ${name}`, `Draft ${name} artifacts`],
      outputs: [`Approved ${name} Specification`, `${name} Sign-off`],
      scope: `The scope of this activity covers all required tasks to fulfill ${name} phase requirements.`,
      artifacts: [
        { name: `${name} Architecture Doc`, reliability: artifactReliability },
        { name: `${name} Compliance Check`, reliability: status === 'GREEN' ? 'RELIABLE' : 'MISSING' }
      ],
      risks: [
        status === 'RED' ? 'High risk of non-compliance due to missing artifacts.' : 'Standard operational risks apply.',
        'Resource constraints may delay activity.'
      ],
      qualityMetrics: [
        'Artifact Completeness Score',
        'Peer Review Pass Rate',
        status === 'RED' ? 'Verifiability: 0%' : status === 'AMBER' ? 'Verifiability: 50%' : 'Verifiability: 100%'
      ]
    };
  };

  return [
    {
      id: '1', name: '1. Ideation',
      activities: [
        createActivity('1.1', 'Assess Opportunity'),
        createActivity('1.2', 'Feasibility - Analyse Current State'),
        createActivity('1.3', 'Feasibility - Define Future State'),
        createActivity('1.4', 'Feasibility - Define Change Plan')
      ]
    },
    {
      id: '2', name: '2. Plan & Monitor',
      activities: [
        createActivity('2.1', 'Identify Change Delivery Controls'),
        createActivity('2.2', 'Plan Change'),
        createActivity('2.3', 'Manage Change'),
        createActivity('2.4', 'Secure Delivery Control Approvals'),
        createActivity('2.5', 'Manage Change Risk'),
        createActivity('2.6', 'Govern Change'),
        createActivity('2.7', 'Transition To BAU')
      ]
    },
    {
      id: '3', name: '3. Design',
      activities: [
        createActivity('3.1', 'Architect Solution'),
        createActivity('3.2', 'Design Data Solution'),
        createActivity('3.3', 'Secure Data Governance Approvals'),
        createActivity('3.4', 'Design Technical Solution'),
        createActivity('3.5', 'Develop Solution Requirements'),
        createActivity('3.6', 'Plan Testing'),
        createActivity('3.7', 'Specify Test Cases')
      ]
    },
    {
      id: '4', name: '4. Build & Test',
      activities: [
        createActivity('4.1', 'Establish Solution Environments'),
        createActivity('4.2', 'Automate Test Cases'),
        createActivity('4.3', 'Develop Data Platform Pattern'),
        createActivity('4.4', 'Develop Data Solution'),
        createActivity('4.5', 'Test Solution'),
        createActivity('4.6', 'Document Built Solution'),
        createActivity('4.7', 'Assess Solution Security'),
        createActivity('4.8', 'Assess Solution Risk')
      ]
    },
    {
      id: '5', name: '5. Release',
      activities: [
        createActivity('5.1', 'Plan Release'),
        createActivity('5.2', 'Test Solution Deployment'),
        createActivity('5.3', 'Test Delivery Controls'),
        createActivity('5.4', 'Create Change Record'),
        createActivity('5.5', 'Secure Change Record Approval'),
        createActivity('5.6', 'Deploy solution'),
        createActivity('5.7', 'Close Change Record'),
        createActivity('5.8', 'Update Configuration Management Database')
      ]
    }
  ];
};

const PHASES = generateMockData();

export const DeliveryModelIndex: React.FC = () => {
  const [selectedActivity, setSelectedActivity] = useState<DeliveryActivity | null>(null);

  const getStatusColor = (status: RAGStatus) => {
    switch (status) {
      case 'GREEN': return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400';
      case 'AMBER': return 'bg-amber-500/10 border-amber-500/30 text-amber-400';
      case 'RED': return 'bg-rose-500/10 border-rose-500/30 text-rose-400';
    }
  };

  const getStatusIcon = (status: RAGStatus) => {
    switch (status) {
      case 'GREEN': return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'AMBER': return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'RED': return <AlertCircle className="w-4 h-4 text-rose-400" />;
    }
  };

  return (
    <div className="w-full">
      {/* Overview Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
         <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center">
            <span className="text-2xl font-black text-indigo-400 mb-1">34</span>
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Total Activities</span>
         </div>
         <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-500/20 flex flex-col items-center justify-center">
            <span className="text-2xl font-black text-emerald-400 mb-1">
               {PHASES.flatMap(p => p.activities).filter(a => a.status === 'GREEN').length}
            </span>
            <span className="text-[10px] text-emerald-500/70 font-bold uppercase tracking-widest">Reliable</span>
         </div>
         <div className="p-4 rounded-2xl bg-amber-950/20 border border-amber-500/20 flex flex-col items-center justify-center">
            <span className="text-2xl font-black text-amber-400 mb-1">
               {PHASES.flatMap(p => p.activities).filter(a => a.status === 'AMBER').length}
            </span>
            <span className="text-[10px] text-amber-500/70 font-bold uppercase tracking-widest">Partial</span>
         </div>
         <div className="p-4 rounded-2xl bg-rose-950/20 border border-rose-500/20 flex flex-col items-center justify-center">
            <span className="text-2xl font-black text-rose-400 mb-1">
               {PHASES.flatMap(p => p.activities).filter(a => a.status === 'RED').length}
            </span>
            <span className="text-[10px] text-rose-500/70 font-bold uppercase tracking-widest">Missing / Risk</span>
         </div>
      </div>

      {/* Phases Grid */}
      <div className="flex space-x-6 overflow-x-auto pb-4 snap-x">
        {PHASES.map((phase) => (
          <div key={phase.id} className="flex-none w-80 snap-start space-y-4">
            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 sticky top-0 z-10 backdrop-blur-md">
              <h3 className="font-bold text-white text-sm">{phase.name}</h3>
            </div>
            
            <div className="space-y-3">
              {phase.activities.map((activity) => (
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  key={activity.id}
                  onClick={() => setSelectedActivity(activity)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${getStatusColor(activity.status)} hover:bg-opacity-20`}
                >
                  <div className="flex items-start justify-between">
                    <div className="pr-4">
                      <span className="text-xs font-mono opacity-60 mb-1 block">{activity.id}</span>
                      <h4 className="text-sm font-semibold leading-tight">{activity.name}</h4>
                    </div>
                    <div className="shrink-0 mt-0.5">{getStatusIcon(activity.status)}</div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Drill-down Modal */}
      <AnimatePresence>
        {selectedActivity && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40"
              onClick={() => setSelectedActivity(null)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-full md:max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-700 rounded-3xl shadow-2xl z-50 flex flex-col overflow-hidden"
            >
              {/* Modal Header */}
              <div className={`p-6 border-b flex justify-between items-center shrink-0 ${
                  selectedActivity.status === 'GREEN' ? 'border-emerald-500/20 bg-emerald-500/5' :
                  selectedActivity.status === 'AMBER' ? 'border-amber-500/20 bg-amber-500/5' :
                  'border-rose-500/20 bg-rose-500/5'
              }`}>
                <div>
                  <div className="flex items-center space-x-3 mb-1">
                     {getStatusIcon(selectedActivity.status)}
                     <span className="text-sm font-mono opacity-70 text-slate-300">{selectedActivity.id}</span>
                  </div>
                  <h2 className="text-2xl font-bold text-white">{selectedActivity.name}</h2>
                </div>
                <button
                  onClick={() => setSelectedActivity(null)}
                  className="p-2 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white transition"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-8 custom-scrollbar">
                
                {/* Artifacts & Verification Status */}
                <div>
                   <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-4">
                     <ShieldAlert className="w-4 h-4" /> <span>Artifact Verifiability</span>
                   </h3>
                   <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     {selectedActivity.artifacts.map((art, i) => (
                        <div key={i} className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                           <span className="text-sm text-slate-300">{art.name}</span>
                           <span className={`text-xs font-bold px-2 py-1 rounded ${
                             art.reliability === 'RELIABLE' ? 'bg-emerald-500/20 text-emerald-400' :
                             art.reliability === 'PARTIAL' ? 'bg-amber-500/20 text-amber-400' :
                             'bg-rose-500/20 text-rose-400'
                           }`}>
                             {art.reliability}
                           </span>
                        </div>
                     ))}
                   </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {/* Left Column */}
                  <div className="space-y-8">
                    <div>
                      <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                        <Target className="w-4 h-4" /> <span>Scope</span>
                      </h3>
                      <p className="text-sm text-slate-300 bg-slate-950 p-4 rounded-xl border border-slate-800 leading-relaxed">
                        {selectedActivity.scope}
                      </p>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                        <FileText className="w-4 h-4" /> <span>Inputs</span>
                      </h3>
                      <ul className="space-y-2">
                        {selectedActivity.input.map((item, i) => (
                          <li key={i} className="flex items-center space-x-3 text-sm text-slate-300 bg-slate-800/30 p-2.5 rounded-lg">
                             <div className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                             <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                        <Layers className="w-4 h-4" /> <span>Outputs</span>
                      </h3>
                      <ul className="space-y-2">
                        {selectedActivity.outputs.map((item, i) => (
                          <li key={i} className="flex items-center space-x-3 text-sm text-slate-300 bg-slate-800/30 p-2.5 rounded-lg">
                             <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                             <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Right Column */}
                  <div className="space-y-8">
                     <div>
                      <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                        <ListChecks className="w-4 h-4" /> <span>Tasks</span>
                      </h3>
                      <ul className="space-y-2">
                        {selectedActivity.tasks.map((item, i) => (
                          <li key={i} className="flex items-center space-x-3 text-sm text-slate-300 bg-slate-800/30 p-2.5 rounded-lg border border-slate-700/50">
                             <CheckCircle2 className="w-4 h-4 text-slate-500" />
                             <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                        <AlertTriangle className="w-4 h-4" /> <span>Risks</span>
                      </h3>
                      <ul className="space-y-2">
                        {selectedActivity.risks.map((item, i) => (
                          <li key={i} className="flex items-start space-x-3 text-sm text-rose-300 bg-rose-950/20 p-3 rounded-xl border border-rose-900/30">
                             <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                             <span className="leading-tight">{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-2 mb-3">
                        <BarChart className="w-4 h-4" /> <span>Quality Metrics</span>
                      </h3>
                      <ul className="space-y-2">
                        {selectedActivity.qualityMetrics.map((item, i) => (
                          <li key={i} className="flex items-center space-x-3 text-sm text-indigo-200 bg-indigo-950/20 p-2.5 rounded-lg border border-indigo-900/30 font-mono text-xs">
                             <Crosshair className="w-4 h-4 text-indigo-400" />
                             <span>{item}</span>
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
