"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  faApi, fmtCurrency, STATUS_BADGE, DEPR_METHOD_LABEL, EVENT_COLOR,
  FAAssetStatus, ScheduleStatus,
} from "@/lib/fixed_assets";

type Tab = "overview" | "schedule" | "events" | "components";

export default function FAAssetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState<Tab>("overview");
  const qc = useQueryClient();

  const { data: asset, isLoading } = useQuery({
    queryKey: ["fa-asset", id],
    queryFn: () => faApi.getAsset(id),
  });
  const { data: schedule = [] } = useQuery({
    queryKey: ["fa-schedule", id],
    queryFn: () => faApi.getSchedule(id),
    enabled: tab === "schedule",
  });
  const { data: events = [] } = useQuery({
    queryKey: ["fa-events", id],
    queryFn: () => faApi.getEvents(id),
    enabled: tab === "events",
  });
  const { data: components = [] } = useQuery({
    queryKey: ["fa-components", id],
    queryFn: () => faApi.getComponents(id),
    enabled: tab === "components",
  });

  const capitalize = useMutation({
    mutationFn: () => faApi.capitalize(id, { capitalization_date: new Date().toISOString().slice(0, 10) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fa-asset", id] }),
  });

  if (isLoading || !asset) return (
    <div className="p-6 flex items-center gap-3 text-gray-400">
      <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />Loading…
    </div>
  );

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview",   label: "Overview" },
    { key: "schedule",   label: "Depreciation Schedule" },
    { key: "events",     label: "Event History" },
    { key: "components", label: "Components" },
  ];

  const deprPct = asset.local_currency_cost > 0
    ? (asset.accumulated_depreciation / asset.local_currency_cost * 100)
    : 0;

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Link href="/dashboard/fixed-assets/assets" className="text-blue-500 text-sm hover:underline">
              ← Asset Register
            </Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{asset.asset_name}</h1>
          <p className="text-sm text-gray-500">{asset.asset_code} · {asset.category_name}</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_BADGE[asset.status]}`}>
            {asset.status}
          </span>
          {asset.status === "DRAFT" && (
            <button onClick={() => capitalize.mutate()} className="glow-button" disabled={capitalize.isPending}>
              {capitalize.isPending ? "Capitalizing…" : "Capitalize"}
            </button>
          )}
          {asset.status === "ACTIVE" && (
            <>
              <Link href={`/dashboard/fixed-assets/transfer?asset_id=${id}`} className="glow-button-secondary">Transfer</Link>
              <Link href={`/dashboard/fixed-assets/disposal?asset_id=${id}`} className="glow-button-secondary">Dispose</Link>
            </>
          )}
        </div>
      </div>

      {/* NBV progress */}
      <div className="glass-panel p-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-500">Depreciation Progress</span>
          <span className="font-medium text-orange-600">{deprPct.toFixed(1)}% depreciated</span>
        </div>
        <div className="relative h-3 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-all"
            style={{
              width: `${deprPct}%`,
              background: "linear-gradient(90deg, rgba(249,115,22,0.7), rgba(239,68,68,0.6))",
            }}
          />
        </div>
        <div className="grid grid-cols-3 mt-3 text-center text-sm">
          <div>
            <p className="text-xs text-gray-500">Gross Cost</p>
            <p className="font-semibold text-blue-600">{fmtCurrency(asset.local_currency_cost)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Accumulated Depr.</p>
            <p className="font-semibold text-orange-600">{fmtCurrency(asset.accumulated_depreciation)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Net Book Value</p>
            <p className="font-semibold text-green-600">{fmtCurrency(asset.net_book_value)}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-all ${
              tab === t.key
                ? "text-blue-600 border-b-2 border-blue-500 bg-blue-50/10"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {[
            {
              title: "Asset Details",
              rows: [
                ["Asset Code",     asset.asset_code],
                ["Asset Type",     asset.asset_type ?? "—"],
                ["Serial No.",     asset.serial_no ?? "—"],
                ["Tag No.",        asset.asset_tag_no ?? "—"],
                ["Condition",      asset.condition_status ?? "—"],
              ],
            },
            {
              title: "Financial Data",
              rows: [
                ["Original Cost",  fmtCurrency(asset.original_cost, asset.currency)],
                ["Local Cost",     fmtCurrency(asset.local_currency_cost)],
                ["Salvage Value",  fmtCurrency(asset.salvage_value)],
                ["Depr. Base",     fmtCurrency(asset.depreciable_base)],
              ],
            },
            {
              title: "Depreciation Settings",
              rows: [
                ["Method",         DEPR_METHOD_LABEL[asset.depreciation_method]],
                ["Frequency",      asset.depreciation_frequency],
                ["Useful Life",    asset.useful_life_months ? `${asset.useful_life_months} months` : "—"],
                ["Start Date",     asset.depreciation_start_date ?? "—"],
                ["End Date",       asset.depreciation_end_date ?? "—"],
                ["Last Depr. Date",asset.last_depreciation_date ?? "—"],
              ],
            },
            {
              title: "Location & Ownership",
              rows: [
                ["Location",       asset.location ?? "—"],
                ["Plant",          asset.plant ?? "—"],
                ["Department",     asset.department ?? "—"],
                ["Cost Center",    asset.cost_center ?? "—"],
              ],
            },
          ].map((section) => (
            <div key={section.title} className="liquid-glass p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{section.title}</h3>
              <dl className="space-y-2">
                {section.rows.map(([label, value]) => (
                  <div key={label} className="flex justify-between text-sm">
                    <dt className="text-gray-500">{label}</dt>
                    <dd className="font-medium text-gray-900 text-right max-w-[55%] truncate">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      )}

      {/* Depreciation Schedule */}
      {tab === "schedule" && (
        <div className="glass-table overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                {["Period","Opening NBV","Scheduled Depr.","Closing NBV","Status","Posted Date"].map(h => (
                  <th key={h} className="px-4 py-3 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {schedule.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No schedule lines. Generate schedule first.</td></tr>
              ) : schedule.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-2 text-xs font-mono">{s.period_start} → {s.period_end}</td>
                  <td className="px-4 py-2 text-right">{s.opening_nbv.toLocaleString(undefined,{maximumFractionDigits:2})}</td>
                  <td className="px-4 py-2 text-right text-orange-600 font-medium">{s.scheduled_amount.toLocaleString(undefined,{maximumFractionDigits:2})}</td>
                  <td className="px-4 py-2 text-right text-green-600">{s.closing_nbv.toLocaleString(undefined,{maximumFractionDigits:2})}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      s.schedule_status === "POSTED" ? "bg-green-100 text-green-700"
                      : s.schedule_status === "REVERSED" ? "bg-red-100 text-red-700"
                      : "bg-yellow-100 text-yellow-700"
                    }`}>{s.schedule_status}</span>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-500">{s.posting_date ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Events */}
      {tab === "events" && (
        <div className="glass-table overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                {["Date","Event","Amount","NBV Before","NBV After","Notes"].map(h => (
                  <th key={h} className="px-4 py-3 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No events recorded.</td></tr>
              ) : events.map((e) => (
                <tr key={e.id}>
                  <td className="px-4 py-2 text-xs">{e.event_date}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs font-medium ${EVENT_COLOR[e.event_type]}`}>
                      {e.event_type.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">{e.amount != null ? e.amount.toLocaleString(undefined,{maximumFractionDigits:2}) : "—"}</td>
                  <td className="px-4 py-2 text-right text-gray-500">{e.nbv_before != null ? e.nbv_before.toLocaleString(undefined,{maximumFractionDigits:2}) : "—"}</td>
                  <td className="px-4 py-2 text-right text-green-600">{e.nbv_after != null ? e.nbv_after.toLocaleString(undefined,{maximumFractionDigits:2}) : "—"}</td>
                  <td className="px-4 py-2 text-xs text-gray-500 max-w-[200px] truncate">{e.notes ?? e.reason ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Components */}
      {tab === "components" && (
        <div className="space-y-4">
          <Link href={`/dashboard/fixed-assets/assets/${id}/add-component`} className="glow-button-secondary text-sm">
            + Add Component
          </Link>
          <div className="glass-table overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  {["Component","Cost","Salvage","Useful Life","Method","NBV","Active"].map(h => (
                    <th key={h} className="px-4 py-3 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {components.length === 0 ? (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No components.</td></tr>
                ) : components.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-2 font-medium">{c.component_name}</td>
                    <td className="px-4 py-2 text-right">{c.component_cost.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right">{c.salvage_value.toLocaleString()}</td>
                    <td className="px-4 py-2">{c.useful_life_months ? `${c.useful_life_months}m` : "—"}</td>
                    <td className="px-4 py-2 text-xs">{DEPR_METHOD_LABEL[c.depreciation_method]}</td>
                    <td className="px-4 py-2 text-right font-medium text-green-600">{c.net_book_value.toLocaleString()}</td>
                    <td className="px-4 py-2">
                      <span className={`text-xs ${c.is_active ? "text-green-600" : "text-gray-400"}`}>
                        {c.is_active ? "Yes" : "No"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
