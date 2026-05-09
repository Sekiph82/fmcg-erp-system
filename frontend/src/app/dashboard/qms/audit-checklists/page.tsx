"use client";
import { useEffect, useState } from "react";

interface Checklist { id: string; audit_ref: string; standard: string; audit_type: string; audit_date: string; conducted_by: string | null; score_pct: number | null; result: string; total_items: number; passed_items: number; certificate_issued: boolean; next_audit_date: string | null; }
interface ChecklistDetail extends Checklist { items: { section: string; item: string; requirement: string; result: string; finding: string | null }[]; }
interface Stats { by_result: Record<string, number>; by_standard: Record<string, number>; avg_score_pct: number | null; }

const STANDARDS = ["BRC", "FSSC_22000", "ISO_22000", "HALAL", "KOSHER", "HACCP_CODEX", "SQF", "CUSTOM"];
const AUDIT_TYPES = ["INTERNAL", "MOCK", "THIRD_PARTY", "REGULATORY"];

const RESULT_COLOR: Record<string, string> = {
  PASS: "bg-green-100 text-green-700", CONDITIONAL_PASS: "bg-amber-100 text-amber-700",
  FAIL: "bg-red-100 text-red-600", IN_PROGRESS: "bg-blue-100 text-blue-600",
};

export default function AuditChecklistsPage() {
  const [checklists, setChecklists] = useState<Checklist[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [selected, setSelected] = useState<ChecklistDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ standard: "BRC", audit_type: "INTERNAL", audit_date: new Date().toISOString().split("T")[0], conducted_by: "", lead_auditor: "", scope: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      fetch("/api/v1/qms/audit-checklists").then(r => r.json()),
      fetch("/api/v1/qms/audit-checklists/stats").then(r => r.json()),
    ]).then(([c, s]) => { setChecklists(c); setStats(s); }).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const openChecklist = async (id: string) => {
    const r = await fetch(`/api/v1/qms/audit-checklists/${id}`).catch(() => null);
    if (r && r.ok) setSelected(await r.json());
  };

  const save = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/qms/audit-checklists", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ standard: form.standard, audit_type: form.audit_type, audit_date: form.audit_date, conducted_by: form.conducted_by || undefined, lead_auditor: form.lead_auditor || undefined, scope: form.scope || undefined }),
      });
      if (!r.ok) throw new Error(await r.text());
      const created = await r.json();
      setShowForm(false); setSelected(created); load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const markItem = async (itemIndex: number, result: string, finding?: string) => {
    if (!selected) return;
    await fetch(`/api/v1/qms/audit-checklists/${selected.id}/items`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify([{ item_index: itemIndex, result, finding: finding || undefined }]),
    });
    const r = await fetch(`/api/v1/qms/audit-checklists/${selected.id}`);
    if (r.ok) setSelected(await r.json());
    load();
  };

  const RESULT_ICON: Record<string, string> = { pass: "✓", fail: "✗", na: "—", pending: "?" };
  const RESULT_CL: Record<string, string> = { pass: "text-green-600", fail: "text-red-600", na: "text-gray-400", pending: "text-gray-300" };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Checklists</h1>
          <p className="text-sm text-gray-500 mt-0.5">BRC, FSSC 22000, HALAL, KOSHER, HACCP Codex audit workflows</p>
        </div>
        <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded">+ New Audit</button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Total Audits", value: Object.values(stats.by_result).reduce((a, b) => a + b, 0), color: "text-gray-800" },
            { label: "Passed", value: stats.by_result.PASS ?? 0, color: "text-green-600" },
            { label: "Failed", value: stats.by_result.FAIL ?? 0, color: "text-red-600" },
            { label: "Avg Score", value: stats.avg_score_pct !== null ? `${stats.avg_score_pct}%` : "—", color: "text-blue-600" },
          ].map((k) => (
            <div key={k.label} className="bg-white border rounded-lg p-4 shadow-sm">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Checklist list */}
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">Audit Records</h2></div>
          {loading ? <div className="p-6 text-sm text-gray-400 text-center">Loading…</div> : checklists.length === 0 ? (
            <div className="p-6 text-sm text-gray-400 text-center">No audits yet.</div>
          ) : (
            <div className="divide-y">
              {checklists.map((c) => (
                <button key={c.id} onClick={() => openChecklist(c.id)} className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs text-blue-600">{c.audit_ref}</span>
                      <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${RESULT_COLOR[c.result] ?? "bg-gray-100"}`}>{c.result.replace(/_/g, " ")}</span>
                      {c.certificate_issued && <span className="text-xs text-green-600 font-medium">✓ Cert</span>}
                    </div>
                    <p className="text-sm font-medium text-gray-800 mt-0.5">{c.standard.replace(/_/g, " ")} — {c.audit_type}</p>
                    <p className="text-xs text-gray-400">{c.audit_date} {c.conducted_by && `· ${c.conducted_by}`}</p>
                    {c.score_pct !== null && (
                      <div className="mt-1 flex items-center gap-2">
                        <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${c.score_pct >= 95 ? "bg-green-500" : c.score_pct >= 75 ? "bg-amber-400" : "bg-red-400"}`} style={{ width: `${c.score_pct}%` }} />
                        </div>
                        <span className="text-xs text-gray-500">{c.score_pct}% ({c.passed_items}/{c.total_items})</span>
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Checklist runner / detail */}
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">
              {selected ? `${selected.audit_ref} — ${selected.standard.replace(/_/g, " ")}` : "Select an audit to run"}
            </h2>
          </div>
          {!selected ? (
            <div className="p-6 text-sm text-gray-400 text-center">Click an audit on the left to open the checklist runner.</div>
          ) : (
            <div className="divide-y max-h-[500px] overflow-y-auto">
              {(selected.items || []).map((item, idx) => (
                <div key={idx} className="px-4 py-3 space-y-1">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-400">§{item.section}</p>
                      <p className="text-sm font-medium text-gray-900">{item.item}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{item.requirement}</p>
                      {item.finding && <p className="text-xs text-red-600 italic mt-0.5">Finding: {item.finding}</p>}
                    </div>
                    <span className={`text-lg font-bold shrink-0 ${RESULT_CL[item.result] ?? "text-gray-300"}`}>{RESULT_ICON[item.result] ?? "?"}</span>
                  </div>
                  <div className="flex gap-2">
                    {["pass", "fail", "na"].map((r) => (
                      <button key={r} onClick={() => markItem(idx, r)}
                        className={`text-xs rounded px-2 py-0.5 border ${item.result === r ? r === "pass" ? "bg-green-500 text-white border-green-500" : r === "fail" ? "bg-red-500 text-white border-red-500" : "bg-gray-400 text-white border-gray-400" : "border-gray-300 text-gray-500 hover:bg-gray-50"}`}>
                        {r.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* New audit form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3 max-w-lg">
          <h2 className="text-sm font-semibold text-gray-700">Start New Audit</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Standard *</label>
              <select value={form.standard} onChange={(e) => setForm((p) => ({ ...p, standard: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {STANDARDS.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Audit Type</label>
              <select value={form.audit_type} onChange={(e) => setForm((p) => ({ ...p, audit_type: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {AUDIT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Date *</label>
              <input type="date" value={form.audit_date} onChange={(e) => setForm((p) => ({ ...p, audit_date: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Conducted By</label>
              <input type="text" value={form.conducted_by} onChange={(e) => setForm((p) => ({ ...p, conducted_by: e.target.value }))} placeholder="e.g. QA Manager"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={saving} className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Creating…" : "Start Audit"}</button>
            <button onClick={() => setShowForm(false)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
