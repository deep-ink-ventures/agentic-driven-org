export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
}

export interface Project {
  id: string;
  name: string;
  goal: string;
  status: "setup" | "active";
  department_count: number;
  agent_count: number;
  source_count: number;
  bootstrap_status: string | null;
  sources: Source[];
  created_at: string;
  updated_at: string;
}

export interface Source {
  id: string;
  source_type: "file" | "url" | "text";
  original_filename: string;
  url: string;
  raw_content: string;
  extracted_text: string;
  word_count: number | null;
  created_at: string;
}

export interface BootstrapProposal {
  id: string;
  status: "pending" | "processing" | "proposed" | "approved" | "failed";
  proposal: BootstrapProposalData | null;
  error_message: string;
  token_usage: { model: string; input_tokens: number; output_tokens: number; cost_usd: number } | null;
  created_at: string;
  updated_at: string;
}

export interface BootstrapProposalData {
  summary: string;
  departments: {
    department_type: string;
    documents: { title: string; content: string; tags: string[] }[];
    agents: { name: string; agent_type: string; instructions: string }[];
  }[];
  ignored_content: { source_id: string; source_name: string; reason: string }[];
}

export interface AgentSummary {
  id: string;
  name: string;
  agent_type: string;
  is_leader: boolean;
  is_active: boolean;
  instructions: string;
  config: Record<string, unknown>;
  auto_actions: Record<string, boolean>;
  pending_task_count: number;
  created_at: string;
}

export interface DepartmentDetail {
  id: string;
  department_type: string;
  display_name: string;
  description: string;
  agents: AgentSummary[];
  created_at: string;
}

export interface ProjectDetail {
  id: string;
  name: string;
  goal: string;
  status: "setup" | "active";
  owner_email: string;
  departments: DepartmentDetail[];
  created_at: string;
  updated_at: string;
}

export interface AgentTask {
  id: string;
  agent: string;
  agent_name: string;
  agent_type: string;
  created_by_agent: string | null;
  created_by_agent_name: string | null;
  status: "awaiting_approval" | "planned" | "queued" | "processing" | "done" | "failed";
  auto_execute: boolean;
  exec_summary: string;
  step_plan: string;
  report: string;
  error_message: string;
  proposed_exec_at: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  token_usage: { model: string; input_tokens: number; output_tokens: number; cost_usd: number } | null;
  created_at: string;
  updated_at: string;
}

export interface BlueprintInfo {
  name: string;
  slug: string;
  description: string;
  tags: string[];
  default_model: string;
  skills_description: string;
  commands: { name: string; description: string; schedule: string | null; model: string | null }[];
  config_schema: Record<string, unknown>;
  auto_actions_schema: Record<string, unknown>;
}
