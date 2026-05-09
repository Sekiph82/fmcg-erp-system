"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { mobileApi, MobileKpis, DeviceStats } from "@/lib/mobile_api";

export default function MobileHubPage() {
  const [kpis, setKpis] = useState<MobileKpis | null>(null);
  const [stats, setStats] = useState<DeviceStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([mobileApi.getKpis(), mobileApi.getDeviceStats()])
      .then(([k, s]) => { setKpis(k); setStats(s); })
      .finally(() => setLoading(false));
  }, []);

  const links = [
    { href: "/dashboard/mobile/approvals", label: "Approval Inbox", desc: "Approve or reject pending requests" },
    { href: "/dashboard/mobile/devices", label: "Device Manager", desc: "Manage registered push token devices" },
    { href: "/dashboard/approvals", label: "Full Approval Console", desc: "Desktop approval workflow" },
    { href: "/dashboard/notification-center", label: "Notification Center", desc: "Notification preferences & history" },
  ];

  const PLATFORM_COLOR: Record<string, string> = {
    ios: "bg-gray-100 text-gray-700",
    android: "bg-green-100 text-green-700",
    web: "bg-blue-100 text-blue-700",
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mobile Apps Support</h1>
        <p className="text-sm text-gray-500 mt-1">
          Push token management, mobile approvals, and device overview.
        </p>
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <>
          {/* KPI Strip */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Pending Approvals", value: kpis?.pending_approvals ?? 0, color: "text-orange-600" },
              { label: "Active Devices", value: kpis?.active_devices ?? 0, color: "text-blue-600" },
              { label: "Sessions (7d)", value: kpis?.active_sessions_7d ?? 0, color: "text-green-600" },
            ].map((k) => (
              <div key={k.label} className="bg-white border rounded-lg p-4 shadow-sm">
                <p className="text-xs text-gray-500">{k.label}</p>
                <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
              </div>
            ))}
          </div>

          {/* Platform breakdown */}
          {stats && (
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                Active Devices by Platform
                <span className="ml-2 font-normal text-gray-400">total: {stats.total_active_devices} / ever registered: {stats.total_registered_ever}</span>
              </h2>
              <div className="flex gap-3 flex-wrap">
                {Object.entries(stats.by_platform).map(([platform, count]) => (
                  <div key={platform} className={`rounded-full px-4 py-1.5 text-sm font-medium ${PLATFORM_COLOR[platform] ?? "bg-gray-100 text-gray-600"}`}>
                    {platform.toUpperCase()} — {count}
                  </div>
                ))}
                {Object.keys(stats.by_platform).length === 0 && (
                  <p className="text-sm text-gray-400">No active devices registered yet.</p>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Navigation links */}
      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Quick Navigation</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="flex flex-col rounded border border-blue-200 bg-blue-50 px-4 py-3 hover:bg-blue-100"
            >
              <span className="text-sm font-semibold text-blue-700">{l.label}</span>
              <span className="text-xs text-blue-500 mt-0.5">{l.desc}</span>
            </Link>
          ))}
        </div>
      </div>

      {/* Info box */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
        <p className="font-semibold mb-1">Push Notification Setup</p>
        <p>
          Register devices via the{" "}
          <code className="bg-amber-100 px-1 rounded">POST /api/v1/mobile/devices</code> endpoint from your
          native app. Supply <code className="bg-amber-100 px-1 rounded">platform</code>,{" "}
          <code className="bg-amber-100 px-1 rounded">device_id</code>, and your FCM/APNs{" "}
          <code className="bg-amber-100 px-1 rounded">token</code>. Wire FCM/APNs SDK on the server side
          to send real push notifications via{" "}
          <code className="bg-amber-100 px-1 rounded">POST /api/v1/mobile/push/send</code>.
        </p>
      </div>
    </div>
  );
}
