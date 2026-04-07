"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useProjectWebSocket } from "@/lib/useProjectWebSocket";
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
  Copy,
  Check,
  RefreshCw,
} from "lucide-react";
import { Separator } from "@/components/ui/separator";
import ReactMarkdown from "react-markdown";

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

    if (deptSlug === "settings") {
      setView("settings");
    } else if (deptSlug) {
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

  // Refs for WS callback to read current state without re-creating the callback
  const projectRef = useRef(project);
  projectRef.current = project;
  const projectIdRef = useRef<string | null>(null);
  projectIdRef.current = project?.id ?? null;

  // WebSocket for real-time updates
  useProjectWebSocket(project?.id ?? null, (data) => {
    if (data.type === "task.created" || data.type === "task.updated") {
      const task = data.task as import("@/lib/types").AgentTask;
      setTaskWsEvent({ type: data.type, task });

      // Update activeTasks map using project ref (not setState-as-reader)
      const currentProject = projectRef.current;
      if (currentProject) {
        const agentId = task.agent;
        const dept = currentProject.departments.find((d) =>
          d.agents.some((a) => a.id === agentId),
        );
        if (dept) {
          const deptId = dept.id;
          const isActive = task.status === "processing" || task.status === "queued";
          setActiveTasks((prevMap) => {
            const deptTasks = prevMap.get(deptId);
            const hadTask = deptTasks?.has(task.id) ?? false;
            if (isActive && hadTask) return prevMap;
            if (!isActive && !hadTask) return prevMap;
            const next = new Map(prevMap);
            const updated = new Set(deptTasks);
            if (isActive) {
              updated.add(task.id);
            } else {
              updated.delete(task.id);
            }
            if (updated.size > 0) {
              next.set(deptId, updated);
            } else {
              next.delete(deptId);
            }
            return next;
          });
        }
      }
    }
    if (data.type === "sprint.created" || data.type === "sprint.updated") {
      const pid = projectIdRef.current;
      if (pid) {
        api.listSprints(pid, { status: "running,paused" }).then(setSprints).catch(() => {});
      }
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
  });

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
    type SettingsTab = "overview" | "integrations";
    const validSettingsTabs: SettingsTab[] = ["overview", "integrations"];

    function settingsTabFromHash(): SettingsTab {
      if (typeof window === "undefined") return "overview";
      const h = window.location.hash.replace("#", "");
      return validSettingsTabs.includes(h as SettingsTab) ? (h as SettingsTab) : "overview";
    }

    const [settingsTab, setSettingsTabState] = useState<SettingsTab>(settingsTabFromHash);
    const [pairingToken, setPairingToken] = useState<string | null>(null);
    const [tokenLoading, setTokenLoading] = useState(false);
    const [copied, setCopied] = useState(false);

    const setSettingsTab = useCallback((t: SettingsTab) => {
      setSettingsTabState(t);
      window.history.replaceState(null, "", `#${t}`);
    }, []);

    useEffect(() => {
      function onHashChange() { setSettingsTabState(settingsTabFromHash()); }
      window.addEventListener("hashchange", onHashChange);
      return () => window.removeEventListener("hashchange", onHashChange);
    }, []);

    async function generateToken() {
      setTokenLoading(true);
      try {
        const res = await api.generateExtensionToken(projectSlug!);
        setPairingToken(res.token);
      } catch {
        // silently fail — user can retry
      } finally {
        setTokenLoading(false);
      }
    }

    function copyToken() {
      if (!pairingToken) return;
      navigator.clipboard.writeText(pairingToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }

    const tabClass = (t: SettingsTab) =>
      `px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
        settingsTab === t
          ? "border-accent-violet text-accent-violet"
          : "border-transparent text-text-secondary hover:text-text-primary"
      }`;

    return (
      <div>
        <h2 className="text-2xl font-semibold mb-4">Project Settings</h2>
        <div className="flex gap-1 border-b border-border mb-6">
          <button onClick={() => setSettingsTab("overview")} className={tabClass("overview")}>
            Overview
          </button>
          <button onClick={() => setSettingsTab("integrations")} className={tabClass("integrations")}>
            Integrations
          </button>
        </div>

        {settingsTab === "overview" && (
          <div className="space-y-6">
            <div className="rounded-lg border border-border bg-bg-surface p-6">
              <h3 className="text-lg font-semibold text-text-heading">{project!.name}</h3>
              {project!.goal && (
                <div className="mt-3 text-sm text-text-primary leading-relaxed prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{project!.goal}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        )}

        {settingsTab === "integrations" && (
          <div className="space-y-6">
            <div className="rounded-lg border border-border bg-bg-surface p-6">
              <h3 className="text-lg font-semibold text-text-heading">Chrome Extension</h3>
              <p className="mt-2 text-sm text-text-secondary">
                Pair the Chrome extension with this project to sync browser sessions for your agents.
              </p>

              <div className="mt-5 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-text-secondary uppercase tracking-wide mb-1.5">
                    Backend URL
                  </label>
                  <code className="block rounded-md border border-border bg-bg-base px-3 py-2 text-sm font-mono text-text-primary select-all">
                    {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
                  </code>
                </div>

                {!pairingToken ? (
                  <button
                    onClick={generateToken}
                    disabled={tokenLoading}
                    className="inline-flex items-center gap-2 rounded-md bg-accent-violet px-4 py-2 text-sm font-medium text-white hover:bg-accent-violet/90 disabled:opacity-50 transition-colors"
                  >
                    {tokenLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4" />
                    )}
                    Generate Pairing Code
                  </button>
                ) : (
                  <div className="space-y-3">
                    <label className="block text-xs font-medium text-text-secondary uppercase tracking-wide">
                      Pairing Code
                    </label>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 rounded-md border border-border bg-bg-base px-3 py-2 text-sm font-mono text-text-primary break-all select-all">
                        {pairingToken}
                      </code>
                      <button
                        onClick={copyToken}
                        className="shrink-0 rounded-md border border-border p-2 text-text-secondary hover:text-text-primary hover:bg-bg-surface-hover transition-colors"
                        title="Copy to clipboard"
                      >
                        {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
                      </button>
                    </div>
                    <p className="text-xs text-text-secondary">
                      Paste this code into the Chrome extension popup. Expires in 24 hours.
                    </p>
                    <button
                      onClick={generateToken}
                      disabled={tokenLoading}
                      className="inline-flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors"
                    >
                      {tokenLoading ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                      Regenerate
                    </button>
                  </div>
                )}
              </div>
            </div>
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
          onNavigateToDept={(deptType) => {
            const dept = project!.departments.find((d) => d.department_type === deptType);
            if (dept) {
              const alreadyOnDept = selectedDept?.id === dept.id && view === "department";
              setSelectedDept(dept);
              setSelectedAgent(null);
              setView("department");
              setSidebarOpen(false);
              if (alreadyOnDept) {
                window.location.hash = "#sprints";
              } else {
                router.push(`/project/${projectSlug}/${deptType}#sprints`);
              }
            }
          }}
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
