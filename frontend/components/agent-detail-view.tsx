"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentSummary, BlueprintInfo } from "@/lib/types";
import { AgentConfigEditor } from "@/components/agent-config-editor";
import { TaskQueue } from "@/components/task-queue";
import {
  Loader2,
  ChevronLeft,
  Check,
  Save,
  FileText,
  Terminal,
  Settings2,
  ListTodo,
  Clock,
  CalendarDays,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";

export function AgentDetailView({
  agent,
  projectId,
  onBack,
  onAgentUpdated,
  taskWsEvent,
}: {
  agent: AgentSummary;
  projectId: string;
  onBack: () => void;
  onAgentUpdated: () => void;
  taskWsEvent?: { type: string; task: import("@/lib/types").AgentTask } | null;
}) {
  const [tab, setTab] = useState<"overview" | "instructions" | "config" | "tasks">(
    "overview",
  );
  const [blueprint, setBlueprint] = useState<BlueprintInfo | null>(null);
  const [instructions, setInstructions] = useState(agent.instructions);
  const [editingInstructions, setEditingInstructions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [instructionsSaved, setInstructionsSaved] = useState(false);

  useEffect(() => {
    api.getAgentBlueprint(agent.id).then(setBlueprint).catch(() => {});
  }, [agent.id]);

  async function saveInstructions() {
    setSaving(true);
    try {
      await api.updateAgent(agent.id, { instructions });
      onAgentUpdated();
      setInstructionsSaved(true);
      setTimeout(() => setInstructionsSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  const tabs = [
    { key: "overview" as const, label: "Overview", icon: FileText },
    { key: "tasks" as const, label: "Tasks", icon: ListTodo },
    { key: "instructions" as const, label: "Instructions", icon: Terminal },
    { key: "config" as const, label: "Config", icon: Settings2 },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem-3rem)]">
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-text-secondary hover:text-text-primary text-sm mb-4 transition-colors shrink-0"
      >
        <ChevronLeft className="h-4 w-4" /> Back
      </button>

      <div className="flex items-center gap-3 mb-1 shrink-0">
        <h2 className="text-2xl font-semibold">{agent.name}</h2>
      </div>

      {blueprint?.tags && (
        <div className="flex gap-1.5 mb-6">
          {blueprint.tags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] px-2 py-0.5 rounded-full bg-accent-violet/10 text-accent-violet border border-accent-violet/20"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-border shrink-0">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm transition-colors border-b-2 -mb-px ${
              tab === key
                ? "border-accent-violet text-accent-violet"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            <Icon className="h-3.5 w-3.5" /> {label}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {tab === "overview" && blueprint && (
        <div className="space-y-6 flex-1 overflow-y-auto min-h-0">
          <div>
            <p className="text-sm text-text-primary">
              {blueprint.description}
            </p>
          </div>
          {/* Scheduled tasks */}
          {blueprint.commands.some((cmd) => cmd.schedule) && (
            <div>
              <h3 className="text-xs uppercase text-text-secondary font-medium mb-2">
                Schedule
              </h3>
              <div className="space-y-1.5">
                {blueprint.commands
                  .filter((cmd) => cmd.schedule)
                  .map((cmd) => (
                    <div
                      key={cmd.name}
                      className="flex items-center gap-2 text-xs rounded-md border border-border bg-bg-input/50 px-2.5 py-1.5"
                    >
                      {cmd.schedule === "hourly" ? (
                        <Clock className="h-3.5 w-3.5 text-accent-violet shrink-0" />
                      ) : (
                        <CalendarDays className="h-3.5 w-3.5 text-accent-gold shrink-0" />
                      )}
                      <span className="text-text-primary font-mono">
                        {cmd.name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-bg-primary border border-border text-text-secondary">
                        {cmd.schedule}
                      </span>
                      <span className="text-text-secondary">
                        {cmd.description}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
          <div>
            <h3 className="text-xs uppercase text-text-secondary font-medium mb-2">
              Skills
            </h3>
            <div className="space-y-1.5">
              {blueprint.skills_description.split("\n").filter(Boolean).map((line, i) => {
                const match = line.match(/^- \*\*(.+?)\*\*:\s*(.+)$/);
                if (!match) return null;
                return (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="text-text-primary font-mono">{match[1]}</span>
                    <span className="text-text-secondary">{match[2]}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div>
            <h3 className="text-xs uppercase text-text-secondary font-medium mb-2">
              Commands
            </h3>
            <div className="space-y-1.5">
              {blueprint.commands.map((cmd) => (
                <div
                  key={cmd.name}
                  className="flex items-center gap-2 text-xs"
                >
                  <span className="text-text-primary font-mono">
                    {cmd.name}
                  </span>
                  {cmd.schedule && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-bg-input border border-border text-text-secondary">
                      {cmd.schedule}
                    </span>
                  )}
                  <span className="text-text-secondary">
                    {cmd.description}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Instructions tab */}
      {tab === "instructions" && (
        <div className="flex flex-col flex-1 min-h-0">
          {editingInstructions ? (
            <>
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Custom instructions for this agent..."
                className="w-full flex-1 min-h-0 rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-violet focus-visible:ring-1 focus-visible:ring-accent-violet/50 resize-none font-mono"
                autoFocus
              />
              <div className="flex gap-2 mt-3 shrink-0">
                <Button
                  onClick={() => { saveInstructions(); setEditingInstructions(false); }}
                  disabled={saving || instructions === agent.instructions}
                  className={`${instructionsSaved ? "bg-flag-strength hover:bg-flag-strength" : "bg-accent-gold hover:bg-accent-gold-hover"} text-bg-primary disabled:opacity-90 transition-colors`}
                >
                  {saving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : instructionsSaved ? (
                    <><Check className="h-4 w-4 mr-1" /> Saved</>
                  ) : (
                    <><Save className="h-4 w-4 mr-1" /> Save</>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => { setInstructions(agent.instructions); setEditingInstructions(false); }}
                  className="border-border text-text-secondary hover:text-text-primary"
                >
                  Cancel
                </Button>
              </div>
            </>
          ) : (
            <div
              className="flex-1 min-h-0 rounded-lg border border-dashed border-border hover:border-accent-violet/40 p-4 cursor-pointer transition-colors overflow-y-auto"
              onClick={() => setEditingInstructions(true)}
            >
              {instructions ? (
                <div className="max-w-none text-sm text-text-primary [&_p]:mb-3 [&_ul]:mb-3 [&_ol]:mb-3 [&_h1]:mb-3 [&_h2]:mb-3 [&_h3]:mb-3 [&_h4]:mb-3 [&_li]:mb-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:text-base [&_h2]:font-semibold [&_h3]:text-sm [&_h3]:font-semibold [&>*:last-child]:mb-0">
                  <ReactMarkdown>{instructions}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-text-secondary text-sm">
                  Click to add custom instructions...
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Config tab */}
      {tab === "config" && blueprint && (
        <AgentConfigEditor
          agent={agent}
          blueprint={blueprint}
          onSaved={onAgentUpdated}
        />
      )}

      {/* Tasks tab */}
      {tab === "tasks" && (
        <div className="flex-1 overflow-y-auto min-h-0">
          <TaskQueue projectId={projectId} agent={agent.id} wsEvent={taskWsEvent} />
        </div>
      )}
    </div>
  );
}
