"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface DocShort {
  id: string;
  title: string;
  category: string;
  version: number;
  status: string;
  expiry_date?: string | null;
  file_name?: string | null;
  related_entity_type?: string | null;
  created_at?: string;
}

const COMPLIANCE_CATEGORIES = [
  "QC_DOCUMENT",
  "CUSTOMS_DOCUMENT",
  "HR_DOCUMENT",
  "TRADE_SPEND_APPROVAL",
  "INFLUENCER_CONTRACT",
  "SURVEY_DOCUMENT",
];

const STATUS_COLOR: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  APPROVED: "bg-green-100 text-green-700",
  OBSOLETE: "bg-red-100 text-red-600",
  ARCHIVED: "bg-gray-100 text-gray-400",
};

async function fetchDocs(category: string): Promise<DocShort[]> {
  const r = await fetch(`/api/v1/documents/?category=${category}&latest_only=true&limit=200`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export default function ComplianceDocsPage() {
  const [selectedCat, setSelectedCat] = useState("QC_DOCUMENT");
  const [docs, setDocs] = useState<DocShort[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchDocs(selectedCat).then(setDocs).catch((e) => setError(String(e))).finally(() => setLoading(false));
  }, [selectedCat]);

  const filtered = docs.filter((d) =>
    !search || d.title.toLowerCase().includes(search.toLowerCase())
  );

  const approvedCount = docs.filter((d) => d.status === "APPROVED").length;
  const draftCount = docs.filter((d) => d.status === "DRAFT").length;
  const expiredCount = docs.filter((d) => d.expiry_date && new Date(d.expiry_date) < new Date()).length;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Compliance Documents</h1>
        <p className="text-sm text-gray-500 mt-0.5">Supplier compliance, QC, customs, HR, and regulatory documents</p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Category filter tabs */}
      <div className="flex flex-wrap gap-2">
        {COMPLIANCE_CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCat(cat)}
            className={`text-xs rounded-full px-3 py-1.5 font-medium border transition-colors ${
              selectedCat === cat
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
            }`}
          >
            {cat.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Approved", value: approvedCount, color: "text-green-600" },
          { label: "Draft", value: draftCount, color: "text-gray-500" },
          { label: "Expired", value: expiredCount, color: "text-red-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white border rounded-lg p-3 shadow-sm">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Search documents…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
      />

      {/* Document list */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">
            {selectedCat.replace(/_/g, " ")}
            <span className="ml-2 font-normal text-gray-400">{filtered.length} docs</span>
          </h2>
          <Link href="/dashboard/documents/new"
            className="text-xs text-blue-600 hover:text-blue-800 font-medium">
            + Upload Document
          </Link>
        </div>

        {loading ? (
          <div className="p-6 text-sm text-gray-400 text-center">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="p-6 text-sm text-gray-400 text-center">
            No {selectedCat.replace(/_/g, " ").toLowerCase()} documents found.
            {" "}<Link href="/dashboard/documents/new" className="text-blue-500 hover:text-blue-700">Upload one.</Link>
          </div>
        ) : (
          <div className="divide-y">
            {filtered.map((d) => {
              const isExpired = d.expiry_date && new Date(d.expiry_date) < new Date();
              return (
                <div key={d.id} className="px-4 py-3 flex items-center gap-4 hover:bg-gray-50">
                  {/* File type icon */}
                  <div className="h-9 w-9 shrink-0 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{d.title}</p>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <span className="text-xs text-gray-400">v{d.version}</span>
                      {d.file_name && <span className="text-xs text-gray-400 truncate max-w-[150px]">{d.file_name}</span>}
                      {d.expiry_date && (
                        <span className={`text-xs ${isExpired ? "text-red-600 font-medium" : "text-gray-500"}`}>
                          Expires: {d.expiry_date} {isExpired && "(expired)"}
                        </span>
                      )}
                    </div>
                  </div>

                  <span className={`text-xs rounded-full px-2 py-0.5 font-medium shrink-0 ${STATUS_COLOR[d.status] ?? "bg-gray-100 text-gray-600"}`}>
                    {d.status}
                  </span>

                  <Link href={`/dashboard/documents/${d.id}`}
                    className="text-xs text-blue-600 hover:text-blue-800 shrink-0">
                    Open →
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick nav */}
      <div className="flex gap-3 flex-wrap">
        <Link href="/dashboard/documents" className="text-sm text-blue-600 hover:text-blue-800">← All Documents</Link>
        <Link href="/dashboard/documents/expiring" className="text-sm text-orange-600 hover:text-orange-800">Expiry Tracker</Link>
        <Link href="/dashboard/esign" className="text-sm text-blue-600 hover:text-blue-800">E-Signatures</Link>
      </div>
    </div>
  );
}
