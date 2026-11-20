"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { dashboardApi } from "@/lib/dashboard";
import { KPICard } from "@/components/dashboard/KPICard";
import { AlertsPanel } from "@/components/dashboard/AlertsPanel";
import { MpesaSection } from "@/components/dashboard/MpesaSection";
import { SectionCard, StatusPill } from "@/components/dashboard/SectionCard";
import { Sparkline } from "@/components/dashboard/Sparkline";

function fmt(n: number, decimals = 0) {
  return n.toLocaleString(undefined, { maximumFractionDigits: decimals });
}

function fmtKES(n: number) {
  if (n >= 1_000_000) return `KES ${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `KES ${(n / 1_000).toFixed(0)}K`;
  return `KES ${fmt(n)}`;
}

export default function DashboardPage() {
  const { user, getFirstAllowedRoute, hasExactPermission } = useAuth();
  const router = useRouter();

  const { data, isLoading, dataUpdatedAt, refetch } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: dashboardApi.getSummary,
    refetchInterval: 60_000, // auto-refresh every 60s
    staleTime: 30_000,
  });

  const { data: work, isFetched: workFetched } = useQuery({
    queryKey: ["my-work"], queryFn: dashboardApi.myWork, refetchInterval: 60_000, staleTime: 30_000,
  });

  const p = data?.production;
  const inv = data?.inventory;
  const s = data?.sales;
  const m = data?.mpesa;
  const log = data?.logistics;
  const alerts = data?.alerts ?? [];

  const criticalAlerts = alerts.filter((a) => a.severity === "critical").length;

  // Sections the caller lacks permission for come back null from the API (role-gated summary).
  const show = (section: unknown) => isLoading || !!section;
  const noCompanyView = !!data && !p && !inv && !s && !m && !log;
  useEffect(() => {
    // no company figures and nothing waiting here: open the user's own first screen instead
    if (!noCompanyView || !user || !workFetched || (work?.length ?? 0) > 0) return;
    const shopFloor = user.permission_codes.some((code) => code.startsWith("shop_floor."));
    const target = shopFloor ? "/dashboard/shop-floor/terminal" : getFirstAllowedRoute();
    if (target !== "/dashboard") router.replace(target);
  }, [noCompanyView, user, router, getFirstAllowedRoute, workFetched, work]);

  const lastRefresh = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div className="w-full min-w-0 px-4 sm:px-6 lg:px-8 space-y-5 pb-10">
      {hasExactPermission("integrations.provider_keys") && <ProviderKeysReminder />}
      {/* ── Header ── */}
      <div className="flex items-center justify-between pt-1">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Executive Dashboard</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            {user?.full_name} · {lastRefresh ? `Updated ${lastRefresh}` : "Loading…"}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="p-2 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          title="Refresh"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* ── My work today: only the queues this user can act on ── */}
      {!!work?.length && (
        <section aria-label="My work today" data-testid="my-work" className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4">
          <h2 className="text-sm font-semibold text-indigo-900 mb-2">My work today</h2>
          <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {work.map((w) => (
              <li key={w.key}>
                <Link href={w.href} className="flex items-center justify-between gap-3 rounded-lg bg-white border px-3 py-2 hover:border-indigo-400">
                  <span className="text-sm text-gray-800">{w.label}</span>
                  <span className="min-w-8 text-center rounded-full bg-indigo-600 px-2 py-0.5 text-sm font-semibold text-white">{w.count}</span>
                </Link>
              </li>))}
          </ul>
        </section>)}

      {/* ── Alerts banner ── */}
      {criticalAlerts > 0 && (
        <div className="flex items-center gap-3 rounded-xl bg-red-600 px-4 py-3 text-white shadow">
          <span className="text-2xl">🚨</span>
          <div className="flex-1">
            <p className="font-bold text-sm">{criticalAlerts} Critical Alert{criticalAlerts > 1 ? "s" : ""}</p>
            <p className="text-xs text-red-100">Immediate attention required</p>
          </div>
          <span className="text-2xl font-bold">{criticalAlerts}</span>
        </div>
      )}

      {/* ── KPI Cards (2-col swipeable grid) ── */}
      <div>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Today&apos;s KPIs</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">

          {show(p) && (
          <KPICard
            label="Active Production"
            value={isLoading ? "—" : fmt(p?.active_orders ?? 0)}
            subtext={p ? `${fmt(p.today_actual_qty, 0)} / ${fmt(p.today_planned_qty, 0)} kg today` : undefined}
            status={
              !p ? "ok"
              : p.completion_rate >= 80 ? "ok"
              : p.completion_rate >= 50 ? "warning"
              : "critical"
            }
            trend={p?.trend_7d}
            trendColor="#6366f1"
            href="/dashboard/production/orders"
            loading={isLoading}
          />
          )}

          {show(p) && (
          <KPICard
            label="Machines Down"
            value={isLoading ? "—" : fmt(p?.machines_down ?? 0)}
            subtext={p ? `${p.open_breakdowns} open breakdown(s)` : undefined}
            status={
              !p ? "ok"
              : p.machines_down === 0 ? "ok"
              : p.machines_down <= 2 ? "warning"
              : "critical"
            }
            href="/dashboard/maintenance/breakdowns"
            loading={isLoading}
          />
          )}

          {show(inv) && (
          <KPICard
            label="Stock Value"
            value={isLoading ? "—" : fmtKES(inv?.total_stock_value ?? 0)}
            subtext={inv ? `${fmt(inv.total_sku_count)} SKUs tracked` : undefined}
            status="ok"
            href="/dashboard/inventory"
            loading={isLoading}
          />
          )}

          {show(inv) && (
          <KPICard
            label="Low Stock"
            value={isLoading ? "—" : fmt(inv?.critical_low_stock_count ?? 0)}
            subtext="items at/below reorder"
            status={
              !inv ? "ok"
              : inv.critical_low_stock_count === 0 ? "ok"
              : inv.critical_low_stock_count <= 3 ? "warning"
              : "critical"
            }
            href="/dashboard/inventory"
            loading={isLoading}
          />
          )}

          {show(s) && (
          <KPICard
            label="Today's Sales"
            value={isLoading ? "—" : fmtKES(s?.today_invoices_amount ?? 0)}
            subtext={s ? `${fmt(s.today_orders_count)} orders` : undefined}
            status="ok"
            trend={s?.trend_7d}
            trendColor="#10b981"
            href="/dashboard/sales/invoices"
            loading={isLoading}
          />
          )}

          {show(s) && (
          <KPICard
            label="Pending Payments"
            value={isLoading ? "—" : fmtKES(s?.pending_payments_amount ?? 0)}
            subtext={s ? `${fmt(s.overdue_invoices_count)} overdue` : undefined}
            status={
              !s ? "ok"
              : s.overdue_invoices_count === 0 ? "ok"
              : s.overdue_invoices_count <= 3 ? "warning"
              : "critical"
            }
            href="/dashboard/sales/invoices"
            loading={isLoading}
          />
          )}

          {show(m) && (
          <KPICard
            label="M-Pesa Today"
            value={isLoading ? "—" : fmtKES(m?.today_collected ?? 0)}
            subtext={m ? `${m.success_rate.toFixed(0)}% success rate` : undefined}
            status={
              !m ? "ok"
              : m.success_rate >= 90 ? "ok"
              : m.success_rate >= 70 ? "warning"
              : "critical"
            }
            href="/dashboard/finance/mpesa"
            loading={isLoading}
          />
          )}

          {show(log) && (
          <KPICard
            label="Shipments"
            value={isLoading ? "—" : fmt((log?.in_transit ?? 0) + (log?.arrived_port ?? 0))}
            subtext={
              log
                ? log.customs_hold > 0
                  ? `⚠️ ${log.customs_hold} on customs hold`
                  : log.delayed_count > 0
                  ? `${log.delayed_count} delayed`
                  : `${log.arrivals_this_week} arriving this week`
                : undefined
            }
            status={
              !log ? "ok"
              : log.customs_hold > 0 ? "critical"
              : log.delayed_count > 0 ? "warning"
              : "ok"
            }
            href="/dashboard/logistics/shipments"
            loading={isLoading}
          />
          )}
        </div>
      </div>

      {/* ── Alerts ── */}
      <SectionCard
        title="Active Alerts"
        icon="🔔"
        badge={
          alerts.length > 0 ? (
            <span className="text-xs font-bold bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
              {alerts.length}
            </span>
          ) : undefined
        }
      >
        <AlertsPanel alerts={alerts} />
      </SectionCard>

      {/* ── Production Section ── */}
      {show(p) && (
      <SectionCard title="Production" icon="⚙️">
        {p ? (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <StatusPill
                value={fmt(p.active_orders)}
                label="Active Orders"
                status={p.active_orders > 0 ? "ok" : "neutral"}
              />
              <StatusPill
                value={`${p.completion_rate.toFixed(0)}%`}
                label="Today Rate"
                status={p.completion_rate >= 80 ? "ok" : p.completion_rate >= 50 ? "warning" : "critical"}
              />
              <StatusPill
                value={fmt(p.machines_down)}
                label="Machines Down"
                status={p.machines_down === 0 ? "ok" : p.machines_down <= 2 ? "warning" : "critical"}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-gray-500 mt-1">
              <span>7-day production trend</span>
              <span>{fmt(p.today_actual_qty, 0)} / {fmt(p.today_planned_qty, 0)} kg today</span>
            </div>
            <Sparkline data={p.trend_7d} color="#6366f1" height={40} width={280} />
          </div>
        ) : (
          <div className="h-16 bg-gray-50 rounded-lg animate-pulse" />
        )}
      </SectionCard>
      )}

      {/* ── Inventory Section ── */}
      {show(inv) && (
      <SectionCard title="Inventory" icon="📦">
        {inv ? (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <StatusPill
                value={fmtKES(inv.total_stock_value)}
                label="Stock Value"
                status="neutral"
              />
              <StatusPill
                value={fmt(inv.total_sku_count)}
                label="SKUs"
                status="neutral"
              />
              <StatusPill
                value={fmt(inv.critical_low_stock_count)}
                label="Low Stock"
                status={inv.critical_low_stock_count === 0 ? "ok" : inv.critical_low_stock_count <= 3 ? "warning" : "critical"}
              />
            </div>
            {inv.low_stock_items.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-1.5">Critical Items</p>
                <div className="space-y-1">
                  {inv.low_stock_items.slice(0, 5).map((item) => (
                    <div key={item.id} className="flex items-center justify-between text-xs rounded bg-red-50 px-2 py-1.5">
                      <span className="font-medium text-gray-800 truncate flex-1">{item.name}</span>
                      <span className="text-red-600 font-bold shrink-0 ml-2">
                        {fmt(item.quantity_on_hand, 1)} {item.uom}
                      </span>
                      <span className="text-gray-400 shrink-0 ml-1">/ {fmt(item.reorder_point, 0)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-16 bg-gray-50 rounded-lg animate-pulse" />
        )}
      </SectionCard>
      )}

      {/* ── Sales Section ── */}
      {show(s) && (
      <SectionCard title="Sales" icon="📊">
        {s ? (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <StatusPill
                value={fmtKES(s.today_invoices_amount)}
                label="Today Revenue"
                status="ok"
              />
              <StatusPill
                value={fmt(s.overdue_invoices_count)}
                label="Overdue"
                status={s.overdue_invoices_count === 0 ? "ok" : s.overdue_invoices_count <= 2 ? "warning" : "critical"}
              />
              <StatusPill
                value={fmt(s.pending_shipments_count)}
                label="Pending Ships"
                status={s.pending_shipments_count > 10 ? "warning" : "neutral"}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>7-day revenue trend</span>
              <span>Pending: {fmtKES(s.pending_payments_amount)}</span>
            </div>
            <Sparkline data={s.trend_7d} color="#10b981" height={40} width={280} />
          </div>
        ) : (
          <div className="h-16 bg-gray-50 rounded-lg animate-pulse" />
        )}
      </SectionCard>
      )}

      {/* ── Finance / M-Pesa Section ── */}
      {show(m) && (
      <SectionCard title="M-Pesa Collections" icon="💚">
        {m ? (
          <MpesaSection data={m} />
        ) : (
          <div className="h-24 bg-gray-50 rounded-lg animate-pulse" />
        )}
      </SectionCard>
      )}

      {/* ── Logistics Section ── */}
      {show(log) && (
      <SectionCard title="Logistics (TR → KE)" icon="🚢">
        {log ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <StatusPill
                value={fmt(log.in_transit)}
                label="In Transit"
                status="neutral"
              />
              <StatusPill
                value={fmt(log.arrived_port)}
                label="At Port"
                status={log.arrived_port > 0 ? "ok" : "neutral"}
              />
              <StatusPill
                value={fmt(log.customs_hold)}
                label="Customs Hold"
                status={log.customs_hold === 0 ? "ok" : "critical"}
              />
              <StatusPill
                value={fmt(log.delayed_count)}
                label="Delayed"
                status={log.delayed_count === 0 ? "ok" : "warning"}
              />
            </div>
            {log.arrivals_this_week > 0 && (
              <div className="flex items-center gap-2 rounded-lg bg-blue-50 border border-blue-100 px-3 py-2">
                <span className="text-lg">📅</span>
                <p className="text-sm text-blue-700 font-medium">
                  {log.arrivals_this_week} shipment{log.arrivals_this_week > 1 ? "s" : ""} expected this week
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="h-16 bg-gray-50 rounded-lg animate-pulse" />
        )}
      </SectionCard>
      )}

      {/* ── Footer ── */}
      <p className="text-center text-[11px] text-gray-300 pb-2">
        Auto-refreshes every 60 seconds · Role: {user?.is_superuser ? "CEO / Admin" : "Manager"}
      </p>
    </div>
  );
}


/** Administrator reminder: providers still waiting for keys (M-Pesa, SMS, WhatsApp, e-mail). */
function ProviderKeysReminder() {
  const { data = [] } = useQuery<{ provider: string; label: string; configured: boolean }[]>({
    queryKey: ["provider-credentials"],
    queryFn: async () => (await (await import("@/lib/api")).apiClient.get("/api/v1/integrations/provider-credentials")).data,
    staleTime: 300_000,
  });
  const waiting = data.filter((p) => !p.configured);
  if (waiting.length === 0) return null;
  return (
    <div role="status" className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 flex flex-wrap items-center gap-2">
      <span>Waiting for provider keys: {waiting.map((p) => p.label.split(" (")[0]).join(", ")}.</span>
      <Link href="/dashboard/integrations?tab=provider-keys" className="font-medium underline">Enter keys</Link>
    </div>
  );
}
