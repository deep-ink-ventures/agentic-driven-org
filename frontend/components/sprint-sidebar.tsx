// frontend/components/sprint-sidebar.tsx
"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Sprint } from "@/lib/types";
import { Pause, Play, Check } from "lucide-react";

interface SprintSidebarProps {
  sprints: Sprint[];
  onUpdate: () => void;
  projectId: string;
  onNavigateToDept: (departmentType: string) => void;
}

export function SprintSidebar({ sprints, onUpdate, projectId, onNavigateToDept }: SprintSidebarProps) {
  const [acting, setActing] = useState<string | null>(null);

  const visible = sprints.filter((s) => s.status !== "done");

  async function updateStatus(e: React.MouseEvent, sprint: Sprint, newStatus: "running" | "paused" | "done") {
    e.stopPropagation();
    setActing(sprint.id);
    try {
      await api.updateSprint(projectId, sprint.id, { status: newStatus });
      onUpdate();
    } finally {
      setActing(null);
    }
  }

  if (visible.length === 0) return null;

  return (
    <div className="px-2 py-2">
      <p className="text-[10px] uppercase text-text-secondary font-medium px-2 mb-2">
        Sprints
      </p>
      {visible.map((sprint) => {
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
                  className="p-0.5 rounded hover:bg-flag-strength/20 text-text-secondary hover:text-flag-strength transition-colors"
                  title="Mark done"
                >
                  <Check className="h-3 w-3" />
                </button>
              </div>
            </div>
            <span className="block text-[9px] mt-0.5 text-text-secondary/60 truncate">
              {sprint.departments.map((d) => d.display_name).join(" · ")}
            </span>
          </div>
        );
      })}
    </div>
  );
}
