"use client";
import React from "react";
import Link from "next/link";
import { tx, lx } from "@/lib/i18n/core";

interface ReportCard {
  title: string;
  desc: string;
  href: string;
  color: string;
  icon: string;
}

const REPORT_GROUPS: { group: string; reports: ReportCard[] }[] = lx(() => [
  {
    group: tx("Daily Overview"),
    reports: [
      {
        title: tx("Daily Consumption"),
        desc: tx("Per-utility daily usage, cost, and trend — filterable by type, department, and shift."),
        href: "/dashboard/utility-management/reports/daily-consumption",
        color: "#fbbf24",
        icon: "⚡",
      },
      {
        title: tx("Daily Utility Summary"),
        desc: tx("Cross-utility aggregate: all utility types side-by-side with cost totals."),
        href: "/dashboard/utility-management/reports/daily-consumption?view=summary",
        color: "#60a5fa",
        icon: "📊",
      },
    ],
  },
  {
    group: tx("Equipment Efficiency"),
    reports: [
      {
        title: tx("Boiler & Steam"),
        desc: tx("Boiler efficiency %, steam generation, fuel consumption, condensate recovery, and load analysis."),
        href: "/dashboard/utility-management/reports/equipment-efficiency",
        color: "#f97316",
        icon: "🔥",
      },
      {
        title: tx("Compressor Performance"),
        desc: tx("Air output, specific energy (kWh/Nm³), leak estimation %, and night idle losses."),
        href: "/dashboard/utility-management/reports/equipment-efficiency?tab=compressor",
        color: "#22d3ee",
        icon: "💨",
      },
      {
        title: tx("Soft Water Production"),
        desc: tx("Volume treated, raw-to-soft conversion %, salt consumption, and hardness tracking."),
        href: "/dashboard/utility-management/reports/equipment-efficiency?tab=softwater",
        color: "#a78bfa",
        icon: "💧",
      },
    ],
  },
  {
    group: tx("Treatment & Renewables"),
    reports: [
      {
        title: tx("Chemical Treatment"),
        desc: tx("Dosing records by chemical and treatment area — overdose/underdose flags and cost."),
        href: "/dashboard/utility-management/reports/treatment",
        color: "#34d399",
        icon: "🧪",
      },
      {
        title: tx("Solar Generation"),
        desc: tx("PV generation vs consumption — self-consumption %, PR ratio, and grid export."),
        href: "/dashboard/utility-management/reports/treatment?tab=solar",
        color: "#facc15",
        icon: "☀️",
      },
      {
        title: tx("Wastewater Compliance"),
        desc: tx("Effluent parameters, COD/BOD removal %, pH, and compliance status per record."),
        href: "/dashboard/utility-management/reports/treatment?tab=wastewater",
        color: "#6ee7b7",
        icon: "♻️",
      },
    ],
  },
  {
    group: tx("Cost Allocation"),
    reports: [
      {
        title: tx("Cost Allocation"),
        desc: tx("Allocated utility cost grouped by department, production line, machine, product, or batch."),
        href: "/dashboard/utility-management/reports/cost-allocation",
        color: "#f43f5e",
        icon: "💰",
      },
    ],
  },
  {
    group: tx("Demand & Load Analysis"),
    reports: [
      {
        title: tx("Base Load Analysis"),
        desc: tx("Statistical distribution of daily consumption — min, P10, median, P90, max, and base load estimate."),
        href: "/dashboard/utility-management/reports/load-analysis",
        color: "#818cf8",
        icon: "📉",
      },
      {
        title: tx("Peak Demand"),
        desc: tx("Top consumption days ranked by utility type — anomaly flagging included."),
        href: "/dashboard/utility-management/reports/load-analysis?tab=peak",
        color: "#fb923c",
        icon: "📈",
      },
    ],
  },
  {
    group: tx("Anomalies & Alarms"),
    reports: [
      {
        title: tx("Alarm Trend Report"),
        desc: tx("Daily alarm counts by severity — critical, alert, warning, info — with top triggered rules."),
        href: "/dashboard/utility-management/reports/anomalies",
        color: "#ef4444",
        icon: "🔔",
      },
      {
        title: tx("Abnormal Consumption"),
        desc: tx("Deviation analysis vs 30-day baseline — flags high-deviation events per utility type."),
        href: "/dashboard/utility-management/reports/anomalies?tab=abnormal",
        color: "#f97316",
        icon: "⚠️",
      },
    ],
  },
  {
    group: tx("Sustainability"),
    reports: [
      {
        title: tx("Sustainability Summary"),
        desc: tx("Energy, water, waste, CO₂e estimate, solar %, and compliance — period overview."),
        href: "/dashboard/utility-management/reports/sustainability",
        color: "#22c55e",
        icon: "🌱",
      },
    ],
  },
]);

export default function ReportsHubPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <Link href="/dashboard/utility-management" className="text-sm text-gray-500 hover:text-blue-600">{tx("← Utility Management")}</Link>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #22c55e", paddingLeft: 12 }}>
          {tx("Utilities Reports & Analytics")}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {REPORT_GROUPS.reduce((s, g) => s + g.reports.length, 0)} {tx("reports across daily consumption, equipment efficiency, cost, anomalies, and sustainability.")}
        </p>
      </div>

      {/* Report groups */}
      {REPORT_GROUPS.map(group => (
        <section key={group.group}>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">{group.group}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {group.reports.map(r => (
              <Link
                key={r.href}
                href={r.href}
                className="group block rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{r.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 transition-colors"
                      style={{ borderLeft: `3px solid ${r.color}`, paddingLeft: 8 }}>
                      {r.title}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">{r.desc}</p>
                  </div>
                </div>
                <div className="mt-4 flex justify-end">
                  <span className="text-xs text-blue-500 group-hover:underline">{tx("Open report →")}</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
