export interface DeliveryType {
  id: string;
  name: string;
  description: string;
  business_purpose: string;
  baseline_risk: string;
  phases_count: number;
  tasks_count: number;
  default_agents: string[];
  required_skills: string[];
}

export interface Agent {
  id: string;
  name: string;
  version: string;
  description: string;
  engineering_role: string;
  capabilities: string[];
  supported_delivery_types: string[];
  skills: string[];
  tools: string[];
  risk_level: string;
  autonomy_level: string;
  trust_score: number;
  certification_status: string;
}

const API_BASE = './api';

export async function fetchDeliveryTypes(): Promise<DeliveryType[]> {
  try {
    const res = await fetch(`${API_BASE}/delivery-types`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Using offline fallback for delivery types", e);
  }
  return [
    {
      id: "DATA_PLATFORM_MIGRATION",
      name: "Data Platform / Warehouse Migration",
      description: "Migrate workloads, pipelines, and data assets from legacy data warehouse to modern cloud lakehouse.",
      business_purpose: "Enterprise platform modernization & cost reduction",
      baseline_risk: "HIGH",
      phases_count: 9,
      tasks_count: 18,
      default_agents: ["Migration Architect Agent", "Impact Analysis Agent", "Regression Test Agent", "Delivery Compliance Agent"],
      required_skills: ["source-discovery", "dependency-analysis", "schema-mapping", "data-reconciliation"]
    },
    {
      id: "DATA_PRODUCT_NEW",
      name: "New Data Product",
      description: "Create a brand new data product from discovery to operational deployment.",
      business_purpose: "Unlock new data capabilities and business value",
      baseline_risk: "MEDIUM",
      phases_count: 8,
      tasks_count: 16,
      default_agents: ["Requirements Agent", "Data Product Architect Agent", "Data Modeling Agent", "Data Quality Agent"],
      required_skills: ["requirement-extraction", "conceptual-modeling", "schema-design"]
    },
    {
      id: "DATA_PRODUCT_AMENDMENT",
      name: "Data Product Amendment",
      description: "Modify an existing data product attribute, transformation, calculation, or contract.",
      business_purpose: "Enhance existing data assets for evolving business needs",
      baseline_risk: "MEDIUM",
      phases_count: 5,
      tasks_count: 10,
      default_agents: ["Change Analysis Agent", "Impact Analysis Agent", "Regression Agent"],
      required_skills: ["impact-analysis", "schema-diff", "contract-validation"]
    }
  ];
}

export async function fetchAgents(): Promise<Agent[]> {
  try {
    const res = await fetch(`${API_BASE}/agents`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Using offline fallback for agents", e);
  }
  return [
    {
      id: "impact-analysis-agent",
      name: "Impact Analysis Agent",
      version: "2.4.0",
      description: "Calculates technical and delivery twin impact resulting from code, schema, or endpoint changes.",
      engineering_role: "Data Systems Architect",
      capabilities: ["Lineage Graph Traversal", "Technical Impact Scoring", "Delivery Task Mapping"],
      supported_delivery_types: ["DATA_PLATFORM_MIGRATION", "DATA_PRODUCT_AMENDMENT"],
      skills: ["dependency-analysis", "impact-analysis"],
      tools: ["lineage-scanner", "git-diff-analyzer"],
      risk_level: "MEDIUM",
      autonomy_level: "AUTOMATIC",
      trust_score: 0.95,
      certification_status: "CERTIFIED"
    },
    {
      id: "regression-test-agent",
      name: "Regression Test Agent",
      version: "1.8.0",
      description: "Selects, executes, and validates targeted regression test suites based on change impact.",
      engineering_role: "Data Quality Engineer",
      capabilities: ["Dynamic Test Selection", "Reconciliation Validation"],
      supported_delivery_types: ["DATA_PLATFORM_MIGRATION", "DATA_PRODUCT_AMENDMENT"],
      skills: ["test-selection", "regression-testing"],
      tools: ["pytest-runner", "reconciliation-engine"],
      risk_level: "LOW",
      autonomy_level: "AUTOMATIC",
      trust_score: 0.96,
      certification_status: "CERTIFIED"
    },
    {
      id: "delivery-compliance-agent",
      name: "Delivery Compliance Agent",
      version: "2.0.1",
      description: "Enforces delivery contracts, checklist completeness, evidence verification, and gate readiness.",
      engineering_role: "Delivery Manager",
      capabilities: ["Contract Compliance Audit", "Evidence Aggregation", "Gate Readiness Evaluation"],
      supported_delivery_types: ["DATA_PLATFORM_MIGRATION", "DATA_PRODUCT_NEW"],
      skills: ["checklist-validation", "gate-readiness", "evidence-validation"],
      tools: ["evidence-collector", "gate-evaluator"],
      risk_level: "HIGH",
      autonomy_level: "APPROVAL_REQUIRED",
      trust_score: 0.97,
      certification_status: "CERTIFIED"
    }
  ];
}

export async function classifyPrompt(prompt: string) {
  try {
    const res = await fetch(`${API_BASE}/classify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Using offline fallback for classification", e);
  }
  return {
    primary_delivery_type: "DATA_PLATFORM_MIGRATION",
    confidence: 0.96,
    evidence_reasoning: [
      "Existing legacy platform detected (Teradata DW)",
      "Target architecture identified (Cloud Lakehouse)",
      "Source-to-target workload redirection required",
      "Pipeline refactoring & schema mapping involved"
    ],
    secondary_delivery_types: ["DATA_PRODUCT_AMENDMENT"],
    available_types: ["DATA_PLATFORM_MIGRATION", "DATA_PRODUCT_NEW", "DATA_PRODUCT_AMENDMENT"]
  };
}

// --- AgentCore Harness Agent APIs ---

export interface WorkflowState {
  workflow_id: string;
  status: string;
  current_step: number;
  total_steps: number;
  steps: WorkflowStep[];
  evidence_count: number;
  created_at: string;
}

export interface WorkflowStep {
  id: string;
  name: string;
  agent_key: string;
  phase: string;
  status: string;
  depends_on: string[];
  started_at: string | null;
  completed_at: string | null;
  result_summary: Record<string, any> | null;
}

export interface Scenario {
  id: string;
  title: string;
  prompt: string;
  expected_classification: string;
  risk_level: string;
}

export async function fetchScenarios(): Promise<Scenario[]> {
  try {
    const res = await fetch(`${API_BASE}/scenarios`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Using offline fallback for scenarios", e);
  }
  return [
    { id: "ATLAS-CR-001", title: "Add PEP flag to customer accounts", prompt: "", expected_classification: "DATA_PRODUCT_AMENDMENT", risk_level: "HIGH" },
    { id: "ATLAS-CR-003", title: "Fix timestamp precision drift", prompt: "", expected_classification: "DATA_PRODUCT_AMENDMENT", risk_level: "HIGH" },
  ];
}

export async function fetchHarnessAgents(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE}/agents/harness`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Fallback for harness agents", e);
  }
  return [];
}

export async function fetchSkillMetadata(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE}/agents/skills`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Fallback for skills", e);
  }
  return [];
}

export async function initializeWorkflow(scenarioId: string): Promise<WorkflowState> {
  const res = await fetch(`${API_BASE}/workflow/initialize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  return await res.json();
}

async function pollUntilDone(taskId: string, onProgress?: (state: WorkflowState) => void): Promise<WorkflowState> {
  while (true) {
    await new Promise(r => setTimeout(r, 2000));
    const res = await fetch(`${API_BASE}/workflow/poll/${taskId}`);
    const data = await res.json();
    if (data.status === 'RUNNING') {
      if (onProgress && data.workflow) onProgress(data.workflow);
      continue;
    }
    return data.result;
  }
}

export async function workflowNextStep(onProgress?: (state: WorkflowState) => void): Promise<WorkflowState> {
  const res = await fetch(`${API_BASE}/workflow/next`, { method: 'POST' });
  const { task_id, error } = await res.json();
  if (error) throw new Error(error);
  return pollUntilDone(task_id, onProgress);
}

export async function workflowRunAll(onProgress?: (state: WorkflowState) => void): Promise<WorkflowState> {
  const res = await fetch(`${API_BASE}/workflow/run-all`, { method: 'POST' });
  const { task_id, error } = await res.json();
  if (error) throw new Error(error);
  return pollUntilDone(task_id, onProgress);
}

export async function getWorkflowState(): Promise<WorkflowState> {
  const res = await fetch(`${API_BASE}/workflow/state`);
  return await res.json();
}

export async function getWorkflowStepResult(stepIndex: number): Promise<any> {
  const res = await fetch(`${API_BASE}/workflow/step/${stepIndex}`);
  return await res.json();
}

export async function runAgent(agentKey: string, taskInput: Record<string, any>): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_key: agentKey, task_input: taskInput }),
  });
  return await res.json();
}

