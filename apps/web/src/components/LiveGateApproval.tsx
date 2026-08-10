import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, FileText, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';
import { fetchDashboard, approveChange, rejectChange, AgentDashboardState } from '../services/ollamaApi';

export const LiveGateApproval: React.FC = () => {
  const [dashboard, setDashboard] = useState<AgentDashboardState | null>(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await fetchDashboard();
        setDashboard(data);
      } catch (e) {
        console.error("Failed to fetch dashboard", e);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const changeRecord = dashboard?.change_record;
  const isPendingApproval = changeRecord?.status === 'pending_approval';
  const isApproved = changeRecord?.status === 'approved';
  const gateStatus = isApproved ? 'APPROVED' : isPendingApproval ? 'PENDING' : 'NO ACTIVE CHANGE';

  const handleApprove = async () => {
    try {
      await approveChange();
    } catch (e) {
      console.error(e);
    }
  };

  const handleReject = async () => {
    try {
      await rejectChange();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 text-amber-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-amber-500/10 rounded-full border border-amber-500/20">
            <ShieldCheck className="w-4 h-4" />
            <span>MCP Change Approval</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Human-in-the-Loop Gateway</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Live integration with Ollama MCP tools. Agents generate fix proposals which require operational sign-off before being applied to the production pipeline.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Gate Checklist */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="lg:col-span-2 glass-panel p-8 rounded-3xl space-y-6"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-white">Active Change Record</h3>
            <span className={`px-4 py-1.5 rounded-lg text-xs font-bold tracking-widest uppercase shadow-lg ${
              isApproved ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 
              isPendingApproval ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 
              'bg-slate-800 text-slate-400'
            }`}>
              Status: {gateStatus}
            </span>
          </div>

          {!changeRecord ? (
            <div className="p-8 text-center text-slate-500 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col items-center">
              <ShieldCheck className="w-12 h-12 mb-4 opacity-20" />
              <p>No active change record pending approval.</p>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800">
                <div className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-2 flex items-center space-x-2">
                  <FileText className="w-4 h-4" /> <span>Change Details</span>
                </div>
                <div className="text-white text-lg font-bold mb-4">ID: {changeRecord.change_id}</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                   <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                     <span className="block text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Proposed Action</span>
                     <span className="text-sm font-mono text-indigo-300">{changeRecord.proposed_action}</span>
                   </div>
                   <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                     <span className="block text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Rationale</span>
                     <span className="text-sm text-slate-300">{changeRecord.rationale}</span>
                   </div>
                </div>
              </div>
            </div>
          )}
        </motion.div>

        {/* Approver Panel */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-panel p-8 rounded-3xl space-y-6 flex flex-col justify-between"
        >
          <div className="space-y-6">
            <h3 className="text-xl font-bold text-white">Approver Panel</h3>
            
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Required Role</div>
              <div className="font-bold text-white text-lg">Lead Data Architect</div>
              <div className="text-xs text-indigo-400 font-mono">User: Operator (Local)</div>
            </div>

            <div className="space-y-3">
              <button
                disabled={!isPendingApproval}
                onClick={handleApprove}
                className={`w-full py-4 rounded-xl text-sm font-bold transition transform ${
                  isPendingApproval ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 hover:-translate-y-0.5' : 'bg-slate-900 text-slate-600 cursor-not-allowed border border-slate-800'
                }`}
              >
                Approve Change
              </button>

              <button
                disabled={!isPendingApproval}
                onClick={handleReject}
                className={`w-full py-3 rounded-xl text-sm font-bold transition ${
                  isPendingApproval ? 'bg-rose-950/40 hover:bg-rose-900/40 text-rose-400 border border-rose-500/30' : 'bg-slate-900 text-slate-600 cursor-not-allowed border border-slate-800'
                }`}
              >
                Reject Gate
              </button>
            </div>
          </div>

          <div className="text-xs text-slate-500 text-center pt-6">
            Changes are routed back to the Ollama backend via MCP tool calls.
          </div>
        </motion.div>
      </div>
    </div>
  );
};
