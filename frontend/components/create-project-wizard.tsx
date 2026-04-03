"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { BootstrapProposal, BootstrapProposalData } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
}

const STEP_LABELS = [
  "Project",
  "Files",
  "URLs",
  "Text",
  "Bootstrap",
  "Review",
];

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
                  isActive ? "text-accent-gold font-medium" : "text-text-secondary"
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
}: CreateProjectWizardProps) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Step 1
  const [projectName, setProjectName] = useState("");
  const [projectGoal, setProjectGoal] = useState("");
  const [projectId, setProjectId] = useState<string | null>(null);

  // Step 2
  const [files, setFiles] = useState<File[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Step 3
  const [urls, setUrls] = useState<string[]>([]);
  const [urlInput, setUrlInput] = useState("");

  // Step 4
  const [rawText, setRawText] = useState("");

  // Step 5-6
  const [proposal, setProposal] = useState<BootstrapProposal | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

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

  async function handleUploadFiles() {
    if (!projectId || files.length === 0) {
      setStep(3);
      return;
    }
    setUploadingFiles(true);
    setError("");
    try {
      for (const file of files) {
        await api.uploadFile(projectId, file);
      }
      setStep(3);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to upload files");
    } finally {
      setUploadingFiles(false);
    }
  }

  async function handleUploadUrls() {
    if (!projectId || urls.length === 0) {
      setStep(4);
      return;
    }
    setLoading(true);
    setError("");
    try {
      for (const url of urls) {
        await api.addSource(projectId, { source_type: "url", url });
      }
      setStep(4);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add URLs");
    } finally {
      setLoading(false);
    }
  }

  async function handleUploadText() {
    if (!projectId || !rawText.trim()) {
      setStep(5);
      startBootstrap();
      return;
    }
    setLoading(true);
    setError("");
    try {
      await api.addSource(projectId, {
        source_type: "text",
        raw_content: rawText.trim(),
      });
      setStep(5);
      startBootstrap();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add text");
    } finally {
      setLoading(false);
    }
  }

  async function startBootstrap() {
    if (!projectId) return;
    setError("");
    setProposal(null);
    try {
      const result = await api.triggerBootstrap(projectId);
      setProposal(result);
      pollRef.current = setInterval(async () => {
        try {
          const latest = await api.getBootstrapLatest(projectId);
          setProposal(latest);
          if (latest.status === "proposed" || latest.status === "failed") {
            stopPolling();
            if (latest.status === "proposed") {
              setStep(6);
            }
          }
        } catch {
          // keep polling
        }
      }, 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start bootstrap");
    }
  }

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

  const canGoBack =
    step >= 2 && step <= 4;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg-primary/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl mx-4">
        <Card className="bg-bg-surface border-border relative">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-text-secondary hover:text-text-primary transition-colors z-10"
          >
            <X className="h-5 w-5" />
          </button>

          <CardHeader>
            <div className="flex flex-col gap-4">
              <CardTitle className="text-xl text-text-heading">
                Create Project
              </CardTitle>
              <StepIndicator current={step} />
            </div>
          </CardHeader>

          <Separator className="bg-border" />

          <CardContent className="pt-6 pb-6 min-h-[320px] flex flex-col">
            {error && (
              <div className="flex items-center gap-2 text-flag-critical text-sm mb-4 p-3 rounded-lg bg-flag-critical/10">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Step 1: Project Name + Goal */}
            {step === 1 && (
              <div className="flex flex-col gap-5 flex-1">
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
                <div className="flex flex-col gap-2">
                  <Label htmlFor="project-goal" className="text-text-primary">
                    Goal{" "}
                    <span className="text-text-secondary font-normal">
                      (optional)
                    </span>
                  </Label>
                  <textarea
                    id="project-goal"
                    rows={3}
                    placeholder="Describe what you want this project to achieve..."
                    value={projectGoal}
                    onChange={(e) => setProjectGoal(e.target.value)}
                    className="w-full rounded-lg border border-border bg-bg-input px-2.5 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-none"
                  />
                </div>
                <div className="mt-auto flex justify-end">
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
              </div>
            )}

            {/* Step 2: Files */}
            {step === 2 && (
              <div className="flex flex-col gap-5 flex-1">
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-1 flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border hover:border-accent-gold/50 p-8 text-center cursor-pointer transition-colors min-h-[160px]"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.docx,.txt,.md"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Upload className="h-10 w-10 text-text-secondary/50 mb-3" />
                  <p className="text-text-primary font-medium mb-1">
                    Drop files here or click to browse
                  </p>
                  <p className="text-text-secondary text-xs">
                    PDF, DOCX, TXT, Markdown
                  </p>
                </div>

                {files.length > 0 && (
                  <div className="space-y-2">
                    {files.map((file, i) => (
                      <div key={`${file.name}-${i}`} className="flex items-center justify-between px-3 py-2 rounded-lg bg-bg-input border border-border">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="h-4 w-4 text-text-secondary shrink-0" />
                          <span className="text-sm text-text-primary truncate">{file.name}</span>
                          <span className="text-xs text-text-secondary shrink-0">
                            {(file.size / 1024).toFixed(0)}KB
                          </span>
                        </div>
                        <button onClick={(e) => { e.stopPropagation(); removeFile(i); }} className="text-text-secondary hover:text-flag-critical transition-colors p-1">
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="mt-auto flex justify-between">
                  <Button
                    variant="outline"
                    onClick={() => setStep(1)}
                    className="border-border text-text-secondary hover:text-text-primary"
                  >
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back
                  </Button>
                  <Button
                    onClick={handleUploadFiles}
                    disabled={uploadingFiles}
                    className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover"
                  >
                    {uploadingFiles ? (
                      <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Uploading...</>
                    ) : (
                      <>Next<ArrowRight className="h-4 w-4 ml-1" /></>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: URLs */}
            {step === 3 && (
              <div className="flex flex-col gap-5 flex-1">
                <div className="flex flex-col gap-2">
                  <Label className="text-text-primary">Add URLs</Label>
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
                </div>
                {urls.length > 0 && (
                  <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto">
                    {urls.map((url, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 rounded-lg bg-bg-primary/50 px-3 py-2 text-sm group"
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
                <div className="mt-auto flex justify-between">
                  <Button
                    variant="outline"
                    onClick={() => setStep(2)}
                    className="border-border text-text-secondary hover:text-text-primary"
                  >
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back
                  </Button>
                  <Button
                    onClick={handleUploadUrls}
                    disabled={loading}
                    className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        {urls.length === 0 ? "Skip" : "Next"}
                        <ArrowRight className="h-4 w-4 ml-1" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Step 4: Additional Text */}
            {step === 4 && (
              <div className="flex flex-col gap-5 flex-1">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="raw-text" className="text-text-primary">
                    Paste additional context
                  </Label>
                  <textarea
                    id="raw-text"
                    rows={8}
                    placeholder="Paste any relevant text — company info, product descriptions, process documentation..."
                    value={rawText}
                    onChange={(e) => setRawText(e.target.value)}
                    className="w-full rounded-lg border border-border bg-bg-input px-2.5 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-none"
                  />
                </div>
                <div className="mt-auto flex justify-between">
                  <Button
                    variant="outline"
                    onClick={() => setStep(3)}
                    className="border-border text-text-secondary hover:text-text-primary"
                  >
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back
                  </Button>
                  <Button
                    onClick={handleUploadText}
                    disabled={loading}
                    className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        {rawText.trim() ? "Next" : "Skip"}
                        <ArrowRight className="h-4 w-4 ml-1" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Step 5: Bootstrap Processing */}
            {step === 5 && (
              <div className="flex flex-col items-center justify-center flex-1 gap-4 py-8">
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
                      Analyzing your sources...
                    </p>
                    <p className="text-text-secondary text-sm">
                      This may take a minute. We are building your project
                      structure.
                    </p>
                  </>
                )}
              </div>
            )}

            {/* Step 6: Review & Approve */}
            {step === 6 && proposal?.proposal && (
              <div className="flex flex-col gap-5 flex-1 overflow-hidden">
                <div className="flex-1 overflow-y-auto space-y-5 pr-1">
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
                            <div
                              key={i}
                              className="text-xs text-text-secondary"
                            >
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

                <Separator className="bg-border" />

                <div className="flex justify-between shrink-0">
                  <Button
                    variant="outline"
                    onClick={() => setStep(4)}
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
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
