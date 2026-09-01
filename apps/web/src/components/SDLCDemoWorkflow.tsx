import React, { useState, useEffect, useRef } from 'react';
import {
  Play, RotateCcw, CheckCircle2, Clock, Loader2, FileText, ChevronDown,
  ChevronRight, Zap, ArrowRight, Shield, ClipboardCheck, ExternalLink, Eye
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  sdlcDemoInitialize, sdlcDemoStatus, sdlcDemoApprove, sdlcDemoReset,
  SDLCStatus, SDLCDocument
} from '../services/api';

const STATE_META: Record<string, { label: string; activeClass: string; icon: React.ReactNode }> = {
  INIT:              { label: 'Not Started',       activeClass: 'border-slate-500 bg-slate-950/30 shadow-lg shadow-slate-500/10 ring-1 ring-slate-500/50', icon: <Clock className="w-4 h-4" /> },
  REQUIREMENTS_REVIEW: { label: 'Requirements Review', activeClass: 'border-amber-500 bg-amber-950/30 shadow-lg shadow-amber-500/10 ring-1 ring-amber-500/50', icon: <FileText className="w-4 h-4" /> },
  DESIGN_REVIEW:     { label: 'Design Review',     activeClass: 'border-indigo-500 bg-indigo-950/30 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500/50', icon: <ClipboardCheck className="w-4 h-4" /> },
  TEST_PLANNING:     { label: 'Test Planning',     activeClass: 'border-cyan-500 bg-cyan-950/30 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500/50', icon: <Loader2 className="w-4 h-4 animate-spin" /> },
  TEST_PLAN_REVIEW:  { label: 'Test Plan Review',  activeClass: 'border-violet-500 bg-violet-950/30 shadow-lg shadow-violet-500/10 ring-1 ring-violet-500/50', icon: <Shield className="w-4 h-4" /> },
  COMPLETED:         { label: 'Completed',         activeClass: 'border-emerald-500 bg-emerald-950/30 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/50', icon: <CheckCircle2 className="w-4 h-4" /> },
};

const ALL_STATES = ['REQUIREMENTS_REVIEW', 'DESIGN_REVIEW', 'TEST_PLANNING', 'TEST_PLAN_REVIEW', 'COMPLETED'];

