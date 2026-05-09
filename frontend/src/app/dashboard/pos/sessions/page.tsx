"use client";

import { useQuery } from "@tanstack/react-query";
import { posApi, POSSession, POSSessionStatus, fmtKES } from "@/lib/pos";

function fmtDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleString("en-KE", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function StatusBadge({ s }: { s: POSSessionStatus }) {
  return s === "OPEN"
    ? <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-700">OPEN</span>
    : <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">CLOSED</span>;
}

export default function POSSessionsPage() {
  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ["pos-sessions"],
    queryFn: () => posApi.listSessions(),
  });

  const open   = sessions.filter(s => s.status === "OPEN").length;
  const closed = sessions.filter(s => s.status === "CLOSED").length;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">POS Sessions</h1>
        <p className="text-sm text-gray-500">Register open/close history</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500 font-medium">Total Sessions</div>
          <div className="text-2xl font-bold text-gray-900">{sessions.length}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500 font-medium">Open</div>
          <div className="text-2xl font-bold text-green-600">{open}</div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="text-xs text-gray-500 font-medium">Closed</div>
          <div className="text-2xl font-bold text-gray-600">{closed}</div>
        </div>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Loading sessions…</div>
        ) : sessions.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No sessions recorded.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {["Session #", "Register", "Cashier", "Status", "Opening Float", "Total Sales", "Transactions", "Opened", "Closed"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sessions.map(s => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono font-medium text-gray-900">{s.session_no}</td>
                    <td className="px-4 py-3 text-gray-700">{s.register_id}</td>
                    <td className="px-4 py-3 text-gray-700">{s.cashier_name ?? "—"}</td>
                    <td className="px-4 py-3"><StatusBadge s={s.status} /></td>
                    <td className="px-4 py-3">{fmtKES(s.opening_float)}</td>
                    <td className="px-4 py-3 font-semibold">{fmtKES(s.total_sales)}</td>
                    <td className="px-4 py-3">{s.total_transactions}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{fmtDate(s.opened_at)}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{fmtDate(s.closed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
