"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import type { AvailableDepartment, AvailableAgent } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  X,
  ArrowLeft,
  ArrowRight,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Building2,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from "lucide-react";

interface AddDepartmentWizardProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onAdded: () => void;
}

/** Resolve which agents should be pre-checked for a department. */
function computePreselected(workforce: AvailableAgent[]): Set<string> {
  const selected = new Set<string>();

  // Start with recommended agents
  for (const a of workforce) {
    if (a.recommended) selected.add(a.agent_type);
  }

  // Add all essential agents
  for (const a of workforce) {
    if (a.essential) selected.add(a.agent_type);
  }

  // For each selected agent, add any agent whose controls list includes it
  let changed = true;
  while (changed) {
    changed = false;
    for (const a of workforce) {
      if (selected.has(a.agent_type)) continue;
      const controls = Array.isArray(a.controls)
        ? a.controls
        : a.controls
        ? [a.controls]
        : [];
      if (controls.some((c) => selected.has(c))) {
        selected.add(a.agent_type);
        changed = true;
      }
    }
  }

  return selected;
}

function AgentBadges({ agent }: { agent: AvailableAgent }) {
  const controls = Array.isArray(agent.controls)
    ? agent.controls
    : agent.controls
    ? [agent.controls]
    : [];

  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {agent.essential && (
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-flag-critical/15 text-flag-critical border border-flag-critical/30">
          Essential
        </span>
      )}
      {agent.recommended && !agent.essential && (
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-flag-strength/15 text-flag-strength border border-flag-strength/30">
          Recommended
        </span>
      )}
      {controls.map((controlled) => (
        <span
          key={controlled}
          className="text-[10px] px-1.5 py-0.5 rounded-full bg-accent-gold/10 text-accent-gold border border-accent-gold/20"
        >
          Reviews {controlled}
        </span>
      ))}
    </div>
  );
}

interface DeptSelectionState {
  checked: boolean;
  expanded: boolean;
  agents: Set<string>;
}