export const SDLCDemoWorkflow: React.FC = () => {
  const [status, setStatus] = useState<SDLCStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState<string | null>(null);
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);
  const [expandedArtifact, setExpandedArtifact] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>(['[System] Click "Start Workflow" to begin the SDLC demo.']);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const addLog = (msg: string) => setLogs(prev => [...prev, msg]);

  const handleInitialize = async () => {
    setLoading(true);
    setLogs(['[System] Initializing SDLC orchestrator workflow...']);
    try {
      const result = await sdlcDemoInitialize();
      setStatus(result);
      addLog(`[Orchestrator] Workflow ${result.orchestrator_id} started`);
      addLog(`[Orchestrator] State: ${result.current_state} — ${result.state_description}`);
      if (Object.keys(result.documents).length > 0) {
        Object.values(result.documents).forEach(doc => {
          addLog(`[Document] ${doc.title} — Status: ${doc.status}`);
        });
      }
    } catch (e: any) {
      addLog(`[Error] ${e.message}`);
    }
    setLoading(false);
  };

  const handleApprove = async (docId: string) => {
    if (!status) return;
    setApproving(docId);
    const docTitle = status.documents[docId]?.title || docId;
    addLog(`[Action] Approving: ${docTitle}...`);

    let prevState = status.current_state;
    let agentLogged = false;

    try {
      const result = await sdlcDemoApprove(docId, (progress) => {
        setStatus(progress);
        // Log state changes and agent activity as they happen
        if (progress.current_state !== prevState) {
          addLog(`[Orchestrator] State: ${prevState} -> ${progress.current_state}`);
          if (progress.current_state === 'TEST_PLANNING' && !agentLogged) {
            addLog('[Agent] test-planner-agent invoked — generating test plan...');
            addLog('[Agent] This may take a few minutes in AGENTCORE mode.');
            agentLogged = true;
          }
          prevState = progress.current_state;
        }
      });

      const freshStatus = await sdlcDemoStatus();
      setStatus(freshStatus);

      addLog(`[Orchestrator] Approved: ${docTitle}`);

      if (freshStatus.current_state === 'TEST_PLAN_REVIEW' || freshStatus.current_state === 'COMPLETED') {
        const agentEntry = freshStatus.history.find(h => h.agent_key);
        if (agentEntry) {
          addLog(`[Agent] Completed: ${agentEntry.agent_key}`);
        }
        if (Object.keys(freshStatus.artifacts).length > 0) {
          addLog('[Artifact] Test plan draft generated — ready for review');
        }
      }

      addLog(`[Orchestrator] State: ${freshStatus.current_state} — ${freshStatus.state_description}`);

      Object.values(freshStatus.documents).forEach(doc => {
        if (doc.status === 'DRAFT') {
          addLog(`[Document] ${doc.title} — Status: ${doc.status}`);
        }
      });

      if (freshStatus.is_terminal) {
        addLog('[System] Workflow COMPLETED — all documents approved and finalized');
      }
    } catch (e: any) {
      addLog(`[Error] ${e.message}`);
      const freshStatus = await sdlcDemoStatus();
      setStatus(freshStatus);
    }
    setApproving(null);
  };

  const handleReset = async () => {
    await sdlcDemoReset();
    setStatus(null);
    setExpandedDoc(null);
    setExpandedArtifact(null);
    setLogs(['[System] Click "Start Workflow" to begin the SDLC demo.']);
  };

  const currentDraftDocs = status
    ? Object.values(status.documents).filter(d => d.status === 'DRAFT')
    : [];

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 rounded-3xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-violet-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/4 pointer-events-none" />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-3">
            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-violet-500/10 text-violet-300 text-xs font-bold border border-violet-500/20 uppercase tracking-widest">
              <Shield className="w-3.5 h-3.5" />
              <span>SDLC Orchestrator Demo</span>
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">Document Approval Workflow</h2>
            <p className="text-slate-400 text-sm max-w-xl">
              Demonstrates the orchestrator-driven SDLC flow: approve design and requirement documents,
              trigger the test plan agent via state machine transitions, review and finalize the generated test plan.
            </p>
          </div>

          <div className="flex gap-2">
            {!status ? (
              <button onClick={handleInitialize} disabled={loading}
                className="px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 transition">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Start Workflow
              </button>
            ) : (
              <button onClick={handleReset}
                className="px-4 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:text-white text-sm font-semibold flex items-center gap-2 transition">
                <RotateCcw className="w-4 h-4" /> Reset
              </button>
            )}
          </div>
        </div>
      </motion.div>

      {status && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Left: State Machine + Documents */}
          <div className="xl:col-span-2 space-y-6">
            {/* State Progress */}
            <div className="glass-panel rounded-3xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-violet-400" />
                State Machine Progress
              </h3>
              <div className="flex items-center gap-1 overflow-x-auto pb-2">
                {ALL_STATES.map((state, idx) => {
                  const meta = STATE_META[state] || STATE_META.INIT;
                  const isCurrent = status.current_state === state;
                  const isPast = ALL_STATES.indexOf(status.current_state) > idx;
                  const colorClass = isCurrent
                    ? meta.activeClass
                    : isPast
                    ? 'border-emerald-500/50 bg-emerald-950/20'
                    : 'border-slate-700 bg-slate-900/40';

                  return (
                    <React.Fragment key={state}>
                      {idx > 0 && (
                        <ArrowRight className={`w-4 h-4 shrink-0 ${isPast ? 'text-emerald-500' : 'text-slate-700'}`} />
                      )}
                      <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-semibold whitespace-nowrap transition-all ${colorClass} ${
                        isCurrent ? 'text-white' : isPast ? 'text-emerald-400' : 'text-slate-500'
                      }`}>
                        {isPast ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : meta.icon}
                        <span>{meta.label}</span>
                      </div>
                    </React.Fragment>
                  );
                })}
              </div>
            </div>

            {/* Agent Running Banner */}
            {status.current_state === 'TEST_PLANNING' && approving && (
              <motion.div
                initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl border border-cyan-500/40 bg-cyan-950/20 p-4"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-cyan-300">test-planner-agent running</div>
                    <div className="text-xs text-slate-400">
                      Generating test plan from approved documents. In AGENTCORE mode this may take 2-3 minutes.
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Document Cards */}
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-amber-400" />
                Documents
                <span className="text-sm font-normal text-slate-400 ml-2">
                  ({Object.keys(status.documents).length} total)
                </span>
              </h3>

              {Object.keys(status.documents).length === 0 ? (
                <div className="glass-panel rounded-2xl p-8 text-center">
                  <p className="text-slate-500 text-sm">Workflow will create documents as states progress.</p>
                </div>
              ) : (
                Object.values(status.documents).map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    doc={doc}
                    isExpanded={expandedDoc === doc.id}
                    onToggle={() => setExpandedDoc(expandedDoc === doc.id ? null : doc.id)}
                    canApprove={doc.status === 'DRAFT' && currentDraftDocs.some(d => d.id === doc.id)}
                    isApproving={approving === doc.id}
                    onApprove={() => handleApprove(doc.id)}
                  />
                ))
              )}
            </div>

            {/* Artifacts */}
            {Object.keys(status.artifacts).length > 0 && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <ExternalLink className="w-5 h-5 text-cyan-400" />
                  Generated Artifacts
                </h3>
                {Object.entries(status.artifacts).map(([key, artifact]) => (
                  <ArtifactCard
                    key={key}
                    artifactKey={key}
                    artifact={artifact}
                    isExpanded={expandedArtifact === key}
                    onToggle={() => setExpandedArtifact(expandedArtifact === key ? null : key)}
                  />
                ))}
              </div>
            )}

            {/* History Timeline */}
            {status.history.length > 0 && (
              <div className="glass-panel rounded-3xl p-6">
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">
                  Transition History
                </h3>
                <div className="space-y-3">
                  {status.history.map((h, i) => (
                    <div key={i} className="flex items-start gap-3 text-xs">
                      <div className="w-2 h-2 rounded-full bg-violet-500 mt-1.5 shrink-0" />
                      <div>
                        <span className="text-slate-500 font-mono">{h.timestamp.slice(11, 19)}</span>
                        <span className="text-slate-400 mx-2">
                          {h.from_state} <ArrowRight className="w-3 h-3 inline" /> {h.to_state}
                        </span>
                        <span className="text-violet-400 font-semibold">{h.event}</span>
                        {h.agent_key && (
                          <span className="ml-2 px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[10px]">
                            {h.agent_key}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: Log Console */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-emerald-400" />
              Orchestrator Log
            </h3>
            <div className="glass-panel rounded-3xl overflow-hidden flex flex-col h-[600px]">
              <div className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-rose-500" />
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="ml-4 text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                  orchestrator.log
                </span>
                {(loading || approving) && (
                  <Loader2 className="w-3 h-3 text-cyan-400 animate-spin ml-auto" />
                )}
              </div>
              <div ref={logRef} className="flex-1 p-4 bg-[#0a0a0a] overflow-y-auto custom-scrollbar font-mono text-xs space-y-1.5">
                {logs.map((log, i) => (
                  <div key={i} className={
                    log.startsWith('[Error]') ? 'text-rose-400' :
                    log.startsWith('[System]') ? 'text-slate-500' :
                    log.startsWith('[Orchestrator]') ? 'text-violet-400 font-semibold' :
                    log.startsWith('[Agent]') ? 'text-cyan-400 font-semibold' :
                    log.startsWith('[Document]') ? 'text-amber-400' :
                    log.startsWith('[Artifact]') ? 'text-emerald-400' :
                    log.startsWith('[Action]') ? 'text-indigo-400' :
                    'text-slate-400'
                  }>{log}</div>
                ))}
                <div className="w-2 h-4 bg-slate-600 animate-pulse mt-2" />
              </div>
            </div>

            {/* State Info */}
            <div className="glass-panel rounded-2xl p-5">
              <h4 className="text-sm font-bold text-violet-400 uppercase tracking-wider mb-3">Current State</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">State</span>
                  <span className="text-white font-bold">{status.current_state}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Description</span>
                  <span className="text-slate-300">{status.state_description}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Documents</span>
                  <span className="text-white font-bold">{Object.keys(status.documents).length}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Artifacts</span>
                  <span className="text-white font-bold">{Object.keys(status.artifacts).length}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


const DocumentCard: React.FC<{
  doc: SDLCDocument;
  isExpanded: boolean;
  onToggle: () => void;
  canApprove: boolean;
  isApproving: boolean;
  onApprove: () => void;
}> = ({ doc, isExpanded, onToggle, canApprove, isApproving, onApprove }) => {
  const statusColor = doc.status === 'APPROVED'
    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
    : doc.status === 'FINALIZED'
    ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
    : 'bg-amber-500/10 text-amber-400 border-amber-500/20';

  const borderColor = doc.status === 'APPROVED'
    ? 'border-emerald-500/50 bg-emerald-950/20'
    : doc.status === 'DRAFT'
    ? 'border-amber-500/40 bg-amber-950/10'
    : 'border-slate-700 bg-slate-900/40';

  return (
    <motion.div layout className={`rounded-2xl border transition-all ${borderColor}`}>
      <div className="p-5">
        <div className="flex items-center gap-4">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
            doc.status === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-400' :
            doc.status === 'DRAFT' ? 'bg-amber-500/20 text-amber-400' :
            'bg-blue-500/20 text-blue-400'
          }`}>
            <FileText className="w-5 h-5" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-white truncate">{doc.title}</h4>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${statusColor}`}>
                {doc.status}
              </span>
            </div>
            <div className="text-xs text-slate-500 font-mono mt-0.5">{doc.id}</div>
          </div>

          <div className="flex items-center gap-2">
            {canApprove && (
              <button
                onClick={(e) => { e.stopPropagation(); onApprove(); }}
                disabled={isApproving}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 transition"
              >
                {isApproving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                Approve
              </button>
            )}
            <button onClick={onToggle} className="p-2 rounded-lg text-slate-500 hover:text-white transition">
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="px-5 pb-5">
              <div className="border-t border-slate-700/50 pt-4">
                <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono bg-slate-950/50 rounded-xl p-4 max-h-64 overflow-y-auto custom-scrollbar">
                  {doc.content}
                </pre>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};


const ArtifactCard: React.FC<{
  artifactKey: string;
  artifact: any;
  isExpanded: boolean;
  onToggle: () => void;
}> = ({ artifactKey, artifact, isExpanded, onToggle }) => {
  const testPlan = artifact?.test_plan;
  const testCases = artifact?.test_cases || [];
  const exitCriteria = artifact?.exit_criteria || [];

  return (
    <motion.div layout className="rounded-2xl border border-cyan-500/40 bg-cyan-950/10 transition-all">
      <div className="p-5 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-cyan-500/20 text-cyan-400">
            <ExternalLink className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-bold text-white">{testPlan?.title || artifactKey}</h4>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-xs text-slate-500 font-mono">{artifactKey}</span>
              {testPlan?.version && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  {testPlan.version}
                </span>
              )}
              <span className="text-xs text-slate-400">{testCases.length} test cases</span>
            </div>
          </div>
          <div className="text-slate-500">
            {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="px-5 pb-5 space-y-4">
              <div className="border-t border-slate-700/50 pt-4">
                {/* Strategy */}
                {testPlan?.strategy && (
                  <div className="mb-3">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Strategy</div>
                    <div className="text-xs text-slate-300">{testPlan.strategy}</div>
                  </div>
                )}

                {/* Test Cases Table */}
                {testCases.length > 0 && (
                  <div className="mb-3">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Test Cases</div>
                    <div className="space-y-1.5">
                      {testCases.map((tc: any) => (
                        <div key={tc.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-slate-900/60 text-xs">
                          <span className="font-mono text-cyan-400 font-bold w-12 shrink-0">{tc.id}</span>
                          <span className="text-white flex-1">{tc.name}</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            tc.priority === 'P1' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400'
                          }`}>{tc.priority}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400">{tc.category}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Exit Criteria */}
                {exitCriteria.length > 0 && (
                  <div className="mb-3">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Exit Criteria</div>
                    <div className="space-y-1">
                      {exitCriteria.map((c: string, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-xs text-slate-300">
                          <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
                          {c}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Risk Assessment */}
                {artifact?.risk_assessment && (
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Risk Assessment</div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs text-slate-400">Overall Risk:</span>
                      <span className={`text-xs font-bold ${
                        artifact.risk_assessment.overall_risk === 'HIGH' ? 'text-rose-400' :
                        artifact.risk_assessment.overall_risk === 'MEDIUM' ? 'text-amber-400' : 'text-emerald-400'
                      }`}>{artifact.risk_assessment.overall_risk}</span>
                    </div>
                    {artifact.risk_assessment.key_risks?.map((r: any, i: number) => (
                      <div key={i} className="px-3 py-2 rounded-lg bg-amber-950/20 border border-amber-500/10 mb-1.5 text-xs">
                        <div className="text-amber-300 font-semibold">{r.risk}</div>
                        <div className="text-slate-400 mt-0.5">Mitigation: {r.mitigation}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
