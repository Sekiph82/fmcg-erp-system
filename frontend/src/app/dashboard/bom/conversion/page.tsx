"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { bomApi, ConversionProfileOut, ConversionCalcResult, fmtKES } from "@/lib/bom";
import { PermissionGuard, RequirePermission } from "@/components/PermissionGuard";

const emptyProfile: Partial<ConversionProfileOut> = {
  profile_code: "", profile_name: "",
  theoretical_conversion_ratio: 1,
  startup_loss_pct: 0.5, shutdown_loss_pct: 0.3,
  packaging_reject_pct: 0.5, residual_bulk_pct: 0.2, line_purge_loss_pct: 0.1,
  is_active: true,
};

export default function ConversionProfilePage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<Partial<ConversionProfileOut>>(emptyProfile);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sourceQty, setSourceQty] = useState("");
  const [sourceUom, setSourceUom] = useState("KG");
  const [calcResult, setCalcResult] = useState<ConversionCalcResult | null>(null);
  const [calculating, setCalculating] = useState(false);

  const { data: profiles = [] } = useQuery<ConversionProfileOut[]>({
    queryKey: ["bom-conversions"],
    queryFn: () => bomApi.listConversions(),
  });

  const create = useMutation({
    mutationFn: () => bomApi.createConversion(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bom-conversions"] });
      setShowCreate(false);
      setForm(emptyProfile);
    },
  });

  const doCalc = async () => {
    if (!selectedId || !sourceQty) return;
    setCalculating(true);
    try {
      const res = await bomApi.calcConversion(selectedId, Number(sourceQty), sourceUom);
      setCalcResult(res);
    } finally {
      setCalculating(false);
    }
  };

  const selected = profiles.find((p) => p.id === selectedId);

  return (
    <RequirePermission permission="bom.view">
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/bom" className="text-sm text-gray-400 hover:text-gray-600">← BOMs</a>
          <h1 className="text-xl font-bold text-gray-900">Bulk-to-Pack Conversion Profiles</h1>
        </div>
        <PermissionGuard permission="bom.create">
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700">
            + New Profile
          </button>
        </PermissionGuard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Profile List */}
        <div className="space-y-3">
          {profiles.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
              No conversion profiles yet.
            </div>
          ) : profiles.map((p) => (
            <div
              key={p.id}
              onClick={() => { setSelectedId(p.id); setCalcResult(null); }}
              className={`bg-white rounded-xl border shadow-sm p-4 cursor-pointer hover:border-indigo-300 transition-colors ${selectedId === p.id ? "border-indigo-500 shadow-indigo-100" : "border-gray-100"}`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-gray-800">{p.profile_name}</p>
                  <p className="text-xs text-gray-400 font-mono mt-0.5">{p.profile_code}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${p.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                  {p.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-gray-500">
                <div><span className="text-gray-400">Ratio</span> <span className="font-medium text-gray-700">×{p.theoretical_conversion_ratio}</span></div>
                <div><span className="text-gray-400">Startup</span> <span className="font-medium">{p.startup_loss_pct}%</span></div>
                <div><span className="text-gray-400">Reject</span> <span className="font-medium">{p.packaging_reject_pct}%</span></div>
                <div><span className="text-gray-400">Shutdown</span> <span className="font-medium">{p.shutdown_loss_pct}%</span></div>
                <div><span className="text-gray-400">Residual</span> <span className="font-medium">{p.residual_bulk_pct}%</span></div>
                <div><span className="text-gray-400">Purge</span> <span className="font-medium">{p.line_purge_loss_pct}%</span></div>
              </div>
              {p.standard_expected_units && (
                <p className="mt-2 text-xs text-indigo-600">Standard expected: {p.standard_expected_units?.toLocaleString()} units</p>
              )}
            </div>
          ))}
        </div>

        {/* Calculator */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <h3 className="font-semibold text-gray-800 mb-3">Conversion Calculator</h3>
            {!selectedId ? (
              <p className="text-sm text-gray-400">Select a profile to calculate.</p>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-gray-600">Profile: <span className="font-medium">{selected?.profile_name}</span></p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Source Quantity</label>
                    <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="e.g. 1000" value={sourceQty} onChange={(e) => setSourceQty(e.target.value)} />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">UOM</label>
                    <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={sourceUom} onChange={(e) => setSourceUom(e.target.value)}>
                      {["KG", "L", "MT", "G", "ML"].map((u) => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </div>
                </div>
                <button onClick={doCalc} disabled={!sourceQty || calculating} className="w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-40">
                  {calculating ? "Calculating…" : "Calculate"}
                </button>
              </div>
            )}
          </div>

          {calcResult && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-3">
              <h3 className="font-semibold text-gray-800">Results</h3>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Theoretical Units", value: calcResult.theoretical_units.toLocaleString(), highlight: false },
                  { label: "Expected Good Units", value: calcResult.expected_good_units.toLocaleString(), highlight: true },
                  { label: "Startup Loss", value: calcResult.startup_loss_units.toLocaleString(), highlight: false },
                  { label: "Shutdown Loss", value: calcResult.shutdown_loss_units.toLocaleString(), highlight: false },
                  { label: "Reject Units", value: calcResult.reject_units.toLocaleString(), highlight: false },
                  { label: "Residual Units", value: calcResult.residual_units.toLocaleString(), highlight: false },
                  { label: "Total Loss %", value: `${calcResult.total_loss_pct.toFixed(2)}%`, highlight: false },
                  { label: "Fill Volume / Unit", value: calcResult.fill_volume_per_unit ? `${calcResult.fill_volume_per_unit} L` : "—", highlight: false },
                ].map((item) => (
                  <div key={item.label} className={`rounded-lg p-3 ${item.highlight ? "bg-indigo-50 border border-indigo-200" : "bg-gray-50"}`}>
                    <p className="text-xs text-gray-400">{item.label}</p>
                    <p className={`text-lg font-bold mt-0.5 ${item.highlight ? "text-indigo-700" : "text-gray-800"}`}>{item.value}</p>
                  </div>
                ))}
              </div>
              {calcResult.notes && <p className="text-xs text-gray-500 border-t pt-2">{calcResult.notes}</p>}
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <PermissionGuard permission="bom.create">
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New Conversion Profile</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Profile Code *" value={form.profile_code} onChange={(e) => setForm({ ...form, profile_code: e.target.value })} />
                <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Profile Name *" value={form.profile_name} onChange={(e) => setForm({ ...form, profile_name: e.target.value })} />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Theoretical Conversion Ratio (source → units)</label>
                <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.theoretical_conversion_ratio} onChange={(e) => setForm({ ...form, theoretical_conversion_ratio: Number(e.target.value) })} />
              </div>
              <p className="text-xs font-medium text-gray-500 pt-1">Loss Percentages</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  ["startup_loss_pct", "Startup Loss %"],
                  ["shutdown_loss_pct", "Shutdown Loss %"],
                  ["packaging_reject_pct", "Packaging Reject %"],
                  ["residual_bulk_pct", "Residual Bulk %"],
                  ["line_purge_loss_pct", "Line Purge %"],
                ].map(([field, label]) => (
                  <div key={field}>
                    <label className="text-xs text-gray-500 mb-1 block">{label}</label>
                    <input type="number" step="0.01" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={(form as any)[field]} onChange={(e) => setForm({ ...form, [field]: Number(e.target.value) })} />
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Fill Volume per Unit</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="e.g. 1.0" value={form.standard_fill_volume ?? ""} onChange={(e) => setForm({ ...form, standard_fill_volume: e.target.value ? Number(e.target.value) : undefined })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Fill Volume UOM</label>
                  <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="L" value={form.fill_volume_uom ?? ""} onChange={(e) => setForm({ ...form, fill_volume_uom: e.target.value })} />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => create.mutate()} disabled={!form.profile_code || !form.profile_name || create.isPending} className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40">
                {create.isPending ? "Creating…" : "Create Profile"}
              </button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
        </PermissionGuard>
      )}
    </div>
    </RequirePermission>
  );
}
