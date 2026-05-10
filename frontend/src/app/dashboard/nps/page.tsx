"use client";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

interface NPSAnalytics {
  nps_score: number | null;
  total_responses: number;
  promoters: number;
  passives: number;
  detractors: number;
  promoter_pct: number;
  detractor_pct: number;
  score_distribution: Record<string, number>;
  avg_score: number | null;
  top_detractors: { customer_name?: string; score: number; comment: string }[];
  top_promoters: { customer_name?: string; score: number; comment: string }[];
}

interface CustomerNPS {
  customer_id: string;
  customer_name?: string;
  avg_score: number;
  response_count: number;
  classification: string;
}

interface Survey {
  id: string;
  title: string;
  target_type: string;
  response_count: number;
  nps_score: number;
}

const CLASS_COLORS: Record<string, string> = {
  PROMOTER: "bg-green-100 text-green-700",
  PASSIVE: "bg-amber-100 text-amber-700",
  DETRACTOR: "bg-red-100 text-red-600",
};

function NPSGauge({ score }: { score: number | null }) {
  if (score === null) return <div className="text-center text-gray-400 text-sm">No data</div>;
  const color = score >= 50 ? "text-green-600" : score >= 0 ? "text-amber-600" : "text-red-600";
  return (
    <div className={`text-center ${color}`}>
      <p className="text-5xl font-bold">{score > 0 ? `+${score}` : score}</p>
      <p className="text-xs text-gray-500 mt-1">NPS Score</p>
      <p className="text-xs text-gray-400 mt-0.5">
        {score >= 50 ? "Excellent 🟢" : score >= 30 ? "Good 🟡" : score >= 0 ? "Fair 🟠" : "Poor 🔴"}
      </p>
    </div>
  );
}

