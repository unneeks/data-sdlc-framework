import React, { useEffect, useRef, useState } from 'react';
import {
  Clock, DollarSign, FileText, Users, CheckCircle2, Circle, ArrowRight, Loader2,
  RotateCcw, Play, User, Database, ShieldCheck, Rocket, ChevronDown, ChevronRight,
  BarChart3, AlertCircle, KeyRound,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  DashboardSnapshot, DashboardLane, AwsIdentity,
  startDashboard, fetchDashboardSnapshot, reviewWorkProduct, fetchAwsIdentity,
} from '../services/api';

const POLL_INTERVAL_MS = 1200;

const LANE_ICONS: Record<string, React.ReactNode> = {
  'data-analyst': <User className="w-5 h-5" />,
  'data-engineer': <Database className="w-5 h-5" />,
  'test-engineer': <ShieldCheck className="w-5 h-5" />,
  'release-lead': <Rocket className="w-5 h-5" />,
};

const COLOR_MAP: Record<string, { bar: string; ring: string; dot: string; text: string }> = {
  blue: { bar: 'bg-blue-600', ring: 'ring-blue-500/40', dot: 'bg-blue-400', text: 'text-blue-400' },
  emerald: { bar: 'bg-emerald-600', ring: 'ring-emerald-500/40', dot: 'bg-emerald-400', text: 'text-emerald-400' },
  violet: { bar: 'bg-violet-600', ring: 'ring-violet-500/40', dot: 'bg-violet-400', text: 'text-violet-400' },
  orange: { bar: 'bg-orange-600', ring: 'ring-orange-500/40', dot: 'bg-orange-400', text: 'text-orange-400' },
};

const WP_STATUS_META: Record<string, { dot: string; label: string }> = {
  COMPLETED: { dot: 'bg-emerald-500', label: 'Completed' },
  IN_PROGRESS: { dot: 'bg-amber-500', label: 'In progress' },
  AWAITING_REVIEW: { dot: 'bg-cyan-500', label: 'Awaiting human review' },
  NOT_STARTED: { dot: 'bg-slate-600', label: 'Not started' },
};

function formatElapsed(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.max(0, Math.round(diffMs / 60000));
  return mins < 1 ? 'just now' : `${mins}m ago`;
}

interface ProjectDashboardProps {
  projectId?: string | null;
  projectTitle?: string | null;
}

