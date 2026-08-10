import React, { useState, useEffect } from 'react';
import { fetchImpactAnalysis } from '../services/api';
import { GitBranch, AlertTriangle, ShieldAlert, CheckCircle2, GitMerge } from 'lucide-react';
import { motion } from 'framer-motion';

export const ImpactAndRCAViewer: React.FC = () => {
  const [impactData, setImpactData] = useState<any>(null);

  useEffect(() => {
    fetchImpactAnalysis().then(setImpactData);
  }, []);

  if (!impactData) return (
    <div className="flex justify-center items-center h-64">
      <div className="w-8 h-8 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
    </div>
  );

  const { technical_impact } = impactData;

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 text-rose-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-rose-500/10 rounded-full border border-rose-500/20">
            <ShieldAlert className="w-4 h-4" />
            <span>Continuous Assurance & RCA</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Impact & Root Cause Analysis</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Deterministic technical lineage diffs combined with AI-driven <strong className="text-white">Test Failure Diagnostics</strong> and Root Cause evidence extraction.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-panel p-8 rounded-3xl relative overflow-hidden"
        >
          <div className="flex items-center space-x-3 mb-6 text-white">
            <GitMerge className="w-5 h-5 text-indigo-400" />
            <h3 className="text-lg font-bold">Technical Lineage Impact Graph</h3>
          </div>

          <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 space-y-4 font-mono text-sm leading-relaxed overflow-x-auto custom-scrollbar">
            <div className="text-amber-400 font-bold tracking-wider uppercase text-[10px] mb-2">Modified Base Files</div>
            {technical_impact.root_changed_files.map((file: string, idx: number) => (
              <div key={idx} className="flex items-center space-x-3 text-slate-300 pl-2">
                <span className="text-amber-500/50">├──</span>
                <span>{file}</span>
              </div>
            ))}

            <div className="text-cyan-400 font-bold tracking-wider uppercase text-[10px] pt-4 mb-2">Redirected Source Assets</div>
            {technical_impact.redirected_assets.map((asset: any, idx: number) => (
              <div key={idx} className="flex items-center space-x-3 text-slate-300 pl-2">
                <span className="text-cyan-500/50">├──</span>
                <span>{asset.name} <span className="text-slate-500 mx-2">➔</span> {asset.new_target}</span>
              </div>
            ))}

            <div className="text-indigo-400 font-bold tracking-wider uppercase text-[10px] pt-4 mb-2">Downstream dbt Impacts</div>
            {technical_impact.impacted_downstream_models.map((model: any, idx: number) => (
              <div key={idx} className="flex items-center space-x-3 text-slate-300 pl-4">
                <span className="text-indigo-500/50">└──</span>
                <span>{model.name}</span>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-panel p-8 rounded-3xl relative overflow-hidden bg-gradient-to-br from-slate-900 to-rose-950/20 border-rose-500/20"
        >
          <div className="absolute top-0 right-0 w-64 h-64 bg-rose-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
          
          <div className="flex items-center justify-between mb-6 relative z-10 text-white">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-5 h-5 text-rose-400" />
              <h3 className="text-lg font-bold">RCA Diagnostics</h3>
            </div>
            <span className="px-3 py-1 rounded-md bg-rose-500/20 text-rose-400 text-[10px] font-bold tracking-widest uppercase border border-rose-500/30 shadow-[0_0_10px_rgba(244,63,94,0.3)]">
              93% Confidence
            </span>
          </div>

          <div className="relative z-10 space-y-6">
            <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
              <div className="text-[10px] font-bold text-rose-400 uppercase tracking-widest">Failed Test Trace</div>
              <div className="text-base font-bold text-white">Source-Target Timestamp Reconciliation</div>
              
              <div className="text-sm space-y-2 mt-2">
                <div className="flex"><span className="text-slate-500 w-24 shrink-0">Expected:</span> <span className="text-slate-300 font-mono text-xs">ISO-8601 (Microsecond Precision)</span></div>
                <div className="flex"><span className="text-rose-400 w-24 shrink-0 font-bold">Actual:</span> <span className="text-rose-300 font-mono text-xs font-bold">Format Mismatch (DW UTC vs Epoch), Drift = 3.8%</span></div>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-rose-950/20 border border-rose-500/30">
              <div className="text-[10px] font-bold text-amber-400 uppercase tracking-widest mb-2">Isolated Root Cause</div>
              <p className="text-sm text-slate-300 leading-relaxed">
                Source feed redirection to Lakehouse Parquet storage omitted explicit timezone normalization during Data Design translation, causing legacy DW UTC text timestamps to be parsed as local epoch microseconds by the BigLake reader.
              </p>
            </div>

            <div className="space-y-3">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Evidence Chain Extraction</div>
              <ul className="space-y-2">
                <li className="flex items-center space-x-3 text-sm text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Git diff (salesforce_ingest.py L42-L58)</span>
                </li>
                <li className="flex items-center space-x-3 text-sm text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Data profile metadata parity scan</span>
                </li>
                <li className="flex items-center space-x-3 text-sm text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Historical incident pattern match (INC-2025-041)</span>
                </li>
              </ul>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};
