import React, { useState } from 'react';
import { Terminal, Copy, Check, Play } from 'lucide-react';
import { motion } from 'framer-motion';

export const CliIntegrationExplorer: React.FC = () => {
  const [activeCli, setActiveCli] = useState<'gemini' | 'copilot'>('gemini');
  const [selectedAgent, setSelectedAgent] = useState('impact-analysis-agent');
  const [copied, setCopied] = useState(false);
  const [cliOutput, setCliOutput] = useState<string | null>(null);

  const geminiCmd = `gemini-agent run --agent ${selectedAgent} --prompt "Analyze business change request CR-2026-8942"`;
  const copilotCmd = `gh copilot agent run --agent ${selectedAgent} --project customer-360`;

  const activeCmd = activeCli === 'gemini' ? geminiCmd : copilotCmd;

  const handleCopy = () => {
    navigator.clipboard.writeText(activeCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRunSimulatedCli = () => {
    if (activeCli === 'gemini') {
      setCliOutput(
        `🤖 [Gemini CLI Agent Invocation: ${selectedAgent}]\n` +
        `   Role: Data Systems Architect | Trust Score: 95%\n` +
        `   Command: ${geminiCmd}\n\n` +
        `--- EXECUTION SUMMARY ---\n` +
        `✓ Skills Activated: dependency-analysis, impact-analysis\n` +
        `✓ Tools Executed: lineage-scanner, git-diff-analyzer\n` +
        `✓ 14 Technical Assets & 4 Delivery Tasks Impacted\n` +
        `Status: SUCCESS (Certified)`
      );
    } else {
      setCliOutput(
        `# 🐙 GitHub Copilot CLI — Agent Report: ${selectedAgent}\n\n` +
        `> **Role**: Data Systems Architect | **Trust Score**: 95%\n\n` +
        `### Analysis Summary\n` +
        `The agent evaluated prompt 'CR-2026-8942' against the Customer 360 project graph.\n` +
        `- **Skills**: \`dependency-analysis\`, \`impact-analysis\`\n` +
        `- **Result**: 14 Technical Assets Impacted, Release Gate BLOCKED pending RCA remediation.`
      );
    }
  };

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 text-cyan-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-cyan-500/10 rounded-full border border-cyan-500/20">
            <Terminal className="w-4 h-4" />
            <span>Developer Extensibility</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">CLI Integrations</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Invoke any agent directly from your terminal workspace using the <strong className="text-white">Gemini CLI</strong> or <strong className="text-white">GitHub Copilot CLI</strong>.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Control Panel */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-panel p-8 rounded-3xl space-y-8"
        >
          <div className="space-y-3">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Select Target Environment</label>
            <div className="flex p-1.5 bg-slate-950 rounded-2xl border border-slate-800">
              <button
                onClick={() => setActiveCli('gemini')}
                className={`flex-1 py-3 rounded-xl text-sm font-bold transition ${
                  activeCli === 'gemini' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Gemini CLI
              </button>
              <button
                onClick={() => setActiveCli('copilot')}
                className={`flex-1 py-3 rounded-xl text-sm font-bold transition ${
                  activeCli === 'copilot' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Copilot CLI
              </button>
            </div>
          </div>

          <div className="space-y-3">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Select Target Agent</label>
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-4 py-4 text-sm font-bold text-white focus:outline-none focus:border-indigo-500 hover:border-slate-700 transition appearance-none cursor-pointer"
            >
              <option value="impact-analysis-agent">Impact Analysis Agent</option>
              <option value="regression-test-agent">Regression Test Agent</option>
              <option value="data-quality-agent">Data Quality Agent</option>
              <option value="delivery-compliance-agent">Delivery Compliance Agent</option>
              <option value="test-failure-analysis-agent">Test Failure Analysis Agent</option>
              <option value="migration-architect-agent">Migration Architect Agent</option>
            </select>
          </div>

          <button
            onClick={handleRunSimulatedCli}
            className="w-full py-4 rounded-2xl bg-gradient-to-r from-cyan-600 to-blue-500 hover:from-cyan-500 hover:to-blue-400 text-white font-bold text-sm shadow-xl shadow-cyan-600/30 flex items-center justify-center space-x-2 transition transform hover:-translate-y-1"
          >
            <Play className="w-5 h-5 fill-current" />
            <span>Execute Agent Command</span>
          </button>
        </motion.div>

        {/* Terminal Window */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-2 glass-panel p-8 rounded-3xl space-y-6 flex flex-col"
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Generated Snippet</span>
              <button
                onClick={handleCopy}
                className="flex items-center space-x-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-bold transition"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            <div className="p-5 rounded-2xl bg-[#0a0a0a] border border-slate-800 text-sm font-mono text-cyan-300 break-all shadow-inner">
              <span className="text-slate-600 select-none">$ </span>
              {activeCmd}
            </div>
          </div>

          <div className="space-y-3 flex-1 flex flex-col">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-4">Simulated Execution Output</span>
            <div className="flex-1 p-6 rounded-2xl bg-black border border-slate-800 text-xs md:text-sm font-mono text-slate-300 whitespace-pre-wrap shadow-inner overflow-y-auto custom-scrollbar min-h-[250px]">
              {cliOutput || (
                <div className="text-slate-600 flex flex-col items-center justify-center h-full space-y-4">
                  <Terminal className="w-12 h-12 opacity-50" />
                  <span>Run command to view agent response stream...</span>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};
