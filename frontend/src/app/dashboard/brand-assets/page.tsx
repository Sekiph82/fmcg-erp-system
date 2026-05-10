"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface BrandAsset {
  id: string; asset_ref: string; name: string; asset_type: string;
  brand: string | null; product_name: string | null; product_sku: string | null;
  version: number; is_latest: boolean; status: string; bom_change_flag: boolean;
  file_url: string | null; thumbnail_url: string | null; file_format: string | null;
  compliance_checklist: Record<string, boolean> | null; created_at: string;
}

interface Stats {
  total_assets: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  bom_change_alerts: number;
}

const STATUS_COLOR: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  IN_REVIEW: "bg-blue-100 text-blue-700",
  APPROVED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-600",
  ARCHIVED: "bg-gray-100 text-gray-400",
  PRINT_READY: "bg-emerald-100 text-emerald-700 font-bold",
};

const TYPE_ICON: Record<string, string> = {
  LABEL: "🏷️", ARTWORK: "🎨", PACKAGING_DESIGN: "📦",
  LOGO: "⭐", BRAND_GUIDELINE: "📋", PRODUCT_PHOTO: "📷",
  MARKETING_MATERIAL: "📢",
};

const ASSET_TYPES = ["LABEL", "ARTWORK", "PACKAGING_DESIGN", "LOGO", "BRAND_GUIDELINE", "PRODUCT_PHOTO", "MARKETING_MATERIAL"];
const STATUSES = ["DRAFT", "IN_REVIEW", "APPROVED", "REJECTED", "PRINT_READY", "ARCHIVED"];

interface NewForm {
  name: string; asset_type: string; brand: string; product_name: string;
  product_sku: string; bom_version: string; file_url: string;
  thumbnail_url: string; file_format: string; notes: string;
}

