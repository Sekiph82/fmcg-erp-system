"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { faApi, FADeprPostResult, fmtCurrency } from "@/lib/fixed_assets";

export default function FAPostingRunPage() {
  const today = new Date().toISOString().slice(0, 10);
  const firstOfMonth = today.slice(0, 7) + "-01";
  const [periodStart, setPeriodStart] = useState(firstOfMonth);
  const [periodEnd,   setPeriodEnd]   = useState(today);
  const [dryRun,      setDryRun]      = useState(true);
  const [result,      setResult]      = useState<FADeprPostResult | null>(null);

  const post = useMutation({
    mutationFn: () => faApi.postDepreciation({ period_start: periodStart, period_end: periodEnd, dry_run: dryRun }),
    onSuccess: (data) => setResult(data),
  });

  const generate = useMutation({
    mutationFn: () => faApi.generateSchedule({ through_date: periodEnd }),
  });

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Depreciation Posting Run</h1>

      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">1. Generate Schedules (if needed)</h2>
        <p className="text-xs text-gray-500">
          Regenerates PLANNED schedule lines for all active assets through the selected end date.
          Already-posted lines are preserved.
        </p>
        <div className="flex items-center gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Through Date</label>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="glow-button-secondary self-end"
          >
            {generate.isPending ? "Generating…" : "Generate Schedules"}
          </button>
        </div>
        {generate.isSuccess && (
          <p className="text-sm text-green-600">
            ✓ Generated schedule lines successfully.
          </p>
        )}
      </div>

      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">2. Post Depreciation</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Period Start</label>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Period End</label>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
            className="rounded"
          />
          <span className="text-sm text-gray-700">Dry Run (preview only — no GL posting)</span>
        </label>

        <button
          onClick={() => post.mutate()}
          disabled={post.isPending}
          className={dryRun ? "glow-button-secondary" : "glow-button"}
        >
          {post.isPending
            ? "Running…"
            : dryRun
            ? "Preview (Dry Run)"
            : "Post Depreciation"}
        </button>

        {!dryRun && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-xs text-orange-700">
            ⚠️ This will post actual depreciation entries and update Net Book Values. Ensure all schedule lines are correct before proceeding.
          </div>
        )}
      </div>

      {result && (
        <div className="liquid-glass p-5 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">
            {result.dry_run ? "Preview Results" : "Posting Results"}
          </h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            {[
              { label: "Assets Processed", value: result.total_assets, color: "text-blue-600" },
              { label: "Lines Posted",     value: result.total_posted, color: "text-green-600" },
              { label: "Total Amount",     value: fmtCurrency(result.total_amount), color: "text-orange-600" },
            ].map((r) => (
              <div key={r.label} className="glow-card p-3">
                <p className="text-xs text-gray-500">{r.label}</p>
                <p className={`text-lg font-bold mt-1 ${r.color}`}>{r.value}</p>
              </div>
            ))}
          </div>
          {result.failed.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-xs font-semibold text-red-700 mb-1">Failed ({result.failed.length}):</p>
              {result.failed.map((f, i) => (
                <p key={i} className="text-xs text-red-600">{f}</p>
              ))}
            </div>
          )}
          {result.dry_run && (
            <p className="text-xs text-yellow-600">
              This was a dry run. Set &quot;Dry Run&quot; off and re-run to post actual entries.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
