"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { connectWs } from "@/lib/ws";
import type {
  ProjectDetail,
  AgentSummary,
  DepartmentDetail,
  Sprint,
} from "@/lib/types";
import { AddDepartmentWizard } from "@/components/add-department-wizard";
import Logomark from "@/components/logomark";
import { TaskQueue } from "@/components/task-queue";
import { SprintSidebar } from "@/components/sprint-sidebar";
import { DepartmentView } from "@/components/department-view";
import { AgentDetailView } from "@/components/agent-detail-view";
import {
  Loader2,
  LayoutDashboard,
  Settings2,
  Plus,
  Menu,
  X,
} from "lucide-react";
import { Separator } from "@/components/ui/separator";

function slugifyName(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
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
  const [taskWsEvent, setTaskWsEvent] = useState<{ type: string; task: import("@/lib/types").AgentTask } | null>(null);
  // Map of department ID → set of active task IDs (processing/queued)
  const [activeTasks, setActiveTasks] = useState<Map<string, Set<string>>>(new Map());
  const [sprints, setSprints] = useState<Sprint[]>([]);

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
        api.listSprints(proj.id, { status: "running,paused" }).then(setSprints).catch(() => {});
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
      if (data.type === "task.created" || data.type === "task.updated") {
        const task = data.task as import("@/lib/types").AgentTask;
        setTaskWsEvent({ type: data.type, task });
        // Track which departments have active tasks via a map of dept → active task count
        const agentId = task.agent;
        setProject((prev) => {
          if (!prev) return prev;
          const dept = prev.departments.find((d) => d.agents.some((a) => a.id === agentId));
          if (dept) {
            setActiveTasks((prevMap) => {
              const next = new Map(prevMap);
              const isActive = task.status === "processing" || task.status === "queued";
              const deptTasks = next.get(dept.id) || new Set<string>();
              const updated = new Set(deptTasks);
              if (isActive) {
                updated.add(task.id);
              } else {
                updated.delete(task.id);
              }
              if (updated.size > 0) {
                next.set(dept.id, updated);
              } else {
                next.delete(dept.id);
              }
              return next;
            });
          }
          return prev;
        });
      }
      if (data.type === "sprint.created" || data.type === "sprint.updated") {
        api.listSprints(project!.id, { status: "running,paused" }).then(setSprints).catch(() => {});
      }
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

  // Derive department status — always returns a value
  function getDeptStatus(dept: DepartmentDetail): "working" | "setup" | "provisioning" | "ready" | "idle" {
    // Setup: JSON Schema has top-level "required" array — check if any are missing from config
    const schema = dept.config_schema as { required?: string[]; properties?: Record<string, unknown> } | undefined;
    if (schema?.required && schema.required.length > 0) {
      const config = (dept.config || {}) as Record<string, unknown>;
      const missingRequired = schema.required.some(
        (key) => config[key] === undefined || config[key] === null || config[key] === "",
      );
      if (missingRequired) return "setup";
    }
    // Provisioning: at least one agent still being set up
    if (dept.agents.some((a) => a.status === "provisioning")) return "provisioning";
    // Working: at least one active task in this department
    if (activeTasks.has(dept.id)) return "working";
    // Ready: at least one agent is active
    if (dept.agents.some((a) => a.status === "active")) return "ready";
    // Idle: all agents inactive or failed
    return "idle";
  }

  function SettingsView({ projectId: pid }: { projectId: string }) {
    const [allSprints, setAllSprints] = useState<Sprint[]>([]);
    const [settingsTab, setSettingsTab] = useState<"general" | "history">("general");

    useEffect(() => {
      if (settingsTab === "history") {
        api.listSprints(pid).then(setAllSprints).catch(() => {});
      }
    }, [pid, settingsTab]);

    return (
      <div>
        <h2 className="text-2xl font-semibold mb-4">Project Settings</h2>
        <div className="flex gap-1 border-b border-border mb-6">
          <button
            onClick={() => setSettingsTab("general")}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
              settingsTab === "general"
                ? "border-accent-violet text-accent-violet"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            General
          </button>
          <button
            onClick={() => setSettingsTab("history")}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
              settingsTab === "history"
                ? "border-accent-violet text-accent-violet"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            Sprint History
          </button>
        </div>
        {settingsTab === "general" && (
          <div className="rounded-lg border border-border bg-bg-surface p-6">
            <p className="text-sm text-text-secondary">
              Project configuration coming soon.
            </p>
          </div>
        )}
        {settingsTab === "history" && (
          <div className="space-y-3">
            {allSprints.length === 0 ? (
              <p className="text-sm text-text-secondary">No sprints yet.</p>
            ) : (
              allSprints.map((sprint) => (
                <div key={sprint.id} className="rounded-lg border border-border bg-bg-surface p-4">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-text-heading">{sprint.text}</span>
                    <span
                      className={`text-[10px] font-medium uppercase px-2 py-0.5 rounded-full ${
                        sprint.status === "running"
                          ? "bg-flag-strength/15 text-flag-strength"
                          : sprint.status === "paused"
                            ? "bg-amber-500/15 text-amber-400"
                            : "bg-bg-input text-text-secondary"
                      }`}
                    >
                      {sprint.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-text-secondary">
                    <span>{sprint.departments.map((d) => d.display_name).join(", ")}</span>
                    <span>{new Date(sprint.created_at).toLocaleDateString()}</span>
                    <span>{sprint.task_count} tasks</span>
                  </div>
                  {sprint.completion_summary && (
                    <p className="mt-2 text-xs text-text-secondary border-t border-border pt-2">
                      {sprint.completion_summary}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}
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
            ? "text-accent-violet bg-accent-violet/10"
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
          const deptStatus = getDeptStatus(dept);
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
                  ? "bg-accent-violet/10 text-accent-violet"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-surface-hover"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm">{dept.display_name}</span>
                <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${
                  deptStatus === "setup" ? "bg-flag-critical" :
                  deptStatus === "provisioning" ? "bg-blue-400 animate-pulse" :
                  deptStatus === "working" ? "bg-flag-strength animate-pulse" :
                  deptStatus === "ready" ? "bg-flag-strength" :
                  "bg-text-secondary/30"
                }`} title={deptStatus} />
              </div>
              <span className="block text-[10px] mt-0.5 opacity-60">
                {activeCount}/{totalCount} agents active
              </span>
            </button>
          );
        })}
      </div>
      {sprints.length > 0 && (
        <SprintSidebar
          sprints={sprints}
          onUpdate={() => {
            api.listSprints(project!.id, { status: "running,paused" }).then(setSprints).catch(() => {});
          }}
          projectId={project.id}
        />
      )}
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
              ? "text-accent-violet bg-accent-violet/10"
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
        className="md:hidden fixed bottom-4 right-4 z-40 h-12 w-12 rounded-full bg-accent-violet text-white flex items-center justify-center shadow-lg active:scale-95 transition-transform"
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
              <span className="flex items-center gap-2 font-serif text-sm text-accent-violet font-bold">
                <Logomark size={18} className="text-accent-violet" />
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
          <>
            <h2 className="text-2xl font-semibold mb-1">Task Queue</h2>
            <p className="text-sm text-text-secondary mb-6">Monitor and manage your agents&apos; work</p>
            <TaskQueue
              projectId={project.id}
              wsEvent={taskWsEvent}
              departments={project.departments}
              onSprintCreated={() => {
                api.listSprints(project!.id, { status: "running,paused" }).then(setSprints).catch(() => {});
              }}
            />
          </>
        )}
        {view === "department" && selectedDept && !selectedAgent && (
          <DepartmentView
            dept={selectedDept}
            projectId={project.id}
            deptStatus={getDeptStatus(selectedDept)}
            onSelectAgent={(agent) => {
              setSelectedAgent(agent);
              setView("agent");
              router.push(`/project/${projectSlug}/${selectedDept.department_type}/${slugifyName(agent.name)}`);
            }}
            onRefresh={load}
            taskWsEvent={taskWsEvent}
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
            taskWsEvent={taskWsEvent}
          />
        )}
        {view === "settings" && (
          <SettingsView projectId={project.id} />
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
