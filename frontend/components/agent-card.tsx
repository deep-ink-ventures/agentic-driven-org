"use client";

import { CheckCircle, ToggleLeft, ToggleRight } from "lucide-react";
import type { AgentSummary } from "@/lib/types";

export function AgentCard({
  agent,
  onClick,
  onToggle,
  onToggleAutoApprove,
}: {
  agent: AgentSummary;
  onClick: () => void;
  onToggle?: () => void;
  onToggleAutoApprove?: () => void;
}) {
  const clickable = agent.status === "active" || agent.status === "inactive";
  const toggleable = agent.status === "active" || agent.status === "inactive";
  return (
    <div
      onClick={clickable ? onClick : undefined}
      className={`w-full text-left border border-border rounded-lg bg-bg-surface transition-colors p-4 group ${clickable ? "hover:border-accent-violet/50 cursor-pointer" : "opacity-60 cursor-default"}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-text-heading group-hover:text-accent-violet transition-colors truncate mr-2">
          {agent.name}
        </span>
        <div className="flex items-center gap-2 shrink-0">
          {agent.status === "provisioning" && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/15 text-blue-400 animate-pulse">
              Provisioning
            </span>
          )}
          {agent.status === "failed" && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-flag-critical/15 text-flag-critical">
              Failed
            </span>
          )}
          {toggleable && onToggle && (
            <button
              onClick={(e) => { e.stopPropagation(); onToggle(); }}
              className={`transition-colors ${agent.status === "active" ? "text-flag-strength" : "text-text-secondary/40 hover:text-flag-strength"}`}
              title={agent.status === "active" ? "Deactivate" : "Activate"}
            >
              {agent.status === "active" ? (
                <ToggleRight className="h-5 w-5" />
              ) : (
                <ToggleLeft className="h-5 w-5" />
              )}
            </button>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between mt-2">
        {agent.pending_task_count > 0 ? (
          <p className="text-xs text-accent-violet">
            {agent.pending_task_count} pending task{agent.pending_task_count !== 1 ? "s" : ""}
          </p>
        ) : <div />}
        {toggleable && onToggleAutoApprove && (
          <button
            onClick={(e) => { e.stopPropagation(); onToggleAutoApprove(); }}
            className={`flex items-center gap-1 text-[10px] transition-colors ${agent.auto_approve ? "text-accent-violet" : "text-text-secondary/50 hover:text-accent-violet"}`}
            title={agent.auto_approve ? "Disable auto-approve" : "Enable auto-approve"}
          >
            <CheckCircle className="h-3 w-3" />
            <span>Auto</span>
          </button>
        )}
      </div>
    </div>
  );
}
