import React, { useState, useEffect, useRef } from 'react';
import { Play, FastForward, RotateCcw, CheckCircle2, XCircle, Clock, Loader2, ChevronDown, ChevronRight, Zap, Database, Shield, FileSearch, TestTube, Layers } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  fetchScenarios, initializeWorkflow, workflowNextStep, workflowRunAll,
  getWorkflowStepResult, Scenario, WorkflowState, WorkflowStep
} from '../services/api';

const PHASE_ICONS: Record<string, React.ReactNode> = {
  Discovery: <Database className="w-4 h-4" />,
  Analysis: <FileSearch className="w-4 h-4" />,
  Quality: <TestTube className="w-4 h-4" />,
  Design: <Layers className="w-4 h-4" />,
  Testing: <TestTube className="w-4 h-4" />,
  Governance: <Shield className="w-4 h-4" />,
};

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'border-slate-700 bg-slate-900/40',
  READY: 'border-slate-600 bg-slate-900/60',
  RUNNING: 'border-cyan-500 bg-cyan-950/30 shadow-lg shadow-cyan-500/10',
  COMPLETED: 'border-emerald-500/50 bg-emerald-950/20',
  FAILED: 'border-rose-500/50 bg-rose-950/20',
};

export const WorkflowSimulation: React.FC = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoRunning, setAutoRunning] = useState(false);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [stepResults, setStepResults] = useState<Record<number, any>>({});
  const [logs, setLogs] = useState<string[]>(['[System] Select a scenario to begin...']);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchScenarios().then(s => {
      setScenarios(s);
      if (s.length > 0) setSelectedScenario(s[0].id);
    });
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const addLog = (msg: string) => setLogs(prev => [...prev, msg]);

  const handleInitialize = async () => {
    if (!selectedScenario) return;
    setLoading(true);
    setStepResults({});
    setExpandedStep(null);
    addLog(`[System] Initializing workflow for ${selectedScenario}...`);
    try {
      const state = await initializeWorkflow(selectedScenario);
      setWorkflow(state);
      addLog(`[System] Workflow ${state.workflow_id} ready — ${state.total_steps} steps`);
      state.steps.forEach(s => addLog(`  → ${s.name} (${s.agent_key})`));
    } catch (e: any) {
      addLog(`[Error] ${e.message}`);
    }
    setLoading(false);
  };

  const handleNextStep = async () => {
    if (!workflow) return;
    setLoading(true);
    const currentIdx = workflow.current_step;
    const stepName = workflow.steps[currentIdx]?.name || 'Unknown';
    addLog(`[Agent] Executing: ${stepName}...`);

    try {
      const state = await workflowNextStep((progress) => {
        setWorkflow(progress);
      });
      setWorkflow(state);

      const step = state.steps[currentIdx];
      if (step) {
        const summary = step.result_summary || {};
        if (step.status === 'COMPLETED') {
          addLog(`[Agent] ✓ ${stepName} — ${formatSummary(summary)}`);
        } else {
          addLog(`[Agent] ✗ ${stepName} FAILED`);
        }

        const result = await getWorkflowStepResult(currentIdx);
        setStepResults(prev => ({ ...prev, [currentIdx]: result }));
      }

      if (state.status === 'COMPLETED') {
        addLog(`[System] Workflow COMPLETED — ${state.evidence_count} evidence items collected`);
      }
    } catch (e: any) {
      addLog(`[Error] ${e.message}`);
    }
    setLoading(false);
  };

  const handleRunAll = async () => {
    if (!workflow) return;
    setAutoRunning(true);
    setLoading(true);
    addLog('[System] Running all steps autonomously...');

    let lastReportedStep = workflow.current_step;
    try {
      const state = await workflowRunAll((progress) => {
        setWorkflow(progress);
        for (let i = lastReportedStep; i < progress.steps.length; i++) {
          const step = progress.steps[i];
          if (step.status === 'COMPLETED' || step.status === 'FAILED') {
            const summary = step.result_summary || {};
            addLog(`[Agent] ${step.status === 'COMPLETED' ? '✓' : '✗'} ${step.name} — ${formatSummary(summary)}`);
            lastReportedStep = i + 1;
          }
        }
      });
      setWorkflow(state);

      for (let i = 0; i < state.steps.length; i++) {
        const step = state.steps[i];
        if (i >= lastReportedStep) {
          const summary = step.result_summary || {};
          addLog(`[Agent] ${step.status === 'COMPLETED' ? '✓' : '✗'} ${step.name} — ${formatSummary(summary)}`);
        }
        try {
          const result = await getWorkflowStepResult(i);
          setStepResults(prev => ({ ...prev, [i]: result }));
        } catch { /* step may not have result */ }
      }

      addLog(`[System] Workflow ${state.status} — ${state.evidence_count} evidence items`);
    } catch (e: any) {
      addLog(`[Error] ${e.message}`);
    }
    setAutoRunning(false);
    setLoading(false);
  };

  const handleReset = () => {
    setWorkflow(null);
    setStepResults({});
    setExpandedStep(null);
    setLogs(['[System] Select a scenario to begin...']);
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 rounded-3xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-indigo-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/4 pointer-events-none" />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-3">
            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-300 text-xs font-bold border border-indigo-500/20 uppercase tracking-widest">
              <Zap className="w-3.5 h-3.5" />
              <span>AgentCore Harness Workflow</span>
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">Autonomous Agent Workflow</h2>
            <p className="text-slate-400 text-sm max-w-xl">
              Execute the full SDLC workflow using metamodel agents. Each agent scans the test-data corpus,
              builds the digital twin, and produces evidenced findings.
            </p>
          </div>

          <div className="flex flex-col gap-3">
            <select value={selectedScenario} onChange={e => setSelectedScenario(e.target.value)}
              className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-sm focus:outline-none focus:border-indigo-500">
              {scenarios.map(s => (
                <option key={s.id} value={s.id}>
                  {s.id}: {s.title} [{s.risk_level}]
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <button onClick={handleInitialize} disabled={loading || !selectedScenario}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold disabled:opacity-50 transition">
                Initialize
              </button>
              <button onClick={handleNextStep} disabled={loading || !workflow || workflow.status === 'COMPLETED'}
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 transition">
                <Play className="w-4 h-4" /> Next
              </button>
              <button onClick={handleRunAll} disabled={loading || !workflow || workflow.status === 'COMPLETED'}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 transition">
                <FastForward className="w-4 h-4" /> Run All
              </button>
              <button onClick={handleReset}
                className="p-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-400 hover:text-white transition">
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Main Content */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Workflow Steps */}
        <div className="xl:col-span-2 space-y-4">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            Agent Execution Pipeline
            {workflow && (
              <span className="text-sm font-normal text-slate-400 ml-2">
                ({workflow.current_step}/{workflow.total_steps} complete)
              </span>
            )}
          </h3>

          {workflow ? (
            <div className="space-y-3">
              {workflow.steps.map((step, idx) => (
                <StepCard key={step.id} step={step} index={idx}
                  isExpanded={expandedStep === idx}
                  onToggle={() => setExpandedStep(expandedStep === idx ? null : idx)}
                  result={stepResults[idx]}
                  isRunning={loading && step.status === 'RUNNING'} />
              ))}
            </div>
          ) : (
            <div className="glass-panel rounded-3xl p-12 text-center">
              <p className="text-slate-500 text-sm">Select a scenario and click Initialize to begin.</p>
            </div>
          )}

          {/* Evidence Summary */}
          {workflow && workflow.evidence_count > 0 && (
            <div className="glass-panel rounded-2xl p-6">
              <h4 className="text-sm font-bold text-emerald-400 uppercase tracking-wider mb-3">Evidence Collected</h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">{workflow.evidence_count}</div>
                  <div className="text-xs text-slate-500">Total Items</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-emerald-400">
                    {workflow.steps.filter(s => s.status === 'COMPLETED').length}
                  </div>
                  <div className="text-xs text-slate-500">Steps Done</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-rose-400">
                    {workflow.steps.filter(s => s.status === 'FAILED').length}
                  </div>
                  <div className="text-xs text-slate-500">Failed</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Log Console */}
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-emerald-400" />
            Execution Log
          </h3>
          <div className="glass-panel rounded-3xl overflow-hidden flex flex-col h-[600px]">
            <div className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-rose-500" />
              <div className="w-3 h-3 rounded-full bg-amber-500" />
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              <span className="ml-4 text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                agent-workflow.log
              </span>
              {(loading || autoRunning) && (
                <Loader2 className="w-3 h-3 text-cyan-400 animate-spin ml-auto" />
              )}
            </div>
            <div ref={logRef} className="flex-1 p-4 bg-[#0a0a0a] overflow-y-auto custom-scrollbar font-mono text-xs space-y-1.5">
              {logs.map((log, i) => (
                <div key={i} className={
                  log.startsWith('[Error]') ? 'text-rose-400' :
                  log.startsWith('[System]') ? 'text-slate-500' :
                  log.startsWith('[Agent] ✓') ? 'text-emerald-400' :
                  log.startsWith('[Agent] ✗') ? 'text-rose-400' :
                  log.startsWith('[Agent]') ? 'text-indigo-400 font-semibold' :
                  log.startsWith('  →') ? 'text-slate-600 pl-4' :
                  'text-slate-400'
                }>{log}</div>
              ))}
              <div className="w-2 h-4 bg-slate-600 animate-pulse mt-2" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const StepCard: React.FC<{
  step: WorkflowStep; index: number; isExpanded: boolean;
  onToggle: () => void; result: any; isRunning: boolean;
}> = ({ step, index, isExpanded, onToggle, result, isRunning }) => {
  const icon = PHASE_ICONS[step.phase] || <Zap className="w-4 h-4" />;

  return (
    <motion.div layout className={`rounded-2xl border transition-all ${STATUS_COLORS[step.status] || STATUS_COLORS.PENDING}`}>
      <div className="p-5 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center gap-4">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
            step.status === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' :
            step.status === 'FAILED' ? 'bg-rose-500/20 text-rose-400' :
            step.status === 'RUNNING' ? 'bg-cyan-500/20 text-cyan-400' :
            'bg-slate-800 text-slate-500'
          }`}>
            {isRunning ? <Loader2 className="w-5 h-5 animate-spin" /> :
             step.status === 'COMPLETED' ? <CheckCircle2 className="w-5 h-5" /> :
             step.status === 'FAILED' ? <XCircle className="w-5 h-5" /> :
             <Clock className="w-5 h-5" />}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-white truncate">{step.name}</h4>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
                {step.phase}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-xs text-slate-500 font-mono">{step.agent_key}</span>
              {step.result_summary && (
                <span className="text-xs text-slate-400">
                  {formatSummary(step.result_summary)}
                </span>
              )}
            </div>
          </div>

          <div className="text-slate-500">
            {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && result && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="px-5 pb-5 pt-0">
              <div className="border-t border-slate-700/50 pt-4">
                <ResultDetails result={result} agentKey={step.agent_key} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const ResultDetails: React.FC<{ result: any; agentKey: string }> = ({ result, agentKey }) => {
  if (!result || result.error) {
    return <p className="text-rose-400 text-xs">{result?.error || 'No result'}</p>;
  }

  return (
    <div className="space-y-3 text-xs">
      {/* Impact Analysis */}
      {result.risk_level && (
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Risk Level" value={result.risk_level}
            color={result.risk_level === 'CRITICAL' ? 'text-rose-400' : result.risk_level === 'HIGH' ? 'text-amber-400' : 'text-emerald-400'} />
          <Stat label="Regulatory" value={result.regulatory_impact ? 'YES' : 'NO'}
            color={result.regulatory_impact ? 'text-rose-400' : 'text-emerald-400'} />
          <Stat label="Directly Affected" value={result.directly_affected?.length || 0} />
          <Stat label="Transitively Affected" value={result.transitively_affected?.length || 0} />
        </div>
      )}

      {/* Test Results */}
      {result.test_execution && (
        <div className="grid grid-cols-4 gap-3">
          <Stat label="Total Tests" value={result.test_execution.summary?.total || 0} />
          <Stat label="Passed" value={result.test_execution.summary?.passed || 0} color="text-emerald-400" />
          <Stat label="Failed" value={result.test_execution.summary?.failed || 0}
            color={result.test_execution.summary?.failed > 0 ? 'text-rose-400' : 'text-emerald-400'} />
          <Stat label="Status" value={result.test_execution.overall_status || '?'}
            color={result.test_execution.overall_status === 'PASSED' ? 'text-emerald-400' : 'text-rose-400'} />
        </div>
      )}

      {/* Gate Assessment */}
      {result.gate_assessment && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className={`font-bold ${result.gate_assessment.ready ? 'text-emerald-400' : 'text-rose-400'}`}>
              Gate: {result.gate_assessment.ready ? 'READY' : 'BLOCKED'}
            </span>
          </div>
          {result.gate_assessment.blockers?.map((b: any, i: number) => (
            <div key={i} className={`px-3 py-2 rounded-lg ${b.severity === 'BLOCKING' ? 'bg-rose-950/40 border border-rose-500/30 text-rose-300' : 'bg-amber-950/40 border border-amber-500/30 text-amber-300'}`}>
              {b.detail}
            </div>
          ))}
          <p className="text-slate-400 italic">{result.gate_assessment.recommendation}</p>
        </div>
      )}

      {/* Data Quality */}
      {result.quality_indicators && (
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Profiles" value={result.profiles?.length || 0} />
          <Stat label="Quality Indicators" value={result.quality_indicators?.length || 0} />
        </div>
      )}

      {/* Entity Count */}
      {result.entity_count != null && !result.risk_level && (
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Entities" value={result.entity_count} />
          <Stat label="Agent" value={result.agent_key || agentKey} />
        </div>
      )}
    </div>
  );
};

const Stat: React.FC<{ label: string; value: any; color?: string }> = ({ label, value, color = 'text-white' }) => (
  <div className="bg-slate-900/60 rounded-lg px-3 py-2">
    <div className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</div>
    <div className={`text-sm font-bold ${color}`}>{String(value)}</div>
  </div>
);

function formatSummary(summary: Record<string, any>): string {
  const parts: string[] = [];
  if (summary.status) parts.push(summary.status);
  if (summary.overall_status) parts.push(summary.overall_status);
  if (summary.risk) parts.push(`Risk: ${summary.risk}`);
  if (summary.risk_level) parts.push(`Risk: ${summary.risk_level}`);
  if (summary.affected) parts.push(`${summary.affected} affected`);
  if (summary.total_affected_count) parts.push(`${summary.total_affected_count} affected`);
  if (summary.entities) parts.push(`${summary.entities} entities`);
  if (summary.entity_count) parts.push(`${summary.entity_count} entities`);
  if (summary.test_summary) {
    const t = summary.test_summary;
    parts.push(`Tests: ${t.passed || 0}✓ ${t.failed || 0}✗`);
  }
  if (summary.gate_ready !== undefined) parts.push(summary.gate_ready ? 'Gate: READY' : 'Gate: BLOCKED');
  return parts.join(' | ') || 'Done';
}
