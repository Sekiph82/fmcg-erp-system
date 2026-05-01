"use client";
import { useEffect, useState } from "react";
import {
  customFieldsApi, CustomFieldDefinition, UsageStat,
  ENTITY_LABEL, FIELD_TYPE_LABEL, EntityType,
} from "@/lib/custom_fields";

type Tab = "definitions" | "usage" | "missing" | "flags";

export default function CustomFieldsReportsPage() {
  const [tab, setTab] = useState<Tab>("definitions");
  const [fields, setFields] = useState<CustomFieldDefinition[]>([]);
  const [stats, setStats] = useState<UsageStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      customFieldsApi.listFields({ active_only: false }),
      customFieldsApi.getUsageStats(),
    ]).then(([f, s]) => { setFields(f); setStats(s); }).finally(() => setLoading(false));
  }, []);

  const tabs: { key: Tab; label: string }[] = [
    { key: "definitions", label: "Field Definitions" },
    { key: "usage", label: "Usage Stats" },
    { key: "missing", label: "Coverage" },
    { key: "flags", label: "Flag Summary" },
  ];

  const byEntity: Record<string, CustomFieldDefinition[]> = {};
  fields.filter(f => f.active_flag).forEach(f => {
    const et = String(f.entity_type);
    byEntity[et] = byEntity[et] ?? [];
    byEntity[et].push(f);
  });

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Custom Fields Reports</h1>

      <div className="flex border-b">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === t.key ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <p className="text-sm text-gray-500 text-center py-8">Loading…</p> : (
        <>
          {tab === "definitions" && (
            <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    {["Label", "Code", "Module", "Type", "Req", "Active", "Created"].map(h => (
                      <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {fields.map(f => (
                    <tr key={f.custom_field_id} className={`hover:bg-gray-50 ${!f.active_flag ? "opacity-60" : ""}`}>
                      <td className="px-4 py-2 font-medium text-gray-800">{f.field_label}</td>
                      <td className="px-4 py-2 font-mono text-xs text-gray-400">{f.field_code}</td>
                      <td className="px-4 py-2 text-gray-600 text-xs">{ENTITY_LABEL[f.entity_type] ?? f.entity_type}</td>
                      <td className="px-4 py-2 text-gray-600 text-xs">{FIELD_TYPE_LABEL[f.field_type]}</td>
                      <td className="px-4 py-2">{f.required_flag ? <span className="text-red-500">✓</span> : "—"}</td>
                      <td className="px-4 py-2">
                        <span className={`text-xs rounded-full px-2 py-0.5 ${f.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                          {f.active_flag ? "active" : "disabled"}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-400 text-xs">{new Date(f.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {fields.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No fields defined.</p>}
            </div>
          )}

          {tab === "usage" && (
            <div className="bg-white border rounded-lg shadow-sm p-5 space-y-3">
              <h2 className="font-semibold text-gray-800 text-sm mb-4">Field Usage (values recorded)</h2>
              {stats.map(s => {
                const max = Math.max(...stats.map(x => x.value_count), 1);
                const pct = Math.round((s.value_count / max) * 100);
                return (
                  <div key={s.custom_field_id}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-gray-700">{s.field_label} <span className="text-gray-400 text-xs">({s.entity_type.replace("_", " ")})</span></span>
                      <span className="font-semibold">{s.value_count}</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div className={`h-2 rounded-full ${s.value_count === 0 ? "bg-gray-300" : "bg-blue-500"}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
              {stats.length === 0 && <p className="text-sm text-gray-400">No usage data yet.</p>}
            </div>
          )}

          {tab === "missing" && (
            <div className="bg-white border rounded-lg shadow-sm p-5">
              <h2 className="font-semibold text-gray-800 text-sm mb-4">Module Coverage</h2>
              <div className="space-y-4">
                {Object.entries(byEntity).map(([et, etFields]) => {
                  const required = etFields.filter(f => f.required_flag);
                  return (
                    <div key={et} className="border rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-medium text-gray-800">{ENTITY_LABEL[et as EntityType] ?? et}</p>
                        <p className="text-sm text-gray-500">{etFields.length} fields, {required.length} required</p>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {etFields.map(f => (
                          <span key={f.custom_field_id}
                            className={`text-xs rounded px-2 py-0.5 ${f.required_flag ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600"}`}>
                            {f.field_label}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {Object.keys(byEntity).length === 0 && <p className="text-sm text-gray-400">No fields defined yet.</p>}
              </div>
            </div>
          )}

          {tab === "flags" && (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {[
                { label: "Required", count: fields.filter(f => f.required_flag && f.active_flag).length, color: "text-red-500" },
                { label: "Searchable", count: fields.filter(f => f.searchable_flag && f.active_flag).length, color: "text-blue-600" },
                { label: "Filterable", count: fields.filter(f => f.filterable_flag && f.active_flag).length, color: "text-purple-600" },
                { label: "Reportable", count: fields.filter(f => f.reportable_flag && f.active_flag).length, color: "text-green-600" },
                { label: "Importable", count: fields.filter(f => f.importable_flag && f.active_flag).length, color: "text-orange-600" },
                { label: "Sensitive", count: fields.filter(f => f.sensitive_flag && f.active_flag).length, color: "text-red-700" },
                { label: "Unique", count: fields.filter(f => f.unique_flag && f.active_flag).length, color: "text-gray-700" },
                { label: "With Options", count: fields.filter(f => f.options.length > 0).length, color: "text-teal-600" },
                { label: "With Rules", count: fields.filter(f => f.validation_rules.length > 0).length, color: "text-indigo-600" },
              ].map(s => (
                <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
                  <p className="text-xs text-gray-500">{s.label}</p>
                  <p className={`text-3xl font-bold mt-1 ${s.color}`}>{s.count}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
