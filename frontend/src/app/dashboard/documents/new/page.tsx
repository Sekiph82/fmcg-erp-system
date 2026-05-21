"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { docsApi, CATEGORY_LABELS, DocumentCategory } from "@/lib/documents";
import { RequirePermission } from "@/components/PermissionGuard";

const CATEGORIES = Object.entries(CATEGORY_LABELS) as [DocumentCategory, string][];

const ENTITY_TYPES = [
  ["mpesa_transaction", "M-Pesa Transaction"],
  ["purchase_order", "Purchase Order"],
  ["sales_order", "Sales Order"],
  ["invoice", "Invoice"],
  ["shipment", "Shipment"],
  ["international_shipment", "International Shipment"],
  ["qc_inspection", "QC Inspection"],
  ["production_order", "Production Order"],
  ["goods_receipt", "Goods Receipt"],
  ["supplier", "Supplier"],
  ["employee", "Employee"],
  ["asset", "Asset"],
  ["delivery_trip", "Delivery Trip"],
  ["cash_transaction", "Cash Transaction"],
  ["payroll_period", "Payroll Period"],
  // Marketing entities
  ["mkt_campaign", "Campaign"],
  ["mkt_promotion", "Promotion"],
  ["mkt_influencer", "Influencer"],
  ["mkt_survey", "Survey"],
  ["mkt_brand_spend", "Brand Spend"],
  ["mkt_trade_spend", "Trade Spend"],
  ["mkt_store", "E-commerce Store"],
];

function NewDocumentContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supersedeId = searchParams.get("supersede");
  const entityTypeParam = searchParams.get("entity_type") ?? "";
  const entityIdParam = searchParams.get("entity_id") ?? "";

  // If superseding, pre-load the parent document
  const { data: parentDoc } = useQuery({
    queryKey: ["doc-parent", supersedeId],
    queryFn: () => docsApi.get(supersedeId!),
    enabled: !!supersedeId,
  });

  const [form, setForm] = useState({
    title: "",
    category: "SOP" as DocumentCategory,
    description: "",
    version: "1",
    revision_note: "",
    status: "DRAFT",
    effective_date: "",
    expiry_date: "",
    related_entity_type: entityTypeParam,
    related_entity_id: entityIdParam,
    file_url: "",
    file_name: "",
  });

  // Pre-fill form from parent document when superseding
  useEffect(() => {
    if (parentDoc) {
      setForm((p) => ({
        ...p,
        title: parentDoc.title,
        category: parentDoc.category,
        description: parentDoc.description ?? "",
        version: String((parentDoc.version ?? 1) + 1),
        related_entity_type: parentDoc.related_entity_type ?? "",
        related_entity_id: parentDoc.related_entity_id ?? "",
      }));
    }
  }, [parentDoc]);

  const f = (k: string) => ({
    value: (form as Record<string, string>)[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [k]: e.target.value })),
  });

  const createMutation = useMutation({
    mutationFn: docsApi.create,
    onSuccess: (doc) => router.push(`/dashboard/documents/${doc.id}`),
  });

  const newVersionMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => docsApi.newVersion(supersedeId!, payload),
    onSuccess: (doc) => router.push(`/dashboard/documents/${doc.id}`),
  });

  const mutation = supersedeId ? newVersionMutation : createMutation;

  const handleSubmit = () => {
    const payload: Record<string, unknown> = {
      title: form.title,
      category: form.category,
      status: form.status,
      version: Number(form.version) || 1,
    };
    if (form.description) payload.description = form.description;
    if (form.revision_note) payload.revision_note = form.revision_note;
    if (form.effective_date) payload.effective_date = form.effective_date;
    if (form.expiry_date) payload.expiry_date = form.expiry_date;
    if (form.related_entity_type) payload.related_entity_type = form.related_entity_type;
    if (form.related_entity_id) payload.related_entity_id = form.related_entity_id;
    if (form.file_url) payload.file_url = form.file_url;
    if (form.file_name) payload.file_name = form.file_name;
    mutation.mutate(payload);
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {supersedeId ? "New Version" : "New Document"}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {supersedeId
            ? `Creating next version — supersedes document ${supersedeId.slice(0, 8)}…`
            : "Add a document record to the ERP document store"}
        </p>
        {supersedeId && parentDoc && (
          <div className="mt-2 bg-indigo-50 border border-indigo-200 rounded px-3 py-2 text-xs text-indigo-700">
            Superseding: <strong>{parentDoc.title}</strong> (v{parentDoc.version}) — previous version will be marked as not-latest.
          </div>
        )}
      </div>

      <div className="bg-white border rounded-lg p-6 space-y-5">
        {/* Core fields */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Title *</label>
          <input className="w-full border rounded px-3 py-2 text-sm" {...f("title")} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Category *</label>
            <select className="w-full border rounded px-3 py-2 text-sm" {...f("category")}>
              {CATEGORIES.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Status</label>
            <select className="w-full border rounded px-3 py-2 text-sm" {...f("status")}>
              {["DRAFT", "APPROVED", "OBSOLETE", "ARCHIVED"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Version</label>
            <input type="number" min={1} className="w-full border rounded px-3 py-2 text-sm" {...f("version")} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Effective Date</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" {...f("effective_date")} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Expiry Date</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" {...f("expiry_date")} />
          </div>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Description</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm" rows={3} {...f("description")} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Revision Note</label>
          <input className="w-full border rounded px-3 py-2 text-sm" {...f("revision_note")} />
        </div>

        {/* Entity link */}
        <div className="border-t pt-4">
          <p className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">Link to ERP Entity (optional)</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Entity Type</label>
              <select className="w-full border rounded px-3 py-2 text-sm" {...f("related_entity_type")}>
                <option value="">— none —</option>
                {ENTITY_TYPES.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Entity ID</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm font-mono"
                placeholder="UUID of the linked record"
                {...f("related_entity_id")}
              />
            </div>
          </div>
          {(form.related_entity_type === "mpesa_transaction" || form.related_entity_type === "cash_transaction") && (
            <div className="mt-2 bg-blue-50 border border-blue-200 rounded px-3 py-2 text-xs text-blue-700">
              M-Pesa / Cash payment document — link payment proof or reconciliation files here.
            </div>
          )}
        </div>

        {/* File placeholder */}
        <div className="border-t pt-4">
          <p className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">File Attachment (placeholder)</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">File Name</label>
              <input className="w-full border rounded px-3 py-2 text-sm" placeholder="e.g. receipt_jan2026.pdf" {...f("file_name")} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">File URL / Storage Key</label>
              <input className="w-full border rounded px-3 py-2 text-sm font-mono" placeholder="s3://bucket/path or https://..." {...f("file_url")} />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            File upload is storage-agnostic. Paste an S3 key, GCS URI, or signed URL. Upload engine is plugged in separately.
          </p>
        </div>

        {mutation.isError && (
          <p className="text-sm text-red-600">Failed to save document. Check required fields.</p>
        )}

        <div className="flex gap-3 pt-2">
          <button
            onClick={handleSubmit}
            disabled={!form.title || mutation.isPending}
            className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Saving..." : "Save Document"}
          </button>
          <button
            onClick={() => router.push("/dashboard/documents")}
            className="px-4 py-2 border rounded text-sm hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default function NewDocumentPage() {
  return (
    <RequirePermission permission="documents.create">
      <NewDocumentContent />
    </RequirePermission>
  );
}
