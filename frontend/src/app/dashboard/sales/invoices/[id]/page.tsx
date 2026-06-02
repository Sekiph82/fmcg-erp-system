"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { salesApi } from "@/lib/sales";
import { extractApiError } from "@/lib/inventory";
import { ETimsSubmission, ETimsStatus, etimsApi } from "@/lib/tax_regulatory";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

const ETIMS_STATUS_BADGE: Record<ETimsStatus, "green" | "red" | "yellow" | "blue" | "gray"> = {
  ACCEPTED:      "green",
  REJECTED:      "red",
  FAILED:        "red",
  ERROR:         "red",
  SUBMITTED:     "yellow",
  PENDING:       "yellow",
  RETRY_PENDING: "yellow",
  DRAFT:         "blue",
  READY:         "blue",
  CANCELLED:     "gray",
};

const ETIMS_RETRY_STATUSES = new Set<ETimsStatus>(["REJECTED", "FAILED", "ERROR", "RETRY_PENDING"]);

function fmtDt(dt?: string | null) {
  return dt ? dt.slice(0, 16).replace("T", " ") : "—";
}

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [showPayment, setShowPayment] = useState(false);
  const [payForm, setPayForm] = useState({
    payment_date: new Date().toISOString().slice(0, 10),
    amount: "",
    reference: "",
    notes: "",
  });

  const [etimsCancelTarget, setEtimsCancelTarget] = useState<ETimsSubmission | null>(null);
  const [etimsCancelReason, setEtimsCancelReason] = useState("");

  // ── Invoice query ──────────────────────────────────────────────────────────

  const { data: invoice, isLoading } = useQuery({
    queryKey: ["sales-invoice", id],
    queryFn: () => salesApi.getInvoice(id),
  });

  // ── eTIMS submission query — 404 = not yet submitted ──────────────────────

  const { data: etims, isLoading: etimsLoading } = useQuery<ETimsSubmission | null>({
    queryKey: ["etims-submission", id],
    queryFn: async () => {
      try {
        return await etimsApi.getByInvoice(id);
      } catch (e: unknown) {
        const status = (e as { response?: { status?: number } })?.response?.status;
        if (status === 404) return null;
        throw e;
      }
    },
    staleTime: 30_000,
  });

  const invalidateEtims = () => {
    qc.invalidateQueries({ queryKey: ["etims-submission", id] });
    qc.invalidateQueries({ queryKey: ["etims-submissions"] });
  };

  // ── Payment mutation ───────────────────────────────────────────────────────

  const paymentMut = useMutation({
    mutationFn: () =>
      salesApi.recordPayment(id, {
        payment_date: payForm.payment_date,
        amount: parseFloat(payForm.amount),
        reference: payForm.reference || undefined,
        notes: payForm.notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sales-invoice", id] });
      qc.invalidateQueries({ queryKey: ["sales-invoices"] });
      qc.invalidateQueries({ queryKey: ["sales-summary"] });
      setShowPayment(false);
      setPayForm({ payment_date: new Date().toISOString().slice(0, 10), amount: "", reference: "", notes: "" });
      toast("success", "Payment recorded");
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  // ── eTIMS mutations ────────────────────────────────────────────────────────

  const etimsSubmitMut = useMutation({
    mutationFn: () => etimsApi.submit(id),
    onSuccess: (sub) => {
      invalidateEtims();
      toast("success", `eTIMS submitted — status: ${sub.status}`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const etimsRetryMut = useMutation({
    mutationFn: (submissionId: string) => etimsApi.retry(submissionId),
    onSuccess: (sub) => {
      invalidateEtims();
      toast("success", `eTIMS retry sent — status: ${sub.status}`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const etimsCancelMut = useMutation({
    mutationFn: ({ submissionId, reason, allowAccepted }: { submissionId: string; reason: string; allowAccepted: boolean }) =>
      etimsApi.cancel(submissionId, { reason, allow_cancel_accepted: allowAccepted }),
    onSuccess: () => {
      invalidateEtims();
      setEtimsCancelTarget(null);
      setEtimsCancelReason("");
      toast("success", "eTIMS submission cancelled");
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const etimsPollMut = useMutation({
    mutationFn: (submissionId: string) => etimsApi.poll(submissionId),
    onSuccess: (sub) => {
      invalidateEtims();
      toast("success", `eTIMS status polled — ${sub.status}`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  // ── Cancel helpers ─────────────────────────────────────────────────────────

  const openEtimsCancel = (sub: ETimsSubmission) => {
    setEtimsCancelTarget(sub);
    setEtimsCancelReason("");
  };

  const closeEtimsCancel = () => {
    setEtimsCancelTarget(null);
    setEtimsCancelReason("");
  };

  const submitEtimsCancel = () => {
    if (!etimsCancelTarget || !etimsCancelReason.trim()) return;
    etimsCancelMut.mutate({
      submissionId: etimsCancelTarget.id,
      reason: etimsCancelReason.trim(),
      allowAccepted: etimsCancelTarget.status === "ACCEPTED",
    });
  };

  // ── Loading / not-found guards ─────────────────────────────────────────────

  if (isLoading) return <div className="text-center py-12 text-gray-500">Loading...</div>;
  if (!invoice) return <div className="text-center py-12 text-red-500">Invoice not found</div>;

  const statusColor = (s: string) =>
    s === "PAID" ? "green" : s === "OVERDUE" ? "red" : s === "PARTIALLY_PAID" ? "yellow" : "blue";

  const canPay = !["PAID", "CANCELLED"].includes(invoice.status);

  const outstandingPct = invoice.total_amount > 0
    ? Math.round((invoice.paid_amount / invoice.total_amount) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard/sales/invoices")} className="text-gray-400 hover:text-gray-600">←</button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{invoice.invoice_no}</h1>
            <p className="text-sm text-gray-500">{invoice.customer_name} · SO: {invoice.so_no}</p>
          </div>
          <Badge label={invoice.status} variant={statusColor(invoice.status) as "green" | "blue" | "yellow" | "red"} />
          {invoice.days_overdue && (
            <span className="text-sm text-red-600 font-medium">{invoice.days_overdue}d overdue</span>
          )}
        </div>
        {canPay && (
          <Button onClick={() => {
            setPayForm({ ...payForm, amount: String(invoice.outstanding_balance) });
            setShowPayment(true);
          }}>Record Payment</Button>
        )}
      </div>

      {/* Payment Progress */}
      <div className="bg-white rounded-lg border p-6">
        <div className="grid grid-cols-4 gap-6 mb-4">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Invoice Date</p>
            <p className="font-semibold mt-1">{invoice.invoice_date}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Due Date</p>
            <p className={`font-semibold mt-1 ${invoice.days_overdue ? "text-red-600" : ""}`}>{invoice.due_date}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Currency</p>
            <p className="font-semibold mt-1">{invoice.currency}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Collection Rate</p>
            <p className="font-semibold mt-1">{outstandingPct}%</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Subtotal</p>
            <p className="text-lg font-bold text-gray-900 mt-1">{Number(invoice.subtotal).toFixed(2)}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Tax</p>
            <p className="text-lg font-bold text-gray-900 mt-1">{Number(invoice.tax_amount).toFixed(2)}</p>
          </div>
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <p className="text-xs text-blue-600 uppercase tracking-wide">Total</p>
            <p className="text-lg font-bold text-blue-700 mt-1">{Number(invoice.total_amount).toFixed(2)}</p>
          </div>
        </div>

        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Collection Progress</span>
          <span className="text-sm text-gray-500">
            {Number(invoice.paid_amount).toFixed(2)} / {Number(invoice.total_amount).toFixed(2)}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-green-500 h-3 rounded-full transition-all"
            style={{ width: `${outstandingPct}%` }}
          />
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-xs text-green-700">Paid: {Number(invoice.paid_amount).toFixed(2)}</span>
          <span className="text-xs text-orange-600 font-medium">Outstanding: {Number(invoice.outstanding_balance).toFixed(2)}</span>
        </div>
      </div>

      {/* Invoice Lines */}
      <div className="bg-white rounded-lg border">
        <div className="px-6 py-4 border-b">
          <h2 className="font-semibold text-gray-900">Invoice Lines</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {["Product", "Description", "Qty", "Unit", "Unit Price", "Discount", "Tax", "Line Total"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {invoice.lines?.map((line) => (
                <tr key={line.id}>
                  <td className="px-4 py-3 text-sm font-medium">{line.product_name || "—"}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{line.description || "—"}</td>
                  <td className="px-4 py-3 text-sm">{Number(line.quantity).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm">{line.unit}</td>
                  <td className="px-4 py-3 text-sm">{Number(line.unit_price).toFixed(4)}</td>
                  <td className="px-4 py-3 text-sm">{(Number(line.discount_pct) * 100).toFixed(1)}%</td>
                  <td className="px-4 py-3 text-sm">{(Number(line.tax_rate) * 100).toFixed(1)}%</td>
                  <td className="px-4 py-3 text-sm font-semibold">{Number(line.line_total).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Payments */}
      <div className="bg-white rounded-lg border">
        <div className="px-6 py-4 border-b">
          <h2 className="font-semibold text-gray-900">Payment History</h2>
        </div>
        {invoice.payments && invoice.payments.length > 0 ? (
          <div className="divide-y">
            {invoice.payments.map((p) => (
              <div key={p.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{invoice.currency} {Number(p.amount).toFixed(2)}</p>
                  <p className="text-sm text-gray-500">
                    {p.payment_date}{p.reference ? ` · Ref: ${p.reference}` : ""}
                  </p>
                  {p.notes && <p className="text-xs text-gray-400 mt-0.5">{p.notes}</p>}
                </div>
                <Badge label="Recorded" variant="green" />
              </div>
            ))}
          </div>
        ) : (
          <div className="px-6 py-4 text-sm text-gray-400">No payments recorded yet.</div>
        )}
      </div>

      {/* eTIMS Fiscalization Card */}
      <div className="bg-white rounded-lg border">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-gray-900">eTIMS Fiscalization</h2>
            <p className="text-xs text-gray-400 mt-0.5">KRA e-Invoice · simulation mode · production execution disabled</p>
          </div>
          {etims && (
            <Badge label={etims.status} variant={ETIMS_STATUS_BADGE[etims.status]} />
          )}
        </div>

        {etimsLoading ? (
          <div className="px-6 py-6 text-sm text-gray-400">Loading eTIMS status…</div>
        ) : etims == null ? (
          <div className="px-6 py-6 space-y-3">
            <p className="text-sm text-gray-500">This invoice has not been submitted to eTIMS yet.</p>
            <Button
              loading={etimsSubmitMut.isPending}
              disabled={etimsSubmitMut.isPending}
              onClick={() => etimsSubmitMut.mutate()}
            >
              Submit to eTIMS
            </Button>
          </div>
        ) : (
          <div className="px-6 py-5 space-y-4">
            {/* Key metadata */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-xs text-gray-400 uppercase font-semibold">Provider</p>
                <p className="mt-0.5 text-gray-700">
                  {etims.provider_name ?? "—"}
                  {etims.environment && <span className="ml-1 text-gray-400">({etims.environment})</span>}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase font-semibold">TIMS No</p>
                <p className="mt-0.5 font-mono text-gray-700">{etims.control_unit_invoice_no ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase font-semibold">KRA Response</p>
                <p className="mt-0.5 text-xs text-gray-600">
                  {etims.kra_response_code && (
                    <span className="font-mono mr-1">[{etims.kra_response_code}]</span>
                  )}
                  {etims.kra_response_message ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase font-semibold">Accepted At</p>
                <p className="mt-0.5 text-gray-600">{fmtDt(etims.accepted_at)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase font-semibold">Last Attempt</p>
                <p className="mt-0.5 text-gray-600">{fmtDt(etims.last_attempt_at ?? etims.transmitted_at)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase font-semibold">Attempts</p>
                <p className="mt-0.5 text-gray-600">{etims.attempt_count} total / {etims.retry_count} retries</p>
              </div>
            </div>

            {/* Error display */}
            {etims.error_code && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
                <span className="font-semibold">Error [{etims.error_code}]:</span> {etims.error_message ?? "—"}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 flex-wrap">
              <Button
                loading={etimsSubmitMut.isPending}
                disabled={
                  etimsSubmitMut.isPending ||
                  ["ACCEPTED", "SUBMITTED", "PENDING"].includes(etims.status)
                }
                onClick={() => etimsSubmitMut.mutate()}
              >
                Submit
              </Button>
              <Button
                variant="secondary"
                loading={etimsRetryMut.isPending}
                disabled={!ETIMS_RETRY_STATUSES.has(etims.status) || etimsRetryMut.isPending}
                onClick={() => etimsRetryMut.mutate(etims.id)}
              >
                Retry
              </Button>
              <Button
                variant="secondary"
                disabled={etims.status === "CANCELLED"}
                onClick={() => openEtimsCancel(etims)}
              >
                Cancel
              </Button>
              <Button
                variant="secondary"
                loading={etimsPollMut.isPending}
                disabled={!etims.provider_reference || etimsPollMut.isPending}
                onClick={() => etimsPollMut.mutate(etims.id)}
              >
                Poll Status
              </Button>
            </div>

            {/* Debug details */}
            {(etims.provider_reference || etims.signed_invoice_hash || etims.request_payload || etims.response_payload) && (
              <details className="text-xs text-gray-500">
                <summary className="cursor-pointer text-gray-400 hover:text-gray-600 select-none py-1">
                  Debug details
                </summary>
                <div className="mt-2 space-y-1 pl-2 border-l-2 border-gray-100">
                  {etims.provider_reference && (
                    <p>
                      <span className="font-semibold">Provider ref:</span>{" "}
                      <span className="font-mono">{etims.provider_reference}</span>
                    </p>
                  )}
                  {etims.signed_invoice_hash && (
                    <p>
                      <span className="font-semibold">Hash:</span>{" "}
                      <span className="font-mono break-all">{etims.signed_invoice_hash}</span>
                    </p>
                  )}
                  {etims.invoice_qr_data && (
                    <p>
                      <span className="font-semibold">QR data:</span>{" "}
                      <span className="font-mono break-all">{etims.invoice_qr_data}</span>
                    </p>
                  )}
                  {etims.request_payload && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-gray-400 select-none">Request payload</summary>
                      <pre className="mt-1 bg-gray-50 rounded p-2 overflow-x-auto">
                        {JSON.stringify(etims.request_payload, null, 2)}
                      </pre>
                    </details>
                  )}
                  {etims.response_payload && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-gray-400 select-none">Response payload</summary>
                      <pre className="mt-1 bg-gray-50 rounded p-2 overflow-x-auto">
                        {JSON.stringify(etims.response_payload, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </details>
            )}
          </div>
        )}
      </div>

      {/* Payment Modal */}
      <Modal open={showPayment} onClose={() => setShowPayment(false)} title="Record Payment">
        <div className="space-y-4">
          <div className="bg-orange-50 border border-orange-200 rounded p-3 text-sm">
            Outstanding: <strong>{invoice.currency} {Number(invoice.outstanding_balance).toFixed(2)}</strong>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Payment Date" type="date" value={payForm.payment_date} onChange={(e) => setPayForm({ ...payForm, payment_date: e.target.value })} required />
            <Input label="Amount" type="number" value={payForm.amount} onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })} required />
          </div>
          <Input label="Reference" value={payForm.reference} onChange={(e) => setPayForm({ ...payForm, reference: e.target.value })} placeholder="Cheque no, bank ref…" />
          <Input label="Notes" value={payForm.notes} onChange={(e) => setPayForm({ ...payForm, notes: e.target.value })} />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowPayment(false)}>Cancel</Button>
            <Button
              onClick={() => paymentMut.mutate()}
              disabled={paymentMut.isPending || !payForm.amount || Number(payForm.amount) <= 0}
            >
              {paymentMut.isPending ? "Recording..." : "Record Payment"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* eTIMS Cancel Modal */}
      <Modal
        open={etimsCancelTarget !== null}
        onClose={closeEtimsCancel}
        title={
          etimsCancelTarget?.status === "ACCEPTED"
            ? "Cancel Accepted eTIMS Submission"
            : "Cancel eTIMS Submission"
        }
      >
        {etimsCancelTarget && (
          <div className="space-y-4">
            {etimsCancelTarget.status === "ACCEPTED" && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
                <strong>Warning:</strong> This submission has been accepted by KRA. Cancelling may require
                a credit note and affect your VAT return. Proceed only if instructed by your tax advisor.
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Cancellation Reason (required)
              </label>
              <textarea
                value={etimsCancelReason}
                onChange={(e) => setEtimsCancelReason(e.target.value)}
                rows={3}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-200"
                placeholder="e.g. Customer request, data entry error…"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <Button variant="secondary" onClick={closeEtimsCancel}>Keep Submission</Button>
              <Button
                variant="danger"
                loading={etimsCancelMut.isPending}
                disabled={!etimsCancelReason.trim() || etimsCancelMut.isPending}
                onClick={submitEtimsCancel}
              >
                Confirm Cancel
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
