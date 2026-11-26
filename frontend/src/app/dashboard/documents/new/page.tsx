"use client";

import { EntityPicker, kindFor } from "@/components/EntityPicker";
import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { docsApi, CATEGORY_LABELS, DocumentCategory } from "@/lib/documents";
import { RequirePermission } from "@/components/PermissionGuard";
import { tx, lx } from "@/lib/i18n/core";

const CATEGORIES = Object.entries(CATEGORY_LABELS) as [DocumentCategory, string][];

const ENTITY_TYPES = lx(() => [
  ["mpesa_transaction", "M-Pesa Transaction"],
  ["purchase_order", tx("Purchase Order")],
  ["sales_order", tx("Sales Order")],
  ["invoice", "Invoice"],
  ["shipment", "Shipment"],
  ["international_shipment", tx("International Shipment")],
  ["qc_inspection", tx("QC Inspection")],
  ["production_order", tx("Production Order")],
  ["goods_receipt", tx("Goods Receipt")],
  ["supplier", "Supplier"],
  ["employee", "Employee"],
  ["asset", "Asset"],
  ["delivery_trip", tx("Delivery Trip")],
  ["cash_transaction", tx("Cash Transaction")],
  ["payroll_period", tx("Payroll Period")],
  // Marketing entities
  ["mkt_campaign", "Campaign"],
  ["mkt_promotion", "Promotion"],
  ["mkt_influencer", "Influencer"],
  ["mkt_survey", "Survey"],
  ["mkt_brand_spend", tx("Brand Spend")],
  ["mkt_trade_spend", tx("Trade Spend")],
  ["mkt_store", tx("E-commerce Store")],
]);

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
    effective_date: "",
    expiry_date: "",
    related_entity_type: entityTypeParam,
    related_entity_id: entityIdParam,
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
      version: Number(form.version) || 1,
    };
    if (form.description) payload.description = form.description;
    if (form.revision_note) payload.revision_note = form.revision_note;
    if (form.effective_date) payload.effective_date = form.effective_date;
    if (form.expiry_date) payload.expiry_date = form.expiry_date;
    if (form.related_entity_type) payload.related_entity_type = form.related_entity_type;
    if (form.related_entity_id) payload.related_entity_id = form.related_entity_id;
    mutation.mutate(payload);
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {supersedeId ? tx("New Version") : tx("New Document")}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {supersedeId
            ? tx("Creating next version — supersedes document {supersedeId}…", { supersedeId: supersedeId.slice(0, 8) })
            : tx("Add a document record to the ERP document store")}
        </p>
        {supersedeId && parentDoc && (
          <div className="mt-2 bg-indigo-50 border border-indigo-200 rounded px-3 py-2 text-xs text-indigo-700">
            {tx("Superseding:")} <strong>{parentDoc.title}</strong> {tx("(v")}{parentDoc.version}{tx(") — previous version will be marked as not-latest.")}
          </div>
        )}
      </div>

      <div className="bg-white border rounded-lg p-6 space-y-5">
        {/* Core fields */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">{tx("Title *")}</label>
          <input className="w-full border rounded px-3 py-2 text-sm" {...f("title")} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">{tx("Category *")}</label>
            <select className="w-full border rounded px-3 py-2 text-sm" {...f("category")}>
              {CATEGORIES.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">{tx("Version")}</label>
            <input type="number" min={1} className="w-full border rounded px-3 py-2 text-sm" {...f("version")} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">{tx("Effective Date")}</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" {...f("effective_date")} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">{tx("Expiry Date")}</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" {...f("expiry_date")} />
          </div>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">{tx("Description")}</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm" rows={3} {...f("description")} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">{tx("Revision Note")}</label>
          <input className="w-full border rounded px-3 py-2 text-sm" {...f("revision_note")} />
        </div>

        {/* Entity link */}
        <div className="border-t pt-4">
          <p className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">{tx("Link to ERP Entity (optional)")}</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">{tx("Entity Type")}</label>
              <select className="w-full border rounded px-3 py-2 text-sm" {...f("related_entity_type")}>
                <option value="">{tx("— none —")}</option>
                {ENTITY_TYPES.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{tx("Record")}</label>
              {form.related_entity_type && kindFor(form.related_entity_type) ? (
                <EntityPicker key={form.related_entity_type} kind={kindFor(form.related_entity_type)!} label={tx("Linked record")}
                  value={form.related_entity_id} onChange={(id) => setForm((p) => ({ ...p, related_entity_id: id }))} />
              ) : (
                <input className="w-full border rounded px-3 py-2 text-sm" placeholder={form.related_entity_type ? tx("Record number") : tx("Choose a type first")}
                  disabled={!form.related_entity_type} {...f("related_entity_id")} />
              )}
            </div>
          </div>
          {(form.related_entity_type === "mpesa_transaction" || form.related_entity_type === "cash_transaction") && (
            <div className="mt-2 bg-blue-50 border border-blue-200 rounded px-3 py-2 text-xs text-blue-700">
              {tx("M-Pesa / Cash payment document — link payment proof or reconciliation files here.")}
            </div>
          )}
        </div>

        {/* Binary files are attached from the saved document's detail page. */}
        <div className="border-t pt-4">
          <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">{tx("File Attachment")}</p>
          <p className="text-sm text-gray-500">
            {tx("Save the document first. You can attach a file from its detail page; it will remain unavailable until a malware scan succeeds.")}
          </p>
        </div>

        {mutation.isError && (
          <p className="text-sm text-red-600">{tx("Failed to save document. Check required fields.")}</p>
        )}

        <div className="flex gap-3 pt-2">
          <button
            onClick={handleSubmit}
            disabled={!form.title || mutation.isPending}
            className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            {mutation.isPending ? tx("Saving...") : tx("Save Document")}
          </button>
          <button
            onClick={() => router.push("/dashboard/documents")}
            className="px-4 py-2 border rounded text-sm hover:bg-gray-50"
          >
            {tx("Cancel")}
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
