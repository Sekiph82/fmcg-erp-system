"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { faApi, DEPR_METHOD_LABEL, DepreciationMethod } from "@/lib/fixed_assets";

interface Form {
  asset_code: string;
  asset_name: string;
  asset_category_id: string;
  description: string;
  serial_number: string;
  original_cost: string;
  salvage_value: string;
  in_service_date: string;
  depreciation_method: DepreciationMethod;
  depreciation_frequency: string;
  depreciation_start_rule: string;
  useful_life_months: string;
  useful_life_units_total: string;
  depreciation_rate: string;
  cost_center: string;
  location: string;
  department: string;
  plant: string;
}

const BLANK: Form = {
  asset_code: "", asset_name: "", asset_category_id: "", description: "",
  serial_number: "", original_cost: "", salvage_value: "0",
  in_service_date: new Date().toISOString().slice(0, 10),
  depreciation_method: "STRAIGHT_LINE", depreciation_frequency: "MONTHLY",
  depreciation_start_rule: "NEXT_MONTH", useful_life_months: "",
  useful_life_units_total: "", depreciation_rate: "",
  cost_center: "", location: "", department: "", plant: "",
};

export default function NewAssetPage() {
  const router = useRouter();
  const [form, setForm] = useState<Form>(BLANK);

  const { data: cats = [] } = useQuery({
    queryKey: ["fa-categories"],
    queryFn: () => faApi.getCategories(true),
  });

  const create = useMutation({
    mutationFn: () => faApi.createAsset({
      asset_code: form.asset_code,
      asset_name: form.asset_name,
      asset_category_id: form.asset_category_id,
      description: form.description || undefined,
      serial_number: form.serial_number || undefined,
      original_cost: Number(form.original_cost),
      salvage_value: Number(form.salvage_value),
      in_service_date: form.in_service_date,
      depreciation_method: form.depreciation_method,
      depreciation_frequency: form.depreciation_frequency as any,
      depreciation_start_rule: form.depreciation_start_rule as any,
      useful_life_months: form.useful_life_months ? Number(form.useful_life_months) : undefined,
      useful_life_units_total: form.useful_life_units_total ? Number(form.useful_life_units_total) : undefined,
      depreciation_rate: form.depreciation_rate ? Number(form.depreciation_rate) : undefined,
      cost_center: form.cost_center || undefined,
      location: form.location || undefined,
      department: form.department || undefined,
      plant: form.plant || undefined,
    }),
    onSuccess: (asset) => router.push(`/dashboard/fixed-assets/assets/${asset.id}`),
  });

  const set = (key: keyof Form, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const isUoP = form.depreciation_method === "UNITS_OF_PRODUCTION";
  const isDB  = form.depreciation_method === "DECLINING_BALANCE";

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">New Fixed Asset</h1>

      {create.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          Failed to create asset. Check required fields and try again.
        </div>
      )}

      {/* Identity */}
      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Identity</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Asset Code *</label>
            <input type="text" value={form.asset_code} onChange={(e) => set("asset_code", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. FA-2024-001" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Asset Name *</label>
            <input type="text" value={form.asset_name} onChange={(e) => set("asset_name", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Category *</label>
            <select value={form.asset_category_id} onChange={(e) => set("asset_category_id", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="">— Select Category —</option>
              {cats.map((c) => <option key={c.id} value={c.id}>{c.category_name}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Serial Number</label>
            <input type="text" value={form.serial_number} onChange={(e) => set("serial_number", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="col-span-2 flex flex-col gap-1">
            <label className="text-xs text-gray-500">Description</label>
            <textarea value={form.description} onChange={(e) => set("description", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" rows={2} />
          </div>
        </div>
      </div>

      {/* Cost */}
      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Cost & Date</h2>
        <div className="grid grid-cols-3 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Original Cost (KES) *</label>
            <input type="number" value={form.original_cost} onChange={(e) => set("original_cost", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Salvage Value (KES)</label>
            <input type="number" value={form.salvage_value} onChange={(e) => set("salvage_value", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">In-Service Date *</label>
            <input type="date" value={form.in_service_date} onChange={(e) => set("in_service_date", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
        </div>
      </div>

      {/* Depreciation */}
      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Depreciation</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Method *</label>
            <select value={form.depreciation_method}
              onChange={(e) => set("depreciation_method", e.target.value as DepreciationMethod)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {Object.entries(DEPR_METHOD_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Frequency</label>
            <select value={form.depreciation_frequency} onChange={(e) => set("depreciation_frequency", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="MONTHLY">Monthly</option>
              <option value="QUARTERLY">Quarterly</option>
              <option value="ANNUAL">Annual</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Start Rule</label>
            <select value={form.depreciation_start_rule} onChange={(e) => set("depreciation_start_rule", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="NEXT_MONTH">Next Month</option>
              <option value="SAME_MONTH">Same Month</option>
              <option value="HALF_YEAR">Half-Year Convention</option>
            </select>
          </div>
          {!isUoP && !isDB && (
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Useful Life (months)</label>
              <input type="number" value={form.useful_life_months} onChange={(e) => set("useful_life_months", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="1" />
            </div>
          )}
          {isUoP && (
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Total Units of Production</label>
              <input type="number" value={form.useful_life_units_total} onChange={(e) => set("useful_life_units_total", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="1" />
            </div>
          )}
          {isDB && (
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Declining Rate (%/year)</label>
              <input type="number" value={form.depreciation_rate} onChange={(e) => set("depreciation_rate", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="1" max="100" />
            </div>
          )}
        </div>
      </div>

      {/* Location */}
      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Location & Assignment</h2>
        <div className="grid grid-cols-2 gap-4">
          {[
            ["Cost Center", "cost_center"],
            ["Location", "location"],
            ["Department", "department"],
            ["Plant", "plant"],
          ].map(([label, key]) => (
            <div key={key} className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">{label}</label>
              <input type="text" value={(form as any)[key]} onChange={(e) => set(key as keyof Form, e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => create.mutate()}
          disabled={create.isPending || !form.asset_code || !form.asset_name || !form.asset_category_id || !form.original_cost}
          className="glow-button"
        >
          {create.isPending ? "Creating…" : "Create Asset"}
        </button>
        <button onClick={() => router.back()} className="glow-button-secondary">
          Cancel
        </button>
      </div>
    </div>
  );
}
