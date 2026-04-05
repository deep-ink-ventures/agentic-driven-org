"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { AgentTask } from "@/lib/types";
import {
  Loader2,
  Check,
  X,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Pencil,
  Clock,
  Filter,
  RefreshCw,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/* ------------------------------------------------------------------ */
/*  Status badge colours                                              */
/* ------------------------------------------------------------------ */

const statusColors: Record<AgentTask["status"], string> = {
  awaiting_approval:
    "bg-accent-violet/15 text-accent-violet border-accent-violet/30",
  awaiting_dependencies: "bg-bg-surface text-text-secondary border-border",
  planned: "bg-bg-surface text-text-secondary border-border",
  queued: "bg-bg-surface text-text-secondary border-border",
  processing: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  done: "bg-flag-strength/15 text-flag-strength border-flag-strength/30",
  failed: "bg-flag-critical/15 text-flag-critical border-flag-critical/30",
};

const statusLabels: Record<AgentTask["status"], string> = {
  awaiting_approval: "needs approval",
  awaiting_dependencies: "waiting",
  planned: "planned",
  queued: "queued",
  processing: "processing",
  done: "done",
  failed: "failed",
};

/* ------------------------------------------------------------------ */
/*  TaskCard (moved from page.tsx — unchanged)                        */
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
  const [showPlan, setShowPlan] = useState(false);
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

  async function handleRetry() {
    setActing(true);
    try {
      const updated = await api.retryTask(projectId, task.id);
      onUpdate(updated);
    } finally {
      setActing(false);
    }
  }

  return (
    <div className="border border-border rounded-lg bg-bg-surface">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-3 px-3 sm:px-4 py-2.5 sm:py-3 text-left"
      >
        <div className="flex items-center gap-2 sm:contents">
          <span
            className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full border ${statusColors[task.status]}`}
          >
            {statusLabels[task.status]}
          </span>
          <span className="text-xs text-text-secondary shrink-0">
            {task.agent_name}
          </span>
          <span className="text-xs text-text-secondary shrink-0 ml-auto sm:hidden">
            {new Date(task.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
        <span className="text-sm text-text-primary truncate flex-1">
          {editing ? editedSummary : task.exec_summary}
        </span>
        <span className="text-xs text-text-secondary shrink-0 hidden sm:inline">
          {new Date(task.created_at).toLocaleTimeString()}
        </span>
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5 text-text-secondary hidden sm:block" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-text-secondary hidden sm:block" />
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

          {/* Plan — toggle visibility, editable for approval tasks */}
          {(task.step_plan || editing) && (
            <div>
              {!editing && (
                <button
                  onClick={() => setShowPlan(!showPlan)}
                  className="text-xs text-text-secondary hover:text-text-primary transition-colors flex items-center gap-1 mb-2"
                >
                  {showPlan ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  {showPlan ? "Hide plan" : "Show plan"}
                </button>
              )}
              {(showPlan || editing) && (
                editing ? (
                  <textarea
                    value={editedPlan}
                    onChange={(e) => setEditedPlan(e.target.value)}
                    rows={Math.max(6, editedPlan.split("\n").length + 2)}
                    className="w-full rounded-lg border border-border bg-bg-input px-3 py-2 text-xs text-text-primary font-mono outline-none focus-visible:border-accent-violet focus-visible:ring-1 focus-visible:ring-accent-violet/50 resize-y"
                  />
                ) : (
                  <div
                    onClick={isApproval ? () => setEditing(true) : undefined}
                    className={`rounded-lg border border-dashed border-border p-3 text-sm text-text-primary max-w-none [&_p]:mb-2 [&_ul]:mb-2 [&_ol]:mb-2 [&_li]:mb-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&>*:last-child]:mb-0 ${isApproval ? "cursor-pointer hover:border-accent-violet/40 transition-colors" : ""}`}
                  >
                    <ReactMarkdown>{task.step_plan}</ReactMarkdown>
                  </div>
                )
              )}
            </div>
          )}

          {/* Report — read only */}
          {task.report && (
            <div>
              <p className="text-xs text-text-secondary mb-1">Report</p>
              <div className="text-xs text-text-primary bg-bg-input rounded-lg p-3 border border-border prose prose-invert prose-xs max-w-none prose-headings:text-text-primary prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1 prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-pre:bg-bg-surface prose-pre:border prose-pre:border-border">
                <ReactMarkdown>{task.report}</ReactMarkdown>
              </div>
            </div>
          )}
          {task.error_message && (
            <div className="flex items-start justify-between gap-2 text-flag-critical text-xs p-2 rounded-lg bg-flag-critical/10">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                <span>{task.error_message}</span>
              </div>
              {task.status === "failed" && (
                <Button
                  size="sm"
                  onClick={handleRetry}
                  disabled={acting}
                  className="shrink-0 bg-accent-gold text-bg-primary hover:bg-accent-gold-hover text-xs h-6 px-2"
                >
                  <RefreshCw className="h-3 w-3 mr-1" /> Retry
                </Button>
              )}
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

          {/* Blocker info for awaiting_dependencies tasks */}
          {task.status === "awaiting_dependencies" && task.blocked_by_summary && (
            <div className="flex items-center gap-2 text-xs text-text-secondary p-2 rounded-lg bg-bg-input">
              <Clock className="h-3.5 w-3.5 shrink-0" />
              <span>Blocked by: {task.blocked_by_summary}</span>
            </div>
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
/*  TaskLane                                                          */
/* ------------------------------------------------------------------ */

interface LaneConfig {
  title: string;
  statuses: string;
  collapsible?: boolean;
  pulse?: boolean;
}

function TaskLane({
  config,
  projectId,
  department,
  agent,
  wsEvent,
}: {
  config: LaneConfig;
  projectId: string;
  department?: string;
  agent?: string;
  wsEvent?: { type: string; task: AgentTask } | null;
}) {
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [expanded, setExpanded] = useState(!config.collapsible);
  const [hasFetched, setHasFetched] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const statusOptions = config.statuses.split(",");
  const activeStatuses = statusFilter || config.statuses;

  const fetchTasks = useCallback(
    async (before?: string) => {
      const page = await api.getProjectTasks(projectId, {
        status: activeStatuses,
        department,
        agent,
        limit: 25,
        before,
      });
      return page;
    },
    [projectId, activeStatuses, department, agent],
  );

  // Defer fetch for collapsible lanes until first expand
  useEffect(() => {
    if (!expanded && !hasFetched) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setHasFetched(true);
    fetchTasks().then((page) => {
      setTasks(page.tasks);
      setTotalCount(page.totalCount);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [fetchTasks, expanded]);

  // Handle WebSocket task events
  const prevWsEvent = useRef(wsEvent);
  useEffect(() => {
    if (!wsEvent || wsEvent === prevWsEvent.current) return;
    prevWsEvent.current = wsEvent;

    const task = wsEvent.task;
    const laneStatuses = config.statuses.split(",");
    const belongsInLane =
      laneStatuses.includes(task.status) &&
      (!department || task.agent === department) &&
      (!agent || task.agent === agent);

    if (wsEvent.type === "task.created") {
      if (belongsInLane) {
        setTasks((prev) => {
          if (prev.some((t) => t.id === task.id)) return prev;
          return [task, ...prev];
        });
        setTotalCount((prev) => prev + 1);
      }
    } else if (wsEvent.type === "task.updated") {
      const wasInLane = tasks.some((t) => t.id === task.id);
      if (wasInLane && !belongsInLane) {
        // Task moved out of this lane
        setTasks((prev) => prev.filter((t) => t.id !== task.id));
        setTotalCount((prev) => Math.max(0, prev - 1));
      } else if (wasInLane && belongsInLane) {
        // Task updated within this lane
        setTasks((prev) => prev.map((t) => (t.id === task.id ? task : t)));
      } else if (!wasInLane && belongsInLane) {
        // Task moved into this lane from another
        setTasks((prev) => [task, ...prev]);
        setTotalCount((prev) => prev + 1);
      }
    }
  }, [wsEvent, config.statuses, department, agent, tasks]);

  async function loadMore() {
    if (tasks.length === 0) return;
    setLoadingMore(true);
    try {
      const oldest = tasks[tasks.length - 1].created_at;
      const page = await fetchTasks(oldest);
      setTasks((prev) => [...prev, ...page.tasks]);
    } finally {
      setLoadingMore(false);
    }
  }

  function handleTaskUpdate(updated: AgentTask) {
    // If the task's status no longer belongs in this lane, remove it
    const laneStatuses = activeStatuses.split(",");
    if (!laneStatuses.includes(updated.status)) {
      setTasks((prev) => prev.filter((t) => t.id !== updated.id));
      setTotalCount((prev) => Math.max(0, prev - 1));
    } else {
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    }
  }

  const hasMore = tasks.length < totalCount;

  return (
    <div className="flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={config.collapsible ? () => setExpanded(!expanded) : undefined}
          className={`flex items-center gap-2 ${config.collapsible ? "cursor-pointer hover:text-text-primary" : "cursor-default"}`}
        >
          {config.collapsible && (
            expanded
              ? <ChevronUp className="h-4 w-4 text-text-secondary" />
              : <ChevronDown className="h-4 w-4 text-text-secondary" />
          )}
          <h3 className="text-sm font-medium text-text-heading">{config.title}</h3>
          <span className={`text-xs px-1.5 py-0.5 rounded-full border text-text-secondary ${config.pulse && totalCount > 0 ? "bg-blue-500/15 border-blue-500/30 text-blue-400 animate-pulse" : "bg-bg-input border-border"}`}>
            {totalCount}
          </span>
        </button>

        {/* Status filter */}
        {statusOptions.length > 1 && expanded && (
          <div className="flex items-center gap-1">
            <Filter className="h-3 w-3 text-text-secondary" />
            <select
              value={statusFilter || ""}
              onChange={(e) => setStatusFilter(e.target.value || null)}
              className="text-xs bg-bg-input border border-border rounded px-1.5 py-0.5 text-text-secondary outline-none focus:border-accent-violet"
            >
              <option value="">All</option>
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {statusLabels[s as AgentTask["status"]] || s.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Task list */}
      {expanded && (
        <>
          {loading ? (
            <div className="flex justify-center py-6">
              <Loader2 className="h-4 w-4 text-text-secondary animate-spin" />
            </div>
          ) : tasks.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border py-6 px-4 text-center">
              <p className="text-text-secondary text-xs">
                No tasks yet — your agents will create tasks as they work.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  projectId={projectId}
                  onUpdate={handleTaskUpdate}
                />
              ))}
              {hasMore && (
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="w-full text-xs text-text-secondary hover:text-text-primary py-2 transition-colors flex items-center justify-center gap-1"
                >
                  {loadingMore ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    `Load more (${totalCount - tasks.length} remaining)`
                  )}
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  TaskQueue — main exported component                               */
/* ------------------------------------------------------------------ */

export function TaskQueue({
  projectId,
  department,
  agent,
  wsEvent,
}: {
  projectId: string;
  department?: string;
  agent?: string;
  wsEvent?: { type: string; task: AgentTask } | null;
}) {
  return (
    <div>

      {/* Two lanes side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <TaskLane
          config={{ title: "Needs Attention", statuses: "awaiting_approval,failed" }}
          projectId={projectId}
          department={department}
          agent={agent}
          wsEvent={wsEvent}
        />
        <TaskLane
          config={{ title: "In Progress", statuses: "queued,processing,awaiting_dependencies,planned", pulse: true }}
          projectId={projectId}
          department={department}
          agent={agent}
          wsEvent={wsEvent}
        />
      </div>

      {/* Collapsed completed stack */}
      <TaskLane
        config={{ title: "Completed", statuses: "done", collapsible: true }}
        projectId={projectId}
        department={department}
        agent={agent}
        wsEvent={wsEvent}
      />
    </div>
  );
}
