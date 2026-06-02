"use client";

import { Fragment, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ETimsStatus,
  ETimsSubmission,
  ETimsProviderHealth,
  etimsApi,
} from "@/lib/tax_regulatory";
import { extractApiError } from "@/lib/inventory";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

const ALL_STATUSES: ETimsStatus[] = [
  "DRAFT", "READY", "PENDING", "SUBMITTED", "ACCEPTED",
  "REJECTED", "RETRY_PENDING", "CANCELLED", "FAILED", "ERROR",
];

const STATUS_BADGE: Record<ETimsStatus, "green" | "red" | "yellow" | "blue" | "gray"> = {
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

const RETRY_STATUSES = new Set<ETimsStatus>(["REJECTED", "FAILED", "ERROR", "RETRY_PENDING"]);

function fmtDt(dt?: string | null) {
  return dt ? dt.slice(0, 16).replace("T", " ") : "—";
}

export default function ETimsPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [filterStatus, setFilterStatus] = useState<string>("");
  const [submitInvoiceId, setSubmitInvoiceId] = useState("");

  const [cancelTarget, setCancelTarget] = useState<ETimsSubmission | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  const [health, setHealth] = useState<ETimsProviderHealth | null>(null);

  // ── Query ──────────────────────────────────────────────────────────────────

  const { data = [], isLoading } = useQuery<ETimsSubmission[]>({
    queryKey: ["etims-submissions", filterStatus],
    queryFn: () =>
      etimsApi.listSubmissions(filterStatus ? { status: filterStatus as ETimsStatus } : undefined),
    staleTime: 30_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["etims-submissions"] });

  // ── Mutations ──────────────────────────────────────────────────────────────

  const submitMut = useMutation({
    mutationFn: (id: string) => etimsApi.submit(id),
    onSuccess: (sub) => {
      invalidate();
      setSubmitInvoiceId("");
      toast("success", `Submitted — status: ${sub.status}`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const retryMut = useMutation({
    mutationFn: (submissionId: string) => etimsApi.retry(submissionId),
    onSuccess: (sub) => {
      invalidate();
      toast("success", `Retry sent — status: ${sub.status}`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const cancelMut = useMutation({
    mutationFn: ({ id, reason, allowAccepted }: { id: string; reason: string; allowAccepted: boolean }) =>
      etimsApi.cancel(id, { reason, allow_cancel_accepted: allowAccepted }),
    onSuccess: () => {
      invalidate();
      setCancelTarget(null);
      setCancelReason("");
      toast("success", "Submission cancelled");
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const pollMut = useMutation({
    mutationFn: (submissionId: string) => etimsApi.poll(submissionId),
    onSuccess: (sub) => {
      invalidate();
      toast("success", `Status polled — ${sub.status}`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const healthMut = useMutation({
    mutationFn: () => etimsApi.health(),
    onSuccess: (h) => {
      setHealth(h);
      toast("success", "Health check complete");
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  // ── Stats ──────────────────────────────────────────────────────────────────

  const stats = {
    total:    data.length,
    accepted: data.filter((s) => s.status === "ACCEPTED").length,
    pending:  data.filter((s) => s.status === "PENDING" || s.status === "SUBMITTED").length,
    rejected: data.filter((s) => s.status === "REJECTED" || s.status === "FAILED" || s.status === "ERROR").length,
  };

  // ── Cancel helpers ─────────────────────────────────────────────────────────

  const openCancel = (sub: ETimsSubmission) => {
    setCancelTarget(sub);
    setCancelReason("");
  };

  const closeCancel = () => {
    setCancelTarget(null);
    setCancelReason("");
  };

  const submitCancel = () => {
    if (!cancelTarget || !cancelReason.trim()) return;
    cancelMut.mutate({
      id: cancelTarget.id,
      reason: cancelReason.trim(),
      allowAccepted: cancelTarget.status === "ACCEPTED",
    });
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-7xl mx-auto space-y-5 pb-10">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">eTIMS — KRA e-Invoice</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Electronic Tax Invoice Management System — Kenya Revenue Authority
        </p>
      </div>

      {/* Simulation banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <strong>Integration Mode:</strong> Running in simulation mode — no live KRA calls.{" "}
        <code className="bg-amber-100 px-1 rounded">production_execution_allowed = false</code>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Submissions", value: stats.total,    color: "text-gray-800" },
          { label: "Accepted",          value: stats.accepted,  color: "text-green-700" },
          { label: "Pending/Submitted", value: stats.pending,   color: "text-yellow-700" },
          { label: "Rejected/Failed",   value: stats.rejected,  color: "text-red-700" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs font-semibold text-gray-400 uppercase">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Provider health */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-800">Provider Health</h2>
          <Button variant="secondary" loading={healthMut.isPending} onClick={() => healthMut.mutate()}>
            Check Health
          </Button>
        </div>
        {health && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <p className="text-xs text-gray-400 uppercase font-semibold">Provider</p>
              <p className="font-mono text-gray-700 mt-0.5">{health.provider ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase font-semibold">Environment</p>
              <p className="font-mono text-gray-700 mt-0.5">{health.environment ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase font-semibold">Live</p>
              <p className="mt-0.5">
                <Badge label={health.live ? "LIVE" : "Simulation"} variant={health.live ? "red" : "gray"} />
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase font-semibold">Production Allowed</p>
              <p className="mt-0.5">
                <Badge
                  label={health.production_execution_allowed ? "YES" : "NO (safe)"}
                  variant={health.production_execution_allowed ? "red" : "green"}
                />
              </p>
            </div>
            {(health.detail || health.note) && (
              <div className="col-span-2 md:col-span-4">
                <p className="text-xs text-gray-400 uppercase font-semibold">Note</p>
                <p className="text-gray-500 text-xs mt-0.5">{health.detail ?? health.note}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Submit invoice form */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Submit Invoice to KRA</h2>
        <div className="flex gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Invoice ID (UUID)</label>
            <input
              value={submitInvoiceId}
              onChange={(e) => setSubmitInvoiceId(e.target.value)}
              placeholder="paste invoice UUID…"
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-80 focus:outline-none focus:ring-2 focus:ring-indigo-300 font-mono"
            />
          </div>
          <Button
            loading={submitMut.isPending}
            disabled={!submitInvoiceId || submitMut.isPending}
            onClick={() => submitInvoiceId && submitMut.mutate(submitInvoiceId)}
          >
            Submit to KRA
          </Button>
        </div>
        {submitMut.data && (
          <div className="mt-3 bg-green-50 border border-green-200 rounded-lg p-3 text-sm">
            <p className="font-semibold text-green-800">Status: {submitMut.data.status}</p>
            {submitMut.data.control_unit_invoice_no && (
              <p className="text-green-700">TIMS No: {submitMut.data.control_unit_invoice_no}</p>
            )}
            {submitMut.data.kra_response_message && (
              <p className="text-green-600 text-xs">{submitMut.data.kra_response_message}</p>
            )}
          </div>
        )}
      </div>

      {/* Submissions table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-4">
          <h2 className="font-semibold text-gray-800">Submissions</h2>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none"
          >
            <option value="">All Statuses</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Invoice</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Provider</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">TIMS No</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">KRA Response</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Attempts</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Last Attempt</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && (
                <tr><td colSpan={8} className="text-center py-8 text-gray-400">Loading…</td></tr>
              )}
              {!isLoading && data.length === 0 && (
                <tr><td colSpan={8} className="text-center py-8 text-gray-400">No eTIMS submissions yet.</td></tr>
              )}
              {data.map((sub) => (
                <Fragment key={sub.id}>
                  <tr className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{sub.invoice_id.slice(0, 8)}…</td>
                    <td className="px-4 py-2.5">
                      <Badge label={sub.status} variant={STATUS_BADGE[sub.status]} />
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      <span className="font-medium text-gray-700">{sub.provider_name ?? "—"}</span>
                      {sub.environment && (
                        <span className="ml-1 text-gray-400">({sub.environment})</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-700">
                      {sub.control_unit_invoice_no ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500 max-w-xs">
                      {sub.kra_response_code && (
                        <span className="font-mono mr-1">[{sub.kra_response_code}]</span>
                      )}
                      <span className="truncate">
                        {sub.kra_response_message ?? sub.error_message ?? "—"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500 text-center">
                      {sub.attempt_count} / {sub.retry_count}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">
                      {fmtDt(sub.last_attempt_at ?? sub.transmitted_at)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex gap-1 justify-end flex-wrap">
                        <Button
                          variant="secondary"
                          className="text-xs !px-2 !py-1"
                          disabled={!RETRY_STATUSES.has(sub.status) || retryMut.isPending}
                          loading={retryMut.isPending}
                          onClick={() => retryMut.mutate(sub.id)}
                        >
                          Retry
                        </Button>
                        <Button
                          variant="secondary"
                          className="text-xs !px-2 !py-1"
                          disabled={sub.status === "CANCELLED"}
                          onClick={() => openCancel(sub)}
                        >
                          Cancel
                        </Button>
                        <Button
                          variant="secondary"
                          className="text-xs !px-2 !py-1"
                          disabled={!sub.provider_reference || pollMut.isPending}
                          loading={pollMut.isPending}
                          onClick={() => pollMut.mutate(sub.id)}
                        >
                          Poll
                        </Button>
                      </div>
                    </td>
                  </tr>
                  {(sub.request_payload || sub.response_payload || sub.signed_invoice_hash || sub.error_code) && (
                    <tr className="bg-gray-50/60">
                      <td colSpan={8} className="px-4 pb-2">
                        <details className="text-xs text-gray-500">
                          <summary className="cursor-pointer text-gray-400 hover:text-gray-600 py-1 select-none">
                            Debug details
                          </summary>
                          <div className="mt-2 space-y-1 pl-2">
                            {sub.error_code && (
                              <p>
                                <span className="font-semibold text-red-600">Error:</span>{" "}
                                [{sub.error_code}] {sub.error_message}
                              </p>
                            )}
                            {sub.provider_reference && (
                              <p>
                                <span className="font-semibold">Provider ref:</span>{" "}
                                <span className="font-mono">{sub.provider_reference}</span>
                              </p>
                            )}
                            {sub.signed_invoice_hash && (
                              <p>
                                <span className="font-semibold">Hash:</span>{" "}
                                <span className="font-mono break-all">{sub.signed_invoice_hash}</span>
                              </p>
                            )}
                            {sub.request_payload && (
                              <details className="mt-1">
                                <summary className="cursor-pointer text-gray-400 select-none">Request payload</summary>
                                <pre className="mt-1 bg-gray-100 rounded p-2 overflow-x-auto text-xs">
                                  {JSON.stringify(sub.request_payload, null, 2)}
                                </pre>
                              </details>
                            )}
                            {sub.response_payload && (
                              <details className="mt-1">
                                <summary className="cursor-pointer text-gray-400 select-none">Response payload</summary>
                                <pre className="mt-1 bg-gray-100 rounded p-2 overflow-x-auto text-xs">
                                  {JSON.stringify(sub.response_payload, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        </details>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cancel confirm modal */}
      <Modal
        open={cancelTarget !== null}
        onClose={closeCancel}
        title={
          cancelTarget?.status === "ACCEPTED"
            ? "Cancel Accepted Submission"
            : "Cancel Submission"
        }
      >
        {cancelTarget && (
          <div className="space-y-4">
            {cancelTarget.status === "ACCEPTED" && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
                <strong>Warning:</strong> This submission has been accepted by KRA. Cancelling may
                require a credit note and may affect your VAT return. Proceed only if instructed by
                your tax advisor.
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Cancellation Reason (required)
              </label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                rows={3}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-200"
                placeholder="e.g. Customer request, data entry error…"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <Button variant="secondary" onClick={closeCancel}>
                Keep Submission
              </Button>
              <Button
                variant="danger"
                loading={cancelMut.isPending}
                disabled={!cancelReason.trim() || cancelMut.isPending}
                onClick={submitCancel}
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
