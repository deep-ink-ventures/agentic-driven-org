"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { AgentSummary, BlueprintInfo } from "@/lib/types";
import { Loader2, Check, Save, ToggleLeft, ToggleRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
  const [autoApprove, setAutoApprove] = useState(agent.auto_approve);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const schema = blueprint.config_schema as {
    required?: string[];
    properties?: Record<string, { type: string; description: string; title?: string }>;
  };

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
        auto_approve: autoApprove,
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

      {/* Auto-approve all toggle */}
      <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-bg-surface">
        <div>
          <p className="text-sm font-medium text-text-primary">Auto-approve tasks</p>
          <p className="text-xs text-text-secondary mt-0.5">
            {autoApprove ? "All tasks execute without manual approval" : "Tasks require manual approval before execution"}
          </p>
        </div>
        <button
          onClick={() => setAutoApprove(!autoApprove)}
          className={`transition-colors ${autoApprove ? "text-accent-violet" : "text-text-secondary hover:text-accent-violet"}`}
        >
          {autoApprove ? (
            <ToggleRight className="h-8 w-8" />
          ) : (
            <ToggleLeft className="h-8 w-8" />
          )}
        </button>
      </div>

      {/* Config fields */}
      {schema?.properties &&
        Object.keys(schema.properties).length > 0 && (
          <div>
            <h3 className="text-xs uppercase text-text-secondary font-medium mb-3">
              Configuration
            </h3>
            <div className="space-y-3">
              {Object.entries(schema.properties).map(([key, spec]) => (
                <div key={key}>
                  <label className="text-xs text-text-primary font-medium block mb-1">
                    {spec.title || key}
                    {requiredKeys.has(key) && <span className="text-flag-critical ml-0.5">*</span>}
                  </label>
                  <p className="text-[10px] text-text-secondary mb-1">
                    {spec.description}
                  </p>
                  <Input
                    value={
                      config[key] == null
                        ? ""
                        : typeof config[key] === "string"
                          ? (config[key] as string)
                          : JSON.stringify(config[key])
                    }
                    placeholder={
                      agent.effective_config[key] != null && !(key in config)
                        ? String(agent.effective_config[key])
                        : (spec.title || key)
                    }
                    onChange={(e) =>
                      setConfig({ ...config, [key]: e.target.value })
                    }
                    className="bg-bg-input border-border text-text-primary text-xs font-mono"
                  />
                  {agent.config_source[key] && agent.config_source[key] !== "agent" && !(key in config) && (
                    <p className="text-[10px] text-accent-violet mt-0.5">
                      Inherited from {agent.config_source[key]}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

      {/* Auto Approve Actions */}
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
