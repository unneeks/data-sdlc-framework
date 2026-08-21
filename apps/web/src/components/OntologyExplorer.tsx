import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface OntologyClass {
  id: string;
  label: string;
  comment: string;
  domain: string;
  subClassOf?: string;
  properties: { name: string; range: string; type: 'object' | 'datatype' }[];
}

interface OntologyRelation {
  from: string;
  to: string;
  label: string;
}

const DOMAINS = {
  technical: { label: 'Technical Twin', color: 'from-cyan-500 to-blue-600', badge: 'bg-cyan-500/20 text-cyan-300' },
  delivery: { label: 'Delivery Twin', color: 'from-violet-500 to-purple-600', badge: 'bg-violet-500/20 text-violet-300' },
  agent: { label: 'Agent Ecosystem', color: 'from-amber-500 to-orange-600', badge: 'bg-amber-500/20 text-amber-300' },
};

const CLASSES: OntologyClass[] = [
  { id: 'Project', label: 'Project', comment: 'A data engineering project containing assets, pipelines, and delivery plans.', domain: 'technical', properties: [
    { name: 'hasDataAsset', range: 'DataAsset', type: 'object' },
    { name: 'hasPipeline', range: 'Pipeline', type: 'object' },
    { name: 'hasDeliveryPlan', range: 'DeliveryPlan', type: 'object' },
    { name: 'name', range: 'xsd:string', type: 'datatype' },
    { name: 'description', range: 'xsd:string', type: 'datatype' },
  ]},
  { id: 'DataAsset', label: 'Data Asset', comment: 'A logical or physical data entity (table, view, topic, storage object).', domain: 'technical', subClassOf: 'LineageNode', properties: [
    { name: 'assetType', range: 'xsd:string', type: 'datatype' },
    { name: 'platform', range: 'xsd:string', type: 'datatype' },
    { name: 'schemaName', range: 'xsd:string', type: 'datatype' },
    { name: 'criticality', range: 'RiskLevel', type: 'datatype' },
    { name: 'status', range: 'AssetStatus', type: 'datatype' },
  ]},
  { id: 'Pipeline', label: 'Pipeline', comment: 'A data transformation or ingestion pipeline (dbt, Dataflow, Airflow, Spark).', domain: 'technical', subClassOf: 'LineageNode', properties: [
    { name: 'consumesInput', range: 'DataAsset', type: 'object' },
    { name: 'producesOutput', range: 'DataAsset', type: 'object' },
    { name: 'pipelineType', range: 'xsd:string', type: 'datatype' },
    { name: 'repositoryId', range: 'xsd:string', type: 'datatype' },
  ]},
  { id: 'LineageNode', label: 'Lineage Node', comment: 'A node in the data lineage graph representing an asset or transformation step.', domain: 'technical', properties: [
    { name: 'dependsOn', range: 'LineageNode', type: 'object' },
  ]},
  { id: 'LineageEdge', label: 'Lineage Edge', comment: 'A directed dependency between two lineage nodes.', domain: 'technical', properties: [
    { name: 'hasSource', range: 'LineageNode', type: 'object' },
    { name: 'hasTarget', range: 'LineageNode', type: 'object' },
  ]},
  { id: 'CodeArtifact', label: 'Code Artifact', comment: 'A versioned source code file in a repository.', domain: 'technical', properties: [
    { name: 'filePath', range: 'xsd:string', type: 'datatype' },
    { name: 'language', range: 'xsd:string', type: 'datatype' },
    { name: 'contentHash', range: 'xsd:string', type: 'datatype' },
  ]},
  { id: 'InfrastructureResource', label: 'Infrastructure Resource', comment: 'A cloud infrastructure resource managed as code.', domain: 'technical', properties: [
    { name: 'resourceType', range: 'xsd:string', type: 'datatype' },
    { name: 'provider', range: 'xsd:string', type: 'datatype' },
  ]},
  { id: 'Change', label: 'Change', comment: 'A modification event triggering impact analysis.', domain: 'technical', properties: [
    { name: 'impacts', range: 'DataAsset', type: 'object' },
    { name: 'modifiesFile', range: 'CodeArtifact', type: 'object' },
    { name: 'changeType', range: 'xsd:string', type: 'datatype' },
    { name: 'timestamp', range: 'xsd:dateTime', type: 'datatype' },
  ]},
  { id: 'Test', label: 'Test', comment: 'A validation test (schema parity, reconciliation, data quality).', domain: 'technical', properties: [
    { name: 'testsAsset', range: 'DataAsset', type: 'object' },
    { name: 'testType', range: 'xsd:string', type: 'datatype' },
    { name: 'status', range: 'TaskStatus', type: 'datatype' },
  ]},
  { id: 'DeliveryType', label: 'Delivery Type', comment: 'A category of data engineering work (migration, new product, amendment, etc.).', domain: 'delivery', properties: [
    { name: 'businessPurpose', range: 'xsd:string', type: 'datatype' },
    { name: 'baselineRisk', range: 'RiskLevel', type: 'datatype' },
  ]},
  { id: 'DeliveryBlueprint', label: 'Delivery Blueprint', comment: 'A versioned template defining standard phases, tasks, and gates.', domain: 'delivery', properties: [
    { name: 'blueprintForType', range: 'DeliveryType', type: 'object' },
    { name: 'version', range: 'xsd:string', type: 'datatype' },
  ]},
  { id: 'DeliveryPlan', label: 'Delivery Plan', comment: 'An instantiated plan for a specific project.', domain: 'delivery', properties: [
    { name: 'derivedFromBlueprint', range: 'DeliveryBlueprint', type: 'object' },
    { name: 'hasPhase', range: 'DeliveryPhase', type: 'object' },
  ]},
  { id: 'DeliveryPhase', label: 'Delivery Phase', comment: 'A sequential stage in a delivery plan.', domain: 'delivery', properties: [
    { name: 'hasTask', range: 'DeliveryTask', type: 'object' },
    { name: 'hasGate', range: 'ApprovalGate', type: 'object' },
    { name: 'sequence', range: 'xsd:integer', type: 'datatype' },
  ]},
  { id: 'DeliveryTask', label: 'Delivery Task', comment: 'A unit of work within a phase with inputs, outputs, and acceptance criteria.', domain: 'delivery', properties: [
    { name: 'requiresAgent', range: 'Agent', type: 'object' },
    { name: 'hasChecklist', range: 'ChecklistItem', type: 'object' },
    { name: 'hasAcceptanceCriterion', range: 'AcceptanceCriterion', type: 'object' },
    { name: 'status', range: 'TaskStatus', type: 'datatype' },
  ]},
  { id: 'ApprovalGate', label: 'Approval Gate', comment: 'A quality checkpoint that must pass before the next phase.', domain: 'delivery', properties: [
    { name: 'requiresEvidence', range: 'Evidence', type: 'object' },
    { name: 'hasApproval', range: 'Approval', type: 'object' },
    { name: 'status', range: 'GateStatus', type: 'datatype' },
  ]},
  { id: 'Evidence', label: 'Evidence', comment: 'A verifiable artifact supporting gate approval.', domain: 'delivery', properties: [
    { name: 'category', range: 'xsd:string', type: 'datatype' },
    { name: 'confidence', range: 'EvidenceConfidence', type: 'datatype' },
  ]},
  { id: 'Agent', label: 'Agent', comment: 'An AI agent with capabilities, skills, tools, and governance policies.', domain: 'agent', properties: [
    { name: 'hasSkill', range: 'Skill', type: 'object' },
    { name: 'usesTool', range: 'Tool', type: 'object' },
    { name: 'hasKnowledgePack', range: 'KnowledgePack', type: 'object' },
    { name: 'governedByPolicy', range: 'Policy', type: 'object' },
    { name: 'supportsDeliveryType', range: 'DeliveryType', type: 'object' },
    { name: 'assignedToTask', range: 'DeliveryTask', type: 'object' },
    { name: 'trustScore', range: 'xsd:float', type: 'datatype' },
    { name: 'engineeringRole', range: 'xsd:string', type: 'datatype' },
    { name: 'autonomyLevel', range: 'AutonomyLevel', type: 'datatype' },
    { name: 'certificationStatus', range: 'CertificationStatus', type: 'datatype' },
  ]},
  { id: 'Skill', label: 'Skill', comment: 'A reusable capability an agent can exercise.', domain: 'agent', properties: [
    { name: 'skillRequiresTool', range: 'Tool', type: 'object' },
    { name: 'riskLevel', range: 'RiskLevel', type: 'datatype' },
  ]},
  { id: 'Tool', label: 'Tool', comment: 'An executable instrument used by agents.', domain: 'agent', properties: [
    { name: 'toolType', range: 'xsd:string', type: 'datatype' },
  ]},
  { id: 'KnowledgePack', label: 'Knowledge Pack', comment: 'A curated domain knowledge collection.', domain: 'agent', properties: [
    { name: 'category', range: 'xsd:string', type: 'datatype' },
  ]},
  { id: 'Policy', label: 'Policy', comment: 'A governance rule set constraining agent behaviour.', domain: 'agent', properties: [
    { name: 'policyType', range: 'xsd:string', type: 'datatype' },
  ]},
  { id: 'DeliveryContract', label: 'Delivery Contract', comment: 'A binding agreement between a task and an agent.', domain: 'agent', properties: [
    { name: 'contractBindsAgent', range: 'Agent', type: 'object' },
    { name: 'contractBindsTask', range: 'DeliveryTask', type: 'object' },
    { name: 'contractRequiresGate', range: 'ApprovalGate', type: 'object' },
  ]},
];

