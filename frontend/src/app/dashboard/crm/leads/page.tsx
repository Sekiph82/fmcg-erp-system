"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  crmApi, CRMRecord, CRMStage, fmtCurrency,
  STATUS_LABELS, STATUS_COLORS, TEMPERATURE_LABELS, TEMPERATURE_COLORS, SOURCE_LABELS,
} from "@/lib/crm_pipeline";

export default function LeadsPage() {
  const [records, setRecords] = useState<CRMRecord[]>([]);
  const [stages, setStages] = useState<CRMStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("OPEN");
  const [tempFilter, setTempFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ company_name: "", contact_person_name: "", contact_email: "", contact_phone: "", source_type: "MANUAL", notes: "" });
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      crmApi.getLeads({ status: statusFilter || undefined, temperature: tempFilter || undefined }),
      crmApi.getStages(true),
    ]).then(([recs, stgs]) => {
      setRecords(recs);
      setStages(stgs);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter, tempFilter]);

  const handleCreate = async () => {
    setSaving(true);
    try {
      await crmApi.createLead(form as Partial<CRMRecord>);
      setShowCreate(false);
      setForm({ company_name: "", contact_person_name: "", contact_email: "", contact_phone: "", source_type: "MANUAL", notes: "" });
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Leads</h1>
        <button onClick={() => setShowCreate(true)} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + New Lead
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Statuses</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={tempFilter} onChange={e => setTempFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Temperatures</option>
          {Object.entries(TEMPERATURE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span className="text-sm text-gray-500">{records.length} records</span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs text-gray-600">
              <th className="px-3 py-2 text-left">Code</th>
              <th className="px-3 py-2 text-left">Company</th>
              <th className="px-3 py-2 text-left">Contact</th>
              <th className="px-3 py-2 text-left">Source</th>
              <th className="px-3 py-2 text-left">Stage</th>
              <th className="px-3 py-2 text-left">Temp</th>
              <th className="px-3 py-2 text-left">Score</th>
              <th className="px-3 py-2 text-left">Expected Rev</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={10} className="px-3 py-6 text-center text-gray-400">Loading…</td></tr>
            )}
            {!loading && records.length === 0 && (
              <tr><td colSpan={10} className="px-3 py-6 text-center text-gray-400">No leads found</td></tr>
            )}
            {records.map(rec => (
              <tr key={rec.id} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 font-mono text-xs text-gray-500">{rec.lead_code || "—"}</td>
                <td className="px-3 py-2 font-medium text-gray-800">{rec.company_name}</td>
                <td className="px-3 py-2 text-gray-600">
                  <div>{rec.contact_person_name}</div>
                  <div className="text-xs text-gray-400">{rec.contact_phone}</div>
                </td>
                <td className="px-3 py-2 text-gray-500 text-xs">{SOURCE_LABELS[rec.source_type] || rec.source_type}</td>
                <td className="px-3 py-2 text-gray-600 text-xs">{rec.stage?.stage_name || "—"}</td>
                <td className="px-3 py-2">
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{ background: TEMPERATURE_COLORS[rec.temperature] + "22", color: TEMPERATURE_COLORS[rec.temperature] }}>
                    {TEMPERATURE_LABELS[rec.temperature]}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1">
                    <div className="w-12 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${rec.lead_score}%` }} />
                    </div>
                    <span className="text-xs text-gray-500">{rec.lead_score}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-gray-700">{fmtCurrency(rec.expected_revenue, rec.currency)}</td>
                <td className="px-3 py-2">
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{ background: STATUS_COLORS[rec.status] + "22", color: STATUS_COLORS[rec.status] }}>
                    {STATUS_LABELS[rec.status]}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <Link href={`/dashboard/crm/records/${rec.id}`}
                    className="text-blue-600 hover:underline text-xs">View</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg">New Lead</h2>
            <input placeholder="Company Name *" value={form.company_name}
              onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Contact Person" value={form.contact_person_name}
              onChange={e => setForm(f => ({ ...f, contact_person_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Email" value={form.contact_email}
              onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Phone" value={form.contact_phone}
              onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <select value={form.source_type}
              onChange={e => setForm(f => ({ ...f, source_type: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              {Object.entries(SOURCE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <textarea placeholder="Notes" value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
            <div className="flex gap-2 pt-1">
              <button onClick={handleCreate} disabled={saving || !form.company_name}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Saving…" : "Create Lead"}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="flex-1 border rounded-lg py-2 text-sm hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
