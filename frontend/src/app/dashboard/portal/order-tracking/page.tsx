"use client";
import { useEffect, useState } from "react";
import { portalApi, PortalAccount } from "@/lib/portal";

interface ERP_Order {
  id: string;
  order_no: string;
  order_date: string | null;
  status: string;
  payment_status: string;
  total_amount: number | null;
  currency: string;
  requested_delivery_date: string | null;
  created_at: string;
}

const STATUS_COLOR: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  CONFIRMED: "bg-blue-100 text-blue-700",
  ALLOCATED: "bg-indigo-100 text-indigo-700",
  PICKING: "bg-purple-100 text-purple-700",
  SHIPPED: "bg-green-100 text-green-700",
  DELIVERED: "bg-green-200 text-green-800",
  CANCELLED: "bg-red-100 text-red-600",
};

const PAYMENT_COLOR: Record<string, string> = {
  PENDING: "text-orange-600",
  PARTIAL: "text-amber-600",
  PAID: "text-green-600",
  OVERDUE: "text-red-600",
};

export default function PortalOrderTrackingPage() {
  const [accounts, setAccounts] = useState<PortalAccount[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [orders, setOrders] = useState<ERP_Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [accsLoading, setAccsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    portalApi.getAccounts({}).then((accs) => {
      setAccounts(accs as PortalAccount[]);
    }).finally(() => setAccsLoading(false));
  }, []);

  const fetchOrders = async (accountId: string) => {
    if (!accountId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`/api/v1/portal/accounts/${accountId}/sales-orders`);
      if (!r.ok) throw new Error(await r.text());
      setOrders(await r.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (id: string) => {
    setSelectedId(id);
    fetchOrders(id);
  };

  const fmtDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Order Tracking</h1>
        <p className="text-sm text-gray-500 mt-0.5">View confirmed ERP sales orders by portal account</p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Account selector */}
      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <label className="text-sm font-medium text-gray-700 block mb-2">Select Portal Account</label>
        {accsLoading ? (
          <p className="text-sm text-gray-400">Loading accounts…</p>
        ) : (
          <select
            value={selectedId}
            onChange={(e) => handleSelect(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">— Select an account —</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.primary_contact_name || a.id} ({a.account_type})
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Orders table */}
      {selectedId && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              Sales Orders
              <span className="ml-2 font-normal text-gray-400">{orders.length} records</span>
            </h2>
            <button
              onClick={() => fetchOrders(selectedId)}
              disabled={loading}
              className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
            >
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="p-6 text-sm text-gray-400 text-center">Loading orders…</div>
          ) : orders.length === 0 ? (
            <div className="p-6 text-sm text-gray-400 text-center">
              No ERP sales orders found for this account. Ensure the account has a linked customer ID.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500">
                  <tr>
                    <th className="text-left px-4 py-2">Order No</th>
                    <th className="text-left px-4 py-2">Order Date</th>
                    <th className="text-left px-4 py-2">Delivery Date</th>
                    <th className="text-left px-4 py-2">Status</th>
                    <th className="text-left px-4 py-2">Payment</th>
                    <th className="text-left px-4 py-2">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {orders.map((o) => (
                    <tr key={o.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 font-mono text-xs text-blue-600 font-medium">{o.order_no}</td>
                      <td className="px-4 py-2.5 text-gray-600">{fmtDate(o.order_date)}</td>
                      <td className="px-4 py-2.5 text-gray-500">{fmtDate(o.requested_delivery_date)}</td>
                      <td className="px-4 py-2.5">
                        <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${STATUS_COLOR[o.status] ?? "bg-gray-100 text-gray-600"}`}>
                          {o.status}
                        </span>
                      </td>
                      <td className={`px-4 py-2.5 text-xs font-medium ${PAYMENT_COLOR[o.payment_status] ?? "text-gray-500"}`}>
                        {o.payment_status}
                      </td>
                      <td className="px-4 py-2.5 text-gray-700 font-semibold">
                        {o.total_amount !== null ? `${o.currency} ${o.total_amount?.toLocaleString()}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
