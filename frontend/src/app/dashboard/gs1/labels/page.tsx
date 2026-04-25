"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gs1Api, type LabelTemplate, packagingLevelLabel } from "@/lib/gs1";

const DEFAULT_FIELDS = {
  show_product_name: true,
  show_gtin: true,
  show_lot_number: true,
  show_expiry_date: true,
  show_production_date: true,
  show_quantity: true,
  show_barcode: true,
  show_qr_code: false,
  show_company_logo: true,
  show_regulatory_text: false,
  regulatory_text: "",
};

export default function LabelsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [preview, setPreview] = useState<LabelTemplate | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    packaging_level: "UNIT",
    width_mm: "100",
    height_mm: "60",
    is_default: false,
    notes: "",
    fields: DEFAULT_FIELDS,
    html_template: `<div class="label">
  <div class="company-name">{{company_name}}</div>
  <div class="product-name">{{product_name}}</div>
  <div class="barcode">{{barcode_image}}</div>
  <div class="gtin">GTIN: {{gtin}}</div>
  <div class="lot">Lot: {{lot_number}}</div>
  <div class="expiry">Best Before: {{expiry_date}}</div>
  <div class="qty">Qty: {{quantity}}</div>
</div>`,
  });

  const { data: templates } = useQuery({ queryKey: ["gs1-templates"], queryFn: () => gs1Api.listTemplates() });

  const create = useMutation({
    mutationFn: gs1Api.createTemplate,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["gs1-templates"] }); setShowForm(false); },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<LabelTemplate> }) => gs1Api.updateTemplate(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["gs1-templates"] }); setPreview(null); },
  });

  const statusLabels: Record<string, string> = { DRAFT: "Draft", ACTIVE: "Active", DEPRECATED: "Deprecated" };
  const statusColors: Record<string, string> = { DRAFT: "bg-yellow-100 text-yellow-800", ACTIVE: "bg-green-100 text-green-800", DEPRECATED: "bg-gray-100 text-gray-500" };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Label Templates</h1>
          <p className="text-sm text-gray-500">Design dynamic label templates per packaging level</p>
        </div>
        <button onClick={() => setShowForm(true)} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
          + New Template
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-4 space-y-4">
          <h2 className="text-sm font-medium text-gray-700">New Label Template</h2>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-500">Name *</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Packaging Level</label>
              <select className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.packaging_level} onChange={(e) => setForm((p) => ({ ...p, packaging_level: e.target.value }))}>
                {Object.entries(packagingLevelLabel).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-xs text-gray-500">Width (mm)</label>
                <input type="number" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.width_mm} onChange={(e) => setForm((p) => ({ ...p, width_mm: e.target.value }))} />
              </div>
              <div className="flex-1">
                <label className="text-xs text-gray-500">Height (mm)</label>
                <input type="number" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.height_mm} onChange={(e) => setForm((p) => ({ ...p, height_mm: e.target.value }))} />
              </div>
            </div>
            <div className="col-span-3">
              <label className="text-xs text-gray-500">Description</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.description} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))} />
            </div>
          </div>

          <div>
            <p className="text-xs text-gray-500 font-medium mb-2">Label Fields</p>
            <div className="grid grid-cols-4 gap-2">
              {Object.entries(DEFAULT_FIELDS).filter(([k]) => k.startsWith("show_")).map(([k]) => (
                <label key={k} className="flex items-center gap-1.5 text-xs">
                  <input
                    type="checkbox"
                    checked={(form.fields as Record<string, boolean>)[k] ?? false}
                    onChange={(e) => setForm((p) => ({ ...p, fields: { ...p.fields, [k]: e.target.checked } }))}
                  />
                  {k.replace("show_", "").replace(/_/g, " ")}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-500">HTML Template (use &#123;&#123;variable&#125;&#125; placeholders)</label>
            <textarea
              rows={8}
              className="mt-0.5 w-full border rounded px-2 py-1.5 text-xs font-mono"
              value={form.html_template}
              onChange={(e) => setForm((p) => ({ ...p, html_template: e.target.value }))}
            />
          </div>

          <label className="flex items-center gap-1.5 text-sm">
            <input type="checkbox" checked={form.is_default} onChange={(e) => setForm((p) => ({ ...p, is_default: e.target.checked }))} />
            Set as default template for this packaging level
          </label>

          <div className="flex gap-2">
            <button onClick={() => create.mutate(form as Partial<LabelTemplate>)} disabled={create.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">Save Template</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
          </div>
        </div>
      )}

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {!templates?.length && (
          <div className="col-span-3 bg-white border rounded-lg p-8 text-center text-gray-400">No label templates yet</div>
        )}
        {templates?.map((t) => (
          <div key={t.id} className="bg-white border rounded-lg p-4 hover:shadow-sm transition-shadow">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="text-sm font-medium text-gray-900">{t.name}</h3>
                <p className="text-xs text-gray-500">{t.description || "No description"}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${statusColors[t.status] ?? ""}`}>{statusLabels[t.status] ?? t.status}</span>
            </div>

            <div className="grid grid-cols-2 gap-1.5 text-xs text-gray-600 mb-3">
              <div><span className="text-gray-400">Level: </span>{packagingLevelLabel[t.packaging_level as keyof typeof packagingLevelLabel] || t.packaging_level || "All"}</div>
              <div><span className="text-gray-400">Size: </span>{t.width_mm && t.height_mm ? `${t.width_mm}×${t.height_mm}mm` : "—"}</div>
              <div><span className="text-gray-400">Version: </span>v{t.template_version}</div>
              <div>{t.is_default && <span className="text-blue-600 font-medium">Default</span>}</div>
            </div>

            {t.html_template && (
              <div className="bg-gray-50 rounded p-2 mb-3">
                <p className="text-xs text-gray-400 mb-1 font-medium">Preview (template)</p>
                <div className="text-xs text-gray-600 font-mono whitespace-pre-wrap overflow-hidden max-h-20">{t.html_template.slice(0, 200)}{t.html_template.length > 200 ? "…" : ""}</div>
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => update.mutate({ id: t.id, data: { status: t.status === "DRAFT" ? "ACTIVE" : "DRAFT" } })}
                className="flex-1 text-xs border rounded py-1 hover:bg-gray-50"
              >
                {t.status === "DRAFT" ? "Activate" : "Set Draft"}
              </button>
              <button onClick={() => setPreview(t)} className="flex-1 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded py-1 hover:bg-blue-100">
                View
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Preview Modal */}
      {preview && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setPreview(null)}>
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-medium text-gray-900 mb-3">Template: {preview.name}</h3>
            <div className="bg-gray-50 rounded p-3 mb-3">
              <p className="text-xs text-gray-500 mb-1 font-medium">Available Placeholders</p>
              <div className="flex flex-wrap gap-1.5">
                {["company_name", "product_name", "gtin", "lot_number", "expiry_date", "production_date", "quantity", "barcode_image", "qr_code"].map((ph) => (
                  <span key={ph} className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono">&#123;&#123;{ph}&#125;&#125;</span>
                ))}
              </div>
            </div>
            <pre className="text-xs font-mono bg-gray-50 rounded p-3 overflow-x-auto whitespace-pre-wrap">{preview.html_template || "No HTML template defined"}</pre>
            <button onClick={() => setPreview(null)} className="mt-3 px-3 py-1.5 text-sm border rounded">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
