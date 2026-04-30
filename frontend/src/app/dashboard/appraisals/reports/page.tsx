"use client";
import { useEffect, useState } from "react";
import { appraisalsApi, AppraisalPeriod, RATING_COLOR } from "@/lib/appraisals";

type ReportTab = "completion" | "ratings" | "promotions";

export default function AppraisalReportsPage() {
  const [tab, setTab] = useState<ReportTab>("completion");
  const [periods, setPeriods] = useState<AppraisalPeriod[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState("");
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    appraisalsApi.listPeriods().then(setPeriods);
  }, []);

  const run = async () => {
    if (tab === "completion" && !selectedPeriod) { alert("Select a period"); return; }
    setLoading(true);
    setData(null);
    try {
      if (tab === "completion") {
        setData(await appraisalsApi.reportCompletion(selectedPeriod));
      } else if (tab === "ratings") {
        setData(await appraisalsApi.reportRatingDist(selectedPeriod || undefined));
      } else {
        setData(await appraisalsApi.reportPromotions(selectedPeriod || undefined));
      }
    } finally {
      setLoading(false);
    }
  };

  const tabs: { key: ReportTab; label: string }[] = [
    { key: "completion", label: "Completion Report" },
    { key: "ratings", label: "Rating Distribution" },
    { key: "promotions", label: "Promotion & Increment" },
  ];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Appraisal Reports</h1>

      <div className="flex gap-2 flex-wrap">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setData(null); }}
            className={`px-4 py-2 text-sm rounded font-medium ${tab === t.key ? "bg-blue-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <div className="flex gap-3 items-end flex-wrap">
          <div>
            <label className="text-xs text-gray-500">Appraisal Period {tab === "completion" ? " *" : " (optional)"}</label>
            <select
              className="block border rounded px-2 py-1 text-sm mt-1 w-64"
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
            >
              <option value="">All Periods</option>
              {periods.map((p) => <option key={p.appraisal_period_id} value={p.appraisal_period_id}>{p.period_name}</option>)}
            </select>
          </div>
          <button
            onClick={run}
            disabled={loading}
            className="rounded bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Loading…" : "Run Report"}
          </button>
        </div>

        {data && tab === "completion" && (
          <div className="space-y-3">
            {(() => {
              const d = data as { total: number; completed: number; pending: number; completion_rate_pct: number; by_status: Record<string, number> };
              return (
                <>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-blue-50 rounded p-3 text-center">
                      <p className="text-2xl font-bold text-blue-700">{d.total}</p>
                      <p className="text-xs text-gray-500">Total</p>
                    </div>
                    <div className="bg-green-50 rounded p-3 text-center">
                      <p className="text-2xl font-bold text-green-700">{d.completed}</p>
                      <p className="text-xs text-gray-500">Completed</p>
                    </div>
                    <div className="bg-yellow-50 rounded p-3 text-center">
                      <p className="text-2xl font-bold text-yellow-700">{d.completion_rate_pct}%</p>
                      <p className="text-xs text-gray-500">Completion Rate</p>
                    </div>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-2">By Status</h3>
                    <div className="space-y-1">
                      {Object.entries(d.by_status).map(([s, c]) => (
                        <div key={s} className="flex items-center gap-2">
                          <span className="text-sm text-gray-600 w-36 capitalize">{s.replace(/_/g," ")}</span>
                          <div className="flex-1 bg-gray-100 rounded-full h-3">
                            <div className="bg-blue-500 h-3 rounded-full" style={{ width: `${d.total ? (c / d.total * 100) : 0}%` }} />
                          </div>
                          <span className="text-sm font-semibold text-gray-700 w-6 text-right">{c}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              );
            })()}
          </div>
        )}

        {data && tab === "ratings" && (
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Rating Distribution</h3>
            <div className="grid grid-cols-2 gap-3">
              {(data as { rating: string; count: number }[]).map((r) => (
                <div key={r.rating} className="flex items-center gap-2 p-2 border rounded">
                  <span className={`w-3 h-3 rounded-full ${RATING_COLOR[r.rating as keyof typeof RATING_COLOR]?.replace("text-","bg-").split(" ")[0] ?? "bg-gray-400"}`} />
                  <span className="text-sm capitalize flex-1">{r.rating.replace(/_/g," ")}</span>
                  <span className="text-sm font-bold text-gray-800">{r.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {data && tab === "promotions" && (
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Promotion & Increment Recommendations</h3>
            <table className="w-full text-sm">
              <thead className="bg-gray-50"><tr>
                {["Employee","Department","Score","Rating","Increment %"].map(h=><th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>)}
              </tr></thead>
              <tbody className="divide-y">
                {(data as { employee_id: string; employee_name: string | null; department: string | null; final_score: number | null; final_rating: string | null; increment_recommendation: number | null }[]).map((r) => (
                  <tr key={r.employee_id}>
                    <td className="px-3 py-2 font-medium">{r.employee_name ?? r.employee_id}</td>
                    <td className="px-3 py-2 text-gray-600">{r.department ?? "—"}</td>
                    <td className="px-3 py-2 font-semibold">{r.final_score ?? "—"}</td>
                    <td className="px-3 py-2">
                      {r.final_rating && (
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${RATING_COLOR[r.final_rating as keyof typeof RATING_COLOR] ?? ""}`}>
                          {r.final_rating.replace(/_/g," ")}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-green-700 font-semibold">{r.increment_recommendation != null ? `${r.increment_recommendation}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(data as unknown[]).length === 0 && <p className="text-gray-400 text-sm text-center py-4">No recommendations found.</p>}
          </div>
        )}
      </div>
    </div>
  );
}
