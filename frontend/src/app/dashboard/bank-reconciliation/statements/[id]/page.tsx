"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import {
  brApi, BRStatementLine, BRMatch, BRAdjustment,
  LINE_STATUS_COLOR, STATUS_COLOR, ERP_TX_LABEL,
  BRERPTransactionType,
} from "@/lib/bank_reconciliation";

export default function StatementDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [matchForm, setMatchForm] = useState<{ lineId: string | null; txType: BRERPTransactionType; amount: string; ref: string; notes: string }>({
    lineId: null, txType: "AR_PAYMENT", amount: "", ref: "", notes: "",
  });
  const [adjForm, setAdjForm] = useState({ type: "BANK_CHARGE", amount: "", description: "", lineId: "" });
  const [showAdj, setShowAdj] = useState(false);

  const { data: stmt, isLoading: lStmt } = useQuery({
    queryKey: ["br-stmt", id],
    queryFn: () => brApi.getStatement(id),
  });

  const { data: lines = [], isLoading: lLines } = useQuery({
    queryKey: ["br-lines", id],
    queryFn: () => brApi.getLines(id),
  });

  const autoMatch = useMutation({
    mutationFn: () => brApi.autoMatch(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["br-lines", id] });
      qc.invalidateQueries({ queryKey: ["br-stmt", id] });
    },
  });

  const doManualMatch = useMutation({
    mutationFn: () => brApi.manualMatch(matchForm.lineId!, {
      erp_transaction_type: matchForm.txType,
      erp_reference: matchForm.ref || undefined,
      matched_amount: parseFloat(matchForm.amount),
      notes: matchForm.notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["br-lines", id] });
      setMatchForm({ lineId: null, txType: "AR_PAYMENT", amount: "", ref: "", notes: "" });
    },
  });

  const doUnmatch = useMutation({
    mutationFn: (lineId: string) => brApi.unmatch(lineId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["br-lines", id] }),
  });

  const doIgnore = useMutation({
    mutationFn: (lineId: string) => brApi.ignoreLine(lineId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["br-lines", id] }),
  });

  const doClose = useMutation({
    mutationFn: () => brApi.closeStatement(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["br-stmt", id] }),
  });

  const doLock = useMutation({
    mutationFn: () => brApi.lockStatement(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["br-stmt", id] }),
  });

  const doReopen = useMutation({
    mutationFn: () => brApi.reopenStatement(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["br-stmt", id] }),
  });

  const doAdj = useMutation({
    mutationFn: () => brApi.createAdjustment({
      statement_id: id,
      statement_line_id: adjForm.lineId || undefined,
      adjustment_type: adjForm.type,
      amount: parseFloat(adjForm.amount),
      description: adjForm.description,
    }),
    onSuccess: () => {
      setShowAdj(false);
      qc.invalidateQueries({ queryKey: ["br-adj", id] });
    },
  });

  const { data: adjustments = [] } = useQuery<BRAdjustment[]>({
    queryKey: ["br-adj", id],
    queryFn: () => brApi.listAdjustments(id),
  });

  if (lStmt || !stmt) return <p className="p-6 text-gray-400">Loading…</p>;

  const matchedLines   = lines.filter((l) => l.match_status === "MATCHED").length;
  const unmatchedLines = lines.filter((l) => l.match_status === "UNMATCHED").length;
  const partialLines   = lines.filter((l) => l.match_status === "PARTIALLY_MATCHED").length;

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{stmt.statement_no}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {stmt.period_start_date} → {stmt.period_end_date} · {stmt.statement_currency}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLOR[stmt.status]}`}>
            {stmt.status.replace(/_/g, " ")}
          </span>
          {stmt.status !== "LOCKED" && stmt.status !== "CLOSED" && (
            <button onClick={() => autoMatch.mutate()} disabled={autoMatch.isPending}
              className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50">
              {autoMatch.isPending ? "Matching…" : "Auto-Match"}
            </button>
          )}
          {autoMatch.data && (
            <span className="text-xs text-green-700 bg-green-50 px-2 py-1 rounded">
              {(autoMatch.data as { auto_applied: number; suggestions_created: number }).auto_applied} applied,{" "}
              {(autoMatch.data as { auto_applied: number; suggestions_created: number }).suggestions_created} suggested
            </span>
          )}
          <button onClick={() => setShowAdj(true)}
            className="px-3 py-1.5 text-xs bg-yellow-600 text-white rounded-lg hover:bg-yellow-700">
            Add Adjustment
          </button>
          {(stmt.status === "IN_RECONCILIATION" || stmt.status === "IMPORTED" || stmt.status === "RECONCILED") && (
            <button onClick={() => doClose.mutate()} disabled={doClose.isPending}
              className="px-3 py-1.5 text-xs bg-gray-700 text-white rounded-lg hover:bg-gray-800">
              Close
            </button>
          )}
          {stmt.status === "CLOSED" && (
            <button onClick={() => doLock.mutate()} disabled={doLock.isPending}
              className="px-3 py-1.5 text-xs bg-gray-900 text-white rounded-lg">
              Lock
            </button>
          )}
          {(stmt.status === "CLOSED" || stmt.status === "LOCKED") && (
            <button onClick={() => doReopen.mutate()} disabled={doReopen.isPending}
              className="px-3 py-1.5 text-xs border rounded-lg text-gray-600 hover:bg-gray-50">
              Reopen
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: "Opening", value: Number(stmt.opening_balance).toLocaleString(undefined, { minimumFractionDigits: 2 }) },
          { label: "Closing", value: Number(stmt.closing_balance).toLocaleString(undefined, { minimumFractionDigits: 2 }) },
          { label: "Total Lines", value: stmt.total_lines },
          { label: "Matched", value: matchedLines, cls: "text-green-700" },
          { label: "Unmatched", value: unmatchedLines + partialLines, cls: unmatchedLines + partialLines > 0 ? "text-red-600" : "text-green-600" },
        ].map((s) => (
          <div key={s.label} className="bg-white border rounded-xl p-3">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-xl font-bold mt-0.5 ${s.cls ?? "text-gray-900"}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Adjustment modal */}
      {showAdj && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 space-y-3">
          <h3 className="text-sm font-semibold text-yellow-800">Add Adjustment</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-gray-500">Type</label>
              <select value={adjForm.type} onChange={(e) => setAdjForm({ ...adjForm, type: e.target.value })}
                className="mt-1 w-full border rounded px-2 py-1.5 text-sm">
                {["BANK_CHARGE", "INTEREST", "ROUNDING", "FX_DIFFERENCE", "WRITE_OFF", "OTHER"].map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Amount</label>
              <input type="number" value={adjForm.amount} onChange={(e) => setAdjForm({ ...adjForm, amount: e.target.value })}
                className="mt-1 w-full border rounded px-2 py-1.5 text-sm" />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500">Description</label>
              <input type="text" value={adjForm.description} onChange={(e) => setAdjForm({ ...adjForm, description: e.target.value })}
                className="mt-1 w-full border rounded px-2 py-1.5 text-sm" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => doAdj.mutate()} disabled={doAdj.isPending || !adjForm.amount || !adjForm.description}
              className="px-4 py-1.5 text-xs bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50">
              Save
            </button>
            <button onClick={() => setShowAdj(false)} className="text-xs text-gray-500 hover:underline">Cancel</button>
          </div>
        </div>
      )}

      {/* Lines workspace */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">Statement Lines — Reconciliation Workspace</h2>
        </div>
        {lLines ? (
          <p className="p-4 text-gray-400 text-sm">Loading…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  {["#", "Date", "D/C", "Amount", "Unmatched", "Narration / Ref", "Status", "Actions"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {lines.map((l: BRStatementLine) => (
                  <tr key={l.id} className={`hover:bg-gray-50 ${l.is_duplicate_suspected ? "bg-red-50" : ""}`}>
                    <td className="px-3 py-2 text-gray-400 text-xs">{l.line_no}</td>
                    <td className="px-3 py-2 text-xs">{l.transaction_date}</td>
                    <td className="px-3 py-2">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${l.debit_credit_indicator === "C" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {l.debit_credit_indicator === "C" ? "CR" : "DR"}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-medium">{Number(l.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className="px-3 py-2 font-medium text-red-600">
                      {Number(l.unmatched_amount) > 0 ? Number(l.unmatched_amount).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "—"}
                    </td>
                    <td className="px-3 py-2 text-xs max-w-xs">
                      <p className="truncate text-gray-700">{l.narration || "—"}</p>
                      {l.external_reference && <p className="text-gray-400 truncate">{l.external_reference}</p>}
                      {l.is_duplicate_suspected && <p className="text-red-500 text-xs">⚠ Duplicate suspected</p>}
                    </td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${LINE_STATUS_COLOR[l.match_status]}`}>
                        {l.match_status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1 flex-wrap">
                        {l.match_status !== "MATCHED" && l.match_status !== "IGNORED" && stmt.status !== "LOCKED" && (
                          <button onClick={() => setMatchForm({ lineId: l.id, txType: "AR_PAYMENT", amount: String(l.unmatched_amount), ref: "", notes: "" })}
                            className="text-xs px-2 py-0.5 bg-blue-600 text-white rounded hover:bg-blue-700">
                            Match
                          </button>
                        )}
                        {l.match_status !== "UNMATCHED" && l.match_status !== "IGNORED" && (
                          <button onClick={() => doUnmatch.mutate(l.id)}
                            className="text-xs px-2 py-0.5 border rounded text-gray-600 hover:bg-gray-50">
                            Unmatch
                          </button>
                        )}
                        {l.match_status !== "IGNORED" && stmt.status !== "LOCKED" && (
                          <button onClick={() => doIgnore.mutate(l.id)}
                            className="text-xs px-2 py-0.5 border rounded text-gray-500 hover:bg-gray-50">
                            Ignore
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {lines.length === 0 && (
                  <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400 text-sm">No lines. Import or add lines.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Manual match panel */}
      {matchForm.lineId && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-3">
          <h3 className="text-sm font-semibold text-blue-800">Manual Match</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-gray-500">ERP Transaction Type</label>
              <select value={matchForm.txType}
                onChange={(e) => setMatchForm({ ...matchForm, txType: e.target.value as BRERPTransactionType })}
                className="mt-1 w-full border rounded px-2 py-1.5 text-sm">
                {Object.entries(ERP_TX_LABEL).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Matched Amount</label>
              <input type="number" value={matchForm.amount}
                onChange={(e) => setMatchForm({ ...matchForm, amount: e.target.value })}
                className="mt-1 w-full border rounded px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="text-xs text-gray-500">ERP Reference</label>
              <input type="text" value={matchForm.ref}
                onChange={(e) => setMatchForm({ ...matchForm, ref: e.target.value })}
                className="mt-1 w-full border rounded px-2 py-1.5 text-sm" placeholder="Optional" />
            </div>
            <div>
              <label className="text-xs text-gray-500">Notes</label>
              <input type="text" value={matchForm.notes}
                onChange={(e) => setMatchForm({ ...matchForm, notes: e.target.value })}
                className="mt-1 w-full border rounded px-2 py-1.5 text-sm" placeholder="Optional" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => doManualMatch.mutate()}
              disabled={doManualMatch.isPending || !matchForm.amount}
              className="px-4 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
              Confirm Match
            </button>
            <button onClick={() => setMatchForm({ lineId: null, txType: "AR_PAYMENT", amount: "", ref: "", notes: "" })}
              className="text-xs text-gray-500 hover:underline">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Adjustments */}
      {adjustments.length > 0 && (
        <div className="bg-white border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">Adjustments ({adjustments.length})</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Type", "Amount", "Description", "Posted", ""].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {adjustments.map((a: BRAdjustment) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-xs">{a.adjustment_type.replace(/_/g, " ")}</td>
                  <td className="px-4 py-2 font-medium">{Number(a.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-2 text-gray-600">{a.description}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${a.posted ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {a.posted ? "Posted" : "Draft"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {!a.posted && (
                      <button onClick={() => brApi.postAdjustment(a.id).then(() => qc.invalidateQueries({ queryKey: ["br-adj", id] }))}
                        className="text-xs text-blue-600 hover:underline">
                        Post
                      </button>
                    )}
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
