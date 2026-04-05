// frontend/components/sprint-input.tsx
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { DepartmentDetail } from "@/lib/types";
import { Loader2, Paperclip, X, Sparkles } from "lucide-react";

interface SprintInputProps {
  projectId: string;
  departments: DepartmentDetail[];
  defaultDepartmentId?: string;
  onCreated?: () => void;
}

export function SprintInput({
  projectId,
  departments,
  defaultDepartmentId,
}: SprintInputProps) {
  const [text, setText] = useState("");
  const [selectedDeptIds, setSelectedDeptIds] = useState<Set<string>>(
    () => new Set(defaultDepartmentId ? [defaultDepartmentId] : []),
  );
  const [files, setFiles] = useState<File[]>([]);
  const [showDropZone, setShowDropZone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadSuggestions = useCallback(async () => {
    const deptIds = Array.from(selectedDeptIds);
    if (deptIds.length === 0) {
      setSuggestions([]);
      return;
    }
    setLoadingSuggestions(true);
    try {
      const res = await api.suggestSprints(projectId, deptIds);
      setSuggestions(res.suggestions || []);
    } catch {
      setSuggestions([]);
    } finally {
      setLoadingSuggestions(false);
    }
  }, [projectId, selectedDeptIds]);

  useEffect(() => {
    loadSuggestions();
  }, [loadSuggestions]);

  function toggleDept(deptId: string) {
    setSelectedDeptIds((prev) => {
      const next = new Set(prev);
      if (next.has(deptId)) {
        next.delete(deptId);
      } else {
        next.add(deptId);
      }
      return next;
    });
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setShowDropZone(false);
    const dropped = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...dropped]);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setShowDropZone(true);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit() {
    if (!text.trim() || selectedDeptIds.size === 0) return;
    setSubmitting(true);
    try {
      const sourceIds: string[] = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        const source = await api.uploadSource(projectId, formData);
        sourceIds.push(source.id);
      }

      await api.createSprint(projectId, {
        text: text.trim(),
        department_ids: Array.from(selectedDeptIds),
        source_ids: sourceIds,
      });

      setText("");
      setFiles([]);
      setShowDropZone(false);
      loadSuggestions();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mb-6">
      {/* Suggestions */}
      <div className="flex flex-wrap gap-2 mb-3 min-h-[28px]">
        {loadingSuggestions ? (
          <div className="flex items-center gap-1.5 text-xs text-text-secondary">
            <Loader2 className="h-3 w-3 animate-spin" />
            Loading suggestions…
          </div>
        ) : (
          suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => setText(s)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-accent-violet/8 text-accent-violet border border-accent-violet/20 hover:bg-accent-violet/15 transition-colors"
            >
              <Sparkles className="h-3 w-3" />
              {s}
            </button>
          ))
        )}
      </div>

      {/* Input area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={() => setShowDropZone(false)}
        onDrop={handleDrop}
        className="rounded-lg border border-border bg-bg-surface"
      >
        <div className="flex gap-2 p-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="What should this department work on?"
            rows={1}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-secondary/50 resize-none focus:outline-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="shrink-0 p-1.5 text-text-secondary hover:text-text-primary transition-colors"
            title="Attach files"
          >
            <Paperclip className="h-4 w-4" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.docx,.txt,.md,.csv"
            onChange={(e) => {
              if (e.target.files) {
                setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
              }
            }}
          />
        </div>

        {/* Drop zone */}
        {showDropZone && (
          <div className="mx-3 mb-3 rounded-lg border-2 border-dashed border-accent-violet/30 bg-accent-violet/5 p-4 text-center text-xs text-accent-violet">
            Drop files here
          </div>
        )}

        {/* File chips */}
        {files.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-3 pb-2">
            {files.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-bg-input border border-border text-[10px] text-text-secondary"
              >
                {f.name}
                <button onClick={() => removeFile(i)} className="hover:text-flag-critical">
                  <X className="h-2.5 w-2.5" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Department selector + submit */}
        <div className="flex items-center justify-between border-t border-border px-3 py-2">
          <div className="flex flex-wrap gap-1.5">
            {departments.map((d) => (
              <button
                key={d.id}
                onClick={() => toggleDept(d.id)}
                className={`px-2 py-0.5 rounded-full text-[10px] border transition-colors ${
                  selectedDeptIds.has(d.id)
                    ? "bg-accent-violet/15 text-accent-violet border-accent-violet/30"
                    : "bg-bg-input text-text-secondary border-border hover:border-accent-violet/30"
                }`}
              >
                {d.display_name}
              </button>
            ))}
          </div>
          <button
            onClick={handleSubmit}
            disabled={submitting || !text.trim() || selectedDeptIds.size === 0}
            className="shrink-0 px-4 py-1.5 rounded-lg text-xs font-semibold bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50 transition-colors"
          >
            {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Start Sprint"}
          </button>
        </div>
      </div>
    </div>
  );
}
