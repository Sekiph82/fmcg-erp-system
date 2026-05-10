"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  customFieldsApi, CustomFieldDefinition, FieldOption,
  ENTITY_LABEL, FIELD_TYPE_LABEL,
} from "@/lib/custom_fields";

export default function FieldDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [field, setField] = useState<CustomFieldDefinition | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const [label, setLabel] = useState("");
  const [helpText, setHelpText] = useState("");
  const [displayOrder, setDisplayOrder] = useState(0);
  const [required, setRequired] = useState(false);
  const [reportable, setReportable] = useState(true);
  const [filterable, setFilterable] = useState(true);
  const [sensitive, setSensitive] = useState(false);
  const [notes, setNotes] = useState("");

  const [newOptValue, setNewOptValue] = useState("");
  const [newOptLabel, setNewOptLabel] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    customFieldsApi.getField(id).then(f => {
      setField(f);
      setLabel(f.field_label);
      setHelpText(f.help_text ?? "");
      setDisplayOrder(f.display_order);
      setRequired(f.required_flag);
      setReportable(f.reportable_flag);
      setFilterable(f.filterable_flag);
      setSensitive(f.sensitive_flag);
      setNotes(f.notes ?? "");
    }).finally(() => setLoading(false));
  }, [id]);

  useEffect(() => { if (id) load(); }, [id, load]);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await customFieldsApi.updateField(id, {
        field_label: label, help_text: helpText, display_order: displayOrder,
        required_flag: required, reportable_flag: reportable,
        filterable_flag: filterable, sensitive_flag: sensitive, notes,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const addOption = async () => {
    if (!newOptValue || !newOptLabel) return;
    await customFieldsApi.addOption(id, {
      option_value: newOptValue, option_label: newOptLabel,
      display_order: (field?.options.length ?? 0),
    });
    setNewOptValue("");
    setNewOptLabel("");
    load();
  };

  const removeOption = async (optId: string) => {
    await customFieldsApi.removeOption(optId);
    load();
  };

  const toggleDisable = async () => {
    if (!field) return;
    if (field.active_flag) {
      if (!confirm("Disable this field? Existing values will be preserved.")) return;
      await customFieldsApi.disableField(id);
    } else {
      await customFieldsApi.updateField(id, { active_flag: true });
    }
    load();
  };

  if (loading) return <div className="p-6"><p className="text-gray-500">Loading…</p></div>;
  if (!field) return <div className="p-6"><p className="text-red-500">Field not found.</p></div>;

  const isSelectType = ["select", "multi_select"].includes(field.field_type);

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{field.field_label}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            <code className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{field.field_code}</code>
            {" · "}{ENTITY_LABEL[field.entity_type]} · {FIELD_TYPE_LABEL[field.field_type]}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={toggleDisable}
            className={`rounded border px-3 py-1.5 text-sm ${field.active_flag ? "text-red-500 border-red-200 hover:bg-red-50" : "text-green-600 border-green-200 hover:bg-green-50"}`}>
            {field.active_flag ? "Disable" : "Enable"}
          </button>
          <a href="/dashboard/custom-fields/fields"
            className="rounded border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">← Back</a>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-5 space-y-4">
        <h2 className="font-semibold text-gray-800 text-sm">Edit Field</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-gray-500">Label</label>
            <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={label}
              onChange={e => setLabel(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-500">Display Order</label>
            <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={displayOrder}
              onChange={e => setDisplayOrder(Number(e.target.value))} />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-500">Help Text</label>
            <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={helpText}
              onChange={e => setHelpText(e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-500">Notes</label>
            <textarea className="w-full border rounded px-2 py-1.5 text-sm mt-1 h-16 resize-none" value={notes}
              onChange={e => setNotes(e.target.value)} />
          </div>
        </div>
        <div className="flex gap-4 flex-wrap">
          {[
            { label: "Required", val: required, set: setRequired },
            { label: "Reportable", val: reportable, set: setReportable },
            { label: "Filterable", val: filterable, set: setFilterable },
            { label: "Sensitive 🔒", val: sensitive, set: setSensitive },
          ].map(({ label: lbl, val, set }) => (
            <label key={lbl} className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={val} onChange={e => set(e.target.checked)} className="w-4 h-4" />
              <span className="text-sm text-gray-700">{lbl}</span>
            </label>
          ))}
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex items-center gap-3">
          <button onClick={save} disabled={saving}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Saving…" : "Save Changes"}
          </button>
          {saved && <span className="text-sm text-green-600">✓ Saved</span>}
        </div>
      </div>

      {isSelectType && (
        <div className="bg-white border rounded-lg p-5 space-y-3">
          <h2 className="font-semibold text-gray-800 text-sm">Dropdown Options</h2>
          <div className="flex gap-2">
            <input className="flex-1 border rounded px-2 py-1.5 text-sm" placeholder="Value"
              value={newOptValue} onChange={e => setNewOptValue(e.target.value)} />
            <input className="flex-1 border rounded px-2 py-1.5 text-sm" placeholder="Label"
              value={newOptLabel} onChange={e => setNewOptLabel(e.target.value)} />
            <button onClick={addOption} className="rounded bg-gray-800 px-3 text-white text-sm">Add</button>
          </div>
          <div className="divide-y border rounded">
            {field.options.map(o => (
              <div key={o.option_id} className={`flex items-center justify-between px-3 py-2 text-sm ${!o.active_flag ? "opacity-50" : ""}`}>
                <span className="font-mono text-gray-500 text-xs w-24">{o.option_value}</span>
                <span className="text-gray-700 flex-1 px-2">{o.option_label}</span>
                <span className="text-xs text-gray-400 w-8">#{o.display_order}</span>
                {o.active_flag && (
                  <button onClick={() => removeOption(o.option_id)} className="text-xs text-red-400 hover:underline">Remove</button>
                )}
              </div>
            ))}
            {field.options.length === 0 && <p className="px-3 py-3 text-sm text-gray-400">No options yet.</p>}
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg p-5">
        <h2 className="font-semibold text-gray-800 text-sm mb-3">Validation Rules</h2>
        {field.validation_rules.length === 0
          ? <p className="text-sm text-gray-400">No validation rules configured.</p>
          : (
            <div className="divide-y border rounded">
              {field.validation_rules.map(r => (
                <div key={r.validation_rule_id} className="flex items-center gap-3 px-3 py-2 text-sm">
                  <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{r.rule_type}</span>
                  {r.rule_value && <code className="font-mono text-xs text-gray-600">{r.rule_value}</code>}
                  {r.error_message && <span className="text-gray-500 flex-1">{r.error_message}</span>}
                </div>
              ))}
            </div>
          )}
      </div>

      <div className="bg-gray-50 border rounded p-4 text-sm grid grid-cols-2 gap-2">
        <div><span className="font-medium">Created:</span> {new Date(field.created_at).toLocaleString()}</div>
        <div><span className="font-medium">By:</span> {field.created_by ?? "—"}</div>
        <div><span className="font-medium">Searchable:</span> {field.searchable_flag ? "Yes" : "No"}</div>
        <div><span className="font-medium">Importable:</span> {field.importable_flag ? "Yes" : "No"}</div>
        <div><span className="font-medium">Exportable:</span> {field.exportable_flag ? "Yes" : "No"}</div>
        <div><span className="font-medium">Unique:</span> {field.unique_flag ? "Yes" : "No"}</div>
      </div>
    </div>
  );
}