const RELATIONS: OntologyRelation[] = [
  { from: 'Project', to: 'DataAsset', label: 'hasDataAsset' },
  { from: 'Project', to: 'Pipeline', label: 'hasPipeline' },
  { from: 'Project', to: 'DeliveryPlan', label: 'hasDeliveryPlan' },
  { from: 'Pipeline', to: 'DataAsset', label: 'consumesInput / producesOutput' },
  { from: 'Change', to: 'DataAsset', label: 'impacts' },
  { from: 'Change', to: 'CodeArtifact', label: 'modifiesFile' },
  { from: 'Test', to: 'DataAsset', label: 'testsAsset' },
  { from: 'DeliveryPlan', to: 'DeliveryBlueprint', label: 'derivedFromBlueprint' },
  { from: 'DeliveryBlueprint', to: 'DeliveryType', label: 'blueprintForType' },
  { from: 'DeliveryPlan', to: 'DeliveryPhase', label: 'hasPhase' },
  { from: 'DeliveryPhase', to: 'DeliveryTask', label: 'hasTask' },
  { from: 'DeliveryPhase', to: 'ApprovalGate', label: 'hasGate' },
  { from: 'ApprovalGate', to: 'Evidence', label: 'requiresEvidence' },
  { from: 'DeliveryTask', to: 'Agent', label: 'requiresAgent' },
  { from: 'Agent', to: 'Skill', label: 'hasSkill' },
  { from: 'Agent', to: 'Tool', label: 'usesTool' },
  { from: 'Agent', to: 'KnowledgePack', label: 'hasKnowledgePack' },
  { from: 'Agent', to: 'Policy', label: 'governedByPolicy' },
  { from: 'Agent', to: 'DeliveryType', label: 'supportsDeliveryType' },
  { from: 'Skill', to: 'Tool', label: 'skillRequiresTool' },
  { from: 'DeliveryContract', to: 'Agent', label: 'contractBindsAgent' },
  { from: 'DeliveryContract', to: 'DeliveryTask', label: 'contractBindsTask' },
];

