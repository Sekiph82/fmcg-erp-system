"use client";
import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { faApi, DEPR_METHOD_LABEL, DepreciationMethod } from "@/lib/fixed_assets";

interface Form {
  component_code: string;
  component_name: string;
  original_cost: string;
  salvage_value: string;
  in_service_date: string;
  depreciation_method: DepreciationMethod;
  useful_life_months: string;
  notes: string;
}

const BLANK: Form = {
  component_code: "", component_name: "", original_cost: "", salvage_value: "0",
  in_service_date: new Date().toISOString().slice(0, 10),
  depreciation_method: "STRAIGHT_LINE", useful_life_months: "", notes: "",
};

export default function AddComponentPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [form, setForm] = useState<Form>(BLANK);

  const { data: asset } = useQuery({
    queryKey: ["fa-asset", id],
    queryFn: () => faApi.getAsset(id),
  });

  const add = useMutation({
    mutationFn: () => faApi.addComponent(id, {
      component_code: form.component_code,
      component_name: form.component_name,
      original_cost: Number(form.original_cost),
      salvage_value: Number(form.salvage_value),
      in_service_date: form.in_service_date,
      depreciation_method: form.depreciation_method,
      useful_life_months: form.useful_life_months ? Number(form.useful_life_months) : undefined,
      notes: form.notes || undefined,
    }),
    onSuccess: () => router.push(`/dashboard/fixed-assets/assets/${id}`),
  });

  const set = (key: keyof Form, val: string) => setForm((f) => ({ ...f, [key]: val }));

  return (
    <div className="p-6 space-y-5 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Add Component</h1>
        {asset && (
          <p className="text-sm text-gray-500 mt-1">
            Parent: <span className="font-medium text-indigo-600">{asset.asset_code} — {asset.asset_name}</span>
          </p>
        )}
      </div>

      {add.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          Failed to add component. Check required fields and try again.
        </div>
      )}

      <div className="liquid-glass p-5 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Component Code *</label>
            <input type="text" value={form.component_code} onChange={(e) => set("component_code", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. FA-001-ENG" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Component Name *</label>
            <input type="text" value={form.component_name} onChange={(e) => set("component_name", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
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
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Depreciation Method</label>
            <select value={form.depreciation_method}
              onChange={(e) => set("depreciation_method", e.target.value as DepreciationMethod)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {Object.entries(DEPR_METHOD_LABEL).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          {form.depreciation_method !== "UNITS_OF_PRODUCTION" && form.depreciation_method !== "MANUAL" && (
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Useful Life (months)</label>
              <input type="number" value={form.useful_life_months} onChange={(e) => set("useful_life_months", e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="1" />
            </div>
          )}
          <div className="col-span-2 flex flex-col gap-1">
            <label className="text-xs text-gray-500">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" rows={2} />
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => add.mutate()}
          disabled={add.isPending || !form.component_code || !form.component_name || !form.original_cost}
          className="glow-button"
        >
          {add.isPending ? "Adding…" : "Add Component"}
        </button>
        <button onClick={() => router.back()} className="glow-button-secondary">
          Cancel
        </button>
      </div>
    </div>
  );
}
