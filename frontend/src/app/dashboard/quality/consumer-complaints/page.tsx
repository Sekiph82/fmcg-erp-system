"use client";
import { useEffect, useState } from "react";

interface Complaint {
  id: string;
  complaint_ref: string;
  consumer_name: string | null;
  consumer_contact: string | null;
  channel: string;
  product_name: string;
  lot_number: string | null;
  severity: string;
  description: string;
  status: string;
  assigned_to: string | null;
  root_cause: string | null;
  corrective_action: string | null;
  recall_triggered_flag: boolean;
  regulatory_report_required: boolean;
  created_at: string;
}

interface Stats {
  total: number;
  open: number;
  recall_triggered: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
}

const SEV_COLOR: Record<string, string> = {
  SAFETY: "bg-red-200 text-red-800 font-bold",
  FOREIGN_OBJECT: "bg-red-100 text-red-700",
  QUALITY: "bg-amber-100 text-amber-700",
  LABEL_ISSUE: "bg-blue-100 text-blue-700",
  PACKAGING: "bg-gray-100 text-gray-600",
  OTHER: "bg-gray-100 text-gray-500",
};

const STATUS_COLOR: Record<string, string> = {
  NEW: "bg-red-100 text-red-700",
  ACKNOWLEDGED: "bg-amber-100 text-amber-700",
  INVESTIGATING: "bg-blue-100 text-blue-700",
  RESOLVED: "bg-green-100 text-green-700",
  COMPENSATED: "bg-green-200 text-green-800",
  ESCALATED: "bg-purple-100 text-purple-700",
  CLOSED: "bg-gray-100 text-gray-500",
};

const CHANNELS = ["PHONE", "EMAIL", "WHATSAPP", "SOCIAL_MEDIA", "WALK_IN", "RETAILER"];
const SEVERITIES = ["SAFETY", "FOREIGN_OBJECT", "QUALITY", "LABEL_ISSUE", "PACKAGING", "OTHER"];
const STATUSES = ["NEW", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "COMPENSATED", "ESCALATED", "CLOSED"];

interface LogForm {
  consumer_name: string;
  consumer_contact: string;
  consumer_location: string;
  channel: string;
  product_name: string;
  lot_number: string;
  purchase_date: string;
  purchase_location: string;
  severity: string;
  description: string;
}

const EMPTY_FORM: LogForm = {
  consumer_name: "", consumer_contact: "", consumer_location: "",
  channel: "PHONE", product_name: "", lot_number: "",
  purchase_date: "", purchase_location: "", severity: "QUALITY", description: "",
};

