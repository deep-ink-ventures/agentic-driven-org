"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type {
  ProjectDetail,
  AgentTask,
  AgentSummary,
  DepartmentDetail,
  BlueprintInfo,
} from "@/lib/types";
import {
  Loader2,
  LayoutDashboard,
  ChevronLeft,
  Check,
  X,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ToggleLeft,
  ToggleRight,
  Save,
  Pencil,
  FileText,
  Terminal,
  Settings2,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

/* ------------------------------------------------------------------ */
/*  Status badge colours                                              */
/* ------------------------------------------------------------------ */

const statusColors: Record<AgentTask["status"], string> = {
  awaiting_approval:
    "bg-accent-gold/15 text-accent-gold border-accent-gold/30",
  planned: "bg-bg-surface text-text-secondary border-border",
  queued: "bg-bg-surface text-text-secondary border-border",
  processing: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  done: "bg-flag-strength/15 text-flag-strength border-flag-strength/30",
  failed: "bg-flag-critical/15 text-flag-critical border-flag-critical/30",
};

/* ------------------------------------------------------------------ */
/*  TaskCard                                                          */
/* ------------------------------------------------------------------ */

function TaskCard({
  task,
  projectId,
  onUpdate,
}: {
  task: AgentTask;
  projectId: string;
  onUpdate: (t: AgentTask) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [acting, setActing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editedPlan, setEditedPlan] = useState(task.step_plan);
  const [editedSummary, setEditedSummary] = useState(task.exec_summary);

  const isApproval = task.status === "awaiting_approval";
  const hasEdits = editedPlan !== task.step_plan || editedSummary !== task.exec_summary;

  async function handleApprove() {
    setActing(true);
    try {
      const edits = hasEdits ? { step_plan: editedPlan, exec_summary: editedSummary } : undefined;
      const updated = await api.approveTask(projectId, task.id, edits);
      onUpdate(updated);
      setEditing(false);
    } finally {
      setActing(false);
    }
  }

  async function handleReject() {
    setActing(true);
    try {
      const updated = await api.rejectTask(projectId, task.id);
      onUpdate(updated);
    } finally {
      setActing(false);
    }
  }

  return (
    <div className="border border-border rounded-lg bg-bg-surface">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left"
      >
        <span
          className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full border ${statusColors[task.status]}`}
        >
          {task.status.replace("_", " ")}
        </span>
        <span className="text-xs text-text-secondary shrink-0">
          {task.agent_name}
        </span>
        <span className="text-sm text-text-primary truncate flex-1">
          {editing ? editedSummary : task.exec_summary}
        </span>
        <span className="text-xs text-text-secondary shrink-0">
          {new Date(task.created_at).toLocaleTimeString()}
        </span>
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5 text-text-secondary" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-text-secondary" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-border pt-3">
          {/* Summary — editable for approval tasks */}
          <div>
            <p className="text-xs text-text-secondary mb-1">Summary</p>
            {editing ? (
              <Input
                value={editedSummary}
                onChange={(e) => setEditedSummary(e.target.value)}
                className="bg-bg-input border-border text-text-primary text-sm"
              />
            ) : (
              <p className="text-sm text-text-primary">{task.exec_summary}</p>
            )}
          </div>

          {/* Plan — editable for approval tasks */}
          {(task.step_plan || editing) && (
            <div>
              <p className="text-xs text-text-secondary mb-1">Plan</p>
              {editing ? (
                <textarea
                  value={editedPlan}
                  onChange={(e) => setEditedPlan(e.target.value)}
                  rows={Math.max(6, editedPlan.split("\n").length + 2)}
                  className="w-full rounded-lg border border-border bg-bg-input px-3 py-2 text-xs text-text-primary font-mono outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-y"
                />
              ) : (
                <pre className="text-xs text-text-primary whitespace-pre-wrap bg-bg-input rounded-lg p-3 border border-border">
                  {task.step_plan}
                </pre>
              )}
            </div>
          )}

          {/* Report — read only */}
          {task.report && (
            <div>
              <p className="text-xs text-text-secondary mb-1">Report</p>
              <pre className="text-xs text-text-primary whitespace-pre-wrap bg-bg-input rounded-lg p-3 border border-border">
                {task.report}
              </pre>
            </div>
          )}
          {task.error_message && (
            <div className="flex items-start gap-2 text-flag-critical text-xs p-2 rounded-lg bg-flag-critical/10">
              <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              {task.error_message}
            </div>
          )}
          {task.token_usage && (
            <p className="text-[10px] text-text-secondary">
              {task.token_usage.model} &middot;{" "}
              {task.token_usage.input_tokens}&rarr;
              {task.token_usage.output_tokens} tokens &middot; $
              {task.token_usage.cost_usd.toFixed(4)}
            </p>
          )}

          {/* Actions for approval tasks */}
          {isApproval && (
            <div className="flex items-center gap-2 pt-1">
              {!editing ? (
                <>
                  <Button
                    size="sm"
                    onClick={handleApprove}
                    disabled={acting}
                    className="bg-flag-strength text-white hover:bg-flag-strength/90 text-xs h-8"
                  >
                    <Check className="h-3.5 w-3.5 mr-1" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditing(true)}
                    className="border-border text-text-secondary hover:text-text-primary text-xs h-8"
                  >
                    <Pencil className="h-3.5 w-3.5 mr-1" /> Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleReject}
                    disabled={acting}
                    className="border-flag-critical/50 text-flag-critical hover:bg-flag-critical/10 text-xs h-8"
                  >
                    <X className="h-3.5 w-3.5 mr-1" /> Reject
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    size="sm"
                    onClick={handleApprove}
                    disabled={acting}
                    className="bg-flag-strength text-white hover:bg-flag-strength/90 text-xs h-8"
                  >
                    <Check className="h-3.5 w-3.5 mr-1" /> {hasEdits ? "Approve with edits" : "Approve"}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => { setEditing(false); setEditedPlan(task.step_plan); setEditedSummary(task.exec_summary); }}
                    className="border-border text-text-secondary hover:text-text-primary text-xs h-8"
                  >
                    Cancel
                  </Button>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  DashboardView                                                     */
/* ------------------------------------------------------------------ */

function DashboardView({
  tasks,
  projectId,
  onTaskUpdate,
}: {
  tasks: AgentTask[];
  projectId: string;
  onTaskUpdate: (t: AgentTask) => void;
}) {
  const statusOrder: AgentTask["status"][] = [
    "awaiting_approval",
    "processing",
    "queued",
    "planned",
    "done",
    "failed",
  ];

  const sorted = [...tasks].sort(
    (a, b) => statusOrder.indexOf(a.status) - statusOrder.indexOf(b.status),
  );

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Task Queue</h2>
      {sorted.length === 0 ? (
        <p className="text-text-secondary text-sm py-10 text-center">
          No tasks yet.
        </p>
      ) : (
        <div className="space-y-2">
          {sorted.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              projectId={projectId}
              onUpdate={onTaskUpdate}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  AgentCard                                                         */
/* ------------------------------------------------------------------ */

function AgentCard({
  agent,
  onClick,
}: {
  agent: AgentSummary;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left border border-border rounded-lg bg-bg-surface hover:border-accent-gold/50 transition-colors p-4 group"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-text-heading group-hover:text-accent-gold transition-colors">
          {agent.name}
        </span>
        <span
          className={`text-[10px] px-1.5 py-0.5 rounded-full ${agent.is_active ? "bg-flag-strength/15 text-flag-strength" : "bg-bg-input text-text-secondary"}`}
        >
          {agent.is_active ? "Active" : "Inactive"}
        </span>
      </div>
      <p className="text-xs text-text-secondary">{agent.agent_type}</p>
      {agent.pending_task_count > 0 && (
        <p className="text-xs text-accent-gold mt-2">
          {agent.pending_task_count} pending task
          {agent.pending_task_count !== 1 ? "s" : ""}
        </p>
      )}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  DepartmentView                                                    */
/* ------------------------------------------------------------------ */

function DepartmentView({
  dept,
  onSelectAgent,
}: {
  dept: DepartmentDetail;
  onSelectAgent: (a: AgentSummary) => void;
}) {
  const leader = dept.agents.find((a) => a.is_leader);
  const workforce = dept.agents.filter((a) => !a.is_leader);

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-2">{dept.display_name}</h2>
      {dept.description && (
        <p className="text-sm text-text-secondary mb-6">{dept.description}</p>
      )}

      {leader && (
        <div className="mb-6">
          <AgentCard
            agent={leader}
            onClick={() => onSelectAgent(leader)}
          />
        </div>
      )}

      <h3 className="text-xs uppercase text-text-secondary font-medium mb-3">
        Workforce
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {workforce.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            onClick={() => onSelectAgent(agent)}
          />
        ))}
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
  const [autoActions, setAutoActions] = useState(agent.auto_actions);
  const [saving, setSaving] = useState(false);

  const schema = blueprint.config_schema as {
    required?: string[];
    properties?: Record<string, { type: string; description: string; title?: string }>;
  };
  const aaSchema = blueprint.auto_actions_schema as {
    properties?: Record<string, unknown>;
  };

  const requiredKeys = new Set(schema?.required ?? []);
  const configComplete = [...requiredKeys].every((k) => {
    const val = config[k];
    return val !== undefined && val !== null && val !== "";
  });

  const [saved, setSaved] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await api.updateAgent(agent.id, {
        config,
        auto_actions: autoActions,
      });
      onSaved();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive() {
    if (!configComplete && !agent.is_active) return;
    setSaving(true);
    try {
      await api.updateAgent(agent.id, { is_active: !agent.is_active });
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Activation toggle — top */}
      <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-bg-surface">
        <div>
          <p className="text-sm font-medium text-text-primary">
            {agent.is_active ? "Agent is active" : "Agent is inactive"}
          </p>
          {!configComplete && !agent.is_active && (
            <p className="text-xs text-text-secondary mt-0.5">
              Fill in required configuration to activate
            </p>
          )}
        </div>
        <button
          onClick={toggleActive}
          disabled={!configComplete && !agent.is_active}
          className={`transition-colors ${agent.is_active ? "text-flag-strength" : configComplete ? "text-text-secondary hover:text-flag-strength" : "text-text-secondary/30 cursor-not-allowed"}`}
        >
          {agent.is_active ? (
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
            <div className="space-y-4">
              {Object.entries(schema.properties).map(([key, spec]) => (
                <div key={key}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-text-primary font-medium">
                      {spec.title || key}
                    </span>
                    {requiredKeys.has(key) && <span className="text-flag-critical text-xs">*</span>}
                    <span className="text-xs text-text-secondary">{spec.description}</span>
                  </div>
                  <Input
                    value={
                      config[key] == null
                        ? ""
                        : typeof config[key] === "string"
                          ? (config[key] as string)
                          : JSON.stringify(config[key])
                    }
                    onChange={(e) =>
                      setConfig({ ...config, [key]: e.target.value })
                    }
                    placeholder={spec.title || key}
                    className="bg-bg-input border-border text-text-primary text-xs"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

      {/* Auto Approve Actions */}
      {aaSchema?.properties &&
        Object.keys(aaSchema.properties).length > 0 && (
          <div>
            <h3 className="text-xs uppercase text-text-secondary font-medium mb-3">
              Auto Approve Actions
            </h3>
            <p className="text-[10px] text-text-secondary mb-3">
              When enabled, tasks from these commands execute without manual approval.
            </p>
            <div className="space-y-3">
              {Object.keys(aaSchema.properties).map((cmdName) => {
                const enabled = autoActions[cmdName] ?? false;
                const cmd = blueprint.commands.find(
                  (c) => c.name === cmdName,
                );
                return (
                  <div
                    key={cmdName}
                    className="flex items-center justify-between py-2 px-3 rounded-lg border border-border bg-bg-surface"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-text-primary font-medium">
                          {cmdName}
                        </span>
                        {cmd?.schedule && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-bg-input border border-border text-text-secondary">
                            {cmd.schedule}
                          </span>
                        )}
                      </div>
                      {cmd?.description && (
                        <p className="text-xs text-text-secondary mt-0.5 truncate">
                          {cmd.description}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() =>
                        setAutoActions({
                          ...autoActions,
                          [cmdName]: !enabled,
                        })
                      }
                      className={`shrink-0 ml-3 ${enabled ? "text-flag-strength" : "text-text-secondary"} transition-colors`}
                    >
                      {enabled ? (
                        <ToggleRight className="h-6 w-6" />
                      ) : (
                        <ToggleLeft className="h-6 w-6" />
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

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
  onBack,
  onAgentUpdated,
}: {
  agent: AgentSummary;
  projectId: string;
  onBack: () => void;
  onAgentUpdated: () => void;
}) {
  const [tab, setTab] = useState<"overview" | "instructions" | "config">(
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
    { key: "instructions" as const, label: "Instructions", icon: Terminal },
    { key: "config" as const, label: "Config", icon: Settings2 },
  ];

  return (
    <div>
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-text-secondary hover:text-text-primary text-sm mb-4 transition-colors"
      >
        <ChevronLeft className="h-4 w-4" /> Back
      </button>

      <div className="flex items-center gap-3 mb-1">
        <h2 className="text-2xl font-semibold">{agent.name}</h2>
        <span className="text-xs px-2 py-0.5 rounded-full bg-bg-input border border-border text-text-secondary">
          {agent.agent_type}
        </span>
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
      <div className="flex gap-1 mb-6 border-b border-border">
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
        <div className="space-y-6">
          <div>
            <p className="text-sm text-text-primary">
              {blueprint.description}
            </p>
          </div>
          <div>
            <h3 className="text-xs uppercase text-text-secondary font-medium mb-2">
              Skills
            </h3>
            <div className="text-xs text-text-primary prose prose-invert prose-xs max-w-none">
              <ReactMarkdown>{blueprint.skills_description}</ReactMarkdown>
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
        <div className="flex flex-col h-full min-h-0">
          {editingInstructions ? (
            <>
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Custom instructions for this agent..."
                className="w-full flex-1 min-h-[200px] rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-none font-mono"
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
            <div className="flex-1 overflow-y-auto">
              <div className="flex justify-end mb-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditingInstructions(true)}
                  className="border-border text-text-secondary hover:text-text-primary text-xs h-7"
                >
                  <Pencil className="h-3 w-3 mr-1" /> Edit
                </Button>
              </div>
              {instructions ? (
                <div className="prose prose-invert prose-sm max-w-none text-text-primary">
                  <ReactMarkdown>{instructions}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-text-secondary/50 text-sm italic">
                  No custom instructions set.
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
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main page                                                         */
/* ------------------------------------------------------------------ */

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"dashboard" | "department" | "agent">(
    "dashboard",
  );
  const [selectedDept, setSelectedDept] = useState<DepartmentDetail | null>(
    null,
  );
  const [selectedAgent, setSelectedAgent] = useState<AgentSummary | null>(
    null,
  );

  const load = useCallback(() => {
    if (!id) return;
    Promise.all([api.getProjectDetail(id), api.getProjectTasks(id)])
      .then(([proj, t]) => {
        setProject(proj);
        setTasks(t);
        // Sync selected dept/agent with fresh data
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
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  function handleTaskUpdate(updated: AgentTask) {
    setTasks((prev) =>
      prev.map((t) => (t.id === updated.id ? updated : t)),
    );
  }

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

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Sidebar */}
      <div className="w-56 border-r border-border bg-bg-surface shrink-0 flex flex-col">
        <button
          onClick={() => {
            setView("dashboard");
            setSelectedDept(null);
            setSelectedAgent(null);
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
            const activeCount = dept.agents.filter((a) => a.is_active && !a.is_leader).length;
            const totalCount = dept.agents.filter((a) => !a.is_leader).length;
            return (
              <button
                key={dept.id}
                onClick={() => {
                  setView("department");
                  setSelectedDept(dept);
                  setSelectedAgent(null);
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
      </div>

      {/* Main area */}
      <div className="flex-1 overflow-y-auto p-6">
        {view === "dashboard" && (
          <DashboardView
            tasks={tasks}
            projectId={project.id}
            onTaskUpdate={handleTaskUpdate}
          />
        )}
        {view === "department" && selectedDept && !selectedAgent && (
          <DepartmentView
            dept={selectedDept}
            onSelectAgent={(agent) => {
              setSelectedAgent(agent);
              setView("agent");
            }}
          />
        )}
        {view === "agent" && selectedAgent && (
          <AgentDetailView
            agent={selectedAgent}
            projectId={project.id}
            onBack={() => {
              setSelectedAgent(null);
              setView("department");
            }}
            onAgentUpdated={load}
          />
        )}
      </div>
    </div>
  );
}
