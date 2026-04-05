"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentSummary, DepartmentDetail, AvailableAgent } from "@/lib/types";
import { AgentCard } from "@/components/agent-card";
import { TaskQueue } from "@/components/task-queue";
import { Loader2, CheckCircle, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

export function DepartmentView({
  dept,
  projectId,
  onSelectAgent,
  onRefresh,
  taskWsEvent,
}: {
  dept: DepartmentDetail;
  projectId: string;
  onSelectAgent: (a: AgentSummary) => void;
  onRefresh: () => void;
  taskWsEvent?: { type: string; task: import("@/lib/types").AgentTask } | null;
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
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors ${deptAllApproved ? "border-accent-violet/30 bg-accent-violet/10 text-accent-violet" : "border-border bg-bg-surface text-text-secondary hover:text-accent-violet hover:border-accent-violet/30"}`}
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
        <TaskQueue projectId={projectId} department={dept.id} wsEvent={taskWsEvent} />
      </div>
    </div>
  );
}
