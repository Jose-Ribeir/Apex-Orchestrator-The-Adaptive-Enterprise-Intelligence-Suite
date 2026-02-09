"use client";

type ToolItem = { id?: string; name?: string };
import type { AgentFormValues } from "@/lib/agent-form";
import { Field, FieldGroup, FieldLabel } from "@ai-router/ui/field";
import { Input } from "@ai-router/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@ai-router/ui/select";
import { Textarea } from "@ai-router/ui/textarea";

/** Mode is a subset of AgentFormValues; use it for the select. */
type AgentModeValue = NonNullable<AgentFormValues["mode"]>;

export interface AgentFormFieldsProps {
  value: AgentFormValues;
  onChange: (next: Partial<AgentFormValues>) => void;
  toolsList: ToolItem[];
  disabled?: boolean;
  idPrefix: string;
  nameLabel?: string;
  instructionsLabel?: string;
  instructionsPlaceholder?: string;
  toolsLabel?: string;
  instructionsRows?: number;
  nameAutoFocus?: boolean;
}

export function AgentFormFields({
  value,
  onChange,
  toolsList,
  disabled = false,
  idPrefix,
  nameLabel = "Agent name",
  instructionsLabel = "Instructions",
  instructionsPlaceholder = "Instruction 1\nInstruction 2",
  toolsLabel = "Tools (optional)",
  instructionsRows = 4,
  nameAutoFocus = false,
}: AgentFormFieldsProps) {
  function toggleTool(id: string) {
    const next = value.selectedToolIds.includes(id)
      ? value.selectedToolIds.filter((x) => x !== id)
      : [...value.selectedToolIds, id];
    onChange({ selectedToolIds: next });
  }

  return (
    <FieldGroup>
      <Field>
        <FieldLabel htmlFor={`${idPrefix}-name`}>{nameLabel}</FieldLabel>
        <Input
          id={`${idPrefix}-name`}
          name="name"
          type="text"
          placeholder="e.g. My Assistant"
          value={value.name}
          onChange={(e) => onChange({ name: e.target.value })}
          required
          disabled={disabled}
          autoFocus={nameAutoFocus}
        />
      </Field>
      <Field>
        <FieldLabel htmlFor={`${idPrefix}-mode`}>Mode</FieldLabel>
        <Select
          value={value.mode}
          onValueChange={(v) => onChange({ mode: v as AgentModeValue })}
          disabled={disabled}
        >
          <SelectTrigger id={`${idPrefix}-mode`}>
            <SelectValue placeholder="Select mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="EFFICIENCY">Efficiency</SelectItem>
            <SelectItem value="BALANCED">Balanced</SelectItem>
            <SelectItem value="PERFORMANCE">Performance</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field>
        <FieldLabel htmlFor={`${idPrefix}-instructions`}>
          {instructionsLabel}
        </FieldLabel>
        <Textarea
          id={`${idPrefix}-instructions`}
          name="instructions"
          placeholder={instructionsPlaceholder}
          value={value.instructionsText}
          onChange={(e) => onChange({ instructionsText: e.target.value })}
          disabled={disabled}
          rows={instructionsRows}
          className="resize-none"
        />
      </Field>
      <Field>
        <FieldLabel>{toolsLabel}</FieldLabel>
        <div className="border-input rounded-md border bg-transparent px-2.5 py-2">
          <div className="flex max-h-32 flex-wrap gap-2 overflow-y-auto">
            {toolsList.length === 0 ? (
              <p className="text-muted-foreground text-xs">
                No tools in catalog yet.
              </p>
            ) : (
              toolsList.map((tool) => (
                <label
                  key={tool.id}
                  className="text-foreground hover:bg-muted flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-xs"
                >
                  <input
                    type="checkbox"
                    name="tools"
                    value={tool.id}
                    checked={value.selectedToolIds.includes(tool.id ?? "")}
                    onChange={() => toggleTool(tool.id ?? "")}
                    disabled={disabled}
                    className="rounded border-input"
                  />
                  <span>{tool.name ?? tool.id}</span>
                </label>
              ))
            )}
          </div>
        </div>
      </Field>
    </FieldGroup>
  );
}
