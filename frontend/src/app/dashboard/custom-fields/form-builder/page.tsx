"use client";
import { useEffect, useState, useRef } from "react";
import {
  customFieldsApi, CustomFieldDefinition, EntityType, FormLayoutItem,
  ENTITY_LABEL, FIELD_TYPE_ICON, FIELD_TYPE_LABEL, FIELD_WIDTH_LABEL,
} from "@/lib/custom_fields";

const ENTITY_TYPES: EntityType[] = [
  "customer", "supplier", "product", "sales_order", "purchase_order",
  "production_order", "employee", "asset", "contract", "crm_record", "expense", "lot",
];

type DragMode = "field" | null;

export default function FormBuilderPage() {
  const [entityType, setEntityType] = useState<EntityType>("customer");
  const [fields, setFields] = useState<CustomFieldDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [tab, setTab] = useState<"builder" | "preview">("builder");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editSection, setEditSection] = useState("");
  const [editWidth, setEditWidth] = useState<"full" | "half" | "third">("full");

  const dragIdx = useRef<number | null>(null);

  const load = async (et: EntityType) => {
    setLoading(true);
    setEditingId(null);
    try {
      const data = await customFieldsApi.getFormLayout(et);
      setFields(data.length ? data : []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(entityType); }, [entityType]);

  const handleDragStart = (idx: number) => { dragIdx.current = idx; };

  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (dragIdx.current === null || dragIdx.current === idx) return;
    const updated = [...fields];
    const [moved] = updated.splice(dragIdx.current, 1);
    updated.splice(idx, 0, moved);
    dragIdx.current = idx;
    setFields(updated.map((f, i) => ({ ...f, display_order: i })));
  };

  const handleDragEnd = () => { dragIdx.current = null; };

  const openEdit = (f: CustomFieldDefinition) => {
    setEditingId(f.custom_field_id);
    setEditSection(f.section_label ?? "");
    setEditWidth((f.field_width as "full" | "half" | "third") ?? "full");
  };

  const applyEdit = () => {
    if (!editingId) return;
    setFields(prev => prev.map(f =>
      f.custom_field_id === editingId
        ? { ...f, section_label: editSection || undefined, field_width: editWidth }
        : f
    ));
    setEditingId(null);
  };

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const items: FormLayoutItem[] = fields.map((f, i) => ({
        custom_field_id: f.custom_field_id,
        display_order: i,
        section_label: f.section_label ?? undefined,
        field_width: f.field_width ?? "full",
      }));
      const updated = await customFieldsApi.reorderFormLayout(entityType, items);
      setFields(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  // Group fields by section for preview
  const sections: Record<string, CustomFieldDefinition[]> = {};
  for (const f of fields) {
    const sec = f.section_label || "General";
    if (!sections[sec]) sections[sec] = [];
    sections[sec].push(f);
  }

  const widthClass: Record<string, string> = {
    full: "col-span-2",
    half: "col-span-1",
    third: "col-span-1 md:col-span-1",
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Form Builder</h1>
          <p className="text-xs text-gray-500 mt-0.5">Drag fields to reorder. Set sections and widths. Save layout.</p>
        </div>
        <div className="flex gap-2 items-center">
          <select
            className="border rounded px-2 py-1.5 text-sm"
            value={entityType}
            onChange={e => setEntityType(e.target.value as EntityType)}
          >
            {ENTITY_TYPES.map(t => <option key={t} value={t}>{ENTITY_LABEL[t]}</option>)}
          </select>
          <div className="flex border rounded overflow-hidden text-sm">
            <button
              onClick={() => setTab("builder")}
              className={`px-3 py-1.5 ${tab === "builder" ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            >
              Builder
            </button>
            <button
              onClick={() => setTab("preview")}
              className={`px-3 py-1.5 ${tab === "preview" ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            >
              Preview
            </button>
          </div>
          {tab === "builder" && (
            <button
              onClick={save}
              disabled={saving}
              className="rounded bg-green-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {saving ? "Saving…" : saved ? "Saved!" : "Save Layout"}
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading fields…</p>
      ) : fields.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-sm">No active custom fields for {ENTITY_LABEL[entityType]}.</p>
          <a href="/dashboard/custom-fields/new-field" className="text-xs text-blue-600 hover:underline mt-2 block">
            Create a field first →
          </a>
        </div>
      ) : tab === "builder" ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Field list with drag */}
          <div className="lg:col-span-2 space-y-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Drag to reorder — {fields.length} fields
            </p>
            {fields.map((f, idx) => (
              <div
                key={f.custom_field_id}
                draggable
                onDragStart={() => handleDragStart(idx)}
                onDragOver={e => handleDragOver(e, idx)}
                onDragEnd={handleDragEnd}
                className={`flex items-center gap-3 bg-white border rounded-lg px-4 py-3 cursor-grab active:cursor-grabbing shadow-sm hover:shadow transition-shadow ${editingId === f.custom_field_id ? "ring-2 ring-blue-400" : ""}`}
              >
                <span className="text-gray-300 text-lg select-none">⋮⋮</span>
                <span className="w-6 text-center text-xs text-gray-400 font-mono">{idx + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {f.field_label}
                    {f.required_flag && <span className="text-red-400 ml-1">*</span>}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-gray-400 font-mono">{f.field_code}</span>
                    <span className="text-xs bg-gray-100 text-gray-600 rounded px-1">
                      {FIELD_TYPE_ICON[f.field_type]} {FIELD_TYPE_LABEL[f.field_type]}
                    </span>
                    {f.section_label && (
                      <span className="text-xs bg-blue-50 text-blue-600 rounded px-1.5 py-0.5">
                        {f.section_label}
                      </span>
                    )}
                    <span className="text-xs bg-purple-50 text-purple-600 rounded px-1.5 py-0.5">
                      {FIELD_WIDTH_LABEL[f.field_width ?? "full"]}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => openEdit(f)}
                  className="text-xs text-blue-600 hover:underline whitespace-nowrap"
                >
                  Edit layout
                </button>
              </div>
            ))}
          </div>

          {/* Edit panel */}
          <div className="bg-white border rounded-lg p-5 h-fit">
            {editingId ? (
              <>
                <h3 className="text-sm font-semibold text-gray-800 mb-4">
                  Layout Settings
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Section Label</label>
                    <input
                      type="text"
                      value={editSection}
                      onChange={e => setEditSection(e.target.value)}
                      placeholder="e.g. Contact Details"
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                    <p className="text-xs text-gray-400 mt-1">Groups this field under a section heading in the form</p>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Field Width</label>
                    <select
                      value={editWidth}
                      onChange={e => setEditWidth(e.target.value as "full" | "half" | "third")}
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    >
                      <option value="full">Full Width (12 cols)</option>
                      <option value="half">Half Width (6 cols)</option>
                      <option value="third">One Third (4 cols)</option>
                    </select>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={applyEdit}
                      className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700"
                    >
                      Apply
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-6 text-gray-400">
                <p className="text-2xl mb-2">✏️</p>
                <p className="text-sm">Click &quot;Edit layout&quot; on a field to set its section and width.</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Preview tab */
        <div className="bg-white border rounded-lg p-6 space-y-6">
          <p className="text-xs text-gray-500">
            Preview of form layout for <strong>{ENTITY_LABEL[entityType]}</strong>.
            This is how custom fields will appear on the record form.
          </p>
          {Object.entries(sections).map(([section, sFields]) => (
            <div key={section}>
              <h3 className="text-sm font-semibold text-gray-700 border-b pb-2 mb-4">{section}</h3>
              <div className="grid grid-cols-2 gap-4">
                {sFields.map(f => (
                  <div
                    key={f.custom_field_id}
                    className={`${widthClass[f.field_width ?? "full"]} space-y-1`}
                  >
                    <label className="block text-xs font-medium text-gray-600">
                      {f.field_label}
                      {f.required_flag && <span className="text-red-400 ml-0.5">*</span>}
                    </label>
                    <div className="border rounded px-3 py-2 text-sm text-gray-400 bg-gray-50">
                      {f.placeholder ?? `Enter ${f.field_label.toLowerCase()}…`}
                    </div>
                    {f.help_text && (
                      <p className="text-xs text-gray-400">{f.help_text}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3 text-xs">
        <a href="/dashboard/custom-fields/fields" className="text-blue-600 hover:underline">Field Manager</a>
        <span className="text-gray-300">|</span>
        <a href="/dashboard/custom-fields/workflow-rules" className="text-blue-600 hover:underline">Workflow Rules</a>
        <span className="text-gray-300">|</span>
        <a href="/dashboard/custom-fields/new-field" className="text-blue-600 hover:underline">Create Field</a>
      </div>
    </div>
  );
}
