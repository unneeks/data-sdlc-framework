import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw, CheckCircle2, AlertTriangle, ShieldAlert, Terminal, Layers, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  demoState: { current_step: number; total_steps: number; step_details: any };
  onNextStep: () => void;
  onResetDemo: () => void;
}

export const HeroDemoSimulation: React.FC<Props> = ({ demoState, onNextStep, onResetDemo }) => {
  const [showBrownfieldChange, setShowBrownfieldChange] = useState(false);
  const terminalRef = useRef<HTMLDivElement>(null);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([
    "[System] Waiting for simulation trigger..."
  ]);

  const sdlcPhases = [
    { step: 1, title: 'CR Ingestion', agent: 'Change Ingestion' },
    { step: 2, title: 'Classification', agent: 'Classifier Engine' },
    { step: 3, title: 'Feasibility Assessment', agent: 'Migration Architect Agent' },
    { step: 4, title: 'Data Design', agent: 'Data Modeling Agent' },
    { step: 5, title: 'Code Update', agent: 'Pipeline Agent' },
    { step: 6, title: 'Reconciliation Testing', agent: 'Regression & DQ Agent' },
    { step: 7, title: 'Root Cause Analysis', agent: 'Test Failure Analysis Agent' },
    { step: 8, title: 'Gate Assessment', agent: 'Delivery Compliance Agent' },
    { step: 9, title: 'Remediation & PR', agent: 'Remediation Engine' }
  ];

  useEffect(() => {
    if (demoState.current_step > 1) {
      setTerminalLogs(prev => [...prev, `[Agent] Executing Step ${demoState.current_step}: ${demoState.step_details.title}`, `[System] ${demoState.step_details.details}`]);
    } else {
      setTerminalLogs(["[System] Waiting for simulation trigger..."]);
    }
  }, [demoState.current_step]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [terminalLogs]);

  return (
    <div className="space-y-8 pb-12">
      {/* Top Banner */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 rounded-3xl relative overflow-hidden"
      >
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-cyan-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/4 pointer-events-none" />
        
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-3">
            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 text-xs font-bold border border-cyan-500/20 uppercase tracking-widest">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Continuous Delivery Simulation</span>
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">CR-2026-8942: Source Feed to Lakehouse</h2>
            <p className="text-slate-400 text-sm max-w-xl">
              Redirecting Salesforce & SAP CRM source feeds from legacy Data Warehouse to Cloud Lakehouse (Iceberg/BigLake).
            </p>
          </div>

          <div className="flex items-center space-x-4">
            <button
              onClick={onNextStep}
              className="px-8 py-4 rounded-2xl bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-bold text-sm shadow-xl shadow-cyan-600/20 flex items-center space-x-3 transition transform hover:-translate-y-1"
            >
              <Play className="w-5 h-5 fill-current" />
              <span>Simulate Next Phase</span>
            </button>
            <button onClick={onResetDemo} className="p-4 rounded-2xl bg-slate-900 border border-slate-700 text-slate-400 hover:text-white transition" title="Reset">
              <RotateCcw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Timeline Stepper */}
        <div className="xl:col-span-2 space-y-6">
          <div className="flex items-center space-x-3 text-white">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h3 className="text-lg font-bold">Multi-Agent Delivery Progression</h3>
          </div>
          
          <div className="glass-panel p-8 rounded-3xl">
            <div className="relative">
              {/* Connecting Line */}
              <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-slate-800" />
              
              <div className="space-y-8 relative">
                {sdlcPhases.map((phase) => {
                  const isActive = phase.step === demoState.current_step;
                  const isCompleted = phase.step < demoState.current_step;
                  const isFailed = (demoState.current_step >= 6 && phase.step === 6) || (demoState.current_step >= 8 && phase.step === 8);

                  return (
                    <motion.div 
                      key={phase.step}
                      initial={false}
                      animate={{ opacity: isActive || isCompleted ? 1 : 0.4 }}
                      className="flex items-start"
                    >
                      <div className="relative z-10 flex items-center justify-center w-12 h-12 rounded-2xl shrink-0 mt-0.5 bg-slate-950 border-2">
                        {isCompleted ? (
                           <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                        ) : isActive ? (
                           <div className="w-3 h-3 rounded-full bg-indigo-500 animate-pulse glow-blue" />
                        ) : (
                           <span className="text-slate-500 font-bold text-sm">{phase.step}</span>
                        )}
                        {/* Dynamic Border based on status */}
                        <div className={`absolute inset-0 rounded-2xl border-2 pointer-events-none transition-colors ${isCompleted ? 'border-emerald-500/50 bg-emerald-500/5' : isActive ? 'border-indigo-500 glow-blue' : 'border-slate-800'}`} />
                      </div>
                      
                      <div className="ml-6 flex-1">
                        <div className={`p-5 rounded-2xl border transition-all ${
                          isActive ? 'bg-indigo-950/40 border-indigo-500/50 shadow-lg shadow-indigo-500/20' : 
                          isCompleted && isFailed ? 'bg-rose-950/20 border-rose-500/30' :
                          isCompleted ? 'bg-slate-900/60 border-slate-700' : 'bg-transparent border-transparent'
                        }`}>
                          <h4 className={`text-base font-bold ${isActive ? 'text-indigo-300' : isCompleted ? 'text-white' : 'text-slate-400'}`}>
                            {phase.title}
                          </h4>
                          <p className="text-xs text-slate-500 mt-1.5 font-mono">Assigned Role: {phase.agent}</p>
                          
                          {isActive && (
                            <motion.div 
                              initial={{ opacity: 0, height: 0 }} 
                              animate={{ opacity: 1, height: 'auto' }}
                              className="mt-4 pt-4 border-t border-indigo-500/30"
                            >
                              <p className="text-sm text-slate-300">{demoState.step_details.details}</p>
                            </motion.div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Live Terminal & Brownfield triggers */}
        <div className="space-y-6">
          <div className="flex items-center justify-between text-white">
            <div className="flex items-center space-x-3">
              <Terminal className="w-5 h-5 text-emerald-400" />
              <h3 className="text-lg font-bold">Execution Console</h3>
            </div>
          </div>

          <div className="glass-panel rounded-3xl border-slate-700 overflow-hidden flex flex-col h-[400px]">
            <div className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-rose-500" />
              <div className="w-3 h-3 rounded-full bg-amber-500" />
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              <span className="ml-4 text-[10px] font-mono text-slate-500 uppercase tracking-widest">agentic-orchestrator.log</span>
            </div>
            <div ref={terminalRef} className="flex-1 p-4 bg-[#0a0a0a] overflow-y-auto custom-scrollbar font-mono text-xs space-y-2">
              {terminalLogs.map((log, i) => (
                <div key={i} className={`${log.startsWith('[System]') ? 'text-slate-500' : log.startsWith('[Agent]') ? 'text-indigo-400 font-bold' : 'text-emerald-400'}`}>
                  {log}
                </div>
              ))}
              <div className="w-2 h-4 bg-slate-500 animate-pulse mt-2" />
            </div>
          </div>

          <motion.div 
            whileHover={{ scale: 1.02 }}
            className="p-6 rounded-3xl bg-gradient-to-br from-amber-950/40 to-slate-900 border border-amber-500/30 cursor-pointer"
            onClick={() => setShowBrownfieldChange(!showBrownfieldChange)}
          >
            <div className="flex items-center space-x-3 text-amber-400 mb-2">
              <ShieldAlert className="w-5 h-5" />
              <h4 className="font-bold text-sm uppercase tracking-widest">Trigger Brownfield Anomaly</h4>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">Simulate a mid-migration upstream schema change (SAP `STATUS` format change) to test continuous reconciliation.</p>
            
            <AnimatePresence>
              {showBrownfieldChange && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-4 pt-4 border-t border-amber-500/30"
                >
                  <div className="text-xs text-slate-300 space-y-2 font-mono">
                    <div>&gt; SOURCE_SCHEMA_CHANGE detected</div>
                    <div className="text-amber-400">&gt; Re-planning Delivery Graph...</div>
                    <div className="text-emerald-400">&gt; Duplicate regression tasks dropped. Blueprint merged.</div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>
    </div>
  );
};
