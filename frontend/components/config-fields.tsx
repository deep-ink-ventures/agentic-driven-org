"use client";

import { ToggleLeft, ToggleRight } from "lucide-react";
import { Input } from "@/components/ui/input";

export type ConfigSchema = {
  required?: string[];
  properties?: Record<
    string,
    { type: string; format?: string; description: string; title?: string }
  >;
};

/**
 * Renders config fields based on a JSON Schema from blueprint config_schema.
 * Handles string, email, and boolean types. Shared by agent, department, and project config editors.
 */
export function ConfigFields({
  schema,
  values,
  onChange,
  inheritedFrom,
  effectiveValues,
  disabled,
}: {
  schema: ConfigSchema;
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
  inheritedFrom?: Record<string, string>;
  effectiveValues?: Record<string, unknown>;
  disabled?: boolean;
}) {
  const properties = schema?.properties || {};
  const requiredKeys = new Set(schema?.required ?? []);

  if (Object.keys(properties).length === 0) return null;

  return (
    <div className="space-y-3">
      {Object.entries(properties).map(([key, spec]) => (
        <div key={key}>
          {spec.type === "boolean" ? (
            <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-bg-surface">
              <div>
                <p className="text-sm font-medium text-text-primary">
                  {spec.title || key}
                </p>
                <p className="text-[10px] text-text-secondary mt-0.5">
                  {spec.description}
                </p>
              </div>
              <button
                onClick={() => onChange(key, !values[key])}
                disabled={disabled}
                className={`transition-colors ${disabled ? "animate-pulse opacity-50" : ""} ${values[key] ? "text-accent-violet" : "text-text-secondary hover:text-accent-violet"}`}
              >
                {values[key] ? (
                  <ToggleRight className="h-6 w-6" />
                ) : (
                  <ToggleLeft className="h-6 w-6" />
                )}
              </button>
            </div>
          ) : (
            <>
              <label className="text-xs text-text-primary font-medium block mb-1">
                {spec.title || key}
                {requiredKeys.has(key) && (
                  <span className="text-flag-critical ml-0.5">*</span>
                )}
              </label>
              <p className="text-[10px] text-text-secondary mb-1">
                {spec.description}
              </p>
              <Input
                type={spec.format === "email" ? "email" : "text"}
                value={
                  values[key] == null
                    ? ""
                    : typeof values[key] === "string"
                      ? (values[key] as string)
                      : JSON.stringify(values[key])
                }
                placeholder={
                  effectiveValues?.[key] != null && !(key in values)
                    ? String(effectiveValues[key])
                    : spec.title || key
                }
                onChange={(e) => onChange(key, e.target.value)}
                disabled={disabled}
                className="bg-bg-input border-border text-text-primary text-xs font-mono"
              />
            </>
          )}
          {inheritedFrom?.[key] &&
            inheritedFrom[key] !== "agent" &&
            !(key in values) && (
              <p className="text-[10px] text-accent-violet mt-0.5">
                Inherited from {inheritedFrom[key]}
              </p>
            )}
        </div>
      ))}
    </div>
  );
}