export default function BrandAssetsPage() {
  const [assets, setAssets] = useState<BrandAsset[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [bomAlertOnly, setBomAlertOnly] = useState(false);
  const [form, setForm] = useState<NewForm>({
    name: "", asset_type: "LABEL", brand: "", product_name: "",
    product_sku: "", bom_version: "", file_url: "", thumbnail_url: "",
    file_format: "PDF", notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    const p = new URLSearchParams({ limit: "100" });
    if (filterType) p.set("asset_type", filterType);
    if (filterStatus) p.set("status", filterStatus);
    if (bomAlertOnly) p.set("bom_change_flag", "true");
    Promise.all([
      fetch(`/api/v1/brand-assets/?${p}`).then((r) => r.json()),
      fetch("/api/v1/brand-assets/stats").then((r) => r.json()),
    ]).then(([a, s]) => { setAssets(a); setStats(s); })
      .finally(() => setLoading(false));
  };

  useEffect(load, [filterType, filterStatus, bomAlertOnly]);

  const save = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/brand-assets/", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name, asset_type: form.asset_type,
          brand: form.brand || undefined, product_name: form.product_name || undefined,
          product_sku: form.product_sku || undefined, bom_version: form.bom_version || undefined,
          file_url: form.file_url || undefined, thumbnail_url: form.thumbnail_url || undefined,
          file_format: form.file_format || undefined, notes: form.notes || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setShowForm(false);
      setForm({ name: "", asset_type: "LABEL", brand: "", product_name: "", product_sku: "", bom_version: "", file_url: "", thumbnail_url: "", file_format: "PDF", notes: "" });
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const compliancePct = (chk: Record<string, boolean> | null) => {
    if (!chk) return 0;
    const vals = Object.values(chk);
    return Math.round(vals.filter(Boolean).length / vals.length * 100);
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Brand Asset Management</h1>
          <p className="text-sm text-gray-500 mt-0.5">Labels, artwork, packaging designs — version control and approval workflow</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded">
          + Upload Asset
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* KPI strip */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Total Assets", value: stats.total_assets, color: "text-gray-800" },
            { label: "Print Ready", value: stats.by_status.PRINT_READY ?? 0, color: "text-green-600" },
            { label: "In Review", value: stats.by_status.IN_REVIEW ?? 0, color: "text-blue-600" },
            { label: "BOM Change Alerts", value: stats.bom_change_alerts, color: "text-red-600" },
          ].map((k) => (
            <div key={k.label} className={`bg-white border rounded-lg p-4 shadow-sm ${k.label === "BOM Change Alerts" && k.value > 0 ? "border-red-300 bg-red-50" : ""}`}>
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-white border rounded-lg p-3 shadow-sm items-end">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Type</label>
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none">
            <option value="">All</option>
            {ASSET_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Status</label>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none">
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" checked={bomAlertOnly} onChange={(e) => setBomAlertOnly(e.target.checked)} className="h-3.5 w-3.5" />
          BOM alerts only
        </label>
        <button onClick={() => { setFilterType(""); setFilterStatus(""); setBomAlertOnly(false); }}
          className="text-xs text-gray-500 underline">Clear</button>
      </div>

      {/* Upload form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Upload Brand Asset</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="sm:col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Asset Name *</label>
              <input type="text" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} placeholder="e.g. Mango Juice Label v1 — 500ml"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Type</label>
              <select value={form.asset_type} onChange={(e) => setForm((p) => ({ ...p, asset_type: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {ASSET_TYPES.map((t) => <option key={t} value={t}>{TYPE_ICON[t]} {t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            {[
              { label: "Brand", key: "brand", ph: "e.g. POVU Naturals" },
              { label: "Product Name", key: "product_name", ph: "e.g. Mango Juice 500ml" },
              { label: "Product SKU", key: "product_sku", ph: "e.g. MJ-500" },
              { label: "BOM Version", key: "bom_version", ph: "e.g. v2.1" },
              { label: "File URL", key: "file_url", ph: "https://files.company.com/…" },
              { label: "Thumbnail URL", key: "thumbnail_url", ph: "https://…/thumb.png" },
              { label: "File Format", key: "file_format", ph: "PDF | AI | PSD | PNG" },
            ].map(({ label, key, ph }) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph}
                  value={(form as unknown as Record<string, string>)[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={saving || !form.name}
              className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Uploading…" : "Create Asset"}</button>
            <button onClick={() => setShowForm(false)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {/* Asset grid */}
      {loading ? <p className="text-gray-400 text-sm">Loading…</p> : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {assets.map((a) => {
            const pct = compliancePct(a.compliance_checklist);
            return (
              <Link key={a.id} href={`/dashboard/brand-assets/${a.id}`}
                className="bg-white border rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden block">
                {/* Thumbnail or placeholder */}
                <div className="h-32 bg-gray-100 flex items-center justify-center relative">
                  {a.thumbnail_url ? (
                    // eslint-disable-next-line @next/next/no-img-element -- Uploaded asset thumbnails can be backend/data URLs outside Next image optimization.
                    <img src={a.thumbnail_url} alt={a.name} className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-4xl">{TYPE_ICON[a.asset_type] ?? "📄"}</span>
                  )}
                  {a.bom_change_flag && (
                    <div className="absolute top-2 right-2 bg-red-500 text-white text-xs font-bold rounded px-2 py-0.5">BOM Changed</div>
                  )}
                  {a.file_format && (
                    <div className="absolute bottom-2 left-2 bg-black/60 text-white text-xs rounded px-2 py-0.5">{a.file_format}</div>
                  )}
                </div>
                <div className="p-4 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 text-sm truncate">{a.name}</p>
                      <p className="text-xs text-gray-400 font-mono">{a.asset_ref} · v{a.version}</p>
                    </div>
                    <span className={`text-xs rounded-full px-2 py-0.5 shrink-0 ${STATUS_COLOR[a.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {a.status.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                    {a.brand && <span className="bg-gray-100 rounded px-2 py-0.5">{a.brand}</span>}
                    {a.product_sku && <span className="bg-gray-100 rounded px-2 py-0.5 font-mono">{a.product_sku}</span>}
                  </div>
                  {/* Compliance bar */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-400">Label compliance</span>
                      <span className="text-xs font-medium text-gray-600">{pct}%</span>
                    </div>
                    <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${pct === 100 ? "bg-green-500" : pct >= 60 ? "bg-amber-400" : "bg-red-400"}`}
                        style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
          {assets.length === 0 && (
            <div className="col-span-3 bg-gray-50 border rounded-xl p-8 text-center text-sm text-gray-400">
              No brand assets yet. Upload your first label or artwork.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
