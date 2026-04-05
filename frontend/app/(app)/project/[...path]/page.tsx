"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { connectWs } from "@/lib/ws";
import type {
  ProjectDetail,
  AgentSummary,
  DepartmentDetail,
  BlueprintInfo,
  AvailableAgent,
} from "@/lib/types";
import { AddDepartmentWizard } from "@/components/add-department-wizard";
import Logomark from "@/components/logomark";
import { TaskQueue } from "@/components/task-queue";
import {
  Loader2,
  LayoutDashboard,
  ChevronLeft,
  Check,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  ToggleLeft,
  ToggleRight,
  Save,
  FileText,
  Terminal,
  Settings2,
  Plus,
  ListTodo,
  Menu,
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

function slugifyName(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

/* ------------------------------------------------------------------ */
/*  AgentCard                                                         */
/* ------------------------------------------------------------------ */

function AgentCard({
  agent,
  onClick,
  onToggle,
  onToggleAutoApprove,
}: {
  agent: AgentSummary;
  onClick: () => void;
  onToggle?: () => void;
  onToggleAutoApprove?: () => void;
}) {
  const clickable = agent.status === "active" || agent.status === "inactive";
  const toggleable = agent.status === "active" || agent.status === "inactive";
  return (
    <div
      onClick={clickable ? onClick : undefined}
      className={`w-full text-left border border-border rounded-lg bg-bg-surface transition-colors p-4 group ${clickable ? "hover:border-accent-gold/50 cursor-pointer" : "opacity-60 cursor-default"}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-text-heading group-hover:text-accent-gold transition-colors truncate mr-2">
          {agent.name}
        </span>
        <div className="flex items-center gap-2 shrink-0">
          {agent.status === "provisioning" && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/15 text-blue-400 animate-pulse">
              Provisioning
            </span>
          )}
          {agent.status === "failed" && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-flag-critical/15 text-flag-critical">
              Failed
            </span>
          )}
          {toggleable && onToggle && (
            <button
              onClick={(e) => { e.stopPropagation(); onToggle(); }}
              className={`transition-colors ${agent.status === "active" ? "text-flag-strength" : "text-text-secondary/40 hover:text-flag-strength"}`}
              title={agent.status === "active" ? "Deactivate" : "Activate"}
            >
              {agent.status === "active" ? (
                <ToggleRight className="h-5 w-5" />
              ) : (
                <ToggleLeft className="h-5 w-5" />
              )}
            </button>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between mt-2">
        {agent.pending_task_count > 0 ? (
          <p className="text-xs text-accent-gold">
            {agent.pending_task_count} pending task{agent.pending_task_count !== 1 ? "s" : ""}
          </p>
        ) : <div />}
        {toggleable && onToggleAutoApprove && (
          <button
            onClick={(e) => { e.stopPropagation(); onToggleAutoApprove(); }}
            className={`flex items-center gap-1 text-[10px] transition-colors ${agent.auto_approve ? "text-accent-gold" : "text-text-secondary/50 hover:text-accent-gold"}`}
            title={agent.auto_approve ? "Disable auto-approve" : "Enable auto-approve"}
          >
            <CheckCircle className="h-3 w-3" />
            <span>Auto</span>
          </button>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  DepartmentView                                                    */
/* ------------------------------------------------------------------ */

function DepartmentView({
  dept,
  projectId,
  onSelectAgent,
  onRefresh,
}: {
  dept: DepartmentDetail;
  projectId: string;
  onSelectAgent: (a: AgentSummary) => void;
  onRefresh: () => void;
}) {
  const leader = dept.agents.find((a) => a.is_leader);
  const workforce = dept.agents.filter((a) => !a.is_leader);

  const [availableAgents, setAvailableAgents] = useState<AvailableAgent[]>([]);
  const [provisioning, setProvisioning] = useState<Set<string>>(new Set());

  async function toggleAgent(agent: AgentSummary) {
    const newStatus = agent.status === "active" ? "inactive" : "active";
    await api.updateAgent(agent.id, { status: newStatus });
    onRefresh();
  }

  async function toggleAutoApprove(agent: AgentSummary) {
    await api.updateAgent(agent.id, { auto_approve: !agent.auto_approve });
    onRefresh();
  }

  async function toggleAllAutoApprove() {
    if (activeAgents.length === 0) return;
    const newValue = !deptAllApproved;
    await Promise.all(activeAgents.map((a) => api.updateAgent(a.id, { auto_approve: newValue })));
    onRefresh();
  }

  useEffect(() => {
    api
      .getAvailableAgents(projectId, dept.id)
      .then((res) => setAvailableAgents(res.agents))
      .catch(() => {});
  }, [projectId, dept.id]);

  async function handleAddAgent(agentType: string) {
    setProvisioning((prev) => new Set(prev).add(agentType));
    try {
      await api.addAgent({ department_id: dept.id, agent_type: agentType });
      setAvailableAgents((prev) => prev.filter((a) => a.agent_type !== agentType));
    } catch {
      // silently fail — user can retry
    } finally {
      setProvisioning((prev) => {
        const next = new Set(prev);
        next.delete(agentType);
        return next;
      });
    }
  }

  const activeAgents = [...(leader ? [leader] : []), ...workforce].filter((a) => a.status === "active" || a.status === "inactive");
  const deptAllApproved = activeAgents.length > 0 && activeAgents.every((a) => a.auto_approve);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-2xl font-semibold">{dept.display_name}</h2>
        {activeAgents.length > 0 && (
          <button
            onClick={toggleAllAutoApprove}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors ${deptAllApproved ? "border-accent-gold/30 bg-accent-gold/10 text-accent-gold" : "border-border bg-bg-surface text-text-secondary hover:text-accent-gold hover:border-accent-gold/30"}`}
          >
            <CheckCircle className="h-3.5 w-3.5" />
            {deptAllApproved ? "Auto-approve on" : "Auto-approve all"}
          </button>
        )}
      </div>
      <p className="text-sm text-text-secondary mb-6">
        {dept.description || `${dept.agents.length} agent${dept.agents.length !== 1 ? "s" : ""} in this department`}
      </p>

      {leader && (
        <div className="mb-6">
          <AgentCard
            agent={leader}
            onClick={() => onSelectAgent(leader)}
            onToggle={() => toggleAgent(leader)}
            onToggleAutoApprove={() => toggleAutoApprove(leader)}
          />
        </div>
      )}

      <h3 className="text-xs uppercase text-text-secondary font-medium mb-3">
        Workforce
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {workforce.map((agent) => (
          <div
            key={agent.id}
            className={agent.status === "provisioning" ? "opacity-50 animate-pulse" : ""}
          >
            <AgentCard
              agent={agent}
              onClick={() => agent.status !== "provisioning" && onSelectAgent(agent)}
              onToggle={() => toggleAgent(agent)}
              onToggleAutoApprove={() => toggleAutoApprove(agent)}
            />
          </div>
        ))}
      </div>

      {availableAgents.length > 0 && (
        <div className="mt-8">
          <h3 className="text-xs uppercase text-text-secondary font-medium mb-3">
            Available Agents
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {availableAgents.map((agent) => {
              const isProvisioning = provisioning.has(agent.agent_type);
              return (
                <div
                  key={agent.agent_type}
                  className="border border-dashed border-border rounded-lg bg-bg-surface p-4 flex flex-col gap-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text-heading">
                      {agent.name}
                    </span>
                    <Button
                      size="sm"
                      onClick={() => handleAddAgent(agent.agent_type)}
                      disabled={isProvisioning}
                      className="h-7 text-xs bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
                    >
                      {isProvisioning ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <>
                          <Plus className="h-3.5 w-3.5 mr-1" />
                          Add
                        </>
                      )}
                    </Button>
                  </div>
                  {agent.description && (
                    <p className="text-xs text-text-secondary line-clamp-2">
                      {agent.description}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Department task queue */}
      <div className="mt-8">
        <TaskQueue projectId={projectId} department={dept.id} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  AgentConfigEditor                                                 */
/* ------------------------------------------------------------------ */

function AgentConfigEditor({
  agent,
  blueprint,
  onSaved,
}: {
  agent: AgentSummary;
  blueprint: BlueprintInfo;
  onSaved: () => void;
}) {
  const [config, setConfig] = useState(agent.config);
  const [autoApprove, setAutoApprove] = useState(agent.auto_approve);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const schema = blueprint.config_schema as {
    required?: string[];
    properties?: Record<string, { type: string; description: string; title?: string }>;
  };

  const requiredKeys = new Set(schema?.required ?? []);
  const configComplete = [...requiredKeys].every((k) => {
    const val = config[k];
    return val !== undefined && val !== null && val !== "";
  });

  async function save() {
    setSaving(true);
    try {
      await api.updateAgent(agent.id, {
        config,
        auto_approve: autoApprove,
      });
      onSaved();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive() {
    if (!configComplete && agent.status !== "active") return;
    setSaving(true);
    try {
      await api.updateAgent(agent.id, {
        status: agent.status === "active" ? "inactive" : "active",
      });
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Activation toggle */}
      <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-bg-surface">
        <div>
          <p className="text-sm font-medium text-text-primary">
            {agent.status === "active" ? "Agent is active" : "Agent is inactive"}
          </p>
          {!configComplete && agent.status !== "active" && (
            <p className="text-xs text-text-secondary mt-0.5">
              Fill in required configuration to activate
            </p>
          )}
        </div>
        <button
          onClick={toggleActive}
          disabled={!configComplete && agent.status !== "active"}
          className={`transition-colors ${agent.status === "active" ? "text-flag-strength" : configComplete ? "text-text-secondary hover:text-flag-strength" : "text-text-secondary/30 cursor-not-allowed"}`}
        >
          {agent.status === "active" ? (
            <ToggleRight className="h-8 w-8" />
          ) : (
            <ToggleLeft className="h-8 w-8" />
          )}
        </button>
      </div>

      {/* Auto-approve all toggle */}
      <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-bg-surface">
        <div>
          <p className="text-sm font-medium text-text-primary">Auto-approve tasks</p>
          <p className="text-xs text-text-secondary mt-0.5">
            {autoApprove ? "All tasks execute without manual approval" : "Tasks require manual approval before execution"}
          </p>
        </div>
        <button
          onClick={() => setAutoApprove(!autoApprove)}
          className={`transition-colors ${autoApprove ? "text-accent-gold" : "text-text-secondary hover:text-accent-gold"}`}
        >
          {autoApprove ? (
            <ToggleRight className="h-8 w-8" />
          ) : (
            <ToggleLeft className="h-8 w-8" />
          )}
        </button>
      </div>

      {/* Config fields */}
      {schema?.properties &&
        Object.keys(schema.properties).length > 0 && (
          <div>
            <h3 className="text-xs uppercase text-text-secondary font-medium mb-3">
              Configuration
            </h3>
            <div className="space-y-3">
              {Object.entries(schema.properties).map(([key, spec]) => (
                <div key={key}>
                  <label className="text-xs text-text-primary font-medium block mb-1">
                    {spec.title || key}
                    {requiredKeys.has(key) && <span className="text-flag-critical ml-0.5">*</span>}
                  </label>
                  <p className="text-[10px] text-text-secondary mb-1">
                    {spec.description}
                  </p>
                  <Input
                    value={
                      config[key] == null
                        ? ""
                        : typeof config[key] === "string"
                          ? (config[key] as string)
                          : JSON.stringify(config[key])
                    }
                    placeholder={
                      agent.effective_config[key] != null && !(key in config)
                        ? String(agent.effective_config[key])
                        : (spec.title || key)
                    }
                    onChange={(e) =>
                      setConfig({ ...config, [key]: e.target.value })
                    }
                    className="bg-bg-input border-border text-text-primary text-xs font-mono"
                  />
                  {agent.config_source[key] && agent.config_source[key] !== "agent" && !(key in config) && (
                    <p className="text-[10px] text-accent-gold mt-0.5">
                      Inherited from {agent.config_source[key]}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

      {/* Auto Approve Actions */}
      <Button
        onClick={save}
        disabled={saving || saved}
        className={`${saved ? "bg-flag-strength hover:bg-flag-strength" : "bg-accent-gold hover:bg-accent-gold-hover"} text-bg-primary disabled:opacity-90 transition-colors`}
      >
        {saving ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : saved ? (
          <>
            <Check className="h-4 w-4 mr-1" /> Saved
          </>
        ) : (
          <>
            <Save className="h-4 w-4 mr-1" /> Save
          </>
        )}
      </Button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  AgentDetailView                                                   */
/* ------------------------------------------------------------------ */

function AgentDetailView({
  agent,
  projectId,
  onBack,
  onAgentUpdated,
}: {
  agent: AgentSummary;
  projectId: string;
  onBack: () => void;
  onAgentUpdated: () => void;
}) {
  const [tab, setTab] = useState<"overview" | "instructions" | "config" | "tasks">(
    "overview",
  );
  const [blueprint, setBlueprint] = useState<BlueprintInfo | null>(null);
  const [instructions, setInstructions] = useState(agent.instructions);
  const [editingInstructions, setEditingInstructions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [instructionsSaved, setInstructionsSaved] = useState(false);

  useEffect(() => {
    api.getAgentBlueprint(agent.id).then(setBlueprint).catch(() => {});
  }, [agent.id]);

  async function saveInstructions() {
    setSaving(true);
    try {
      await api.updateAgent(agent.id, { instructions });
      onAgentUpdated();
      setInstructionsSaved(true);
      setTimeout(() => setInstructionsSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  const tabs = [
    { key: "overview" as const, label: "Overview", icon: FileText },
    { key: "tasks" as const, label: "Tasks", icon: ListTodo },
    { key: "instructions" as const, label: "Instructions", icon: Terminal },
    { key: "config" as const, label: "Config", icon: Settings2 },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem-3rem)]">
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-text-secondary hover:text-text-primary text-sm mb-4 transition-colors shrink-0"
      >
        <ChevronLeft className="h-4 w-4" /> Back
      </button>

      <div className="flex items-center gap-3 mb-1 shrink-0">
        <h2 className="text-2xl font-semibold">{agent.name}</h2>
      </div>

      {blueprint?.tags && (
        <div className="flex gap-1.5 mb-6">
          {blueprint.tags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] px-2 py-0.5 rounded-full bg-accent-gold/10 text-accent-gold border border-accent-gold/20"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-border shrink-0">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm transition-colors border-b-2 -mb-px ${
              tab === key
                ? "border-accent-gold text-accent-gold"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            <Icon className="h-3.5 w-3.5" /> {label}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {tab === "overview" && blueprint && (
        <div className="space-y-6 flex-1 overflow-y-auto min-h-0">
          <div>
            <p className="text-sm text-text-primary">
              {blueprint.description}
            </p>
          </div>
          <div>
            <h3 className="text-xs uppercase text-text-secondary font-medium mb-2">
              Skills
            </h3>
            <div className="space-y-1.5">
              {blueprint.skills_description.split("\n").filter(Boolean).map((line, i) => {
                const match = line.match(/^- \*\*(.+?)\*\*:\s*(.+)$/);
                if (!match) return null;
                return (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="text-text-primary font-mono">{match[1]}</span>
                    <span className="text-text-secondary">{match[2]}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div>
            <h3 className="text-xs uppercase text-text-secondary font-medium mb-2">
              Commands
            </h3>
            <div className="space-y-1.5">
              {blueprint.commands.map((cmd) => (
                <div
                  key={cmd.name}
                  className="flex items-center gap-2 text-xs"
                >
                  <span className="text-text-primary font-mono">
                    {cmd.name}
                  </span>
                  {cmd.schedule && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-bg-input border border-border text-text-secondary">
                      {cmd.schedule}
                    </span>
                  )}
                  <span className="text-text-secondary">
                    {cmd.description}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Instructions tab */}
      {tab === "instructions" && (
        <div className="flex flex-col flex-1 min-h-0">
          {editingInstructions ? (
            <>
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Custom instructions for this agent..."
                className="w-full flex-1 min-h-0 rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-none font-mono"
                autoFocus
              />
              <div className="flex gap-2 mt-3 shrink-0">
                <Button
                  onClick={() => { saveInstructions(); setEditingInstructions(false); }}
                  disabled={saving || instructions === agent.instructions}
                  className={`${instructionsSaved ? "bg-flag-strength hover:bg-flag-strength" : "bg-accent-gold hover:bg-accent-gold-hover"} text-bg-primary disabled:opacity-90 transition-colors`}
                >
                  {saving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : instructionsSaved ? (
                    <><Check className="h-4 w-4 mr-1" /> Saved</>
                  ) : (
                    <><Save className="h-4 w-4 mr-1" /> Save</>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => { setInstructions(agent.instructions); setEditingInstructions(false); }}
                  className="border-border text-text-secondary hover:text-text-primary"
                >
                  Cancel
                </Button>
              </div>
            </>
          ) : (
            <div
              className="flex-1 min-h-0 rounded-lg border border-dashed border-border hover:border-accent-gold/40 p-4 cursor-pointer transition-colors overflow-y-auto"
              onClick={() => setEditingInstructions(true)}
            >
              {instructions ? (
                <div className="max-w-none text-sm text-text-primary [&_p]:mb-3 [&_ul]:mb-3 [&_ol]:mb-3 [&_h1]:mb-3 [&_h2]:mb-3 [&_h3]:mb-3 [&_h4]:mb-3 [&_li]:mb-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:text-base [&_h2]:font-semibold [&_h3]:text-sm [&_h3]:font-semibold [&>*:last-child]:mb-0">
                  <ReactMarkdown>{instructions}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-text-secondary text-sm">
                  Click to add custom instructions...
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Config tab */}
      {tab === "config" && blueprint && (
        <AgentConfigEditor
          agent={agent}
          blueprint={blueprint}
          onSaved={onAgentUpdated}
        />
      )}

      {/* Tasks tab */}
      {tab === "tasks" && (
        <div className="flex-1 overflow-y-auto min-h-0">
          <TaskQueue projectId={projectId} agent={agent.id} />
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main page                                                         */
/* ------------------------------------------------------------------ */

export default function ProjectDetailPage() {
  const params = useParams<{ path: string[] }>();
  const pathSegments = params.path || [];
  const projectSlug = pathSegments[0] || "";
  const deptSlug = pathSegments[1] || "";
  const agentSlug = pathSegments[2] || "";
  const router = useRouter();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAddDept, setShowAddDept] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [view, setView] = useState<"dashboard" | "department" | "agent" | "settings">(
    "dashboard",
  );
  const [selectedDept, setSelectedDept] = useState<DepartmentDetail | null>(
    null,
  );
  const [selectedAgent, setSelectedAgent] = useState<AgentSummary | null>(
    null,
  );
  const [initialDeepLinkDone, setInitialDeepLinkDone] = useState(false);

  // Apply deep link from URL on first load
  useEffect(() => {
    if (!project || initialDeepLinkDone) return;
    setInitialDeepLinkDone(true);

    if (deptSlug) {
      const dept = project.departments.find(
        (d) => d.department_type === deptSlug,
      );
      if (dept) {
        setSelectedDept(dept);
        if (agentSlug) {
          const agent = dept.agents.find(
            (a) => a.agent_type === agentSlug || slugifyName(a.name) === agentSlug,
          );
          if (agent) {
            setSelectedAgent(agent);
            setView("agent");
            // Handle #config hash
            if (typeof window !== "undefined" && window.location.hash === "#config") {
              // Tab will be set in AgentDetailView
            }
          } else {
            setView("department");
          }
        } else {
          setView("department");
        }
      }
    }
  }, [project, initialDeepLinkDone, deptSlug, agentSlug]);

  const load = useCallback(() => {
    if (!projectSlug) return;
    api
      .getProjectDetail(projectSlug)
      .then((proj) => {
        setProject(proj);
        setSelectedDept((prev) => {
          if (!prev) return prev;
          return proj.departments.find((d) => d.id === prev.id) ?? prev;
        });
        setSelectedAgent((prev) => {
          if (!prev) return prev;
          for (const dept of proj.departments) {
            const fresh = dept.agents.find((a) => a.id === prev.id);
            if (fresh) return fresh;
          }
          return prev;
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectSlug]);

  useEffect(() => {
    load();
  }, [load]);

  // WebSocket for real-time agent status updates
  const wsRef = useRef<WebSocket | null>(null);
  useEffect(() => {
    if (!project) return;
    let cancelled = false;
    connectWs(`/ws/project/${project.id}/`, (data) => {
      if (data.type === "agent.status") {
        const agentId = data.agent_id as string;
        const newStatus = data.status as string;
        setProject((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            departments: prev.departments.map((dept) => ({
              ...dept,
              agents: dept.agents.map((a) =>
                a.id === agentId ? { ...a, status: newStatus as AgentSummary["status"] } : a,
              ),
            })),
          };
        });
        setSelectedDept((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            agents: prev.agents.map((a) =>
              a.id === agentId ? { ...a, status: newStatus as AgentSummary["status"] } : a,
            ),
          };
        });
        setSelectedAgent((prev) => {
          if (!prev || prev.id !== agentId) return prev;
          return { ...prev, status: newStatus as AgentSummary["status"] };
        });
      }
    }).then((ws) => {
      if (cancelled) { ws.close(); return; }
      wsRef.current = ws;
    }).catch(() => {});
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [project?.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <Loader2 className="h-6 w-6 text-text-secondary animate-spin" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <p className="text-text-secondary">Project not found.</p>
      </div>
    );
  }

  const sidebarContent = (
    <>
      <button
        onClick={() => {
          setView("dashboard");
          setSelectedDept(null);
          setSelectedAgent(null);
          setSidebarOpen(false);
          router.push(`/project/${projectSlug}`);
        }}
        className={`flex items-center gap-2 px-4 py-3 text-sm transition-colors ${
          view === "dashboard"
            ? "text-accent-gold bg-accent-gold/10"
            : "text-text-secondary hover:text-text-primary hover:bg-bg-surface-hover"
        }`}
      >
        <LayoutDashboard className="h-4 w-4" />
        Dashboard
      </button>
      <Separator />
      <div className="flex-1 overflow-y-auto px-2 py-2">
        <p className="text-[10px] uppercase text-text-secondary font-medium px-2 mb-2">
          Departments
        </p>
        {project.departments.map((dept) => {
          const activeCount = dept.agents.filter((a) => a.status === "active").length;
          const totalCount = dept.agents.length;
          return (
            <button
              key={dept.id}
              onClick={() => {
                setView("department");
                setSelectedDept(dept);
                setSelectedAgent(null);
                setSidebarOpen(false);
                router.push(`/project/${projectSlug}/${dept.department_type}`);
              }}
              className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                selectedDept?.id === dept.id && view !== "dashboard"
                  ? "bg-accent-gold/10 text-accent-gold"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-surface-hover"
              }`}
            >
              <span className="text-sm">{dept.display_name}</span>
              <span className="block text-[10px] mt-0.5 opacity-60">
                {activeCount}/{totalCount} agents active
              </span>
            </button>
          );
        })}
      </div>
      <div className="px-2 py-2 border-t border-border space-y-1">
        <button
          onClick={() => { setShowAddDept(true); setSidebarOpen(false); }}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-bg-surface-hover transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Department
        </button>
        <button
          onClick={() => {
            setView("settings");
            setSelectedDept(null);
            setSelectedAgent(null);
            setSidebarOpen(false);
            router.push(`/project/${projectSlug}/settings`);
          }}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
            view === "settings"
              ? "text-accent-gold bg-accent-gold/10"
              : "text-text-secondary hover:text-text-primary hover:bg-bg-surface-hover"
          }`}
        >
          <Settings2 className="h-4 w-4" />
          Settings
        </button>
      </div>
    </>
  );

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Mobile sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(true)}
        className="md:hidden fixed bottom-4 right-4 z-40 h-12 w-12 rounded-full bg-accent-gold text-bg-primary flex items-center justify-center shadow-lg active:scale-95 transition-transform"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSidebarOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-64 bg-bg-surface border-r border-border flex flex-col animate-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <span className="flex items-center gap-2 font-serif text-sm text-accent-gold font-bold">
                <Logomark size={18} className="text-accent-gold" />
                Navigation
              </span>
              <button onClick={() => setSidebarOpen(false)} className="text-text-secondary hover:text-text-primary">
                <X className="h-4 w-4" />
              </button>
            </div>
            {sidebarContent}
          </div>
        </div>
      )}

      {/* Desktop sidebar */}
      <div className="hidden md:flex w-56 border-r border-border bg-bg-surface shrink-0 flex-col">
        {sidebarContent}
      </div>

      {/* Main area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        {view === "dashboard" && (
          <TaskQueue projectId={project.id} />
        )}
        {view === "department" && selectedDept && !selectedAgent && (
          <DepartmentView
            dept={selectedDept}
            projectId={project.id}
            onSelectAgent={(agent) => {
              setSelectedAgent(agent);
              setView("agent");
              router.push(`/project/${projectSlug}/${selectedDept.department_type}/${slugifyName(agent.name)}`);
            }}
            onRefresh={load}
          />
        )}
        {view === "agent" && selectedAgent && (
          <AgentDetailView
            agent={selectedAgent}
            projectId={project.id}
            onBack={() => {
              setSelectedAgent(null);
              setView("department");
              if (selectedDept) router.push(`/project/${projectSlug}/${selectedDept.department_type}`);
            }}
            onAgentUpdated={load}
          />
        )}
        {view === "settings" && (
          <div>
            <h2 className="text-2xl font-semibold mb-4">Project Settings</h2>
            <p className="text-sm text-text-secondary mb-6">
              Configure project-level settings that apply to all departments.
            </p>
            <div className="rounded-lg border border-border bg-bg-surface p-6">
              <p className="text-sm text-text-secondary">
                Project configuration coming soon.
              </p>
            </div>
          </div>
        )}
      </div>

      <AddDepartmentWizard
        projectId={project.id}
        isOpen={showAddDept}
        onClose={() => setShowAddDept(false)}
        onAdded={() => {
          setShowAddDept(false);
          load();
        }}
      />
    </div>
  );
}
