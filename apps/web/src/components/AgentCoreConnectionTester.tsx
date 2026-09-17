import React, { useEffect, useRef, useState } from 'react';
import {
  Plug, CheckCircle2, XCircle, Loader2, Save, KeyRound, Globe, FolderOpen, Briefcase, RotateCcw,
  Rocket, Send, Bell, X,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ConnectionSettings, ConnectionTestResult, LiveAgent, LiveEvent, PendingClientToolCall,
  fetchConnectionSettings, saveConnectionSettings, runConnectionTest,
  fetchLiveAgents, startLiveSession, pollLiveSession, approveClientToolCall, denyClientToolCall,
} from '../services/api';
import { formatLog } from './AgentOrchestratorWorkflow';

const EMPTY_SETTINGS: ConnectionSettings = { credentials_path: '', profile: '', region: '', project: '' };
const POLL_INTERVAL_MS = 700;
const LOCAL_CALLBACK_PROMPT =
  'Before answering, call the client_git_status tool to check this repository\'s local git working-tree status, then summarize what you find.';

export const AgentCoreConnectionTester: React.FC = () => {
  const [settings, setSettings] = useState<ConnectionSettings>(EMPTY_SETTINGS);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ConnectionTestResult | null>(null);
  const [dirty, setDirty] = useState(false);

  // Invoke Harness + Test Local Callback share the harness dropdown
  const [harnesses, setHarnesses] = useState<LiveAgent[]>([]);
  const [selectedHarnessId, setSelectedHarnessId] = useState<string>('');

  const [invokePrompt, setInvokePrompt] = useState('Summarize what this project does.');
  const [invokeLive, setInvokeLive] = useState(true);
  const [invokeSessionId, setInvokeSessionId] = useState<string | null>(null);
  const [invokeStatus, setInvokeStatus] = useState<string>('IDLE');
  const [invokeEvents, setInvokeEvents] = useState<LiveEvent[]>([]);
  const [invokeFinalText, setInvokeFinalText] = useState<string | null>(null);
  const [invokePendingCalls, setInvokePendingCalls] = useState<PendingClientToolCall[]>([]);
  const [invokeResolvingCallId, setInvokeResolvingCallId] = useState<string | null>(null);
  const invokeCursorRef = useRef(0);
  const invokeLogRef = useRef<HTMLDivElement>(null);

  const [callbackSessionId, setCallbackSessionId] = useState<string | null>(null);
  const [callbackStatus, setCallbackStatus] = useState<string>('IDLE');
  const [callbackEvents, setCallbackEvents] = useState<LiveEvent[]>([]);
  const [callbackFinalText, setCallbackFinalText] = useState<string | null>(null);
  const callbackCursorRef = useRef(0);
  const handledCallIdsRef = useRef<Set<string>>(new Set());
  const [popupOpen, setPopupOpen] = useState(false);
  const [popupPhase, setPopupPhase] = useState<'received' | 'resolved'>('received');
  const [popupCall, setPopupCall] = useState<PendingClientToolCall | null>(null);
  const [popupResult, setPopupResult] = useState<any>(null);

  useEffect(() => {
    fetchLiveAgents().then(list => {
      const agentcoreHarnesses = list.filter(a => a.backend === 'AGENTCORE');
      setHarnesses(agentcoreHarnesses);
      if (agentcoreHarnesses.length > 0) setSelectedHarnessId(agentcoreHarnesses[0].id);
    });
  }, []);

  useEffect(() => {
    if (invokeLogRef.current) invokeLogRef.current.scrollTop = invokeLogRef.current.scrollHeight;
  }, [invokeEvents]);

  useEffect(() => {
    if (!invokeSessionId || invokeStatus !== 'RUNNING') return;
    const interval = setInterval(async () => {
      const p = await pollLiveSession(invokeSessionId, invokeCursorRef.current);
      invokeCursorRef.current = p.next_cursor;
      if (p.events.length) setInvokeEvents(prev => [...prev, ...p.events]);
      setInvokeStatus(p.status);
      setInvokePendingCalls(p.pending_calls);
      if (p.final_text) setInvokeFinalText(p.final_text);
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [invokeSessionId, invokeStatus]);

  const handleApproveInvoke = async (callId: string) => {
    if (!invokeSessionId) return;
    setInvokeResolvingCallId(callId);
    await approveClientToolCall(invokeSessionId, callId);
    setInvokeResolvingCallId(null);
  };

  const handleDenyInvoke = async (callId: string) => {
    if (!invokeSessionId) return;
    setInvokeResolvingCallId(callId);
    await denyClientToolCall(invokeSessionId, callId);
    setInvokeResolvingCallId(null);
  };

  useEffect(() => {
    if (!callbackSessionId || callbackStatus !== 'RUNNING') return;
    const interval = setInterval(async () => {
      const p = await pollLiveSession(callbackSessionId, callbackCursorRef.current);
      callbackCursorRef.current = p.next_cursor;
      if (p.events.length) setCallbackEvents(prev => [...prev, ...p.events]);
      setCallbackStatus(p.status);
      if (p.final_text) setCallbackFinalText(p.final_text);

      const pending = p.pending_calls.find(c => !handledCallIdsRef.current.has(c.call_id));
      if (pending) {
        handledCallIdsRef.current.add(pending.call_id);
        setPopupCall(pending);
        setPopupPhase('received');
        setPopupResult(null);
        setPopupOpen(true);
        // Per the confirmed test flow: auto-approve and execute immediately,
        // no separate operator click — this test proves the full round trip.
        const approved = await approveClientToolCall(callbackSessionId, pending.call_id);
        setPopupPhase('resolved');
        setPopupResult(approved);
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [callbackSessionId, callbackStatus]);

  const handleInvokeHarness = async () => {
    if (!selectedHarnessId) return;
    setInvokeEvents([]);
    setInvokeFinalText(null);
    setInvokePendingCalls([]);
    invokeCursorRef.current = 0;
    const { session_id } = await startLiveSession(selectedHarnessId, 'AGENTCORE', invokeLive, invokePrompt);
    setInvokeSessionId(session_id);
    setInvokeStatus('RUNNING');
  };

  const handleTestLocalCallback = async () => {
    if (!selectedHarnessId) return;
    setCallbackEvents([]);
    setCallbackFinalText(null);
    handledCallIdsRef.current = new Set();
    callbackCursorRef.current = 0;
    const { session_id } = await startLiveSession(selectedHarnessId, 'AGENTCORE', invokeLive, LOCAL_CALLBACK_PROMPT);
    setCallbackSessionId(session_id);
    setCallbackStatus('RUNNING');
  };

  const loadAndTest = async () => {
    const loadedSettings = await fetchConnectionSettings();
    setSettings(loadedSettings);
    setLoaded(true);
    setDirty(false);
    setTesting(true);
    setResult(await runConnectionTest(loadedSettings));
    setTesting(false);
  };

  useEffect(() => { loadAndTest(); }, []);

  const handleChange = (field: keyof ConnectionSettings) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setSettings(prev => ({ ...prev, [field]: e.target.value }));
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    const saved = await saveConnectionSettings(settings);
    setSettings(saved);
    setDirty(false);
    setSaving(false);
  };

  const handleTest = async () => {
    setTesting(true);
    setResult(await runConnectionTest(settings));
    setTesting(false);
  };

  const handleSaveAndTest = async () => {
    await handleSave();
    await handleTest();
  };

  const handleReset = () => { loadAndTest(); };

  return (
    <div className="space-y-6 pb-12">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 rounded-3xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-cyan-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/4 pointer-events-none" />
        <div className="relative z-10 space-y-3">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 text-xs font-bold border border-cyan-500/20 uppercase tracking-widest">
            <Plug className="w-3.5 h-3.5" /><span>AgentCore Connection Tester</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Connection Tester</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Verifies this machine can reach both AWS (via STS) and Bedrock AgentCore specifically,
            using your own local AWS session — a credentials file (standard AWS format, or a JSON
            export), a named profile, or plain environment variables. Region and project default
            from environment variables and can be overridden below.
          </p>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Settings form */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-cyan-400" /> Settings
          </h3>

          <Field icon={<FolderOpen className="w-4 h-4" />} label="Credentials Path"
            hint="Path to an AWS credentials file (INI) or a JSON export ({aws_access_key_id, ...}). Leave blank to use the default AWS chain."
            value={settings.credentials_path} onChange={handleChange('credentials_path')}
            placeholder="~/.aws/credentials or /path/to/creds.json" />

          <Field icon={<KeyRound className="w-4 h-4" />} label="Profile"
            hint="AWS named profile (AWS_PROFILE). Ignored when using a JSON credentials file."
            value={settings.profile} onChange={handleChange('profile')} placeholder="default" />

          <Field icon={<Globe className="w-4 h-4" />} label="Region"
            hint="Defaults from AGENTCORE_AWS_REGION / AWS_DEFAULT_REGION."
            value={settings.region} onChange={handleChange('region')} placeholder="us-west-2" />

          <Field icon={<Briefcase className="w-4 h-4" />} label="Project"
            hint="Defaults from AGENTCORE_PROJECT. Display/context label only."
            value={settings.project} onChange={handleChange('project')} placeholder="data-sdlc-framework" />

          <div className="flex items-center gap-2 pt-2">
            <button onClick={handleSaveAndTest} disabled={!loaded || saving || testing}
              className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 transition">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save &amp; Test
            </button>
            <button onClick={handleTest} disabled={!loaded || testing}
              className="px-4 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 transition">
              {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plug className="w-4 h-4" />}
              Test Connection
            </button>
            <button onClick={handleReset} disabled={testing}
              className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-400 hover:text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 transition">
              <RotateCcw className="w-3.5 h-3.5" /> Reload Saved
            </button>
            {dirty && <span className="text-[11px] text-amber-400">Unsaved changes</span>}
          </div>
        </div>

        {/* Results */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Connection Status</h3>

          {!result && testing && (
            <div className="flex items-center gap-2 text-slate-400 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Testing...</div>
          )}

          {result?.error && (
            <StatusRow ok={false} title="Session setup" detail={result.error} />
          )}

          {result?.aws_identity && (
            <StatusRow
              ok={result.aws_identity.available}
              title="AWS Identity (STS)"
              detail={
                result.aws_identity.available
                  ? `${result.aws_identity.arn}`
                  : result.aws_identity.reason
              }
              sub={result.aws_identity.available ? `Account ${result.aws_identity.account}` : undefined}
            />
          )}

          {result?.agentcore && (
            <StatusRow
              ok={result.agentcore.available}
              title="Bedrock AgentCore"
              detail={
                result.agentcore.available
                  ? `Reachable in ${result.agentcore.region} — ${result.agentcore.harness_count} harness(es) visible`
                  : result.agentcore.reason
              }
            />
          )}

          {!result && !testing && (
            <div className="text-xs text-slate-500">No test run yet.</div>
          )}

          {testing && result && (
            <div className="flex items-center gap-2 text-slate-500 text-xs pt-2"><Loader2 className="w-3 h-3 animate-spin" /> Re-testing...</div>
          )}
        </div>
      </div>

      {/* Harness selector shared by Invoke Harness + Test Local Callback */}
      <div className="glass-panel rounded-2xl p-6 space-y-3">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <Rocket className="w-4 h-4 text-cyan-400" /> Harness
        </h3>
        <select
          value={selectedHarnessId}
          onChange={(e) => setSelectedHarnessId(e.target.value)}
          className="w-full bg-slate-950/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
        >
          {harnesses.length === 0 && <option value="">No AgentCore harnesses found</option>}
          {harnesses.map((h) => (
            <option key={h.id} value={h.id}>{h.name} ({h.harness_status})</option>
          ))}
        </select>
        {(() => {
          const selected = harnesses.find((h) => h.id === selectedHarnessId);
          if (!selected) return null;
          return (
            <div className="text-[11px] text-slate-500 font-mono space-y-0.5">
              {selected.model_id && <div>Model: <span className="text-slate-300">{selected.model_id}</span></div>}
              {selected.harness_arn && <div className="break-all">ARN: <span className="text-slate-300">{selected.harness_arn}</span></div>}
            </div>
          );
        })()}
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={invokeLive} onChange={(e) => setInvokeLive(e.target.checked)}
            className="accent-cyan-500" />
          Live mode (uncheck for a scripted DEMO run — no AWS calls, still exercises the same flow)
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Invoke Harness */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Send className="w-4 h-4 text-cyan-400" /> Invoke Harness
          </h3>
          <textarea
            value={invokePrompt} onChange={(e) => setInvokePrompt(e.target.value)}
            rows={3}
            className="w-full bg-slate-950/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
            placeholder="Prompt to send to the selected harness..."
          />
          <button onClick={handleInvokeHarness} disabled={!selectedHarnessId || invokeStatus === 'RUNNING'}
            className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 transition">
            {invokeStatus === 'RUNNING' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Submit
          </button>
          {invokePendingCalls.map((call) => (
            <div key={call.call_id} className="rounded-xl border border-rose-500/50 bg-rose-950/20 p-3 space-y-2">
              <div className="text-xs font-bold text-rose-300">Approval needed: run on your machine</div>
              <div className="text-[11px] text-slate-400">
                Calls <span className="font-mono text-white">{call.tool_name}</span> with{' '}
                <span className="font-mono text-slate-300">{JSON.stringify(call.arguments)}</span>
              </div>
              <div className="flex gap-2">
                <button onClick={() => handleApproveInvoke(call.call_id)} disabled={invokeResolvingCallId === call.call_id}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 transition">
                  {invokeResolvingCallId === call.call_id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                  Approve
                </button>
                <button onClick={() => handleDenyInvoke(call.call_id)} disabled={invokeResolvingCallId === call.call_id}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 transition">
                  <XCircle className="w-3 h-3" /> Deny
                </button>
              </div>
            </div>
          ))}
          <div ref={invokeLogRef} className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 h-56 overflow-y-auto font-mono text-xs space-y-1">
            {invokeEvents.length === 0 && <div className="text-slate-600">No activity yet.</div>}
            {invokeEvents.map((e) => {
              const { text, className } = formatLog(e);
              return <div key={e.id} className={className}>{text}</div>;
            })}
            {invokeFinalText && (
              <div className="text-white pt-2 border-t border-slate-800 mt-2 whitespace-pre-wrap">{invokeFinalText}</div>
            )}
          </div>
        </div>

        {/* Test Local Callback */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Bell className="w-4 h-4 text-cyan-400" /> Test Local Callback
          </h3>
          <p className="text-xs text-slate-500">
            Sends a prompt that instructs the harness to call the <code className="text-slate-300">client_git_status</code> client
            tool — the same pause/resume bridge every developer-machine tool call uses. On receipt, this
            automatically approves and executes it, so a single click proves the whole round trip.
          </p>
          <button onClick={handleTestLocalCallback} disabled={!selectedHarnessId || callbackStatus === 'RUNNING'}
            className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 transition">
            {callbackStatus === 'RUNNING' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bell className="w-4 h-4" />}
            Test Local Callback
          </button>
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 h-40 overflow-y-auto font-mono text-xs space-y-1">
            {callbackEvents.length === 0 && <div className="text-slate-600">No activity yet.</div>}
            {callbackEvents.map((e) => {
              const { text, className } = formatLog(e);
              return <div key={e.id} className={className}>{text}</div>;
            })}
            {callbackFinalText && (
              <div className="text-white pt-2 border-t border-slate-800 mt-2 whitespace-pre-wrap">{callbackFinalText}</div>
            )}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {popupOpen && popupCall && (
          <ToolCallPopup
            phase={popupPhase} call={popupCall} result={popupResult}
            onClose={() => setPopupOpen(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

const Field: React.FC<{
  icon: React.ReactNode; label: string; hint: string; value: string; placeholder: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}> = ({ icon, label, hint, value, placeholder, onChange }) => (
  <div>
    <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-1">{icon} {label}</label>
    <input
      value={value} onChange={onChange} placeholder={placeholder}
      className="w-full bg-slate-950/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
    />
    <p className="text-[11px] text-slate-500 mt-1">{hint}</p>
  </div>
);

const ToolCallPopup: React.FC<{
  phase: 'received' | 'resolved'; call: PendingClientToolCall; result: any; onClose: () => void;
}> = ({ phase, call, result, onClose }) => (
  <motion.div
    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
    className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
  >
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }}
      className="glass-panel rounded-2xl p-6 max-w-md w-full space-y-4 border border-cyan-500/30"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-cyan-300 font-bold text-sm uppercase tracking-wider">
          <Bell className="w-4 h-4" /> Tool call message received
        </div>
        <button onClick={onClose} className="text-slate-500 hover:text-white"><X className="w-4 h-4" /></button>
      </div>

      <div className="text-xs text-slate-400 font-mono break-all">
        <div><span className="text-slate-500">tool_name:</span> {call.tool_name}</div>
        <div className="mt-1"><span className="text-slate-500">arguments:</span> {JSON.stringify(call.arguments)}</div>
      </div>

      {phase === 'received' ? (
        <div className="flex items-center gap-2 text-amber-300 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Auto-approving and executing locally...</div>
      ) : (
        <div className={`rounded-xl border px-3 py-2.5 ${
          result?.status === 'COMPLETED' ? 'bg-emerald-950/30 border-emerald-500/30' : 'bg-rose-950/30 border-rose-500/30'
        }`}>
          <div className={`text-xs font-bold flex items-center gap-1.5 ${result?.status === 'COMPLETED' ? 'text-emerald-300' : 'text-rose-300'}`}>
            {result?.status === 'COMPLETED' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
            {result?.status}
          </div>
          <div className="text-[11px] text-slate-400 font-mono break-all mt-1 max-h-32 overflow-y-auto">
            {result?.error || JSON.stringify(result?.output)}
          </div>
        </div>
      )}
    </motion.div>
  </motion.div>
);

const StatusRow: React.FC<{ ok: boolean; title: string; detail?: string; sub?: string }> = ({ ok, title, detail, sub }) => (
  <div className={`rounded-xl border px-3 py-2.5 flex items-start gap-2.5 ${
    ok ? 'bg-emerald-950/30 border-emerald-500/30' : 'bg-rose-950/30 border-rose-500/30'
  }`}>
    {ok ? <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />}
    <div className="min-w-0">
      <div className={`text-xs font-bold ${ok ? 'text-emerald-300' : 'text-rose-300'}`}>{title}</div>
      {detail && <div className="text-[11px] text-slate-400 font-mono break-all mt-0.5">{detail}</div>}
      {sub && <div className="text-[11px] text-slate-500 mt-0.5">{sub}</div>}
    </div>
  </div>
);
