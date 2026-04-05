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
  slug: string;
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
  status: "provisioning" | "active" | "inactive" | "failed";
  instructions: string;
  config: Record<string, unknown>;
  auto_approve: boolean;
  pending_task_count: number;
  effective_config: Record<string, unknown>;
  config_source: Record<string, string>;
  tags: string[];
  created_at: string;
}

export interface DepartmentDetail {
  id: string;
  department_type: string;
  display_name: string;
  description: string;
  config: Record<string, unknown>;
  config_schema: Record<string, unknown>;
  agents: AgentSummary[];
  created_at: string;
}

export interface ProjectDetail {
  id: string;
  name: string;
  slug: string;
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
  status: "awaiting_approval" | "awaiting_dependencies" | "planned" | "queued" | "processing" | "done" | "failed";
  auto_execute: boolean;
  command_name: string;
  blocked_by: string | null;
  blocked_by_summary: string | null;
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
}

export interface AvailableAgent {
  agent_type: string;
  name: string;
  description: string;
  recommended: boolean;
  essential: boolean;
  controls: string | string[] | null;
}

export interface AvailableDepartment {
  department_type: string;
  name: string;
  description: string;
  recommended: boolean;
  config_schema: Record<string, unknown>;
  workforce: AvailableAgent[];
}

export interface AvailableDepartmentsResponse {
  departments: AvailableDepartment[];
}

export interface TaskPage {
  tasks: AgentTask[];
  totalCount: number;
}

export interface Output {
  id: string;
  project: string;
  department: string | null;
  title: string;
  label: string;
  output_type: "markdown" | "fountain" | "plaintext" | "pdf" | "html" | "other";
  content: string;
  original_filename: string;
  file_size: number;
  content_type: string;
  version: number;
  parent: string | null;
  word_count: number;
  created_by_task: string | null;
  created_by_task_summary: { id: string; exec_summary: string } | null;
  created_at: string;
  updated_at: string;
}

export interface BriefingAttachment {
  id: string;
  original_filename: string;
  file_format: string;
  file_size: number;
  word_count: number;
}

export interface Briefing {
  id: string;
  project: string;
  department: string | null;
  title: string;
  content: string;
  status: "active" | "archived";
  attachments: BriefingAttachment[];
  task_count: number;
  created_by_email: string;
  created_at: string;
  updated_at: string;
}
