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
  department_count: number;
  agent_count: number;
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
