"use client";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

interface PendingBill {
  template_id: string;
  template_code: string;
  template_name: string;
  so_id: string;
  so_no: string;
  customer_id: string;
  invoice_due_days: number;
  scheduled_date?: string;
}

interface GeneratedInvoice {
  invoice_id: string;
  invoice_no: string;
  total_amount: number;
  due_date: string;
}

export default function RecurringBillingPage() {
  const [pending, setPending] = useState<PendingBill[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const [generated, setGenerated] = useState<Record<string, GeneratedInvoice>>({});
  const [error, setError] = useState<Record<string, string>>({});

  const load = async () => {
    setLoading(true);
    try {
      const r = await apiClient.get<PendingBill[]>("/api/v1/recurring-orders/billing/pending");
      setPending(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const generate = async (bill: PendingBill) => {
    setGenerating(bill.so_id);
    setError(e => ({ ...e, [bill.so_id]: "" }));
    try {
      const r = await apiClient.post<GeneratedInvoice>(
        `/api/v1/recurring-orders/${bill.template_id}/billing/generate-invoice`,
        { so_id: bill.so_id }
      );
      setGenerated(g => ({ ...g, [bill.so_id]: r.data }));
      await load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed";
      setError(err => ({ ...err, [bill.so_id]: msg }));
    } finally { setGenerating(null); }
  };

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Recurring Billing</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Auto-invoicing for subscriptions with billing enabled. Shows SOs that need invoicing.
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
        <p className="text-xs text-blue-700 font-medium mb-1">How Auto-Invoicing Works</p>
        <p className="text-xs text-blue-600">
          Enable <code className="bg-blue-100 px-1 rounded">auto_invoice_flag</code> on a subscription template.
          After each recurring SO is generated, this page shows it as pending billing.
          Click "Generate Invoice" to create and issue the invoice. Due date =
          today + <code className="bg-blue-100 px-1 rounded">invoice_due_days</code>.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : pending.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">✅</p>
          <p className="text-sm">No recurring SOs pending invoicing.</p>
          <p className="text-xs mt-1">Enable auto_invoice_flag on subscriptions to see billing queue here.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Subscription", "SO No.", "Scheduled", "Due Days", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {pending.map(bill => {
                const inv = generated[bill.so_id];
                const err = error[bill.so_id];
                return (
                  <tr key={bill.so_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800 text-sm">{bill.template_name}</p>
                      <p className="text-xs text-gray-400 font-mono">{bill.template_code}</p>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-700">{bill.so_no}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">{bill.scheduled_date ?? "—"}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">{bill.invoice_due_days}d</td>
                    <td className="px-4 py-3">
                      {inv ? (
                        <span className="text-xs bg-green-100 text-green-700 rounded-full px-2 py-0.5">
                          Invoiced: {inv.invoice_no}
                        </span>
                      ) : err ? (
                        <span className="text-xs bg-red-100 text-red-600 rounded px-2 py-0.5">{err}</span>
                      ) : (
                        <span className="text-xs bg-amber-100 text-amber-700 rounded-full px-2 py-0.5">
                          Pending
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {!inv && (
                        <button
                          onClick={() => generate(bill)}
                          disabled={generating === bill.so_id}
                          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                          {generating === bill.so_id ? "Generating…" : "Generate Invoice"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <a href="/dashboard/recurring-orders" className="text-xs text-blue-600 hover:underline">← Recurring Orders</a>
    </div>
  );
}
