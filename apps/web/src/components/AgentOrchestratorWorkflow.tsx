import React, { useEffect, useRef, useState } from 'react';
import {
  Play, RotateCcw, Loader2, Zap, Cloud, Github, ShieldAlert, CheckCircle2,
  XCircle, Cpu, Activity, KeyRound, ChevronDown, ChevronRight, Terminal,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LiveAgent, LiveEvent, PendingClientToolCall, AwsIdentity, AgentCoreMetrics, ClientTool,
  fetchLiveAgents, fetchAwsIdentity, fetchLiveMetrics, fetchClientTools,
  startLiveSession, pollLiveSession, approveClientToolCall, denyClientToolCall,
} from '../services/api';

const POLL_INTERVAL_MS = 700;

function formatLog(e: LiveEvent): { text: string; className: string } {
  const p = e.payload || {};
  switch (e.event_type) {
    case 'SESSION_STARTED':
      return { text: `[Orchestrator] Session started — backend=${p.backend} mode=${p.mode}${p.harness_arn ? ` arn=${p.harness_arn}` : ''}`, className: 'text-violet-400 font-semibold' };
    case 'THINKING':
      return { text: `[Agent] ${p.text}`, className: 'text-cyan-300' };
    case 'TOOL_CALL':
      return { text: `[Tool] Calling ${p.name}(${JSON.stringify(p.input || {})})`, className: 'text-amber-400' };
    case 'TOOL_RESULT':
      return { text: `[Tool] ${p.name} → ${p.result}`, className: 'text-amber-300' };
    case 'CLIENT_TOOL_CALL_REQUESTED':
      return { text: `[Client Tool] ${p.tool_name} requested — awaiting operator approval to run on your machine`, className: 'text-rose-300 font-semibold' };
    case 'CLIENT_TOOL_CALL_APPROVED':
      return { text: `[Client Tool] ${p.tool_name} approved — running locally…`, className: 'text-emerald-300' };
    case 'CLIENT_TOOL_CALL_RESOLVED':
      return { text: `[Client Tool] ${p.tool_name} → ${p.status}`, className: p.status === 'COMPLETED' ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold' };
    case 'SESSION_RESPONSE':
      return { text: `[Agent] Final response ready`, className: 'text-white font-semibold' };
    case 'SESSION_COMPLETED':
      return { text: `[System] Session completed`, className: 'text-emerald-400 font-bold' };
    case 'SESSION_FAILED':
      return { text: `[Error] ${p.error}`, className: 'text-rose-500 font-bold' };
    default:
      return { text: `[${e.event_type}]`, className: 'text-slate-400' };
  }
}

export const AgentOrchestratorWorkflow: React.FC = () => {
  const [live, setLive] = useState(false); // false = DEMO, true = LIVE
  const [agents, setAgents] = useState<LiveAgent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<LiveAgent | null>(null);
  const [prompt, setPrompt] = useState('Assess the delivery impact of renaming customer_id to customer_uid.');
  const [awsIdentity, setAwsIdentity] = useState<AwsIdentity | null>(null);
  const [metrics, setMetrics] = useState<AgentCoreMetrics | null>(null);
  const [clientTools, setClientTools] = useState<ClientTool[]>([]);
  const [toolsExpanded, setToolsExpanded] = useState(false);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('IDLE');
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [pendingCalls, setPendingCalls] = useState<PendingClientToolCall[]>([]);
  const [finalText, setFinalText] = useState<string | null>(null);
  const [resolvingCallId, setResolvingCallId] = useState<string | null>(null);

  const cursorRef = useRef(0);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchLiveAgents().then(setAgents);
    fetchAwsIdentity().then(setAwsIdentity);
    fetchClientTools().then(setClientTools);
  }, []);

  useEffect(() => {
    if (selectedAgent?.backend === 'AGENTCORE') {
      fetchLiveMetrics(selectedAgent.id).then(setMetrics);
    } else {
      setMetrics(null);
    }
  }, [selectedAgent]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [events]);

  useEffect(() => {
    if (!sessionId || status !== 'RUNNING') return;
    const interval = setInterval(async () => {
      const p = await pollLiveSession(sessionId, cursorRef.current);
      cursorRef.current = p.next_cursor;
      if (p.events.length) setEvents(prev => [...prev, ...p.events]);
      setPendingCalls(p.pending_calls);
      setStatus(p.status);
      if (p.final_text) setFinalText(p.final_text);
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [sessionId, status]);

  const handleRun = async () => {
    if (!selectedAgent) return;
    setEvents([]);
    setPendingCalls([]);
    setFinalText(null);
    cursorRef.current = 0;
    const { session_id } = await startLiveSession(selectedAgent.id, selectedAgent.backend, live, prompt);
    setSessionId(session_id);
    setStatus('RUNNING');
  };

  const handleReset = () => {
    setSessionId(null);
    setStatus('IDLE');
    setEvents([]);
    setPendingCalls([]);
    setFinalText(null);
    cursorRef.current = 0;
  };

  const handleApprove = async (callId: string) => {
    if (!sessionId) return;
    setResolvingCallId(callId);
    await approveClientToolCall(sessionId, callId);
    setResolvingCallId(null);
  };

  const handleDeny = async (callId: string) => {
    if (!sessionId) return;
    setResolvingCallId(callId);
    await denyClientToolCall(sessionId, callId);
    setResolvingCallId(null);
  };

  const isRunning = status === 'RUNNING';

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 rounded-3xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-cyan-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/4 pointer-events-none" />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-3">
            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 text-xs font-bold border border-cyan-500/20 uppercase tracking-widest">
              <Zap className="w-3.5 h-3.5" />
              <span>Agent Orchestrator</span>
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">Live Agent Orchestrator</h2>
            <p className="text-slate-400 text-sm max-w-xl">
              Invokes agents running in AWS Bedrock AgentCore Harness or as GitHub Copilot CLI agents.
              A curated set of tools can be delegated to run on this developer machine — the orchestrator
              pauses the agent's turn, waits for your approval, runs the tool locally, and resumes the
              conversation from where it left off.
            </p>
          </div>

          <div className="flex flex-col items-end gap-3">
            {/* Live / Demo toggle */}
            <div className="flex items-center gap-2 bg-slate-900/60 border border-slate-700 rounded-xl p-1">
              <button
                onClick={() => setLive(false)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${!live ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
              >
                DEMO
              </button>
              <button
                onClick={() => setLive(true)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${live ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
              >
                LIVE
              </button>
            </div>

            {/* AWS identity chip */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-mono border ${
              awsIdentity?.available
                ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300'
                : 'bg-slate-900/60 border-slate-700 text-slate-500'
            }`}>
              <KeyRound className="w-3 h-3" />
              {awsIdentity?.available
                ? `AWS: ${awsIdentity.arn?.split('/').pop() || awsIdentity.account}`
                : 'AWS: not connected (aws sso login)'}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Agent picker */}
      <div className="space-y-3">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <Cpu className="w-5 h-5 text-cyan-400" /> Choose an Agent
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {agents.map(agent => {
            const isSelected = selectedAgent?.id === agent.id;
            return (
              <button
                key={`${agent.backend}-${agent.id}`}
                onClick={() => setSelectedAgent(agent)}
                className={`text-left p-4 rounded-2xl border transition-all ${
                  isSelected
                    ? 'border-cyan-500 bg-cyan-950/20 ring-1 ring-cyan-500/50'
                    : 'border-slate-700 bg-slate-900/40 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                    agent.backend === 'AGENTCORE'
                      ? 'bg-orange-500/10 text-orange-300 border-orange-500/20'
                      : 'bg-slate-500/10 text-slate-300 border-slate-500/30'
                  }`}>
                    {agent.backend === 'AGENTCORE' ? <Cloud className="w-3 h-3" /> : <Github className="w-3 h-3" />}
                    {agent.backend === 'AGENTCORE' ? 'AgentCore' : 'GitHub Copilot'}
                  </span>
                  {agent.backend === 'AGENTCORE' && (
                    <span className={`text-[10px] font-bold ${agent.live_ready ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {agent.harness_status}
                    </span>
                  )}
                </div>
                <div className="text-sm font-bold text-white">{agent.name}</div>
                <div className="text-xs text-slate-500 mt-1 line-clamp-2">{agent.description}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Client tools disclosure */}
      <div className="glass-panel rounded-2xl overflow-hidden">
        <button onClick={() => setToolsExpanded(!toolsExpanded)}
          className="w-full flex items-center justify-between px-5 py-3 text-sm font-bold text-slate-300 hover:text-white transition">
          <span className="flex items-center gap-2"><Terminal className="w-4 h-4 text-emerald-400" /> Tools this agent may run on your machine ({clientTools.length})</span>
          {toolsExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <AnimatePresence>
          {toolsExpanded && (
            <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
              <div className="px-5 pb-4 space-y-1.5">
                {clientTools.map(t => (
                  <div key={t.name} className="text-xs flex gap-3 px-3 py-2 rounded-lg bg-slate-900/60">
                    <span className="font-mono text-emerald-400 shrink-0">{t.name}</span>
                    <span className="text-slate-400">{t.description}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Prompt + run controls */}
      <div className="glass-panel rounded-3xl p-6 space-y-4">
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          rows={3}
          className="w-full bg-slate-950/60 border border-slate-700 rounded-xl p-4 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
          placeholder="Describe the change or question for the agent…"
        />
        <div className="flex items-center gap-3">
          <button
            onClick={handleRun}
            disabled={!selectedAgent || isRunning}
            className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold disabled:opacity-40 flex items-center gap-2 transition"
          >
            {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Run {live ? 'LIVE' : 'DEMO'}
          </button>
          <button onClick={handleReset}
            className="px-4 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:text-white text-sm font-semibold flex items-center gap-2 transition">
            <RotateCcw className="w-4 h-4" /> Reset
          </button>
          {!selectedAgent && <span className="text-xs text-slate-500">Select an agent above to enable Run.</span>}
        </div>
      </div>

      {sessionId && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Left: log + pending calls */}
          <div className="xl:col-span-2 space-y-6">
            {pendingCalls.map(call => (
              <motion.div key={call.call_id} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl border border-rose-500/50 bg-rose-950/20 p-5">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-xl bg-rose-500/20 flex items-center justify-center shrink-0">
                    <ShieldAlert className="w-5 h-5 text-rose-400" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-bold text-rose-300">Approval needed: run on your machine</div>
                    <div className="text-xs text-slate-400 mt-1">
                      The agent wants to call <span className="font-mono text-white">{call.tool_name}</span> with
                      arguments <span className="font-mono text-slate-300">{JSON.stringify(call.arguments)}</span>.
                      This executes locally on this machine, not in the cloud.
                    </div>
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => handleApprove(call.call_id)}
                        disabled={resolvingCallId === call.call_id}
                        className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 transition"
                      >
                        {resolvingCallId === call.call_id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                        Approve & Run Locally
                      </button>
                      <button
                        onClick={() => handleDeny(call.call_id)}
                        disabled={resolvingCallId === call.call_id}
                        className="px-4 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 transition"
                      >
                        <XCircle className="w-3.5 h-3.5" /> Deny
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}

            <div className="glass-panel rounded-3xl overflow-hidden flex flex-col h-[520px]">
              <div className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-rose-500" />
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="ml-4 text-[10px] font-mono text-slate-500 uppercase tracking-widest">orchestrator.log</span>
                {isRunning && <Loader2 className="w-3 h-3 text-cyan-400 animate-spin ml-auto" />}
              </div>
              <div ref={logRef} className="flex-1 p-4 bg-[#0a0a0a] overflow-y-auto custom-scrollbar font-mono text-xs space-y-1.5">
                {events.map((e, i) => {
                  const { text, className } = formatLog(e);
                  return <div key={e.id || i} className={className}>{text}</div>;
                })}
                <div className="w-2 h-4 bg-slate-600 animate-pulse mt-2" />
              </div>
            </div>

            {finalText && (
              <div className="glass-panel rounded-2xl p-5 border border-emerald-500/30">
                <h4 className="text-sm font-bold text-emerald-400 uppercase tracking-wider mb-2">Final Response</h4>
                <pre className="text-xs text-slate-200 whitespace-pre-wrap font-sans">{finalText}</pre>
              </div>
            )}
          </div>

          {/* Right: metrics + status */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-400" /> AgentCore Metrics
            </h3>
            <div className="glass-panel rounded-2xl p-5">
              {metrics?.available ? (
                <div className="grid grid-cols-2 gap-3">
                  {(metrics.series || []).map(s => (
                    <div key={s.metric} className="rounded-xl bg-slate-900/60 p-3">
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{s.metric}</div>
                      <div className="text-xl font-extrabold text-white mt-1">{s.total}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500">
                  {selectedAgent?.backend !== 'AGENTCORE'
                    ? 'Metrics are only available for AgentCore-backed agents.'
                    : (metrics?.reason || 'No CloudWatch data yet for this runtime.')}
                </div>
              )}
            </div>

            <div className="glass-panel rounded-2xl p-5">
              <h4 className="text-sm font-bold text-violet-400 uppercase tracking-wider mb-3">Session</h4>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between"><span className="text-slate-500">Status</span><span className="text-white font-bold">{status}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Backend</span><span className="text-white font-bold">{selectedAgent?.backend}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Mode</span><span className="text-white font-bold">{live ? 'LIVE' : 'DEMO'}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Events</span><span className="text-white font-bold">{events.length}</span></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
