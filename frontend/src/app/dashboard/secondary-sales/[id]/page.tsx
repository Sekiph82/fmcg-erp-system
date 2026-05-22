"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  secondarySalesApi,
  SecondarySalesDetail,
  SecondarySalesStatus,
} from "@/lib/secondarySales";

const STATUS_COLORS: Record<SecondarySalesStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  VALIDATED: "bg-blue-100 text-blue-700",
  PROCESSED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
};

export default function SecondarySalesDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [record, setRecord] = useState<SecondarySalesDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await secondarySalesApi.get(id);
      setRecord(data);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404) {
        setError("not_found");
      } else {
        setError("Failed to load secondary sales record.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (id) load(); }, [id]);

  const handleProcess = async () => {
    setActionLoading(true); setActionError("");
    try {
      await secondarySalesApi.process(id);
      await load();
    } catch {
      setActionError("Failed to process record.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) { setActionError("Rejection reason required."); return; }
    setActionLoading(true); setActionError("");
    try {
      await secondarySalesApi.reject(id, rejectReason.trim());
      setShowRejectForm(false);
      setRejectReason("");
      await load();
    } catch {
      setActionError("Failed to reject record.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <a href="/dashboard/secondary-sales" className="text-sm text-blue-600 hover:underline">
          ← Secondary Sales
        </a>
        <p className="mt-6 text-sm text-gray-500">Loading…</p>
      </div>
    );
  }

  if (error === "not_found") {
    return (
      <div className="p-6">
        <a href="/dashboard/secondary-sales" className="text-sm text-blue-600 hover:underline">
          ← Secondary Sales
        </a>
        <div className="mt-8 text-center">
          <p className="text-lg font-medium text-gray-700">Record not found</p>
          <p className="text-sm text-gray-500 mt-1">No secondary sales upload with ID <span className="font-mono text-xs bg-gray-100 px-1 rounded">{id}</span></p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <a href="/dashboard/secondary-sales" className="text-sm text-blue-600 hover:underline">
          ← Secondary Sales
        </a>
        <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{error}</div>
      </div>
    );
  }

  if (!record) return null;

  const canProcess = record.status === "VALIDATED";
  const canReject = record.status === "PENDING" || record.status === "VALIDATED";
  const validLines = record.lines.filter(l => l.is_valid).length;
  const invalidLines = record.lines.filter(l => !l.is_valid).length;

  return (
    <div className="p-6 space-y-5 max-w-6xl">
      {/* Breadcrumb */}
      <div>
        <a href="/dashboard/secondary-sales" className="text-sm text-blue-600 hover:underline">
          ← Secondary Sales
        </a>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 font-mono">{record.reference_no}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {record.distributor_name || "Unknown Distributor"} · {record.period_from} – {record.period_to}
          </p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[record.status]}`}>
          {record.status}
        </span>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Total Lines", value: record.total_lines },
          { label: "Total Value", value: `KES ${record.total_value.toLocaleString()}` },
          { label: "Valid Lines", value: validLines, color: "text-green-600" },
          { label: "Invalid Lines", value: invalidLines, color: invalidLines > 0 ? "text-red-600" : "text-gray-700" },
        ].map(k => (
          <div key={k.label} className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color ?? "text-gray-800"}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Detail card */}
      <div className="bg-white border rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-800 mb-4">Upload Details</h2>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">
          {[
            { label: "Reference", value: record.reference_no },
            { label: "Upload Source", value: record.upload_source },
            { label: "Upload Date", value: record.upload_date ? new Date(record.upload_date).toLocaleDateString() : "—" },
            { label: "Period From", value: record.period_from },
            { label: "Period To", value: record.period_to },
            { label: "Distributor ID", value: record.distributor_id },
          ].map(f => (
            <div key={f.label}>
              <dt className="text-xs text-gray-500">{f.label}</dt>
              <dd className="font-medium text-gray-800 mt-0.5 font-mono text-xs">{f.value}</dd>
            </div>
          ))}
        </dl>
        {record.notes && (
          <div className="mt-4 pt-4 border-t">
            <p className="text-xs text-gray-500 mb-1">Notes</p>
            <p className="text-sm text-gray-700">{record.notes}</p>
          </div>
        )}
        {record.validation_errors && (
          <div className="mt-4 pt-4 border-t">
            <p className="text-xs text-red-500 mb-1">Validation Errors</p>
            <p className="text-sm text-red-700 bg-red-50 p-2 rounded">{record.validation_errors}</p>
          </div>
        )}
      </div>

      {/* Actions */}
      {(canProcess || canReject) && (
        <div className="bg-white border rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-800 mb-3">Actions</h2>
          <div className="flex gap-3 flex-wrap items-start">
            {canProcess && (
              <button
                onClick={handleProcess}
                disabled={actionLoading}
                className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {actionLoading ? "Processing…" : "Process Upload"}
              </button>
            )}
            {canReject && !showRejectForm && (
              <button
                onClick={() => setShowRejectForm(true)}
                disabled={actionLoading}
                className="rounded border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                Reject
              </button>
            )}
            {showRejectForm && (
              <div className="flex items-center gap-2 flex-wrap">
                <input
                  type="text"
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  placeholder="Rejection reason…"
                  className="border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-red-500 outline-none"
                />
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="rounded bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {actionLoading ? "Rejecting…" : "Confirm Reject"}
                </button>
                <button
                  onClick={() => { setShowRejectForm(false); setRejectReason(""); }}
                  className="rounded border px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            )}
            {actionError && <p className="text-xs text-red-600 w-full">{actionError}</p>}
          </div>
        </div>
      )}

      {/* Lines table */}
      <div>
        <h2 className="text-sm font-semibold text-gray-800 mb-3">
          Sales Lines
          {record.lines.length > 0 && (
            <span className="ml-2 text-xs font-normal text-gray-500">({record.lines.length} total)</span>
          )}
        </h2>
        {record.lines.length === 0 ? (
          <div className="bg-white border rounded-lg p-8 text-center text-gray-400 text-sm">No lines in this upload.</div>
        ) : (
          <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
                  <tr>
                    <th className="px-4 py-3 text-left">Retailer</th>
                    <th className="px-4 py-3 text-left">Product</th>
                    <th className="px-4 py-3 text-left">SKU</th>
                    <th className="px-4 py-3 text-right">Qty Sold</th>
                    <th className="px-4 py-3 text-right">Unit Price</th>
                    <th className="px-4 py-3 text-right">Total Value</th>
                    <th className="px-4 py-3 text-left">Sale Date</th>
                    <th className="px-4 py-3 text-left">Valid</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {record.lines.map(line => (
                    <tr key={line.id} className={line.is_valid ? "hover:bg-gray-50" : "bg-red-50 hover:bg-red-100"}>
                      <td className="px-4 py-3 text-gray-700">{line.retailer_name || "—"}</td>
                      <td className="px-4 py-3 text-gray-700">{line.product_name || "—"}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500">{line.product_sku || "—"}</td>
                      <td className="px-4 py-3 text-right font-medium">{line.quantity_sold.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{line.unit_price != null ? line.unit_price.toLocaleString() : "—"}</td>
                      <td className="px-4 py-3 text-right font-medium">{line.total_value != null ? line.total_value.toLocaleString() : "—"}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{line.sale_date || "—"}</td>
                      <td className="px-4 py-3">
                        {line.is_valid ? (
                          <span className="text-green-600 text-xs font-medium">✓</span>
                        ) : (
                          <span className="text-red-600 text-xs font-medium" title={line.validation_note || ""}>✗</span>
                        )}
                        {line.validation_note && (
                          <span className="ml-1 text-xs text-red-500">{line.validation_note}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
