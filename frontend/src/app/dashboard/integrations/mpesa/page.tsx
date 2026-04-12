"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  integrationsApi,
  MpesaTransaction,
  MpesaTxStatus,
  MpesaInitiateRequest,
} from "@/lib/integrations";
import { RequirePermission } from "@/components/PermissionGuard";

function fmtKES(n: number) {
  if (n >= 1_000_000) return `KES ${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `KES ${(n / 1_000).toFixed(1)}K`;
  return `KES ${n.toLocaleString()}`;
}

const STATUS_CFG: Record<MpesaTxStatus, { label: string; cls: string }> = {
  PENDING: { label: "Pending", cls: "bg-amber-100 text-amber-800" },
  SUCCESS: { label: "Success", cls: "bg-emerald-100 text-emerald-800" },
  FAILED: { label: "Failed", cls: "bg-red-100 text-red-800" },
  CANCELLED: { label: "Cancelled", cls: "bg-gray-100 text-gray-600" },
  TIMEOUT: { label: "Timeout", cls: "bg-orange-100 text-orange-800" },
  REVERSED: { label: "Reversed", cls: "bg-purple-100 text-purple-800" },
};

function StatusBadge({ status }: { status: MpesaTxStatus }) {
  const cfg = STATUS_CFG[status] ?? { label: status, cls: "bg-gray-100 text-gray-600" };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

function InitiateModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState<MpesaInitiateRequest>({
    phone_number: "",
    amount: 0,
    merchant_reference: `TXN-${Date.now()}`,
  });
  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: integrationsApi.initiateMpesa,
    onSuccess: () => {
      onSuccess();
      onClose();
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="text-lg font-bold text-gray-900">Initiate M-Pesa Payment</h2>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
        )}

        {[
          { label: "Phone (254XXXXXXXXX)", key: "phone_number", type: "tel" },
          { label: "Amount (KES)", key: "amount", type: "number" },
          { label: "Merchant Reference", key: "merchant_reference", type: "text" },
        ].map(({ label, key, type }) => (
          <div key={key}>
            <label className="block text-xs font-medium text-gray-700 mb-1">{label}</label>
            <input
              type={type}
              value={(form as unknown as Record<string, string | number>)[key] as string}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  [key]: type === "number" ? parseFloat(e.target.value) || 0 : e.target.value,
                }))
              }
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
        ))}

        <div className="flex gap-3 pt-2">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => mut.mutate(form)}
            disabled={mut.isPending || !form.phone_number || !form.amount || !form.merchant_reference}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          >
            {mut.isPending ? "Sending..." : "Send STK Push"}
          </button>
        </div>
      </div>
    </div>
  );
}

function MpesaPageContent() {
  const qc = useQueryClient();
  const [filterStatus, setFilterStatus] = useState<MpesaTxStatus | "">("");
  const [showInitiate, setShowInitiate] = useState(false);

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["mpesa-transactions", filterStatus],
    queryFn: () =>
      integrationsApi.listMpesaTransactions({
        status: filterStatus || undefined,
        limit: 100,
      }),
    refetchInterval: 30_000,
  });

  const { data: configStatus } = useQuery({
    queryKey: ["mpesa-config"],
    queryFn: integrationsApi.getMpesaConfig,
  });

  const retryMut = useMutation({
    mutationFn: integrationsApi.retryMpesa,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mpesa-transactions"] }),
  });

  const checkMut = useMutation({
    mutationFn: integrationsApi.checkMpesaStatus,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mpesa-transactions"] }),
  });

  // Summary stats
  const totalSuccess = transactions.filter((t) => t.status === "SUCCESS").reduce((s, t) => s + t.amount, 0);
  const pendingCount = transactions.filter((t) => t.status === "PENDING").length;
  const failedCount = transactions.filter((t) => t.status === "FAILED").length;
  const successCount = transactions.filter((t) => t.status === "SUCCESS").length;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {showInitiate && (
        <InitiateModal
          onClose={() => setShowInitiate(false)}
          onSuccess={() => qc.invalidateQueries({ queryKey: ["mpesa-transactions"] })}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📱 M-Pesa Transactions</h1>
          {configStatus && (
            <p className="text-xs text-gray-500 mt-0.5">
              {configStatus.configured ? (
                <span className="text-emerald-600">● Live ({configStatus.environment})</span>
              ) : (
                <span className="text-amber-600">● Sandbox mode (credentials not configured)</span>
              )}
              {" · "}Shortcode: {configStatus.shortcode || "—"}
            </p>
          )}
        </div>
        <button
          onClick={() => setShowInitiate(true)}
          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
        >
          + New Payment
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Collected", value: fmtKES(totalSuccess), color: "text-emerald-600" },
          { label: "Successful", value: successCount, color: "text-emerald-600" },
          { label: "Pending", value: pendingCount, color: "text-amber-600" },
          { label: "Failed", value: failedCount, color: "text-red-600" },
        ].map((s) => (
          <div key={s.label} className="bg-white border border-gray-200 rounded-xl p-4 text-center">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-gray-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        {(["", "PENDING", "SUCCESS", "FAILED", "CANCELLED", "TIMEOUT"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              filterStatus === s
                ? "bg-indigo-600 text-white border-indigo-600"
                : "bg-white text-gray-600 border-gray-200 hover:border-indigo-300"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading...</div>
        ) : transactions.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">No transactions found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {["Reference", "Phone", "Amount", "Status", "Receipt", "Date", "Actions"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {transactions.map((tx: MpesaTransaction) => (
                  <tr key={tx.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900 text-xs">{tx.merchant_reference}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-700 text-xs">{tx.phone_number}</td>
                    <td className="px-4 py-3 font-semibold text-gray-900">{fmtKES(tx.amount)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={tx.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs font-mono">
                      {tx.mpesa_receipt_number || "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {new Date(tx.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        {tx.status === "PENDING" && (
                          <>
                            <button
                              onClick={() => checkMut.mutate(tx.id)}
                              disabled={checkMut.isPending}
                              className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded hover:bg-blue-100"
                            >
                              Check
                            </button>
                            {tx.retry_count < 3 && (
                              <button
                                onClick={() => retryMut.mutate(tx.id)}
                                disabled={retryMut.isPending}
                                className="px-2 py-1 text-xs bg-amber-50 text-amber-700 rounded hover:bg-amber-100"
                              >
                                Retry
                              </button>
                            )}
                          </>
                        )}
                        {tx.status === "FAILED" && tx.retry_count < 3 && (
                          <button
                            onClick={() => retryMut.mutate(tx.id)}
                            disabled={retryMut.isPending}
                            className="px-2 py-1 text-xs bg-amber-50 text-amber-700 rounded hover:bg-amber-100"
                          >
                            Retry ({tx.retry_count}/3)
                          </button>
                        )}
                      </div>
                    </td>
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

export default function MpesaPage() {
  return (
    <RequirePermission permission="mpesa.view_transactions">
      <MpesaPageContent />
    </RequirePermission>
  );
}
