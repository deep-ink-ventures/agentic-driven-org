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
