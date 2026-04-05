"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentSummary, DepartmentDetail, AvailableAgent } from "@/lib/types";
import { AgentCard } from "@/components/agent-card";
import { TaskQueue } from "@/components/task-queue";
import { Loader2, CheckCircle, Plus, Users, ListTodo, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function DepartmentView({
  dept,
  projectId,
  deptStatus,
  onSelectAgent,
  onRefresh,
  taskWsEvent,
}: {
  dept: DepartmentDetail;
  projectId: string;
  deptStatus?: "working" | "setup" | "provisioning" | "ready" | "idle";
  onSelectAgent: (a: AgentSummary) => void;
  onRefresh: () => void;
  taskWsEvent?: { type: string; task: import("@/lib/types").AgentTask } | null;
}) {
  const leader = dept.agents.find((a) => a.is_leader);
  const workforce = dept.agents.filter((a) => !a.is_leader);

  const [availableAgents, setAvailableAgents] = useState<AvailableAgent[]>([]);
  const [provisioning, setProvisioning] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState<"agents" | "tasks" | "config">("agents");
  const [configDraft, setConfigDraft] = useState<Record<string, string>>({});
  const [configSaving, setConfigSaving] = useState(false);

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

  // Sync config draft when department changes or settings tab opens
  useEffect(() => {
    const config = (dept.config || {}) as Record<string, unknown>;
    const draft: Record<string, string> = {};
    for (const [key, value] of Object.entries(config)) {
      draft[key] = typeof value === "string" ? value : JSON.stringify(value);
    }
    setConfigDraft(draft);
  }, [dept.id, dept.config]);

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

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border mb-6">
        <button
          onClick={() => setTab("agents")}
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
            tab === "agents"
              ? "border-accent-violet text-accent-violet"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <Users className="h-3.5 w-3.5" />
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
          <ListTodo className="h-3.5 w-3.5" />
          Tasks
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

      {/* Agents tab */}
      {tab === "agents" && (
        <>
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
        </>
      )}

      {/* Tasks tab */}
      {tab === "tasks" && (
        <TaskQueue projectId={projectId} department={dept.id} wsEvent={taskWsEvent} />
      )}

      {/* Config tab */}
      {tab === "config" && (
        <div className="max-w-lg">
          {(() => {
            const schema = dept.config_schema as {
              properties?: Record<string, { title?: string; description?: string; type?: string }>;
              required?: string[];
            } | undefined;
            const properties = schema?.properties || {};
            const requiredFields = new Set(schema?.required || []);

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
                  const val = configDraft[key]?.trim();
                  payload[key] = val || null;
                }
                await api.updateDepartmentConfig(dept.id, payload);
                onRefresh();
              } finally {
                setConfigSaving(false);
              }
            }

            return (
              <div className="space-y-4">
                {Object.entries(properties).map(([key, spec]) => (
                  <div key={key}>
                    <label className="block text-sm font-medium text-text-primary mb-1">
                      {spec.title || key}
                      {requiredFields.has(key) && (
                        <span className="text-flag-critical ml-1">*</span>
                      )}
                    </label>
                    {spec.description && (
                      <p className="text-xs text-text-secondary mb-1.5">{spec.description}</p>
                    )}
                    <input
                      type="text"
                      value={configDraft[key] || ""}
                      onChange={(e) =>
                        setConfigDraft((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      className="w-full rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:ring-1 focus:ring-accent-violet"
                      placeholder={spec.description || key}
                    />
                  </div>
                ))}
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
  );
}
