"use client";
import React from "react";
import Link from "next/link";

interface ReportCard {
  title: string;
  desc: string;
  href: string;
  color: string;
  icon: string;
}

const REPORT_GROUPS: { group: string; reports: ReportCard[] }[] = [
  {
    group: "Daily Overview",
    reports: [
      {
        title: "Daily Consumption",
        desc: "Per-utility daily usage, cost, and trend — filterable by type, department, and shift.",
        href: "/dashboard/utility-management/reports/daily-consumption",
        color: "#fbbf24",
        icon: "⚡",
      },
      {
        title: "Daily Utility Summary",
        desc: "Cross-utility aggregate: all utility types side-by-side with cost totals.",
        href: "/dashboard/utility-management/reports/daily-consumption?view=summary",
        color: "#60a5fa",
        icon: "📊",
      },
    ],
  },
  {
    group: "Equipment Efficiency",
    reports: [
      {
        title: "Boiler & Steam",
        desc: "Boiler efficiency %, steam generation, fuel consumption, condensate recovery, and load analysis.",
        href: "/dashboard/utility-management/reports/equipment-efficiency",
        color: "#f97316",
        icon: "🔥",
      },
      {
        title: "Compressor Performance",
        desc: "Air output, specific energy (kWh/Nm³), leak estimation %, and night idle losses.",
        href: "/dashboard/utility-management/reports/equipment-efficiency?tab=compressor",
        color: "#22d3ee",
        icon: "💨",
      },
      {
        title: "Soft Water Production",
        desc: "Volume treated, raw-to-soft conversion %, salt consumption, and hardness tracking.",
        href: "/dashboard/utility-management/reports/equipment-efficiency?tab=softwater",
        color: "#a78bfa",
        icon: "💧",
      },
    ],
  },
  {
    group: "Treatment & Renewables",
    reports: [
      {
        title: "Chemical Treatment",
        desc: "Dosing records by chemical and treatment area — overdose/underdose flags and cost.",
        href: "/dashboard/utility-management/reports/treatment",
        color: "#34d399",
        icon: "🧪",
      },
      {
        title: "Solar Generation",
        desc: "PV generation vs consumption — self-consumption %, PR ratio, and grid export.",
        href: "/dashboard/utility-management/reports/treatment?tab=solar",
        color: "#facc15",
        icon: "☀️",
      },
      {
        title: "Wastewater Compliance",
        desc: "Effluent parameters, COD/BOD removal %, pH, and compliance status per record.",
        href: "/dashboard/utility-management/reports/treatment?tab=wastewater",
        color: "#6ee7b7",
        icon: "♻️",
      },
    ],
  },
  {
    group: "Cost Allocation",
    reports: [
      {
        title: "Cost Allocation",
        desc: "Allocated utility cost grouped by department, production line, machine, product, or batch.",
        href: "/dashboard/utility-management/reports/cost-allocation",
        color: "#f43f5e",
        icon: "💰",
      },
    ],
  },
  {
    group: "Demand & Load Analysis",
    reports: [
      {
        title: "Base Load Analysis",
        desc: "Statistical distribution of daily consumption — min, P10, median, P90, max, and base load estimate.",
        href: "/dashboard/utility-management/reports/load-analysis",
        color: "#818cf8",
        icon: "📉",
      },
      {
        title: "Peak Demand",
        desc: "Top consumption days ranked by utility type — anomaly flagging included.",
        href: "/dashboard/utility-management/reports/load-analysis?tab=peak",
        color: "#fb923c",
        icon: "📈",
      },
    ],
  },
  {
    group: "Anomalies & Alarms",
    reports: [
      {
        title: "Alarm Trend Report",
        desc: "Daily alarm counts by severity — critical, alert, warning, info — with top triggered rules.",
        href: "/dashboard/utility-management/reports/anomalies",
        color: "#ef4444",
        icon: "🔔",
      },
      {
        title: "Abnormal Consumption",
        desc: "Deviation analysis vs 30-day baseline — flags high-deviation events per utility type.",
        href: "/dashboard/utility-management/reports/anomalies?tab=abnormal",
        color: "#f97316",
        icon: "⚠️",
      },
    ],
  },
  {
    group: "Sustainability",
    reports: [
      {
        title: "Sustainability Summary",
        desc: "Energy, water, waste, CO₂e estimate, solar %, and compliance — period overview.",
        href: "/dashboard/utility-management/reports/sustainability",
        color: "#22c55e",
        icon: "🌱",
      },
    ],
  },
];

export default function ReportsHubPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <Link href="/dashboard/utility-management" className="text-sm text-gray-500 hover:text-blue-600">← Utility Management</Link>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #22c55e", paddingLeft: 12 }}>
          Utilities Reports & Analytics
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {REPORT_GROUPS.reduce((s, g) => s + g.reports.length, 0)} reports across daily consumption, equipment efficiency, cost, anomalies, and sustainability.
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
                  <span className="text-xs text-blue-500 group-hover:underline">Open report →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
