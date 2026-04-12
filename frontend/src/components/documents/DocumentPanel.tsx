"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { docsApi, CATEGORY_LABELS, DocumentShort, DocumentStatus } from "@/lib/documents";
import { Badge } from "@/components/ui/Badge";

const STATUS_VARIANT: Record<DocumentStatus, "yellow" | "green" | "gray" | "red"> = {
  DRAFT: "yellow",
  APPROVED: "green",
  OBSOLETE: "gray",
  ARCHIVED: "red",
};

interface DocumentPanelProps {
  /** e.g. "mpesa_transaction", "purchase_order", "invoice" */
  entityType: string;
  /** UUID string of the linked record */
  entityId: string;
  /** Show a compact collapsed view — user can expand */
  collapsible?: boolean;
  /** Optional label override for the panel header */
  title?: string;
}

/**
 * Embeddable document panel.
 * Drop into any module detail page to show/add documents linked to a specific ERP record.
 *
 * Usage:
 *   <DocumentPanel entityType="mpesa_transaction" entityId={tx.id} />
 *   <DocumentPanel entityType="invoice"           entityId={invoice.id} />
 *   <DocumentPanel entityType="purchase_order"    entityId={po.id} />
 */
export function DocumentPanel({
  entityType,
  entityId,
  collapsible = true,
  title = "Documents",
}: DocumentPanelProps) {
  const [open, setOpen] = useState(!collapsible);

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["docs-panel", entityType, entityId],
    queryFn: () => docsApi.listByEntity(entityType, entityId),
    enabled: open && !!entityId,
  });

  const addUrl = `/dashboard/documents/new?entity_type=${entityType}&entity_id=${entityId}`;

  return (
    <div className="bg-white border rounded-lg overflow-hidden">
      {/* Header */}
      <div
        className={`flex items-center justify-between px-4 py-3 bg-gray-50 border-b ${collapsible ? "cursor-pointer hover:bg-gray-100" : ""}`}
        onClick={collapsible ? () => setOpen((o) => !o) : undefined}
      >
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="text-sm font-semibold text-gray-700">{title}</span>
          {docs.length > 0 && (
            <span className="text-xs bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded-full">
              {docs.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={addUrl}
            onClick={(e) => e.stopPropagation()}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
          >
            + Add
          </Link>
          {collapsible && (
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          )}
        </div>
      </div>

      {/* Body */}
      {open && (
        <div>
          {isLoading ? (
            <p className="p-4 text-xs text-gray-400 text-center">Loading documents…</p>
          ) : docs.length === 0 ? (
            <div className="p-4 text-center">
              <p className="text-xs text-gray-400">No documents attached</p>
              <Link
                href={addUrl}
                className="mt-2 inline-block text-xs text-indigo-600 hover:underline"
              >
                Attach a document →
              </Link>
            </div>
          ) : (
            <ul className="divide-y">
              {docs.map((doc) => (
                <DocumentPanelRow key={doc.id} doc={doc} />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function DocumentPanelRow({ doc }: { doc: DocumentShort }) {
  return (
    <li className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50">
      {/* File icon */}
      <svg className="w-4 h-4 text-gray-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>

      <div className="flex-1 min-w-0">
        <Link href={`/dashboard/documents/${doc.id}`} className="text-sm font-medium text-gray-800 hover:text-indigo-600 truncate block">
          {doc.title}
        </Link>
        <p className="text-xs text-gray-400 mt-0.5">
          {CATEGORY_LABELS[doc.category]} · v{doc.version}
          {doc.file_name && ` · ${doc.file_name}`}
        </p>
      </div>

      <Badge label={doc.status} variant={STATUS_VARIANT[doc.status]} />
    </li>
  );
}
