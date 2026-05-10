"use client";
import { useCallback, useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { spApi, SPDocument, SPDocUploadType, SPDocReviewStatus, SP_DOC_REVIEW_COLORS } from "@/lib/supplier_portal";

const DOC_TYPES: SPDocUploadType[] = [
  "INVOICE", "DELIVERY_NOTE", "PACKING_LIST", "BILL_OF_LADING",
  "COA", "MSDS", "SPECIFICATION", "COMPLIANCE_CERT",
  "FOOD_SAFETY_CERT", "HALAL_CERT", "TEST_RESULT", "TAX_DOC", "OTHER",
];

function DocumentsContent() {
  const sp = useSearchParams();
  const accountId = sp.get("account") || "";
  const [docs, setDocs] = useState<SPDocument[]>([]);
  const [expiring, setExpiring] = useState<SPDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [reviewFilter, setReviewFilter] = useState("");
  const [uploading, setUploading] = useState(false);
  const [reviewing, setReviewing] = useState<SPDocument | null>(null);
  const [form, setForm] = useState({ upload_type: "DELIVERY_NOTE" as SPDocUploadType, file_name: "", file_path: "", linked_po_id: "", expiry_date: "", notes: "" });
  const [reviewForm, setReviewForm] = useState({ review_status: "ACCEPTED", reviewed_by: "", notes: "" });

  const load = useCallback(() => {
    if (!accountId) return;
    setLoading(true);
    Promise.all([
      spApi.listDocuments(accountId, typeFilter || undefined, reviewFilter || undefined),
      spApi.expiringDocuments(30),
    ]).then(([d, e]) => { setDocs(d); setExpiring(e); }).finally(() => setLoading(false));
  }, [accountId, typeFilter, reviewFilter]);

  useEffect(() => { load(); }, [load]);

  const upload = async () => {
    if (!accountId) return;
    await spApi.uploadDocument(accountId, {
      upload_type: form.upload_type,
      file_name: form.file_name,
      file_path: form.file_path,
      linked_po_id: form.linked_po_id || undefined,
      expiry_date: form.expiry_date || undefined,
      notes: form.notes || undefined,
    } as any);
    setUploading(false);
    load();
  };

  const review = async () => {
    if (!reviewing) return;
    await spApi.reviewDocument(reviewing.id, reviewForm as any);
    setReviewing(null);
    load();
  };

  const badge = (s: SPDocReviewStatus) => (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SP_DOC_REVIEW_COLORS[s]}`}>{s}</span>
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Supplier Document Center</h1>
        {accountId && (
          <button onClick={() => setUploading(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            + Upload Document
          </button>
        )}
      </div>

      {expiring.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-red-800 mb-2">Expiring Certificates (next 30 days)</h3>
          <div className="flex flex-wrap gap-2">
            {expiring.map((d) => (
              <span key={d.id} className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-lg">
                {d.file_name} — expires {d.expiry_date}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Types</option>
          {DOC_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
        <select value={reviewFilter} onChange={(e) => setReviewFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {(["PENDING", "ACCEPTED", "REJECTED", "SUPERSEDED"] as SPDocReviewStatus[]).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["File Name", "Type", "Linked PO", "Uploaded", "Expiry", "Status", "Reviewed By", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : docs.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No documents found.</td></tr>
            ) : docs.map((d) => (
              <tr key={d.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-blue-700">{d.file_name}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">{d.upload_type.replace(/_/g, " ")}</span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{d.linked_po_id?.slice(0, 8) || "—"}</td>
                <td className="px-4 py-3 text-gray-500">{new Date(d.uploaded_at).toLocaleDateString()}</td>
                <td className="px-4 py-3 text-gray-500">{d.expiry_date || "—"}</td>
                <td className="px-4 py-3">{badge(d.review_status)}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{d.reviewed_by || "—"}</td>
                <td className="px-4 py-3">
                  {d.review_status === "PENDING" && (
                    <button onClick={() => setReviewing(d)} className="text-blue-600 hover:underline text-xs">Review</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {uploading && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Upload Document</h2>
            <div>
              <label className="text-xs font-medium text-gray-700">Document Type</label>
              <select value={form.upload_type} onChange={(e) => setForm({ ...form, upload_type: e.target.value as SPDocUploadType })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                {DOC_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">File Name</label>
              <input value={form.file_name} onChange={(e) => setForm({ ...form, file_name: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="document.pdf" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">File Path / Reference</label>
              <input value={form.file_path} onChange={(e) => setForm({ ...form, file_path: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="/uploads/doc.pdf" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Linked PO ID (optional)</label>
              <input value={form.linked_po_id} onChange={(e) => setForm({ ...form, linked_po_id: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Expiry Date (if applicable)</label>
              <input type="date" value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Notes</label>
              <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setUploading(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={upload} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Upload</button>
            </div>
          </div>
        </div>
      )}

      {reviewing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Review Document</h2>
            <p className="text-sm text-gray-600">{reviewing.file_name}</p>
            <div>
              <label className="text-xs font-medium text-gray-700">Decision</label>
              <select value={reviewForm.review_status} onChange={(e) => setReviewForm({ ...reviewForm, review_status: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="ACCEPTED">Accept</option>
                <option value="REJECTED">Reject</option>
                <option value="SUPERSEDED">Supersede</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Reviewed By</label>
              <input value={reviewForm.reviewed_by} onChange={(e) => setReviewForm({ ...reviewForm, reviewed_by: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Notes</label>
              <textarea value={reviewForm.notes} onChange={(e) => setReviewForm({ ...reviewForm, notes: e.target.value })}
                rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setReviewing(null)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={review} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Submit</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  return <Suspense fallback={<div className="p-6 text-gray-400">Loading…</div>}><DocumentsContent /></Suspense>;
}
