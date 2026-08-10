export interface AgentDashboardState {
  system_state: string;
  agent_status: string;
  agent_phase: string;
  approval_required: boolean;
  incident_active: boolean;
  latest_log_tail: string[];
  remediation_report: string | null;
  change_record: any | null;
  events: any[];
}

export const fetchDashboard = async (): Promise<AgentDashboardState> => {
  const res = await fetch('/api/dashboard');
  if (!res.ok) throw new Error('Failed to fetch dashboard');
  return res.json();
};

export const approveChange = async (): Promise<void> => {
  const res = await fetch('/api/approval/approve', { method: 'POST' });
  if (!res.ok) throw new Error('Failed to approve change');
};

export const rejectChange = async (): Promise<void> => {
  const res = await fetch('/api/approval/reject', { method: 'POST' });
  if (!res.ok) throw new Error('Failed to reject change');
};

export const triggerRun = async (prompt: string): Promise<void> => {
  const res = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt })
  });
  if (!res.ok) throw new Error('Failed to trigger run');
};
