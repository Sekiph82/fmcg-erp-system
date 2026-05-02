"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  securityApi, SecurityDashboard, FailedLoginEntry, AnomalyEntry,
  RISK_COLORS, EVENT_LABELS,
} from "@/lib/securityMonitor";

const RISK_ICON: Record<string, string> = {
  low: "✅", medium: "⚠️", high: "🔶", critical: "🚨",
};

function KpiBox({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm p-4 space-y-1">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest">{label}</p>
      <p className={`text-2xl font-bold ${accent ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

export default function SecurityMonitorPage() {
  const qc = useQueryClient();
  const [hours, setHours] = useState(24);
  const [unlockTarget, setUnlockTarget] = useState("");
  const [tab, setTab] = useState<"overview" | "failed" | "anomalies">("overview");

  const { data: dash, isLoading } = useQuery<SecurityDashboard>({
    queryKey: ["sec-dashboard", hours],
    queryFn: () => securityApi.dashboard(hours),
    refetchInterval: 30_000,
  });

  const { data: failedLogins = [] } = useQuery<FailedLoginEntry[]>({
    queryKey: ["sec-failed", hours],
    queryFn: () => securityApi.failedLogins(hours),
    enabled: tab === "failed",
  });

  const { data: anomalies = [] } = useQuery<AnomalyEntry[]>({
    queryKey: ["sec-anomalies"],
    queryFn: () => securityApi.anomalies(72),
    enabled: tab === "anomalies",
  });

  const unlock = useMutation({
    mutationFn: (identifier: string) => securityApi.unlock(identifier),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sec-dashboard"] });
      setUnlockTarget("");
      alert("Account unlocked.");
    },
    onError: () => alert("Unlock failed. Check permissions."),
  });

  const riskClass = RISK_COLORS[dash?.risk_level ?? "low"] ?? "";

  return (
    <div className="p-6 space-y-5 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Security Monitor</h1>
          <p className="text-sm text-gray-500">Real-time threat detection and account protection</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
          >
            {[1, 6, 24, 48, 72, 168].map((h) => (
              <option key={h} value={h}>{h}h window</option>
            ))}
          </select>
          {dash && (
            <span className={`text-sm font-semibold px-3 py-1.5 rounded-lg border ${riskClass}`}>
              {RISK_ICON[dash.risk_level]} {dash.risk_level.toUpperCase()} RISK
            </span>
          )}
        </div>
      </div>

      {isLoading && <div className="text-gray-400 text-sm">Loading security data…</div>}

      {/* KPI row */}
      {dash && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <KpiBox label="Failed Logins" value={dash.stats.failed_logins} accent="text-red-600" />
          <KpiBox label="Successful Logins" value={dash.stats.successful_logins} accent="text-green-600" />
          <KpiBox label="Attacker IPs" value={dash.stats.unique_attacker_ips} accent="text-orange-600" />
          <KpiBox label="Security Events" value={dash.stats.security_events_total} accent="text-yellow-700" />
          <KpiBox label="AI Injections" value={dash.stats.ai_injection_attempts} accent="text-purple-600" />
          <KpiBox label="Blocked Tokens" value={dash.stats.blocked_tokens_in_memory} sub="in memory" />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-100">
        {(["overview", "failed", "anomalies"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === t ? "border-red-500 text-red-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t === "overview" ? "Top IPs" : t === "failed" ? "Failed Logins" : "Anomalies"}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && dash && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-50">
              <h2 className="font-semibold text-gray-800 text-sm">Top IPs with Failed Logins</h2>
            </div>
            {dash.top_attacker_ips.length === 0 ? (
              <p className="px-4 py-8 text-center text-gray-400 text-sm">No failed login IPs in this window. ✅</p>
            ) : (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-400 uppercase border-b border-gray-50">
                    <th className="px-4 py-2 text-left">IP Address</th>
                    <th className="px-4 py-2 text-right">Failures</th>
                    <th className="px-4 py-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {dash.top_attacker_ips.map((ip) => (
                    <tr key={ip.ip}>
                      <td className="px-4 py-2.5 font-mono text-gray-700">{ip.ip}</td>
                      <td className="px-4 py-2.5 text-right">
                        <span className={`font-semibold ${ip.failures >= 10 ? "text-red-600" : ip.failures >= 5 ? "text-orange-600" : "text-gray-700"}`}>
                          {ip.failures}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <button
                          onClick={() => unlock.mutate(ip.ip)}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Unlock
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Manual unlock */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <h2 className="font-semibold text-gray-800 text-sm mb-3">Manual Account Unlock</h2>
            <div className="flex gap-2">
              <input
                value={unlockTarget}
                onChange={(e) => setUnlockTarget(e.target.value)}
                placeholder="Username or IP address"
                className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm"
              />
              <button
                onClick={() => unlockTarget && unlock.mutate(unlockTarget)}
                disabled={!unlockTarget || unlock.isPending}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {unlock.isPending ? "Unlocking…" : "Unlock"}
              </button>
            </div>
          </div>
        </div>
      )}

      {tab === "failed" && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="text-xs text-gray-400 uppercase border-b border-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">Email / Username</th>
                <th className="px-4 py-2 text-left">IP</th>
                <th className="px-4 py-2 text-left">Reason</th>
                <th className="px-4 py-2 text-right">Attempts</th>
                <th className="px-4 py-2 text-right">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {failedLogins.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No failed logins in this window.</td></tr>
              )}
              {failedLogins.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 text-gray-700">{r.actor_email ?? "—"}</td>
                  <td className="px-4 py-2.5 font-mono text-gray-500 text-xs">{r.ip_address ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs bg-red-50 text-red-700 px-1.5 py-0.5 rounded">
                      {r.reason ?? "unknown"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right font-medium">{r.failure_count ?? 1}</td>
                  <td className="px-4 py-2.5 text-right text-xs text-gray-400">
                    {r.created_at ? new Date(r.created_at).toLocaleTimeString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "anomalies" && (
        <div className="space-y-2">
          {anomalies.length === 0 && (
            <p className="text-center py-8 text-gray-400 text-sm">No anomalies detected in the last 72 hours. ✅</p>
          )}
          {anomalies.map((a) => (
            <div key={a.id} className="bg-white rounded-lg border border-orange-100 px-4 py-3 flex items-start gap-3">
              <div className="shrink-0 mt-0.5 text-orange-500 text-lg">⚠️</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-semibold text-orange-700 uppercase">
                    {EVENT_LABELS[a.event_type] ?? a.event_type}
                  </span>
                  {a.actor_email && <span className="text-xs text-gray-500">{a.actor_email}</span>}
                  {a.ip_address && <span className="text-xs font-mono text-gray-400">{a.ip_address}</span>}
                </div>
                {a.target_name && <p className="text-sm text-gray-700 mt-0.5">{a.target_name}</p>}
              </div>
              <span className="text-xs text-gray-400 shrink-0">
                {a.created_at ? new Date(a.created_at).toLocaleString() : "—"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