export const ProjectDashboard: React.FC<ProjectDashboardProps> = ({ projectId, projectTitle }) => {
  const [live, setLive] = useState(false);
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [expandedLane, setExpandedLane] = useState<string | null>(null);
  const [reviewingKey, setReviewingKey] = useState<string | null>(null);
  const [awsIdentity, setAwsIdentity] = useState<AwsIdentity | null>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    fetchAwsIdentity().then(setAwsIdentity);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const poll = async () => setSnapshot(await fetchDashboardSnapshot(sessionId));
    poll();
    pollRef.current = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => { if (pollRef.current) window.clearInterval(pollRef.current); };
  }, [sessionId]);

  const handleStart = async () => {
    const { session_id } = await startDashboard(live, projectTitle || undefined, projectId || undefined);
    setSessionId(session_id);
  };

  const handleReset = () => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    setSessionId(null);
    setSnapshot(null);
    setExpandedLane(null);
  };

  const handleReview = async (laneKey: string, workProductKey: string, approve: boolean) => {
    if (!sessionId) return;
    setReviewingKey(`${laneKey}:${workProductKey}`);
    await reviewWorkProduct(sessionId, laneKey, workProductKey, approve, approve ? 'v1.0' : '');
    setSnapshot(await fetchDashboardSnapshot(sessionId));
    setReviewingKey(null);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Start controls (before a session exists) */}
      {!snapshot && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="glass-panel p-8 rounded-3xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-blue-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/4 pointer-events-none" />
          <div className="relative z-10 space-y-4">
            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-500/10 text-blue-300 text-xs font-bold border border-blue-500/20 uppercase tracking-widest">
              <BarChart3 className="w-3.5 h-3.5" /><span>Project Dashboard</span>
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">{projectTitle || 'Customer Payments Data Product'}</h2>
            <p className="text-slate-400 text-sm max-w-2xl">
              End-to-end SDLC supported by AI agents — Data Analyst, Data Engineer, Test Engineer and
              Release Lead run concurrently, producing work products through Requirements, Design,
              Build, Test and Release. DEMO mode is fully scripted; LIVE mode invokes real AgentCore
              Harness / GitHub Copilot agents and reports their real token usage and cost.
            </p>
            <div className="flex items-center gap-3 pt-2">
              <div className="flex items-center gap-2 bg-slate-900/60 border border-slate-700 rounded-xl p-1">
                <button onClick={() => setLive(false)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${!live ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}>DEMO</button>
                <button onClick={() => setLive(true)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${live ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}>LIVE</button>
              </div>
              <button onClick={handleStart}
                className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold flex items-center gap-2 transition">
                <Play className="w-4 h-4" /> Start Project
              </button>
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-mono border ${
                awsIdentity?.available ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300' : 'bg-slate-900/60 border-slate-700 text-slate-500'
              }`}>
                <KeyRound className="w-3 h-3" />
                {awsIdentity?.available ? `AWS: ${awsIdentity.arn?.split('/').pop() || awsIdentity.account}` : 'AWS: not connected (aws sso login)'}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {snapshot && (
        <>
          {/* Header + stat tiles */}
          <div className="glass-panel p-6 rounded-3xl">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-2xl font-extrabold text-white tracking-tight">{snapshot.title}</h2>
                  <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">In Progress</span>
                </div>
                <p className="text-slate-500 text-sm mt-1">End-to-end SDLC supported by AI agents</p>
              </div>
              <div className="flex flex-wrap items-center gap-6">
                <StatTile icon={<Clock className="w-4 h-4" />} label="Elapsed Time" value={formatElapsed(snapshot.elapsed_seconds)} sub={snapshot.live ? 'LIVE' : 'DEMO'} />
                <StatTile icon={<DollarSign className="w-4 h-4" />} label="Total Token Cost" value={`$${snapshot.token_cost_usd.toFixed(2)}`} sub={`~${Math.round(snapshot.total_tokens / 1000)}k tokens`} />
                <StatTile icon={<FileText className="w-4 h-4" />} label="Work Products" value={`${snapshot.work_products_done} / ${snapshot.work_products_total}`} sub={`${Math.round(100 * snapshot.work_products_done / Math.max(1, snapshot.work_products_total))}% complete`} />
                <StatTile icon={<Users className="w-4 h-4" />} label="Agents Active" value={`${snapshot.agents_active} / ${snapshot.agents_total}`} sub={snapshot.agents_active === snapshot.agents_total ? 'All running' : 'Some idle'} />
                <button onClick={handleReset} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition">
                  <RotateCcw className="w-3.5 h-3.5" /> Reset
                </button>
              </div>
            </div>

            {/* Phase stepper */}
            <div className="flex items-center gap-1 overflow-x-auto pt-6 pb-1">
              {snapshot.phases.map((phase, idx) => {
                const isDone = phase.total > 0 && phase.done >= phase.total;
                const isCurrent = !isDone && phase.done > 0;
                return (
                  <React.Fragment key={phase.key}>
                    {idx > 0 && <div className={`h-0.5 w-10 shrink-0 ${isDone || isCurrent ? 'bg-blue-500' : 'bg-slate-700'}`} />}
                    <div className="flex items-center gap-2 shrink-0">
                      {isDone ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <Circle className={`w-5 h-5 ${isCurrent ? 'text-blue-400' : 'text-slate-600'}`} />}
                      <div>
                        <div className={`text-sm font-bold ${isDone ? 'text-emerald-400' : isCurrent ? 'text-white' : 'text-slate-500'}`}>{phase.label}</div>
                        <div className="text-[11px] text-slate-500">{phase.done} / {phase.total}</div>
                      </div>
                    </div>
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* Lane cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {snapshot.lanes.map(lane => (
              <LaneCard
                key={lane.key} lane={lane}
                expanded={expandedLane === lane.key}
                onToggleLogs={() => setExpandedLane(expandedLane === lane.key ? null : lane.key)}
                onReview={handleReview}
                reviewingKey={reviewingKey}
              />
            ))}
          </div>

          {/* Bottom row */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <RecentActivityPanel events={snapshot.recent_activity} />
            <HumanAttentionPanel items={snapshot.human_attention_required} onReview={handleReview} reviewingKey={reviewingKey} />
            <ProjectInsightsPanel snapshot={snapshot} />
          </div>
        </>
      )}
    </div>
  );
};

const StatTile: React.FC<{ icon: React.ReactNode; label: string; value: string; sub: string }> = ({ icon, label, value, sub }) => (
  <div className="flex items-center gap-3">
    <div className="w-9 h-9 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400">{icon}</div>
    <div>
      <div className="text-[11px] text-slate-500 font-semibold uppercase tracking-wide">{label}</div>
      <div className="text-lg font-extrabold text-white leading-tight">{value}</div>
      <div className="text-[11px] text-slate-500">{sub}</div>
    </div>
  </div>
);

const LaneCard: React.FC<{
  lane: DashboardLane; expanded: boolean; onToggleLogs: () => void;
  onReview: (laneKey: string, wpKey: string, approve: boolean) => void; reviewingKey: string | null;
}> = ({ lane, expanded, onToggleLogs, onReview, reviewingKey }) => {
  const colors = COLOR_MAP[lane.color] || COLOR_MAP.blue;
  const statusMeta = {
    RUNNING: { dot: 'bg-emerald-400 animate-pulse', label: 'Running' },
    WAITING_FOR_APPROVAL: { dot: 'bg-amber-400', label: 'Waiting for approval' },
    COMPLETED: { dot: 'bg-emerald-400', label: 'Completed' },
    FAILED: { dot: 'bg-rose-500', label: 'Failed' },
    IDLE: { dot: 'bg-slate-500', label: 'Idle' },
  }[lane.status];

  return (
    <div className="glass-panel rounded-2xl overflow-hidden flex flex-col">
      <div className={`${colors.bar} px-4 py-3`}>
        <div className="flex items-center gap-2 text-white">
          {LANE_ICONS[lane.key] || <User className="w-5 h-5" />}
          <div>
            <div className="text-sm font-bold leading-tight">{lane.name}</div>
            <div className="text-[11px] opacity-80 leading-tight">{lane.role}</div>
          </div>
        </div>
      </div>

      <div className="p-4 flex-1 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
            <span className={`w-2 h-2 rounded-full ${statusMeta.dot}`} /> {statusMeta.label}
          </div>
          <button onClick={onToggleLogs} className="text-[11px] text-slate-500 hover:text-white flex items-center gap-1">
            View logs {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </button>
        </div>

        <div className="rounded-xl bg-slate-900/60 p-3 flex gap-2">
          <Loader2 className={`w-4 h-4 mt-0.5 shrink-0 ${colors.text} ${lane.status === 'RUNNING' ? 'animate-spin' : ''}`} />
          <div>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-0.5">Current activity</div>
            <div className="text-xs text-slate-300 line-clamp-3">{lane.current_activity}</div>
          </div>
        </div>

        <AnimatePresence>
          {expanded && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <div className="rounded-xl bg-black/40 p-2 font-mono text-[10px] text-slate-400 space-y-1 max-h-32 overflow-y-auto custom-scrollbar">
                {lane.events.slice(-10).map((e, i) => (
                  <div key={i}>{e.event_type}{e.payload?.name ? `: ${e.payload.name}` : ''}</div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <div className="text-xs font-bold text-slate-300">Work Products</div>
            <div className="text-[11px] text-slate-500">{lane.counts.done} / {lane.counts.total}</div>
          </div>
          <div className="space-y-1">
            {lane.work_products.map(wp => {
              const meta = WP_STATUS_META[wp.status];
              const isReviewing = reviewingKey === `${lane.key}:${wp.key}`;
              return (
                <div key={wp.key} className="flex items-center gap-2 text-xs py-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${meta.dot}`} />
                  <span className="text-slate-300 truncate flex-1">{wp.name}</span>
                  {wp.version && <span className="text-[10px] text-slate-500 font-mono shrink-0">{wp.version}</span>}
                  {wp.status === 'AWAITING_REVIEW' ? (
                    <div className="flex gap-1 shrink-0">
                      <button disabled={isReviewing} onClick={() => onReview(lane.key, wp.key, true)}
                        className="px-1.5 py-0.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-semibold disabled:opacity-50">
                        {isReviewing ? '…' : 'Approve'}
                      </button>
                    </div>
                  ) : (
                    <span className="text-[10px] text-slate-500 shrink-0">{timeAgo(wp.updated_at)}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="mt-auto pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
          <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {formatElapsed(lane.elapsed_seconds)}</span>
          <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" /> ${lane.token_cost_usd.toFixed(2)} <span className="text-slate-600">~{Math.round(lane.total_tokens / 1000)}k tok</span></span>
        </div>
      </div>
    </div>
  );
};

const RecentActivityPanel: React.FC<{ events: any[] }> = ({ events }) => (
  <div className="glass-panel rounded-2xl p-4">
    <h4 className="text-sm font-bold text-white mb-3">Recent Activity (All Agents)</h4>
    <div className="space-y-1.5 max-h-56 overflow-y-auto custom-scrollbar">
      {events.slice(-8).reverse().map((e, i) => (
        <div key={i} className="flex items-start gap-2 text-[11px]">
          <span className="text-slate-600 font-mono shrink-0">{e.timestamp?.slice(11, 19)}</span>
          <span className="text-slate-400 flex-1">
            <span className="font-semibold text-slate-300">{e.source_agent_id}</span>{' '}
            {e.event_type.replace(/_/g, ' ').toLowerCase()}
            {e.payload?.name ? ` — ${e.payload.name}` : ''}
          </span>
        </div>
      ))}
      {events.length === 0 && <div className="text-xs text-slate-600">No activity yet.</div>}
    </div>
  </div>
);

const HumanAttentionPanel: React.FC<{
  items: DashboardSnapshot['human_attention_required']; onReview: (l: string, w: string, a: boolean) => void; reviewingKey: string | null;
}> = ({ items, onReview, reviewingKey }) => (
  <div className="glass-panel rounded-2xl p-4">
    <div className="flex items-center gap-2 mb-3">
      <h4 className="text-sm font-bold text-white">Human Attention Required</h4>
      {items.length > 0 && <span className="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 text-[11px] font-bold">{items.length}</span>}
    </div>
    <div className="space-y-2">
      {items.map(item => {
        const isReviewing = reviewingKey === `${item.lane_key}:${item.work_product_key}`;
        return (
          <div key={`${item.lane_key}-${item.work_product_key}`} className="flex items-center justify-between gap-2 rounded-xl bg-slate-900/60 px-3 py-2">
            <div className="min-w-0">
              <div className="text-xs font-semibold text-white truncate">{item.work_product_name}</div>
              <div className="text-[11px] text-slate-500">{item.lane_name} · {timeAgo(item.requested_at)}</div>
            </div>
            <button disabled={isReviewing} onClick={() => onReview(item.lane_key, item.work_product_key, true)}
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shrink-0 disabled:opacity-50">
              {isReviewing ? '…' : 'Review'}
            </button>
          </div>
        );
      })}
      {items.length === 0 && <div className="text-xs text-slate-600 flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Nothing waiting on you.</div>}
    </div>
  </div>
);

const ProjectInsightsPanel: React.FC<{ snapshot: DashboardSnapshot }> = ({ snapshot }) => {
  const anyFailed = snapshot.lanes.some(l => l.status === 'FAILED');
  return (
    <div className="glass-panel rounded-2xl p-4 space-y-3">
      <h4 className="text-sm font-bold text-white">Project Insights</h4>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-slate-900/60 p-3">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Target vs Actual</div>
          <div className="text-lg font-extrabold text-emerald-400 mt-1">{snapshot.live ? '—' : '−80% faster'}</div>
          <div className="text-[10px] text-slate-500">vs. traditional delivery</div>
        </div>
        <div className="rounded-xl bg-slate-900/60 p-3">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Estimated Cost</div>
          <div className="text-lg font-extrabold text-white mt-1">${snapshot.token_cost_usd.toFixed(2)}</div>
          <div className="text-[10px] text-slate-500">~{Math.round(snapshot.total_tokens / 1000)}k tokens</div>
        </div>
      </div>
      {anyFailed ? (
        <div className="rounded-xl bg-rose-950/30 border border-rose-500/30 px-3 py-2 flex items-center gap-2 text-xs text-rose-300">
          <AlertCircle className="w-4 h-4 shrink-0" /> One or more agent lanes failed — check View logs.
        </div>
      ) : (
        <div className="rounded-xl bg-emerald-950/30 border border-emerald-500/30 px-3 py-2 flex items-center gap-2 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 shrink-0" /> On track to complete all work products today.
        </div>
      )}
    </div>
  );
};
