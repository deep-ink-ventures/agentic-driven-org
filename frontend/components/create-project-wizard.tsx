"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { Project, BootstrapProposal, BootstrapProposalData } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  X,
  ArrowLeft,
  ArrowRight,
  Loader2,
  Plus,
  Trash2,
  Globe,
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Building2,
  Users,
  FileCheck,
} from "lucide-react";

interface CreateProjectWizardProps {
  onClose: () => void;
  onCreated: () => void;
  existingProject?: Project;
}

const STEP_LABELS = ["Project", "Sources", "Misc", "Analyze", "Review"];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2">
      {STEP_LABELS.map((label, i) => {
        const step = i + 1;
        const isActive = step === current;
        const isDone = step < current;
        return (
          <div key={label} className="flex items-center gap-2">
            {i > 0 && (
              <div
                className={`h-px w-6 ${
                  isDone ? "bg-accent-gold" : "bg-border"
                }`}
              />
            )}
            <div className="flex items-center gap-1.5">
              <div
                className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-accent-gold text-bg-primary"
                    : isDone
                      ? "bg-accent-gold/20 text-accent-gold"
                      : "bg-bg-surface text-text-secondary ring-1 ring-border"
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                ) : (
                  step
                )}
              </div>
              <span
                className={`text-xs hidden sm:inline ${
                  isActive
                    ? "text-accent-gold font-medium"
                    : "text-text-secondary"
                }`}
              >
                {label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function CreateProjectWizard({
  onClose,
  onCreated,
  existingProject,
}: CreateProjectWizardProps) {
  // Determine initial step based on existingProject
  function getInitialStep(): number {
    if (!existingProject) return 1;
    if (existingProject.bootstrap_status === "proposed") return 5;
    if (existingProject.bootstrap_status === "processing") return 4;
    return 2;
  }

  const [step, setStep] = useState(getInitialStep);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Step 1 — Project
  const [projectName, setProjectName] = useState(
    existingProject?.name ?? "",
  );
  const [projectGoal, setProjectGoal] = useState(
    existingProject?.goal ?? "",
  );
  const [projectId, setProjectId] = useState<string | null>(
    existingProject?.id ?? null,
  );

  // Step 2 — Sources (files + URLs)
  const [files, setFiles] = useState<File[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [urls, setUrls] = useState<string[]>([]);
  const [urlInput, setUrlInput] = useState("");

  // Step 3 — Misc (additional text)
  const [rawText, setRawText] = useState("");

  // Existing sources (for reopen)
  const [existingSources] = useState(existingProject?.sources ?? []);

  // Step 4-5
  const [proposal, setProposal] = useState<BootstrapProposal | null>(null);
  const [phase, setPhase] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const closeWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => closeWs();
  }, [closeWs]);

  // If resuming at step 4 (processing), connect WebSocket
  useEffect(() => {
    if (existingProject && step === 4 && projectId) {
      connectBootstrapWs(projectId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // If resuming at step 5 (proposed), fetch the latest proposal
  useEffect(() => {
    if (existingProject && step === 5 && projectId && !proposal) {
      api
        .getBootstrapLatest(projectId)
        .then(setProposal)
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ----- Step 1 handlers -----

  async function handleCreateProject() {
    if (!projectName.trim()) return;
    setLoading(true);
    setError("");
    try {
      const project = await api.createProject({
        name: projectName.trim(),
        goal: projectGoal.trim() || undefined,
      });
      setProjectId(project.id);
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create project");
    } finally {
      setLoading(false);
    }
  }

  // ----- Step 2 handlers (Sources — files + URLs only) -----

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

  function addUrl() {
    const trimmed = urlInput.trim();
    if (!trimmed) return;
    try {
      new URL(trimmed);
    } catch {
      setError("Please enter a valid URL");
      return;
    }
    setError("");
    setUrls((prev) => [...prev, trimmed]);
    setUrlInput("");
  }

  function removeUrl(index: number) {
    setUrls((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleUploadSources() {
    if (!projectId) return;

    const hasFiles = files.length > 0;
    const hasUrls = urls.length > 0;

    if (!hasFiles && !hasUrls) {
      // Nothing to upload — go straight to Misc step
      setStep(3);
      return;
    }

    setUploadingFiles(true);
    setError("");
    try {
      // Upload files
      for (const file of files) {
        await api.uploadFile(projectId, file);
      }
      // Upload URLs
      for (const url of urls) {
        await api.addSource(projectId, { source_type: "url", url });
      }
      setStep(3);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to upload sources");
    } finally {
      setUploadingFiles(false);
    }
  }

  // ----- Step 3 handler (Misc — additional text) -----

  async function handleMiscNext() {
    if (!projectId) return;
    // Upload text if provided
    if (rawText.trim()) {
      setLoading(true);
      setError("");
      try {
        await api.addSource(projectId, { source_type: "text", raw_content: rawText.trim() });
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to add text");
        setLoading(false);
        return;
      }
      setLoading(false);
    }
    setStep(4);
    startBootstrap();
  }

  // ----- Step 4 handlers (Bootstrap) -----

  async function connectBootstrapWs(pid: string) {
    closeWs();
    try {
      const { connectWs } = await import("@/lib/ws");
      const ws = await connectWs(
        `/ws/bootstrap/${pid}/`,
        async (data) => {
          const status = data.status as string;
          if (data.phase) {
            setPhase(data.phase as string);
          }
          if (status === "proposed" || status === "failed") {
            const latest = await api.getBootstrapLatest(pid);
            setProposal(latest);
            closeWs();
            if (status === "proposed") {
              setStep(5);
            }
          }
        },
      );
      wsRef.current = ws;
    } catch {
      // Fallback: if WS fails, fetch once after a delay
      setTimeout(async () => {
        try {
          const latest = await api.getBootstrapLatest(pid);
          setProposal(latest);
          if (latest.status === "proposed") setStep(5);
        } catch { /* ignore */ }
      }, 5000);
    }
  }

  async function startBootstrap() {
    if (!projectId) return;
    setError("");
    setProposal(null);
    try {
      const result = await api.triggerBootstrap(projectId);
      setProposal(result);
      connectBootstrapWs(projectId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start bootstrap");
    }
  }

  // ----- Step 5 handlers (Review) -----

  async function handleApprove() {
    if (!projectId || !proposal) return;
    setLoading(true);
    setError("");
    try {
      await api.approveBootstrap(projectId, proposal.id);
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to approve proposal");
    } finally {
      setLoading(false);
    }
  }

  // ----- Footer buttons -----

  function renderFooter() {
    // Step 1: only Next (create project)
    if (step === 1) {
      return (
        <div className="flex justify-end">
          <Button
            onClick={handleCreateProject}
            disabled={!projectName.trim() || loading}
            className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                Next
                <ArrowRight className="h-4 w-4 ml-1" />
              </>
            )}
          </Button>
        </div>
      );
    }

    // Step 2: Back + Next (upload sources)
    if (step === 2) {
      return (
        <div className="flex justify-between">
          {!existingProject && (
            <Button
              variant="outline"
              onClick={() => setStep(1)}
              className="border-border text-text-secondary hover:text-text-primary"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
          )}
          {existingProject && <div />}
          <Button
            onClick={handleUploadSources}
            disabled={uploadingFiles}
            className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
          >
            {uploadingFiles ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                {files.length === 0 && urls.length === 0
                  ? "Skip"
                  : "Next"}
                <ArrowRight className="h-4 w-4 ml-1" />
              </>
            )}
          </Button>
        </div>
      );
    }

    // Step 3: Back + Next (Misc — additional text)
    if (step === 3) {
      return (
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={() => setStep(2)}
            className="border-border text-text-secondary hover:text-text-primary"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <Button
            onClick={handleMiscNext}
            disabled={loading}
            className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                {!rawText.trim() ? "Skip" : "Next"}
                <ArrowRight className="h-4 w-4 ml-1" />
              </>
            )}
          </Button>
        </div>
      );
    }

    // Step 4: no navigation (spinner)
    if (step === 4) {
      return null;
    }

    // Step 5: Back to sources + Approve
    if (step === 5) {
      return (
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={() => setStep(2)}
            className="border-border text-text-secondary hover:text-text-primary"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to edit
          </Button>
          <Button
            onClick={handleApprove}
            disabled={loading}
            className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 mr-1" />
                Approve & Create
              </>
            )}
          </Button>
        </div>
      );
    }

    return null;
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-bg-primary border border-border rounded-2xl shadow-2xl w-full max-w-3xl h-[min(680px,90vh)] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0">
          <StepIndicator current={step} />
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary transition-colors ml-4"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content — scrollable */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {error && (
            <div className="flex items-center gap-2 text-flag-critical text-sm mb-4 p-3 rounded-lg bg-flag-critical/10">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Step 1: Project Name + Goal */}
          {step === 1 && (
            <div className="flex flex-col gap-5 h-full">
              <div className="flex flex-col gap-2">
                <Label htmlFor="project-name" className="text-text-primary">
                  Project name
                </Label>
                <Input
                  id="project-name"
                  placeholder="e.g. Acme Corp Operations"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  onKeyDown={(e) =>
                    e.key === "Enter" && handleCreateProject()
                  }
                  className="bg-bg-input border-border text-text-primary placeholder:text-text-secondary/50"
                />
              </div>
              <div className="flex flex-col gap-2 flex-1 min-h-0">
                <Label htmlFor="project-goal" className="text-text-primary">
                  Goal{" "}
                  <span className="text-text-secondary font-normal">
                    (optional)
                  </span>
                </Label>
                <textarea
                  id="project-goal"
                  placeholder="Describe what you want this project to achieve..."
                  value={projectGoal}
                  onChange={(e) => setProjectGoal(e.target.value)}
                  className="w-full flex-1 rounded-lg border border-border bg-bg-input px-2.5 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-none"
                />
              </div>
            </div>
          )}

          {/* Step 2: Sources (Files + URLs) */}
          {step === 2 && (
            <div className="flex flex-col gap-6">
              {/* Existing sources (read-only) */}
              {existingSources.length > 0 && (
                <div className="flex flex-col gap-2 mb-2">
                  <h3 className="text-xs font-medium text-text-secondary">Previously added</h3>
                  <div className="flex flex-wrap gap-2">
                    {existingSources.map((s) => (
                      <div key={s.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-accent-gold/10 border border-accent-gold/20 text-xs">
                        {s.source_type === "file" ? <FileText className="h-3 w-3 text-accent-gold" /> :
                         s.source_type === "url" ? <Globe className="h-3 w-3 text-accent-gold" /> :
                         <FileCheck className="h-3 w-3 text-accent-gold" />}
                        <span className="text-text-primary truncate max-w-[200px]">
                          {s.original_filename || s.url || "Text input"}
                        </span>
                      </div>
                    ))}
                  </div>
                  <Separator className="bg-border" />
                </div>
              )}

              {/* Files section */}
              <div className="flex flex-col gap-3">
                <h3 className="text-sm font-medium text-text-heading">
                  Files
                </h3>
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border hover:border-accent-gold/50 p-6 text-center cursor-pointer transition-colors"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.docx,.txt,.md"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Upload className="h-8 w-8 text-text-secondary/50 mb-2" />
                  <p className="text-text-primary font-medium text-sm mb-0.5">
                    Drop files here or click to browse
                  </p>
                  <p className="text-text-secondary text-xs">
                    PDF, DOCX, TXT, Markdown
                  </p>
                </div>
                {files.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {files.map((file, i) => (
                      <div key={`${file.name}-${i}`} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-input border border-border text-xs">
                        <FileText className="h-3 w-3 text-text-secondary" />
                        <span className="text-text-primary truncate max-w-[150px]">{file.name}</span>
                        <button onClick={(e) => { e.stopPropagation(); removeFile(i); }} className="text-text-secondary hover:text-flag-critical transition-colors">
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <Separator className="bg-border" />

              {/* URLs section */}
              <div className="flex flex-col gap-3">
                <h3 className="text-sm font-medium text-text-heading">URLs</h3>
                <div className="flex gap-2">
                  <Input
                    placeholder="https://example.com/about"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addUrl()}
                    className="bg-bg-input border-border text-text-primary placeholder:text-text-secondary/50 flex-1"
                  />
                  <Button
                    onClick={addUrl}
                    variant="outline"
                    className="border-border text-text-secondary hover:text-text-primary shrink-0"
                  >
                    <Plus className="h-4 w-4" />
                    Add
                  </Button>
                </div>
                {urls.length > 0 && (
                  <div className="flex flex-col gap-1.5 max-h-32 overflow-y-auto">
                    {urls.map((url, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 rounded-lg bg-bg-input border border-border px-3 py-2 text-sm group"
                      >
                        <Globe className="h-3.5 w-3.5 text-text-secondary shrink-0" />
                        <span className="text-text-primary truncate flex-1">
                          {url}
                        </span>
                        <button
                          onClick={() => removeUrl(i)}
                          className="text-text-secondary hover:text-flag-critical opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Misc — Additional Text */}
          {step === 3 && (
            <div className="flex flex-col gap-4">
              <div>
                <h3 className="text-sm font-medium text-text-heading mb-1">Additional context</h3>
                <p className="text-text-secondary text-xs mb-3">Optional — paste any extra text that helps describe your project.</p>
                <textarea
                  rows={8}
                  placeholder="Company info, product descriptions, notes..."
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  className="w-full rounded-lg border border-border bg-bg-input px-2.5 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-none"
                />
              </div>
            </div>
          )}

          {/* Step 4: Bootstrap Processing */}
          {step === 4 && (
            <div className="flex flex-col items-center justify-center gap-4 py-12">
              {proposal?.status === "failed" ? (
                <>
                  <AlertCircle className="h-12 w-12 text-flag-critical" />
                  <p className="text-text-heading font-medium text-lg">
                    Bootstrap failed
                  </p>
                  <p className="text-text-secondary text-sm text-center max-w-sm">
                    {proposal.error_message || "An unknown error occurred."}
                  </p>
                  <Button
                    onClick={() => startBootstrap()}
                    className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover mt-2"
                  >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Retry
                  </Button>
                </>
              ) : (
                <>
                  <Loader2 className="h-10 w-10 text-accent-gold animate-spin" />
                  <p className="text-text-heading font-medium text-lg">
                    {phase || "Preparing..."}
                  </p>
                  <p className="text-text-secondary text-sm">
                    This may take a moment.
                  </p>
                </>
              )}
            </div>
          )}

          {/* Step 5: Review & Approve */}
          {step === 5 && proposal?.proposal && (
            <div className="flex flex-col gap-5">
              {/* Summary */}
              <div>
                <h3 className="text-sm font-medium text-text-heading mb-2">
                  Summary
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {proposal.proposal.summary}
                </p>
              </div>

              <Separator className="bg-border" />

              {/* Departments */}
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-text-heading">
                  Departments
                </h3>
                {proposal.proposal.departments.map((dept, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-border bg-bg-primary/30 p-4 space-y-3"
                  >
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-accent-gold" />
                      <span className="text-sm font-medium text-text-heading capitalize">
                        {dept.department_type.replace(/_/g, " ")}
                      </span>
                    </div>

                    {dept.agents.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                          <Users className="h-3 w-3" />
                          <span>
                            {dept.agents.length} agent
                            {dept.agents.length !== 1 ? "s" : ""}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {dept.agents.map((agent, j) => (
                            <span
                              key={j}
                              className="inline-flex items-center rounded-md bg-accent-gold-muted px-2 py-0.5 text-xs text-accent-gold"
                            >
                              {agent.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {dept.documents.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                          <FileCheck className="h-3 w-3" />
                          <span>
                            {dept.documents.length} document
                            {dept.documents.length !== 1 ? "s" : ""}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {dept.documents.map((doc, j) => (
                            <span
                              key={j}
                              className="inline-flex items-center rounded-md bg-bg-surface-hover px-2 py-0.5 text-xs text-text-secondary"
                            >
                              {doc.title}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Ignored content */}
              {proposal.proposal.ignored_content.length > 0 && (
                <>
                  <Separator className="bg-border" />
                  <div>
                    <h3 className="text-sm font-medium text-text-heading mb-2">
                      Ignored content
                    </h3>
                    <div className="space-y-1.5">
                      {proposal.proposal.ignored_content.map((item, i) => (
                        <div key={i} className="text-xs text-text-secondary">
                          <span className="text-text-primary">
                            {item.source_name}
                          </span>{" "}
                          — {item.reason}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer with navigation */}
        {renderFooter() && (
          <div className="px-6 py-4 border-t border-border shrink-0">
            {renderFooter()}
          </div>
        )}
      </div>
    </div>
  );
}
