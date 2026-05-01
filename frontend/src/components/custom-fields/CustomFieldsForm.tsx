"use client";
import { useEffect, useState, useCallback } from "react";
import {
  customFieldsApi, CustomFieldDefinition, FieldValueOut, FieldType,
} from "@/lib/custom_fields";

interface Props {
  entityType: string;
  entityId?: string;
  currentUser?: string;
  onChange?: (values: Record<string, unknown>) => void;
  readOnly?: boolean;
  compact?: boolean;
}

function renderInput(
  field: CustomFieldDefinition,
  value: unknown,
  onChange: (v: unknown) => void,
  readOnly: boolean,
) {
  const cls = "w-full border rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:bg-gray-50";

  if (field.field_type === "computed") {
    return <span className="text-sm text-gray-600 py-1 block">{value !== null && value !== undefined ? String(value) : "—"}</span>;
  }

  if (readOnly) {
    return <span className="text-sm text-gray-700 py-1 block">{value !== null && value !== undefined ? String(value) : "—"}</span>;
  }

  switch (field.field_type as FieldType) {
    case "text":
    case "url":
    case "email":
    case "phone":
      return (
        <input
          type={field.field_type === "email" ? "email" : field.field_type === "url" ? "url" : field.field_type === "phone" ? "tel" : "text"}
          className={cls}
          value={(value as string) ?? ""}
          placeholder={field.placeholder ?? ""}
          onChange={e => onChange(e.target.value)}
        />
      );
    case "long_text":
      return (
        <textarea
          className={`${cls} h-20 resize-none`}
          value={(value as string) ?? ""}
          placeholder={field.placeholder ?? ""}
          onChange={e => onChange(e.target.value)}
        />
      );
    case "number":
    case "decimal":
    case "currency":
      return (
        <input
          type="number"
          step={field.field_type === "number" ? "1" : "0.01"}
          className={cls}
          value={(value as number) ?? ""}
          placeholder={field.placeholder ?? "0"}
          onChange={e => onChange(e.target.value === "" ? null : Number(e.target.value))}
        />
      );
    case "date":
      return (
        <input type="date" className={cls}
          value={(value as string)?.slice(0, 10) ?? ""}
          onChange={e => onChange(e.target.value)} />
      );
    case "datetime":
      return (
        <input type="datetime-local" className={cls}
          value={(value as string)?.slice(0, 16) ?? ""}
          onChange={e => onChange(e.target.value)} />
      );
    case "boolean":
      return (
        <label className="flex items-center gap-2 cursor-pointer py-1">
          <input type="checkbox" checked={!!value}
            onChange={e => onChange(e.target.checked)}
            className="w-4 h-4 rounded" />
          <span className="text-sm text-gray-700">{value ? "Yes" : "No"}</span>
        </label>
      );
    case "select":
      return (
        <select className={cls} value={(value as string) ?? ""}
          onChange={e => onChange(e.target.value)}>
          <option value="">Select…</option>
          {field.options.filter(o => o.active_flag).map(o => (
            <option key={o.option_value} value={o.option_value}>{o.option_label}</option>
          ))}
        </select>
      );
    case "multi_select": {
      const selected = Array.isArray(value) ? (value as string[]) : [];
      return (
        <div className="flex flex-wrap gap-3 py-1">
          {field.options.filter(o => o.active_flag).map(o => (
            <label key={o.option_value} className="flex items-center gap-1.5 cursor-pointer">
              <input type="checkbox"
                checked={selected.includes(o.option_value)}
                onChange={e => {
                  const updated = e.target.checked
                    ? [...selected, o.option_value]
                    : selected.filter(v => v !== o.option_value);
                  onChange(updated);
                }}
                className="w-3.5 h-3.5" />
              <span className="text-sm text-gray-700">{o.option_label}</span>
            </label>
          ))}
        </div>
      );
    }
    case "file_attachment":
      return (
        <input type="text" className={cls}
          placeholder="File name or path…"
          value={(value as string) ?? ""}
          onChange={e => onChange(e.target.value)} />
      );
    default:
      return (
        <input type="text" className={cls}
          value={(value as string) ?? ""}
          placeholder={field.placeholder ?? ""}
          onChange={e => onChange(e.target.value)} />
      );
  }
}

export default function CustomFieldsForm({
  entityType, entityId, currentUser = "User",
  onChange, readOnly = false, compact = false,
}: Props) {
  const [fields, setFields] = useState<CustomFieldDefinition[]>([]);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const fs = await customFieldsApi.getEntityFields(entityType);
      setFields(fs);
      const defaults: Record<string, unknown> = {};
      fs.forEach(f => { if (f.default_value) defaults[f.field_code] = f.default_value; });
      if (entityId) {
        const vals = await customFieldsApi.getValues(entityType, entityId);
        vals.forEach(v => { if (v.value !== null && v.value !== undefined) defaults[v.field_code] = v.value; });
      }
      setValues(defaults);
    } finally {
      setLoading(false);
    }
  }, [entityType, entityId]);

  useEffect(() => { load(); }, [load]);

  const handleChange = (fieldCode: string, value: unknown) => {
    const updated = { ...values, [fieldCode]: value };
    setValues(updated);
    onChange?.(updated);
  };

  const save = async () => {
    if (!entityId) return;
    setSaving(true);
    try {
      await customFieldsApi.setValues(entityType, entityId, values, currentUser);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="text-xs text-gray-400 py-2">Loading custom fields…</p>;
  if (fields.length === 0) return null;

  // Group by section
  const sections: Record<string, CustomFieldDefinition[]> = {};
  fields.forEach(f => {
    const sec = f.section_label || "Custom Fields";
    sections[sec] = sections[sec] ?? [];
    sections[sec].push(f);
  });

  return (
    <div className={compact ? "space-y-4" : "space-y-6"}>
      {Object.entries(sections).map(([section, sectionFields]) => (
        <div key={section}>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
            <span>{section}</span>
            <div className="h-px flex-1 bg-gray-200" />
          </h3>
          <div className={compact ? "space-y-3" : "grid grid-cols-1 gap-4 md:grid-cols-2"}>
            {sectionFields.map(field => (
              <div key={field.custom_field_id} className={field.field_type === "long_text" ? "md:col-span-2" : ""}>
                <label className="text-xs text-gray-500 block mb-1">
                  {field.field_label}
                  {field.required_flag && <span className="text-red-500 ml-0.5">*</span>}
                  {field.sensitive_flag && <span className="text-orange-500 ml-1 text-xs">(sensitive)</span>}
                  {field.field_type === "computed" && <span className="text-gray-400 ml-1">∑ computed</span>}
                </label>
                {renderInput(field, values[field.field_code], v => handleChange(field.field_code, v), readOnly)}
                {field.help_text && <p className="text-xs text-gray-400 mt-0.5">{field.help_text}</p>}
              </div>
            ))}
          </div>
        </div>
      ))}

      {!readOnly && entityId && (
        <div className="flex items-center gap-3">
          <button onClick={save} disabled={saving}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Saving…" : "Save Custom Fields"}
          </button>
          {saved && <span className="text-sm text-green-600">✓ Saved</span>}
        </div>
      )}
    </div>
  );
}
