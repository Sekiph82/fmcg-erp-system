"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

type ETimsStatus = "PENDING" | "SUBMITTED" | "ACCEPTED" | "REJECTED" | "FAILED";

interface ETimsSubmission {
  id: string;
  invoice_id: string;
  status: ETimsStatus;
  control_unit_invoice_no?: string;
  signed_invoice_hash?: string;
  invoice_qr_data?: string;
  transmitted_at?: string;
  kra_response_code?: string;
  kra_response_message?: string;
  error_message?: string;
  retry_count: number;
  created_at: string;
}

const STATUS_PILL: Record<ETimsStatus, string> = {
  PENDING: "bg-gray-100 text-gray-600",
  SUBMITTED: "bg-blue-100 text-blue-700",
  ACCEPTED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
  FAILED: "bg-orange-100 text-orange-700",
};

const taxApi = {
  async listSubmissions(status?: string): Promise<ETimsSubmission[]> {
    const res = await apiClient.get<ETimsSubmission[]>("/api/v1/tax/etims/submissions", {
      params: status ? { status } : undefined,
    });
    return res.data;
  },
  async submitInvoice(invoiceId: string): Promise<ETimsSubmission> {
    const res = await apiClient.post<ETimsSubmission>(`/api/v1/tax/etims/submit/${invoiceId}`);
    return res.data;
  },
};

export default function ETimsPage() {
  const qc = useQueryClient();
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [submitInvoiceId, setSubmitInvoiceId] = useState("");

  const { data, isLoading } = useQuery<ETimsSubmission[]>({
    queryKey: ["etims-submissions", filterStatus],
    queryFn: () => taxApi.listSubmissions(filterStatus || undefined),
    staleTime: 30_000,
  });

  const submitMut = useMutation({
    mutationFn: (id: string) => taxApi.submitInvoice(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["etims-submissions"] });
      setSubmitInvoiceId("");
    },
  });

  const stats = {
    total: data?.length ?? 0,
    accepted: data?.filter((s) => s.status === "ACCEPTED").length ?? 0,
    pending: data?.filter((s) => s.status === "PENDING").length ?? 0,
    rejected: data?.filter((s) => s.status === "REJECTED").length ?? 0,
  };

  return (
    <div className="max-w-6xl mx-auto space-y-5 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">eTIMS — KRA e-Invoice</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Electronic Tax Invoice Management System — Kenya Revenue Authority
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <strong>Integration Mode:</strong> Set <code className="bg-amber-100 px-1 rounded">ETIMS_API_URL</code> environment
        variable to enable live KRA eTIMS API calls. Currently running in simulation mode.
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Submissions", value: stats.total, color: "text-gray-800" },
          { label: "Accepted", value: stats.accepted, color: "text-green-700" },
          { label: "Pending", value: stats.pending, color: "text-yellow-700" },
          { label: "Rejected", value: stats.rejected, color: "text-red-700" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs font-semibold text-gray-400 uppercase">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
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
          <button
            onClick={() => submitInvoiceId && submitMut.mutate(submitInvoiceId)}
            disabled={!submitInvoiceId || submitMut.isPending}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {submitMut.isPending ? "Submitting…" : "Submit to KRA"}
          </button>
        </div>
        {submitMut.isError && (
          <p className="text-sm text-red-500 mt-2">Submission failed. Check invoice ID is valid.</p>
        )}
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
            {["PENDING", "SUBMITTED", "ACCEPTED", "REJECTED", "FAILED"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Invoice ID</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">TIMS No</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Transmitted</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">KRA Response</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Retries</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">Loading…</td></tr>
            )}
            {!isLoading && (data ?? []).length === 0 && (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">No eTIMS submissions yet.</td></tr>
            )}
            {(data ?? []).map((sub) => (
              <tr key={sub.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{sub.invoice_id.slice(0, 8)}…</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${STATUS_PILL[sub.status]}`}>
                    {sub.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 font-mono text-xs text-gray-700">{sub.control_unit_invoice_no ?? "—"}</td>
                <td className="px-4 py-2.5 text-xs text-gray-500">
                  {sub.transmitted_at ? sub.transmitted_at.slice(0, 16).replace("T", " ") : "—"}
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-500 max-w-xs truncate">
                  {sub.kra_response_message ?? sub.error_message ?? "—"}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-400">{sub.retry_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
