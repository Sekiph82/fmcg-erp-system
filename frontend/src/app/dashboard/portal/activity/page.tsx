"use client";
import { useEffect, useState } from "react";
import { portalApi, PortalActivityLog } from "@/lib/portal";

const ACTIVITY_COLORS: Record<string, string> = {
  LOGIN: "#3B82F6",
  SUBMIT_ORDER: "#8B5CF6",
  DOWNLOAD_INVOICE: "#F59E0B",
  SUBMIT_CLAIM: "#EF4444",
  VIEW_ORDER: "#6B7280",
  INITIATE_PAYMENT: "#10B981",
  DOWNLOAD_STATEMENT: "#0EA5E9",
  VIEW_SHIPMENT: "#6B7280",
  OTHER: "#6B7280",
};

export default function PortalActivityPage() {
  const [accounts, setAccounts] = useState<{ id: string; account_code: string }[]>([]);
  const [selectedAccount, setSelectedAccount] = useState("");
  const [logs, setLogs] = useState<PortalActivityLog[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    portalApi.getAccounts().then(a => setAccounts(a as { id: string; account_code: string }[])).catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedAccount) return;
    setLoading(true);
    portalApi.getActivity(selectedAccount, 200)
      .then(d => setLogs(d as PortalActivityLog[]))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedAccount]);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Portal Activity Log</h1>
        <select value={selectedAccount} onChange={e => setSelectedAccount(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">Select Account…</option>
          {accounts.map(a => <option key={a.id} value={a.id}>{a.account_code}</option>)}
        </select>
      </div>

      {!selectedAccount && (
        <div className="bg-gray-50 rounded-xl border-2 border-dashed p-8 text-center text-gray-400 text-sm">
          Select a portal account to view activity
        </div>
      )}

      {selectedAccount && (
        <div className="space-y-2">
          {loading && <div className="text-gray-400 text-sm py-4">Loading…</div>}
          {!loading && logs.length === 0 && <div className="text-gray-400 text-sm py-4">No activity logged</div>}
          {logs.map(log => (
            <div key={log.id} className="bg-white rounded-xl border shadow-sm p-3 flex items-start gap-3">
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                style={{ background: ACTIVITY_COLORS[log.activity_type] || "#6B7280" }}>
                {log.activity_type.slice(0, 2)}
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-800">{log.activity_type.replace(/_/g, " ")}</div>
                <div className="text-xs text-gray-400 mt-0.5">
                  {new Date(log.activity_datetime).toLocaleString()}
                  {log.reference_type && ` · ${log.reference_type}: ${log.reference_id}`}
                </div>
                {log.notes && <p className="text-xs text-gray-500 mt-0.5">{log.notes}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