const ENUMERATIONS = [
  { name: 'RiskLevel', values: ['HIGH', 'MEDIUM', 'LOW'] },
  { name: 'AutonomyLevel', values: ['AUTOMATIC', 'SEMI_AUTOMATIC', 'APPROVAL_REQUIRED'] },
  { name: 'CertificationStatus', values: ['CERTIFIED', 'EVALUATING', 'DEPRECATED'] },
  { name: 'AssetStatus', values: ['ACTIVE', 'MIGRATING', 'DEPRECATED'] },
  { name: 'TaskStatus', values: ['NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED'] },
  { name: 'GateStatus', values: ['PASSED', 'BLOCKED', 'PENDING'] },
  { name: 'EvidenceConfidence', values: ['OBSERVED', 'INFERRED', 'LIKELY', 'CONFIRMED'] },
];

export function OntologyExplorer() {
  const [selectedClass, setSelectedClass] = useState<OntologyClass | null>(null);
  const [filterDomain, setFilterDomain] = useState<string | null>(null);
  const [view, setView] = useState<'classes' | 'relations' | 'enumerations'>('classes');

  const filteredClasses = filterDomain
    ? CLASSES.filter(c => c.domain === filterDomain)
    : CLASSES;

  const filteredRelations = filterDomain
    ? RELATIONS.filter(r => {
        const fromClass = CLASSES.find(c => c.id === r.from);
        const toClass = CLASSES.find(c => c.id === r.to);
        return fromClass?.domain === filterDomain || toClass?.domain === filterDomain;
      })
    : RELATIONS;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">
          Ontology Explorer
        </h1>
        <p className="text-slate-400 mt-2">
          Browse the Data SDLC ontology — classes, properties, and relationships across the Technical Twin,
          Delivery Twin, and Agent Ecosystem domains.
        </p>
      </div>

      {/* Domain filter + view toggle */}
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setFilterDomain(null)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              !filterDomain ? 'bg-slate-700 text-white' : 'bg-slate-800/50 text-slate-400 hover:text-slate-200'
            }`}
          >All Domains</button>
          {Object.entries(DOMAINS).map(([key, d]) => (
            <button
              key={key}
              onClick={() => setFilterDomain(key)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                filterDomain === key ? 'bg-slate-700 text-white' : 'bg-slate-800/50 text-slate-400 hover:text-slate-200'
              }`}
            >{d.label}</button>
          ))}
        </div>
        <div className="flex gap-1 bg-slate-800/50 rounded-lg p-1">
          {(['classes', 'relations', 'enumerations'] as const).map(v => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium capitalize transition-all ${
                view === v ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >{v}</button>
          ))}
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <div className="text-2xl font-bold text-white">{CLASSES.length}</div>
          <div className="text-sm text-slate-400">Classes</div>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <div className="text-2xl font-bold text-white">{RELATIONS.length}</div>
          <div className="text-sm text-slate-400">Object Properties</div>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <div className="text-2xl font-bold text-white">{ENUMERATIONS.length}</div>
          <div className="text-sm text-slate-400">Enumerations</div>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <div className="text-2xl font-bold text-white">2</div>
          <div className="text-sm text-slate-400">Formats (OWL + RDFS)</div>
        </div>
      </div>

      {/* Main content */}
      {view === 'classes' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Class list */}
          <div className="lg:col-span-1 space-y-2 max-h-[600px] overflow-y-auto custom-scrollbar pr-2">
            {filteredClasses.map(cls => {
              const domain = DOMAINS[cls.domain as keyof typeof DOMAINS];
              return (
                <motion.button
                  key={cls.id}
                  whileHover={{ scale: 1.01 }}
                  onClick={() => setSelectedClass(cls)}
                  className={`w-full text-left p-3 rounded-xl border transition-all ${
                    selectedClass?.id === cls.id
                      ? 'bg-slate-700/80 border-slate-500'
                      : 'bg-slate-800/30 border-slate-700/30 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-mono ${domain.badge}`}>
                      {cls.domain.slice(0, 3).toUpperCase()}
                    </span>
                    <span className="font-medium text-white text-sm">{cls.label}</span>
                  </div>
                  {cls.subClassOf && (
                    <div className="text-xs text-slate-500 mt-1 ml-12">
                      extends {cls.subClassOf}
                    </div>
                  )}
                </motion.button>
              );
            })}
          </div>

          {/* Class detail */}
          <div className="lg:col-span-2">
            {selectedClass ? (
              <motion.div
                key={selectedClass.id}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6 space-y-5"
              >
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-white">{selectedClass.label}</h2>
                    <span className={`px-2 py-0.5 rounded text-xs font-mono ${
                      DOMAINS[selectedClass.domain as keyof typeof DOMAINS].badge
                    }`}>
                      {DOMAINS[selectedClass.domain as keyof typeof DOMAINS].label}
                    </span>
                  </div>
                  <p className="text-slate-400 mt-2">{selectedClass.comment}</p>
                  {selectedClass.subClassOf && (
                    <p className="text-sm text-slate-500 mt-1">
                      <span className="text-slate-600">rdfs:subClassOf</span>{' '}
                      <span className="text-emerald-400 font-mono">{selectedClass.subClassOf}</span>
                    </p>
                  )}
                  <p className="text-xs text-slate-600 mt-2 font-mono">
                    URI: dsdlc:{selectedClass.id}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
                    Properties
                  </h3>
                  <div className="space-y-2">
                    {selectedClass.properties.map((prop, i) => (
                      <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-slate-900/50">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${
                          prop.type === 'object' ? 'bg-blue-500/20 text-blue-300' : 'bg-slate-600/30 text-slate-400'
                        }`}>
                          {prop.type === 'object' ? 'obj' : 'data'}
                        </span>
                        <span className="font-mono text-sm text-white">{prop.name}</span>
                        <span className="text-slate-600 text-sm">&rarr;</span>
                        <span className={`font-mono text-sm ${
                          prop.type === 'object' ? 'text-emerald-400' : 'text-slate-500'
                        }`}>{prop.range}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Incoming relations */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
                    Incoming Relations
                  </h3>
                  {RELATIONS.filter(r => r.to === selectedClass.id).length === 0 ? (
                    <p className="text-sm text-slate-600 italic">None</p>
                  ) : (
                    <div className="space-y-1">
                      {RELATIONS.filter(r => r.to === selectedClass.id).map((r, i) => (
                        <div key={i} className="text-sm flex gap-2 items-center">
                          <span className="text-emerald-400 font-mono">{r.from}</span>
                          <span className="text-slate-600">&mdash;</span>
                          <span className="text-slate-400 font-mono text-xs">{r.label}</span>
                          <span className="text-slate-600">&rarr;</span>
                          <span className="text-white font-mono">{r.to}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </motion.div>
            ) : (
              <div className="bg-slate-800/30 border border-slate-700/30 rounded-2xl p-12 text-center">
                <p className="text-slate-500">Select a class to view its properties and relations.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {view === 'relations' && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="text-left p-4 text-slate-400 font-medium">Domain (from)</th>
                <th className="text-left p-4 text-slate-400 font-medium">Property</th>
                <th className="text-left p-4 text-slate-400 font-medium">Range (to)</th>
              </tr>
            </thead>
            <tbody>
              {filteredRelations.map((rel, i) => (
                <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-700/20">
                  <td className="p-4 font-mono text-emerald-400">{rel.from}</td>
                  <td className="p-4 font-mono text-slate-300">{rel.label}</td>
                  <td className="p-4 font-mono text-cyan-400">{rel.to}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {view === 'enumerations' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {ENUMERATIONS.map(en => (
            <div key={en.name} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
              <h3 className="font-mono text-white font-semibold mb-3">{en.name}</h3>
              <div className="flex flex-wrap gap-2">
                {en.values.map(v => (
                  <span key={v} className="px-2 py-1 bg-slate-900/50 border border-slate-700/50 rounded text-xs font-mono text-slate-300">
                    {v}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Format info */}
      <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Available Formats</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-slate-900/50 rounded-lg">
            <div className="font-mono text-white text-sm mb-1">data-sdlc.owl</div>
            <p className="text-xs text-slate-500">
              Full OWL 2 ontology with class restrictions, enumerations (owl:oneOf), inverse properties,
              and formal constraints for automated reasoning.
            </p>
          </div>
          <div className="p-4 bg-slate-900/50 rounded-lg">
            <div className="font-mono text-white text-sm mb-1">data-sdlc.rdfs</div>
            <p className="text-xs text-slate-500">
              Lightweight RDFS vocabulary with classes, properties, domain/range, and subclass hierarchy.
              Ideal for SPARQL queries and basic graph tooling.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
