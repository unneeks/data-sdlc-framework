import React, { useCallback, useState } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  ConnectionLineType
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Cpu, Wrench, Database, FileText, Sparkles, Server } from 'lucide-react';
import { motion } from 'framer-motion';

// --- Custom Node Components ---

const AgentNode = ({ data }: any) => (
  <div className="px-4 py-3 shadow-lg shadow-indigo-500/20 rounded-xl bg-slate-900 border-2 border-indigo-500 min-w-[200px]">
    <Handle type="target" position={Position.Left} className="w-3 h-3 bg-indigo-500" />
    <div className="flex items-center space-x-3">
      <div className="w-8 h-8 rounded-lg bg-indigo-500/20 flex items-center justify-center text-indigo-400">
        <Cpu className="w-4 h-4" />
      </div>
      <div>
        <div className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Agent</div>
        <div className="text-sm font-bold text-white">{data.label}</div>
      </div>
    </div>
    <Handle type="source" position={Position.Right} className="w-3 h-3 bg-indigo-500" />
  </div>
);

const SkillNode = ({ data }: any) => (
  <div className="px-4 py-3 shadow-lg shadow-emerald-500/10 rounded-xl bg-slate-900 border border-emerald-500/50 min-w-[180px]">
    <Handle type="target" position={Position.Left} className="w-2 h-2 bg-emerald-500" />
    <div className="flex items-center space-x-3">
      <div className="w-6 h-6 rounded-md bg-emerald-500/10 flex items-center justify-center text-emerald-400">
        <Sparkles className="w-3 h-3" />
      </div>
      <div>
        <div className="text-[9px] font-bold text-emerald-400 uppercase tracking-widest">Skill</div>
        <div className="text-xs font-bold text-slate-200">{data.label}</div>
      </div>
    </div>
    <Handle type="source" position={Position.Right} className="w-2 h-2 bg-emerald-500" />
  </div>
);

const ToolNode = ({ data }: any) => (
  <div className="px-4 py-3 shadow-lg shadow-amber-500/10 rounded-xl bg-slate-900 border border-amber-500/50 min-w-[150px]">
    <Handle type="target" position={Position.Left} className="w-2 h-2 bg-amber-500" />
    <div className="flex items-center space-x-3">
      <div className="w-6 h-6 rounded-md bg-amber-500/10 flex items-center justify-center text-amber-400">
        <Wrench className="w-3 h-3" />
      </div>
      <div>
        <div className="text-[9px] font-bold text-amber-400 uppercase tracking-widest">Tool</div>
        <div className="text-xs font-bold text-slate-200">{data.label}</div>
      </div>
    </div>
    <Handle type="source" position={Position.Right} className="w-2 h-2 bg-amber-500" />
  </div>
);

const AssetNode = ({ data }: any) => (
  <div className="px-4 py-3 shadow-lg shadow-cyan-500/20 rounded-xl bg-slate-800 border-2 border-cyan-500 min-w-[200px]">
    <Handle type="target" position={Position.Left} className="w-3 h-3 bg-cyan-500" />
    <div className="flex items-center space-x-3">
      <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400">
        <Database className="w-4 h-4" />
      </div>
      <div>
        <div className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest">{data.type || 'Tech Asset'}</div>
        <div className="text-sm font-bold text-white">{data.label}</div>
      </div>
    </div>
    <Handle type="source" position={Position.Right} className="w-3 h-3 bg-cyan-500" />
  </div>
);

const DocNode = ({ data }: any) => (
  <div className="px-4 py-3 shadow-lg shadow-rose-500/10 rounded-xl bg-slate-900 border border-rose-500/50 min-w-[180px]">
    <Handle type="target" position={Position.Left} className="w-2 h-2 bg-rose-500" />
    <div className="flex items-center space-x-3">
      <div className="w-6 h-6 rounded-md bg-rose-500/10 flex items-center justify-center text-rose-400">
        <FileText className="w-3 h-3" />
      </div>
      <div>
        <div className="text-[9px] font-bold text-rose-400 uppercase tracking-widest">Documentation</div>
        <div className="text-xs font-bold text-slate-200">{data.label}</div>
      </div>
    </div>
    <Handle type="source" position={Position.Right} className="w-2 h-2 bg-rose-500" />
  </div>
);

const nodeTypes = {
  agent: AgentNode,
  skill: SkillNode,
  tool: ToolNode,
  asset: AssetNode,
  doc: DocNode,
};

// --- Initial Graph Data ---

