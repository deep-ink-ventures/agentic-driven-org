"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { AgentSummary, BlueprintInfo } from "@/lib/types";
import { Loader2, Check, Save, ToggleLeft, ToggleRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfigFields, type ConfigSchema } from "@/components/config-fields";

export function AgentConfigEditor({
  agent,
  blueprint,
  onSaved,
}: {
  agent: AgentSummary;
  blueprint: BlueprintInfo;
  onSaved: () => void;
}) {
  const [config, setConfig] = useState(agent.config);
  const [enabledCommands, setEnabledCommands] = useState<Record<string, boolean>>(agent.enabled_commands || {});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const allEnabled = blueprint.commands.length > 0
    && blueprint.commands.every((cmd: { name: string }) => enabledCommands[cmd.name]);

  function toggleCommand(name: string) {
    setEnabledCommands((prev) => ({ ...prev, [name]: !prev[name] }));
  }

  function toggleAllCommands() {
    const newValue = !allEnabled;
    const updated: Record<string, boolean> = {};
    for (const cmd of blueprint.commands) {
      updated[cmd.name] = newValue;
    }
    setEnabledCommands(updated);
  }

  const schema = blueprint.config_schema as ConfigSchema;

  const requiredKeys = new Set(schema?.required ?? []);
  const configComplete = [...requiredKeys].every((k) => {
    const val = config[k];
    return val !== undefined && val !== null && val !== "";
  });

  async function save() {
    setSaving(true);
    try {
      await api.updateAgent(agent.id, {
        config,
        enabled_commands: enabledCommands,
      });
      onSaved();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive() {
    if (!configComplete && agent.status !== "active") return;
    setSaving(true);
    try {
      await api.updateAgent(agent.id, {
        status: agent.status === "active" ? "inactive" : "active",
      });
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Activation toggle */}
      <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-bg-surface">
        <div>
          <p className="text-sm font-medium text-text-primary">
            {agent.status === "active" ? "Agent is active" : "Agent is inactive"}
          </p>
          {!configComplete && agent.status !== "active" && (
            <p className="text-xs text-text-secondary mt-0.5">
              Fill in required configuration to activate
            </p>
          )}
        </div>
        <button
          onClick={toggleActive}
          disabled={!configComplete && agent.status !== "active"}
          className={`transition-colors ${agent.status === "active" ? "text-flag-strength" : configComplete ? "text-text-secondary hover:text-flag-strength" : "text-text-secondary/30 cursor-not-allowed"}`}
        >
          {agent.status === "active" ? (
            <ToggleRight className="h-8 w-8" />
          ) : (
            <ToggleLeft className="h-8 w-8" />
          )}
        </button>
      </div>

      {/* Per-command auto-approve */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs uppercase text-text-secondary font-medium">
            Command Approval
          </h3>
          <button
            onClick={toggleAllCommands}
            disabled={saving}
            className={`text-[10px] transition-colors ${saving ? "animate-pulse opacity-50" : "hover:text-accent-violet"} ${allEnabled ? "text-accent-violet" : "text-text-secondary"}`}
          >
            {allEnabled ? "Revoke all" : "Auto-approve all"}
          </button>
        </div>
        <div className="space-y-2">
          {blueprint.commands.map((cmd: { name: string; description: string }) => (
            <div key={cmd.name} className="flex items-center justify-between p-3 rounded-lg border border-border bg-bg-surface">
              <div>
                <p className="text-sm font-medium text-text-primary">{cmd.name}</p>
                <p className="text-xs text-text-secondary mt-0.5">{cmd.description}</p>
              </div>
              <button
                onClick={() => toggleCommand(cmd.name)}
                disabled={saving}
                className={`transition-colors ${saving ? "animate-pulse opacity-50" : ""} ${enabledCommands[cmd.name] ? "text-accent-violet" : "text-text-secondary hover:text-accent-violet"}`}
              >
                {enabledCommands[cmd.name] ? <ToggleRight className="h-6 w-6" /> : <ToggleLeft className="h-6 w-6" />}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Config fields */}
      {schema?.properties && Object.keys(schema.properties).length > 0 && (
        <div>
          <h3 className="text-xs uppercase text-text-secondary font-medium mb-3">
            Configuration
          </h3>
          <ConfigFields
            schema={schema}
            values={config}
            onChange={(key, value) => setConfig({ ...config, [key]: value })}
            inheritedFrom={agent.config_source}
            effectiveValues={agent.effective_config}
            disabled={saving}
          />
        </div>
      )}

      {/* Save */}
      <Button
        onClick={save}
        disabled={saving || saved}
        className={`${saved ? "bg-flag-strength hover:bg-flag-strength" : "bg-accent-gold hover:bg-accent-gold-hover"} text-bg-primary disabled:opacity-90 transition-colors`}
      >
        {saving ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : saved ? (
          <>
            <Check className="h-4 w-4 mr-1" /> Saved
          </>
        ) : (
          <>
            <Save className="h-4 w-4 mr-1" /> Save
          </>
        )}
      </Button>
    </div>
  );
}
