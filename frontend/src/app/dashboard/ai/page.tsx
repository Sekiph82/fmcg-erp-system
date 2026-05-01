"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { aiApi, AIDashboard, AIPrediction, AIRecommendation, parseAIError } from "@/lib/aiApi";

const RISK_PILL: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

const PRIORITY_PILL: Record<string, string> = {
  low: "bg-gray-100 text-gray-600",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

const TREND_ICON: Record<string, string> = {
  up: "↑",
  down: "↓",
  stable: "→",
};

function KpiCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function AIDashboardPage() {
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery<AIDashboard>({
    queryKey: ["ai-dashboard"],
    queryFn: () => aiApi.dashboard(),
    refetchInterval: 30_000,
  });

  const { data: status } = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiApi.status(),
  });

  const generatePreds = useMutation({
    mutationFn: () => aiApi.generatePredictions(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-dashboard"] }),
    onError: (err) => { const e = parseAIError(err); alert(e.message + (e.resetAt ? ` Reset at: ${new Date(e.resetAt).toLocaleTimeString()}` : "")); },
  });

  const generateRecs = useMutation({
    mutationFn: () => aiApi.generateRecommendations(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-dashboard"] }),
    onError: (err) => { const e = parseAIError(err); alert(e.message + (e.resetAt ? ` Reset at: ${new Date(e.resetAt).toLocaleTimeString()}` : "")); },
  });

  const actionRec = useMutation({
    mutationFn: (id: string) => aiApi.actionRecommendation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-dashboard"] }),
  });

  const dismissRec = useMutation({
    mutationFn: (id: string) => aiApi.dismissRecommendation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-dashboard"] }),
  });

  if (isLoading) return <div className="p-8 text-gray-500">Loading AI dashboard…</div>;
  if (error) {
    const aiErr = parseAIError(error);
    if (aiErr.status === 401) return <div className="p-8 text-yellow-600">Please log in to access AI features.</div>;
    if (aiErr.status === 403) return <div className="p-8 text-orange-600">You do not have permission to use AI features.</div>;
    return <div className="p-8 text-red-500">{aiErr.message}</div>;
  }

  const stats = data?.stats;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI & Intelligence</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Powered by{" "}
            <span className={`font-semibold ${status?.configured ? "text-green-600" : "text-yellow-600"}`}>
              {status?.provider ?? "…"} / {status?.model ?? "…"}
            </span>
            {" "}
            <span className={`text-xs px-2 py-0.5 rounded-full ${status?.mode === "llm" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
              {status?.ai_mode_label ?? status?.mode ?? ""}
            </span>
            {status?.fallback_active && (
              <span className="ml-2 text-xs text-yellow-600">⚠ Mock mode — no API key configured</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => generatePreds.mutate()}
            disabled={generatePreds.isPending}
            className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {generatePreds.isPending ? "Generating…" : "Generate Predictions"}
          </button>
          <button
            onClick={() => generateRecs.mutate()}
            disabled={generateRecs.isPending}
            className="px-4 py-2 text-sm font-medium bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {generateRecs.isPending ? "Generating…" : "Generate Recommendations"}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="Active Predictions" value={stats?.active_predictions ?? 0} sub="not archived" color="text-indigo-600" />
        <KpiCard label="Pending Recommendations" value={stats?.pending_recommendations ?? 0} sub="not actioned / dismissed" color="text-purple-600" />
        <KpiCard label="Saved Formulations" value={stats?.saved_formulations ?? 0} sub="all versions" color="text-teal-600" />
        <KpiCard label="Scenario Simulations" value={stats?.scenario_simulations ?? 0} sub="all time" color="text-orange-600" />
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          { label: "Predictions", href: "/dashboard/ai/predictions", icon: "📈" },
          { label: "Recommendations", href: "/dashboard/ai/recommendations", icon: "💡" },
          { label: "Scenario Simulator", href: "/dashboard/ai/scenarios", icon: "🎯" },
          { label: "Formulation Engine", href: "/dashboard/ai/formulations", icon: "🧪" },
          { label: "AI Logs", href: "/dashboard/ai/logs", icon: "📋" },
        ].map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="flex flex-col items-center justify-center gap-1 bg-white border border-gray-100 rounded-xl p-4 hover:border-indigo-300 hover:shadow-sm transition"
          >
            <span className="text-2xl">{l.icon}</span>
            <span className="text-xs font-medium text-gray-700">{l.label}</span>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Predictions */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
            <h2 className="font-semibold text-gray-800">Recent Predictions</h2>
            <Link href="/dashboard/ai/predictions" className="text-xs text-indigo-600 hover:underline">View all →</Link>
          </div>
          <div className="divide-y divide-gray-50">
            {data?.recent_predictions?.length === 0 && (
              <p className="px-5 py-8 text-sm text-gray-400 text-center">No predictions yet. Click "Generate Predictions" above.</p>
            )}
            {data?.recent_predictions?.map((p: AIPrediction) => (
              <div key={p.id} className="px-5 py-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {TREND_ICON[p.trend ?? ""] ?? ""} {p.subject_name ?? p.prediction_type}
                  </p>
                  <p className="text-xs text-gray-400 truncate">{p.summary?.slice(0, 80)}</p>
                </div>
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  {p.risk_level && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${RISK_PILL[p.risk_level] ?? "bg-gray-100 text-gray-600"}`}>
                      {p.risk_level}
                    </span>
                  )}
                  {p.confidence_score != null && (
                    <span className="text-xs text-gray-400">{(p.confidence_score * 100).toFixed(0)}% conf.</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Critical Recommendations */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
            <h2 className="font-semibold text-gray-800">Critical Recommendations</h2>
            <Link href="/dashboard/ai/recommendations" className="text-xs text-purple-600 hover:underline">View all →</Link>
          </div>
          <div className="divide-y divide-gray-50">
            {data?.critical_recommendations?.length === 0 && (
              <p className="px-5 py-8 text-sm text-gray-400 text-center">No critical recommendations. Click "Generate Recommendations" above.</p>
            )}
            {data?.critical_recommendations?.map((r: AIRecommendation) => (
              <div key={r.id} className="px-5 py-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_PILL[r.priority ?? ""] ?? "bg-gray-100 text-gray-600"}`}>
                      {r.priority}
                    </span>
                    <span className="text-xs text-gray-400">{r.category}</span>
                  </div>
                  <p className="text-sm font-medium text-gray-800">{r.title}</p>
                  {r.expected_impact && <p className="text-xs text-gray-400 truncate">{r.expected_impact}</p>}
                </div>
                <div className="flex gap-1 flex-shrink-0">
                  <button
                    onClick={() => actionRec.mutate(r.id)}
                    className="text-xs px-2 py-1 bg-green-50 text-green-700 rounded hover:bg-green-100"
                  >
                    Action
                  </button>
                  <button
                    onClick={() => dismissRec.mutate(r.id)}
                    className="text-xs px-2 py-1 bg-gray-50 text-gray-500 rounded hover:bg-gray-100"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
