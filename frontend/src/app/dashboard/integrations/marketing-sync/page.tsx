"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { integrationsApi, MarketingProviderSyncRow } from "@/lib/integrations";

const PROVIDER_META: Record<string, { label: string; description: string; color: string }> = {
  META_ADS:            { label: "Meta Ads",           description: "Facebook & Instagram ad performance sync",    color: "text-blue-400" },
  GOOGLE_ADS:          { label: "Google Ads",          description: "Google Ads + Analytics performance sync",     color: "text-yellow-400" },
  TIKTOK_ADS:          { label: "TikTok Ads",          description: "TikTok for Business ad performance sync",     color: "text-pink-400" },
  SOCIAL_ANALYTICS:    { label: "Social Analytics",    description: "Social listening & engagement analytics",     color: "text-violet-400" },
  ECOMMERCE_ANALYTICS: { label: "E-com Analytics",     description: "Store performance & conversion analytics",    color: "text-teal-400" },
  CRM:                 { label: "CRM Sync",            description: "Customer profile & segment sync",             color: "text-indigo-400" },
  SHOPIFY:             { label: "Shopify",             description: "Shopify orders & inventory sync",             color: "text-emerald-400" },
  WOOCOMMERCE:         { label: "WooCommerce",         description: "WooCommerce orders & inventory sync",         color: "text-orange-400" },
};

const STATUS_CLS: Record<string, string> = {
  SUCCESS:        "text-emerald-400",
  PENDING:        "text-yellow-400",
  FAILED:         "text-red-400",
  NOT_CONFIGURED: "text-slate-500",
};

export default function MarketingSyncPage() {
  const qc = useQueryClient();
  const [syncingProvider, setSyncingProvider] = useState<string | null>(null);

  const { data: statuses = [], isLoading } = useQuery<MarketingProviderSyncRow[]>({
    queryKey: ["marketing-sync-status"],
    queryFn: () => integrationsApi.getMarketingSyncStatus(),
    refetchInterval: 30_000,
  });

  const adsMut = useMutation({
    mutationFn: (provider: string) => integrationsApi.triggerAdsSync(provider),
    onMutate: (p) => setSyncingProvider(p),
    onSettled: () => {
      setSyncingProvider(null);
      qc.invalidateQueries({ queryKey: ["marketing-sync-status"] });
    },
  });

  const socialMut = useMutation({
    mutationFn: (provider: string) => integrationsApi.triggerSocialSync(provider),
    onMutate: (p) => setSyncingProvider(p),
    onSettled: () => {
      setSyncingProvider(null);
      qc.invalidateQueries({ queryKey: ["marketing-sync-status"] });
    },
  });

  const ecommMut = useMutation({
    mutationFn: (provider: string) => integrationsApi.triggerEcommerceSync(provider),
    onMutate: (p) => setSyncingProvider(p),
    onSettled: () => {
      setSyncingProvider(null);
      qc.invalidateQueries({ queryKey: ["marketing-sync-status"] });
    },
  });

  function triggerSync(provider: string) {
    const ads = ["META_ADS", "GOOGLE_ADS", "TIKTOK_ADS"];
    const social = ["SOCIAL_ANALYTICS", "ECOMMERCE_ANALYTICS"];
    const ecomm = ["SHOPIFY", "WOOCOMMERCE", "CRM"];
    if (ads.includes(provider)) adsMut.mutate(provider);
    else if (social.includes(provider)) socialMut.mutate(provider);
    else ecommMut.mutate(provider);
  }

  const statusMap = Object.fromEntries(statuses.map((s) => [s.provider, s]));

  return (
    <div className="min-h-screen bg-[#0b1120] p-6 text-white">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Marketing Sync</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Placeholder sync hooks for ad platforms, social analytics, and e-commerce channels.
          Configure credentials in Integration Config to activate live syncs.
        </p>
      </div>

      <div className="mb-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-400">
        All syncs are queued as placeholders until API credentials are configured in the Integration Config screen.
        Once connected, these will pull real data into the ERP marketing module.
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-slate-800/50" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(PROVIDER_META).map(([provider, meta]) => {
            const syncStatus = statusMap[provider];
            const isSyncing = syncingProvider === provider;

            return (
              <div
                key={provider}
                className="rounded-xl border border-slate-700/50 bg-[#131c2e] p-5"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className={`text-sm font-semibold ${meta.color}`}>{meta.label}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{meta.description}</p>
                  </div>
                  <span className={`text-[10px] font-medium uppercase tracking-wider ${STATUS_CLS[syncStatus?.status ?? "NOT_CONFIGURED"]}`}>
                    {syncStatus?.status ?? "NOT_CONFIGURED"}
                  </span>
                </div>

                {syncStatus?.last_sync && (
                  <p className="text-[11px] text-slate-500 mb-2">
                    Last sync: {syncStatus.last_sync.slice(0, 16)}
                  </p>
                )}
                {syncStatus?.error && (
                  <p className="text-[11px] text-red-400 mb-2 truncate">{syncStatus.error}</p>
                )}

                <button
                  onClick={() => triggerSync(provider)}
                  disabled={isSyncing}
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-800/50 py-1.5 text-xs font-medium text-slate-300 hover:border-slate-600 hover:bg-slate-800 disabled:opacity-40 transition-colors"
                >
                  {isSyncing ? "Queuing…" : "Trigger Sync"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
