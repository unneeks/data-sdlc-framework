import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw, CheckCircle2, AlertTriangle, ShieldAlert, Terminal, Layers, Sparkles, Activity } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchDashboard, triggerRun, AgentDashboardState } from '../services/ollamaApi';

export const HeroDemoSimulation: React.FC = () => {
  const [dashboard, setDashboard] = useState<AgentDashboardState | null>(null);
  const [prompt, setPrompt] = useState('Why did the nightly customer ETL job fail and how do we fix it?');
  const [isPolling, setIsPolling] = useState(true);
  const terminalRef = useRef<HTMLDivElement>(null);

  // Poll dashboard
  useEffect(() => {
    let interval: any;
    if (isPolling) {
      interval = setInterval(async () => {
        try {
          const data = await fetchDashboard();
          setDashboard(data);
        } catch (e) {
          console.error("Failed to fetch dashboard", e);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPolling]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [dashboard?.latest_log_tail]);

  const handleTriggerRun = async () => {
    try {
      await triggerRun(prompt);
    } catch (e) {
      console.error(e);
    }
  };

  const mapPhaseToStep = (phase: string) => {
    switch (phase) {
      case 'idle': return 0;
      case 'understand_request': return 1;
      case 'create_plan': return 2;
      case 'execute_tools': return 3;
      case 'reflect_on_results': return 4;
      case 'generate_fix': return 5;
      case 'raise_change_record': return 6;
      case 'verify_fix': return 7;
      case 'return_final_answer': return 8;
      default: return 0;
    }
  };

  const currentStep = dashboard ? mapPhaseToStep(dashboard.agent_phase) : 0;

  const sdlcPhases = [
    { step: 1, phase_id: 'understand_request', title: 'Goal Understanding', agent: 'Goal Architect' },
    { step: 2, phase_id: 'create_plan', title: 'Planning', agent: 'Execution Planner' },
    { step: 3, phase_id: 'execute_tools', title: 'Tool Execution', agent: 'Tool Executor' },
    { step: 4, phase_id: 'reflect_on_results', title: 'Reflection & RCA', agent: 'Diagnostics Engine' },
    { step: 5, phase_id: 'generate_fix', title: 'Fix Generation', agent: 'Remediation Agent' },
    { step: 6, phase_id: 'raise_change_record', title: 'Change Control', agent: 'Compliance Gatekeeper' },
    { step: 7, phase_id: 'verify_fix', title: 'Verification', agent: 'Testing Agent' },
    { step: 8, phase_id: 'return_final_answer', title: 'Final Answer', agent: 'Incident Commander' }
  ];

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
          <div className="space-y-3 flex-1">
            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 text-xs font-bold border border-cyan-500/20 uppercase tracking-widest">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Live Agentic AI Integration</span>
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">Ollama Incident Investigator</h2>
            
            <div className="flex items-center space-x-4 mt-4">
              <input 
                type="text" 
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={handleTriggerRun}
                className="px-8 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-bold text-sm shadow-xl shadow-cyan-600/20 flex items-center space-x-3 transition transform hover:-translate-y-1"
              >
                <Play className="w-5 h-5 fill-current" />
                <span>Invoke Agent</span>
              </button>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Timeline Stepper */}
        <div className="xl:col-span-2 space-y-6">
          <div className="flex items-center space-x-3 text-white">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h3 className="text-lg font-bold">LangGraph Execution Timeline</h3>
            {dashboard?.incident_active && (
              <span className="ml-auto px-3 py-1 bg-rose-500/20 border border-rose-500/50 text-rose-400 text-xs font-bold rounded-lg uppercase animate-pulse">
                Incident Active
              </span>
            )}
          </div>
          
          <div className="glass-panel p-8 rounded-3xl">
            <div className="relative">
              <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-slate-800" />
              
              <div className="space-y-8 relative">
                {sdlcPhases.map((phase) => {
                  const isActive = phase.step === currentStep;
                  const isCompleted = phase.step < currentStep || dashboard?.agent_status === 'completed';
                  
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
                        <div className={`absolute inset-0 rounded-2xl border-2 pointer-events-none transition-colors ${isCompleted ? 'border-emerald-500/50 bg-emerald-500/5' : isActive ? 'border-indigo-500 glow-blue' : 'border-slate-800'}`} />
                      </div>
                      
                      <div className="ml-6 flex-1">
                        <div className={`p-5 rounded-2xl border transition-all ${
                          isActive ? 'bg-indigo-950/40 border-indigo-500/50 shadow-lg shadow-indigo-500/20' : 
                          isCompleted ? 'bg-slate-900/60 border-slate-700' : 'bg-transparent border-transparent'
                        }`}>
                          <h4 className={`text-base font-bold ${isActive ? 'text-indigo-300' : isCompleted ? 'text-white' : 'text-slate-400'}`}>
                            {phase.title}
                          </h4>
                          <p className="text-xs text-slate-500 mt-1.5 font-mono">Mapped Role: {phase.agent}</p>
                          
                          {isActive && dashboard?.events && (
                            <motion.div 
                              initial={{ opacity: 0, height: 0 }} 
                              animate={{ opacity: 1, height: 'auto' }}
                              className="mt-4 pt-4 border-t border-indigo-500/30"
                            >
                              <div className="text-xs text-slate-300 font-mono space-y-1">
                                {dashboard.events.slice(-3).map((e, idx) => (
                                  <div key={idx}>{e.message}</div>
                                ))}
                              </div>
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

        {/* Live Terminal */}
        <div className="space-y-6">
          <div className="flex items-center justify-between text-white">
            <div className="flex items-center space-x-3">
              <Terminal className="w-5 h-5 text-emerald-400" />
              <h3 className="text-lg font-bold">Continuous Pipeline Monitor</h3>
            </div>
          </div>

          <div className="glass-panel rounded-3xl border-slate-700 overflow-hidden flex flex-col h-[500px]">
            <div className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-rose-500" />
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="ml-4 text-[10px] font-mono text-slate-500 uppercase tracking-widest">pipeline.log</span>
              </div>
              <Activity className={`w-4 h-4 ${dashboard?.system_state === 'healthy' ? 'text-emerald-500' : 'text-rose-500 animate-pulse'}`} />
            </div>
            <div ref={terminalRef} className="flex-1 p-4 bg-[#0a0a0a] overflow-y-auto custom-scrollbar font-mono text-xs space-y-2">
              {dashboard?.latest_log_tail?.map((line, i) => (
                <div key={i} className={`whitespace-pre-wrap break-words ${
                  line.includes('ERROR') || line.includes('FAIL') ? 'text-rose-400' : 
                  line.includes('WARN') ? 'text-amber-400' : 
                  'text-slate-400'
                }`}>
                  {line}
                </div>
              ))}
              <div className="w-2 h-4 bg-slate-500 animate-pulse mt-2" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