export default function NPSPage() {
  const [analytics, setAnalytics] = useState<NPSAnalytics | null>(null);
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [byCustomer, setByCustomer] = useState<CustomerNPS[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLog, setShowLog] = useState(false);
  const [logForm, setLogForm] = useState({
    survey_id: "", customer_id: "", score: "8", comment: "", channel: "manual",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [a, s, c] = await Promise.all([
        apiClient.get<NPSAnalytics>("/api/v1/nps/analytics"),
        apiClient.get<Survey[]>("/api/v1/nps/surveys"),
        apiClient.get<CustomerNPS[]>("/api/v1/nps/analytics/by-customer"),
      ]);
      setAnalytics(a.data); setSurveys(s.data); setByCustomer(c.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const logResponse = async () => {
    if (!logForm.customer_id || !logForm.survey_id) { setError("Customer ID + Survey required"); return; }
    setSaving(true); setError("");
    try {
      await apiClient.post("/api/v1/nps/responses", {
        survey_id: logForm.survey_id,
        customer_id: logForm.customer_id,
        score: parseInt(logForm.score),
        comment: logForm.comment || null,
        channel: logForm.channel,
      });
      setShowLog(false);
      setLogForm({ survey_id: "", customer_id: "", score: "8", comment: "", channel: "manual" });
      await load();
    } catch { setError("Failed to log response"); }
    finally { setSaving(false); }
  };

  const dist = analytics?.score_distribution ?? {};
  const maxDist = Math.max(...Object.values(dist), 1);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">NPS Tracking</h1>
          <p className="text-xs text-gray-500 mt-0.5">Net Promoter Score — measure customer loyalty and satisfaction.</p>
        </div>
        <div className="flex gap-2">
          <a href="/dashboard/nps/surveys"
            className="rounded border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
            Manage Surveys
          </a>
          <button onClick={() => { setShowLog(true); setError(""); }}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            + Log Response
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Main NPS score */}
          <div className="bg-white border rounded-xl p-6 shadow-sm flex flex-col items-center justify-center">
            <NPSGauge score={analytics?.nps_score ?? null} />
            {analytics && analytics.total_responses > 0 && (
              <div className="mt-4 grid grid-cols-3 gap-3 w-full text-center">
                {[
                  { label: "Promoters", value: analytics.promoters, pct: analytics.promoter_pct, color: "text-green-600" },
                  { label: "Passives", value: analytics.passives, pct: 100 - analytics.promoter_pct - analytics.detractor_pct, color: "text-amber-600" },
                  { label: "Detractors", value: analytics.detractors, pct: analytics.detractor_pct, color: "text-red-600" },
                ].map(s => (
                  <div key={s.label}>
                    <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
                    <p className="text-xs text-gray-500">{s.label}</p>
                    <p className="text-xs text-gray-400">{s.pct?.toFixed(0)}%</p>
                  </div>
                ))}
              </div>
            )}
            {analytics && (
              <p className="text-xs text-gray-400 mt-3">{analytics.total_responses} total responses</p>
            )}
          </div>

          {/* Score distribution */}
          <div className="bg-white border rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Score Distribution</h3>
            <div className="space-y-1.5">
              {Array.from({ length: 11 }, (_, i) => i).reverse().map(score => {
                const count = dist[String(score)] ?? 0;
                const pct = Math.round(count / maxDist * 100);
                const color = score >= 9 ? "bg-green-500" : score >= 7 ? "bg-amber-400" : "bg-red-400";
                return (
                  <div key={score} className="flex items-center gap-2">
                    <span className="w-4 text-xs text-gray-500 text-right">{score}</span>
                    <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                      <div className={`h-4 rounded-full ${color}`} style={{ width: `${pct}%` }} />
                    </div>
                    <span className="w-6 text-xs text-gray-500">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Active surveys */}
          <div className="bg-white border rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Surveys</h3>
            {surveys.length === 0 ? (
              <p className="text-xs text-gray-400">No surveys yet.</p>
            ) : (
              <div className="space-y-3">
                {surveys.map(s => (
                  <div key={s.id} className="border rounded-lg p-3">
                    <p className="text-xs font-medium text-gray-800">{s.title}</p>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-gray-400">{s.response_count} responses</span>
                      <span className={`text-xs font-bold ${s.nps_score >= 50 ? "text-green-600" : s.nps_score >= 0 ? "text-amber-600" : "text-red-600"}`}>
                        {s.nps_score > 0 ? "+" : ""}{s.nps_score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Customer NPS table */}
      {byCustomer.length > 0 && (
        <div className="bg-white border rounded-xl shadow-sm">
          <div className="px-5 py-3 border-b">
            <h3 className="text-sm font-semibold text-gray-700">NPS by Customer</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {["Customer", "Avg Score", "Responses", "Classification"].map(h => (
                    <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {byCustomer.map(c => (
                  <tr key={c.customer_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{c.customer_name ?? c.customer_id.slice(0, 8)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-bold ${c.avg_score >= 9 ? "text-green-600" : c.avg_score >= 7 ? "text-amber-600" : "text-red-600"}`}>
                          {c.avg_score.toFixed(1)}
                        </span>
                        <div className="w-20 h-2 bg-gray-200 rounded-full">
                          <div className={`h-2 rounded-full ${c.avg_score >= 9 ? "bg-green-500" : c.avg_score >= 7 ? "bg-amber-400" : "bg-red-400"}`}
                            style={{ width: `${c.avg_score / 10 * 100}%` }} />
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">{c.response_count}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${CLASS_COLORS[c.classification] ?? "bg-gray-100 text-gray-600"}`}>
                        {c.classification}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Verbatim feedback */}
      {analytics && (analytics.top_detractors.length > 0 || analytics.top_promoters.length > 0) && (
        <div className="grid grid-cols-2 gap-5">
          {[
            { label: "Detractor Comments", items: analytics.top_detractors, color: "border-red-200 bg-red-50", textColor: "text-red-700" },
            { label: "Promoter Comments", items: analytics.top_promoters, color: "border-green-200 bg-green-50", textColor: "text-green-700" },
          ].map(section => (
            <div key={section.label} className={`border rounded-xl p-4 ${section.color}`}>
              <h3 className={`text-xs font-semibold mb-3 ${section.textColor}`}>{section.label}</h3>
              <div className="space-y-2">
                {section.items.map((item, i) => (
                  <div key={i} className="bg-white rounded-lg p-3 border">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-700">{item.customer_name ?? "Anonymous"}</span>
                      <span className={`text-xs font-bold ${section.textColor}`}>{item.score}/10</span>
                    </div>
                    <p className="text-xs text-gray-600 italic">&quot;{item.comment}&quot;</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Log Response Modal */}
      {showLog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">Log NPS Response</h2>
              <button onClick={() => setShowLog(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-4">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Survey *</label>
                <select value={logForm.survey_id}
                  onChange={e => setLogForm(f => ({ ...f, survey_id: e.target.value }))}
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
                  <option value="">Select survey…</option>
                  {surveys.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Customer ID (UUID) *</label>
                <input type="text" value={logForm.customer_id}
                  onChange={e => setLogForm(f => ({ ...f, customer_id: e.target.value }))}
                  placeholder="UUID"
                  className="w-full border rounded px-3 py-2 text-sm font-mono focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-2">Score (0-10) *</label>
                <div className="flex gap-1.5 flex-wrap">
                  {Array.from({ length: 11 }, (_, i) => i).map(n => (
                    <button key={n} onClick={() => setLogForm(f => ({ ...f, score: String(n) }))}
                      className={`w-9 h-9 rounded-full border text-xs font-bold transition-colors ${
                        logForm.score === String(n)
                          ? "bg-blue-600 text-white border-blue-600"
                          : n <= 6 ? "bg-red-50 text-red-600 border-red-200"
                          : n <= 8 ? "bg-amber-50 text-amber-600 border-amber-200"
                          : "bg-green-50 text-green-600 border-green-200"
                      }`}>
                      {n}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Comment</label>
                <textarea value={logForm.comment}
                  onChange={e => setLogForm(f => ({ ...f, comment: e.target.value }))}
                  rows={2} placeholder="Customer feedback…"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                />
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={logResponse} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Saving…" : "Log Response"}
              </button>
              <button onClick={() => setShowLog(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