export default function ConsumerComplaintsPage() {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<LogForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState<Complaint | null>(null);
  const [filterSev, setFilterSev] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterLot, setFilterLot] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [updateForm, setUpdateForm] = useState({ status: "", assigned_to: "", root_cause: "", corrective_action: "" });
  const [updating, setUpdating] = useState(false);

  const load = () => {
    setLoading(true);
    const p = new URLSearchParams({ limit: "200" });
    if (filterSev) p.set("severity", filterSev);
    if (filterStatus) p.set("status", filterStatus);
    if (filterLot) p.set("lot_number", filterLot);
    Promise.all([
      fetch(`/api/v1/consumer-complaints/?${p}`).then((r) => r.json()),
      fetch("/api/v1/consumer-complaints/stats").then((r) => r.json()),
    ]).then(([c, s]) => { setComplaints(c); setStats(s); }).finally(() => setLoading(false));
  };

  useEffect(load, [filterSev, filterStatus, filterLot]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/consumer-complaints/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          consumer_name: form.consumer_name || undefined,
          consumer_contact: form.consumer_contact || undefined,
          consumer_location: form.consumer_location || undefined,
          channel: form.channel,
          product_name: form.product_name,
          lot_number: form.lot_number || undefined,
          purchase_date: form.purchase_date || undefined,
          purchase_location: form.purchase_location || undefined,
          severity: form.severity,
          description: form.description,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      const res = await r.json();
      if (res.warning) alert(res.warning);
      setShowForm(false);
      setForm(EMPTY_FORM);
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const update = async () => {
    if (!selected) return;
    setUpdating(true);
    const body: Record<string, string> = {};
    if (updateForm.status) body.status = updateForm.status;
    if (updateForm.assigned_to) body.assigned_to = updateForm.assigned_to;
    if (updateForm.root_cause) body.root_cause = updateForm.root_cause;
    if (updateForm.corrective_action) body.corrective_action = updateForm.corrective_action;
    await fetch(`/api/v1/consumer-complaints/${selected.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setSelected(null);
    load();
    setUpdating(false);
  };

  const fmtDt = (iso: string) => new Date(iso).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Consumer Complaint Management</h1>
          <p className="text-sm text-gray-500 mt-0.5">End-consumer complaints linked to product batches and lots</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded">
          + Log Complaint
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* KPI strip */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Total Complaints", value: stats.total, color: "text-gray-800" },
            { label: "Open", value: stats.open, color: "text-orange-600" },
            { label: "Recall Triggered", value: stats.recall_triggered, color: "text-red-600" },
            { label: "SAFETY", value: stats.by_severity.SAFETY ?? 0, color: "text-red-800" },
          ].map((k) => (
            <div key={k.label} className={`bg-white border rounded-lg p-4 shadow-sm ${k.label === "Recall Triggered" && k.value > 0 ? "border-red-300 bg-red-50" : ""}`}>
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-white border rounded-lg p-3 shadow-sm items-end">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Severity</label>
          <select value={filterSev} onChange={(e) => setFilterSev(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none">
            <option value="">All</option>
            {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Status</label>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none">
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Lot Number</label>
          <input type="text" value={filterLot} onChange={(e) => setFilterLot(e.target.value)}
            placeholder="e.g. LOT-2026-001"
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none w-36" />
        </div>
        <button onClick={() => { setFilterSev(""); setFilterStatus(""); setFilterLot(""); }}
          className="text-xs text-gray-500 hover:text-gray-700 underline">Clear</button>
      </div>

      {/* Log form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Log Consumer Complaint</h2>
          {form.severity === "SAFETY" && (
            <div className="bg-red-50 border border-red-300 rounded p-2 text-xs text-red-800 font-medium">
              SAFETY severity will auto-trigger recall flag and mark as regulatory reporting required.
            </div>
          )}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: "Consumer Name", key: "consumer_name", placeholder: "Optional" },
              { label: "Contact (Phone/Email)", key: "consumer_contact", placeholder: "Optional" },
              { label: "Consumer Location", key: "consumer_location", placeholder: "e.g. Nairobi, Karen" },
              { label: "Product Name *", key: "product_name", placeholder: "e.g. Mango Juice 500ml" },
              { label: "Lot Number", key: "lot_number", placeholder: "e.g. LOT-2026-001" },
              { label: "Purchase Date", key: "purchase_date", placeholder: "YYYY-MM-DD" },
              { label: "Purchase Location", key: "purchase_location", placeholder: "e.g. Naivas Karen" },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={placeholder}
                  value={(form as unknown as Record<string, string>)[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Channel</label>
              <select value={form.channel} onChange={(e) => setForm((p) => ({ ...p, channel: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {CHANNELS.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Severity *</label>
              <select value={form.severity} onChange={(e) => setForm((p) => ({ ...p, severity: e.target.value }))}
                className={`w-full border rounded px-3 py-1.5 text-sm focus:outline-none ${form.severity === "SAFETY" ? "border-red-400 bg-red-50" : "border-gray-300"}`}>
                {SEVERITIES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Description *</label>
            <textarea rows={3} value={form.description} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
              placeholder="Detailed complaint description"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={saving || !form.product_name || !form.description}
              className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Logging…" : "Log Complaint"}</button>
            <button onClick={() => setShowForm(false)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {/* Complaint list */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">Complaints <span className="font-normal text-gray-400">({complaints.length})</span></h2>
        </div>
        {loading ? <div className="p-6 text-sm text-gray-400 text-center">Loading…</div> :
         complaints.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No complaints found.</div> : (
          <div className="divide-y">
            {complaints.map((c) => (
              <div key={c.id} className={`px-4 py-3 ${c.recall_triggered_flag ? "bg-red-50" : ""}`}>
                <div className="flex items-start gap-3">
                  {c.recall_triggered_flag && <span className="text-xs bg-red-600 text-white rounded px-2 py-0.5 font-bold shrink-0 mt-0.5">RECALL</span>}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs text-blue-600">{c.complaint_ref}</span>
                      <span className={`text-xs rounded-full px-2 py-0.5 ${SEV_COLOR[c.severity] ?? "bg-gray-100 text-gray-600"}`}>{c.severity}</span>
                      <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLOR[c.status] ?? "bg-gray-100 text-gray-600"}`}>{c.status}</span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 mt-0.5">{c.product_name}</p>
                    <p className="text-xs text-gray-500 truncate">{c.description}</p>
                    <div className="flex gap-3 text-xs text-gray-400 mt-0.5 flex-wrap">
                      {c.lot_number && <span>Lot: {c.lot_number}</span>}
                      <span>{c.channel.replace(/_/g, " ")}</span>
                      <span>{fmtDt(c.created_at)}</span>
                      {c.assigned_to && <span>→ {c.assigned_to}</span>}
                    </div>
                  </div>
                  <button onClick={() => { setSelected(c); setUpdateForm({ status: c.status, assigned_to: c.assigned_to ?? "", root_cause: c.root_cause ?? "", corrective_action: c.corrective_action ?? "" }); }}
                    className="text-xs text-blue-600 hover:text-blue-800 shrink-0">Update</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Update modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg space-y-4 p-6">
            <h2 className="text-sm font-semibold text-gray-800">Update Complaint — {selected.complaint_ref}</h2>
            <p className="text-xs text-gray-500">{selected.product_name} · {selected.severity}</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Status</label>
                <select value={updateForm.status} onChange={(e) => setUpdateForm((p) => ({ ...p, status: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                  {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Assigned To</label>
                <input type="text" value={updateForm.assigned_to} onChange={(e) => setUpdateForm((p) => ({ ...p, assigned_to: e.target.value }))}
                  placeholder="e.g. QA Manager"
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs text-gray-500 block mb-1">Root Cause</label>
                <textarea rows={2} value={updateForm.root_cause} onChange={(e) => setUpdateForm((p) => ({ ...p, root_cause: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs text-gray-500 block mb-1">Corrective Action</label>
                <textarea rows={2} value={updateForm.corrective_action} onChange={(e) => setUpdateForm((p) => ({ ...p, corrective_action: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={update} disabled={updating}
                className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{updating ? "Saving…" : "Save"}</button>
              <button onClick={() => setSelected(null)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
