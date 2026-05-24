"use client";
import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Cert {
  id: string;
  cert_ref: string;
  certificate_number: string | null;
  authority: string;
  entity_type: string;
  entity_name: string;
  country: string;
  scope: string | null;
  issued_date: string | null;
  expiry_date: string | null;
  days_to_expiry: number | null;
  status: string;
  document_url: string | null;
  renewal_notes: string | null;
  created_at: string;
}

interface Stats {
  total_active: number;
  expired: number;
  expiring_90d: number;
  by_authority: Record<string, number>;
}

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-700",
  PENDING_RENEWAL: "bg-amber-100 text-amber-700",
  EXPIRED: "bg-red-100 text-red-700",
  SUSPENDED: "bg-orange-100 text-orange-600",
  REVOKED: "bg-red-200 text-red-800",
  PENDING_INITIAL: "bg-blue-100 text-blue-700",
};

const AUTHORITIES = ["KEBS", "KEPHIS", "PPB", "NEMA", "FSCC", "HALAL", "KOSHER", "ISO_9001", "ISO_22000", "FSSC_22000", "BRC", "NAFDAC", "WHO_GMP", "ORGANIC", "FAIR_TRADE", "OTHER"];
const ENTITY_TYPES = ["PRODUCT", "PLANT", "SUPPLIER", "COMPANY"];
const STATUSES = ["ACTIVE", "PENDING_RENEWAL", "EXPIRED", "SUSPENDED", "REVOKED", "PENDING_INITIAL"];

interface NewCertForm {
  entity_name: string; authority: string; entity_type: string;
  entity_id: string; certificate_number: string; country: string;
  issuing_body: string; scope: string; issued_date: string;
  expiry_date: string; status: string; document_url: string;
}

const EMPTY_FORM: NewCertForm = {
  entity_name: "", authority: "KEBS", entity_type: "PRODUCT",
  entity_id: "", certificate_number: "", country: "Kenya",
  issuing_body: "", scope: "", issued_date: "", expiry_date: "",
  status: "ACTIVE", document_url: "",
};

const EMPTY_STATS: Stats = {
  total_active: 0,
  expired: 0,
  expiring_90d: 0,
  by_authority: {},
};

function normalizeStats(input: unknown): Stats {
  const s = input as Record<string, unknown> | null | undefined;
  return {
    total_active: Number(s?.total_active ?? 0),
    expired: Number(s?.expired ?? 0),
    expiring_90d: Number(s?.expiring_90d ?? 0),
    by_authority:
      s?.by_authority && typeof s.by_authority === "object"
        ? (s.by_authority as Record<string, number>)
        : {},
  };
}

function urgencyColor(days: number | null): string {
  if (days === null) return "text-gray-400";
  if (days < 0) return "text-red-600 font-bold";
  if (days <= 30) return "text-red-500 font-semibold";
  if (days <= 60) return "text-orange-500";
  if (days <= 90) return "text-amber-500";
  return "text-green-600";
}

