import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, GitPullRequest } from 'lucide-react';
import { motion } from 'framer-motion';

export const DeliveryGateApproval: React.FC = () => {
  const [gateStatus, setGateStatus] = useState<'BLOCKED' | 'APPROVED'>('BLOCKED');
  const [isFixApplied, setIsFixApplied] = useState(false);

  const handleApplyFix = () => {
    setIsFixApplied(true);
    setGateStatus('APPROVED');
  };

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 text-amber-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-amber-500/10 rounded-full border border-amber-500/20">
            <ShieldCheck className="w-4 h-4" />
            <span>Governance & Approval Gate</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Release Readiness</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Enforces mandatory delivery controls, verifiable evidence checks, and human sign-offs before deployment.
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
            <h3 className="text-xl font-bold text-white">Evidence Checklist</h3>
            <span className={`px-4 py-1.5 rounded-lg text-xs font-bold tracking-widest uppercase shadow-lg ${
              gateStatus === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-emerald-500/20' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30 shadow-rose-500/20'
            }`}>
              Status: {gateStatus}
            </span>
          </div>

          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-2xl bg-slate-900 border border-slate-800 transition hover:border-slate-700 gap-4">
              <div>
                <div className="text-sm font-bold text-white">Feasibility & Design Sign-off</div>
                <div className="text-xs text-slate-500 mt-1">Contracts verified by Migration Architect Agent</div>
              </div>
              <span className="text-emerald-400 font-bold flex items-center space-x-2 text-sm shrink-0">
                <CheckCircle2 className="w-5 h-5" />
                <span>100% Verified</span>
              </span>
            </div>

            <div className={`flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-2xl border transition gap-4 ${isFixApplied ? 'bg-slate-900 border-slate-800 hover:border-slate-700' : 'bg-rose-950/20 border-rose-500/30'}`}>
              <div>
                <div className="text-sm font-bold text-white">Regression & Reconciliation Suite</div>
                <div className="text-xs text-slate-500 mt-1">Source-target parity verification</div>
              </div>
              <span className={`font-bold flex items-center space-x-2 text-sm shrink-0 ${isFixApplied ? 'text-emerald-400' : 'text-rose-400'}`}>
                {isFixApplied ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                <span>{isFixApplied ? '10 / 10 PASSED' : '9 / 10 PASSED'}</span>
              </span>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-2xl bg-slate-900 border border-slate-800 transition hover:border-slate-700 gap-4">
              <div>
                <div className="text-sm font-bold text-white">Data Quality & Governance Audit</div>
                <div className="text-xs text-slate-500 mt-1">PII masking and retention policies applied</div>
              </div>
              <span className="text-emerald-400 font-bold flex items-center space-x-2 text-sm shrink-0">
                <CheckCircle2 className="w-5 h-5" />
                <span>14 / 14 PASSED</span>
              </span>
            </div>

            <div className={`flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-2xl border transition gap-4 ${isFixApplied ? 'bg-slate-900 border-slate-800 hover:border-slate-700' : 'bg-rose-950/20 border-rose-500/30'}`}>
              <div>
                <div className="text-sm font-bold text-white">Lakehouse Operational Runbook</div>
                <div className="text-xs text-slate-500 mt-1">SRE tier-1 support documentation</div>
              </div>
              <span className={`font-bold flex items-center space-x-2 text-sm shrink-0 ${isFixApplied ? 'text-emerald-400' : 'text-rose-400'}`}>
                {isFixApplied ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                <span>{isFixApplied ? 'VERIFIED' : 'MISSING'}</span>
              </span>
            </div>
          </div>

          <div className="pt-6 border-t border-slate-800/80">
            <button
              onClick={handleApplyFix}
              disabled={isFixApplied}
              className={`w-full py-4 rounded-2xl font-bold text-sm shadow-xl flex items-center justify-center space-x-3 transition transform ${
                isFixApplied
                  ? 'bg-slate-900 text-slate-500 cursor-not-allowed border border-slate-800'
                  : 'bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white shadow-emerald-600/30 hover:-translate-y-1'
              }`}
            >
              <GitPullRequest className="w-5 h-5" />
              <span>{isFixApplied ? 'Remediation Applied & PR Created' : 'Create PR & Apply Automated Remediation'}</span>
            </button>
          </div>
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
              <div className="text-xs text-indigo-400 font-mono">User: Ranjit Pillai</div>
            </div>

            <div className="space-y-3">
              <button
                disabled={gateStatus === 'BLOCKED'}
                onClick={() => alert("Release Readiness Gate APPROVED!")}
                className={`w-full py-3 rounded-xl text-sm font-bold transition transform ${
                  gateStatus === 'APPROVED' ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 hover:-translate-y-0.5' : 'bg-slate-900 text-slate-600 cursor-not-allowed border border-slate-800'
                }`}
              >
                Approve Gate
              </button>

              <button
                disabled={gateStatus === 'BLOCKED'}
                onClick={() => alert("Release Readiness Gate APPROVED WITH CONDITIONS!")}
                className={`w-full py-3 rounded-xl text-sm font-bold transition ${
                  gateStatus === 'APPROVED' ? 'bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-500/30' : 'bg-slate-900 text-slate-600 cursor-not-allowed border border-slate-800'
                }`}
              >
                Approve With Conditions
              </button>

              <button
                onClick={() => alert("Gate REJECTED!")}
                className="w-full py-3 rounded-xl bg-rose-950/40 hover:bg-rose-900/40 text-rose-400 border border-rose-500/30 text-sm font-bold transition"
              >
                Reject Gate
              </button>
            </div>
          </div>

          <div className="text-xs text-slate-500 text-center pt-6">
            All gate decisions write an immutable audit log record.
          </div>
        </motion.div>
      </div>
    </div>
  );
};
