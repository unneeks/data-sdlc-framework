import React, { useEffect, useState } from 'react';
import {
  Plug, CheckCircle2, XCircle, Loader2, Save, KeyRound, Globe, FolderOpen, Briefcase, RotateCcw,
} from 'lucide-react';
import { motion } from 'framer-motion';
import {
  ConnectionSettings, ConnectionTestResult,
  fetchConnectionSettings, saveConnectionSettings, runConnectionTest,
} from '../services/api';

const EMPTY_SETTINGS: ConnectionSettings = { credentials_path: '', profile: '', region: '', project: '' };

export const AgentCoreConnectionTester: React.FC = () => {
  const [settings, setSettings] = useState<ConnectionSettings>(EMPTY_SETTINGS);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ConnectionTestResult | null>(null);
  const [dirty, setDirty] = useState(false);

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
