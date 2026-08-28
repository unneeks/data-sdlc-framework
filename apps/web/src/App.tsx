import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { BusinessAppOnboarding } from './components/BusinessAppOnboarding';
import { DeliveryTypeOnboarding } from './components/DeliveryTypeOnboarding';
import { DeliveryComparisonMatrix } from './components/DeliveryComparisonMatrix';
import { DigitalTwinExplorer } from './components/DigitalTwinExplorer';
import { MetamodelExplorer } from './components/MetamodelExplorer';
import { AgentExplorer } from './components/AgentExplorer';
import { SkillsExplorer } from './components/SkillsExplorer';
import { EngineeringControlCenter } from './components/EngineeringControlCenter';
import { HeroDemoSimulation } from './components/HeroDemoSimulation';
import { ImpactAndRCAViewer } from './components/ImpactAndRCAViewer';
import { DeliveryGateApproval } from './components/DeliveryGateApproval';
import { CliIntegrationExplorer } from './components/CliIntegrationExplorer';
import { OntologyExplorer } from './components/OntologyExplorer';

import { fetchDeliveryTypes, fetchAgents, DeliveryType, Agent } from './services/api';

const API_BASE = './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('project_onboarding');
  const [deliveryTypes, setDeliveryTypes] = useState<DeliveryType[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [harnessMode, setHarnessMode] = useState<string>('DEMO');
  const [runtimeArn, setRuntimeArn] = useState<string>('');
  const [demoState, setDemoState] = useState({
    current_step: 1,
    total_steps: 9,
    step_details: {
      title: "Change Request Received (CR-2026-8942)",
      details: "Request: Redirect Salesforce & SAP source feeds to Cloud Lakehouse"
    }
  });

  useEffect(() => {
    fetchDeliveryTypes().then(setDeliveryTypes);
    fetchAgents().then(setAgents);
    fetch(`${API_BASE}/status`).then(r => r.json()).then(data => {
      setHarnessMode(data.mode || 'DEMO');
      setRuntimeArn(data.agentcore_runtime || '');
    }).catch(() => {});
  }, []);

  const toggleMode = async () => {
    const newMode = harnessMode === 'REAL' ? 'DEMO' : 'REAL';
    const res = await fetch(`${API_BASE}/harness/mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: newMode })
    });
    if (res.ok) {
      const data = await res.json();
      setHarnessMode(data.mode);
    }
  };

  const handleNextDemoStep = () => {
    const nextStep = Math.min(demoState.current_step + 1, demoState.total_steps);
    const stepTitles = [
      { title: "Change Request Ingestion (CR-2026-8942)", details: "Ingested request payload for source feed redirection." },
      { title: "Delivery Type Classification", details: "Classified as DATA_PLATFORM_MIGRATION (96% Confidence)" },
      { title: "Architecture & Feasibility Assessment", details: "Feasibility Assessment Agent evaluates BigLake/Iceberg storage & cost" },
      { title: "Target Data & Technical Design", details: "Data Architecture Agent drafts schema mapping matrix dw_staging ➔ lakehouse_raw" },
      { title: "Pipeline & Infrastructure Code Update", details: "Generated terraform/lakehouse_ingestion.tf and updated salesforce_customer_ingest.py" },
      { title: "Source-to-Target Data Reconciliation", details: "Executed 10 test suites; 9 PASSED, 1 FAILED (Timestamp Precision Format Drift)" },
      { title: "Automated Root Cause Analysis", details: "Test Failure Analysis Agent isolated timezone offset error in Parquet conversion" },
      { title: "Delivery Gate Assessment", details: "Release Readiness Gate status: BLOCKED due to reconciliation failure & missing runbook" },
      { title: "Automated Remediation & PR Creation", details: "Proposed timestamp fix in dbt model, updated runbook, and generated Pull Request" }
    ];

    setDemoState({
      current_step: nextStep,
      total_steps: 9,
      step_details: stepTitles[nextStep - 1]
    });
  };

  const handleResetDemo = () => {
    setDemoState({
      current_step: 1,
      total_steps: 9,
      step_details: {
        title: "Change Request Ingestion (CR-2026-8942)",
        details: "Request: Redirect Salesforce & SAP source feeds to Cloud Lakehouse"
      }
    });
  };

  const pageVariants: any = {
    initial: { opacity: 0, y: 15, scale: 0.98 },
    in: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4, ease: "easeOut" } },
    out: { opacity: 0, y: -15, scale: 0.98, transition: { duration: 0.2, ease: "easeIn" } }
  };

  return (
    <div className="flex min-h-screen bg-transparent relative">
      <div className="ambient-bg" />
      
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <div className="flex-1 flex flex-col min-h-screen relative z-10 overflow-hidden">
        {/* AgentCore Mode Banner */}
        <div className={`px-4 py-2 flex items-center justify-between text-sm font-mono ${
          harnessMode === 'REAL'
            ? 'bg-emerald-900/80 border-b border-emerald-500/50 text-emerald-200'
            : 'bg-amber-900/80 border-b border-amber-500/50 text-amber-200'
        }`}>
          <div className="flex items-center gap-3">
            <span className={`inline-block w-2 h-2 rounded-full ${
              harnessMode === 'REAL' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
            }`} />
            <span>
              {harnessMode === 'REAL'
                ? `AGENTCORE RUNTIME — ${runtimeArn}`
                : 'LOCAL DEMO MODE — responses served locally'}
            </span>
          </div>
          <button
            onClick={toggleMode}
            className={`px-3 py-1 rounded text-xs font-semibold transition ${
              harnessMode === 'REAL'
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                : 'bg-amber-600 hover:bg-amber-500 text-white'
            }`}
          >
            Switch to {harnessMode === 'REAL' ? 'DEMO' : 'AGENTCORE'}
          </button>
        </div>

        <TopBar onResetDemo={handleResetDemo} />

        <main className="flex-1 overflow-y-auto p-8 custom-scrollbar">
          <div className="max-w-7xl mx-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial="initial"
                animate="in"
                exit="out"
                variants={pageVariants}
                className="w-full h-full"
              >
                {activeTab === 'project_onboarding' && <BusinessAppOnboarding />}
                {activeTab === 'onboarding' && (
                  <DeliveryTypeOnboarding
                    deliveryTypes={deliveryTypes}
                    onSelectDeliveryType={(id) => setActiveTab('sdlc')}
                  />
                )}
                {activeTab === 'comparison' && <DeliveryComparisonMatrix />}
                {activeTab === 'twin' && <DigitalTwinExplorer />}
                {activeTab === 'metamodel' && <MetamodelExplorer />}
                {activeTab === 'agents' && <AgentExplorer />}
                {activeTab === 'skills' && <SkillsExplorer />}
                {activeTab === 'sdlc' && (
                  <HeroDemoSimulation
                    demoState={demoState}
                    onNextStep={handleNextDemoStep}
                    onResetDemo={handleResetDemo}
                  />
                )}
                {activeTab === 'impact' && <ImpactAndRCAViewer />}
                {activeTab === 'gate' && <DeliveryGateApproval />}
                {activeTab === 'cli' && <CliIntegrationExplorer />}
                {activeTab === 'ontology' && <OntologyExplorer />}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}
