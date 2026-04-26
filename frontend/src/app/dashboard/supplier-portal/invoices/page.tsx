"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { spApi, SPDocument, SP_DOC_REVIEW_COLORS } from "@/lib/supplier_portal";

function InvoicesContent() {
  const sp = useSearchParams();
  const accountId = sp.get("account") || "";
  const [invoices, setInvoices] = useState<SPDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [form, setForm] = useState({
    file_name: "", file_path: "", linked_po_id: "",
    notes: "", invoice_number: "", invoice_date: "", currency: "KES", total_amount: "",
  });

  const load = () => {
    if (!accountId) return;
    setLoading(true);
    spApi.listDocuments(accountId, "INVOICE").then(setInvoices).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [accountId]);

  const upload = async () => {
    if (!accountId) return;
    const notes = `Invoice #${form.invoice_number} | Date: ${form.invoice_date} | ${form.currency} ${form.total_amount}`;
    await spApi.uploadDocument(accountId, {
      upload_type: "INVOICE",
      file_name: form.file_name,
      file_path: form.file_path,
      linked_po_id: form.linked_po_id || undefined,
      notes,
    } as any);
    setUploading(false);
    load();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Invoice Submission</h1>
          <p className="text-sm text-gray-500 mt-1">Upload supplier invoices linked to purchase orders</p>
        </div>
        {accountId && (
          <button onClick={() => setUploading(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            + Submit Invoice
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["File Name", "Linked PO", "Uploaded", "Review Status", "Notes", "Reviewed By"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : invoices.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No invoices submitted yet.</td></tr>
            ) : invoices.map((inv) => (
              <tr key={inv.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-blue-700">{inv.file_name}</td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{inv.linked_po_id?.slice(0, 8) || "—"}</td>
                <td className="px-4 py-3 text-gray-500">{new Date(inv.uploaded_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SP_DOC_REVIEW_COLORS[inv.review_status]}`}>{inv.review_status}</span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">{inv.notes || "—"}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{inv.reviewed_by || "Pending"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {uploading && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Submit Invoice</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-700">Invoice Number</label>
                <input value={form.invoice_number} onChange={(e) => setForm({ ...form, invoice_number: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="INV-001" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Invoice Date</label>
                <input type="date" value={form.invoice_date} onChange={(e) => setForm({ ...form, invoice_date: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Currency</label>
                <input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Total Amount</label>
                <input type="number" value={form.total_amount} onChange={(e) => setForm({ ...form, total_amount: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">File Name</label>
              <input value={form.file_name} onChange={(e) => setForm({ ...form, file_name: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="invoice.pdf" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">File Path / Reference</label>
              <input value={form.file_path} onChange={(e) => setForm({ ...form, file_path: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="/uploads/invoice.pdf" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Linked PO ID (optional)</label>
              <input value={form.linked_po_id} onChange={(e) => setForm({ ...form, linked_po_id: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setUploading(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={upload} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Submit</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function InvoicesPage() {
  return <Suspense fallback={<div className="p-6 text-gray-400">Loading…</div>}><InvoicesContent /></Suspense>;
}