export default function CertificatesPage() {
  const [certs, setCerts] = useState<Cert[]>([]);
  const [stats, setStats] = useState<Stats>(EMPTY_STATS);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NewCertForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [filterAuth, setFilterAuth] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [expiringOnly, setExpiringOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    const endpoint = expiringOnly ? `${API_BASE}/api/v1/regulatory-certs/expiring?days=90` : (() => {
      const p = new URLSearchParams({ limit: "200" });
      if (filterAuth) p.set("authority", filterAuth);
      if (filterStatus) p.set("status", filterStatus);
      if (filterType) p.set("entity_type", filterType);
      return `${API_BASE}/api/v1/regulatory-certs/?${p}`;
    })();
    Promise.all([
      fetch(endpoint, { credentials: "include" }).then((r) => r.json()),
      fetch(`${API_BASE}/api/v1/regulatory-certs/stats`, { credentials: "include" }).then((r) => r.json()),
    ]).then(([c, s]) => { setCerts(Array.isArray(c) ? c : []); setStats(normalizeStats(s)); })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [filterAuth, filterStatus, filterType, expiringOnly]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/api/v1/regulatory-certs/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_name: form.entity_name,
          authority: form.authority,
          entity_type: form.entity_type,
          entity_id: form.entity_id || undefined,
          certificate_number: form.certificate_number || undefined,
          country: form.country,
          issuing_body: form.issuing_body || undefined,
          scope: form.scope || undefined,
          issued_date: form.issued_date || undefined,
          expiry_date: form.expiry_date || undefined,
          status: form.status,
          document_url: form.document_url || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setShowForm(false);
      setForm(EMPTY_FORM);
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Regulatory Certificate Register</h1>
          <p className="text-sm text-gray-500 mt-0.5">KEBS, HALAL, ISO, FSCC, NAFDAC and all regulatory certifications</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded">
          + Add Certificate
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Total Active", value: stats.total_active, color: "text-gray-800" },
          { label: "Expiring (90d)", value: stats.expiring_90d, color: "text-amber-600" },
          { label: "Expired", value: stats.expired, color: "text-red-600" },
          { label: "Authorities", value: Object.keys(stats?.by_authority ?? {}).length, color: "text-blue-600" },
        ].map((k) => (
          <div key={k.label} className={`bg-white border rounded-lg p-4 shadow-sm ${k.label === "Expired" && k.value > 0 ? "border-red-300 bg-red-50" : ""}`}>
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Authority breakdown */}
      {Object.keys(stats?.by_authority ?? {}).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(stats.by_authority).sort(([, a], [, b]) => b - a).map(([auth, cnt]) => (
            <button key={auth} onClick={() => setFilterAuth(filterAuth === auth ? "" : auth)}
              className={`text-xs rounded-full border px-3 py-1 ${filterAuth === auth ? "bg-blue-600 text-white border-blue-600" : "bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"}`}>
              {auth} ({cnt})
            </button>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-white border rounded-lg p-3 shadow-sm items-end">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Status</label>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none">
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Entity Type</label>
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none">
            <option value="">All</option>
            {ENTITY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" checked={expiringOnly} onChange={(e) => setExpiringOnly(e.target.checked)} className="h-3.5 w-3.5" />
          Expiring / Expired only
        </label>
        <button onClick={() => { setFilterAuth(""); setFilterStatus(""); setFilterType(""); setExpiringOnly(false); }}
          className="text-xs text-gray-500 hover:text-gray-700 underline">Clear</button>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Register Certificate</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="sm:col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Entity Name *</label>
              <input type="text" value={form.entity_name} onChange={(e) => setForm((p) => ({ ...p, entity_name: e.target.value }))} placeholder="e.g. Mango Juice 500ml or Plant A"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Authority *</label>
              <select value={form.authority} onChange={(e) => setForm((p) => ({ ...p, authority: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {AUTHORITIES.map((a) => <option key={a} value={a}>{a.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Entity Type</label>
              <select value={form.entity_type} onChange={(e) => setForm((p) => ({ ...p, entity_type: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {ENTITY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Certificate Number</label>
              <input type="text" value={form.certificate_number} onChange={(e) => setForm((p) => ({ ...p, certificate_number: e.target.value }))} placeholder="e.g. KEBS/SB/2026/123"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Issued Date</label>
              <input type="date" value={form.issued_date} onChange={(e) => setForm((p) => ({ ...p, issued_date: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Expiry Date</label>
              <input type="date" value={form.expiry_date} onChange={(e) => setForm((p) => ({ ...p, expiry_date: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Country</label>
              <input type="text" value={form.country} onChange={(e) => setForm((p) => ({ ...p, country: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Status</label>
              <select value={form.status} onChange={(e) => setForm((p) => ({ ...p, status: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Document URL</label>
              <input type="text" value={form.document_url} onChange={(e) => setForm((p) => ({ ...p, document_url: e.target.value }))} placeholder="https://…"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={saving || !form.entity_name}
              className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Saving…" : "Register Certificate"}</button>
            <button onClick={() => setShowForm(false)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {/* Certificate table */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">Certificates <span className="font-normal text-gray-400">({certs.length})</span></h2>
        </div>
        {loading ? <div className="p-6 text-sm text-gray-400 text-center">Loading…</div> :
         certs.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No certificates found.</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">Ref</th>
                  <th className="text-left px-4 py-2">Entity</th>
                  <th className="text-left px-4 py-2">Authority</th>
                  <th className="text-left px-4 py-2">Type</th>
                  <th className="text-left px-4 py-2">Expiry</th>
                  <th className="text-left px-4 py-2">Days Left</th>
                  <th className="text-left px-4 py-2">Status</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {certs.map((c) => (
                  <tr key={c.id} className={(c.days_to_expiry !== null && c.days_to_expiry < 0) ? "bg-red-50" : (c.days_to_expiry !== null && c.days_to_expiry <= 30) ? "bg-amber-50" : ""}>
                    <td className="px-4 py-2.5 font-mono text-xs text-blue-600">{c.cert_ref}</td>
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-gray-900 text-sm truncate max-w-[150px]">{c.entity_name}</p>
                      {c.certificate_number && <p className="text-xs text-gray-400 font-mono">{c.certificate_number}</p>}
                    </td>
                    <td className="px-4 py-2.5 text-xs font-medium text-gray-700">{c.authority.replace(/_/g, " ")}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">{c.entity_type}</td>
                    <td className="px-4 py-2.5 text-gray-600 text-xs">{c.expiry_date ?? "—"}</td>
                    <td className={`px-4 py-2.5 text-xs ${urgencyColor(c.days_to_expiry)}`}>
                      {c.days_to_expiry !== null
                        ? c.days_to_expiry < 0
                          ? `Expired ${Math.abs(c.days_to_expiry)}d ago`
                          : `${c.days_to_expiry}d`
                        : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLOR[c.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {c.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      {c.document_url && (
                        <a href={c.document_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:text-blue-700">Doc ↗</a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
