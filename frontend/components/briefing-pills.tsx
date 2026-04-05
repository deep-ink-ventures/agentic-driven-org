"use client";

import { useState } from "react";
import type { Briefing } from "@/lib/types";
import { X, Plus, ChevronDown, ChevronUp, Paperclip } from "lucide-react";

interface BriefingPillsProps {
  projectId: string;
  briefings: Briefing[];
  onArchive: (id: string) => void;
  onNewBriefing: () => void;
}

export function BriefingPills({ briefings, onArchive, onNewBriefing }: BriefingPillsProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [confirmArchiveId, setConfirmArchiveId] = useState<string | null>(null);

  function handleArchiveClick(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    if (confirmArchiveId === id) {
      onArchive(id);
      setConfirmArchiveId(null);
      if (expandedId === id) setExpandedId(null);
    } else {
      setConfirmArchiveId(id);
      // Auto-clear confirmation after 3s
      setTimeout(() => setConfirmArchiveId((prev) => (prev === id ? null : prev)), 3000);
    }
  }

  function truncate(text: string, max: number) {
    if (text.length <= max) return text;
    return text.slice(0, max) + "...";
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {briefings.map((b) => (
          <button
            key={b.id}
            onClick={() => setExpandedId(expandedId === b.id ? null : b.id)}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs transition-colors border group ${
              expandedId === b.id
                ? "bg-accent-gold/15 text-accent-gold border-accent-gold/30"
                : "bg-bg-surface text-text-primary border-border hover:border-accent-gold/30"
            }`}
          >
            <span className="truncate max-w-[200px]">{truncate(b.title, 30)}</span>
            {b.department === null && <span className="text-[9px] opacity-50">all</span>}
            {expandedId === b.id ? (
              <ChevronUp className="h-3 w-3 shrink-0 opacity-60" />
            ) : (
              <ChevronDown className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-60" />
            )}
            <span
              onClick={(e) => handleArchiveClick(e, b.id)}
              className={`shrink-0 transition-colors rounded-full p-0.5 ${
                confirmArchiveId === b.id
                  ? "text-flag-critical bg-flag-critical/10"
                  : "text-text-secondary opacity-0 group-hover:opacity-100 hover:text-flag-critical"
              }`}
              title={confirmArchiveId === b.id ? "Click again to archive" : "Archive briefing"}
            >
              <X className="h-3 w-3" />
            </span>
          </button>
        ))}
        <button
          onClick={onNewBriefing}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs text-text-secondary border border-dashed border-border hover:border-accent-gold/50 hover:text-accent-gold transition-colors"
        >
          <Plus className="h-3 w-3" />
          New Briefing
        </button>
      </div>

      {/* Expanded briefing detail */}
      {expandedId &&
        (() => {
          const b = briefings.find((x) => x.id === expandedId);
          if (!b) return null;
          return (
            <div className="rounded-lg border border-border bg-bg-surface p-4 text-sm space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-text-heading font-medium text-sm">{b.title}</h4>
                <span className="text-[10px] text-text-secondary">
                  {new Date(b.created_at).toLocaleDateString()} &middot; {b.created_by_email}
                </span>
              </div>
              <p className="text-text-primary text-sm whitespace-pre-wrap">{b.content}</p>
              {b.attachments.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {b.attachments.map((att) => (
                    <span
                      key={att.id}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-bg-input border border-border text-[10px] text-text-secondary"
                    >
                      <Paperclip className="h-2.5 w-2.5" />
                      {att.original_filename}
                      <span className="opacity-50">
                        ({att.word_count ? `${att.word_count} words` : att.file_format})
                      </span>
                    </span>
                  ))}
                </div>
              )}
              {b.task_count > 0 && (
                <p className="text-[10px] text-text-secondary pt-1">
                  {b.task_count} task{b.task_count !== 1 ? "s" : ""} generated
                </p>
              )}
            </div>
          );
        })()}
    </div>
  );
}
