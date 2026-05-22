"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import {
  docsApi, CATEGORY_LABELS, DocumentStatus, DocumentRead,
} from "@/lib/documents";
import { RequirePermission } from "@/components/PermissionGuard";
import { Badge } from "@/components/ui/Badge";

const STATUS_VARIANT: Record<DocumentStatus, "yellow" | "green" | "gray" | "red"> = {
  DRAFT: "yellow",
  APPROVED: "green",
  OBSOLETE: "gray",
  ARCHIVED: "red",
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  mpesa_transaction: "M-Pesa Transaction",
  purchase_order: "Purchase Order",
  sales_order: "Sales Order",
  invoice: "Invoice",
  shipment: "Shipment",
  international_shipment: "Intl Shipment",
  qc_inspection: "QC Inspection",
  production_order: "Production Order",
  goods_receipt: "Goods Receipt",
  supplier: "Supplier",
  employee: "Employee",
  asset: "Asset",
  delivery_trip: "Delivery Trip",
  cash_transaction: "Cash Transaction",
  payroll_period: "Payroll Period",
};

function EditPanel({ doc, onClose }: { doc: DocumentRead; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    title: doc.title,
    description: doc.description ?? "",
    revision_note: doc.revision_note ?? "",
    related_entity_type: doc.related_entity_type ?? "",
    related_entity_id: doc.related_entity_id ?? "",
    file_url: doc.file_url ?? "",
    file_name: doc.file_name ?? "",
    effective_date: doc.effective_date ?? "",
    expiry_date: doc.expiry_date ?? "",
  });

  const f = (k: string) => ({
    value: (form as Record<string, string>)[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((p) => ({ ...p, [k]: e.target.value })),
  });

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => docsApi.update(doc.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document", doc.id] });
      onClose();
    },
  });

  const payload = () => {
    const out: Record<string, unknown> = { title: form.title };
    if (form.description) out.description = form.description;
    if (form.revision_note) out.revision_note = form.revision_note;
    if (form.related_entity_type) out.related_entity_type = form.related_entity_type;
    if (form.related_entity_id) out.related_entity_id = form.related_entity_id;
    if (form.file_url) out.file_url = form.file_url;
    if (form.file_name) out.file_name = form.file_name;
    if (form.effective_date) out.effective_date = form.effective_date;
    if (form.expiry_date) out.expiry_date = form.expiry_date;
    return out;
  };

  return (
    <div className="bg-white border rounded-lg p-5 space-y-4">
      <h3 className="font-semibold text-gray-800">Edit Document</h3>
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className="text-xs text-gray-500">Title</label>
          <input className="w-full border rounded px-3 py-2 text-sm mt-1" {...f("title")} />
        </div>
        <div className="col-span-2">
          <label className="text-xs text-gray-500">Description</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm mt-1" rows={2} {...f("description")} />
        </div>
        <div className="col-span-2">
          <label className="text-xs text-gray-500">Revision Note</label>
          <input className="w-full border rounded px-3 py-2 text-sm mt-1" {...f("revision_note")} />
        </div>
        <div>
          <label className="text-xs text-gray-500">Effective Date</label>
          <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1" {...f("effective_date")} />
        </div>
        <div>
          <label className="text-xs text-gray-500">Expiry Date</label>
          <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1" {...f("expiry_date")} />
        </div>
        <div>
          <label className="text-xs text-gray-500">File Name</label>
          <input className="w-full border rounded px-3 py-2 text-sm mt-1" {...f("file_name")} />
        </div>
        <div>
          <label className="text-xs text-gray-500">File URL / Key</label>
          <input className="w-full border rounded px-3 py-2 text-sm mt-1 font-mono" {...f("file_url")} />
        </div>
      </div>
      <div className="flex gap-3">
        <button
          onClick={() => mutation.mutate(payload())}
          disabled={mutation.isPending}
          className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          {mutation.isPending ? "Saving..." : "Save"}
        </button>
        <button onClick={onClose} className="px-4 py-2 border rounded text-sm hover:bg-gray-50">Cancel</button>
      </div>
    </div>
  );
}

