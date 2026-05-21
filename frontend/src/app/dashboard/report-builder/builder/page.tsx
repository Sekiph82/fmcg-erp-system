"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  reportBuilderApi, DataSource, DataSourceField,
  AggregationType, FilterOperator, SortDirection,
  AGG_TYPES, FILTER_OPS, AGG_LABEL, OP_LABEL,
} from "@/lib/report_builder";

interface FieldRow {
  field_path: string;
  alias: string;
  aggregation: AggregationType;
  is_group_by: boolean;
  sort_direction: SortDirection | "";
}

interface FilterRow {
  field_path: string;
  operator: FilterOperator;
  value: string;
  value_to: string;
  logical_op: "and" | "or";
}

export default function ReportBuilderPage() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<Record<string, DataSource>>({});
  const [reportCode, setReportCode] = useState("");
  const [reportName, setReportName] = useState("");
  const [dataSource, setDataSource] = useState("");
  const [dsInfo, setDsInfo] = useState<DataSource | null>(null);
  const [fields, setFields] = useState<FieldRow[]>([]);
  const [filters, setFilters] = useState<FilterRow[]>([]);
  const [visibility, setVisibility] = useState<"private" | "team" | "global">("team");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { reportBuilderApi.getCatalog().then(setCatalog); }, []);

  const selectDS = (key: string) => {
    setDataSource(key);
    setDsInfo(catalog[key] ?? null);
    setFields([]);
    setFilters([]);
  };

  const addField = (f: DataSourceField) => {
    if (fields.find(r => r.field_path === f.path)) return;
    setFields([...fields, { field_path: f.path, alias: f.label, aggregation: "none", is_group_by: false, sort_direction: "" }]);
  };

  const updateField = (i: number, key: keyof FieldRow, val: unknown) => {
    const n = [...fields];
    ((n[i] as unknown) as Record<string, unknown>)[key] = val;
    setFields(n);
  };

  const removeField = (i: number) => setFields(fields.filter((_, j) => j !== i));

  const addFilter = () => {
    if (!dsInfo) return;
    setFilters([...filters, { field_path: dsInfo.fields[0]?.path ?? "", operator: "eq", value: "", value_to: "", logical_op: "and" }]);
  };

  const updateFilter = (i: number, key: keyof FilterRow, val: string) => {
    const n = [...filters];
    ((n[i] as unknown) as Record<string, unknown>)[key] = val;
    setFilters(n);
  };

  const save = async () => {
    if (!reportCode || !reportName || !dataSource) { setError("Code, Name, and Data Source are required"); return; }
    setError("");
    setSaving(true);
    try {
      const report = await reportBuilderApi.createReport({
        report_code: reportCode,
        report_name: reportName,
        data_source: dataSource,
        visibility,
        fields: fields.map((f, i) => ({ ...f, position: i, sort_direction: f.sort_direction || undefined })),
        filters: filters.map((f, i) => ({ ...f, position: i })),
      });
      router.push(`/dashboard/report-builder/viewer?id=${report.report_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <h1 className="text-xl font-bold text-gray-900">Build Report</h1>
      {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 text-sm">{error}</div>}

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <h2 className="font-semibold text-gray-800">1. Report Details</h2>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-xs text-gray-500">Report Code *</label>
            <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={reportCode}
              onChange={(e) => setReportCode(e.target.value)} placeholder="MY-REPORT-001" /></div>
          <div><label className="text-xs text-gray-500">Report Name *</label>
            <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={reportName}
              onChange={(e) => setReportName(e.target.value)} /></div>
          <div><label className="text-xs text-gray-500">Visibility</label>
            <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={visibility}
              onChange={(e) => setVisibility(e.target.value as typeof visibility)}>
              {(["private","team","global"] as const).map(v => <option key={v} value={v}>{v}</option>)}
            </select></div>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <h2 className="font-semibold text-gray-800">2. Select Data Source *</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {Object.entries(catalog).map(([key, ds]) => (
            <button key={key} onClick={() => selectDS(key)}
              className={`rounded border px-3 py-2 text-xs text-left transition-colors ${dataSource === key ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-700 hover:bg-gray-50"}`}>
              <p className="font-semibold">{ds.label}</p>
              <p className="opacity-70">{ds.field_count} fields</p>
            </button>
          ))}
        </div>
      </div>

      {dsInfo && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">3. Select Fields</h2>
          <div className="flex flex-wrap gap-2 mb-3">
            {dsInfo.fields.map(f => (
              <button key={f.path} onClick={() => addField(f)}
                className={`rounded border px-2 py-1 text-xs ${fields.find(r => r.field_path === f.path) ? "bg-blue-100 text-blue-700 border-blue-300" : "bg-gray-50 text-gray-600 hover:bg-gray-100"}`}>
                {f.label} <span className="text-gray-400">({f.type})</span>
              </button>
            ))}
          </div>

          {fields.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-50 border-b"><tr>
                  {["Field","Alias","Aggregation","Group By","Sort",""].map(h=><th key={h} className="px-2 py-1.5 text-left text-gray-600">{h}</th>)}
                </tr></thead>
                <tbody className="divide-y">
                  {fields.map((f, i) => (
                    <tr key={i}>
                      <td className="px-2 py-1.5 font-mono text-gray-700">{f.field_path}</td>
                      <td className="px-2 py-1.5">
                        <input className="border rounded px-1.5 py-0.5 text-xs w-28" value={f.alias}
                          onChange={(e) => updateField(i, "alias", e.target.value)} />
                      </td>
                      <td className="px-2 py-1.5">
                        <select className="border rounded px-1.5 py-0.5 text-xs" value={f.aggregation}
                          onChange={(e) => updateField(i, "aggregation", e.target.value)}>
                          {AGG_TYPES.map(a => <option key={a} value={a}>{AGG_LABEL[a]}</option>)}
                        </select>
                      </td>
                      <td className="px-2 py-1.5 text-center">
                        <input type="checkbox" checked={f.is_group_by}
                          onChange={(e) => updateField(i, "is_group_by", e.target.checked)} />
                      </td>
                      <td className="px-2 py-1.5">
                        <select className="border rounded px-1.5 py-0.5 text-xs" value={f.sort_direction}
                          onChange={(e) => updateField(i, "sort_direction", e.target.value)}>
                          <option value="">None</option>
                          <option value="asc">ASC</option>
                          <option value="desc">DESC</option>
                        </select>
                      </td>
                      <td className="px-2 py-1.5">
                        <button onClick={() => removeField(i)} className="text-red-400 hover:text-red-600">✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {dsInfo && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">4. Add Filters</h2>
            <button onClick={addFilter} className="text-xs text-blue-600 hover:underline">+ Add Filter</button>
          </div>
          {filters.map((f, i) => (
            <div key={i} className="grid grid-cols-5 gap-2 items-center">
              {i > 0 && (
                <select className="border rounded px-1.5 py-0.5 text-xs col-span-1" value={f.logical_op}
                  onChange={(e) => updateFilter(i, "logical_op", e.target.value)}>
                  <option value="and">AND</option>
                  <option value="or">OR</option>
                </select>
              )}
              {i === 0 && <span className="text-xs text-gray-500 font-medium">WHERE</span>}
              <select className="border rounded px-1.5 py-0.5 text-xs" value={f.field_path}
                onChange={(e) => updateFilter(i, "field_path", e.target.value)}>
                {dsInfo.fields.map(df => <option key={df.path} value={df.path}>{df.label}</option>)}
              </select>
              <select className="border rounded px-1.5 py-0.5 text-xs" value={f.operator}
                onChange={(e) => updateFilter(i, "operator", e.target.value)}>
                {FILTER_OPS.map(op => <option key={op} value={op}>{OP_LABEL[op]}</option>)}
              </select>
              {!["is_null","is_not_null"].includes(f.operator) && (
                <input className="border rounded px-1.5 py-0.5 text-xs" placeholder="Value"
                  value={f.value} onChange={(e) => updateFilter(i, "value", e.target.value)} />
              )}
              {f.operator === "between" && (
                <input className="border rounded px-1.5 py-0.5 text-xs" placeholder="To"
                  value={f.value_to} onChange={(e) => updateFilter(i, "value_to", e.target.value)} />
              )}
              <button onClick={() => setFilters(filters.filter((_, j) => j !== i))}
                className="text-red-400 hover:text-red-600 text-xs">✕</button>
            </div>
          ))}
          {filters.length === 0 && <p className="text-xs text-gray-400">No filters. Report will return all records.</p>}
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={save} disabled={saving}
          className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {saving ? "Saving…" : "Save & Preview"}
        </button>
        <button onClick={() => router.back()} className="rounded border px-6 py-2 text-sm text-gray-600 hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </div>
  );
}
