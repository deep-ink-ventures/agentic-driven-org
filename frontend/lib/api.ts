const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : null;
}

async function requestWithHeaders<T>(path: string, options: RequestInit = {}): Promise<{ data: T; headers: Headers }> {
  const url = `${API_URL}${path}`;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const method = (options.method || "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }
  }

  const doFetch = () =>
    fetch(url, { ...options, credentials: "include", headers });

  let res: Response;
  try {
    res = await doFetch();
  } catch {
    await new Promise((r) => setTimeout(r, 2000));
    res = await doFetch();
  }

  if (res.status === 503) {
    await new Promise((r) => setTimeout(r, 2000));
    res = await doFetch();
  }

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return { data: undefined as T, headers: res.headers };
  return { data: await res.json(), headers: res.headers };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { data } = await requestWithHeaders<T>(path, options);
  return data;
}

export const api = {
  getSession: () =>
    request<{ user: import("./types").User | null }>("/api/auth/session/"),

  login: (email: string, password: string) =>
    request<{ user: import("./types").User }>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  signup: (email: string, password: string, termsAccepted: boolean) =>
    request<{ user: import("./types").User }>("/api/auth/signup/", {
      method: "POST",
      body: JSON.stringify({ email, password, terms_accepted: termsAccepted }),
    }),

  logout: () =>
    request<void>("/api/auth/logout/", { method: "POST" }),

  listProjects: () =>
    request<import("./types").Project[]>("/api/projects/"),

  createProject: (data: { name: string; goal?: string }) =>
    request<import("./types").Project>("/api/projects/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  addSource: (projectId: string, data: { source_type: string; raw_content?: string; url?: string }) =>
    request<import("./types").Source>(`/api/projects/${projectId}/sources/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  uploadFile: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_type", "file");
    return request<import("./types").Source>(`/api/projects/${projectId}/sources/`, {
      method: "POST",
      body: formData,
    });
  },

  getWsTicket: () =>
    request<{ ticket: string }>("/api/auth/ws-ticket/", { method: "POST" }),

  triggerBootstrap: (projectId: string) =>
    request<import("./types").BootstrapProposal>(`/api/projects/${projectId}/bootstrap/`, {
      method: "POST",
    }),

  getBootstrapLatest: (projectId: string) =>
    request<import("./types").BootstrapProposal>(`/api/projects/${projectId}/bootstrap/latest/`),

  approveBootstrap: (projectId: string, proposalId: string, proposal?: import("./types").BootstrapProposalData) =>
    request<import("./types").BootstrapProposal>(`/api/projects/${projectId}/bootstrap/${proposalId}/approve/`, {
      method: "POST",
      body: JSON.stringify(proposal ? { proposal } : {}),
    }),

  getProjectDetail: (slug: string) =>
    request<import("./types").ProjectDetail>(`/api/projects/${slug}/detail/`),

  getProjectTasks: async (
    projectId: string,
    params?: {
      status?: string;
      department?: string;
      agent?: string;
      limit?: number;
      before?: string;
    },
  ): Promise<import("./types").TaskPage> => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set("status", params.status);
    if (params?.department) sp.set("department", params.department);
    if (params?.agent) sp.set("agent", params.agent);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.before) sp.set("before", params.before);
    const qs = sp.toString();
    const { data, headers } = await requestWithHeaders<import("./types").AgentTask[]>(
      `/api/projects/${projectId}/tasks/${qs ? `?${qs}` : ""}`,
    );
    return {
      tasks: data,
      totalCount: parseInt(headers.get("X-Total-Count") || "0", 10),
    };
  },

  approveTask: (projectId: string, taskId: string, edits?: { step_plan?: string; exec_summary?: string }) =>
    request<import("./types").AgentTask>(`/api/projects/${projectId}/tasks/${taskId}/approve/`, {
      method: "POST",
      body: JSON.stringify(edits ?? {}),
    }),

  rejectTask: (projectId: string, taskId: string) =>
    request<import("./types").AgentTask>(`/api/projects/${projectId}/tasks/${taskId}/reject/`, { method: "POST" }),

  retryTask: (projectId: string, taskId: string) =>
    request<import("./types").AgentTask>(`/api/projects/${projectId}/tasks/${taskId}/retry/`, { method: "POST" }),

  updateAgent: (
    agentId: string,
    data: {
      instructions?: string;
      config?: Record<string, unknown>;
      auto_approve?: boolean;
      status?: string;
    },
  ) => request<unknown>(`/api/agents/${agentId}/`, { method: "PATCH", body: JSON.stringify(data) }),

  getAgentBlueprint: (agentId: string) =>
    request<import("./types").BlueprintInfo>(`/api/agents/${agentId}/blueprint/`),

  getAvailableDepartments: (projectId: string) =>
    request<import("./types").AvailableDepartmentsResponse>(
      `/api/projects/${projectId}/departments/available/`,
    ),

  addDepartments: (
    projectId: string,
    data: {
      departments: { department_type: string; agents: string[] }[];
      context?: string;
    },
  ) =>
    request<{ departments: { id: string; department_type: string }[]; status: string }>(
      `/api/projects/${projectId}/departments/add/`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),

  addAgent: (data: { department_id: string; agent_type: string }) =>
    request<{ id: string; name: string; agent_type: string; status: string }>(
      "/api/agents/add/",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),

  getAvailableAgents: (projectId: string, deptId: string) =>
    request<{ agents: import("./types").AvailableAgent[] }>(
      `/api/projects/${projectId}/departments/${deptId}/available-agents/`,
    ),

  updateDepartmentConfig: (deptId: string, config: Record<string, unknown>) =>
    request<{ config: Record<string, unknown> }>(
      `/api/departments/${deptId}/config/`,
      { method: "PATCH", body: JSON.stringify(config) },
    ),

  getProjectConfig: (slug: string) =>
    request<{ config: Record<string, unknown>; schema: Record<string, unknown> }>(
      `/api/projects/${slug}/config/`,
    ),

  updateProjectConfig: (slug: string, config: Record<string, unknown>) =>
    request<{ config: Record<string, unknown>; schema: Record<string, unknown> }>(
      `/api/projects/${slug}/config/`,
      {
        method: "PATCH",
        body: JSON.stringify({ config }),
      },
    ),

  generateExtensionToken: (slug: string) =>
    request<{ token: string; project: string }>(`/api/projects/${slug}/extension-token/`, {
      method: "POST",
    }),

  listOutputs: (
    projectId: string,
    params?: { department?: string; label?: string; output_type?: string },
  ) => {
    const sp = new URLSearchParams();
    if (params?.department) sp.set("department", params.department);
    if (params?.label) sp.set("label", params.label);
    if (params?.output_type) sp.set("output_type", params.output_type);
    const qs = sp.toString();
    return request<import("./types").Output[]>(
      `/api/projects/${projectId}/outputs/${qs ? `?${qs}` : ""}`,
    );
  },

  getOutput: (projectId: string, outputId: string) =>
    request<import("./types").Output>(`/api/projects/${projectId}/outputs/${outputId}/`),

  listSprints: (projectId: string, params?: { status?: string; department?: string }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set("status", params.status);
    if (params?.department) sp.set("department", params.department);
    const qs = sp.toString();
    return request<import("./types").Sprint[]>(
      `/api/projects/${projectId}/sprints/${qs ? `?${qs}` : ""}`,
    );
  },

  createSprint: (projectId: string, data: { text: string; department_ids: string[]; source_ids?: string[] }) =>
    request<import("./types").Sprint>(`/api/projects/${projectId}/sprints/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateSprint: (projectId: string, sprintId: string, data: { status?: string; completion_summary?: string }) =>
    request<import("./types").Sprint>(`/api/projects/${projectId}/sprints/${sprintId}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  suggestSprints: (projectId: string, departmentIds: string[]) =>
    request<{ suggestions: string[] }>(`/api/projects/${projectId}/sprints/suggest/`, {
      method: "POST",
      body: JSON.stringify({ department_ids: departmentIds }),
    }),

  uploadSource: (projectId: string, formData: FormData) =>
    fetch(`${API_URL}/api/projects/${projectId}/sources/`, {
      method: "POST",
      headers: { "X-CSRFToken": getCsrfToken() || "" },
      credentials: "include",
      body: formData,
    }).then(async (r) => {
      if (!r.ok) throw new Error(await r.text());
      return r.json() as Promise<import("./types").Source>;
    }),
};
