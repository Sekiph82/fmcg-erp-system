"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gs1Api, type GS1CompanyConfig, type ProductGS1Config, packagingLevelLabel } from "@/lib/gs1";

export default function GS1ConfigPage() {
  const qc = useQueryClient();
  const [showCompanyForm, setShowCompanyForm] = useState(false);
  const [showProductForm, setShowProductForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<ProductGS1Config | null>(null);
  const [companyForm, setCompanyForm] = useState({ company_name: "", gs1_company_prefix: "", country_code: "", notes: "" });
  const [productForm, setProductForm] = useState({
    product_id: "", gtin: "", barcode_type: "EAN13", packaging_level: "UNIT",
    requires_lot_tracking: true, requires_expiry_tracking: true, requires_serialization: false,
    units_per_inner_pack: "", inner_packs_per_carton: "", cartons_per_pallet: "", notes: "",
  });

  const { data: configs } = useQuery({ queryKey: ["gs1-company-configs"], queryFn: gs1Api.listCompanyConfigs });
  const { data: productConfigs } = useQuery({ queryKey: ["gs1-product-configs"], queryFn: gs1Api.listProductConfigs });

  const createCompany = useMutation({
    mutationFn: gs1Api.createCompanyConfig,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["gs1-company-configs"] }); setShowCompanyForm(false); },
  });
  const createProduct = useMutation({
    mutationFn: gs1Api.createProductConfig,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["gs1-product-configs"] }); setShowProductForm(false); setEditingProduct(null); },
  });
  const updateProduct = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProductGS1Config> }) => gs1Api.updateProductConfig(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["gs1-product-configs"] }); setEditingProduct(null); },
  });

  function handleProductSubmit() {
    const data = {
      ...productForm,
      units_per_inner_pack: productForm.units_per_inner_pack ? Number(productForm.units_per_inner_pack) : undefined,
      inner_packs_per_carton: productForm.inner_packs_per_carton ? Number(productForm.inner_packs_per_carton) : undefined,
      cartons_per_pallet: productForm.cartons_per_pallet ? Number(productForm.cartons_per_pallet) : undefined,
    };
    if (editingProduct) {
      updateProduct.mutate({ id: editingProduct.id, data: data as unknown as Partial<ProductGS1Config> });
    } else {
      createProduct.mutate(data as unknown as Partial<ProductGS1Config>);
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">GS1 Configuration</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowCompanyForm(true)} className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded hover:bg-gray-700">
            + Company Config
          </button>
          <button onClick={() => setShowProductForm(true)} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
            + Product GS1 Config
          </button>
        </div>
      </div>

      {/* Company Config Form */}
      {showCompanyForm && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-gray-700">New GS1 Company Config</h2>
          <div className="grid grid-cols-2 gap-3">
            {[["Company Name", "company_name"], ["GS1 Company Prefix", "gs1_company_prefix"], ["Country Code", "country_code"]].map(([label, key]) => (
              <div key={key}>
                <label className="text-xs text-gray-500">{label}</label>
                <input
                  className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm"
                  value={(companyForm as Record<string, string>)[key]}
                  onChange={(e) => setCompanyForm((p) => ({ ...p, [key]: e.target.value }))}
                />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500">Notes</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={companyForm.notes} onChange={(e) => setCompanyForm((p) => ({ ...p, notes: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => createCompany.mutate(companyForm as Partial<GS1CompanyConfig>)} disabled={createCompany.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">Save</button>
            <button onClick={() => setShowCompanyForm(false)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
          </div>
        </div>
      )}

      {/* Company Configs Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b"><h2 className="text-sm font-medium text-gray-700">Company GS1 Configs</h2></div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {["Company", "GS1 Prefix", "Country", "Extension Digit", "SSCC Counter", "Active"].map((h) => (
                <th key={h} className="px-4 py-2 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!configs?.length && <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No company configs yet</td></tr>}
            {configs?.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{c.company_name}</td>
                <td className="px-4 py-2 font-mono text-xs">{c.gs1_company_prefix}</td>
                <td className="px-4 py-2">{c.country_code || "—"}</td>
                <td className="px-4 py-2">{c.extension_digit}</td>
                <td className="px-4 py-2">{c.sscc_serial_counter}</td>
                <td className="px-4 py-2">{c.is_active ? <span className="text-green-600">Active</span> : <span className="text-gray-400">Inactive</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Product GS1 Config Form */}
      {(showProductForm || editingProduct) && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-gray-700">{editingProduct ? "Edit" : "New"} Product GS1 Config</h2>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-500">Product ID (UUID)</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={productForm.product_id} onChange={(e) => setProductForm((p) => ({ ...p, product_id: e.target.value }))} placeholder="product-uuid..." />
            </div>
            <div>
              <label className="text-xs text-gray-500">GTIN (14 digits)</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={productForm.gtin} onChange={(e) => setProductForm((p) => ({ ...p, gtin: e.target.value }))} placeholder="00000000000000" maxLength={14} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Barcode Type</label>
              <select className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={productForm.barcode_type} onChange={(e) => setProductForm((p) => ({ ...p, barcode_type: e.target.value }))}>
                {["EAN13", "GS1_128", "QR_CODE", "CODE128"].map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Packaging Level</label>
              <select className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={productForm.packaging_level} onChange={(e) => setProductForm((p) => ({ ...p, packaging_level: e.target.value }))}>
                {(Object.keys(packagingLevelLabel) as Array<keyof typeof packagingLevelLabel>).map((k) => <option key={k} value={k}>{packagingLevelLabel[k]}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Units / Inner Pack</label>
              <input type="number" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={productForm.units_per_inner_pack} onChange={(e) => setProductForm((p) => ({ ...p, units_per_inner_pack: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Inner Packs / Carton</label>
              <input type="number" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={productForm.inner_packs_per_carton} onChange={(e) => setProductForm((p) => ({ ...p, inner_packs_per_carton: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Cartons / Pallet</label>
              <input type="number" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={productForm.cartons_per_pallet} onChange={(e) => setProductForm((p) => ({ ...p, cartons_per_pallet: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-4 text-sm">
            {[["requires_lot_tracking", "Lot Tracking"], ["requires_expiry_tracking", "Expiry Tracking"], ["requires_serialization", "Serialization"]].map(([key, label]) => (
              <label key={key} className="flex items-center gap-1.5">
                <input type="checkbox" checked={(productForm as unknown as Record<string, boolean>)[key]} onChange={(e) => setProductForm((p) => ({ ...p, [key]: e.target.checked }))} />
                {label}
              </label>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={handleProductSubmit} disabled={createProduct.isPending || updateProduct.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">Save</button>
            <button onClick={() => { setShowProductForm(false); setEditingProduct(null); }} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
          </div>
        </div>
      )}

      {/* Product Configs Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b"><h2 className="text-sm font-medium text-gray-700">Product GS1 Configurations</h2></div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {["Product", "GTIN", "Barcode Type", "Level", "Packaging Hierarchy", "Lot", "Expiry", "Serial"].map((h) => (
                <th key={h} className="px-3 py-2 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!productConfigs?.length && <tr><td colSpan={8} className="px-4 py-6 text-center text-gray-400">No product GS1 configs yet</td></tr>}
            {productConfigs?.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => { setEditingProduct(c); setProductForm({ product_id: String(c.product_id), gtin: c.gtin || "", barcode_type: c.barcode_type, packaging_level: c.packaging_level, requires_lot_tracking: c.requires_lot_tracking, requires_expiry_tracking: c.requires_expiry_tracking, requires_serialization: c.requires_serialization, units_per_inner_pack: c.units_per_inner_pack ? String(c.units_per_inner_pack) : "", inner_packs_per_carton: c.inner_packs_per_carton ? String(c.inner_packs_per_carton) : "", cartons_per_pallet: c.cartons_per_pallet ? String(c.cartons_per_pallet) : "", notes: c.notes || "" }); }}>
                <td className="px-3 py-2 font-medium">{c.product_name || c.product_id.slice(0, 8)}</td>
                <td className="px-3 py-2 font-mono text-xs">{c.gtin || <span className="text-red-500">Missing</span>}</td>
                <td className="px-3 py-2"><span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{c.barcode_type}</span></td>
                <td className="px-3 py-2">{packagingLevelLabel[c.packaging_level] || c.packaging_level}</td>
                <td className="px-3 py-2 text-xs text-gray-500">
                  {c.units_per_inner_pack && c.cartons_per_pallet
                    ? `${c.units_per_inner_pack}u → ${c.inner_packs_per_carton ?? "?"}ip → ${c.cartons_per_pallet}ctn/plt`
                    : "—"}
                </td>
                <td className="px-3 py-2">{c.requires_lot_tracking ? "✓" : "—"}</td>
                <td className="px-3 py-2">{c.requires_expiry_tracking ? "✓" : "—"}</td>
                <td className="px-3 py-2">{c.requires_serialization ? "✓" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
