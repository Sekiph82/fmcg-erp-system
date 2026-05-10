"use client";
import { useCallback, useEffect, useState } from "react";
import {
  customFieldsApi, CustomFieldDefinition, EntityType,
  ENTITY_LABEL, FIELD_TYPE_LABEL, FIELD_TYPE_ICON,
} from "@/lib/custom_fields";

const ENTITY_TYPES: EntityType[] = [
  "customer", "supplier", "product", "sales_order", "purchase_order",
  "production_order", "employee", "asset", "contract", "crm_record", "expense", "lot",
];

export default function FieldManagerPage() {
  const [fields, setFields] = useState<CustomFieldDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterEntity, setFilterEntity] = useState("");
  const [filterActive, setFilterActive] = useState("");

  const load = useCallback(() =>
    customFieldsApi.listFields({
      entity_type: filterEntity || undefined,
      active_only: filterActive === "true" ? true : filterActive === "false" ? false : undefined,
    } as Parameters<typeof customFieldsApi.listFields>[0])
      .then(setFields).finally(() => setLoading(false)), [filterEntity, filterActive]);

  useEffect(() => { load(); }, [load]);

  const disable = async (id: string) => {
    if (!confirm("Disable this field? Values will be preserved.")) return;
    await customFieldsApi.disableField(id);
    load();
  };

  const enable = async (id: string) => {
    await customFieldsApi.updateField(id, { active_flag: true });
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold text-gray-900">Field Manager</h1>
        <a href="/dashboard/custom-fields/new-field"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Create Field
        </a>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select className="border rounded px-2 py-1.5 text-sm" value={filterEntity}
          onChange={e => setFilterEntity(e.target.value)}>
          <option value="">All Modules</option>
          {ENTITY_TYPES.map(t => <option key={t} value={t}>{ENTITY_LABEL[t]}</option>)}
        </select>
        <select className="border rounded px-2 py-1.5 text-sm" value={filterActive}
          onChange={e => setFilterActive(e.target.value)}>
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Disabled</option>
        </select>
        <span className="text-xs text-gray-500 self-center">{fields.length} fields</span>
      </div>

      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Label", "Code", "Module", "Type", "Flags", "Order", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {fields.map(f => (
                <tr key={f.custom_field_id} className={`hover:bg-gray-50 ${!f.active_flag ? "opacity-60" : ""}`}>
                  <td className="px-4 py-2 font-medium text-gray-800">
                    <a href={`/dashboard/custom-fields/${f.custom_field_id}`} className="hover:text-blue-600">
                      {f.field_label}
                      {f.required_flag && <span className="text-red-400 ml-1 text-xs">*</span>}
                    </a>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{f.field_code}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{ENTITY_LABEL[f.entity_type] ?? f.entity_type}</td>
                  <td className="px-4 py-2">
                    <span className="text-xs bg-gray-100 text-gray-700 rounded px-1.5 py-0.5">
                      {FIELD_TYPE_ICON[f.field_type]} {FIELD_TYPE_LABEL[f.field_type]}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-1 flex-wrap">
                      {f.searchable_flag && <span className="text-xs bg-blue-50 text-blue-600 rounded px-1">Search</span>}
                      {f.filterable_flag && <span className="text-xs bg-purple-50 text-purple-600 rounded px-1">Filter</span>}
                      {f.reportable_flag && <span className="text-xs bg-green-50 text-green-600 rounded px-1">Report</span>}
                      {f.sensitive_flag && <span className="text-xs bg-red-50 text-red-500 rounded px-1">🔒</span>}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{f.display_order}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${f.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {f.active_flag ? "active" : "disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      <a href={`/dashboard/custom-fields/${f.custom_field_id}`}
                        className="text-xs text-blue-600 hover:underline">Edit</a>
                      {f.active_flag
                        ? <button onClick={() => disable(f.custom_field_id)}
                            className="text-xs text-red-500 hover:underline">Disable</button>
                        : <button onClick={() => enable(f.custom_field_id)}
                            className="text-xs text-green-600 hover:underline">Enable</button>
                      }
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {fields.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No fields found.</p>}
        </div>
      )}
    </div>
  );
}
