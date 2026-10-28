"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { bomApi, BOMSummary, ConversionProfileCreate, ConversionProfileOut, ConversionCalcResult, PackageComponentCalcResult } from "@/lib/bom";
import { productsApi, Product } from "@/lib/products";
import { ImportModal } from "@/components/import/ImportModal";
import { importApi } from "@/lib/importApi";
import { PermissionGuard, RequirePermission } from "@/components/PermissionGuard";

const emptyProfile: ConversionProfileCreate = {
  profile_code: null, profile_name: "", version_no: "1.0",
  effective_from: null, effective_to: null,
  theoretical_conversion_ratio: 1,
  startup_loss_pct: 0.5, shutdown_loss_pct: 0.3,
  packaging_reject_pct: 0.5, residual_bulk_pct: 0.2, line_purge_loss_pct: 0.1,
};

export default function ConversionProfilePage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<ConversionProfileCreate>(emptyProfile);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sourceQty, setSourceQty] = useState("");
  const [sourceUom, setSourceUom] = useState("KG");
  const [asOfDate, setAsOfDate] = useState("");
  const [calcResult, setCalcResult] = useState<ConversionCalcResult | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [packageQty, setPackageQty] = useState("");
  const [packageUom, setPackageUom] = useState("");
  const [packageResult, setPackageResult] = useState<PackageComponentCalcResult | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const { data: profiles = [] } = useQuery<ConversionProfileOut[]>({
    queryKey: ["bom-conversions"],
    queryFn: () => bomApi.listConversions(),
  });

  const { data: products = [], isLoading: productsLoading, isError: productsError, refetch: refetchProducts } = useQuery<Product[]>({
    queryKey: ["conversion-profile-products"],
    queryFn: () => productsApi.list(0, 500),
  });

  const { data: packagingBoms = [], isLoading: packagingBomsLoading, isError: packagingBomsError, refetch: refetchPackagingBoms } = useQuery<BOMSummary[]>({
    queryKey: ["conversion-packaging-boms"],
    queryFn: () => bomApi.list({ bom_type: "PACKAGING" }),
  });

  const create = useMutation({
    mutationFn: () => bomApi.createConversion(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bom-conversions"] });
      setShowCreate(false);
      setForm(emptyProfile);
    },
  });

  const packageComponents = useMutation({
    mutationFn: () => bomApi.packageComponents(
      selectedId!, Number(packageQty), packageUom || undefined, asOfDate || undefined,
    ),
    onSuccess: (result) => setPackageResult(result),
  });

  const doCalc = async () => {
    if (!selectedId || !sourceQty) return;
    setCalculating(true);
    try {
      const res = await bomApi.calcConversion(selectedId, Number(sourceQty), sourceUom, asOfDate || undefined);
      setCalcResult(res);
    } finally {
      setCalculating(false);
    }
  };

  const exportProfiles = async () => {
    setExporting(true);
    setExportError(null);
    try {
      await importApi.downloadConversionProfiles();
    } catch {
      setExportError("Could not export conversion profiles. Check your export permission and try again.");
    } finally {
      setExporting(false);
    }
  };

  const selected = profiles.find((p) => p.id === selectedId);
  const selectedTarget = products.find((product) => product.id === selected?.target_product_id);
  const formTargetPackagingBoms = packagingBoms.filter((bom) => bom.product_id === form.target_product_id);
  const expectedUnitValues = [form.standard_expected_units, form.realistic_expected_units];
  const lossValues = [form.startup_loss_pct, form.shutdown_loss_pct, form.packaging_reject_pct, form.residual_bulk_pct, form.line_purge_loss_pct];
  const canCreate = Boolean(
    form.profile_name.trim()
      && form.profile_name.trim().length <= 255
      && (form.profile_code == null || (form.profile_code.trim().length > 0 && form.profile_code.trim().length <= 80))
      && Boolean(form.version_no?.trim())
      && (form.version_no?.trim().length ?? 0) <= 20
      && Number.isFinite(form.theoretical_conversion_ratio)
      && form.theoretical_conversion_ratio! > 0
      && form.theoretical_conversion_ratio! <= 9999.999999
      && lossValues.every((value) => value != null && Number.isFinite(value) && value >= 0 && value <= 100)
      && Number.isFinite(form.fill_tolerance_pct)
      && form.fill_tolerance_pct! >= 0
      && form.fill_tolerance_pct! <= 99.999
      && (form.standard_fill_volume == null || (Number.isFinite(form.standard_fill_volume) && form.standard_fill_volume > 0 && form.standard_fill_volume <= 9999999999.9999))
      && (form.standard_fill_volume == null || Boolean(form.fill_volume_uom?.trim()))
      && (form.density_g_per_ml == null || (Number.isFinite(form.density_g_per_ml) && form.density_g_per_ml > 0 && form.density_g_per_ml <= 9999.9999))
      && expectedUnitValues.every((value) => value == null || (Number.isFinite(value) && Number.isInteger(value) && value >= 0 && value <= 99999999999999))
      && !(form.effective_from && form.effective_to && form.effective_to < form.effective_from)
  );

  return (
    <RequirePermission permission="bom.view">
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/bom" className="text-sm text-gray-400 hover:text-gray-600">← BOMs</a>
          <h1 className="text-xl font-bold text-gray-900">Bulk-to-Pack Conversion Profiles</h1>
        </div>
        <div className="flex items-center gap-2">
          <PermissionGuard permission="bom.import">
            <PermissionGuard permission="bom.import_template">
              <ImportModal module="conversion_profiles" onSuccess={() => qc.invalidateQueries({ queryKey: ["bom-conversions"] })} />
            </PermissionGuard>
          </PermissionGuard>
          <PermissionGuard permission="bom.export">
            <button type="button" onClick={exportProfiles} disabled={exporting} className="px-3 py-2 border border-gray-200 text-gray-600 text-sm rounded-lg hover:bg-gray-50 disabled:opacity-40">
              {exporting ? "Exporting…" : "Export CSV"}
            </button>
          </PermissionGuard>
          <PermissionGuard permission="bom.create">
            <button onClick={() => { create.reset(); setShowCreate(true); }} className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700">
              + New Profile
            </button>
          </PermissionGuard>
        </div>
      </div>
      {exportError && <p className="text-sm text-red-600" role="alert">{exportError}</p>}

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
              onClick={() => { setSelectedId(p.id); setCalcResult(null); setPackageResult(null); packageComponents.reset(); }}
              className={`bg-white rounded-xl border shadow-sm p-4 cursor-pointer hover:border-indigo-300 transition-colors ${selectedId === p.id ? "border-indigo-500 shadow-indigo-100" : "border-gray-100"}`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-gray-800">{p.profile_name}</p>
                  <p className="text-xs text-gray-400 font-mono mt-0.5">{p.profile_code} · v{p.version_no}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Effective {p.effective_from || "from any date"} – {p.effective_to || "open-ended"}
                  </p>
                  {p.target_product_name && <p className="text-xs text-indigo-600 mt-1">Target SKU: {p.target_product_name}</p>}
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
                <p className="text-xs text-gray-500">Version {selected?.version_no} · {selected?.effective_from || "no start date"} to {selected?.effective_to || "open-ended"}</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Source Quantity</label>
                    <input type="number" min="0.000001" step="0.000001" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="e.g. 1000" value={sourceQty} onChange={(e) => setSourceQty(e.target.value)} />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">UOM</label>
                    <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={sourceUom} onChange={(e) => setSourceUom(e.target.value)}>
                      {["KG", "L", "MT", "G", "ML"].map((u) => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Calculate as of date (optional)</label>
                  <input type="date" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={asOfDate} onChange={(e) => { setAsOfDate(e.target.value); setPackageResult(null); }} />
                  <p className="text-xs text-gray-400 mt-1">Leave blank to use today. Effective start and end dates include their boundary day.</p>
                </div>
                <button onClick={doCalc} disabled={!sourceQty || !Number.isFinite(Number(sourceQty)) || Number(sourceQty) <= 0 || calculating} className="w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-40">
                  {calculating ? "Calculating…" : "Calculate"}
                </button>
              </div>
            )}
          </div>

          {calcResult && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-3">
              <h3 className="font-semibold text-gray-800">Results</h3>
              <p className="text-xs text-gray-500">Profile {calcResult.profile_code} · v{calcResult.version_no} · calculated for {calcResult.as_of_date}</p>
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

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-3">
            <div>
              <h3 className="font-semibold text-gray-800">Packaging Components by SKU</h3>
              <p className="text-xs text-gray-500 mt-1">Enter the requested target SKU quantity explicitly. It is not inferred from the conversion yield result.</p>
            </div>
            {!selectedId ? (
              <p className="text-sm text-gray-400">Select a conversion profile to calculate its packaging components.</p>
            ) : !selected?.target_product_id || !selected.linked_packaging_bom_id ? (
              <p className="text-sm text-amber-700 bg-amber-50 rounded-lg p-3">This profile needs a target product and a linked packaging BOM before component quantities can be calculated.</p>
            ) : (
              <>
                <p className="text-xs text-gray-500">Target: {selectedTarget?.sku || selected.target_product_name || "configured product"} · {selected.linked_packaging_bom_id}</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Requested SKU Quantity</label>
                    <input type="number" min="0.0001" step="0.0001" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="e.g. 24" value={packageQty} onChange={(e) => { setPackageQty(e.target.value); setPackageResult(null); }} />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Quantity UOM (optional)</label>
                    <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder={selectedTarget?.uom || "Use target SKU UOM"} value={packageUom} onChange={(e) => { setPackageUom(e.target.value); setPackageResult(null); }} />
                  </div>
                </div>
                <button onClick={() => packageComponents.mutate()} disabled={!packageQty || !Number.isFinite(Number(packageQty)) || Number(packageQty) <= 0 || packageComponents.isPending} className="w-full py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-40">
                  {packageComponents.isPending ? "Calculating…" : "Calculate Packaging Components"}
                </button>
                {packageComponents.isError && <p className="text-xs text-red-600" role="alert">Could not calculate packaging components. Check the linked packaging BOM and requested quantity.</p>}
                {packageResult && (
                  <div className="border-t pt-3 space-y-2">
                    <p className="text-xs text-gray-600">{packageResult.target_sku} · requested {packageResult.requested_qty} {packageResult.requested_uom} · normalized {packageResult.normalized_qty} {packageResult.normalized_uom}</p>
                    {packageResult.components.length === 0 ? (
                      <p className="text-sm text-gray-400">The linked packaging BOM has no packaging component lines.</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                          <thead className="text-gray-400 border-b"><tr><th className="py-2 pr-3">Component</th><th className="py-2 pr-3">Code</th><th className="py-2 pr-3 text-right">Required</th><th className="py-2 text-right">Adjusted</th></tr></thead>
                          <tbody>{packageResult.components.map((component, index) => (
                            <tr key={`${component.line_no}-${component.item_id || component.item_code || index}`} className="border-b last:border-0">
                              <td className="py-2 pr-3">{component.item_name || "Unnamed component"}</td>
                              <td className="py-2 pr-3 font-mono text-gray-500">{component.item_code || "—"}</td>
                              <td className="py-2 pr-3 text-right">{component.scaled_qty.toFixed(4)} {component.required_uom}</td>
                              <td className="py-2 text-right">{component.adjusted_qty.toFixed(4)} {component.required_uom}</td>
                            </tr>
                          ))}</tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
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
                <input maxLength={80} className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Profile Code (optional)" value={form.profile_code ?? ""} onChange={(e) => setForm({ ...form, profile_code: e.target.value || null })} />
                <input maxLength={255} className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Profile Name *" value={form.profile_name} onChange={(e) => setForm({ ...form, profile_name: e.target.value })} />
              </div>
              <p className="text-xs text-gray-400">Leave the code blank to generate one automatically. Reuse a profile code for versions in one family; each code/version pair must be unique.</p>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Version</label>
                  <input maxLength={20} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="1.0" value={form.version_no ?? "1.0"} onChange={(e) => setForm({ ...form, version_no: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Effective from</label>
                  <input type="date" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.effective_from ?? ""} onChange={(e) => setForm({ ...form, effective_from: e.target.value || null })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Effective to</label>
                  <input type="date" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.effective_to ?? ""} onChange={(e) => setForm({ ...form, effective_to: e.target.value || null })} />
                </div>
              </div>
              {form.effective_from && form.effective_to && form.effective_to < form.effective_from && (
                <p className="text-xs text-red-600" role="alert">Effective to must be on or after effective from.</p>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Source Product (optional)</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" disabled={productsLoading || productsError || products.length === 0} value={form.source_product_id ?? ""} onChange={(e) => {
                    const product = products.find((candidate) => candidate.id === e.target.value);
                    setForm({ ...form, source_product_id: product?.id ?? null, source_product_name: product?.name ?? null });
                  }}>
                    <option value="">Choose manually by UOM</option>
                    {products.map((product) => <option key={product.id} value={product.id}>{product.sku} · {product.name} ({product.uom})</option>)}
                  </select>
                  {productsLoading && <p className="text-xs text-gray-400 mt-1">Loading products…</p>}
                  {productsError && <button type="button" onClick={() => refetchProducts()} className="text-xs text-red-600 mt-1">Could not load products. Retry.</button>}
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Target SKU (optional)</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" disabled={productsLoading || productsError || products.length === 0} value={form.target_product_id ?? ""} onChange={(e) => {
                    const product = products.find((candidate) => candidate.id === e.target.value);
                    setForm({ ...form, target_product_id: product?.id ?? null, target_product_name: product?.name ?? null, linked_packaging_bom_id: null });
                  }}>
                    <option value="">No target SKU linked</option>
                    {products.map((product) => <option key={product.id} value={product.id}>{product.sku} · {product.name} ({product.uom})</option>)}
                  </select>
                  {productsLoading && <p className="text-xs text-gray-400 mt-1">Loading products…</p>}
                  {productsError && <button type="button" onClick={() => refetchProducts()} className="text-xs text-red-600 mt-1">Could not load products. Retry.</button>}
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-gray-500 mb-1 block">Packaging BOM for target SKU (optional)</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.linked_packaging_bom_id ?? ""} disabled={!form.target_product_id || packagingBomsLoading || packagingBomsError} onChange={(e) => setForm({ ...form, linked_packaging_bom_id: e.target.value || null })}>
                    <option value="">No packaging BOM linked</option>
                    {formTargetPackagingBoms.map((bom) => <option key={bom.id} value={bom.id}>{bom.bom_code} · {bom.bom_name} ({bom.lifecycle})</option>)}
                  </select>
                  {!form.target_product_id && <p className="text-xs text-gray-400 mt-1">Select a target SKU first.</p>}
                  {packagingBomsLoading && <p className="text-xs text-gray-400 mt-1">Loading packaging BOMs…</p>}
                  {packagingBomsError && <button type="button" onClick={() => refetchPackagingBoms()} className="text-xs text-red-600 mt-1">Could not load packaging BOMs. Retry.</button>}
                  {form.target_product_id && !packagingBomsLoading && !packagingBomsError && formTargetPackagingBoms.length === 0 && <p className="text-xs text-gray-400 mt-1">No packaging BOM is available for this target SKU.</p>}
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Theoretical Conversion Ratio (source → units)</label>
                <input type="number" min="0.000001" max="9999.999999" step="0.000001" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.theoretical_conversion_ratio ?? 1} onChange={(e) => setForm({ ...form, theoretical_conversion_ratio: Number(e.target.value) })} />
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
                    <input type="number" min="0" max="100" step="0.001" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={(form as any)[field]} onChange={(e) => setForm({ ...form, [field]: Number(e.target.value) })} />
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Fill Volume per Unit</label>
                  <input type="number" min="0.0001" max="9999999999.9999" step="0.0001" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="e.g. 1.0" value={form.standard_fill_volume ?? ""} onChange={(e) => setForm({ ...form, standard_fill_volume: e.target.value ? Number(e.target.value) : null })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Fill Volume UOM</label>
                  <input maxLength={20} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="L" value={form.fill_volume_uom ?? ""} onChange={(e) => setForm({ ...form, fill_volume_uom: e.target.value })} />
                </div>
              </div>
              {form.standard_fill_volume != null && !form.fill_volume_uom?.trim() && <p className="text-xs text-red-600" role="alert">Fill volume UOM is required when a fill volume is set.</p>}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Fill Tolerance %</label>
                  <input type="number" min="0" max="99.999" step="0.001" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.fill_tolerance_pct ?? 1} onChange={(e) => setForm({ ...form, fill_tolerance_pct: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Density (g/ml, optional)</label>
                  <input type="number" min="0.0001" max="9999.9999" step="0.0001" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.density_g_per_ml ?? ""} onChange={(e) => setForm({ ...form, density_g_per_ml: e.target.value ? Number(e.target.value) : null})} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Standard Expected Units (optional)</label>
                  <input type="number" min="0" max="99999999999999" step="1" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.standard_expected_units ?? ""} onChange={(e) => setForm({ ...form, standard_expected_units: e.target.value ? Number(e.target.value) : null })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Realistic Expected Units (optional)</label>
                  <input type="number" min="0" max="99999999999999" step="1" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.realistic_expected_units ?? ""} onChange={(e) => setForm({ ...form, realistic_expected_units: e.target.value ? Number(e.target.value) : null })} />
                </div>
              </div>
              {create.isError && <p className="text-xs text-red-600" role="alert">Could not create this profile version. Check the code/version, dates, quantities, loss percentages, and fill UOM.</p>}
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => create.mutate()} disabled={!canCreate || create.isPending} className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40">
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
