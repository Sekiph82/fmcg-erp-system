"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allergenApi } from "@/lib/allergen";

export default function ChangeLogsPage() {
  const qc = useQueryClient();
  const [reviewPending, setReviewPending] = useState<boolean | undefined>(true);

  const { data: logs } = useQuery({
    queryKey: ["allergen-change-logs", reviewPending],
    queryFn: () => allergenApi.listChangeLogs({ review_pending: reviewPending }),
  });

  const mark = useMutation({
    mutationFn: ({ id, type }: { id: string; type: "label" | "qc" }) => allergenApi.markReviewed(id, type),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["allergen-change-logs"] }),
  });

  const changeTypeColors: Record<string, string> = {
    ADDED: "bg-red-100 text-red-700",
    REMOVED: "bg-blue-100 text-blue-700",
    SEVERITY_CHANGED: "bg-orange-100 text-orange-700",
    DECLARATION_CHANGED: "bg-purple-100 text-purple-700",
    MAY_CONTAIN_CHANGED: "bg-yellow-100 text-yellow-700",
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Allergen Change Logs</h1>
          <p className="text-sm text-gray-500">Track allergen changes across BOM versions — label and QC review workflow</p>
        </div>
      </div>

      <div className="flex gap-2">
        {[["Pending Review", true], ["All", undefined]].map(([label, val]) => (
          <button key={String(label)} onClick={() => setReviewPending(val as boolean | undefined)} className={`px-3 py-1 text-xs rounded border ${reviewPending === val ? "bg-gray-900 text-white" : "bg-white hover:bg-gray-50"}`}>{label as string}</button>
        ))}
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>{["Product", "Allergen", "Change", "From", "To", "Versions", "Label Review", "QC Review", "Actions"].map((h) => <th key={h} className="px-3 py-2 text-left whitespace-nowrap">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!logs?.length && <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">No allergen change logs</td></tr>}
            {logs?.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-3 py-2 font-medium">{log.product_name || "—"}</td>
                <td className="px-3 py-2">{log.allergen_name || "—"}</td>
                <td className="px-3 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${changeTypeColors[log.change_type] || "bg-gray-100 text-gray-600"}`}>{log.change_type.replace(/_/g, " ")}</span>
                </td>
                <td className="px-3 py-2 text-gray-500 text-xs">{log.old_value || "—"}</td>
                <td className="px-3 py-2 text-gray-700 text-xs">{log.new_value || "—"}</td>
                <td className="px-3 py-2 text-gray-400 text-xs">{log.bom_version_from || "?"} → {log.bom_version_to || "?"}</td>
                <td className="px-3 py-2">
                  {log.requires_label_review ? (
                    log.label_review_done ? <span className="text-green-600 text-xs">✓ Done</span> : <span className="text-orange-600 text-xs font-medium">Pending</span>
                  ) : <span className="text-gray-400 text-xs">N/A</span>}
                </td>
                <td className="px-3 py-2">
                  {log.requires_qc_review ? (
                    log.qc_review_done ? <span className="text-green-600 text-xs">✓ Done</span> : <span className="text-orange-600 text-xs font-medium">Pending</span>
                  ) : <span className="text-gray-400 text-xs">N/A</span>}
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-1">
                    {log.requires_label_review && !log.label_review_done && (
                      <button onClick={() => mark.mutate({ id: log.id, type: "label" })} disabled={mark.isPending} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded hover:bg-blue-100 disabled:opacity-50">Label ✓</button>
                    )}
                    {log.requires_qc_review && !log.qc_review_done && (
                      <button onClick={() => mark.mutate({ id: log.id, type: "qc" })} disabled={mark.isPending} className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded hover:bg-purple-100 disabled:opacity-50">QC ✓</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
