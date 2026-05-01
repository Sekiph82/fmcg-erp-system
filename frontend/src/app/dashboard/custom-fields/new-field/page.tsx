"use client";
import { useState } from "react";
import {
  customFieldsApi, EntityType, FieldType,
  ENTITY_LABEL, FIELD_TYPE_LABEL, ValidationRuleType,
} from "@/lib/custom_fields";

const ENTITY_TYPES: EntityType[] = [
  "customer", "supplier", "product", "sales_order", "purchase_order",
  "production_order", "employee", "asset", "contract", "crm_record", "expense", "lot",
];
const FIELD_TYPES: FieldType[] = [
  "text", "long_text", "number", "decimal", "currency", "date", "datetime",
  "boolean", "select", "multi_select", "reference", "file_attachment", "url", "email", "phone", "computed",
];
const RULE_TYPES: ValidationRuleType[] = ["min", "max", "min_length", "max_length", "regex", "unique"];

interface Option { value: string; label: string; order: number }
interface Rule { type: ValidationRuleType; value: string; message: string }

export default function NewFieldPage() {
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState("");

  const [core, setCore] = useState({
    entity_type: "" as EntityType,
    field_code: "",
    field_label: "",
    field_type: "text" as FieldType,
    help_text: "",
    placeholder: "",
    default_value: "",
    display_order: 0,
    section_label: "",
    reference_entity: "",
    formula: "",
    notes: "",
  });

  const [flags, setFlags] = useState({
    required_flag: false,
    unique_flag: false,
    searchable_flag: true,
    filterable_flag: true,
    reportable_flag: true,
    importable_flag: true,
    exportable_flag: true,
    sensitive_flag: false,
    active_flag: true,
  });

  const [options, setOptions] = useState<Option[]>([]);
  const [newOpt, setNewOpt] = useState({ value: "", label: "" });

  const [rules, setRules] = useState<Rule[]>([]);
  const [newRule, setNewRule] = useState({ type: "min" as ValidationRuleType, value: "", message: "" });

  const isSelectType = ["select", "multi_select"].includes(core.field_type);
  const isComputedType = core.field_type === "computed";

  const autoCode = (label: string) =>
    label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");

  const submit = async () => {
    setError("");
    setSubmitting(true);
    try {
      const f = await customFieldsApi.createField({
        ...core,
        ...flags,
        options: options.map((o, i) => ({ option_value: o.value, option_label: o.label, display_order: i })),
        validation_rules: rules.map(r => ({ rule_type: r.type, rule_value: r.value, error_message: r.message })),
      });
      setDone(f.custom_field_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create field");
    } finally {
      setSubmitting(false);
    }
  };

  if (done) return (
    <div className="p-6 text-center space-y-3">
      <p className="text-green-600 font-semibold text-lg">Field created!</p>
      <div className="flex justify-center gap-3">
        <a href={`/dashboard/custom-fields/${done}`} className="text-sm text-blue-600 hover:underline">View Field</a>
        <a href="/dashboard/custom-fields/fields" className="text-sm text-gray-600 hover:underline">Field Manager</a>
        <button onClick={() => { setDone(null); setStep(1); setCore({ ...core, field_code: "", field_label: "" }); }}
          className="text-sm text-gray-500 hover:underline">Create Another</button>
      </div>
    </div>
  );

  const steps = ["Core Info", "Settings & Flags", "Options & Rules"];

  return (
    <div className="p-6 max-w-2xl space-y-5">
      <h1 className="text-xl font-bold text-gray-900">Create Custom Field</h1>

      <div className="flex gap-1">
        {steps.map((s, i) => (
          <div key={s} className={`flex-1 text-center text-xs py-1 rounded font-medium ${i + 1 === step ? "bg-blue-600 text-white" : i + 1 < step ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
            {i + 1}. {s}
          </div>
        ))}
      </div>

      {step === 1 && (
        <div className="bg-white border rounded-lg p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Module / Entity Type *</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={core.entity_type}
                onChange={e => setCore({ ...core, entity_type: e.target.value as EntityType })}>
                <option value="">Select module…</option>
                {ENTITY_TYPES.map(t => <option key={t} value={t}>{ENTITY_LABEL[t]}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Field Label *</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={core.field_label}
                onChange={e => setCore({ ...core, field_label: e.target.value, field_code: autoCode(e.target.value) })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Field Code * (auto-generated)</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1 font-mono" value={core.field_code}
                onChange={e => setCore({ ...core, field_code: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Field Type *</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={core.field_type}
                onChange={e => setCore({ ...core, field_type: e.target.value as FieldType })}>
                {FIELD_TYPES.map(t => <option key={t} value={t}>{FIELD_TYPE_LABEL[t]}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Display Order</label>
              <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={core.display_order}
                onChange={e => setCore({ ...core, display_order: Number(e.target.value) })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Section Label (groups fields)</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" placeholder="e.g. Shipping Info"
                value={core.section_label} onChange={e => setCore({ ...core, section_label: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Placeholder Text</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={core.placeholder}
                onChange={e => setCore({ ...core, placeholder: e.target.value })} />
            </div>
            {!isSelectType && !isComputedType && (
              <div>
                <label className="text-xs text-gray-500">Default Value</label>
                <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={core.default_value}
                  onChange={e => setCore({ ...core, default_value: e.target.value })} />
              </div>
            )}
            {isComputedType && (
              <div className="col-span-2">
                <label className="text-xs text-gray-500">Formula (e.g. {"{price}"} * {"{qty}"} )</label>
                <input className="w-full border rounded px-2 py-1.5 text-sm mt-1 font-mono" value={core.formula}
                  onChange={e => setCore({ ...core, formula: e.target.value })} />
              </div>
            )}
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Help Text</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={core.help_text}
                onChange={e => setCore({ ...core, help_text: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Notes</label>
              <textarea className="w-full border rounded px-2 py-1.5 text-sm mt-1 h-16 resize-none" value={core.notes}
                onChange={e => setCore({ ...core, notes: e.target.value })} />
            </div>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="font-semibold text-gray-800 text-sm">Field Flags & Visibility</h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { key: "required_flag", label: "Required", desc: "Entity cannot be saved without this field" },
              { key: "unique_flag", label: "Unique", desc: "Value must be unique across all entities" },
              { key: "searchable_flag", label: "Searchable", desc: "Included in text search" },
              { key: "filterable_flag", label: "Filterable", desc: "Available as a list filter" },
              { key: "reportable_flag", label: "Reportable", desc: "Exposed to the Report Builder" },
              { key: "importable_flag", label: "Importable", desc: "Included in CSV import template" },
              { key: "exportable_flag", label: "Exportable", desc: "Included in CSV export" },
              { key: "sensitive_flag", label: "Sensitive 🔒", desc: "Restricted visibility (flagged)" },
              { key: "active_flag", label: "Active", desc: "Field is visible and in use" },
            ].map(({ key, label, desc }) => (
              <label key={key} className="flex items-start gap-2.5 cursor-pointer p-2 border rounded hover:bg-gray-50">
                <input type="checkbox" checked={flags[key as keyof typeof flags]}
                  onChange={e => setFlags({ ...flags, [key]: e.target.checked })}
                  className="mt-0.5 w-4 h-4" />
                <div>
                  <p className="text-sm font-medium text-gray-800">{label}</p>
                  <p className="text-xs text-gray-400">{desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          {isSelectType && (
            <div className="bg-white border rounded-lg p-5 space-y-3">
              <h2 className="font-semibold text-gray-800 text-sm">Dropdown Options</h2>
              <div className="flex gap-2">
                <input className="flex-1 border rounded px-2 py-1.5 text-sm" placeholder="Value (stored)"
                  value={newOpt.value} onChange={e => setNewOpt({ ...newOpt, value: e.target.value })} />
                <input className="flex-1 border rounded px-2 py-1.5 text-sm" placeholder="Label (displayed)"
                  value={newOpt.label} onChange={e => setNewOpt({ ...newOpt, label: e.target.value })} />
                <button onClick={() => {
                  if (!newOpt.value || !newOpt.label) return;
                  setOptions(prev => [...prev, { value: newOpt.value, label: newOpt.label, order: prev.length }]);
                  setNewOpt({ value: "", label: "" });
                }} className="rounded bg-gray-800 px-3 text-white text-sm">+</button>
              </div>
              {options.length > 0 && (
                <div className="divide-y border rounded">
                  {options.map((o, i) => (
                    <div key={i} className="flex items-center justify-between px-3 py-2 text-sm">
                      <span className="font-mono text-gray-500 text-xs">{o.value}</span>
                      <span className="text-gray-700">{o.label}</span>
                      <button onClick={() => setOptions(prev => prev.filter((_, j) => j !== i))}
                        className="text-red-400 text-xs hover:underline">Remove</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="bg-white border rounded-lg p-5 space-y-3">
            <h2 className="font-semibold text-gray-800 text-sm">Validation Rules (optional)</h2>
            <div className="flex gap-2">
              <select className="border rounded px-2 py-1.5 text-sm" value={newRule.type}
                onChange={e => setNewRule({ ...newRule, type: e.target.value as ValidationRuleType })}>
                {RULE_TYPES.map(r => <option key={r} value={r}>{r.replace("_", " ")}</option>)}
              </select>
              <input className="flex-1 border rounded px-2 py-1.5 text-sm" placeholder="Value (e.g. 100, ^[A-Z]+)"
                value={newRule.value} onChange={e => setNewRule({ ...newRule, value: e.target.value })} />
              <input className="flex-1 border rounded px-2 py-1.5 text-sm" placeholder="Error message"
                value={newRule.message} onChange={e => setNewRule({ ...newRule, message: e.target.value })} />
              <button onClick={() => {
                if (!newRule.value && !newRule.message) return;
                setRules(prev => [...prev, { ...newRule }]);
                setNewRule({ type: "min", value: "", message: "" });
              }} className="rounded bg-gray-800 px-3 text-white text-sm">+</button>
            </div>
            {rules.length > 0 && (
              <div className="divide-y border rounded">
                {rules.map((r, i) => (
                  <div key={i} className="flex items-center justify-between px-3 py-2 text-sm">
                    <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{r.type}</span>
                    <span className="font-mono text-gray-600 text-xs">{r.value}</span>
                    <span className="text-gray-500 text-xs flex-1 px-2">{r.message}</span>
                    <button onClick={() => setRules(prev => prev.filter((_, j) => j !== i))}
                      className="text-red-400 text-xs hover:underline">Remove</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-gray-50 border rounded p-4 text-sm space-y-1">
            <p className="font-medium text-gray-700 mb-2">Summary</p>
            <p><span className="font-medium">Module:</span> {ENTITY_LABEL[core.entity_type] ?? core.entity_type}</p>
            <p><span className="font-medium">Code:</span> <code className="font-mono text-xs">{core.field_code}</code></p>
            <p><span className="font-medium">Label:</span> {core.field_label}</p>
            <p><span className="font-medium">Type:</span> {FIELD_TYPE_LABEL[core.field_type]}</p>
            <p><span className="font-medium">Required:</span> {flags.required_flag ? "Yes" : "No"} · Options: {options.length} · Rules: {rules.length}</p>
          </div>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex justify-between">
        <button onClick={() => setStep(s => Math.max(1, s - 1))} disabled={step === 1}
          className="rounded border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40">Back</button>
        {step < 3
          ? <button onClick={() => setStep(s => s + 1)}
              disabled={!core.entity_type || !core.field_label || !core.field_code}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">Next</button>
          : <button onClick={submit} disabled={submitting}
              className="rounded bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-50">
              {submitting ? "Creating…" : "Create Field"}
            </button>
        }
      </div>
    </div>
  );
}
