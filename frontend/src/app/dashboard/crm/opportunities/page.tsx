"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  crmApi, CRMRecord, CRMStage, fmtCurrency,
  STATUS_LABELS, STATUS_COLORS, TEMPERATURE_LABELS, TEMPERATURE_COLORS,
} from "@/lib/crm_pipeline";

export default function OpportunitiesPage() {
  const [records, setRecords] = useState<CRMRecord[]>([]);
  const [stages, setStages] = useState<CRMStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("OPEN");
  const [stageFilter, setStageFilter] = useState("");
  const [repFilter, setRepFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    company_name: "", contact_person_name: "", contact_email: "", contact_phone: "",
    expected_revenue: "", expected_close_date: "", assigned_rep_id: "", stage_id: "", notes: "",
  });
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      crmApi.getOpportunities({ status: statusFilter || undefined, stage_id: stageFilter || undefined }),
      crmApi.getStages(true),
    ]).then(([recs, stgs]) => { setRecords(recs); setStages(stgs); })
      .catch(console.error).finally(() => setLoading(false));
  }, [statusFilter, stageFilter]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { ...form };
      if (form.expected_revenue) payload.expected_revenue = parseFloat(form.expected_revenue);
      if (!form.stage_id) delete payload.stage_id;
      await crmApi.createOpportunity(payload as Partial<CRMRecord>);
      setShowCreate(false);
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const totalPipeline = records.reduce((s, r) => s + (r.expected_revenue || 0), 0);
  const weightedPipeline = records.reduce((s, r) => s + (r.expected_revenue || 0) * (r.probability_pct || 0) / 100, 0);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Opportunities</h1>
        <button onClick={() => setShowCreate(true)}
          className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700">
          + New Opportunity
        </button>
      </div>

      {/* Summary Bars */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-3">
          <div className="text-xs text-gray-500">Open Opportunities</div>
          <div className="text-xl font-bold text-purple-700">{records.filter(r => r.status === "OPEN").length}</div>
        </div>
        <div className="bg-white border rounded-xl p-3 shadow-sm">
          <div className="text-xs text-gray-500">Total Pipeline</div>
          <div className="text-xl font-bold text-gray-800">{fmtCurrency(totalPipeline)}</div>
        </div>
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3">
          <div className="text-xs text-gray-500">Weighted Pipeline</div>
          <div className="text-xl font-bold text-indigo-700">{fmtCurrency(weightedPipeline)}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Statuses</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={stageFilter} onChange={e => setStageFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Stages</option>
          {stages.map(s => <option key={s.id} value={s.id}>{s.stage_name}</option>)}
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
              <th className="px-3 py-2 text-left">Stage</th>
              <th className="px-3 py-2 text-left">Temp</th>
              <th className="px-3 py-2 text-left">Prob %</th>
              <th className="px-3 py-2 text-left">Expected Rev</th>
              <th className="px-3 py-2 text-left">Weighted</th>
              <th className="px-3 py-2 text-left">Close Date</th>
              <th className="px-3 py-2 text-left">Rep</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={11} className="px-3 py-6 text-center text-gray-400">Loading…</td></tr>}
            {!loading && records.length === 0 && <tr><td colSpan={11} className="px-3 py-6 text-center text-gray-400">No opportunities found</td></tr>}
            {records.map(rec => {
              const weighted = ((rec.expected_revenue || 0) * (rec.probability_pct || 0) / 100);
              return (
                <tr key={rec.id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs text-gray-500">{rec.opportunity_code || "—"}</td>
                  <td className="px-3 py-2 font-medium text-gray-800">{rec.company_name}</td>
                  <td className="px-3 py-2 text-xs text-gray-600">{rec.stage?.stage_name || "—"}</td>
                  <td className="px-3 py-2">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{ background: TEMPERATURE_COLORS[rec.temperature] + "22", color: TEMPERATURE_COLORS[rec.temperature] }}>
                      {TEMPERATURE_LABELS[rec.temperature]}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-gray-700">{rec.probability_pct ?? 0}%</td>
                  <td className="px-3 py-2 text-gray-800 font-medium">{fmtCurrency(rec.expected_revenue, rec.currency)}</td>
                  <td className="px-3 py-2 text-indigo-700">{fmtCurrency(weighted, rec.currency)}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{rec.expected_close_date || "—"}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{rec.assigned_rep_id || "—"}</td>
                  <td className="px-3 py-2">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{ background: STATUS_COLORS[rec.status] + "22", color: STATUS_COLORS[rec.status] }}>
                      {STATUS_LABELS[rec.status]}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <Link href={`/dashboard/crm/records/${rec.id}`} className="text-blue-600 hover:underline text-xs">View</Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg">New Opportunity</h2>
            <input placeholder="Company Name *" value={form.company_name}
              onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Contact Person" value={form.contact_person_name}
              onChange={e => setForm(f => ({ ...f, contact_person_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Email" value={form.contact_email}
              onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input type="number" placeholder="Expected Revenue" value={form.expected_revenue}
              onChange={e => setForm(f => ({ ...f, expected_revenue: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input type="date" placeholder="Expected Close Date" value={form.expected_close_date}
              onChange={e => setForm(f => ({ ...f, expected_close_date: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <select value={form.stage_id} onChange={e => setForm(f => ({ ...f, stage_id: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              <option value="">Select Stage</option>
              {stages.map(s => <option key={s.id} value={s.id}>{s.stage_name}</option>)}
            </select>
            <input placeholder="Assigned Rep ID" value={form.assigned_rep_id}
              onChange={e => setForm(f => ({ ...f, assigned_rep_id: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <div className="flex gap-2 pt-1">
              <button onClick={handleCreate} disabled={saving || !form.company_name}
                className="flex-1 bg-purple-600 text-white py-2 rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50">
                {saving ? "Saving…" : "Create Opportunity"}
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
