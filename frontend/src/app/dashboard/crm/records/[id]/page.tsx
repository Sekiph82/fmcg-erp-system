"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  crmApi, CRMRecord, CRMStage, CRMActivity, CRM360View,
  fmtCurrency, STATUS_LABELS, STATUS_COLORS, TEMPERATURE_LABELS, TEMPERATURE_COLORS,
  ACTIVITY_TYPE_LABELS, ACTIVITY_RESULT_LABELS, LOSS_REASON_LABELS, WIN_REASON_LABELS,
} from "@/lib/crm_pipeline";

type Tab = "overview" | "activities" | "products" | "competitors" | "360" | "close";

const RISK_COLOR: Record<string, string> = {
  LOW: "#10B981",
  MEDIUM: "#F59E0B",
  HIGH: "#EF4444",
  UNKNOWN: "#6B7280",
};

export default function RecordDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [record, setRecord] = useState<CRMRecord | null>(null);
  const [view360, setView360] = useState<CRM360View | null>(null);
  const [stages, setStages] = useState<CRMStage[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);

  // Close forms
  const [showWon, setShowWon] = useState(false);
  const [showLost, setShowLost] = useState(false);
  const [showConvert, setShowConvert] = useState(false);
  const [wonForm, setWonForm] = useState({ final_revenue: "", win_reason_code: "", competitor_name: "", narrative: "" });
  const [lostForm, setLostForm] = useState({ loss_reason_code: "", competitor_name: "", narrative: "" });
  const [convertForm, setConvertForm] = useState({ expected_revenue: "", expected_close_date: "", stage_id: "" });
  const [saving, setSaving] = useState(false);

  // Activity form
  const [showActivity, setShowActivity] = useState(false);
  const [actForm, setActForm] = useState({ activity_type: "CALL", subject: "", description: "", due_datetime: "", assigned_to: "" });

  const load = useCallback(async () => {
    try {
      const [rec, stgs] = await Promise.all([crmApi.getRecord(id), crmApi.getStages(true)]);
      setRecord(rec);
      setStages(stgs);
      crmApi.get360(id).then(setView360).catch(() => {});
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handleCloseWon = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { ...wonForm };
      if (wonForm.final_revenue) payload.final_revenue = parseFloat(wonForm.final_revenue);
      await crmApi.closeWon(id, payload);
      await load();
      setShowWon(false);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleCloseLost = async () => {
    setSaving(true);
    try {
      await crmApi.closeLost(id, { ...lostForm });
      await load();
      setShowLost(false);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleConvert = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { ...convertForm };
      if (convertForm.expected_revenue) payload.expected_revenue = parseFloat(convertForm.expected_revenue);
      if (!convertForm.stage_id) delete payload.stage_id;
      await crmApi.convert(id, payload);
      await load();
      setShowConvert(false);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleAddActivity = async () => {
    setSaving(true);
    try {
      await crmApi.createActivity({ ...actForm, crm_record_id: id } as Parameters<typeof crmApi.createActivity>[0]);
      setShowActivity(false);
      setActForm({ activity_type: "CALL", subject: "", description: "", due_datetime: "", assigned_to: "" });
      await load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleCompleteActivity = async (actId: string) => {
    try {
      await crmApi.completeActivity(actId, { result_status: "COMPLETED" });
      await load();
    } catch (e) { console.error(e); }
  };

  const handleUpdateScore = async () => {
    try { await crmApi.updateScore(id); await load(); } catch (e) { console.error(e); }
  };

  if (loading) return <div className="p-6 text-gray-500">Loading…</div>;
  if (!record) return <div className="p-6 text-red-500">Record not found</div>;

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "activities", label: `Activities (${record.activities?.length || 0})` },
    { id: "products", label: `Products (${record.interest_lines?.length || 0})` },
    { id: "competitors", label: `Competitors (${record.competitors?.length || 0})` },
    { id: "360", label: "360 View" },
    { id: "close", label: "Close Deal" },
  ];

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Link href="/dashboard/crm" className="text-sm text-gray-400 hover:underline">CRM</Link>
            <span className="text-gray-300">/</span>
            <span className="text-sm text-gray-600">{record.company_name}</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{record.company_name}</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs font-mono text-gray-500">{record.lead_code || record.opportunity_code}</span>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{ background: STATUS_COLORS[record.status] + "22", color: STATUS_COLORS[record.status] }}>
              {STATUS_LABELS[record.status]}
            </span>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{ background: TEMPERATURE_COLORS[record.temperature] + "22", color: TEMPERATURE_COLORS[record.temperature] }}>
              {TEMPERATURE_LABELS[record.temperature]}
            </span>
            <span className="text-xs text-gray-500">{record.record_type}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {record.record_type === "LEAD" && record.status === "OPEN" && (
            <button onClick={() => setShowConvert(true)}
              className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700">
              Convert to Opportunity
            </button>
          )}
          <button onClick={() => setShowActivity(true)}
            className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
            + Activity
          </button>
          <button onClick={handleUpdateScore}
            className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
            Update Score
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t.id ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {tab === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border shadow-sm p-4 space-y-3">
            <h2 className="font-semibold text-gray-800">Contact Details</h2>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-gray-500">Contact</div><div className="text-gray-800">{record.contact_person_name || "—"}</div>
              <div className="text-gray-500">Email</div><div className="text-gray-800">{record.contact_email || "—"}</div>
              <div className="text-gray-500">Phone</div><div className="text-gray-800">{record.contact_phone || "—"}</div>
              <div className="text-gray-500">Region</div><div className="text-gray-800">{record.region_id || "—"}</div>
              <div className="text-gray-500">Channel</div><div className="text-gray-800">{record.channel_id || "—"}</div>
            </div>
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-4 space-y-3">
            <h2 className="font-semibold text-gray-800">Deal Details</h2>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-gray-500">Stage</div><div className="text-gray-800">{record.stage?.stage_name || "—"}</div>
              <div className="text-gray-500">Probability</div><div className="text-gray-800">{record.probability_pct ?? 0}%</div>
              <div className="text-gray-500">Expected Rev</div><div className="text-gray-800 font-semibold">{fmtCurrency(record.expected_revenue, record.currency)}</div>
              <div className="text-gray-500">Expected Margin</div><div className="text-gray-800">{fmtCurrency(record.expected_margin, record.currency)}</div>
              <div className="text-gray-500">Close Date</div><div className="text-gray-800">{record.expected_close_date || "—"}</div>
              <div className="text-gray-500">Next Action</div><div className="text-gray-800">{record.next_action_date || "—"}</div>
              <div className="text-gray-500">Rep</div><div className="text-gray-800">{record.assigned_rep_id || "—"}</div>
              <div className="text-gray-500">Lead Score</div>
              <div className="flex items-center gap-1">
                <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${record.lead_score}%` }} />
                </div>
                <span className="text-xs">{record.lead_score}/100</span>
              </div>
            </div>
          </div>
          {record.notes && (
            <div className="md:col-span-2 bg-white rounded-xl border shadow-sm p-4">
              <h2 className="font-semibold text-gray-800 mb-2">Notes</h2>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{record.notes}</p>
            </div>
          )}
          {record.win_loss && (
            <div className="md:col-span-2 bg-white rounded-xl border shadow-sm p-4">
              <h2 className="font-semibold text-gray-800 mb-2">Win/Loss Record</h2>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-gray-500">Result</div><div className="font-bold" style={{ color: record.win_loss.final_status === "WON" ? "#10B981" : "#EF4444" }}>{record.win_loss.final_status}</div>
                <div className="text-gray-500">Close Date</div><div>{record.win_loss.close_date || "—"}</div>
                <div className="text-gray-500">Final Revenue</div><div>{fmtCurrency(record.win_loss.final_revenue)}</div>
                <div className="text-gray-500">Reason</div>
                <div>{record.win_loss.win_reason_code ? WIN_REASON_LABELS[record.win_loss.win_reason_code] : record.win_loss.loss_reason_code ? LOSS_REASON_LABELS[record.win_loss.loss_reason_code] : "—"}</div>
                {record.win_loss.competitor_name && <><div className="text-gray-500">Competitor</div><div>{record.win_loss.competitor_name}</div></>}
                {record.win_loss.narrative && <><div className="text-gray-500 col-span-2">Narrative</div><div className="col-span-2 text-xs text-gray-600">{record.win_loss.narrative}</div></>}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Activities Tab */}
      {tab === "activities" && (
        <div className="space-y-3">
          <button onClick={() => setShowActivity(true)}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            + Log Activity
          </button>
          {(record.activities || []).length === 0 && <p className="text-sm text-gray-400">No activities yet</p>}
          <div className="space-y-2">
            {(record.activities || []).map(act => (
              <div key={act.id} className="bg-white rounded-xl border shadow-sm p-4 flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-700 text-xs font-bold">
                  {ACTIVITY_TYPE_LABELS[act.activity_type]?.slice(0, 2).toUpperCase()}
                </div>
                <div className="flex-1">
                  <div className="font-medium text-gray-800 text-sm">{act.subject}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {ACTIVITY_TYPE_LABELS[act.activity_type]} · {act.result_status}
                    {act.due_datetime && ` · Due: ${new Date(act.due_datetime).toLocaleDateString()}`}
                  </div>
                  {act.description && <p className="text-xs text-gray-600 mt-1">{act.description}</p>}
                  {act.next_step && <p className="text-xs text-indigo-600 mt-1">Next: {act.next_step}</p>}
                </div>
                {act.result_status === "PLANNED" && (
                  <button onClick={() => handleCompleteActivity(act.id)}
                    className="text-xs text-green-600 hover:underline flex-shrink-0">Complete</button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Products Tab */}
      {tab === "products" && (
        <div className="space-y-3">
          <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-600">
                  <th className="px-3 py-2 text-left">Item</th>
                  <th className="px-3 py-2 text-left">Brand</th>
                  <th className="px-3 py-2 text-left">Exp Qty</th>
                  <th className="px-3 py-2 text-left">Exp Value</th>
                  <th className="px-3 py-2 text-left">Competitor</th>
                  <th className="px-3 py-2 text-left">Comp Price</th>
                </tr>
              </thead>
              <tbody>
                {(record.interest_lines || []).length === 0 && (
                  <tr><td colSpan={6} className="px-3 py-6 text-center text-gray-400">No product interests</td></tr>
                )}
                {(record.interest_lines || []).map(line => (
                  <tr key={line.id} className="border-b">
                    <td className="px-3 py-2 text-gray-800">{line.item_name || line.item_id || "—"}</td>
                    <td className="px-3 py-2 text-gray-600 text-xs">{line.brand_id || "—"}</td>
                    <td className="px-3 py-2 text-gray-600">{line.expected_qty ?? "—"}</td>
                    <td className="px-3 py-2 text-gray-800">{fmtCurrency(line.expected_value)}</td>
                    <td className="px-3 py-2 text-xs text-gray-500">{line.competitive_brand || "—"}</td>
                    <td className="px-3 py-2 text-gray-600">{fmtCurrency(line.competitor_price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Competitors Tab */}
      {tab === "competitors" && (
        <div className="space-y-3">
          {(record.competitors || []).length === 0 && <p className="text-sm text-gray-400">No competitors logged</p>}
          {(record.competitors || []).map(c => (
            <div key={c.id} className="bg-white rounded-xl border shadow-sm p-4">
              <div className="font-semibold text-gray-800">{c.competitor_name}</div>
              <div className="grid grid-cols-2 gap-2 text-sm mt-2">
                <div className="text-gray-500">Product</div><div>{c.competitor_product || "—"}</div>
                <div className="text-gray-500">Price</div><div>{fmtCurrency(c.competitor_price)}</div>
                <div className="text-gray-500">Risk</div><div>{c.risk_level || "—"}</div>
                {c.competitor_strength && <><div className="text-gray-500">Strength</div><div className="text-xs">{c.competitor_strength}</div></>}
                {c.competitor_weakness && <><div className="text-gray-500">Weakness</div><div className="text-xs">{c.competitor_weakness}</div></>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 360 View Tab */}
      {tab === "360" && (
        <div className="space-y-4">
          {!view360 ? (
            <div className="text-sm text-gray-400">Loading 360 view…</div>
          ) : (
            <>
              {/* Health Score */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border shadow-sm p-4 text-center">
                  <div className="text-xs text-gray-500 mb-1">Activity Health Score</div>
                  <div className="text-3xl font-bold text-indigo-700">{view360.activity_health_score}</div>
                  <div className="text-xs text-gray-400">/ 100</div>
                  <div className="w-full h-2 bg-gray-100 rounded-full mt-2 overflow-hidden">
                    <div className="h-full rounded-full"
                      style={{ width: `${view360.activity_health_score}%`, background: view360.activity_health_score >= 70 ? "#10B981" : view360.activity_health_score >= 40 ? "#F59E0B" : "#EF4444" }} />
                  </div>
                </div>
                <div className="bg-white rounded-xl border shadow-sm p-4 text-center">
                  <div className="text-xs text-gray-500 mb-1">Communication Risk</div>
                  <div className="text-2xl font-bold" style={{ color: RISK_COLOR[view360.communication_risk] }}>
                    {view360.communication_risk}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {view360.days_since_last_activity != null
                      ? `Last contact ${view360.days_since_last_activity}d ago`
                      : "No contact recorded"}
                  </div>
                </div>
                <div className="bg-white rounded-xl border shadow-sm p-4 text-center">
                  <div className="text-xs text-gray-500 mb-1">Pipeline Age</div>
                  <div className="text-2xl font-bold text-gray-800">{view360.pipeline_age_days}d</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {view360.days_to_close != null
                      ? view360.days_to_close >= 0
                        ? `${view360.days_to_close}d to close`
                        : `${Math.abs(view360.days_to_close)}d overdue`
                      : "No close date"}
                  </div>
                </div>
              </div>

              {/* Activity Metrics */}
              <div className="bg-white rounded-xl border shadow-sm p-4">
                <h3 className="font-semibold text-gray-800 mb-3 text-sm">Activity Metrics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                  <div>
                    <div className="text-xl font-bold text-gray-800">{view360.total_activities}</div>
                    <div className="text-xs text-gray-400">Total</div>
                  </div>
                  <div>
                    <div className="text-xl font-bold text-green-600">{view360.completed_activities}</div>
                    <div className="text-xs text-gray-400">Completed</div>
                  </div>
                  <div>
                    <div className="text-xl font-bold text-red-500">{view360.overdue_activities}</div>
                    <div className="text-xs text-gray-400">Overdue</div>
                  </div>
                  <div>
                    <div className="text-xl font-bold text-indigo-700">{view360.activity_completion_rate}%</div>
                    <div className="text-xs text-gray-400">Completion Rate</div>
                  </div>
                </div>
              </div>

              {/* Deal Intelligence */}
              <div className="bg-white rounded-xl border shadow-sm p-4">
                <h3 className="font-semibold text-gray-800 mb-3 text-sm">Deal Intelligence</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="text-gray-500">Weighted Value</div>
                  <div className="font-semibold text-indigo-700">{fmtCurrency(view360.weighted_value)}</div>
                  <div className="text-gray-500">Products Interested</div>
                  <div>{view360.interest_product_count}</div>
                  <div className="text-gray-500">Territory</div>
                  <div>{view360.territory_name || "—"}</div>
                  <div className="text-gray-500">Credit Signal</div>
                  <div className="text-gray-400 italic">{view360.credit_signal}</div>
                  <div className="text-gray-500">Deal Risk</div>
                  <div>{view360.deal_risk_flag
                    ? <span className="text-red-600 font-medium">OVERDUE CLOSE DATE</span>
                    : <span className="text-green-600">On Track</span>}
                  </div>
                  {view360.last_activity_type && (
                    <>
                      <div className="text-gray-500">Last Activity</div>
                      <div>{view360.last_activity_type}</div>
                    </>
                  )}
                </div>
              </div>

              {/* Summary Flags */}
              {view360.summary_flags.length > 0 && (
                <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
                  <h3 className="font-semibold text-orange-800 mb-2 text-sm">Action Flags</h3>
                  <div className="flex flex-wrap gap-2">
                    {view360.summary_flags.map(flag => (
                      <span key={flag} className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded-full font-medium">
                        {flag.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Close Deal Tab */}
      {tab === "close" && record.status === "OPEN" && (
        <div className="space-y-4 max-w-lg">
          <p className="text-sm text-gray-600">Record the outcome of this {record.record_type.toLowerCase()}.</p>
          <div className="flex gap-3">
            <button onClick={() => { setShowWon(true); setShowLost(false); }}
              className="flex-1 py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700">
              Mark as Won
            </button>
            <button onClick={() => { setShowLost(true); setShowWon(false); }}
              className="flex-1 py-3 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700">
              Mark as Lost
            </button>
          </div>
          <button onClick={() => crmApi.onHold(id).then(load)}
            className="w-full py-2 border-2 border-yellow-400 text-yellow-700 rounded-xl font-medium hover:bg-yellow-50">
            Put On Hold
          </button>
        </div>
      )}
      {tab === "close" && record.status !== "OPEN" && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">This record is {STATUS_LABELS[record.status]}.</p>
          {record.status !== "ARCHIVED" && (
            <button onClick={() => crmApi.reopen(id).then(load)}
              className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">
              Reopen
            </button>
          )}
        </div>
      )}

      {/* Convert Modal */}
      {showConvert && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg">Convert to Opportunity</h2>
            <input type="number" placeholder="Expected Revenue" value={convertForm.expected_revenue}
              onChange={e => setConvertForm(f => ({ ...f, expected_revenue: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input type="date" value={convertForm.expected_close_date}
              onChange={e => setConvertForm(f => ({ ...f, expected_close_date: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <select value={convertForm.stage_id} onChange={e => setConvertForm(f => ({ ...f, stage_id: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              <option value="">Select Stage</option>
              {stages.map(s => <option key={s.id} value={s.id}>{s.stage_name}</option>)}
            </select>
            <div className="flex gap-2 pt-1">
              <button onClick={handleConvert} disabled={saving}
                className="flex-1 bg-purple-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {saving ? "Converting…" : "Convert"}
              </button>
              <button onClick={() => setShowConvert(false)} className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Won Modal */}
      {showWon && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg text-green-700">Mark as Won</h2>
            <input type="number" placeholder="Final Revenue" value={wonForm.final_revenue}
              onChange={e => setWonForm(f => ({ ...f, final_revenue: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <select value={wonForm.win_reason_code}
              onChange={e => setWonForm(f => ({ ...f, win_reason_code: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              <option value="">Win Reason</option>
              {Object.entries(WIN_REASON_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input placeholder="Competitor (if any)" value={wonForm.competitor_name}
              onChange={e => setWonForm(f => ({ ...f, competitor_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <textarea placeholder="Narrative" value={wonForm.narrative}
              onChange={e => setWonForm(f => ({ ...f, narrative: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
            <div className="flex gap-2 pt-1">
              <button onClick={handleCloseWon} disabled={saving}
                className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {saving ? "Saving…" : "Confirm Won"}
              </button>
              <button onClick={() => setShowWon(false)} className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Lost Modal */}
      {showLost && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg text-red-700">Mark as Lost</h2>
            <select value={lostForm.loss_reason_code}
              onChange={e => setLostForm(f => ({ ...f, loss_reason_code: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              <option value="">Loss Reason *</option>
              {Object.entries(LOSS_REASON_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input placeholder="Competitor (if any)" value={lostForm.competitor_name}
              onChange={e => setLostForm(f => ({ ...f, competitor_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <textarea placeholder="Narrative" value={lostForm.narrative}
              onChange={e => setLostForm(f => ({ ...f, narrative: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
            <div className="flex gap-2 pt-1">
              <button onClick={handleCloseLost} disabled={saving}
                className="flex-1 bg-red-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {saving ? "Saving…" : "Confirm Lost"}
              </button>
              <button onClick={() => setShowLost(false)} className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Activity Modal */}
      {showActivity && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg">Log Activity</h2>
            <select value={actForm.activity_type}
              onChange={e => setActForm(f => ({ ...f, activity_type: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              {Object.entries(ACTIVITY_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input placeholder="Subject *" value={actForm.subject}
              onChange={e => setActForm(f => ({ ...f, subject: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <textarea placeholder="Description" value={actForm.description}
              onChange={e => setActForm(f => ({ ...f, description: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
            <input type="datetime-local" placeholder="Due Date/Time" value={actForm.due_datetime}
              onChange={e => setActForm(f => ({ ...f, due_datetime: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Assigned To" value={actForm.assigned_to}
              onChange={e => setActForm(f => ({ ...f, assigned_to: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <div className="flex gap-2 pt-1">
              <button onClick={handleAddActivity} disabled={saving || !actForm.subject}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {saving ? "Saving…" : "Log Activity"}
              </button>
              <button onClick={() => setShowActivity(false)}
                className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
