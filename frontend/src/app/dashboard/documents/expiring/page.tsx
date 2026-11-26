"use client";
import { apiFetch } from "@/lib/api";
import { useEffect, useState } from "react";
import Link from "next/link";
import { tx } from "@/lib/i18n/core";

interface ExpiringDoc {
  id: string;
  title: string;
  category: string;
  version: number;
  expiry_date: string | null;
  status: string;
  days_until_expiry: number | null;
  expired: boolean;
  file_name: string | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
}

async function fetchExpiring(days: number): Promise<ExpiringDoc[]> {
  const r = await apiFetch(`/api/v1/documents/expiring/list?days=${days}&include_expired=true`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function urgencyColor(days: number | null, expired: boolean): string {
  if (expired) return "text-red-600 bg-red-100";
  if (days === null) return "text-gray-500";
  if (days <= 7) return "text-red-600 bg-red-100";
  if (days <= 30) return "text-orange-600 bg-orange-100";
  return "text-amber-600 bg-amber-100";
}

function urgencyLabel(days: number | null, expired: boolean): string {
  if (expired) return "Expired";
  if (days === null) return "—";
  if (days === 0) return tx("Expires today");
  if (days < 0) return tx("Expired {days}d ago", { days: Math.abs(days) });
  return `${days}d left`;
}

export default function ExpiringDocumentsPage() {
  const [docs, setDocs] = useState<ExpiringDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    fetchExpiring(days).then(setDocs).catch((e) => setError(String(e))).finally(() => setLoading(false));
  };

  useEffect(load, [days]);

  const expired = docs.filter((d) => d.expired);
  const expiringSoon = docs.filter((d) => !d.expired);

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Document Expiry Tracker")}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{tx("Monitor approved documents approaching or past expiry")}</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none"
          >
            <option value={7}>{tx("Next 7 days")}</option>
            <option value={30}>{tx("Next 30 days")}</option>
            <option value={60}>{tx("Next 60 days")}</option>
            <option value={90}>{tx("Next 90 days")}</option>
          </select>
          <button onClick={load} disabled={loading}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
            {tx("Refresh")}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {[
          { label: tx("Expired"), value: expired.length, color: "text-red-600" },
          { label: tx("Expiring in {days}d", { days }), value: expiringSoon.length, color: "text-orange-500" },
          { label: tx("Total At Risk"), value: docs.length, color: "text-gray-700" },
        ].map((k) => (
          <div key={k.label} className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">{tx("Loading…")}</p>
      ) : docs.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <p className="text-green-700 font-semibold">{tx("All clear")}</p>
          <p className="text-green-600 text-sm mt-1">{tx("No documents expiring in the next")} {days} {tx("days.")}</p>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">{tx("Documents Requiring Attention")}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">{tx("Title")}</th>
                  <th className="text-left px-4 py-2">{tx("Category")}</th>
                  <th className="text-left px-4 py-2">{tx("v")}</th>
                  <th className="text-left px-4 py-2">{tx("Expiry Date")}</th>
                  <th className="text-left px-4 py-2">{tx("Status")}</th>
                  <th className="text-left px-4 py-2">{tx("Linked To")}</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {docs.map((d) => (
                  <tr key={d.id} className={d.expired ? "bg-red-50" : ""}>
                    <td className="px-4 py-2.5 font-medium text-gray-900 max-w-[200px] truncate">{d.title}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-600">{d.category.replace(/_/g, " ")}</td>
                    <td className="px-4 py-2.5 text-gray-400">{tx("v")}{d.version}</td>
                    <td className="px-4 py-2.5">
                      {d.expiry_date && (
                        <div className="flex items-center gap-2">
                          <span className="text-gray-700">{d.expiry_date}</span>
                          <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${urgencyColor(d.days_until_expiry, d.expired)}`}>
                            {urgencyLabel(d.days_until_expiry, d.expired)}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="text-xs text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">{d.status}</span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-400">
                      {d.related_entity_type ? `${d.related_entity_type.replace(/_/g, " ")} / ${d.related_entity_id?.slice(0, 8)}…` : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <Link href={`/dashboard/documents/${d.id}`}
                        className="text-xs text-blue-600 hover:text-blue-800">
                        {tx("View")}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
        <p className="font-semibold mb-1">{tx("Renewal Workflow")}</p>
        <p className="text-xs">
          {tx("For each expiring document: open the document, upload a new version via")}{" "}
          <strong>{tx("+ New Version")}</strong>{tx(", then approve the new version. The old version is automatically marked obsolete. Set a new expiry date during approval.")}
        </p>
      </div>
    </div>
  );
}
