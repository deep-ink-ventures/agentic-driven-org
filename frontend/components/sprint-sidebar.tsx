// frontend/components/sprint-sidebar.tsx
"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Sprint } from "@/lib/types";
import { Pause, Play, Square, RotateCcw } from "lucide-react";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

interface SprintSidebarProps {
  sprints: Sprint[];
  onUpdate: () => void;
  projectId: string;
  onNavigateToDept: (departmentType: string) => void;
}

export function SprintSidebar({ sprints, onUpdate, projectId, onNavigateToDept }: SprintSidebarProps) {
  const [acting, setActing] = useState<string | null>(null);
  const [stopping, setStopping] = useState<Sprint | null>(null);
  const [resetting, setResetting] = useState<Sprint | null>(null);

  const active = sprints.filter((s) => s.status !== "done");
  const done = sprints.filter((s) => s.status === "done");

  async function updateStatus(e: React.MouseEvent, sprint: Sprint, newStatus: "running" | "paused" | "done") {
    e.stopPropagation();
    if (newStatus === "done") {
      setStopping(sprint);
      return;
    }
    setActing(sprint.id);
    try {
      await api.updateSprint(projectId, sprint.id, { status: newStatus });
      onUpdate();
    } finally {
      setActing(null);
    }
  }

  async function confirmStop() {
    if (!stopping) return;
    setActing(stopping.id);
    setStopping(null);
    try {
      await api.updateSprint(projectId, stopping.id, { status: "done" });
      onUpdate();
    } finally {
      setActing(null);
    }
  }

  async function confirmReset() {
    if (!resetting) return;
    setActing(resetting.id);
    setResetting(null);
    try {
      await api.resetSprint(projectId, resetting.id);
      onUpdate();
    } finally {
      setActing(null);
    }
  }

  if (active.length === 0 && done.length === 0) return null;

  return (
    <div className="px-2 py-2">
      {active.length > 0 && (
        <>
          <p className="text-[10px] uppercase text-text-secondary font-medium px-2 mb-2">
            Sprints
          </p>
          {active.map((sprint) => {
            const firstDept = sprint.departments[0];
            return (
              <div
                key={sprint.id}
                role="button"
                tabIndex={0}
                onClick={() => firstDept && onNavigateToDept(firstDept.department_type)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); firstDept && onNavigateToDept(firstDept.department_type); } }}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors mb-1 cursor-pointer ${
                  sprint.status === "running"
                    ? "border border-flag-strength/15 bg-flag-strength/4"
                    : "border border-border bg-bg-surface"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs truncate max-w-[120px] text-text-primary">
                    {sprint.text.length > 35 ? sprint.text.slice(0, 35) + "…" : sprint.text}
                  </span>
                  <div className="flex items-center gap-1 shrink-0 ml-1">
                    {sprint.status === "running" ? (
                      <button
                        onClick={(e) => updateStatus(e, sprint, "paused")}
                        disabled={acting === sprint.id}
                        className="p-0.5 rounded hover:bg-amber-500/20 text-text-secondary hover:text-amber-400 transition-colors"
                        title="Pause"
                      >
                        <Pause className="h-3 w-3" />
                      </button>
                    ) : (
                      <button
                        onClick={(e) => updateStatus(e, sprint, "running")}
                        disabled={acting === sprint.id}
                        className="p-0.5 rounded hover:bg-flag-strength/20 text-text-secondary hover:text-flag-strength transition-colors"
                        title="Resume"
                      >
                        <Play className="h-3 w-3" />
                      </button>
                    )}
                    <button
                      onClick={(e) => updateStatus(e, sprint, "done")}
                      disabled={acting === sprint.id}
                      className="p-0.5 rounded hover:bg-flag-critical/20 text-text-secondary hover:text-flag-critical transition-colors"
                      title="Stop sprint"
                    >
                      <Square className="h-2.5 w-2.5" />
                    </button>
                  </div>
                </div>
                <span className="block text-[9px] mt-0.5 text-text-secondary/60 truncate">
                  {sprint.departments.map((d) => d.display_name).join(" · ")}
                </span>
              </div>
            );
          })}
        </>
      )}

      {done.length > 0 && (
        <>
          <p className="text-[10px] uppercase text-text-secondary font-medium px-2 mb-2 mt-3">
            Completed
          </p>
          {done.map((sprint) => (
            <div
              key={sprint.id}
              className="w-full text-left px-3 py-2 rounded-lg transition-colors mb-1 border border-border bg-bg-surface opacity-60 hover:opacity-100"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs truncate max-w-[120px] text-text-secondary">
                  {sprint.text.length > 35 ? sprint.text.slice(0, 35) + "…" : sprint.text}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); setResetting(sprint); }}
                  disabled={acting === sprint.id}
                  className="p-0.5 rounded hover:bg-accent-violet/20 text-text-secondary hover:text-accent-violet transition-colors shrink-0 ml-1"
                  title="Reset &amp; restart"
                >
                  <RotateCcw className="h-3 w-3" />
                </button>
              </div>
              <span className="block text-[9px] mt-0.5 text-text-secondary/60 truncate">
                {sprint.departments.map((d) => d.display_name).join(" · ")}
              </span>
            </div>
          ))}
        </>
      )}

      <ConfirmDialog
        open={!!stopping}
        title="Stop sprint"
        description="This will mark the sprint as done. In-flight tasks will finish, but no new work will be created."
        confirmLabel="Stop sprint"
        cancelLabel="Keep running"
        variant="danger"
        onConfirm={confirmStop}
        onCancel={() => setStopping(null)}
      />
      <ConfirmDialog
        open={!!resetting}
        title="Reset &amp; restart sprint"
        description="This will delete all tasks, documents, and outputs from this sprint and restart it from scratch. This cannot be undone."
        confirmLabel="Reset &amp; restart"
        cancelLabel="Cancel"
        variant="danger"
        onConfirm={confirmReset}
        onCancel={() => setResetting(null)}
      />
    </div>
  );
}