export async function buildContext(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/context`, { method: 'POST' });
  return await res.json();
}

export async function fetchAgentTraces(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/traces`);
  return await res.json();
}

// --- SDLC Demo Orchestrator APIs ---

export interface SDLCDocument {
  id: string;
  title: string;
  status: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface SDLCEvent {
  event: string;
  condition: string;
  target: string;
  description: string;
}

export interface SDLCStatus {
  orchestrator_id: string;
  current_state: string;
  state_description: string;
  is_terminal: boolean;
  documents: Record<string, SDLCDocument>;
  artifacts: Record<string, any>;
  history: Array<{
    timestamp: string;
    from_state: string;
    event: string;
    to_state: string;
    action: string;
    payload?: Record<string, any>;
    agent_key?: string;
    agent_result_summary?: Record<string, any>;
  }>;
  available_events: SDLCEvent[];
  created_at: string;
  agent_result?: any;
  error?: string;
}

export async function sdlcDemoInitialize(): Promise<SDLCStatus> {
  const res = await fetch(`${API_BASE}/sdlc-demo/initialize`, { method: 'POST' });
  return await res.json();
}

export async function sdlcDemoStatus(): Promise<SDLCStatus> {
  try {
    const res = await fetch(`${API_BASE}/sdlc-demo/status`);
    return await res.json();
  } catch {
    return {
      orchestrator_id: '', current_state: 'INIT', state_description: '',
      is_terminal: false, documents: {}, artifacts: {}, history: [],
      available_events: [], created_at: '', error: 'Not initialized',
    };
  }
}

export async function sdlcDemoApprove(
  documentId: string,
  onProgress?: (status: SDLCStatus) => void,
): Promise<SDLCStatus> {
  const res = await fetch(`${API_BASE}/sdlc-demo/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId }),
  });
  const { task_id, error } = await res.json();
  if (error) throw new Error(error);
  // Poll for completion
  while (true) {
    await new Promise(r => setTimeout(r, 1500));
    const pollRes = await fetch(`${API_BASE}/workflow/poll/${task_id}`);
    const data = await pollRes.json();
    if (data.status === 'RUNNING') {
      if (onProgress) {
        const status = await sdlcDemoStatus();
        onProgress(status);
      }
      continue;
    }
    // Task done — fetch fresh status
    return await sdlcDemoStatus();
  }
}

export async function sdlcDemoDocument(docId: string): Promise<SDLCDocument> {
  const res = await fetch(`${API_BASE}/sdlc-demo/document/${docId}`);
  return await res.json();
}

export async function sdlcDemoArtifact(artifactKey: string): Promise<any> {
  const res = await fetch(`${API_BASE}/sdlc-demo/artifact/${artifactKey}`);
  return await res.json();
}

export async function sdlcDemoReset(): Promise<void> {
  await fetch(`${API_BASE}/sdlc-demo/reset`, { method: 'POST' });
}

// --- AgentCore Connection Tester APIs ---

export interface ConnectionSettings {
  credentials_path: string;
  profile: string;
  region: string;
  project: string;
}

export interface ConnectionTestResult {
  settings: ConnectionSettings;
  aws_identity: { available: boolean; account?: string; arn?: string; user_id?: string; reason?: string } | null;
  agentcore: { available: boolean; harness_count?: number; region?: string; reason?: string } | null;
  error?: string;
}

export async function fetchConnectionSettings(): Promise<ConnectionSettings> {
  const res = await fetch(`${API_BASE}/connection-tester/settings`);
  return await res.json();
}

export async function saveConnectionSettings(settings: ConnectionSettings): Promise<ConnectionSettings> {
  const res = await fetch(`${API_BASE}/connection-tester/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  return await res.json();
}

export async function runConnectionTest(settings?: ConnectionSettings): Promise<ConnectionTestResult> {
  const res = await fetch(`${API_BASE}/connection-tester/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings || {}),
  });
  return await res.json();
}

// --- Project Dashboard APIs ---

export interface ChecklistItem {
  id: string;
  text: string;
  completed: boolean;
  verified_by?: string;
}

export interface DashboardWorkProduct {
  key: string;
  name: string;
  phase: string;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'AWAITING_REVIEW' | 'COMPLETED';
  version: string;
  review_gate: boolean;
  updated_at: string | null;
  requested_at: string | null;
  checklist?: ChecklistItem[];
  owner?: { agent_id?: string | null; human_role?: string | null } | null;
}

export interface Comment {
  id: string;
  task_id: string;
  author: string;
  author_type: 'agent' | 'human' | 'system';
  body: string;
  timestamp: string;
  thread_id?: string;
}

export interface DashboardLane {
  key: string;
  name: string;
  role: string;
  color: string;
  status: 'IDLE' | 'RUNNING' | 'WAITING_FOR_APPROVAL' | 'COMPLETED' | 'FAILED';
  current_activity: string;
  work_products: DashboardWorkProduct[];
  counts: { done: number; total: number };
  elapsed_seconds: number;
  token_cost_usd: number;
  total_tokens: number;
  backend: string;
  events: any[];
}

export interface DashboardPhase {
  key: string;
  label: string;
  done: number;
  total: number;
}

export interface DashboardHumanAttentionItem {
  lane_key: string;
  lane_name: string;
  work_product_key: string;
  work_product_name: string;
  requested_at: string | null;
  version: string;
}

export interface DashboardSnapshot {
  session_id: string;
  title: string;
  live: boolean;
  started_at: string;
  elapsed_seconds: number;
  token_cost_usd: number;
  total_tokens: number;
  work_products_done: number;
  work_products_total: number;
  agents_active: number;
  agents_total: number;
  phases: DashboardPhase[];
  lanes: DashboardLane[];
  recent_activity: any[];
  human_attention_required: DashboardHumanAttentionItem[];
}

export async function startDashboard(
  live: boolean, title?: string, projectId?: string,
): Promise<{ session_id: string; live: boolean }> {
  const res = await fetch(`${API_BASE}/dashboard/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ live, title, project_id: projectId }),
  });
  return await res.json();
}

