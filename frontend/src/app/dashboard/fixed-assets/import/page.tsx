"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { faApi, DEPR_METHOD_LABEL, DepreciationMethod } from "@/lib/fixed_assets";

interface RowForm {
  asset_code: string;
  asset_name: string;
  asset_category_id: string;
  original_cost: string;
  accumulated_depreciation_to_date: string;
  in_service_date: string;
  depreciation_method: DepreciationMethod;
  useful_life_months: string;
  salvage_value: string;
  cost_center: string;
  location: string;
}

const BLANK: RowForm = {
  asset_code:"", asset_name:"", asset_category_id:"",
  original_cost:"", accumulated_depreciation_to_date:"",
  in_service_date:"", depreciation_method:"STRAIGHT_LINE",
  useful_life_months:"", salvage_value:"0", cost_center:"", location:"",
};

export default function FALegacyImportPage() {
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().slice(0, 10));
  const [rows, setRows] = useState<RowForm[]>([{ ...BLANK }]);
  const [result, setResult] = useState<{ total: number; succeeded: number; failed: string[] } | null>(null);

  const { data: cats = [] } = useQuery({
    queryKey: ["fa-categories"],
    queryFn: () => faApi.getCategories(true),
  });

  const importMut = useMutation({
    mutationFn: () => faApi.importLegacy({
      as_of_date: asOfDate,
      rows: rows.map((r) => ({
        ...r,
        original_cost: Number(r.original_cost),
        accumulated_depreciation_to_date: Number(r.accumulated_depreciation_to_date),
        salvage_value: Number(r.salvage_value),
        useful_life_months: r.useful_life_months ? Number(r.useful_life_months) : undefined,
      })),
    }),
    onSuccess: (data) => setResult(data),
  });

  const addRow = () => setRows([...rows, { ...BLANK }]);
  const removeRow = (i: number) => setRows(rows.filter((_, idx) => idx !== i));
  const updateRow = (i: number, key: keyof RowForm, val: string) => {
    setRows(rows.map((r, idx) => idx === i ? { ...r, [key]: val } : r));
  };

  return (
    <div className="p-6 space-y-5">
      <h1 className="text-2xl font-bold text-gray-900">Legacy Asset Import</h1>
      <p className="text-sm text-gray-500 max-w-2xl">
        Import existing assets with their opening accumulated depreciation and NBV balances.
        Assets will be created in ACTIVE status with legacy-import flag for audit purposes.
      </p>

      <div className="glass-panel p-4 flex items-center gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">As-of Date (opening balance date)</label>
          <input type="date" value={asOfDate} onChange={(e) => setAsOfDate(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
        </div>
        <button onClick={addRow} className="glow-button-secondary self-end">+ Add Row</button>
      </div>

      <div className="space-y-3">
        {rows.map((row, i) => (
          <div key={i} className="liquid-glass p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-500 uppercase">Row {i + 1}</span>
              {rows.length > 1 && (
                <button onClick={() => removeRow(i)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                ["asset_code","Asset Code","text"],
                ["asset_name","Asset Name","text"],
                ["original_cost","Original Cost","number"],
                ["accumulated_depreciation_to_date","Accum. Depr.","number"],
                ["in_service_date","In-Service Date","date"],
                ["salvage_value","Salvage Value","number"],
                ["useful_life_months","Useful Life (months)","number"],
                ["cost_center","Cost Center","text"],
                ["location","Location","text"],
              ].map(([key, label, type]) => (
                <div key={key} className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">{label}</label>
                  <input type={type} value={(row as any)[key]}
                    onChange={(e) => updateRow(i, key as keyof RowForm, e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
              ))}
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Category</label>
                <select value={row.asset_category_id}
                  onChange={(e) => updateRow(i, "asset_category_id", e.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  <option value="">— Select —</option>
                  {cats.map((c) => <option key={c.id} value={c.id}>{c.category_name}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Depreciation Method</label>
                <select value={row.depreciation_method}
                  onChange={(e) => updateRow(i, "depreciation_method", e.target.value as DepreciationMethod)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  {Object.entries(DEPR_METHOD_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={() => importMut.mutate()}
        disabled={importMut.isPending || rows.some(r => !r.asset_code || !r.asset_name || !r.asset_category_id)}
        className="glow-button"
      >
        {importMut.isPending ? "Importing…" : `Import ${rows.length} Asset${rows.length > 1 ? "s" : ""}`}
      </button>

      {result && (
        <div className="liquid-glass p-5 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Import Result</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="glow-card p-3">
              <p className="text-xs text-gray-500">Total</p>
              <p className="text-xl font-bold text-blue-600">{result.total}</p>
            </div>
            <div className="glow-card p-3">
              <p className="text-xs text-gray-500">Succeeded</p>
              <p className="text-xl font-bold text-green-600">{result.succeeded}</p>
            </div>
            <div className="glow-card p-3">
              <p className="text-xs text-gray-500">Failed</p>
              <p className="text-xl font-bold text-red-600">{result.failed.length}</p>
            </div>
          </div>
          {result.failed.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 space-y-1">
              {result.failed.map((f, i) => <p key={i} className="text-xs text-red-600">{f}</p>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
