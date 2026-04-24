"use client";
import { useEffect, useState } from "react";
import { qmsApi, QMSDashboard, RISK_BG, RELEASE_BG } from "@/lib/qms";

function KPI({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color || "text-gray-800"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function QMSDashboardPage() {
  const [dash, setDash] = useState<QMSDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    qmsApi.getDashboard().then(setDash).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-gray-500">Loading QMS dashboard…</div>;
  if (!dash) return <div className="p-8 text-red-500">Failed to load dashboard</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quality Management System</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            QC checkpoints · HACCP · CCP monitoring · Deviations · Corrective actions · Release control
          </p>
        </div>
      </div>

      {/* QC Inspections */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">QC Inspections</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          <KPI label="Total" value={dash.total_inspections} />
          <KPI label="Pending" value={dash.pending_inspections}
            color={dash.pending_inspections > 0 ? "text-amber-700" : "text-gray-800"} />
          <KPI label="Passed Today" value={dash.passed_today} color="text-green-700" />
          <KPI label="Failed Today" value={dash.failed_today}
            color={dash.failed_today > 0 ? "text-red-700" : "text-gray-800"} />
          <KPI label="Conditional Today" value={dash.conditional_today}
            color={dash.conditional_today > 0 ? "text-orange-700" : "text-gray-800"} />
          <KPI label="Pass Rate (7d)" value={`${dash.pass_rate_7d}%`}
            color={dash.pass_rate_7d >= 95 ? "text-green-700" : dash.pass_rate_7d >= 80 ? "text-amber-700" : "text-red-700"} />
        </div>
      </div>

      {/* HACCP / CCP */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">HACCP & CCP</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <KPI label="Active CCPs" value={dash.active_ccps} />
          <KPI label="CCP Violations (7d)" value={dash.ccp_violations_7d}
            color={dash.ccp_violations_7d > 0 ? "text-red-700" : "text-green-700"} />
          <KPI label="Allergen Validations Pending" value={dash.allergen_validations_pending}
            color={dash.allergen_validations_pending > 0 ? "text-orange-700" : "text-gray-800"} />
        </div>
      </div>

      {/* Deviations & CAs */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Deviations & Corrective Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI label="Open Deviations" value={dash.open_deviations}
            color={dash.open_deviations > 0 ? "text-amber-700" : "text-gray-800"} />
          <KPI label="Critical Deviations" value={dash.critical_deviations}
            color={dash.critical_deviations > 0 ? "text-red-700" : "text-green-700"} />
          <KPI label="Open Corrective Actions" value={dash.open_corrective_actions}
            color={dash.open_corrective_actions > 0 ? "text-amber-700" : "text-gray-800"} />
          <KPI label="Overdue CAs" value={dash.overdue_corrective_actions}
            color={dash.overdue_corrective_actions > 0 ? "text-red-700" : "text-green-700"} />
        </div>
      </div>

      {/* Lot / Release */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Lot Quality & Release</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI label="On Hold" value={dash.lots_on_hold}
            color={dash.lots_on_hold > 0 ? "text-orange-700" : "text-gray-800"} />
          <KPI label="Quarantined" value={dash.lots_quarantined}
            color={dash.lots_quarantined > 0 ? "text-red-700" : "text-gray-800"} />
          <KPI label="Pending Release" value={dash.lots_pending_release}
            color={dash.lots_pending_release > 0 ? "text-amber-700" : "text-gray-800"} />
          <KPI label="AI Recommendations" value={dash.ai_recommendations_pending}
            color="text-indigo-700" />
        </div>
      </div>

      {/* Navigation */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 gap-3">
        {[
          { label: "QC Inspections", href: "/dashboard/qms/inspections", color: "border-blue-200 hover:bg-blue-50" },
          { label: "QC Templates", href: "/dashboard/qms/templates", color: "border-indigo-200 hover:bg-indigo-50" },
          { label: "HACCP Analysis", href: "/dashboard/qms/haccp", color: "border-teal-200 hover:bg-teal-50" },
          { label: "CCP Monitoring", href: "/dashboard/qms/ccp", color: "border-green-200 hover:bg-green-50" },
          { label: "Deviations", href: "/dashboard/qms/deviations", color: "border-orange-200 hover:bg-orange-50" },
          { label: "Corrective Actions", href: "/dashboard/qms/corrective-actions", color: "border-purple-200 hover:bg-purple-50" },
          { label: "Quarantine / Hold", href: "/dashboard/qms/quarantine", color: "border-red-200 hover:bg-red-50" },
          { label: "Allergen Validation", href: "/dashboard/qms/allergen", color: "border-yellow-200 hover:bg-yellow-50" },
          { label: "QMS Reports", href: "/dashboard/qms/reports", color: "border-gray-200 hover:bg-gray-50" },
          { label: "AI Quality Agents", href: "/dashboard/qms/ai", color: "border-violet-200 hover:bg-violet-50" },
        ].map(n => (
          <a key={n.href} href={n.href}
            className={`block border rounded-xl p-3 text-center text-sm font-medium text-gray-700 ${n.color} transition-colors`}>
            {n.label}
          </a>
        ))}
      </div>
    </div>
  );
}
