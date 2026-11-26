"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { imApi, DuplicateLog, DuplicateRisk } from "@/lib/invoice_match";
import { tx } from "@/lib/i18n/core";

const RISK_COLOR: Record<DuplicateRisk, string> = {
  EXACT:     "bg-red-100 text-red-700",
  SUSPECTED: "bg-orange-100 text-orange-700",
  LOW:       "bg-yellow-100 text-yellow-700",
};

export default function DuplicatesPage() {
  const qc = useQueryClient();
  const [resolver, setResolver] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});

  const { data = [], isLoading } = useQuery<DuplicateLog[]>({
    queryKey: ["im-duplicates"],
    queryFn: () => imApi.getDuplicateSuspicions(),
  });

  const resolve = useMutation({
    mutationFn: ({ id }: { id: string }) =>
      imApi.resolveDuplicate(id, resolver, notes[id] ?? ""),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["im-duplicates"] }),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Duplicate Invoice Review")}</h1>
          <p className="text-sm text-gray-500 mt-1">{tx("Invoices flagged for potential duplication")}</p>
        </div>
        <span className={`text-lg font-bold ${data.length > 0 ? "text-red-600" : "text-green-600"}`}>
          {data.length} {tx("unresolved")}
        </span>
      </div>

      <div className="flex gap-2 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">{tx("Resolver Name")}</label>
          <input className="border rounded-lg px-3 py-1.5 text-sm w-48"
            placeholder={tx("Your name")}
            value={resolver} onChange={(e) => setResolver(e.target.value)} />
        </div>
      </div>

      {isLoading ? (
        <p className="text-gray-400">{tx("Loading…")}</p>
      ) : data.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
          <p className="text-green-700 font-medium">{tx("✓ No unresolved duplicate suspicions.")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((dup) => (
            <div key={dup.id} className="bg-white border rounded-xl p-5 space-y-3">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${RISK_COLOR[dup.duplicate_risk]}`}>
                      {dup.duplicate_risk} DUPLICATE
                    </span>
                    {dup.similarity_score != null && (
                      <span className="text-xs text-gray-400">
                        {tx("Similarity:")} {Math.round(Number(dup.similarity_score) * 100)}%
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-gray-800">
                    {tx("Invoice:")} <span className="font-mono">{dup.invoice_no ?? "—"}</span>
                    {" "}{tx("matches")}{" "}
                    <span className="font-mono">{dup.matched_invoice_no ?? "—"}</span>
                  </p>
                  {dup.match_reasons && (
                    <p className="text-xs text-gray-500">
                      {tx("Matched on:")} {(dup.match_reasons as string[]).join(", ")}
                    </p>
                  )}
                </div>
                {!dup.is_resolved && (
                  <div className="flex flex-col gap-2">
                    <input
                      className="border rounded-lg px-3 py-1.5 text-sm w-64"
                      placeholder={tx("Resolution notes")}
                      value={notes[dup.id] ?? ""}
                      onChange={(e) => setNotes({ ...notes, [dup.id]: e.target.value })}
                    />
                    <button
                      onClick={() => resolve.mutate({ id: dup.id })}
                      disabled={!resolver || resolve.isPending}
                      className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      {tx("Mark Resolved")}
                    </button>
                  </div>
                )}
                {dup.is_resolved && (
                  <span className="text-xs text-green-600 font-medium">
                    {tx("✓ Resolved by")} {dup.resolved_by}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400">{tx("Detected")} {new Date(dup.created_at).toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
