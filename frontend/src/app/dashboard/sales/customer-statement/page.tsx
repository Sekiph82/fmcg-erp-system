"use client";
import { useState } from "react";
import {
  salesApi, CustomerStatement, Customer,
  StatementInvoiceRow,
} from "@/lib/sales";

const BUCKET_COLORS: Record<string, string> = {
  CURRENT: "text-green-700 bg-green-50",
  "1-30": "text-amber-700 bg-amber-50",
  "31-60": "text-orange-700 bg-orange-50",
  "61-90": "text-red-600 bg-red-50",
  "90+": "text-red-800 bg-red-100",
};

function fmt(n?: number) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function CustomerStatementPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customersLoaded, setCustomersLoaded] = useState(false);
  const [selectedId, setSelectedId] = useState("");
  const [statement, setStatement] = useState<CustomerStatement | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadCustomers = async () => {
    if (customersLoaded) return;
    const data = await salesApi.listCustomers(false);
    setCustomers(data);
    setCustomersLoaded(true);
  };

  const loadStatement = async (id: string) => {
    if (!id) return;
    setLoading(true);
    setError("");
    setStatement(null);
    try {
      const data = await salesApi.getCustomerStatement(id);
      setStatement(data);
    } catch {
      setError("Failed to load statement");
    } finally {
      setLoading(false);
    }
  };

  const aged = statement?.aged_balance;

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Customer Statement</h1>
        <p className="text-xs text-gray-500 mt-0.5">Outstanding invoices, aged balance, and credit utilization per customer.</p>
      </div>

      <div className="flex gap-3 items-center">
        <select
          className="border rounded px-3 py-2 text-sm min-w-64"
          value={selectedId}
          onFocus={loadCustomers}
          onChange={e => { setSelectedId(e.target.value); loadStatement(e.target.value); }}
        >
          <option value="">Select customer…</option>
          {customers.map(c => (
            <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
          ))}
        </select>
        {loading && <span className="text-xs text-gray-500">Loading…</span>}
      </div>

      {error && <p className="text-xs text-red-500">{error}</p>}

      {statement && (
        <div className="space-y-5">
          {/* Header */}
          <div className="bg-white border rounded-lg p-5">
            <div className="flex items-start justify-between flex-wrap gap-4">
              <div>
                <h2 className="text-base font-bold text-gray-900">{statement.customer_name}</h2>
                <p className="text-xs text-gray-500 mt-0.5">Code: {statement.customer_code} · As of {statement.as_of_date}</p>
              </div>
              <div className="grid grid-cols-3 gap-4 text-center">
                {[
                  { label: "Credit Limit", value: fmt(statement.credit_limit), color: "text-gray-700" },
                  { label: "Credit Used", value: fmt(statement.credit_used), color: "text-red-600" },
                  { label: "Credit Available", value: fmt(statement.credit_available), color: "text-green-700" },
                ].map(s => (
                  <div key={s.label} className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500">{s.label}</p>
                    <p className={`text-sm font-bold mt-0.5 ${s.color}`}>{s.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Aged Balance */}
          {aged && (
            <div className="bg-white border rounded-lg p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Aged Balance Summary</h3>
              <div className="grid grid-cols-5 gap-3">
                {[
                  { label: "Current", value: aged.current, bucket: "CURRENT" },
                  { label: "1-30 Days", value: aged.days_1_30, bucket: "1-30" },
                  { label: "31-60 Days", value: aged.days_31_60, bucket: "31-60" },
                  { label: "61-90 Days", value: aged.days_61_90, bucket: "61-90" },
                  { label: "90+ Days", value: aged.days_90_plus, bucket: "90+" },
                ].map(b => (
                  <div key={b.label} className={`rounded-lg p-3 text-center ${BUCKET_COLORS[b.bucket]}`}>
                    <p className="text-xs font-medium">{b.label}</p>
                    <p className="text-sm font-bold mt-0.5">{fmt(b.value)}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t flex justify-between items-center">
                <span className="text-sm font-semibold text-gray-700">Total Outstanding</span>
                <span className="text-base font-bold text-gray-900">{fmt(aged.total_outstanding)}</span>
              </div>
            </div>
          )}

          {/* Invoice List */}
          <div className="bg-white border rounded-lg shadow-sm">
            <div className="px-5 py-3 border-b">
              <h3 className="text-sm font-semibold text-gray-700">
                Open Invoices ({statement.invoices.length})
              </h3>
            </div>
            {statement.invoices.length === 0 ? (
              <div className="p-10 text-center text-gray-400 text-sm">No outstanding invoices.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      {["Invoice No.", "SO No.", "Invoice Date", "Due Date", "Total", "Paid", "Outstanding", "Age", "Status"].map(h => (
                        <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {statement.invoices.map((inv: StatementInvoiceRow) => (
                      <tr key={inv.invoice_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-mono text-xs text-gray-700">{inv.invoice_no}</td>
                        <td className="px-4 py-3 text-xs text-gray-500">{inv.so_no ?? "—"}</td>
                        <td className="px-4 py-3 text-xs text-gray-600">{inv.invoice_date}</td>
                        <td className="px-4 py-3 text-xs text-gray-600">{inv.due_date}</td>
                        <td className="px-4 py-3 text-xs text-right font-medium">{fmt(inv.total_amount)}</td>
                        <td className="px-4 py-3 text-xs text-right text-green-700">{fmt(inv.paid_amount)}</td>
                        <td className="px-4 py-3 text-xs text-right font-bold text-red-700">{fmt(inv.outstanding_balance)}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs rounded-full px-2 py-0.5 ${BUCKET_COLORS[inv.age_bucket]}`}>
                            {inv.age_bucket}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs text-gray-600 capitalize">
                            {inv.status.toLowerCase().replace("_", " ")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {!statement && !loading && selectedId && (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-sm">No outstanding invoices found for this customer.</p>
        </div>
      )}
    </div>
  );
}
