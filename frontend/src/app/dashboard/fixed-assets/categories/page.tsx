"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { faApi, FAAssetCategory, DEPR_METHOD_LABEL } from "@/lib/fixed_assets";

export default function FACategoriesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    category_code: "", category_name: "",
    default_depreciation_method: "STRAIGHT_LINE",
    default_useful_life_months: "",
    default_salvage_value_pct: "0",
    capitalization_threshold: "",
    asset_account: "", accum_depreciation_account: "",
    depreciation_expense_account: "", notes: "",
  });

  const { data: cats = [], isLoading } = useQuery({
    queryKey: ["fa-categories"],
    queryFn: () => faApi.getCategories(false),
  });

  const create = useMutation({
    mutationFn: () => faApi.createCategory({
      ...form,
      default_useful_life_months: form.default_useful_life_months ? Number(form.default_useful_life_months) : undefined,
      capitalization_threshold: form.capitalization_threshold ? Number(form.capitalization_threshold) : undefined,
    } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fa-categories"] });
      setShowForm(false);
      setForm({ category_code:"",category_name:"",default_depreciation_method:"STRAIGHT_LINE",default_useful_life_months:"",default_salvage_value_pct:"0",capitalization_threshold:"",asset_account:"",accum_depreciation_account:"",depreciation_expense_account:"",notes:"" });
    },
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Asset Categories</h1>
        <button onClick={() => setShowForm(!showForm)} className="glow-button">
          {showForm ? "Cancel" : "+ New Category"}
        </button>
      </div>

      {showForm && (
        <div className="liquid-glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">New Asset Category</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {[
              ["category_code","Category Code","text"],
              ["category_name","Category Name","text"],
              ["default_useful_life_months","Default Useful Life (months)","number"],
              ["default_salvage_value_pct","Default Salvage % ","number"],
              ["capitalization_threshold","Capitalization Threshold","number"],
              ["asset_account","Asset GL Account","text"],
              ["accum_depreciation_account","Accum. Depr. Account","text"],
              ["depreciation_expense_account","Depr. Expense Account","text"],
            ].map(([key, label, type]) => (
              <div key={key} className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">{label}</label>
                <input
                  type={type}
                  value={(form as any)[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            ))}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Depreciation Method</label>
              <select
                value={form.default_depreciation_method}
                onChange={(e) => setForm({ ...form, default_depreciation_method: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                {Object.entries(DEPR_METHOD_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Notes</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
              rows={2}
            />
          </div>
          <button
            onClick={() => create.mutate()}
            disabled={create.isPending || !form.category_code || !form.category_name}
            className="glow-button"
          >
            {create.isPending ? "Saving…" : "Save Category"}
          </button>
        </div>
      )}

      <div className="glass-table overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr>
              {["Code","Name","Depr. Method","Useful Life","Cap. Threshold","Asset A/C","Depr. A/C","Active"].map(h => (
                <th key={h} className="px-4 py-3 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="px-4 py-10 text-center text-gray-400">Loading…</td></tr>
            ) : cats.map((c) => (
              <tr key={c.id}>
                <td className="px-4 py-2 font-mono text-xs font-medium">{c.category_code}</td>
                <td className="px-4 py-2 font-medium">{c.category_name}</td>
                <td className="px-4 py-2 text-xs">{DEPR_METHOD_LABEL[c.default_depreciation_method]}</td>
                <td className="px-4 py-2">{c.default_useful_life_months ? `${c.default_useful_life_months}m` : "—"}</td>
                <td className="px-4 py-2">{c.capitalization_threshold ? c.capitalization_threshold.toLocaleString() : "—"}</td>
                <td className="px-4 py-2 font-mono text-xs">{c.asset_account ?? "—"}</td>
                <td className="px-4 py-2 font-mono text-xs">{c.accum_depreciation_account ?? "—"}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs font-medium ${c.is_active ? "text-green-600" : "text-gray-400"}`}>
                    {c.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
