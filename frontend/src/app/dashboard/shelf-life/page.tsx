"use client";
import { useEffect, useState } from "react";
import {
  shelfLifeApi, ShelfLifeDashboard, ShelfLifeKPIs,
  SL_STATUS_BG, ALERT_SEV_BG, DISPOSITION_ACTION_LABEL, AI_AGENT_LABEL,
  fmtDays, expiryBgColor,
} from "@/lib/shelfLife";

function KPI({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color || "text-gray-800"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function ShelfLifeDashboardPage() {
  const [data, setData] = useState<ShelfLifeDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    shelfLifeApi.getDashboard().then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-gray-500">Loading shelf-life dashboard…</div>;
  if (!data) return <div className="p-8 text-red-500">Failed to load dashboard</div>;

  const k = data.kpis;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">FEFO + Shelf-Life Control</h1>
          <p className="text-sm text-gray-500 mt-0.5">Expiry tracking, FEFO enforcement, near-expiry monitoring</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => shelfLifeApi.generateAlerts().then(() => window.location.reload())}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Refresh Alerts
          </button>
          <button
            onClick={() => shelfLifeApi.runAIAgents().then(() => window.location.reload())}
            className="px-3 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            Run AI Agents
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-4">
        <KPI label="Lots Tracked" value={k.total_lots_tracked} />
        <KPI label="Active" value={k.active_lots} color="text-green-700" />
        <KPI label="Near Expiry" value={k.near_expiry_lots} color="text-amber-700" />
        <KPI label="Expired" value={k.expired_lots} color="text-red-700" />
        <KPI label="Blocked" value={k.blocked_lots} color="text-red-600" />
        <KPI label="Pending Retest" value={k.pending_retest_lots} color="text-blue-700" />
        <KPI label="Open Alerts" value={k.open_alerts} color={k.open_alerts > 0 ? "text-red-600" : "text-gray-700"} />
        <KPI label="Dispositions Due" value={k.pending_dispositions} color={k.pending_dispositions > 0 ? "text-amber-700" : "text-gray-700"} />
        <KPI label="FEFO Compliance" value={k.fefo_compliance_pct ? `${k.fefo_compliance_pct}%` : "—"} color="text-indigo-700" />
        <KPI label="Retest Overdue" value={data.retest_overdue} color={data.retest_overdue > 0 ? "text-orange-700" : "text-gray-700"} />
        <KPI label="Bulk Hold At Risk" value={data.bulk_hold_at_risk} color={data.bulk_hold_at_risk > 0 ? "text-amber-700" : "text-gray-700"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Critical Alerts */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h2 className="font-semibold text-gray-800 mb-3">Critical Alerts</h2>
          {data.critical_alerts.length === 0 ? (
            <p className="text-sm text-gray-400">No unresolved alerts</p>
          ) : (
            <div className="space-y-2">
              {data.critical_alerts.map((a) => (
                <div key={a.id} className={`flex items-start gap-3 p-3 rounded-lg ${ALERT_SEV_BG[a.severity]}`}>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{a.title}</p>
                    <p className="text-xs mt-0.5 opacity-80">{a.message}</p>
                  </div>
                  {a.days_remaining !== null && (
                    <span className="text-xs font-mono">{fmtDays(a.days_remaining)}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Near-Expiry Lots */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h2 className="font-semibold text-gray-800 mb-3">Near-Expiry Lots</h2>
          {data.near_expiry_lots.length === 0 ? (
            <p className="text-sm text-gray-400">No near-expiry lots</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {data.near_expiry_lots.map((p) => (
                <div key={p.id} className={`flex items-center justify-between py-2 px-2 rounded ${expiryBgColor(p.remaining_shelf_life_days)}`}>
                  <div>
                    <span className="text-xs font-mono text-gray-700">{p.lot_id.slice(0, 8)}</span>
                    <span className={`ml-2 text-xs px-1.5 py-0.5 rounded ${SL_STATUS_BG[p.shelf_life_status]}`}>
                      {p.shelf_life_status}
                    </span>
                  </div>
                  <span className="text-sm font-semibold text-amber-700">{fmtDays(p.remaining_shelf_life_days)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Disposition Suggestions */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h2 className="font-semibold text-gray-800 mb-3">Pending Dispositions</h2>
          {data.pending_dispositions.length === 0 ? (
            <p className="text-sm text-gray-400">No pending dispositions</p>
          ) : (
            <div className="space-y-2">
              {data.pending_dispositions.map((d) => (
                <div key={d.id} className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-amber-800">{DISPOSITION_ACTION_LABEL[d.action]}</p>
                    <p className="text-xs text-amber-600 mt-0.5">{d.reason}</p>
                  </div>
                  {d.urgency_score !== null && (
                    <span className="text-xs font-mono bg-amber-200 text-amber-800 px-2 py-0.5 rounded">
                      Score: {d.urgency_score}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Recommendations */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h2 className="font-semibold text-gray-800 mb-3">AI Recommendations</h2>
          {data.pending_ai_recs.length === 0 ? (
            <p className="text-sm text-gray-400">No pending AI recommendations</p>
          ) : (
            <div className="space-y-2">
              {data.pending_ai_recs.map((r) => (
                <div key={r.id} className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs bg-indigo-200 text-indigo-700 px-2 py-0.5 rounded">
                      {AI_AGENT_LABEL[r.agent_type]}
                    </span>
                    {r.confidence_score && (
                      <span className="text-xs text-gray-500">{parseFloat(r.confidence_score) * 100}% conf</span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-indigo-800">{r.title}</p>
                  <p className="text-xs text-indigo-600 mt-0.5 line-clamp-2">{r.recommendation}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Expired Lots */}
      {data.expired_lots.length > 0 && (
        <div className="bg-red-50 rounded-xl border border-red-200 p-4">
          <h2 className="font-semibold text-red-800 mb-3">Expired Lots in Active Stock ({data.expired_lots.length})</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {data.expired_lots.map((p) => (
              <div key={p.id} className="bg-red-100 border border-red-200 rounded-lg p-2">
                <p className="text-xs font-mono text-red-700">{p.lot_id.slice(0, 8)}</p>
                <p className="text-sm font-bold text-red-800">{fmtDays(p.remaining_shelf_life_days)}</p>
                <p className="text-xs text-red-600">{p.expiry_date}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Navigation */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
        {[
          { label: "FEFO Config", href: "/dashboard/shelf-life/fefo-config", color: "border-indigo-200 hover:bg-indigo-50" },
          { label: "Lot Aging", href: "/dashboard/shelf-life/lot-aging", color: "border-gray-200 hover:bg-gray-50" },
          { label: "Near-Expiry Board", href: "/dashboard/shelf-life/near-expiry", color: "border-amber-200 hover:bg-amber-50" },
          { label: "Expired Board", href: "/dashboard/shelf-life/expired", color: "border-red-200 hover:bg-red-50" },
          { label: "Retest Queue", href: "/dashboard/shelf-life/retest-queue", color: "border-blue-200 hover:bg-blue-50" },
          { label: "Shipment Validation", href: "/dashboard/shelf-life/shipment-validation", color: "border-green-200 hover:bg-green-50" },
          { label: "Production Validation", href: "/dashboard/shelf-life/production-validation", color: "border-purple-200 hover:bg-purple-50" },
          { label: "Compliance Audit", href: "/dashboard/shelf-life/compliance", color: "border-teal-200 hover:bg-teal-50" },
          { label: "Disposition Console", href: "/dashboard/shelf-life/disposition", color: "border-orange-200 hover:bg-orange-50" },
          { label: "Customer Rules", href: "/dashboard/shelf-life/customer-rules", color: "border-pink-200 hover:bg-pink-50" },
          { label: "Bulk Hold Monitor", href: "/dashboard/shelf-life/bulk-hold-monitor", color: "border-yellow-200 hover:bg-yellow-50" },
        ].map((n) => (
          <a key={n.href} href={n.href}
            className={`block border rounded-xl p-3 text-center text-sm font-medium text-gray-700 ${n.color} transition-colors`}>
            {n.label}
          </a>
        ))}
      </div>
    </div>
  );
}
