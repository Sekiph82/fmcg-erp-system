"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  docsApi, DocumentCategory, DocumentStatus,
  CATEGORY_LABELS, DocumentShort,
} from "@/lib/documents";
import { RequirePermission } from "@/components/PermissionGuard";
import { Badge } from "@/components/ui/Badge";
import { PermissionGuard } from "@/components/PermissionGuard";

const STATUS_VARIANT: Record<DocumentStatus, "yellow" | "green" | "gray" | "red"> = {
  DRAFT: "yellow",
  APPROVED: "green",
  OBSOLETE: "gray",
  ARCHIVED: "red",
};

const CATEGORIES = Object.entries(CATEGORY_LABELS) as [DocumentCategory, string][];

// Entity type display labels for the filter
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

function DocumentsContent() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [entityType, setEntityType] = useState("");
  const [latestOnly, setLatestOnly] = useState(true);

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["documents", search, category, status, entityType, latestOnly],
    queryFn: () =>
      docsApi.list({
        search: search || undefined,
        category: category || undefined,
        status: status || undefined,
        related_entity_type: entityType || undefined,
        latest_only: latestOnly,
      }),
  });

  const { data: stats } = useQuery({
    queryKey: ["docs-stats"],
    queryFn: docsApi.stats,
    staleTime: 60_000,
  });

  // Summary counts — prefer server stats when no filter is active, else count from current docs
  const counts = {
    DRAFT:    status || category || entityType || search ? docs.filter((d) => d.status === "DRAFT").length    : (stats?.by_status?.DRAFT ?? 0),
    APPROVED: status || category || entityType || search ? docs.filter((d) => d.status === "APPROVED").length : (stats?.by_status?.APPROVED ?? 0),
    OBSOLETE: status || category || entityType || search ? docs.filter((d) => d.status === "OBSOLETE").length : (stats?.by_status?.OBSOLETE ?? 0),
    ARCHIVED: status || category || entityType || search ? docs.filter((d) => d.status === "ARCHIVED").length : (stats?.by_status?.ARCHIVED ?? 0),
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-sm text-gray-500 mt-1">
            {stats ? `${stats.total} total · ${stats.latest_only_count} latest versions` : `${docs.length} shown`}
          </p>
        </div>
        <PermissionGuard permission="documents.create">
          <button
            onClick={() => router.push("/dashboard/documents/new")}
            className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700"
          >
            + New Document
          </button>
        </PermissionGuard>
      </div>

      {/* Expiry warnings */}
      {stats && (stats.expiring_soon_count > 0 || stats.expired_count > 0) && (
        <div className="flex gap-3 flex-wrap">
          {stats.expired_count > 0 && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-700">
              <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
              {stats.expired_count} document{stats.expired_count !== 1 ? "s" : ""} expired
            </div>
          )}
          {stats.expiring_soon_count > 0 && (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-700">
              <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
              {stats.expiring_soon_count} expiring within 30 days
            </div>
          )}
        </div>
      )}

      {/* Status summary */}
      <div className="grid grid-cols-4 gap-3">
        {(Object.entries(counts) as [DocumentStatus, number][]).map(([s, n]) => (
          <button
            key={s}
            onClick={() => setStatus(status === s ? "" : s)}
            className={`bg-white border rounded-lg px-4 py-3 text-center hover:border-indigo-300 transition-colors ${status === s ? "border-indigo-400 ring-1 ring-indigo-300" : ""}`}
          >
            <p className="text-xs text-gray-500">{s}</p>
            <p className="text-xl font-bold mt-1">{n}</p>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          placeholder="Search title..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border rounded px-3 py-2 text-sm w-48"
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All Categories</option>
          {CATEGORIES.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {["DRAFT", "APPROVED", "OBSOLETE", "ARCHIVED"].map((s) => <option key={s}>{s}</option>)}
        </select>
        <select value={entityType} onChange={(e) => setEntityType(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All Entity Types</option>
          {Object.entries(ENTITY_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={latestOnly}
            onChange={(e) => setLatestOnly(e.target.checked)}
            className="rounded"
          />
          Latest only
        </label>
      </div>

      {/* Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400 text-center">Loading...</p>
        ) : docs.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No documents found</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Title</th>
                <th className="px-4 py-2 text-left">Category</th>
                <th className="px-4 py-2 text-left">Ver.</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Linked To</th>
                <th className="px-4 py-2 text-left">File</th>
                <th className="px-4 py-2 text-left">Created</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {docs.map((doc) => (
                <DocumentRow key={doc.id} doc={doc} onClick={() => router.push(`/dashboard/documents/${doc.id}`)} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function DocumentRow({ doc, onClick }: { doc: DocumentShort; onClick: () => void }) {
  return (
    <tr className="hover:bg-gray-50 cursor-pointer" onClick={onClick}>
      <td className="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">{doc.title}</td>
      <td className="px-4 py-3 text-gray-600 text-xs">{CATEGORY_LABELS[doc.category]}</td>
      <td className="px-4 py-3 text-gray-500 text-center font-mono text-xs">v{doc.version}</td>
      <td className="px-4 py-3">
        <Badge label={doc.status} variant={STATUS_VARIANT[doc.status]} />
      </td>
      <td className="px-4 py-3 text-xs text-gray-500">
        {doc.related_entity_type ? (
          <span className="bg-gray-100 px-2 py-0.5 rounded font-mono">
            {ENTITY_TYPE_LABELS[doc.related_entity_type] ?? doc.related_entity_type}
          </span>
        ) : (
          <span className="text-gray-300">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-gray-500 max-w-[120px] truncate">
        {doc.file_name ?? <span className="text-gray-300">—</span>}
      </td>
      <td className="px-4 py-3 text-xs text-gray-400">
        {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : ""}
      </td>
      <td className="px-4 py-3 text-right">
        <span className="text-xs text-indigo-600 hover:underline">View</span>
      </td>
    </tr>
  );
}

const DocsCompliancePage = dynamic(() => import("@/app/dashboard/documents/compliance/page"), { ssr: false });
const DocsExpiringPage   = dynamic(() => import("@/app/dashboard/documents/expiring/page"),   { ssr: false });
const KnowledgeBasePage  = dynamic(() => import("@/app/dashboard/knowledge-base/page"),       { ssr: false });
const ESignPage          = dynamic(() => import("@/app/dashboard/esign/page"),                { ssr: false });

export default function DocumentsPage() {
  const tabs = [
    { key: "documents",      label: "Documents",      permission: "documents.view", content: <DocumentsContent /> },
    { key: "compliance",     label: "Compliance",     permission: "documents.view", content: <DocsCompliancePage /> },
    { key: "expiring",       label: "Expiring",       permission: "documents.view", content: <DocsExpiringPage /> },
    { key: "knowledge-base", label: "Knowledge Base", permission: "documents.view", content: <KnowledgeBasePage /> },
    { key: "esign",          label: "E-Sign",         permission: "documents.view", content: <ESignPage /> },
  ];
  return (
    <ModuleWorkspace
      title="Documents"
      description="Document library, compliance docs, expiring alerts, knowledge base, e-sign"
      permission="documents.view"
      tabs={tabs}
      defaultTab="documents"
    />
  );
}
