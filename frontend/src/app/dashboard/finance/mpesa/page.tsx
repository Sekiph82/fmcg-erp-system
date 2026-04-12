"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { financeApi, MpesaReconciliation, ReconciliationStatus } from "@/lib/finance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { RequirePermission } from "@/components/PermissionGuard";

const statusBadge = (s: ReconciliationStatus) =>
  s === "MATCHED" ? "green" : s === "EXCEPTION" ? "red" : s === "MANUAL" ? "blue" : "yellow";

function MpesaReconciliationContent() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<ReconciliationStatus | "ALL">("ALL");
  const [selected, setSelected] = useState<MpesaReconciliation | null>(null);
  const [showMatch, setShowMatch] = useState(false);
  const [showException, setShowException] = useState(false);

  const { data: recons = [], isLoading } = useQuery({
    queryKey: ["finance-reconciliations", filter],
    queryFn: () => financeApi.listReconciliations(filter === "ALL" ? undefined : filter),
  });

  const autoMatch = useMutation({
    mutationFn: () => financeApi.autoMatchMpesa(),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["finance-reconciliations"] });
      alert(`Auto-match complete: ${res.matched} matched, ${res.skipped} skipped`);
    },
  });

  const manualMatch = useMutation({
    mutationFn: ({ reconId, data }: { reconId: string; data: object }) =>
      financeApi.manualMatch(reconId, data as Parameters<typeof financeApi.manualMatch>[1]),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-reconciliations"] });
      setShowMatch(false);
      setSelected(null);
    },
  });

  const markException = useMutation({
    mutationFn: ({ reconId, reason }: { reconId: string; reason: string }) =>
      financeApi.markException(reconId, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-reconciliations"] });
      setShowException(false);
      setSelected(null);
    },
  });

  const counts = {
    ALL: recons.length,
    UNMATCHED: recons.filter((r) => r.status === "UNMATCHED").length,
    MATCHED: recons.filter((r) => r.status === "MATCHED").length,
    MANUAL: recons.filter((r) => r.status === "MANUAL").length,
    EXCEPTION: recons.filter((r) => r.status === "EXCEPTION").length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">M-Pesa Reconciliation</h1>
          <p className="text-sm text-gray-500 mt-1">Match M-Pesa receipts to invoices and sales orders</p>
        </div>
        <Button onClick={() => autoMatch.mutate()} loading={autoMatch.isPending}>
          Run Auto-Match
        </Button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {(["ALL", "UNMATCHED", "MATCHED", "MANUAL", "EXCEPTION"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              filter === s ? "bg-indigo-600 text-white" : "bg-white border text-gray-600 hover:border-indigo-300"
            }`}
          >
            {s} {filter === "ALL" && s === "ALL" ? `(${counts.ALL})` : s !== "ALL" ? `(${counts[s as keyof typeof counts]})` : ""}
          </button>
        ))}
      </div>

      {/* Reconciliation table */}
      <div className="bg-white rounded-lg border">
        {isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Date</th>
                <th className="px-5 py-2 text-left">M-Pesa Receipt</th>
                <th className="px-5 py-2 text-left">Phone</th>
                <th className="px-5 py-2 text-left">Name</th>
                <th className="px-5 py-2 text-right">Amount</th>
                <th className="px-5 py-2 text-left">Matched To</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {recons.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 text-gray-600">{r.tx_date || "—"}</td>
                  <td className="px-5 py-3 font-mono text-xs">{r.mpesa_receipt || "—"}</td>
                  <td className="px-5 py-3">{r.mpesa_phone || "—"}</td>
                  <td className="px-5 py-3 text-gray-700">{r.mpesa_name || "—"}</td>
                  <td className="px-5 py-3 text-right font-semibold">
                    {r.tx_amount != null ? Number(r.tx_amount).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "—"}
                  </td>
                  <td className="px-5 py-3">
                    {r.invoice_no ? (
                      <span className="text-green-700">Invoice: {r.invoice_no}</span>
                    ) : r.so_no ? (
                      <span className="text-blue-700">SO: {r.so_no}</span>
                    ) : r.exception_reason ? (
                      <span className="text-red-600 text-xs">{r.exception_reason}</span>
                    ) : (
                      <span className="text-gray-400">Unmatched</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <Badge label={r.status} variant={statusBadge(r.status)} />
                  </td>
                  <td className="px-5 py-3">
                    {(r.status === "UNMATCHED" || r.status === "EXCEPTION") && (
                      <div className="flex gap-2">
                        <button
                          className="text-xs text-indigo-600 hover:underline"
                          onClick={() => { setSelected(r); setShowMatch(true); }}
                        >
                          Match
                        </button>
                        <button
                          className="text-xs text-red-500 hover:underline"
                          onClick={() => { setSelected(r); setShowException(true); }}
                        >
                          Exception
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {recons.length === 0 && (
                <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-400">No records</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Manual Match modal */}
      {showMatch && selected && (
        <ManualMatchModal
          recon={selected}
          onClose={() => { setShowMatch(false); setSelected(null); }}
          onSubmit={(data) => manualMatch.mutate({ reconId: selected.id, data })}
          loading={manualMatch.isPending}
        />
      )}

      {/* Exception modal */}
      {showException && selected && (
        <ExceptionModal
          recon={selected}
          onClose={() => { setShowException(false); setSelected(null); }}
          onSubmit={(reason) => markException.mutate({ reconId: selected.id, reason })}
          loading={markException.isPending}
        />
      )}
    </div>
  );
}

export default function MpesaReconciliationPage() {
  return (
    <RequirePermission permission="mpesa.view_transactions">
      <MpesaReconciliationContent />
    </RequirePermission>
  );
}

function ManualMatchModal({ recon, onClose, onSubmit, loading }: { recon: MpesaReconciliation; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const [form, setForm] = useState({ invoice_id: "", so_id: "", matched_amount: recon.tx_amount?.toString() ?? "", notes: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <div>
          <h2 className="font-semibold text-lg">Manual Match</h2>
          <p className="text-xs text-gray-500 mt-1">
            Receipt: <span className="font-mono">{recon.mpesa_receipt}</span> · Amount: KES {Number(recon.tx_amount).toLocaleString()}
          </p>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Invoice ID (UUID)</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" placeholder="Leave blank if matching to SO" value={form.invoice_id} onChange={(e) => set("invoice_id", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Sales Order ID (UUID)</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" placeholder="Leave blank if matching to Invoice" value={form.so_id} onChange={(e) => set("so_id", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Matched Amount</label>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.matched_amount} onChange={(e) => set("matched_amount", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            invoice_id: form.invoice_id || undefined,
            so_id: form.so_id || undefined,
            matched_amount: parseFloat(form.matched_amount) || undefined,
            notes: form.notes || undefined,
          })}>Confirm Match</Button>
        </div>
      </div>
    </div>
  );
}

function ExceptionModal({ recon, onClose, onSubmit, loading }: { recon: MpesaReconciliation; onClose: () => void; onSubmit: (reason: string) => void; loading: boolean }) {
  const [reason, setReason] = useState("");
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">Mark as Exception</h2>
        <p className="text-xs text-gray-500">Receipt: <span className="font-mono">{recon.mpesa_receipt}</span></p>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Exception Reason</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Describe why this cannot be matched…" />
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="danger" loading={loading} onClick={() => onSubmit(reason)}>Mark Exception</Button>
        </div>
      </div>
    </div>
  );
}
