"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

// ── Icons ─────────────────────────────────────────────────────────────────────

function IconBolt() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  );
}

function IconChartBar() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );
}

function IconBeaker() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
    </svg>
  );
}

function IconWrench() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    </svg>
  );
}

function IconShield() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  );
}

function IconCube() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  );
}

function IconLink() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
  );
}

// ── Card component ────────────────────────────────────────────────────────────

function IntegrationCard({
  icon,
  title,
  description,
  links,
  statusBadge,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  links: Array<{ label: string; href: string }>;
  statusBadge?: React.ReactNode;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 flex items-center justify-center">
            {icon}
          </div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
        </div>
        {statusBadge}
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">{description}</p>
      <div className="flex flex-wrap gap-2">
        {links.map(link => (
          <Link
            key={link.href}
            href={link.href}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <IconLink />
            {link.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

// ── Live health check panel ───────────────────────────────────────────────────

function HealthStatusPanel() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["integration-health"],
    queryFn: async () => {
      const r = await apiClient.get<{ status: string }>("/api/v1/utility-management/integration/health");
      return r.data;
    },
    refetchInterval: 60000,
    retry: 1,
  });

  const online = !isError && !isLoading && !!data;
  const offline = isError;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Live Integration Status</h3>
      <div className="flex items-center gap-3">
        {isLoading ? (
          <>
            <span className="w-3 h-3 rounded-full bg-gray-300 dark:bg-gray-600 animate-pulse" />
            <span className="text-sm text-gray-500 dark:text-gray-400">Checking Integration API…</span>
          </>
        ) : offline ? (
          <>
            <span className="w-3 h-3 rounded-full bg-red-500 flex-shrink-0" />
            <span className="text-sm font-medium text-red-600 dark:text-red-400">Integration API Offline</span>
          </>
        ) : (
          <>
            <span className="w-3 h-3 rounded-full bg-green-500 flex-shrink-0 animate-pulse" />
            <span className="text-sm font-medium text-green-600 dark:text-green-400">Integration API Online</span>
          </>
        )}
      </div>
      <p className="text-xs text-gray-400 mt-3">Auto-checks every 60 seconds.</p>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function UtilityIntegrationHubPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Link
            href="/dashboard/utility-management/kpi-center"
            className="text-sm text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
          >
            ← KPI Center
          </Link>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Utility Integration Hub</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Cross-module connectivity status — Finance, Production, Inventory, Maintenance, and Quality.
        </p>
      </div>

      {/* Live status */}
      <HealthStatusPanel />

      {/* Grid of integration sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Section 1: Finance / GL */}
        <IntegrationCard
          icon={<IconBolt />}
          title="Finance / GL Posting"
          description="Post approved utility bills to the General Ledger as journal entries. Verified bills can be posted with a debit and credit account to create double-entry journal records in the Finance module."
          links={[
            { label: "Utility Billing →", href: "/dashboard/utility-management/billing" },
            { label: "Finance →", href: "/dashboard/finance" },
          ]}
          statusBadge={
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
              GL Posting
            </span>
          }
        />

        {/* Section 2: Production */}
        <IntegrationCard
          icon={<IconChartBar />}
          title="Production Integration"
          description="Utility consumption is tracked per production order and batch via MachineConsumptionRecord and UtilityTransaction tables. Cost allocations can be posted to production costing for accurate product cost calculations."
          links={[
            { label: "Machine Utility →", href: "/dashboard/utility-management/machine-utility" },
            { label: "Production →", href: "/dashboard/production" },
          ]}
          statusBadge={
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
              Cost Tracking
            </span>
          }
        />

        {/* Section 3: Inventory / Chemical */}
        <IntegrationCard
          icon={<IconCube />}
          title="Inventory / Chemical Stock"
          description="Chemical dosing records can be synced to inventory stock movements when a material is linked. Each dosing event issued from a warehouse will generate a corresponding stock movement in the Inventory module."
          links={[
            { label: "Chemical Treatment →", href: "/dashboard/utility-management/chemical-treatment" },
            { label: "Inventory →", href: "/dashboard/inventory" },
          ]}
          statusBadge={
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
              Stock Sync
            </span>
          }
        />

        {/* Section 4: Maintenance */}
        <IntegrationCard
          icon={<IconWrench />}
          title="Maintenance Integration"
          description="Utility assets can be linked to maintenance module assets for PM schedules and breakdown tracking. Alarm events can trigger work orders or breakdown records directly from the Alarm Center."
          links={[
            { label: "Utility Assets →", href: "/dashboard/utility-management/assets" },
            { label: "Maintenance →", href: "/dashboard/maintenance" },
          ]}
          statusBadge={
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
              PM & Breakdowns
            </span>
          }
        />

        {/* Section 5: Quality */}
        <IntegrationCard
          icon={<IconBeaker />}
          title="Quality Integration"
          description="Water quality parameters (boiler chemistry, soft water hardness, wastewater compliance) can be linked to QC inspections. Compliance status and lot-level quality decisions are visible from utility assets."
          links={[
            { label: "Wastewater →", href: "/dashboard/utility-management/wastewater" },
            { label: "Quality →", href: "/dashboard/quality" },
          ]}
          statusBadge={
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300">
              QC Linkage
            </span>
          }
        />

        {/* Section 6: Alarm Center shortcut */}
        <IntegrationCard
          icon={<IconShield />}
          title="Alarm Center"
          description="Monitor real-time utility alarms and anomalies. From the Alarm Center you can acknowledge, resolve, suppress alarms, and create maintenance work orders or breakdown records directly from alarm events."
          links={[
            { label: "Alarm Center →", href: "/dashboard/utility-management/alarm-center" },
            { label: "Alarm Rules →", href: "/dashboard/utility-management/alarm-rules" },
          ]}
          statusBadge={
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300">
              Real-time
            </span>
          }
        />
      </div>
    </div>
  );
}
