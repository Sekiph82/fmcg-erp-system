"use client";
import { useState } from "react";
import { spApi } from "@/lib/supplier_portal";

type ReportKey = "adoption" | "ack_time" | "eta" | "not_responding";

export default function SPReports() {
  const [active, setActive] = useState<ReportKey>("adoption");
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const REPORTS: { key: ReportKey; label: string; desc: string }[] = [
    { key: "adoption", label: "Portal Adoption", desc: "Login frequency, document uploads, active users per supplier account" },
    { key: "ack_time", label: "PO Acknowledgment Time", desc: "Response time from PO creation to supplier acknowledgment" },
    { key: "eta", label: "ETA Revision History", desc: "All ETA revision records with status and supplier reasons" },
    { key: "not_responding", label: "Non-Responding Suppliers", desc: "Suppliers with unacknowledged purchase orders" },
  ];

  const load = async (key: ReportKey) => {
    setActive(key);
    setLoading(true);
    try {
      const result = await (key === "adoption" ? spApi.reportAdoption()
        : key === "ack_time" ? spApi.reportAckTime()
        : key === "eta" ? spApi.reportETA()
        : spApi.reportNotResponding());
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const renderTable = () => {
    if (!data.length) return <p className="text-gray-400 text-sm p-4">No data available.</p>;
    const keys = Object.keys(data[0]);
    return (
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {keys.map((k) => (
              <th key={k} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">
                {k.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              {keys.map((k) => (
                <td key={k} className="px-4 py-3 text-gray-700">
                  {String(row[k] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Supplier Portal Reports</h1>
        <p className="text-sm text-gray-500 mt-1">Analytics and compliance visibility for the supplier portal</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {REPORTS.map((r) => (
          <button key={r.key} onClick={() => load(r.key)}
            className={`text-left p-4 rounded-xl border transition ${active === r.key ? "border-blue-500 bg-blue-50" : "border-gray-200 bg-white hover:border-blue-300"}`}>
            <div className="font-semibold text-gray-900 text-sm">{r.label}</div>
            <div className="text-xs text-gray-500 mt-1">{r.desc}</div>
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <span className="text-sm font-semibold text-gray-900">
            {REPORTS.find((r) => r.key === active)?.label}
          </span>
          <span className="text-xs text-gray-400">{data.length} row{data.length !== 1 ? "s" : ""}</span>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading…</div>
        ) : (
          renderTable()
        )}
      </div>
    </div>
  );
}