// --- Project APIs (per-project datastore seeded at onboarding) ---

export interface ProjectRecord {
  project_id: string;
  title: string;
  delivery_type_id: string | null;
  created_at: string;
  phases: DashboardPhase[];
  lanes: any[];
}

export async function createProject(title: string, deliveryTypeId?: string): Promise<ProjectRecord> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, delivery_type_id: deliveryTypeId }),
  });
  return await res.json();
}

export async function fetchDashboardSnapshot(sessionId: string): Promise<DashboardSnapshot> {
  const res = await fetch(`${API_BASE}/dashboard/${sessionId}/snapshot`);
  return await res.json();
}

export async function reviewWorkProduct(
  sessionId: string, laneKey: string, workProductKey: string, approve: boolean, version: string = '',
): Promise<any> {
  const res = await fetch(`${API_BASE}/dashboard/${sessionId}/work-products/${laneKey}/${workProductKey}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approve, version }),
  });
  return await res.json();
}

// --- Live Agent Orchestrator APIs ---

export interface LiveAgent {
  id: string;
  name: string;
  description: string;
  backend: 'AGENTCORE' | 'GITHUB_COPILOT';
  live_ready: boolean;
  harness_status: string;
}

export interface LiveEvent {
  id: string;
  event_type: string;
  source_agent_id: string;
  session_id: string;
  payload: Record<string, any>;
  timestamp: string;
}

export interface PendingClientToolCall {
  call_id: string;
  session_id: string;
  turn: number;
  tool_name: string;
  arguments: Record<string, any>;
  status: string;
  requested_at: string;
}

export interface LiveSessionPoll {
  status: string;
  events: LiveEvent[];
  next_cursor: number;
  pending_calls: PendingClientToolCall[];
  final_text: string | null;
}

export interface AwsIdentity {
  available: boolean;
  account?: string;
  arn?: string;
  user_id?: string;
  region?: string;
  reason?: string;
}

export interface AgentCoreMetrics {
  available: boolean;
  reason?: string;
  namespace?: string;
  agent_runtime_id?: string;
  lookback_minutes?: number;
  series?: Array<{ metric: string; timestamps: string[]; values: number[]; total: number }>;
}

export interface ClientTool {
  name: string;
  description: string;
}

export async function fetchClientTools(): Promise<ClientTool[]> {
  try {
    const res = await fetch(`${API_BASE}/live/tools/client`);
    if (res.ok) return (await res.json()).tools;
  } catch (e) {
    console.warn("Using offline fallback for client tools", e);
  }
  return [];
}

export async function fetchLiveAgents(): Promise<LiveAgent[]> {
  try {
    const res = await fetch(`${API_BASE}/live/agents`);
    if (res.ok) return (await res.json()).agents;
  } catch (e) {
    console.warn("Using offline fallback for live agents", e);
  }
  return [];
}

export async function fetchAwsIdentity(): Promise<AwsIdentity> {
  try {
    const res = await fetch(`${API_BASE}/live/aws/identity`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Failed to fetch AWS identity", e);
  }
  return { available: false, reason: 'not reachable' };
}

export async function fetchLiveMetrics(agentId: string): Promise<AgentCoreMetrics> {
  try {
    const res = await fetch(`${API_BASE}/live/metrics?agent_id=${encodeURIComponent(agentId)}`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Failed to fetch live metrics", e);
  }
  return { available: false, reason: 'not reachable' };
}

export async function startLiveSession(
  agentId: string, backend: 'AGENTCORE' | 'GITHUB_COPILOT', live: boolean, prompt: string,
): Promise<{ session_id: string }> {
  const res = await fetch(`${API_BASE}/live/session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: agentId, backend, live, prompt }),
  });
  return await res.json();
}

