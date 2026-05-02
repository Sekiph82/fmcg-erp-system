"use client";

import { useState } from "react";
import { getAccuracyReport, getVarianceReport, getCompletionReport, getVarianceAnalyzer, getCountOptimizer } from "@/lib/cycleCount";
import { Button } from "@/components/ui/Button";

export default function CycleCountReportsPage() {
  const [days, setDays] = useState(30);
  const [accuracy, setAccuracy] = useState<unknown>(null);
  const [variances, setVariances] = useState<unknown[]>([]);
  const [completion, setCompletion] = useState<unknown>(null);
  const [ai1, setAi1] = useState<unknown>(null);
  const [ai2, setAi2] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function loadAll() {
    setLoading(true);
    try {
      const [acc, var_, comp, a1, a2] = await Promise.all([
        getAccuracyReport(days),
        getVarianceReport(days),
        getCompletionReport(days),
        getVarianceAnalyzer(),
        getCountOptimizer(),
      ]);
      setAccuracy(acc); setVariances(var_ as unknown[]); setCompletion(comp);
      setAi1(a1); setAi2(a2);
    } catch {}
    setLoading(false);
  }

  type AccuracyData = { accuracy_pct?: number; total_entries?: number; accurate_entries?: number; inaccurate_entries?: number; total_variance_value?: number };
  type CompletionData = { completion_pct?: number; total_tasks?: number; by_status?: Record<string, number> };

  const acc = accuracy as AccuracyData | null;
  const comp = completion as CompletionData | null;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cycle Count Reports & AI</h1>
          <p className="text-sm text-gray-500 mt-1">Accuracy, variance, and completion analytics</p>
        </div>
        <div className="flex items-center gap-3">
          <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <Button onClick={loadAll} loading={loading}>Load Reports</Button>
        </div>
      </div>

      {acc && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { label: "Accuracy", value: `${acc.accuracy_pct}%`, color: Number(acc.accuracy_pct) >= 98 ? "text-green-700" : "text-amber-600" },
            { label: "Total Counts", value: acc.total_entries, color: "text-gray-900" },
            { label: "Accurate", value: acc.accurate_entries, color: "text-green-700" },
            { label: "Variances", value: acc.inaccurate_entries, color: "text-red-600" },
            { label: "Variance Value", value: `KES ${Number(acc.total_variance_value || 0).toLocaleString()}`, color: "text-amber-600" },
          ].map((k) => (
            <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className={`text-xl font-bold ${k.color}`}>{k.value}</div>
              <div className="text-xs text-gray-500 mt-1">{k.label}</div>
            </div>
          ))}
        </div>
      )}

      {comp && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-3 text-sm">Task Completion</h2>
          <div className="flex items-center gap-6">
            <div className="text-3xl font-bold text-indigo-700">{comp.completion_pct}%</div>
            <div className="flex gap-4 text-sm text-gray-600">
              {comp.by_status && Object.entries(comp.by_status).map(([k, v]) => (
                <span key={k} className="capitalize">{k.replace("_", " ")}: <strong>{v}</strong></span>
              ))}
            </div>
          </div>
        </div>
      )}

      {variances.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-3 text-sm">Top Variances</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {["System Qty", "Counted Qty", "Variance", "Variance %", "Value (KES)", "Root Cause"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 font-medium text-gray-700">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(variances as Array<Record<string, unknown>>).slice(0, 20).map((v, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-2">{Number(v.system_qty).toFixed(3)}</td>
                    <td className="px-3 py-2">{Number(v.counted_qty).toFixed(3)}</td>
                    <td className={`px-3 py-2 font-medium ${Number(v.variance_qty) < 0 ? "text-red-600" : "text-amber-600"}`}>
                      {Number(v.variance_qty) > 0 ? "+" : ""}{Number(v.variance_qty).toFixed(3)}
                    </td>
                    <td className="px-3 py-2">{Number(v.variance_pct).toFixed(2)}%</td>
                    <td className="px-3 py-2">{v.variance_value ? Math.abs(Number(v.variance_value)).toLocaleString() : "—"}</td>
                    <td className="px-3 py-2 text-gray-500 text-xs">{String(v.root_cause || "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!!ai1 && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-3">AI: Variance Analyzer</h2>
          <pre className="text-xs bg-gray-900 text-amber-300 rounded-lg p-4 overflow-auto max-h-64">{JSON.stringify(ai1, null, 2)}</pre>
        </div>
      )}
      {!!ai2 && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-3">AI: Count Optimizer</h2>
          <pre className="text-xs bg-gray-900 text-blue-300 rounded-lg p-4 overflow-auto max-h-64">{JSON.stringify(ai2, null, 2)}</pre>
        </div>
      )}

      {!accuracy && !loading && (
        <div className="text-center py-16 text-gray-400">Click "Load Reports" to fetch analytics and AI insights.</div>
      )}
    </div>
  );
}
