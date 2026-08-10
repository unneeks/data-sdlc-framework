import React, { useState } from 'react';
import { DeliveryType, classifyPrompt } from '../services/api';
import { ArrowRight, CheckCircle2, Sparkles, Layers, Cpu, ArrowUpCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  deliveryTypes: DeliveryType[];
  onSelectDeliveryType: (typeId: string) => void;
}

export const DeliveryTypeOnboarding: React.FC<Props> = ({ deliveryTypes, onSelectDeliveryType }) => {
  const [promptText, setPromptText] = useState('Move the customer warehouse tables from legacy Teradata to the new Cloud Lakehouse architecture.');
  const [classificationResult, setClassificationResult] = useState<any>(null);
  const [isClassifying, setIsClassifying] = useState(false);

  const handleClassify = async () => {
    setIsClassifying(true);
    setClassificationResult(null);
    setTimeout(async () => {
      const res = await classifyPrompt(promptText);
      setClassificationResult(res);
      setIsClassifying(false);
    }, 1200); // Artificial delay for premium AI feel
  };

  const containerVariants: any = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const itemVariants: any = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <div className="space-y-10 pb-12">
      {/* Premium Header Banner */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="glass-panel p-10 rounded-3xl relative overflow-hidden bg-gradient-to-br from-indigo-950/80 via-slate-900 to-slate-950 border border-indigo-500/20 shadow-2xl"
      >
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/3 pointer-events-none" />
        
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-bold uppercase tracking-widest">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Delivery Intent Gateway</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight leading-tight">
            What are you building today?
          </h2>
          <p className="text-slate-400 text-sm md:text-base leading-relaxed max-w-2xl">
            Describe your business request in natural language. The ecosystem will auto-classify your intent, assemble the correct multi-agent workforce, and instantiate a deterministic delivery blueprint.
          </p>
        </div>
      </motion.div>

      {/* AI Request Classifier Box */}
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 via-cyan-500 to-emerald-500 rounded-3xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
          <div className="relative glass-panel p-2 rounded-3xl flex items-center bg-slate-950/90 border border-slate-700">
            <div className="pl-6 pr-2">
              <Cpu className="w-6 h-6 text-indigo-400" />
            </div>
            <input
              type="text"
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              placeholder="E.g., Move the customer tables to the new Lakehouse..."
              className="flex-1 bg-transparent border-none px-4 py-5 text-lg text-white focus:outline-none placeholder-slate-600"
              onKeyDown={(e) => e.key === 'Enter' && handleClassify()}
            />
            <button
              onClick={handleClassify}
              disabled={isClassifying}
              className="m-2 p-4 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 flex items-center justify-center transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isClassifying ? (
                <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <ArrowUpCircle className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        <AnimatePresence>
          {classificationResult && (
            <motion.div 
              initial={{ opacity: 0, height: 0, y: -20 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.5, type: "spring" }}
              className="overflow-hidden"
            >
              <div className="p-8 rounded-3xl bg-slate-900/80 border border-indigo-500/40 shadow-2xl space-y-6 backdrop-blur-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center glow-emerald">
                      <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                    </div>
                    <div>
                      <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Identified Blueprint</span>
                      <h4 className="text-2xl font-extrabold text-white bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
                        {classificationResult.primary_delivery_type.replace(/_/g, ' ')}
                      </h4>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-black text-white">{(classificationResult.confidence * 100).toFixed(0)}%</div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Confidence Score</span>
                  </div>
                </div>

                <div className="space-y-3 pt-4 border-t border-slate-800/80">
                  <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider">Classification Rationale:</span>
                  <motion.ul variants={containerVariants} initial="hidden" animate="show" className="grid grid-cols-1 gap-3">
                    {classificationResult.evidence_reasoning.map((reason: string, idx: number) => (
                      <motion.li key={idx} variants={itemVariants} className="flex items-center space-x-3 bg-slate-950/60 p-4 rounded-xl border border-slate-800/60">
                        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse shadow-[0_0_10px_rgba(99,102,241,0.8)]" />
                        <span className="text-sm font-medium text-slate-300">{reason}</span>
                      </motion.li>
                    ))}
                  </motion.ul>
                </div>

                <div className="pt-6 mt-2 border-t border-slate-800 flex items-center justify-end space-x-4">
                  <button className="px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-sm border border-slate-700 transition">
                    Change Delivery Type
                  </button>
                  <button
                    onClick={() => onSelectDeliveryType(classificationResult.primary_delivery_type)}
                    className="px-8 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-sm shadow-xl shadow-emerald-600/20 transition transform hover:-translate-y-0.5"
                  >
                    Accept & Instantiate Plan
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Manual Selection Grid */}
      <div className="space-y-6 pt-10">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center space-x-2">
          <Layers className="w-4 h-4 text-slate-400" />
          <span>Or Select Manually from Catalog</span>
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {deliveryTypes.map((dt) => (
            <motion.div
              key={dt.id}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSelectDeliveryType(dt.id)}
              className="glass-panel-interactive p-6 rounded-2xl cursor-pointer flex flex-col justify-between group"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-slate-800/80 px-2 py-1 rounded-md">
                    {dt.phases_count} Phases
                  </span>
                  <span className={`text-[10px] px-2.5 py-1 rounded-md font-bold uppercase tracking-wider ${
                    dt.baseline_risk === 'HIGH' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}>
                    {dt.baseline_risk} Risk
                  </span>
                </div>
                <h4 className="text-xl font-bold text-white group-hover:text-indigo-300 transition-colors">
                  {dt.name}
                </h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                  {dt.description}
                </p>
              </div>

              <div className="mt-8 flex items-center justify-between text-indigo-400 font-bold text-sm">
                <span>Configure</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};
