"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { SprintNote } from "@/lib/types";
import { Loader2, Paperclip, Send, X } from "lucide-react";

interface SprintNotesProps {
  projectId: string;
  sprintId: string;
  sprintStatus: string;
}

export function SprintNotes({ projectId, sprintId, sprintStatus }: SprintNotesProps) {
  const [notes, setNotes] = useState<SprintNote[]>([]);
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadNotes = useCallback(() => {
    api.listSprintNotes(projectId, sprintId).then(setNotes).catch(() => {});
  }, [projectId, sprintId]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  async function handleSubmit() {
    if (!text.trim()) return;
    setSubmitting(true);
    try {
      const sourceIds: string[] = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        const source = await api.uploadSource(projectId, formData);
        sourceIds.push(source.id);
      }

      await api.createSprintNote(projectId, sprintId, {
        text: text.trim(),
        source_ids: sourceIds.length > 0 ? sourceIds : undefined,
      });

      setText("");
      setFiles([]);
      loadNotes();
    } finally {
      setSubmitting(false);
    }
  }

  function formatTime(iso: string) {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function formatDate(iso: string) {
    const d = new Date(iso);
    const today = new Date();
    if (d.toDateString() === today.toDateString()) return "Today";
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
    return d.toLocaleDateString();
  }

  // Group notes by date
  const grouped: Record<string, SprintNote[]> = {};
  for (const note of notes) {
    const dateKey = formatDate(note.created_at);
    if (!grouped[dateKey]) grouped[dateKey] = [];
    grouped[dateKey].push(note);
  }

  const isActive = sprintStatus === "running" || sprintStatus === "paused";

  return (
    <div className="mt-3">
      {/* Notes thread */}
      {notes.length > 0 && (
        <div className="space-y-3 mb-3">
          {Object.entries(grouped).map(([date, dateNotes]) => (
            <div key={date}>
              <div className="text-[9px] text-text-secondary/50 uppercase tracking-wider text-center mb-2">
                {date}
              </div>
              <div className="space-y-1.5">
                {dateNotes.map((note) => (
                  <div
                    key={note.id}
                    className="flex gap-2 px-2.5 py-2 rounded-lg bg-bg-input/50 border border-border/30"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-text-primary whitespace-pre-wrap">
                        {note.text}
                      </div>
                      {note.sources.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {note.sources.map((s) => (
                            <span
                              key={s.id}
                              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-bg-surface border border-border text-[9px] text-text-secondary"
                            >
                              <Paperclip className="h-2 w-2" />
                              {s.original_filename}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="text-[9px] text-text-secondary/40 mt-1">
                        {formatTime(note.created_at)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Input — only for active sprints */}
      {isActive && (
        <div className="flex gap-2 items-end">
          <div className="flex-1 rounded-lg border border-border bg-bg-input">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Add a note for the agents..."
              rows={1}
              className="w-full px-2.5 py-1.5 bg-transparent text-xs text-text-primary placeholder:text-text-secondary/40 resize-none focus:outline-none"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = "auto";
                target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
              }}
            />
            {files.length > 0 && (
              <div className="flex flex-wrap gap-1 px-2.5 pb-1.5">
                {files.map((f, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-bg-surface border border-border text-[9px] text-text-secondary"
                  >
                    {f.name}
                    <button onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))} className="hover:text-flag-critical">
                      <X className="h-2 w-2" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="shrink-0 p-1.5 text-text-secondary hover:text-text-primary transition-colors"
            title="Attach file"
          >
            <Paperclip className="h-3.5 w-3.5" />
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
          <button
            onClick={handleSubmit}
            disabled={submitting || !text.trim()}
            className="shrink-0 p-1.5 rounded-lg bg-accent-violet/15 text-accent-violet hover:bg-accent-violet/25 disabled:opacity-30 transition-colors"
            title="Post note"
          >
            {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
          </button>
        </div>
      )}
    </div>
  );
}
