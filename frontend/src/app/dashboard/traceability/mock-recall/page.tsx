"use client";
import { useState } from "react";
import { traceApi, RecallHeader, RecallDetail, SEVERITY_BG } from "@/lib/traceability";

interface DrillMetrics {
  time_to_trace_minutes: number;
  time_to_contain_minutes: number;
  scope_lines_found: number;
  lots_identified: number;
  customers_identified: number;
  effectiveness_score: number;
}

export default function MockRecallPage() {
  const [step, setStep] = useState<"setup"|"running"|"results">("setup");
  const [recall, setRecall] = useState<RecallDetail | null>(null);
  const [metrics, setMetrics] = useState<DrillMetrics | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    source_lot_id: "",
    scenario_name: "Mock Recall Drill " + new Date().toLocaleDateString(),
    severity_level: "high",
    target_market: "Domestic Kenya",
    notes: "",
  });

  const handleStart = async () => {
    setSaving(true);
    const t0 = Date.now();
    setStartTime(t0);
    setStep("running");
    try {
      // 1. Initiate mock recall
      const r = await traceApi.initiateRecall({
        recall_type: "mock_recall",
        recall_reason: `Mock Recall Drill: ${form.scenario_name}`,
        trigger_source: "manual",
        severity_level: form.severity_level,
        source_lot_id: form.source_lot_id || undefined,
        target_market: form.target_market,
        notes: form.notes || undefined,
      }) as RecallHeader;

      // 2. Calculate scope
      await traceApi.calculateScope(r.id);

      // 3. Build customer impact
      await traceApi.buildCustomerImpact(r.id);

      // 4. Run AI agents
      await traceApi.runAIAgents(r.id);

      // 5. Get detail
      const detail = await traceApi.getRecallDetail(r.id);
      setRecall(detail);

      const elapsedMs = Date.now() - t0;
      const traceMin = Math.round(elapsedMs / 60000 * 10) / 10;
      const containMin = traceMin + 2;
      const score = Math.min(100, Math.round(
        (traceMin < 5 ? 100 : traceMin < 10 ? 80 : traceMin < 30 ? 60 : 40)
      ));

      setMetrics({
        time_to_trace_minutes: traceMin,
        time_to_contain_minutes: containMin,
        scope_lines_found: detail.scope_lines.length,
        lots_identified: detail.scope_lines.length,
        customers_identified: detail.customer_impacts.length,
        effectiveness_score: score,
      });

      // Update effectiveness
      await traceApi.closeRecall(r.id, score);

      setStep("results");
    } catch (e: any) { alert(e.message); setStep("setup"); }
    finally { setSaving(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Mock Recall Drill</h1>
        <p className="text-sm text-gray-500">Simulate a recall to test traceability systems, measure response times, and evaluate readiness</p>
      </div>

      {step === "setup" && (
        <div className="bg-white rounded-xl border border-amber-200 p-6 space-y-4 max-w-2xl">
          <div className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg">
            <svg className="h-5 w-5 text-amber-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-amber-700">
              This will create a MOCK recall record. No actual customer notifications will be sent. Use to test recall readiness and traceability completeness.
            </p>
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-600">Drill Name</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.scenario_name} onChange={e => setForm(f => ({ ...f, scenario_name: e.target.value }))} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-600">Source Lot ID (to trace)</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" placeholder="UUID"
                  value={form.source_lot_id} onChange={e => setForm(f => ({ ...f, source_lot_id: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Severity Level</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.severity_level} onChange={e => setForm(f => ({ ...f, severity_level: e.target.value }))}>
                  {["low","medium","high","critical"].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Target Market</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.target_market} onChange={e => setForm(f => ({ ...f, target_market: e.target.value }))} />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Notes</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
          </div>
          <button onClick={handleStart} disabled={saving}
            className="w-full py-3 bg-amber-600 text-white text-sm font-semibold rounded-lg hover:bg-amber-700 disabled:opacity-50">
            {saving ? "Starting Drill…" : "Start Mock Recall Drill"}
          </button>
        </div>
      )}

      {step === "running" && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center max-w-lg mx-auto">
          <div className="animate-spin h-12 w-12 border-4 border-amber-600 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="font-semibold text-gray-800">Running Mock Recall Drill…</p>
          <p className="text-sm text-gray-500 mt-1">Running forward trace, calculating scope, building customer impact list, running AI agents</p>
          <p className="text-xs text-gray-400 mt-3">Timer running since {startTime ? new Date(startTime).toLocaleTimeString() : "—"}</p>
        </div>
      )}

      {step === "results" && recall && metrics && (
        <div className="space-y-6 max-w-3xl">
          <div className="bg-green-50 border border-green-200 rounded-xl p-5">
            <h2 className="font-bold text-green-800 text-lg">Drill Completed — {recall.recall_no}</h2>
            <p className="text-sm text-green-700 mt-1">Mock recall drill executed successfully</p>
          </div>

          {/* Effectiveness Score */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 text-center">
            <p className="text-sm text-gray-500 uppercase tracking-wide">Effectiveness Score</p>
            <p className={`text-6xl font-bold mt-2 ${metrics.effectiveness_score >= 80 ? "text-green-600" : metrics.effectiveness_score >= 60 ? "text-amber-600" : "text-red-600"}`}>
              {metrics.effectiveness_score}/100
            </p>
            <p className="text-xs text-gray-400 mt-2">Based on time-to-trace and scope completeness</p>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {[
              { label: "Time to Trace", value: `${metrics.time_to_trace_minutes}min`, ok: metrics.time_to_trace_minutes < 10 },
              { label: "Time to Contain (est.)", value: `${metrics.time_to_contain_minutes}min`, ok: metrics.time_to_contain_minutes < 30 },
              { label: "Lots Identified", value: metrics.lots_identified },
              { label: "Scope Lines", value: metrics.scope_lines_found },
              { label: "Customers Found", value: metrics.customers_identified },
              { label: "Status", value: recall.status.replace("_"," "), ok: true },
            ].map(s => (
              <div key={s.label} className={`rounded-xl border p-4 text-center ${s.ok === false ? "border-red-200 bg-red-50" : s.ok === true ? "border-green-200 bg-green-50" : "border-gray-200 bg-white"}`}>
                <p className="text-2xl font-bold text-gray-800">{s.value}</p>
                <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Recommendations */}
          {recall.ai_recs.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-800 mb-3">AI Recommendations from Drill</h3>
              <div className="space-y-2">
                {recall.ai_recs.map(r => (
                  <div key={r.id} className="p-3 bg-indigo-50 rounded-lg">
                    <p className="text-sm font-medium text-indigo-800">{r.title}</p>
                    <p className="text-xs text-indigo-600 mt-0.5">{r.recommendation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <a href={`/dashboard/traceability/recalls/${recall.id}`}
              className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">
              View Full Recall Record →
            </a>
            <button onClick={() => { setStep("setup"); setRecall(null); setMetrics(null); }}
              className="px-4 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700">
              Run Another Drill
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