export function AddDepartmentWizard({
  projectId,
  isOpen,
  onClose,
  onAdded,
}: AddDepartmentWizardProps) {
  const [step, setStep] = useState(1);
  const [available, setAvailable] = useState<AvailableDepartment[]>([]);
  const [loadingAvailable, setLoadingAvailable] = useState(true);
  const [deptStates, setDeptStates] = useState<Record<string, DeptSelectionState>>({});
  const [context, setContext] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const closeWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Fetch available departments on open
  useEffect(() => {
    if (!isOpen) return;
    setLoadingAvailable(true);
    setError("");
    api
      .getAvailableDepartments(projectId)
      .then((res) => {
        const depts = res.departments;
        setAvailable(depts);

        // Build initial selection state
        const states: Record<string, DeptSelectionState> = {};
        for (const dept of depts) {
          const preselected = computePreselected(dept.workforce);
          states[dept.department_type] = {
            checked: dept.recommended,
            expanded: dept.recommended,
            agents: preselected,
          };
        }
        setDeptStates(states);
      })
      .catch(() => setError("Failed to load available departments"))
      .finally(() => setLoadingAvailable(false));
  }, [isOpen, projectId]);

  // Reset on open
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setContext("");
      setSubmitting(false);
      setError("");
    }
    return () => closeWs();
  }, [isOpen, closeWs]);

  function toggleDept(deptType: string) {
    setDeptStates((prev) => {
      const cur = prev[deptType];
      if (!cur) return prev;
      const nowChecked = !cur.checked;
      return {
        ...prev,
        [deptType]: {
          ...cur,
          checked: nowChecked,
          expanded: nowChecked ? true : cur.expanded,
        },
      };
    });
  }

  function toggleExpand(deptType: string) {
    setDeptStates((prev) => {
      const cur = prev[deptType];
      if (!cur) return prev;
      return { ...prev, [deptType]: { ...cur, expanded: !cur.expanded } };
    });
  }

  function toggleAgent(deptType: string, agentType: string) {
    setDeptStates((prev) => {
      const cur = prev[deptType];
      if (!cur) return prev;
      const next = new Set(cur.agents);
      if (next.has(agentType)) {
        next.delete(agentType);
      } else {
        next.add(agentType);
      }
      return { ...prev, [deptType]: { ...cur, agents: next } };
    });
  }

  const selectedDepts = available.filter(
    (d) => deptStates[d.department_type]?.checked,
  );

  async function handleSubmit() {
    setSubmitting(true);
    setError("");
    try {
      await api.addDepartments(projectId, {
        departments: selectedDepts.map((d) => ({
          department_type: d.department_type,
          agents: Array.from(deptStates[d.department_type]?.agents ?? []),
        })),
        context: context.trim() || undefined,
      });

      try {
        const { connectWs } = await import("@/lib/ws");
        const ws = await connectWs(`/ws/project/${projectId}/`, (data) => {
          const eventType = data.type as string;
          if (eventType === "department.status" && data.status === "configured") {
            closeWs();
            onAdded();
            onClose();
          }
        });
        wsRef.current = ws;
      } catch {
        // WS failed — use fallback
      }

      setTimeout(() => {
        onAdded();
        onClose();
      }, 5000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add departments");
      setSubmitting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-bg-primary border border-border rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[min(700px,90vh)]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-accent-gold" />
            <span className="text-sm font-medium text-text-heading">
              {step === 1 ? "Select Departments & Agents" : "Additional Context"}
            </span>
            <span className="text-xs text-text-secondary">Step {step} of 2</span>
          </div>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {error && (
            <div className="flex items-center gap-2 text-flag-critical text-sm mb-4 p-3 rounded-lg bg-flag-critical/10">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Step 1: Departments + Agents */}
          {step === 1 && (
            <>
              {loadingAvailable ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-5 w-5 text-text-secondary animate-spin" />
                </div>
              ) : available.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <CheckCircle2 className="h-10 w-10 text-flag-strength/60" />
                  <p className="text-sm text-text-secondary">
                    All departments are already installed
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {available.map((dept) => {
                    const state = deptStates[dept.department_type];
                    if (!state) return null;
                    const isChecked = state.checked;
                    const isExpanded = state.expanded;

                    return (
                      <div
                        key={dept.department_type}
                        className={`rounded-lg border transition-colors ${
                          isChecked
                            ? "border-accent-gold bg-accent-gold/5"
                            : "border-border bg-bg-surface"
                        }`}
                      >
                        {/* Department header row */}
                        <div className="flex items-center gap-3 p-4">
                          <button
                            onClick={() => toggleDept(dept.department_type)}
                            className={`h-5 w-5 rounded border flex items-center justify-center shrink-0 transition-colors ${
                              isChecked
                                ? "bg-accent-gold border-accent-gold"
                                : "border-border bg-bg-input hover:border-accent-gold/50"
                            }`}
                          >
                            {isChecked && (
                              <CheckCircle2 className="h-3.5 w-3.5 text-bg-primary" />
                            )}
                          </button>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-text-heading">
                                {dept.name}
                              </p>
                              {dept.recommended && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-accent-gold/10 text-accent-gold border border-accent-gold/20">
                                  Recommended
                                </span>
                              )}
                            </div>
                            {dept.description && (
                              <p className="text-xs text-text-secondary mt-0.5 line-clamp-1">
                                {dept.description}
                              </p>
                            )}
                          </div>
                          {dept.workforce.length > 0 && isChecked && (
                            <button
                              onClick={() => toggleExpand(dept.department_type)}
                              className="text-text-secondary hover:text-text-primary transition-colors shrink-0"
                            >
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4" />
                              ) : (
                                <ChevronDown className="h-4 w-4" />
                              )}
                            </button>
                          )}
                        </div>

                        {/* Agent list */}
                        {isChecked && isExpanded && dept.workforce.length > 0 && (
                          <div className="border-t border-border/60 px-4 pb-3 pt-2 space-y-1.5">
                            <p className="text-[10px] uppercase text-text-secondary font-medium mb-2">
                              Workforce
                            </p>
                            {dept.workforce.map((agent) => {
                              const agentChecked = state.agents.has(agent.agent_type);
                              const isEssentialOrController =
                                agent.essential ||
                                (Array.isArray(agent.controls)
                                  ? agent.controls.some((c) => state.agents.has(c))
                                  : agent.controls
                                  ? state.agents.has(agent.controls)
                                  : false);
                              const showWarning =
                                !agentChecked && isEssentialOrController;

                              return (
                                <div key={agent.agent_type}>
                                  <button
                                    onClick={() =>
                                      toggleAgent(dept.department_type, agent.agent_type)
                                    }
                                    className={`w-full text-left flex items-start gap-2.5 rounded-md px-3 py-2 transition-colors ${
                                      agentChecked
                                        ? "bg-bg-primary/60"
                                        : "hover:bg-bg-primary/30"
                                    }`}
                                  >
                                    <div
                                      className={`h-4 w-4 rounded border flex items-center justify-center shrink-0 mt-0.5 transition-colors ${
                                        agentChecked
                                          ? "bg-accent-gold border-accent-gold"
                                          : "border-border bg-bg-input"
                                      }`}
                                    >
                                      {agentChecked && (
                                        <CheckCircle2 className="h-2.5 w-2.5 text-bg-primary" />
                                      )}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                      <p className="text-xs font-medium text-text-heading">
                                        {agent.name}
                                      </p>
                                      {agent.description && (
                                        <p className="text-[10px] text-text-secondary mt-0.5 line-clamp-2">
                                          {agent.description}
                                        </p>
                                      )}
                                      <AgentBadges agent={agent} />
                                    </div>
                                  </button>
                                  {showWarning && (
                                    <div className="flex items-center gap-1.5 mx-3 mt-1 mb-1 text-[10px] text-amber-400">
                                      <AlertTriangle className="h-3 w-3 shrink-0" />
                                      <span>
                                        {agent.essential
                                          ? "This agent is essential for the department to function."
                                          : "This agent reviews/controls another selected agent."}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}

          {/* Step 2: Context */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-text-secondary mb-3">
                  Adding:{" "}
                  {selectedDepts.map((d) => d.name).join(", ")}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-text-heading block mb-2">
                  Any specific context for these departments?
                </label>
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="e.g., We're launching a new product next month..."
                  rows={4}
                  className="w-full rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-none"
                />
                <p className="text-[10px] text-text-secondary mt-1">
                  Optional — helps tailor the department setup to your needs.
                </p>
              </div>

              {submitting && (
                <div className="flex items-center gap-3 p-4 rounded-lg bg-accent-gold/5 border border-accent-gold/20">
                  <Loader2 className="h-4 w-4 text-accent-gold animate-spin" />
                  <span className="text-sm text-text-primary">
                    Configuring departments...
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border shrink-0">
          {step === 1 && (
            <div className="flex justify-end">
              <Button
                onClick={() => setStep(2)}
                disabled={selectedDepts.length === 0}
                className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
              >
                Next
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
          {step === 2 && (
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setStep(1)}
                disabled={submitting}
                className="border-border text-text-secondary hover:text-text-primary"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={submitting}
                className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Configuring...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-1" />
                    Add Departments
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
