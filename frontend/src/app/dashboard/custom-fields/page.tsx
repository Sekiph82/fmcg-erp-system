"use client";
import { useEffect, useState } from "react";
import {
  customFieldsApi, CustomFieldDefinition, UsageStat,
  ENTITY_LABEL, FIELD_TYPE_LABEL, EntityType,
} from "@/lib/custom_fields";

export default function CustomFieldsDashboard() {
  const [fields, setFields] = useState<CustomFieldDefinition[]>([]);
  const [stats, setStats] = useState<UsageStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      customFieldsApi.listFields({ active_only: false }),
      customFieldsApi.getUsageStats(),
    ]).then(([f, s]) => { setFields(f); setStats(s); }).finally(() => setLoading(false));
  }, []);

  const activeFields = fields.filter(f => f.active_flag);
  const requiredFields = activeFields.filter(f => f.required_flag);
  const entitiesWithFields = new Set(activeFields.map(f => f.entity_type)).size;
  const totalValues = stats.reduce((a, s) => a + s.value_count, 0);

  // By entity type
  const byEntity: Record<string, number> = {};
  activeFields.forEach(f => {
    const et = String(f.entity_type);
    byEntity[et] = (byEntity[et] ?? 0) + 1;
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Custom Fields</h1>
        <a href="/dashboard/custom-fields/new-field"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Create Field
        </a>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Active Fields", value: activeFields.length, color: "text-blue-600" },
          { label: "Required Fields", value: requiredFields.length, color: "text-red-500" },
          { label: "Entities Covered", value: entitiesWithFields, color: "text-green-600" },
          { label: "Total Values", value: totalValues, color: "text-purple-600" },
        ].map(s => (
          <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold mt-1 ${s.color}`}>{loading ? "—" : s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="bg-white border rounded-lg shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 text-sm mb-4">Fields by Module</h2>
          {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
            <div className="space-y-2">
              {Object.entries(byEntity).sort((a, b) => b[1] - a[1]).map(([et, count]) => {
                const max = Math.max(...Object.values(byEntity), 1);
                const pct = Math.round((count / max) * 100);
                return (
                  <div key={et}>
                    <div className="flex justify-between text-sm mb-0.5">
                      <span className="text-gray-700">
                        {ENTITY_LABEL[et as EntityType] ?? et.replace("_", " ")}
                      </span>
                      <span className="font-semibold">{count}</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div className="h-2 rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
              {Object.keys(byEntity).length === 0 && <p className="text-sm text-gray-400">No fields yet.</p>}
            </div>
          )}
        </div>

        <div className="bg-white border rounded-lg shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 text-sm mb-4">Most Used Fields</h2>
          {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
            <div className="divide-y">
              {stats.slice(0, 8).map(s => (
                <div key={s.custom_field_id} className="py-2 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{s.field_label}</p>
                    <p className="text-xs text-gray-400 capitalize">{s.entity_type.replace("_", " ")}</p>
                  </div>
                  <span className="text-sm font-semibold text-blue-600">{s.value_count}</span>
                </div>
              ))}
              {stats.length === 0 && <p className="text-sm text-gray-400">No values recorded yet.</p>}
            </div>
          )}
        </div>
      </div>

      <div className="bg-white border rounded-lg shadow-sm">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800 text-sm">Recent Fields</h2>
          <a href="/dashboard/custom-fields/fields" className="text-xs text-blue-600 hover:underline">View all</a>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Label", "Code", "Module", "Type", "Required", "Values", "Status"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {fields.slice(0, 10).map(f => {
                const usage = stats.find(s => s.custom_field_id === f.custom_field_id);
                return (
                  <tr key={f.custom_field_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium text-gray-800">
                      <a href={`/dashboard/custom-fields/${f.custom_field_id}`} className="hover:text-blue-600">
                        {f.field_label}
                      </a>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-500">{f.field_code}</td>
                    <td className="px-4 py-2 text-gray-600 capitalize">{ENTITY_LABEL[f.entity_type] ?? f.entity_type}</td>
                    <td className="px-4 py-2 text-gray-600 text-xs">{FIELD_TYPE_LABEL[f.field_type]}</td>
                    <td className="px-4 py-2">{f.required_flag ? <span className="text-red-500">✓</span> : <span className="text-gray-300">—</span>}</td>
                    <td className="px-4 py-2 text-gray-600">{usage?.value_count ?? 0}</td>
                    <td className="px-4 py-2">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${f.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                        {f.active_flag ? "active" : "disabled"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {fields.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No custom fields yet.</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
        {[
          { href: "/dashboard/custom-fields/fields", label: "Field Manager", icon: "📋" },
          { href: "/dashboard/custom-fields/form-builder", label: "Form Builder", icon: "🎨" },
          { href: "/dashboard/custom-fields/workflow-rules", label: "Workflow Rules", icon: "⚡" },
          { href: "/dashboard/custom-fields/new-field", label: "New Field", icon: "➕" },
          { href: "/dashboard/custom-fields/values", label: "Values Browser", icon: "🔍" },
          { href: "/dashboard/custom-fields/ai", label: "AI Insights", icon: "🤖" },
        ].map(l => (
          <a key={l.href} href={l.href}
            className="bg-white border rounded-lg p-4 shadow-sm hover:bg-gray-50 text-center">
            <div className="text-2xl mb-1">{l.icon}</div>
            <p className="text-sm font-medium text-gray-700">{l.label}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
