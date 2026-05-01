"use client";
import { useState } from "react";
import {
  customFieldsApi, FieldValueOut, EntityType,
  ENTITY_LABEL, FIELD_TYPE_LABEL,
} from "@/lib/custom_fields";

const ENTITY_TYPES: EntityType[] = [
  "customer", "supplier", "product", "sales_order", "purchase_order",
  "production_order", "employee", "asset", "contract", "crm_record", "expense", "lot",
];

export default function ValuesBrowserPage() {
  const [entityType, setEntityType] = useState<EntityType>("customer");
  const [entityId, setEntityId] = useState("");
  const [values, setValues] = useState<FieldValueOut[]>([]);
  const [missing, setMissing] = useState<{ entity_id: string; field_code: string; field_label: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const lookup = async () => {
    if (!entityId.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const vals = await customFieldsApi.getValues(entityType, entityId.trim());
      setValues(vals);
      const ev: Record<string, unknown> = {};
      vals.forEach(v => { ev[v.field_code] = v.value; });
      setEditValues(ev);
    } finally {
      setLoading(false);
    }
  };

  const loadMissing = async () => {
    setLoading(true);
    try {
      const m = await customFieldsApi.getMissingRequired(entityType);
      setMissing(m);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const saveEdit = async () => {
    if (!entityId) return;
    setSaving(true);
    try {
      await customFieldsApi.setValues(entityType, entityId, editValues);
      setSaved(true);
      setEditMode(false);
      setTimeout(() => setSaved(false), 2000);
      await lookup();
    } finally {
      setSaving(false);
    }
  };

  const renderEditInput = (v: FieldValueOut) => {
    const cls = "w-full border rounded px-2 py-1 text-sm";
    const cur = editValues[v.field_code];
    switch (v.field_type) {
      case "boolean":
        return <input type="checkbox" checked={!!cur} onChange={e => setEditValues({ ...editValues, [v.field_code]: e.target.checked })} />;
      case "number": case "decimal": case "currency":
        return <input type="number" className={cls} value={cur as number ?? ""} onChange={e => setEditValues({ ...editValues, [v.field_code]: e.target.value })} />;
      case "date":
        return <input type="date" className={cls} value={(cur as string)?.slice(0, 10) ?? ""} onChange={e => setEditValues({ ...editValues, [v.field_code]: e.target.value })} />;
      default:
        return <input type="text" className={cls} value={(cur as string) ?? ""} onChange={e => setEditValues({ ...editValues, [v.field_code]: e.target.value })} />;
    }
  };

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <h1 className="text-xl font-bold text-gray-900">Values Browser</h1>

      <div className="bg-white border rounded-lg p-5 space-y-3 shadow-sm">
        <h2 className="font-semibold text-gray-800 text-sm">Look Up Entity Values</h2>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Module</label>
            <select className="w-full border rounded px-2 py-1.5 text-sm" value={entityType}
              onChange={e => { setEntityType(e.target.value as EntityType); setSearched(false); }}>
              {ENTITY_TYPES.map(t => <option key={t} value={t}>{ENTITY_LABEL[t]}</option>)}
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-500 block mb-1">Entity ID</label>
            <div className="flex gap-2">
              <input className="flex-1 border rounded px-2 py-1.5 text-sm" placeholder="Paste UUID of the record…"
                value={entityId} onChange={e => setEntityId(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") lookup(); }} />
              <button onClick={lookup} className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700">
                Look Up
              </button>
            </div>
          </div>
        </div>
        <button onClick={loadMissing} className="text-xs text-orange-600 hover:underline">
          Show missing required values for {ENTITY_LABEL[entityType]}
        </button>
      </div>

      {loading && <p className="text-sm text-gray-500 text-center py-6">Loading…</p>}

      {searched && !loading && entityId && values.length === 0 && (
        <div className="bg-white border rounded-lg p-5 text-center">
          <p className="text-sm text-gray-400">No custom field values recorded for this entity. The entity may have custom fields defined but no values saved yet.</p>
        </div>
      )}

      {searched && !loading && entityId && values.length > 0 && (
        <div className="bg-white border rounded-lg shadow-sm">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-800 text-sm">Custom Field Values</h2>
            <div className="flex gap-2">
              {saved && <span className="text-sm text-green-600">✓ Saved</span>}
              {editMode
                ? <>
                    <button onClick={saveEdit} disabled={saving}
                      className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
                      {saving ? "Saving…" : "Save"}
                    </button>
                    <button onClick={() => setEditMode(false)}
                      className="rounded border px-3 py-1 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
                  </>
                : <button onClick={() => setEditMode(true)}
                    className="rounded border px-3 py-1 text-sm text-gray-600 hover:bg-gray-50">Edit</button>
              }
            </div>
          </div>
          <div className="divide-y">
            {values.map(v => (
              <div key={v.custom_field_id} className="px-4 py-3 flex items-start gap-4">
                <div className="w-40 shrink-0">
                  <p className="text-sm font-medium text-gray-700">
                    {v.field_label}
                    {v.required_flag && <span className="text-red-400 ml-1">*</span>}
                    {v.sensitive_flag && <span className="text-orange-400 ml-1 text-xs">🔒</span>}
                  </p>
                  <p className="text-xs text-gray-400 font-mono">{v.field_code}</p>
                </div>
                <div className="flex-1">
                  {editMode
                    ? renderEditInput(v)
                    : <p className="text-sm text-gray-800">{v.display_value ?? <span className="text-gray-400 italic">no value</span>}</p>
                  }
                </div>
                <span className="text-xs text-gray-300 w-20 text-right">{FIELD_TYPE_LABEL[v.field_type]}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {searched && !loading && missing.length > 0 && !entityId && (
        <div className="bg-white border rounded-lg shadow-sm">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-gray-800 text-sm">
              Missing Required Values ({missing.length} gaps found)
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {["Entity ID", "Field", "Field Code"].map(h => (
                    <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {missing.slice(0, 50).map((m, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs text-gray-500 max-w-[200px] truncate">{m.entity_id}</td>
                    <td className="px-4 py-2 text-orange-600 font-medium">{m.field_label}</td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-400">{m.field_code}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
