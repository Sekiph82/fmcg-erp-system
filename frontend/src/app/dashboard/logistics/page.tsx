"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { logisticsApi, IntlShipmentStatus, ClearanceStatus } from "@/lib/logistics";
import { Badge } from "@/components/ui/Badge";
import { tx } from "@/lib/i18n/core";

const statusBadge = (s: IntlShipmentStatus) => {
  if (s === "DELIVERED" || s === "CUSTOMS_CLEARED") return "green";
  if (s === "CUSTOMS_HOLD") return "red";
  if (s === "IN_TRANSIT" || s === "CARGO_LOADED") return "blue";
  if (s === "ARRIVED_PORT" || s === "OUT_FOR_DELIVERY") return "yellow";
  if (s === "CANCELLED") return "gray";
  return "gray";
};

const clearanceBadge = (s?: ClearanceStatus) => {
  if (!s) return "gray";
  if (s === "CLEARED") return "green";
  if (s === "HELD") return "red";
  if (s === "DUTY_PAID") return "yellow";
  return "blue";
};

const modeBadge = (m: string) => m === "SEA" ? "blue" : m === "AIR" ? "yellow" : "gray";

function LogisticsShipmentsTab() {
  const router = useRouter();

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["logistics-dashboard"],
    queryFn: () => logisticsApi.getDashboard(),
  });

  const { data: alerts = [] } = useQuery({
    queryKey: ["logistics-eta-alerts"],
    queryFn: () => logisticsApi.getEtaAlerts(14),
  });

  const active = rows.filter((r) => !["DELIVERED", "CANCELLED"].includes(r.status));
  const inTransit = rows.filter((r) => r.status === "IN_TRANSIT" || r.status === "CARGO_LOADED");
  const atPort = rows.filter((r) => r.status === "ARRIVED_PORT" || r.status === "CUSTOMS_HOLD" || r.status === "CUSTOMS_CLEARED");
  const overdueDocs = rows.filter((r) => r.has_overdue_docs);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{tx("International Logistics")}</h1>
        <p className="text-sm text-gray-500 mt-1">{tx("Turkey → Kenya supply chain visibility")}</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: tx("Active Shipments"), value: active.length, sub: "in planning or transit", color: "text-gray-900", href: "/dashboard/logistics?tab=shipments" },
          { label: tx("In Transit"), value: inTransit.length, sub: "vessels at sea", color: "text-blue-700", href: "/dashboard/logistics?tab=shipments" },
          { label: tx("At Port / Clearing"), value: atPort.length, sub: tx("Mombasa port / customs"), color: "text-orange-600", href: "/dashboard/logistics?tab=arrivals" },
          { label: tx("Overdue Documents"), value: overdueDocs.length, sub: "draft or rejected docs", color: overdueDocs.length > 0 ? "text-red-600" : "text-gray-700", href: "/dashboard/logistics?tab=documents" },
        ].map((t) => (
          <button key={t.label} onClick={() => router.push(t.href)} className="bg-white rounded-lg border p-5 text-left hover:border-indigo-300 transition-colors">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{t.label}</p>
            <p className={`text-3xl font-bold mt-1 ${t.color}`}>{t.value}</p>
            <p className="text-xs text-gray-400 mt-1">{t.sub}</p>
          </button>
        ))}
      </div>

      {/* ETA alerts */}
      {alerts.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-sm font-semibold text-amber-800 mb-2">{alerts.length} {tx("shipment(s) arriving within 14 days")}</p>
          <div className="space-y-1">
            {alerts.map((s) => (
              <div key={s.id} className="flex items-center justify-between text-xs text-amber-700">
                <span className="font-mono font-semibold">{s.shipment_no}</span>
                <span>{s.vessel_name || s.carrier || "—"}</span>
                <span>ETA: <strong>{s.eta}</strong></span>
                <span className={s.days_to_eta != null && s.days_to_eta <= 3 ? "text-red-600 font-bold" : ""}>
                  {s.days_to_eta != null ? tx("{days_to_eta}d", { days_to_eta: s.days_to_eta }) : "—"}
                </span>
                <button className="text-indigo-600 hover:underline" onClick={() => router.push("/dashboard/logistics?tab=arrivals")}>{tx("View")}</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Shipment pipeline */}
      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">{tx("Shipment Pipeline — Turkey to Kenya")}</h2>
          <button className="text-xs text-indigo-600 hover:underline" onClick={() => router.push("/dashboard/logistics?tab=shipments")}>{tx("Manage all")}</button>
        </div>
        {isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">{tx("Loading…")}</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">{tx("Shipment")}</th>
                <th className="px-5 py-2 text-left">{tx("Mode")}</th>
                <th className="px-5 py-2 text-left">{tx("Vessel / Carrier")}</th>
                <th className="px-5 py-2 text-left">B/L</th>
                <th className="px-5 py-2 text-left">{tx("Origin Port")}</th>
                <th className="px-5 py-2 text-right">ETA</th>
                <th className="px-5 py-2 text-right">{tx("ETA (revised)")}</th>
                <th className="px-5 py-2 text-right">{tx("Days")}</th>
                <th className="px-5 py-2 text-center">{tx("Ctrs")}</th>
                <th className="px-5 py-2 text-center">{tx("POs")}</th>
                <th className="px-5 py-2 text-left">{tx("Clearance")}</th>
                <th className="px-5 py-2 text-left">{tx("Status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((r) => (
                <tr
                  key={r.shipment_id}
                  className={`hover:bg-gray-50 cursor-pointer ${r.has_overdue_docs ? "bg-red-50" : ""}`}
                  onClick={() => router.push("/dashboard/logistics?tab=shipments")}
                >
                  <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-700">{r.shipment_no}</td>
                  <td className="px-5 py-3"><Badge label={r.mode} variant={modeBadge(r.mode) as "blue" | "yellow" | "gray"} /></td>
                  <td className="px-5 py-3 text-gray-700">{r.vessel_name || r.carrier || "—"}</td>
                  <td className="px-5 py-3 font-mono text-xs">{r.bl_number || "—"}</td>
                  <td className="px-5 py-3 text-gray-500">{r.origin_port || "—"}</td>
                  <td className="px-5 py-3 text-right">{r.eta || "—"}</td>
                  <td className="px-5 py-3 text-right text-indigo-600">{r.eta_revised || "—"}</td>
                  <td className="px-5 py-3 text-right">
                    {r.days_to_eta != null ? (
                      <span className={r.days_to_eta < 0 ? "text-red-600 font-semibold" : r.days_to_eta <= 7 ? "text-orange-500 font-semibold" : "text-gray-600"}>
                        {r.days_to_eta < 0 ? tx("{days_to_eta}d late", { days_to_eta: Math.abs(r.days_to_eta) }) : tx("{days_to_eta}d", { days_to_eta: r.days_to_eta })}
                      </span>
                    ) : r.ata ? <span className="text-green-600 text-xs">{tx("Arrived")}</span> : "—"}
                  </td>
                  <td className="px-5 py-3 text-center">{r.container_count}</td>
                  <td className="px-5 py-3 text-center">{r.po_count}</td>
                  <td className="px-5 py-3">
                    {r.clearance_status ? <Badge label={r.clearance_status} variant={clearanceBadge(r.clearance_status)} /> : <span className="text-gray-400 text-xs">—</span>}
                  </td>
                  <td className="px-5 py-3"><Badge label={r.status.replace("_", " ")} variant={statusBadge(r.status)} /></td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={12} className="px-5 py-8 text-center text-gray-400">{tx("No active shipments")}</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: tx("Shipment Planning"), desc: tx("Create and manage import shipments"), href: "/dashboard/logistics?tab=shipments" },
          { label: tx("Container Tracking"), desc: tx("Track container status and seal numbers"), href: "/dashboard/logistics?tab=containers" },
          { label: tx("Customs Documents"), desc: tx("Invoice, BL, packing list, certificates"), href: "/dashboard/logistics?tab=documents" },
          { label: tx("Arrival & Clearance"), desc: tx("ETA alerts, port events, KRA clearance"), href: "/dashboard/logistics?tab=arrivals" },
        ].map((item) => (
          <button key={item.href} onClick={() => router.push(item.href)} className="bg-white rounded-lg border p-4 text-left hover:border-indigo-300 transition-colors">
            <p className="font-semibold text-sm text-gray-800">{item.label}</p>
            <p className="text-xs text-gray-500 mt-1">{item.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

const LogisticsContainersPage = dynamic(() => import("@/app/dashboard/logistics/containers/page"), { ssr: false });
const LogisticsArrivalsPage   = dynamic(() => import("@/app/dashboard/logistics/arrivals/page"),   { ssr: false });
const LogisticsDocumentsPage  = dynamic(() => import("@/app/dashboard/logistics/documents/page"),  { ssr: false });
const LogisticsShipmentsPage  = dynamic(() => import("@/app/dashboard/logistics/shipments/page"),  { ssr: false });
const FleetPage               = dynamic(() => import("@/app/dashboard/fleet/page"),                { ssr: false });

export default function LogisticsDashboardPage() {
  const tabs = [
    { key: "overview",    label: tx("Overview"),    permission: "logistics.view", content: <LogisticsShipmentsTab /> },
    { key: "shipments",   label: tx("Shipments"),   permission: "logistics.view", content: <LogisticsShipmentsPage /> },
    { key: "containers",  label: tx("Containers"),  permission: "logistics.view", content: <LogisticsContainersPage /> },
    { key: "arrivals",    label: tx("Arrivals"),    permission: "logistics.view", content: <LogisticsArrivalsPage /> },
    { key: "documents",   label: tx("Documents"),   permission: "logistics.view", content: <LogisticsDocumentsPage /> },
    { key: "fleet",       label: tx("Fleet"),       permission: "logistics.view", content: <FleetPage /> },
  ];
  return (
    <ModuleWorkspace
      title={tx("Logistics")}
      description={tx("International shipments, containers, fleet, customs clearance")}
      permission="logistics.view"
      tabs={tabs}
      defaultTab="overview"
    />
  );
}