export async function pollLiveSession(sessionId: string, since: number): Promise<LiveSessionPoll> {
  const res = await fetch(`${API_BASE}/live/session/${sessionId}/poll?since=${since}`);
  return await res.json();
}

export async function approveClientToolCall(sessionId: string, callId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/live/session/${sessionId}/tool-calls/${callId}/approve`, { method: 'POST' });
  return await res.json();
}

export async function denyClientToolCall(sessionId: string, callId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/live/session/${sessionId}/tool-calls/${callId}/deny`, { method: 'POST' });
  return await res.json();
}

export async function fetchImpactAnalysis(changeId: string = "CR-2026-8942") {
  try {
    const res = await fetch(`${API_BASE}/impact/${changeId}`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Using offline fallback for impact analysis", e);
  }
  return {
    technical_impact: {
      change_id: changeId,
      root_changed_files: [
        "terraform/lakehouse_ingestion.tf",
        "pipelines/salesforce_customer_ingest.py",
        "models/staging/schema.yml"
      ],
      redirected_assets: [
        { name: "dw_staging.customer_events", new_target: "lakehouse_raw.customer_events", type: "BigLake / Parquet Storage" }
      ],
      impacted_downstream_models: [
        { id: "M-01", name: "stg_lakehouse_customers.sql", type: "dbt model", status: "IMPACTED" },
        { id: "M-02", name: "customer_profile.sql", type: "dbt model", status: "IMPACTED" },
        { id: "M-03", name: "customer_360.sql", type: "dbt model", status: "IMPACTED" },
        { id: "M-04", name: "customer_quality_report.sql", type: "dbt model", status: "IMPACTED" }
      ],
      affected_pipelines_count: 14,
      affected_assets_count: 25,
      status_classification: { Changed: 3, Redirected: 2, Impacted: 14, Tested: 10, Safe: 45, Risk: 1 }
    },
    delivery_impact: {
      affected_delivery_tasks: [
        { phase: "Architecture", task: "Feasibility Assessment & Risk Analysis", status: "COMPLETED" },
        { phase: "Design", task: "Target Data & Schema Design", status: "COMPLETED" },
        { phase: "Design", task: "Pipeline Technical Spec & Infrastructure Plan", status: "COMPLETED" },
        { phase: "Development", task: "Source Feed Endpoint Modification", status: "COMPLETED" },
        { phase: "Testing", task: "Source-to-Target Data Reconciliation", status: "FAILED" },
        { phase: "Operations", task: "Lakehouse Operational Runbook Update", status: "MISSING" }
      ],
      affected_gates: [
        { name: "Architectural Feasibility Gate", status: "PASSED" },
        { name: "Security & Governance Gate", status: "PASSED" },
        { name: "Release Readiness Gate", status: "BLOCKED" }
      ]
    }
  };
}

// --- Kanban Board APIs ---

export async function fetchBoardSnapshot(sessionId: string): Promise<DashboardSnapshot> {
  try {
    const res = await fetch(`${API_BASE}/board/${sessionId}/snapshot`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn("Using offline fallback for board snapshot", e);
  }
  return {
    session_id: sessionId,
    title: "Customer Payments Data Product",
    live: false,
    started_at: new Date().toISOString(),
    elapsed_seconds: 0,
    token_cost_usd: 0,
    total_tokens: 0,
    work_products_done: 0,
    work_products_total: 0,
    agents_active: 0,
    agents_total: 4,
    phases: [],
    lanes: [],
    recent_activity: [],
    human_attention_required: [],
  };
}

export async function updateTaskStatus(
  sessionId: string,
  taskKey: string,
  newStatus: string,
): Promise<any> {
  const res = await fetch(`${API_BASE}/board/${sessionId}/tasks/${taskKey}/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_status: newStatus }),
  });
  if (!res.ok) throw new Error(`Failed to update task status: ${res.statusText}`);
  return await res.json();
}

export async function fetchTaskComments(sessionId: string, taskKey: string): Promise<Comment[]> {
  try {
    const res = await fetch(`${API_BASE}/board/${sessionId}/tasks/${taskKey}/comments`);
    if (res.ok) {
      const data = await res.json();
      return data.comments || [];
    }
  } catch (e) {
    console.warn("Failed to fetch task comments", e);
  }
  return [];
}

export async function postTaskComment(
  sessionId: string,
  taskKey: string,
  author: string,
  authorType: 'agent' | 'human' | 'system',
  body: string,
): Promise<Comment> {
  const res = await fetch(`${API_BASE}/board/${sessionId}/tasks/${taskKey}/comments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ author, author_type: authorType, body }),
  });
  if (!res.ok) throw new Error(`Failed to post comment: ${res.statusText}`);
  const data = await res.json();
  return data.comment;
}

export async function updateChecklistItem(
  sessionId: string,
  taskKey: string,
  itemId: string,
  completed: boolean,
): Promise<any> {
  const res = await fetch(`${API_BASE}/board/${sessionId}/tasks/${taskKey}/checklist/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ completed }),
  });
  if (!res.ok) throw new Error(`Failed to update checklist item: ${res.statusText}`);
  return await res.json();
}
