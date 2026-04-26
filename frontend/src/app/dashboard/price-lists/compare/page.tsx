"use client";
import { useState, useEffect } from "react";
import { plApi, PLHeader } from "@/lib/price_list";

export default function VersionComparePage() {
  const [headers, setHeaders] = useState<PLHeader[]>([]);
  const [idA, setIdA] = useState("");
  const [idB, setIdB] = useState("");
  const [diff, setDiff] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { plApi.listHeaders().then(setHeaders); }, []);

  const compare = async () => {
    if (!idA || !idB || idA === idB) return;
    setLoading(true);
    const result = await plApi.versionCompare(idA, idB);
    setDiff(result);
    setLoading(false);
  };

  const STATUS_COLOR: Record<string, string> = {
    same: "text-gray-400",
    changed: "text-yellow-700 font-semibold",
    added: "text-green-700",
    removed: "text-red-600 line-through",
  };

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Price Version Comparison</h1>
        <p className="text-sm text-gray-500 mt-1">Compare price lines between two price list versions</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-gray-700">Price List A (base)</label>
            <select value={idA} onChange={(e) => setIdA(e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="">Select…</option>
              {headers.map((h) => <option key={h.id} value={h.id}>{h.price_list_code} — {h.price_list_name} ({h.status})</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-700">Price List B (compare)</label>
            <select value={idB} onChange={(e) => setIdB(e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="">Select…</option>
              {headers.filter((h) => h.id !== idA).map((h) => <option key={h.id} value={h.id}>{h.price_list_code} — {h.price_list_name} ({h.status})</option>)}
            </select>
          </div>
        </div>
        <button onClick={compare} disabled={!idA || !idB || loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
          {loading ? "Comparing…" : "Compare"}
        </button>
      </div>

      {diff && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">{diff.diff_lines.length} product lines compared</h2>
            <div className="flex gap-4 mt-1 text-xs text-gray-500">
              <span className="flex items-center gap-1 text-green-700">✦ {diff.diff_lines.filter((d: any) => d.status === "added").length} Added</span>
              <span className="flex items-center gap-1 text-yellow-700">↔ {diff.diff_lines.filter((d: any) => d.status === "changed").length} Changed</span>
              <span className="flex items-center gap-1 text-red-600">✕ {diff.diff_lines.filter((d: any) => d.status === "removed").length} Removed</span>
              <span className="flex items-center gap-1 text-gray-400">= {diff.diff_lines.filter((d: any) => d.status === "same").length} Same</span>
            </div>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Product ID</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Price A</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Price B</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Delta</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Delta %</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {diff.diff_lines.filter((d: any) => d.status !== "same").map((d: any) => (
                <tr key={d.product_id} className="hover:bg-gray-50">
                  <td className={`px-4 py-3 font-mono text-xs ${STATUS_COLOR[d.status]}`}>{d.product_id?.slice(0, 16)}…</td>
                  <td className="px-4 py-3 text-right font-mono">{d.price_a?.toLocaleString() ?? "—"}</td>
                  <td className="px-4 py-3 text-right font-mono">{d.price_b?.toLocaleString() ?? "—"}</td>
                  <td className={`px-4 py-3 text-right font-mono ${d.delta > 0 ? "text-red-600" : d.delta < 0 ? "text-green-600" : "text-gray-400"}`}>
                    {d.delta != null ? (d.delta > 0 ? `+${d.delta}` : d.delta) : "—"}
                  </td>
                  <td className={`px-4 py-3 text-right font-mono ${d.delta_pct > 0 ? "text-red-600" : d.delta_pct < 0 ? "text-green-600" : "text-gray-400"}`}>
                    {d.delta_pct != null ? `${d.delta_pct > 0 ? "+" : ""}${d.delta_pct}%` : "—"}
                  </td>
                  <td className={`px-4 py-3 text-center text-xs font-semibold ${STATUS_COLOR[d.status]}`}>
                    {d.status.toUpperCase()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
