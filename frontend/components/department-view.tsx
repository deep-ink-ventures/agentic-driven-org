"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentSummary, DepartmentDetail, AvailableAgent } from "@/lib/types";
import { AgentCard } from "@/components/agent-card";
import { TaskQueue } from "@/components/task-queue";
import { Loader2, CheckCircle, Plus, Zap, Settings2, Pause, Play, Square, RotateCcw, ChevronDown, ChevronRight, FileText, Link2, File, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ConfigFields, type ConfigSchema } from "@/components/config-fields";
import { SprintNotes } from "@/components/sprint-notes";

export function DepartmentView({
  dept,
  projectId,
  deptStatus,
  onSelectAgent,
  onRefresh,
  wsEventQueue,
  wsEventTick,
}: {
  dept: DepartmentDetail;
  projectId: string;
  deptStatus?: "working" | "setup" | "provisioning" | "ready" | "idle";
  onSelectAgent: (a: AgentSummary) => void;
  onRefresh: () => void;
  wsEventQueue?: Array<{ type: string; task: import("@/lib/types").AgentTask }>;
  wsEventTick?: number;
}) {
  const leader = dept.agents.find((a) => a.is_leader);
  const workforce = dept.agents.filter((a) => !a.is_leader);

  type Tab = "agents" | "tasks" | "sprints" | "config";
  const validTabs: Tab[] = ["agents", "tasks", "sprints", "config"];

  function tabFromHash(): Tab {
    if (typeof window === "undefined") return "agents";
    const h = window.location.hash.replace("#", "");
    return validTabs.includes(h as Tab) ? (h as Tab) : "agents";
  }

  const [tab, setTabState] = useState<Tab>(tabFromHash);

  const setTab = useCallback((t: Tab) => {
    setTabState(t);
    window.history.replaceState(null, "", `#${t}`);
  }, []);

  useEffect(() => {
    function onHashChange() {
      setTabState(tabFromHash());
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  const [availableAgents, setAvailableAgents] = useState<AvailableAgent[]>([]);
  const [provisioning, setProvisioning] = useState<Set<string>>(new Set());
  const [togglingAgents, setTogglingAgents] = useState<Set<string>>(new Set());
  const [configDraft, setConfigDraft] = useState<Record<string, unknown>>({});
  const [configSaving, setConfigSaving] = useState(false);
  const [deptSprints, setDeptSprints] = useState<import("@/lib/types").Sprint[]>([]);
  const [expandedSprints, setExpandedSprints] = useState<Set<string>>(new Set());
  const [sprintActing, setSprintActing] = useState<string | null>(null);
  const [stoppingSprint, setStoppingSprint] = useState<import("@/lib/types").Sprint | null>(null);
  const [resettingSprint, setResettingSprint] = useState<import("@/lib/types").Sprint | null>(null);

  async function toggleAgent(agent: AgentSummary) {
    const newStatus = agent.status === "active" ? "inactive" : "active";
    await api.updateAgent(agent.id, { status: newStatus });
    onRefresh();
  }

  async function toggleAutoApprove(agent: AgentSummary) {
    setTogglingAgents((prev) => new Set(prev).add(agent.id));
    try {
      const cmds = agent.enabled_commands || {};
      const allEnabled = Object.keys(cmds).length > 0 && Object.values(cmds).every(Boolean);
      if (allEnabled) {
        await api.updateAgent(agent.id, { enabled_commands: {} });
      } else {
        const bp = await api.getAgentBlueprint(agent.id);
        const dict: Record<string, boolean> = {};
        for (const cmd of bp.commands) {
          dict[cmd.name] = true;
        }
        await api.updateAgent(agent.id, { enabled_commands: dict });
      }
      onRefresh();
    } finally {
      setTogglingAgents((prev) => {
        const next = new Set(prev);
        next.delete(agent.id);
        return next;
      });
    }
  }

  async function toggleAllAutoApprove() {
    if (activeAgents.length === 0) return;
    const newValue = !deptAllApproved;
    setTogglingAgents(new Set(activeAgents.map((a) => a.id)));
    try {
      await Promise.all(activeAgents.map(async (a) => {
        if (newValue) {
          const bp = await api.getAgentBlueprint(a.id);
          const dict: Record<string, boolean> = {};
          for (const cmd of bp.commands) {
            dict[cmd.name] = true;
          }
          await api.updateAgent(a.id, { enabled_commands: dict });
        } else {
          await api.updateAgent(a.id, { enabled_commands: {} });
        }
      }));
      onRefresh();
    } finally {
      setTogglingAgents(new Set());
    }
  }

  // Sync config draft when department changes or settings tab opens
  useEffect(() => {
    const config = (dept.config || {}) as Record<string, unknown>;
    setConfigDraft({ ...config });
  }, [dept.id, dept.config]);

  useEffect(() => {
    api
      .getAvailableAgents(projectId, dept.id)
      .then((res) => setAvailableAgents(res.agents))
      .catch(() => {});
  }, [projectId, dept.id]);

  const refreshSprints = useCallback(() => {
    api.listSprints(projectId, { department: dept.id }).then(setDeptSprints).catch(() => {});
  }, [projectId, dept.id]);

  useEffect(() => {
    if (tab === "sprints") refreshSprints();
  }, [tab, refreshSprints]);

  async function updateSprintStatus(sprint: import("@/lib/types").Sprint, newStatus: "running" | "paused" | "done") {
    if (newStatus === "done") {
      setStoppingSprint(sprint);
      return;
    }
    setSprintActing(sprint.id);
    try {
      await api.updateSprint(projectId, sprint.id, { status: newStatus });
      refreshSprints();
      onRefresh();
    } finally {
      setSprintActing(null);
    }
  }

  async function confirmStopSprint() {
    if (!stoppingSprint) return;
    setSprintActing(stoppingSprint.id);
    setStoppingSprint(null);
    try {
      await api.updateSprint(projectId, stoppingSprint.id, { status: "done" });
      refreshSprints();
      onRefresh();
    } finally {
      setSprintActing(null);
    }
  }

  async function confirmResetSprint() {
    if (!resettingSprint) return;
    setSprintActing(resettingSprint.id);
    setResettingSprint(null);
    try {
      await api.resetSprint(projectId, resettingSprint.id);
      refreshSprints();
      onRefresh();
    } finally {
      setSprintActing(null);
    }
  }

  function toggleExpanded(sprintId: string) {
    setExpandedSprints((prev) => {
      const next = new Set(prev);
      if (next.has(sprintId)) next.delete(sprintId);
      else next.add(sprintId);
      return next;
    });
  }

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
  const deptAllApproved = activeAgents.length > 0 && activeAgents.every((a) => {
    const cmds = a.enabled_commands || {};
    return Object.keys(cmds).length > 0 && Object.values(cmds).every(Boolean);
  });

  return (
    <>
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <h2 className="text-2xl font-semibold">{dept.display_name}</h2>
          <span className={`inline-flex items-center gap-1 text-[10px] font-medium uppercase px-2 py-0.5 rounded-full ${
            deptStatus === "setup" ? "bg-flag-critical/15 text-flag-critical" :
            deptStatus === "provisioning" ? "bg-blue-500/15 text-blue-400 animate-pulse" :
            deptStatus === "working" ? "bg-flag-strength/15 text-flag-strength animate-pulse" :
            deptStatus === "ready" ? "bg-flag-strength/15 text-flag-strength" :
            "bg-bg-surface text-text-secondary"
          }`}>
            {deptStatus === "setup" ? "Setup required" :
             deptStatus === "provisioning" ? "Provisioning" :
             deptStatus === "working" ? "Working" :
             deptStatus === "ready" ? "Ready" :
             "Idle"}
          </span>
        </div>
        {activeAgents.length > 0 && (
          <button
            onClick={toggleAllAutoApprove}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors ${deptAllApproved ? "border-accent-violet/30 bg-accent-violet/10 text-accent-violet" : "border-border bg-bg-surface text-text-secondary hover:text-accent-violet hover:border-accent-violet/30"}`}
          >
            <CheckCircle className="h-3.5 w-3.5" />
            {deptAllApproved ? "Auto-approve on" : "Auto-approve all"}
          </button>
        )}
      </div>
      <p className="text-sm text-text-secondary mb-4">
        {dept.description || `${dept.agents.length} agent${dept.agents.length !== 1 ? "s" : ""} in this department`}
      </p>

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-border mb-6">
        <button
          onClick={() => setTab("agents")}
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
            tab === "agents"
              ? "border-accent-violet text-accent-violet"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          Agents
        </button>
        <button
          onClick={() => setTab("tasks")}
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
            tab === "tasks"
              ? "border-accent-violet text-accent-violet"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          Tasks
        </button>
        <button
          onClick={() => setTab("sprints")}
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
            tab === "sprints"
              ? "border-accent-violet text-accent-violet"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <Zap className="h-3.5 w-3.5" />
          Sprints
        </button>
        <button
          onClick={() => setTab("config")}
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
            tab === "config"
              ? "border-accent-violet text-accent-violet"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <Settings2 className="h-3.5 w-3.5" />
          Config
        </button>
      </div>


      {tab === "agents" && (
        <>
          {leader && (
            <div className="mb-6">
              <AgentCard
                agent={leader}
                onClick={() => onSelectAgent(leader)}
                onToggle={() => toggleAgent(leader)}
                onToggleAutoApprove={() => toggleAutoApprove(leader)}
                toggling={togglingAgents.has(leader.id)}
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
                  toggling={togglingAgents.has(agent.id)}
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
        </>
      )}

      {tab === "tasks" && (
        <TaskQueue
          projectId={projectId}
          department={dept.id}
          wsEventQueue={wsEventQueue}
          wsEventTick={wsEventTick}
          departments={[dept]}
        />
      )}

      {tab === "sprints" && (
        <div className="space-y-1.5">
          {deptSprints.length === 0 ? (
            <p className="text-sm text-text-secondary">No sprints for this department yet.</p>
          ) : (
            deptSprints.map((sprint) => {
              const expanded = expandedSprints.has(sprint.id);
              const acting = sprintActing === sprint.id;
              return (
                <div
                  key={sprint.id}
                  className={`rounded-lg border ${
                    sprint.status === "running"
                      ? "border-flag-strength/20 bg-flag-strength/4"
                      : sprint.status === "paused"
                        ? "border-amber-500/20 bg-amber-500/4"
                        : "border-border bg-bg-surface opacity-60"
                  }`}
                >
                  {/* Compact header row */}
                  <div className="flex items-center gap-2 px-3 py-2">
                    <button
                      onClick={() => toggleExpanded(sprint.id)}
                      className="shrink-0 text-text-secondary hover:text-text-primary transition-colors"
                    >
                      {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    </button>
                    <span
                      onClick={() => toggleExpanded(sprint.id)}
                      className="text-sm text-text-heading truncate flex-1 cursor-pointer"
                    >
                      {sprint.text}
                    </span>
                    <span className="text-[10px] text-text-secondary shrink-0">
                      {sprint.task_count} tasks
                    </span>
                    <span
                      className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded-full shrink-0 ${
                        sprint.status === "running"
                          ? "bg-flag-strength/15 text-flag-strength"
                          : sprint.status === "paused"
                            ? "bg-amber-500/15 text-amber-400"
                            : "bg-bg-input text-text-secondary"
                      }`}
                    >
                      {sprint.status}
                    </span>
                    {/* Action buttons */}
                    {sprint.status !== "done" ? (
                      <div className="flex items-center gap-1 shrink-0">
                        {sprint.status === "running" ? (
                          <button
                            onClick={() => updateSprintStatus(sprint, "paused")}
                            disabled={acting}
                            className="p-1 rounded hover:bg-amber-500/20 text-text-secondary hover:text-amber-400 transition-colors disabled:opacity-50"
                            title="Pause sprint"
                          >
                            <Pause className="h-3.5 w-3.5" />
                          </button>
                        ) : (
                          <button
                            onClick={() => updateSprintStatus(sprint, "running")}
                            disabled={acting}
                            className="p-1 rounded hover:bg-flag-strength/20 text-text-secondary hover:text-flag-strength transition-colors disabled:opacity-50"
                            title="Resume sprint"
                          >
                            <Play className="h-3.5 w-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => updateSprintStatus(sprint, "done")}
                          disabled={acting}
                          className="p-1 rounded hover:bg-flag-critical/20 text-text-secondary hover:text-flag-critical transition-colors disabled:opacity-50"
                          title="Stop sprint"
                        >
                          <Square className="h-3 w-3" />
                        </button>
                      </div>
                    ) : null}
                  </div>
                  {/* Collapsible details */}
                  {expanded && (
                    <div className="px-3 pb-2.5 border-t border-border/50 mx-3">
                      <p className="text-sm text-text-primary pt-2 whitespace-pre-wrap">
                        {sprint.text}
                      </p>
                      <div className="flex items-center justify-between text-[10px] text-text-secondary mt-2">
                        <div className="flex items-center gap-3">
                          <span>{new Date(sprint.created_at).toLocaleDateString()}</span>
                          <span>{sprint.created_by_email}</span>
                          {sprint.departments.length > 1 && (
                            <span>{sprint.departments.map((d) => d.display_name).join(" · ")}</span>
                          )}
                        </div>
                        {sprint.status === "done" && (
                          <button
                            onClick={() => setResettingSprint(sprint)}
                            disabled={acting}
                            className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-[10px] font-medium text-text-secondary hover:text-accent-violet hover:border-accent-violet/40 transition-colors disabled:opacity-50"
                          >
                            <RotateCcw className="h-3 w-3" />
                            Reset &amp; Restart
                          </button>
                        )}
                      </div>
                      {sprint.status === "done" && sprint.completion_summary && (
                        <p className="mt-2 text-xs text-text-secondary">
                          {sprint.completion_summary}
                        </p>
                      )}
                      {/* Sprint outputs */}
                      {sprint.outputs && sprint.outputs.length > 0 && (
                        <div className="mt-3 space-y-2">
                          <div className="text-[10px] font-medium text-text-secondary uppercase tracking-wider">
                            Results
                          </div>
                          {sprint.outputs.map((output) => (
                            <div
                              key={output.id}
                              className="flex items-center gap-2 rounded-md bg-surface-raised/50 border border-border/30 px-2.5 py-2"
                            >
                              {output.output_type === "markdown" || output.output_type === "plaintext" ? (
                                <FileText className="h-3.5 w-3.5 text-accent-primary shrink-0" />
                              ) : output.output_type === "link" ? (
                                <Link2 className="h-3.5 w-3.5 text-accent-primary shrink-0" />
                              ) : (
                                <File className="h-3.5 w-3.5 text-accent-primary shrink-0" />
                              )}
                              <div className="flex-1 min-w-0">
                                <div className="text-xs font-medium text-text-primary truncate">
                                  {output.title}
                                </div>
                                {output.label && (
                                  <div className="text-[10px] text-text-secondary">{output.label}</div>
                                )}
                              </div>
                              <div className="flex items-center gap-1 shrink-0">
                                {output.output_type === "link" && output.url && (
                                  <a
                                    href={output.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-1 rounded hover:bg-accent-primary/20 text-text-secondary hover:text-accent-primary transition-colors"
                                    title="Open link"
                                  >
                                    <Link2 className="h-3 w-3" />
                                  </a>
                                )}
                                {(output.output_type === "markdown" || output.output_type === "plaintext") && output.content && (
                                  <button
                                    onClick={() => {
                                      const blob = new Blob([output.content], { type: "text/markdown" });
                                      const url = URL.createObjectURL(blob);
                                      const a = document.createElement("a");
                                      a.href = url;
                                      a.download = `${output.title.toLowerCase().replace(/\s+/g, "-")}.md`;
                                      a.click();
                                      URL.revokeObjectURL(url);
                                    }}
                                    className="p-1 rounded hover:bg-accent-primary/20 text-text-secondary hover:text-accent-primary transition-colors"
                                    title="Download"
                                  >
                                    <Download className="h-3 w-3" />
                                  </button>
                                )}
                                {output.output_type === "file" && output.original_filename && (
                                  <span className="text-[10px] text-text-secondary">
                                    {output.original_filename}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      {/* Sprint notes */}
                      <SprintNotes
                        projectId={projectId}
                        sprintId={sprint.id}
                        sprintStatus={sprint.status}
                      />
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {tab === "config" && (
        <div>
          {(() => {
            const schema = dept.config_schema as ConfigSchema | undefined;
            const properties = schema?.properties || {};

            if (Object.keys(properties).length === 0) {
              return (
                <p className="text-sm text-text-secondary">
                  No configuration options for this department.
                </p>
              );
            }

            async function saveConfig() {
              setConfigSaving(true);
              try {
                const payload: Record<string, unknown> = {};
                for (const key of Object.keys(properties)) {
                  const val = configDraft[key];
                  if (typeof val === "boolean") {
                    payload[key] = val;
                  } else if (typeof val === "string") {
                    payload[key] = val.trim() || null;
                  } else {
                    payload[key] = val ?? null;
                  }
                }
                await api.updateDepartmentConfig(dept.id, payload);
                onRefresh();
              } finally {
                setConfigSaving(false);
              }
            }

            return (
              <div className="space-y-4">
                <ConfigFields
                  schema={schema!}
                  values={configDraft}
                  onChange={(key, value) =>
                    setConfigDraft((prev) => ({ ...prev, [key]: value }))
                  }
                  disabled={configSaving}
                />
                <Button
                  onClick={saveConfig}
                  disabled={configSaving}
                  className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
                >
                  {configSaving ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : null}
                  Save
                </Button>
              </div>
            );
          })()}
        </div>
      )}
    </div>
    <ConfirmDialog
      open={!!stoppingSprint}
      title="Stop sprint"
      description="This will mark the sprint as done. In-flight tasks will finish, but no new work will be created."
      confirmLabel="Stop sprint"
      cancelLabel="Keep running"
      variant="danger"
      onConfirm={confirmStopSprint}
      onCancel={() => setStoppingSprint(null)}
    />
    <ConfirmDialog
      open={!!resettingSprint}
      title="Reset &amp; restart sprint"
      description="This will delete all tasks, documents, and outputs from this sprint and restart it from scratch. This cannot be undone."
      confirmLabel="Reset &amp; restart"
      cancelLabel="Cancel"
      variant="danger"
      onConfirm={confirmResetSprint}
      onCancel={() => setResettingSprint(null)}
    />
    </>
  );
}
