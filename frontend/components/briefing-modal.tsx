"use client";

import { useState, useRef } from "react";
import { api } from "@/lib/api";
import type { Briefing } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { X, Upload, FileText, Loader2, AlertCircle } from "lucide-react";

interface BriefingModalProps {
  projectId: string;
  department?: { id: string; name: string } | null;
  isOpen: boolean;
  onClose: () => void;
  onCreated: (briefing: Briefing) => void;
}

export function BriefingModal({
  projectId,
  department,
  isOpen,
  onClose,
  onCreated,
}: BriefingModalProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...dropped]);
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit() {
    if (!content.trim()) return;
    setLoading(true);
    setError("");
    try {
      const briefing = await api.createBriefing(projectId, {
        content: content.trim(),
        title: title.trim() || undefined,
        department: department?.id ?? null,
      });

      // Upload files sequentially
      for (const file of files) {
        await api.uploadBriefingFile(projectId, briefing.id, file);
      }

      // Re-fetch if files were uploaded so attachments are included
      if (files.length > 0) {
        const updated = await api.listBriefings(projectId, { status: "active" });
        const fresh = updated.find((b) => b.id === briefing.id);
        onCreated(fresh ?? briefing);
      } else {
        onCreated(briefing);
      }

      // Reset
      setTitle("");
      setContent("");
      setFiles([]);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create briefing");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-bg-primary border border-border rounded-2xl shadow-2xl w-full max-w-lg flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0">
          <div>
            <h3 className="text-sm font-medium text-text-heading">New Briefing</h3>
            <p className="text-xs text-text-secondary mt-0.5">
              {department ? department.name : "All departments"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-5 space-y-4 overflow-y-auto max-h-[60vh]">
          {error && (
            <div className="flex items-center gap-2 text-flag-critical text-sm p-3 rounded-lg bg-flag-critical/10">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title (auto-generated from content)"
              className="bg-bg-input border-border text-text-primary placeholder:text-text-secondary/50 text-sm"
            />
          </div>

          <div>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="What should the team focus on?"
              rows={5}
              className="w-full rounded-lg border border-border bg-bg-input px-2.5 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-none"
            />
          </div>

          {/* File upload */}
          <div>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border hover:border-accent-gold/50 p-4 text-center cursor-pointer transition-colors"
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md,.csv"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Upload className="h-6 w-6 text-text-secondary/50 mb-1" />
              <p className="text-text-primary font-medium text-xs mb-0.5">
                Drop files here or click to browse
              </p>
              <p className="text-text-secondary text-[10px]">
                PDF, DOCX, TXT, Markdown, CSV &middot; 50MB max
              </p>
            </div>
            {files.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {files.map((file, i) => (
                  <div
                    key={`${file.name}-${i}`}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-input border border-border text-xs"
                  >
                    <FileText className="h-3 w-3 text-text-secondary" />
                    <span className="text-text-primary truncate max-w-[150px]">{file.name}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(i);
                      }}
                      className="text-text-secondary hover:text-flag-critical transition-colors"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border shrink-0 flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            className="border-border text-text-secondary hover:text-text-primary"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!content.trim() || loading}
            className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Briefing"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
