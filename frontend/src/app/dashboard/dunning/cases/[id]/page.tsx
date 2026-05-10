"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  dunningApi, DunningCase, DunningCaseInvoice, DunningActionLog, DunningPTP,
  DunningException, CASE_STATUS_COLORS, PTP_STATUS_COLORS, OUTCOME_COLORS, DunningActionType,
} from "@/lib/dunning";

type Tab = "overview" | "invoices" | "timeline" | "ptps" | "exceptions";

export default function DunningCaseDetail() {
  const { id } = useParams<{ id: string }>();
  const [dc, setDC] = useState<DunningCase | null>(null);
  const [invoices, setInvoices] = useState<DunningCaseInvoice[]>([]);
  const [actions, setActions] = useState<DunningActionLog[]>([]);
  const [ptps, setPTPs] = useState<DunningPTP[]>([]);
  const [exceptions, setExceptions] = useState<DunningException[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [reminderChannel, setReminderChannel] = useState<DunningActionType>("EMAIL");
  const [noteText, setNoteText] = useState("");
  const [ptpForm, setPTPForm] = useState({ promised_amount: "", promised_date: "", recorded_by: "", notes: "" });
  const [holdForm, setHoldForm] = useState({ reason: "", applied_by: "" });
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    Promise.all([
      dunningApi.getCase(id),
      dunningApi.getCaseInvoices(id),
      dunningApi.listActions(id),
      dunningApi.listPTPs(id),
      dunningApi.listExceptions(id),
    ]).then(([c, inv, act, p, exc]) => { setDC(c); setInvoices(inv); setActions(act); setPTPs(p); setExceptions(exc); });
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const sendReminder = async () => {
    setSaving(true);
    await dunningApi.sendReminder(id, reminderChannel);
    setSaving(false);
    load();
  };

  const addNote = async () => {
    if (!noteText.trim()) return;
    setSaving(true);
    await dunningApi.addNote(id, noteText);
    setNoteText("");
    setSaving(false);
    load();
  };

  const createPTP = async () => {
    setSaving(true);
    await dunningApi.createPTP(id, {
      promised_amount: Number(ptpForm.promised_amount),
      promised_date: ptpForm.promised_date,
      recorded_by: ptpForm.recorded_by,
      notes: ptpForm.notes || undefined,
    });
    setPTPForm({ promised_amount: "", promised_date: "", recorded_by: "", notes: "" });
    setSaving(false);
    load();
  };

  const applyHold = async () => {
    setSaving(true);
    await dunningApi.applyCreditHold(id, holdForm.reason, holdForm.applied_by);
    setSaving(false);
    load();
  };

  const releaseHold = async () => {
    setSaving(true);
    await dunningApi.releaseCreditHold(id, "manual_release");
    setSaving(false);
    load();
  };

  if (!dc) return <div className="p-6 text-gray-400">Loading…</div>;

  const TABS: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "invoices", label: `Invoices (${invoices.length})` },
    { key: "timeline", label: `Timeline (${actions.length})` },
    { key: "ptps", label: `PTPs (${ptps.length})` },
    { key: "exceptions", label: `Exceptions (${exceptions.length})` },
  ];

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <a href="/dashboard/dunning/cases" className="text-blue-600 hover:underline text-sm">← Cases</a>
            <h1 className="text-xl font-bold text-gray-900">{dc.case_no}</h1>
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${CASE_STATUS_COLORS[dc.case_status]}`}>{dc.case_status}</span>
            {dc.credit_hold_flag && <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-bold">CREDIT HOLD</span>}
          </div>
          <div className="text-sm text-gray-500 mt-1">
            Customer: {dc.customer_id.slice(0, 12)}… · Level {dc.current_level_no} · Priority {dc.priority_score}/100
          </div>
        </div>
        <div className="flex gap-2">
          <select value={reminderChannel} onChange={(e) => setReminderChannel(e.target.value as DunningActionType)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
            {(["EMAIL", "SMS", "WHATSAPP", "CALL_REMINDER"] as DunningActionType[]).map((c) => (
              <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
            ))}
          </select>
          <button onClick={sendReminder} disabled={saving}
            className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            Send Reminder
          </button>
          {dc.credit_hold_flag ? (
            <button onClick={releaseHold} disabled={saving}
              className="px-3 py-2 bg-green-600 text-white rounded-lg text-sm font-medium">
              Release Hold
            </button>
          ) : (
            <button onClick={() => setTab("overview")}
              className="px-3 py-2 bg-red-600 text-white rounded-lg text-sm font-medium">
              Apply Hold
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition ${tab === t.key ? "border-blue-600 text-blue-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === "overview" && (
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Case Summary</h3>
              <div className="space-y-2 text-sm">
                {[
                  ["Total Overdue", `${Number(dc.total_overdue_amount).toLocaleString()}`],
                  ["Oldest Due Date", dc.oldest_due_date || "—"],
                  ["Current Level", `Level ${dc.current_level_no}`],
                  ["Next Action Date", dc.next_action_date || "—"],
                  ["Last Action", dc.latest_action_date ? new Date(dc.latest_action_date).toLocaleDateString() : "—"],
                  ["Credit Hold", dc.credit_hold_flag ? `YES — ${dc.credit_hold_date}` : "No"],
                  ["Hold Reason", dc.credit_hold_reason || "—"],
                ].map(([k, v]) => (
                  <div key={String(k)} className="flex justify-between">
                    <span className="text-gray-500">{k}</span>
                    <span className="font-medium text-gray-900">{v}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Apply Credit Hold</h3>
              <div className="space-y-3">
                <input value={holdForm.reason} onChange={(e) => setHoldForm({ ...holdForm, reason: e.target.value })}
                  placeholder="Hold reason" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                <input value={holdForm.applied_by} onChange={(e) => setHoldForm({ ...holdForm, applied_by: e.target.value })}
                  placeholder="Applied by" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                <button onClick={applyHold} className="w-full px-3 py-2 bg-red-600 text-white rounded-lg text-sm font-medium">Apply Hold</button>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Collector Notes</h3>
              <textarea value={dc.collector_notes || ""} readOnly rows={4}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50" />
              <div className="mt-3 flex gap-2">
                <input value={noteText} onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Add note…" className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                <button onClick={addNote} className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm">Add</button>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Record Promise-to-Pay</h3>
              <div className="space-y-2">
                <input type="number" value={ptpForm.promised_amount} onChange={(e) => setPTPForm({ ...ptpForm, promised_amount: e.target.value })}
                  placeholder="Promised amount" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                <input type="date" value={ptpForm.promised_date} onChange={(e) => setPTPForm({ ...ptpForm, promised_date: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                <input value={ptpForm.recorded_by} onChange={(e) => setPTPForm({ ...ptpForm, recorded_by: e.target.value })}
                  placeholder="Recorded by" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                <button onClick={createPTP} disabled={saving}
                  className="w-full px-3 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium">
                  Record PTP
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Invoices */}
      {tab === "invoices" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Invoice #", "Due Date", "Balance", "Days Overdue", "Dispute", "Excluded", "Notes"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.map((inv) => (
                <tr key={inv.id} className={inv.dispute_flag ? "bg-orange-50" : ""}>
                  <td className="px-4 py-3 font-medium text-blue-700">{inv.invoice_number}</td>
                  <td className="px-4 py-3 text-gray-600">{inv.invoice_due_date}</td>
                  <td className="px-4 py-3 font-mono font-semibold text-red-700">{Number(inv.invoice_balance_amount).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${inv.days_overdue > 30 ? "bg-red-100 text-red-800" : inv.days_overdue > 7 ? "bg-orange-100 text-orange-800" : "bg-yellow-100 text-yellow-800"}`}>
                      {inv.days_overdue}d
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {inv.dispute_flag ? <span className="px-2 py-0.5 bg-orange-100 text-orange-800 rounded-full text-xs font-semibold">DISPUTED</span> : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {inv.excluded_from_dunning ? <span className="text-xs text-gray-500">Excluded</span> : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">{inv.dispute_reason || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Timeline */}
      {tab === "timeline" && (
        <div className="space-y-3">
          {actions.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">No actions logged yet.</div>
          ) : actions.map((a) => (
            <div key={a.id} className="flex gap-4 bg-white rounded-xl border border-gray-200 p-4">
              <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0"></div>
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-sm text-gray-900">{a.action_type.replace(/_/g, " ")}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs ${OUTCOME_COLORS[a.outcome_status]}`}>{a.outcome_status}</span>
                  <span className="text-xs text-gray-400">Level {a.level_no} · {a.sent_by_system_flag ? "System" : "Manual"}</span>
                </div>
                {a.rendered_subject && <div className="text-sm text-gray-700 mt-1 font-medium">{a.rendered_subject}</div>}
                {a.rendered_body && <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">{a.rendered_body}</div>}
                <div className="text-xs text-gray-400 mt-1">{new Date(a.action_datetime).toLocaleString()}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* PTPs */}
      {tab === "ptps" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Promised Amount", "Promise Date", "Recorded By", "Status", "Notes", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {ptps.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No PTPs recorded.</td></tr>
              ) : ptps.map((p) => (
                <tr key={p.id} className={p.status === "BROKEN" ? "bg-red-50" : ""}>
                  <td className="px-4 py-3 font-mono font-semibold">{Number(p.promised_amount).toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-700">{p.promised_date}</td>
                  <td className="px-4 py-3 text-gray-500">{p.recorded_by}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${PTP_STATUS_COLORS[p.status]}`}>{p.status.replace(/_/g, " ")}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{p.notes || "—"}</td>
                  <td className="px-4 py-3">
                    {p.status === "OPEN" && (
                      <div className="flex gap-2">
                        <button onClick={() => dunningApi.updatePTP(p.id, "MET").then(load)}
                          className="text-green-600 hover:underline text-xs">Met</button>
                        <button onClick={() => dunningApi.updatePTP(p.id, "BROKEN").then(load)}
                          className="text-red-600 hover:underline text-xs">Broken</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Exceptions */}
      {tab === "exceptions" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Type", "Approved By", "Start Date", "End Date", "Reason"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {exceptions.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No exceptions.</td></tr>
              ) : exceptions.map((e) => (
                <tr key={e.id}>
                  <td className="px-4 py-3 font-medium">{e.exception_type.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3 text-gray-600">{e.approved_by}</td>
                  <td className="px-4 py-3 text-gray-600">{e.start_date}</td>
                  <td className="px-4 py-3 text-gray-600">{e.end_date || "Open-ended"}</td>
                  <td className="px-4 py-3 text-gray-500 text-sm max-w-xs">{e.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
