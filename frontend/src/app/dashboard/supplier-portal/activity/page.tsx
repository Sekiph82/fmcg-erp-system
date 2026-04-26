"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { spApi, SPActivityLog } from "@/lib/supplier_portal";

function ActivityContent() {
  const sp = useSearchParams();
  const accountId = sp.get("account") || "";
  const [logs, setLogs] = useState<SPActivityLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!accountId) { setLoading(false); return; }
    spApi.listActivity(accountId, 200).then(setLogs).finally(() => setLoading(false));
  }, [accountId]);

  const ACTIVITY_COLORS: Record<string, string> = {
    LOGIN: "bg-blue-100 text-blue-800",
    VIEW_PO: "bg-gray-100 text-gray-700",
    ACKNOWLEDGE_PO: "bg-green-100 text-green-800",
    PROPOSE_ETA: "bg-yellow-100 text-yellow-800",
    UPLOAD_INVOICE: "bg-purple-100 text-purple-800",
    UPLOAD_DOC: "bg-indigo-100 text-indigo-800",
    VIEW_PAYMENT: "bg-teal-100 text-teal-800",
    UPDATE_PROFILE: "bg-orange-100 text-orange-800",
    INVITE_USER: "bg-pink-100 text-pink-800",
    DEACTIVATE_USER: "bg-red-100 text-red-800",
    OTHER: "bg-gray-100 text-gray-700",
  };

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Portal Activity Log</h1>
        <p className="text-sm text-gray-500 mt-1">Full audit trail of all supplier portal actions</p>
      </div>

      {!accountId ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-800">
          Select a supplier account to view activity.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Timestamp", "Activity", "Reference", "User", "IP / Session", "Notes"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
              ) : logs.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No activity recorded yet.</td></tr>
              ) : logs.map((l) => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{new Date(l.activity_datetime).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${ACTIVITY_COLORS[l.activity_type] || "bg-gray-100 text-gray-700"}`}>
                      {l.activity_type.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{l.reference_type} {l.reference_id?.slice(0, 8)}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs font-mono">{l.user_id?.slice(0, 8) || "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{l.ip_or_session || "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">{l.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ActivityPage() {
  return <Suspense fallback={<div className="p-6 text-gray-400">Loading…</div>}><ActivityContent /></Suspense>;
}