function DocumentDetailContent({ id }: { id: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [showVersions, setShowVersions] = useState(false);

  const { data: doc, isLoading } = useQuery({
    queryKey: ["document", id],
    queryFn: () => docsApi.get(id),
  });

  const { data: versions = [] } = useQuery({
    queryKey: ["document-versions", id],
    queryFn: () => docsApi.versions(id),
    enabled: showVersions,
  });

  const approveMutation = useMutation({
    mutationFn: () => docsApi.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document", id] }),
  });

  const obsoleteMutation = useMutation({
    mutationFn: () => docsApi.obsolete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document", id] }),
  });

  const archiveMutation = useMutation({
    mutationFn: () => docsApi.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document", id] }),
  });

  if (isLoading) return <p className="text-sm text-gray-400 p-6">Loading...</p>;
  if (!doc) return <p className="text-sm text-red-500 p-6">Document not found.</p>;

  return (
    <div className="space-y-5 max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <button onClick={() => router.push("/dashboard/documents")} className="text-xs text-gray-400 hover:text-gray-600 mb-2 inline-block">
            ← Documents
          </button>
          <h1 className="text-xl font-bold text-gray-900">{doc.title}</h1>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <Badge label={doc.status} variant={STATUS_VARIANT[doc.status]} />
            <span className="text-xs text-gray-500">{CATEGORY_LABELS[doc.category]}</span>
            <span className="text-xs font-mono text-gray-400">v{doc.version}</span>
            {!doc.is_latest && (
              <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded">Not Latest</span>
            )}
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          {doc.status === "DRAFT" && (
            <>
              <button
                onClick={() => setEditing(!editing)}
                className="px-3 py-1.5 border rounded text-sm hover:bg-gray-50"
              >
                {editing ? "Cancel Edit" : "Edit"}
              </button>
              <button
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
                className="px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
              >
                Approve
              </button>
            </>
          )}
          {doc.status === "APPROVED" && (
            <button
              onClick={() => obsoleteMutation.mutate()}
              disabled={obsoleteMutation.isPending}
              className="px-3 py-1.5 border border-red-200 text-red-600 rounded text-sm hover:bg-red-50 disabled:opacity-50"
            >
              Mark Obsolete
            </button>
          )}
          {doc.status !== "ARCHIVED" && (
            <button
              onClick={() => archiveMutation.mutate()}
              disabled={archiveMutation.isPending}
              className="px-3 py-1.5 border text-gray-500 rounded text-sm hover:bg-gray-50 disabled:opacity-50"
            >
              Archive
            </button>
          )}
          <button
            onClick={() => router.push(`/dashboard/documents/new?supersede=${id}`)}
            className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700"
          >
            New Version
          </button>
        </div>
      </div>

      {editing && <EditPanel doc={doc} onClose={() => setEditing(false)} />}

      {/* Detail cards */}
      <div className="grid grid-cols-2 gap-4">
        {/* Core info */}
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Document Info</h3>
          <Row label="Category" value={CATEGORY_LABELS[doc.category]} />
          <Row label="Version" value={`v${doc.version}`} />
          <Row label="Status" value={doc.status} />
          <Row label="Effective" value={doc.effective_date ?? "—"} />
          <Row label="Expires" value={doc.expiry_date ?? "—"} />
          {doc.revision_note && <Row label="Revision Note" value={doc.revision_note} />}
        </div>

        {/* Entity link */}
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Linked ERP Entity</h3>
          {doc.related_entity_type ? (
            <>
              <Row
                label="Entity Type"
                value={ENTITY_TYPE_LABELS[doc.related_entity_type] ?? doc.related_entity_type}
              />
              <Row label="Entity ID" value={doc.related_entity_id ?? "—"} mono />
              {(doc.related_entity_type === "mpesa_transaction" || doc.related_entity_type === "cash_transaction") && (
                <div className="bg-blue-50 border border-blue-200 rounded px-3 py-2 text-xs text-blue-700">
                  M-Pesa / payment document — linked to transaction record.
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-400">No entity linked</p>
          )}
        </div>

        {/* File */}
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">File Attachment</h3>
          {doc.file_name || doc.file_url ? (
            <>
              {doc.file_name && <Row label="File Name" value={doc.file_name} />}
              {doc.mime_type && <Row label="MIME Type" value={doc.mime_type} />}
              {doc.file_size_bytes && <Row label="Size" value={`${(doc.file_size_bytes / 1024).toFixed(1)} KB`} />}
              {doc.file_url && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Storage Key / URL</p>
                  <p className="text-xs font-mono text-gray-700 break-all bg-gray-50 p-2 rounded">{doc.file_url}</p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-400">No file attached</p>
          )}
        </div>

        {/* Accountability */}
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Accountability</h3>
          <Row label="Owner User ID" value={doc.owner_user_id ?? "—"} mono />
          <Row label="Approved By ID" value={doc.approved_by_id ?? "—"} mono />
          <Row label="Created" value={new Date(doc.created_at).toLocaleString()} />
          <Row label="Updated" value={new Date(doc.updated_at).toLocaleString()} />
        </div>
      </div>

      {/* Description */}
      {doc.description && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Description</h3>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{doc.description}</p>
        </div>
      )}

      {/* Version history */}
      <div className="bg-white border rounded-lg">
        <button
          className="w-full px-4 py-3 text-left flex items-center justify-between hover:bg-gray-50"
          onClick={() => setShowVersions(!showVersions)}
        >
          <span className="text-sm font-semibold text-gray-800">Version History</span>
          <span className="text-xs text-gray-400">{showVersions ? "▲ hide" : "▼ show"}</span>
        </button>
        {showVersions && (
          <div className="border-t">
            {versions.length === 0 ? (
              <p className="p-4 text-sm text-gray-400">No history found</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                    <th className="px-4 py-2 text-left">Version</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Latest</th>
                    <th className="px-4 py-2 text-left">Note</th>
                    <th className="px-4 py-2 text-left">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {versions.map((v) => (
                    <tr key={v.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs">v{v.version}</td>
                      <td className="px-4 py-2">
                        <Badge label={v.status} variant={STATUS_VARIANT[v.status]} />
                      </td>
                      <td className="px-4 py-2 text-xs">{v.is_latest ? <span className="text-green-600">Yes</span> : <span className="text-gray-400">No</span>}</td>
                      <td className="px-4 py-2 text-xs text-gray-500">{v.revision_note ?? "—"}</td>
                      <td className="px-4 py-2 text-xs text-gray-400">{new Date(v.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-xs text-gray-500 w-28 shrink-0">{label}</span>
      <span className={`text-xs text-gray-800 break-all ${mono ? "font-mono" : ""}`}>{value}</span>
    </div>
  );
}

export default function DocumentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  return (
    <RequirePermission permission="documents.view">
      <DocumentDetailContent id={id} />
    </RequirePermission>
  );
}
