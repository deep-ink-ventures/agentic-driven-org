"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Sprint } from "@/lib/types";
import { History, Search, X, FileText } from "lucide-react";

interface SprintPickerDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (sprints: Sprint[]) => void;
  projectId: string;
  departmentId?: string;
  alreadySelectedIds: Set<string>;
}

export function SprintPickerDialog({
  open,
  onClose,
  onConfirm,
  projectId,
  departmentId,
  alreadySelectedIds,
}: SprintPickerDialogProps) {
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(alreadySelectedIds));

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setSelectedIds(new Set(alreadySelectedIds));
    api
      .listSprints(projectId, { status: "done", ...(departmentId ? { department: departmentId } : {}) })
      .then(setSprints)
      .catch(() => setSprints([]))
      .finally(() => setLoading(false));
  }, [open, projectId, departmentId, alreadySelectedIds]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const filtered = useMemo(() => {
    if (!search.trim()) return sprints;
    const q = search.toLowerCase();
    return sprints.filter(
      (s) =>
        s.text.toLowerCase().includes(q) ||
        s.departments.some((d) => d.display_name.toLowerCase().includes(q)),
    );
  }, [sprints, search]);

  // Group by department at project level
  const grouped = useMemo(() => {
    if (departmentId) return { "": filtered };
    const groups: Record<string, Sprint[]> = {};
    for (const s of filtered) {
      const deptName = s.departments.map((d) => d.display_name).join(", ") || "No department";
      if (!groups[deptName]) groups[deptName] = [];
      groups[deptName].push(s);
    }
    return groups;
  }, [filtered, departmentId]);

  function toggle(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function handleConfirm() {
    const selected = sprints.filter((s) => selectedIds.has(s.id));
    onConfirm(selected);
    onClose();
  }

  if (!open) return null;

  const outputCount = (s: Sprint) => s.outputs?.filter((o) => o.content).length ?? 0;

  function formatDate(iso: string) {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    const days = Math.floor(diff / 86400000);
    if (days === 0) return "today";
    if (days === 1) return "yesterday";
    if (days < 30) return `${days}d ago`;
    return d.toLocaleDateString();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg mx-4 rounded-xl border border-border bg-bg-surface shadow-2xl animate-in fade-in zoom-in-95 duration-150 flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-border">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-accent-violet" />
            <h3 className="text-sm font-semibold text-text-heading">Progress from sprint</h3>
          </div>
          <button onClick={onClose} className="p-1 text-text-secondary hover:text-text-primary transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Search */}
        <div className="px-5 py-3 border-b border-border">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-secondary/50" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search sprints..."
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-border bg-bg-input text-xs text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-accent-violet/50"
            />
          </div>
        </div>

        {/* Sprint list */}
        <div className="flex-1 overflow-y-auto px-5 py-3 min-h-0">
          {loading ? (
            <div className="text-xs text-text-secondary text-center py-8">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="text-xs text-text-secondary text-center py-8">
              {sprints.length === 0 ? "No completed sprints yet" : "No sprints match your search"}
            </div>
          ) : (
            Object.entries(grouped).map(([group, groupSprints]) => (
              <div key={group}>
                {group && (
                  <div className="text-[10px] font-medium text-text-secondary uppercase tracking-wider mb-2 mt-3 first:mt-0">
                    {group}
                  </div>
                )}
                <div className="space-y-1.5">
                  {groupSprints.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => toggle(s.id)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${
                        selectedIds.has(s.id)
                          ? "bg-accent-violet/10 border-accent-violet/30"
                          : "bg-bg-input/50 border-border hover:border-accent-violet/20"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-text-primary truncate">{s.text}</div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[10px] text-text-secondary">{formatDate(s.completed_at || s.updated_at)}</span>
                            {outputCount(s) > 0 && (
                              <span className="inline-flex items-center gap-0.5 text-[10px] text-text-secondary">
                                <FileText className="h-2.5 w-2.5" />
                                {outputCount(s)}
                              </span>
                            )}
                          </div>
                        </div>
                        <div
                          className={`shrink-0 mt-0.5 w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                            selectedIds.has(s.id)
                              ? "bg-accent-violet border-accent-violet"
                              : "border-border"
                          }`}
                        >
                          {selectedIds.has(s.id) && (
                            <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-5 py-3">
          <span className="text-[10px] text-text-secondary">
            {selectedIds.size > 0 ? `${selectedIds.size} selected` : "Select sprints to carry forward"}
          </span>
          <button
            onClick={handleConfirm}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-accent-violet/15 text-accent-violet border border-accent-violet/30 hover:bg-accent-violet/25 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