const initialNodes = [
  // Assets (Left)
  { id: 'sap', type: 'asset', position: { x: 50, y: 150 }, data: { label: 'SAP CRM', type: 'Source System' } },
  { id: 'salesforce', type: 'asset', position: { x: 50, y: 300 }, data: { label: 'Salesforce', type: 'Source System' } },
  
  // Agents (Center)
  { id: 'migration-architect', type: 'agent', position: { x: 400, y: 100 }, data: { label: 'Migration Architect' } },
  { id: 'data-modeler', type: 'agent', position: { x: 400, y: 220 }, data: { label: 'Data Modeling Agent' } },
  { id: 'pipeline-agent', type: 'agent', position: { x: 400, y: 340 }, data: { label: 'Pipeline Agent' } },
  
  // Skills & Tools (Top/Bottom)
  { id: 'schema-parsing', type: 'skill', position: { x: 750, y: 50 }, data: { label: 'Schema Extraction' } },
  { id: 'dbt-codegen', type: 'skill', position: { x: 750, y: 150 }, data: { label: 'dbt Code Generation' } },
  { id: 'git-client', type: 'tool', position: { x: 750, y: 250 }, data: { label: 'GitHub API' } },
  { id: 'dbt-cli', type: 'tool', position: { x: 750, y: 350 }, data: { label: 'dbt CLI' } },
  
  // Target Assets (Right)
  { id: 'lakehouse', type: 'asset', position: { x: 1050, y: 220 }, data: { label: 'Iceberg Lakehouse', type: 'Target System' } },
  
  // Docs
  { id: 'runbook', type: 'doc', position: { x: 1050, y: 350 }, data: { label: 'Lakehouse Runbook' } },
];

const initialEdges = [
  // Sources to Agents
  { id: 'e1', source: 'sap', target: 'migration-architect', animated: true, style: { stroke: '#94a3b8' } },
  { id: 'e2', source: 'salesforce', target: 'migration-architect', animated: true, style: { stroke: '#94a3b8' } },
  { id: 'e3', source: 'sap', target: 'data-modeler', animated: true, style: { stroke: '#94a3b8' } },
  
  // Agents collaborating
  { id: 'e4', source: 'migration-architect', target: 'data-modeler', style: { stroke: '#818cf8', strokeWidth: 2 } },
  { id: 'e5', source: 'data-modeler', target: 'pipeline-agent', style: { stroke: '#818cf8', strokeWidth: 2 } },
  
  // Agents using skills
  { id: 'e6', source: 'migration-architect', target: 'schema-parsing', style: { stroke: '#34d399', strokeDasharray: '5 5' } },
  { id: 'e7', source: 'pipeline-agent', target: 'dbt-codegen', style: { stroke: '#34d399', strokeDasharray: '5 5' } },
  
  // Agents using tools
  { id: 'e8', source: 'pipeline-agent', target: 'git-client', style: { stroke: '#fbbf24', strokeDasharray: '5 5' } },
  { id: 'e9', source: 'pipeline-agent', target: 'dbt-cli', style: { stroke: '#fbbf24', strokeDasharray: '5 5' } },
  
  // Agents interacting with target
  { id: 'e10', source: 'pipeline-agent', target: 'lakehouse', animated: true, style: { stroke: '#22d3ee', strokeWidth: 2 } },
  
  // Documentation outputs
  { id: 'e11', source: 'migration-architect', target: 'runbook', style: { stroke: '#fb7185' } },
];

export const ProjectGraphExplorer: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback((params: any) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  return (
    <div className="space-y-6 h-full flex flex-col pb-12">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 text-indigo-400 text-xs font-bold uppercase tracking-widest px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/20">
            <Server className="w-4 h-4" />
            <span>CR-2026-8942</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Project Ecosystem Graph</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Interactive map of all Agents, Skills, Tools, Tech Assets, and Documentation associated with this delivery mandate.
          </p>
        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex-1 min-h-[600px] glass-panel rounded-3xl overflow-hidden relative border border-slate-700 shadow-2xl shadow-indigo-900/20"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          connectionLineType={ConnectionLineType.SmoothStep}
          fitView
          className="bg-transparent"
        >
          <Background color="#334155" gap={24} size={2} />
          <Controls className="bg-slate-900 border-slate-700 fill-white" />
          <MiniMap 
            nodeColor={(n: any) => {
              if (n.type === 'agent') return '#6366f1';
              if (n.type === 'skill') return '#10b981';
              if (n.type === 'tool') return '#f59e0b';
              if (n.type === 'asset') return '#06b6d4';
              if (n.type === 'doc') return '#f43f5e';
              return '#475569';
            }}
            maskColor="rgba(15, 23, 42, 0.7)"
            className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden"
          />
        </ReactFlow>

        {/* Legend */}
        <div className="absolute bottom-6 left-6 p-4 bg-slate-900/80 backdrop-blur-xl border border-slate-700 rounded-2xl flex flex-col space-y-3 shadow-xl">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Graph Legend</div>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-300">
              <div className="w-3 h-3 rounded bg-indigo-500" /> <span>Agents</span>
            </div>
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-300">
              <div className="w-3 h-3 rounded bg-cyan-500" /> <span>Tech Assets</span>
            </div>
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-300">
              <div className="w-3 h-3 rounded bg-emerald-500" /> <span>Skills</span>
            </div>
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-300">
              <div className="w-3 h-3 rounded bg-rose-500" /> <span>Docs</span>
            </div>
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-300">
              <div className="w-3 h-3 rounded bg-amber-500" /> <span>Tools</span>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
