// frontend/components/sprint-sidebar.tsx
"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Sprint } from "@/lib/types";
import { Pause, Play, Check, X } from "lucide-react";

interface SprintSidebarProps {
  sprints: Sprint[];
  onUpdate: () => void;
  projectId: string;
}

export function SprintSidebar({ sprints, onUpdate, projectId }: SprintSidebarProps) {
  const [popoverId, setPopoverId] = useState<string | null>(null);
  const [acting, setActing] = useState(false);

  const visible = sprints.filter((s) => s.status !== "done");

  async function updateStatus(sprint: Sprint, newStatus: "running" | "paused" | "done") {
    setActing(true);
    try {
      await api.updateSprint(projectId, sprint.id, { status: newStatus });
      onUpdate();
      setPopoverId(null);
    } finally {
      setActing(false);
    }
  }

  if (visible.length === 0) return null;

  return (
    <div className="px-2 py-2">
      <p className="text-[10px] uppercase text-text-secondary font-medium px-2 mb-2">
        Sprints
      </p>
      {visible.map((sprint) => (
        <div key={sprint.id} className="relative mb-1">
          <button
            onClick={() => setPopoverId(popoverId === sprint.id ? null : sprint.id)}
            className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
              sprint.status === "running"
                ? "border border-flag-strength/15 bg-flag-strength/4"
                : "border border-border bg-bg-surface"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs truncate max-w-[140px] text-text-primary">
                {sprint.text.length > 35 ? sprint.text.slice(0, 35) + "…" : sprint.text}
              </span>
              <div className="flex items-center gap-1 shrink-0 ml-2">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    sprint.status === "running" ? "bg-flag-strength animate-pulse" : "bg-text-secondary/30"
                  }`}
                />
                <span
                  className={`text-[9px] ${
                    sprint.status === "running" ? "text-flag-strength" : "text-text-secondary/50"
                  }`}
                >
                  {sprint.status}
                </span>
              </div>
            </div>
            <span className="block text-[9px] mt-0.5 text-text-secondary/60 truncate">
              {sprint.departments.map((d) => d.display_name).join(" · ")}
            </span>
          </button>

          {/* Popover */}
          {popoverId === sprint.id && (
            <div className="absolute left-0 right-0 top-full mt-1 z-50 rounded-lg border border-border bg-bg-surface shadow-lg p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-text-heading">{sprint.text}</span>
                <button
                  onClick={() => setPopoverId(null)}
                  className="text-text-secondary hover:text-text-primary"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
              <p className="text-[10px] text-text-secondary mb-3">
                {sprint.departments.map((d) => d.display_name).join(" · ")} ·{" "}
                {new Date(sprint.created_at).toLocaleDateString()}
              </p>
              <div className="flex gap-1.5">
                {sprint.status === "running" ? (
                  <button
                    onClick={() => updateStatus(sprint, "paused")}
                    disabled={acting}
                    className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-[10px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30 hover:bg-amber-500/25 transition-colors"
                  >
                    <Pause className="h-3 w-3" /> Pause
                  </button>
                ) : (
                  <button
                    onClick={() => updateStatus(sprint, "running")}
                    disabled={acting}
                    className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-[10px] font-semibold bg-flag-strength/10 text-flag-strength border border-flag-strength/20 hover:bg-flag-strength/20 transition-colors"
                  >
                    <Play className="h-3 w-3" /> Resume
                  </button>
                )}
                <button
                  onClick={() => updateStatus(sprint, "done")}
                  disabled={acting}
                  className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-[10px] font-semibold bg-flag-strength/10 text-flag-strength border border-flag-strength/20 hover:bg-flag-strength/20 transition-colors"
                >
                  <Check className="h-3 w-3" /> Done
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
