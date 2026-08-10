import React, { useState, useEffect } from 'react';
import { Briefcase, GitBranch, Database, FileText, CheckCircle2, ChevronRight, Activity, Scan, Cpu, ShieldCheck, Play, Link as LinkIcon, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { DeliveryModelIndex } from './DeliveryModelIndex';

export const BusinessAppOnboarding: React.FC = () => {
  const [repoUrl, setRepoUrl] = useState('');
  const [intentUrl, setIntentUrl] = useState('');
  const [portalUrl, setPortalUrl] = useState('');
  const [step, setStep] = useState(0); // 0: Input, 1: Scan Repo, 2: Arch Discovery, 3: Historical, 4: Playbook
  
  // Simulated Agent Outputs
  const [techStack, setTechStack] = useState<string[]>([]);
  const [dqTestsFound, setDqTestsFound] = useState(0);
  const [archNodes, setArchNodes] = useState<any[]>([]);
  const [historicalStats, setHistoricalStats] = useState<any>(null);
  
  const handleStartOnboarding = () => {
    if (!repoUrl || !intentUrl || !portalUrl) return;
    setStep(1);
  };

  useEffect(() => {
    if (step === 1) {
      // Step 1: Repository & Tech Scan (project-discovery-agent)
      setTimeout(() => {
        setTechStack(['dbt', 'BigQuery', 'Airflow', 'Terraform']);
        setDqTestsFound(142);
        setStep(2);
      }, 2500);
    } else if (step === 2) {
      // Step 2: Architecture Discovery (architecture-discovery-agent)
      setTimeout(() => {
        setArchNodes([
          { layer: 'Source', type: 'Salesforce API', status: 'Inferred' },
          { layer: 'Storage', type: 'BigLake / Iceberg', status: 'Mapped to KG' },
          { layer: 'Transform', type: 'dbt Core models', status: 'Mapped to KG' }
        ]);
        setStep(3);
      }, 3000);
    } else if (step === 3) {
      // Step 3: Historical Change Analysis (metadata-discovery-agent)
      setTimeout(() => {
        setHistoricalStats({
          crsAnalyzed: 84,
          standardArtifacts: 62,
          driftDetected: 12
        });
        setStep(4);
      }, 2500);
    }
  }, [step]);

  const containerVariants: any = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants: any = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <div className="space-y-10 pb-12">
      {/* Header Banner */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="glass-panel p-10 rounded-3xl relative overflow-hidden bg-gradient-to-br from-indigo-950/60 via-slate-900 to-slate-950 border border-indigo-500/20 shadow-2xl"
      >
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-indigo-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/3 pointer-events-none" />
        
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-bold uppercase tracking-widest">
            <Briefcase className="w-3.5 h-3.5" />
            <span>Delivery Model Analysis</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight leading-tight">
            Ecosystem Discovery & Assessment
          </h2>
          <p className="text-slate-400 text-sm md:text-base leading-relaxed max-w-2xl">
            Provide the coordinates to your project's ecosystem. Our autonomous agents will assess the GitHub repository, Solution Intent, and Request Portal against the Institutional Delivery Model to identify gaps and missing artifacts.
          </p>
        </div>
      </motion.div>

      {/* Input Stage */}
      {step === 0 && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-4xl mx-auto space-y-6">
          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 via-cyan-500 to-emerald-500 rounded-3xl blur opacity-25 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
            <div className="relative glass-panel p-6 rounded-3xl bg-slate-950/90 border border-slate-700 space-y-4">
              
              <div className="flex items-center bg-slate-900 border border-slate-800 rounded-2xl px-4 py-2">
                <GitBranch className="w-5 h-5 text-indigo-400 mr-3" />
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="GitHub Repository URL (e.g., https://github.com/enterprise/customer-360-data)"
                  className="flex-1 bg-transparent border-none py-3 text-sm text-white focus:outline-none placeholder-slate-600 font-mono"
                />
              </div>

              <div className="flex items-center bg-slate-900 border border-slate-800 rounded-2xl px-4 py-2">
                <FileText className="w-5 h-5 text-emerald-400 mr-3" />
                <input
                  type="text"
                  value={intentUrl}
                  onChange={(e) => setIntentUrl(e.target.value)}
                  placeholder="Solution Intent URL (e.g., Confluence / SharePoint)"
                  className="flex-1 bg-transparent border-none py-3 text-sm text-white focus:outline-none placeholder-slate-600 font-mono"
                />
              </div>

              <div className="flex items-center bg-slate-900 border border-slate-800 rounded-2xl px-4 py-2">
                <ExternalLink className="w-5 h-5 text-amber-400 mr-3" />
                <input
                  type="text"
                  value={portalUrl}
                  onChange={(e) => setPortalUrl(e.target.value)}
                  placeholder="Request Portal URL (e.g., Jira / ServiceNow)"
                  className="flex-1 bg-transparent border-none py-3 text-sm text-white focus:outline-none placeholder-slate-600 font-mono"
                />
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  onClick={handleStartOnboarding}
                  disabled={!repoUrl || !intentUrl || !portalUrl}
                  className="px-8 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold shadow-lg shadow-indigo-600/30 flex items-center space-x-2 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>Initialize Delivery Model Assessment</span>
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>

            </div>
          </div>
        </motion.div>
      )}

      {/* Discovery Wizard Progress */}
      {step > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          
          {/* Progress Timeline */}
          <div className="glass-panel p-8 rounded-3xl h-fit border-slate-800">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-8">Discovery Pipeline</h3>
            <div className="relative">
              <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-800/80" />
              
              <div className="space-y-8 relative">
                {[
                  { s: 1, title: 'Repository & Tech Scan', agent: 'project-discovery-agent', icon: Scan },
                  { s: 2, title: 'Architecture Discovery', agent: 'architecture-discovery-agent', icon: Database },
                  { s: 3, title: 'Historical Analysis', agent: 'metadata-discovery-agent', icon: Activity },
                  { s: 4, title: 'Playbook Generation', agent: 'solution-architecture-agent', icon: FileText }
                ].map((phase) => {
                  const isActive = phase.s === step;
                  const isCompleted = phase.s < step;
                  const Icon = phase.icon;

                  return (
                    <div key={phase.s} className="flex items-start">
                      <div className="relative z-10 flex items-center justify-center w-8 h-8 rounded-xl shrink-0 mt-0.5 bg-slate-950 border">
                        {isCompleted ? (
                           <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : isActive ? (
                           <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse glow-blue" />
                        ) : (
                           <Icon className="w-4 h-4 text-slate-600" />
                        )}
                        <div className={`absolute inset-0 rounded-xl border pointer-events-none transition-colors ${isCompleted ? 'border-emerald-500/50 bg-emerald-500/5' : isActive ? 'border-indigo-500 glow-blue' : 'border-slate-800'}`} />
                      </div>
                      <div className="ml-5">
                        <h4 className={`text-sm font-bold ${isActive ? 'text-indigo-300' : isCompleted ? 'text-white' : 'text-slate-500'}`}>
                          {phase.title}
                        </h4>
                        <p className={`text-[10px] font-mono mt-1 ${isActive ? 'text-indigo-400' : 'text-slate-600'}`}>
                          Role: {phase.agent}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Dynamic Content Area */}
          <div className="xl:col-span-2 space-y-6">
            <AnimatePresence mode="wait">
              {/* Step 1: Scan */}
              {step === 1 && (
                <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="glass-panel p-8 rounded-3xl space-y-6">
                  <div className="flex items-center space-x-3 text-indigo-400 mb-2">
                    <Scan className="w-6 h-6 animate-pulse" />
                    <h3 className="text-xl font-bold text-white">Scanning GitHub Repository</h3>
                  </div>
                  <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 font-mono text-sm text-slate-300">
                    <div className="flex items-center space-x-2"><Cpu className="w-4 h-4 text-slate-500" /><span>Cloning source tree...</span></div>
                    <div className="flex items-center space-x-2"><Cpu className="w-4 h-4 text-slate-500" /><span>Extracting dependencies (requirements.txt, dbt_project.yml)...</span></div>
                    <div className="flex items-center space-x-2 text-indigo-400"><Cpu className="w-4 h-4" /><span>Identifying implicit coding standards...</span></div>
                  </div>
                </motion.div>
              )}

              {/* Step 2: Architecture */}
              {step >= 2 && step <= 3 && (
                <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="glass-panel p-8 rounded-3xl space-y-6">
                  <div className="flex items-center space-x-3 text-emerald-400 mb-2">
                    {step === 2 ? <Database className="w-6 h-6 animate-pulse" /> : <CheckCircle2 className="w-6 h-6" />}
                    <h3 className="text-xl font-bold text-white">Architecture Discovery & KG Mapping</h3>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-2">Detected Techset</div>
                      <div className="flex flex-wrap gap-2">
                        {techStack.map((tech, i) => (
                          <span key={i} className="px-2 py-1 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-xs font-mono">{tech}</span>
                        ))}
                      </div>
                    </div>
                    <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-2">Quality & Testing</div>
                      <div className="text-2xl font-bold text-emerald-400">{dqTestsFound} <span className="text-sm font-normal text-slate-400">DQ tests extracted</span></div>
                    </div>
                  </div>

                  <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                    <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-2">Inferred Technical Architecture</div>
                    {archNodes.map((node, i) => (
                      <div key={i} className="flex justify-between items-center text-sm border-b border-slate-800/50 pb-2 last:border-0 last:pb-0">
                        <span className="text-slate-400 w-24">{node.layer}</span>
                        <span className="text-white font-mono flex-1">{node.type}</span>
                        <span className="text-emerald-400 text-xs">{node.status}</span>
                      </div>
                    ))}
                  </div>

                  {step === 3 && (
                     <div className="mt-6 pt-6 border-t border-slate-800/80">
                        <div className="flex items-center space-x-3 text-amber-400 mb-4">
                          <Activity className="w-5 h-5 animate-pulse" />
                          <h3 className="text-lg font-bold text-white">Analyzing Historical Changes...</h3>
                        </div>
                     </div>
                  )}
                </motion.div>
              )}

              {/* Step 4: Playbook & Gap Analysis */}
              {step === 4 && (
                <motion.div key="step4" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="space-y-6">
                  
                  <div className="flex justify-between items-center mb-6">
                     <div>
                       <div className="inline-flex items-center space-x-2 text-indigo-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/20 mb-2">
                         <ShieldCheck className="w-4 h-4" />
                         <span>Assessment Complete</span>
                       </div>
                       <h3 className="text-2xl font-bold text-white">Institutional Data Delivery Model Status</h3>
                     </div>
                  </div>

                  <DeliveryModelIndex />

                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
};
