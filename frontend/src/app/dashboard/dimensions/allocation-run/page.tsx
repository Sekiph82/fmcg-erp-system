"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { dimApi, AllocationRun } from "@/lib/dimensions";

export default function AllocationRunPage() {
  const today = new Date().toISOString().slice(0, 10);
  const firstOfMonth = today.slice(0, 7) + "-01";
  const [ruleId, setRuleId] = useState("");
  const [periodStart, setPeriodStart] = useState(firstOfMonth);
  const [periodEnd, setPeriodEnd] = useState(today);
  const [poolAmount, setPoolAmount] = useState("0");
  const [dryRun, setDryRun] = useState(true);
  const [result, setResult] = useState<AllocationRun | null>(null);

  const { data: rules = [] } = useQuery({
    queryKey: ["allocation-rules"],
    queryFn: () => dimApi.getAllocationRules(),
  });

  const { data: pastRuns = [] } = useQuery({
    queryKey: ["allocation-runs", ruleId],
    queryFn: () => dimApi.getAllocationRuns(ruleId || undefined),
  });

  const runAlloc = useMutation({
    mutationFn: () => (dryRun ? dimApi.previewAllocation : dimApi.postAllocation)({
      rule_id: ruleId,
      period_start: periodStart,
      period_end: periodEnd,
      source_pool_amount: Number(poolAmount),
      dry_run: dryRun,
    }),
    onSuccess: (data) => setResult(data),
  });

  const fmtCcy = (n: number) => `KES ${Number(n).toLocaleString("en-KE", { minimumFractionDigits: 2 })}`;

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">Allocation Run</h1>

      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">1. Configure Run</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2 flex flex-col gap-1">
            <label className="text-xs text-gray-500">Allocation Rule *</label>
            <select value={ruleId} onChange={(e) => setRuleId(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="">— Select Rule —</option>
              {rules.map((r) => <option key={r.id} value={r.id}>{r.rule_name}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Period Start</label>
            <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Period End</label>
            <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="col-span-2 flex flex-col gap-1">
            <label className="text-xs text-gray-500">Source Pool Amount (KES) *</label>
            <input type="number" value={poolAmount} onChange={(e) => setPoolAmount(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
          </div>
        </div>

        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} className="rounded" />
          <span className="text-sm text-gray-700">Dry Run (preview — no journal entries created)</span>
        </label>

        {!dryRun && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-xs text-orange-700">
            ⚠️ This will post actual allocation journal entries. Ensure the pool amount and targets are correct.
          </div>
        )}

        <button
          onClick={() => runAlloc.mutate()}
          disabled={runAlloc.isPending || !ruleId || !poolAmount}
          className={dryRun ? "glow-button-secondary" : "glow-button"}
        >
          {runAlloc.isPending ? "Running…" : dryRun ? "Preview Allocation" : "Post Allocation"}
        </button>
      </div>

      {result && (
        <div className="liquid-glass p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">
            {result.dry_run ? "Preview Result" : "Posting Result"}
            <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${result.dry_run ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"}`}>
              {result.status}
            </span>
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">Pool Amount</p>
              <p className="text-lg font-bold text-blue-400 mt-1">{fmtCcy(result.source_pool_amount)}</p>
            </div>
            <div className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">Total Allocated</p>
              <p className="text-lg font-bold text-green-400 mt-1">{fmtCcy(result.total_allocated)}</p>
            </div>
          </div>
          <div className="glass-table overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-blue-900/30">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Target</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">%</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Amount</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Journal Ref</th>
                </tr>
              </thead>
              <tbody>
                {result.lines.map((l) => (
                  <tr key={l.id} className="border-b border-blue-900/20">
                    <td className="px-4 py-3 text-gray-300">{l.target_dim_value_name}</td>
                    <td className="px-4 py-3 text-right text-gray-300">{Number(l.pct_applied ?? 0).toFixed(2)}%</td>
                    <td className="px-4 py-3 text-right font-medium text-indigo-300">{fmtCcy(l.allocated_amount ?? 0)}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{l.journal_entry_id ?? (result.dry_run ? "— (dry run)" : "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result.dry_run && (
            <p className="text-xs text-yellow-600">Dry run — no entries posted. Uncheck &ldquo;Dry Run&rdquo; and re-run to post.</p>
          )}
        </div>
      )}

      {pastRuns.length > 0 && (
        <div className="liquid-glass p-5 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Past Runs</h2>
          <div className="space-y-2">
            {pastRuns.map((run) => (
              <div key={run.id} className="flex items-center justify-between text-sm border-b border-blue-900/20 pb-2">
                <div>
                  <span className="text-gray-300">{run.period_start} → {run.period_end}</span>
                  <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${run.dry_run ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"}`}>
                    {run.status}
                  </span>
                </div>
                <span className="text-indigo-300">{fmtCcy(run.total_allocated)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
