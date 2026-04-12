"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { integrationsApi, ProviderStatus } from "@/lib/integrations";

const PROVIDER_META: Record<string, { icon: string; label: string; href: string }> = {
  MPESA: { icon: "📱", label: "M-Pesa Daraja", href: "/dashboard/integrations/mpesa" },
  CRM: { icon: "👥", label: "CRM", href: "/dashboard/integrations/sync" },
  SHOPIFY: { icon: "🛒", label: "Shopify", href: "/dashboard/integrations/sync" },
  WOOCOMMERCE: { icon: "🛍️", label: "WooCommerce", href: "/dashboard/integrations/sync" },
  BARCODE: { icon: "📷", label: "Barcode", href: "/dashboard/integrations/barcode" },
  IOT: { icon: "🏭", label: "IoT / Machines", href: "/dashboard/integrations/sync" },
  GENERIC: { icon: "🔌", label: "Generic", href: "/dashboard/integrations/logs" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, string> = {
    ACTIVE: "bg-emerald-100 text-emerald-800",
    INACTIVE: "bg-gray-100 text-gray-600",
    ERROR: "bg-red-100 text-red-800",
    TESTING: "bg-amber-100 text-amber-800",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}

function ProviderCard({ p }: { p: ProviderStatus }) {
  const meta = PROVIDER_META[p.provider] ?? { icon: "🔌", label: p.name, href: "/dashboard/integrations/logs" };
  const hasErrors = p.recent_failures > 0;

  return (
    <Link href={meta.href} className="block">
      <div className={`bg-white rounded-xl border p-4 hover:shadow-md transition-shadow ${hasErrors ? "border-red-200" : "border-gray-200"}`}>
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{meta.icon}</span>
            <div>
              <p className="font-semibold text-gray-900 text-sm">{meta.label}</p>
              <p className="text-xs text-gray-500">{p.provider}</p>
            </div>
          </div>
          <StatusBadge status={p.status} />
        </div>

        <div className="grid grid-cols-2 gap-2 mt-3">
          <div className="text-center bg-gray-50 rounded-lg p-2">
            <p className="text-lg font-bold text-gray-900">{p.recent_success}</p>
            <p className="text-xs text-gray-500">Success (24h)</p>
          </div>
          <div className={`text-center rounded-lg p-2 ${hasErrors ? "bg-red-50" : "bg-gray-50"}`}>
            <p className={`text-lg font-bold ${hasErrors ? "text-red-600" : "text-gray-900"}`}>
              {p.recent_failures}
            </p>
            <p className="text-xs text-gray-500">Errors (24h)</p>
          </div>
        </div>

        {p.last_tested_at && (
          <p className="text-xs text-gray-400 mt-2 text-right">
            Tested: {new Date(p.last_tested_at).toLocaleString()}
          </p>
        )}
      </div>
    </Link>
  );
}

export default function IntegrationsDashboardPage() {
  const { data: providers = [], isLoading, refetch } = useQuery({
    queryKey: ["integration-providers"],
    queryFn: integrationsApi.getProviders,
    refetchInterval: 60_000,
  });

  const totalErrors = providers.reduce((s, p) => s + p.recent_failures, 0);
  const totalCalls = providers.reduce((s, p) => s + p.recent_success, 0);
  const activeCount = providers.filter((p) => p.status === "ACTIVE").length;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Integration Hub</h1>
          <p className="text-gray-500 text-sm mt-0.5">All external system connections</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            ↻ Refresh
          </button>
          <Link
            href="/dashboard/integrations/logs"
            className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            View Logs
          </Link>
        </div>
      </div>

      {/* Summary bar */}
      {!isLoading && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Active Providers", value: activeCount, color: "text-emerald-600" },
            { label: "Calls (24h)", value: totalCalls, color: "text-blue-600" },
            { label: "Errors (24h)", value: totalErrors, color: totalErrors > 0 ? "text-red-600" : "text-gray-600" },
          ].map((s) => (
            <div key={s.label} className="bg-white border border-gray-200 rounded-xl p-4 text-center">
              <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Provider cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-36 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {providers.map((p) => (
            <ProviderCard key={p.provider} p={p} />
          ))}
        </div>
      )}

      {/* Quick links */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { href: "/dashboard/integrations/mpesa", icon: "📱", label: "M-Pesa Transactions" },
          { href: "/dashboard/integrations/logs", icon: "📋", label: "Integration Logs" },
          { href: "/dashboard/integrations/barcode", icon: "📷", label: "Barcode Scanner" },
          { href: "/dashboard/integrations/sync", icon: "🔄", label: "Sync Status" },
        ].map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="flex flex-col items-center gap-2 p-4 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 hover:border-indigo-300 transition-colors"
          >
            <span className="text-2xl">{link.icon}</span>
            <span className="text-xs text-gray-700 font-medium text-center">{link.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
