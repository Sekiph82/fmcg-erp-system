"use client";

import type { ImportResult, ImportRowError } from "@/lib/importApi";

interface Props {
  result: ImportResult;
  onDownloadErrors?: () => void;
}

export function ImportResultView({ result, onDownloadErrors }: Props) {
  const hasErrors = result.errors.length > 0;

  return (
    <div className="space-y-4">
      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Total Rows"   value={result.total_rows}  color="text-slate-300" />
        <Stat label="Valid"        value={result.valid_rows}   color="text-emerald-400" />
        <Stat label="Failed"       value={result.failed_rows}  color={result.failed_rows > 0 ? "text-red-400" : "text-slate-500"} />
      </div>

      {/* State banner */}
      {result.imported && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5 text-sm text-emerald-300">
          ✓ {result.valid_rows} record{result.valid_rows !== 1 ? "s" : ""} imported successfully.
          {result.failed_rows > 0 && ` ${result.failed_rows} row${result.failed_rows !== 1 ? "s" : ""} skipped due to errors.`}
        </div>
      )}

      {!result.imported && !hasErrors && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5 text-sm text-emerald-300">
          ✓ All {result.total_rows} rows are valid and ready to import.
        </div>
      )}

      {/* Error table */}
      {hasErrors && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
              Row Errors ({result.errors.length})
            </p>
            {onDownloadErrors && (
              <button
                onClick={onDownloadErrors}
                className="text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                ↓ Download Error CSV
              </button>
            )}
          </div>
          <div className="max-h-64 overflow-y-auto rounded-xl border border-white/[0.06]">
            <table className="w-full text-left text-[12px]">
              <thead className="sticky top-0 bg-[#0b1120] border-b border-white/[0.06]">
                <tr>
                  <th className="px-3 py-2 text-slate-500 font-medium w-16">Row</th>
                  <th className="px-3 py-2 text-slate-500 font-medium w-32">Field</th>
                  <th className="px-3 py-2 text-slate-500 font-medium">Error</th>
                </tr>
              </thead>
              <tbody>
                {result.errors.map((e, i) => (
                  <ErrorRow key={i} error={e} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 text-center">
      <p className="text-[10px] uppercase tracking-widest text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold leading-none ${color}`}>{value}</p>
    </div>
  );
}

function ErrorRow({ error }: { error: ImportRowError }) {
  return (
    <tr className="border-b border-white/[0.04] hover:bg-white/[0.02]">
      <td className="px-3 py-2 font-mono text-slate-400">{error.row}</td>
      <td className="px-3 py-2 text-slate-500 truncate max-w-[120px]">{error.field ?? "—"}</td>
      <td className="px-3 py-2 text-red-400">{error.message}</td>
    </tr>
  );
}
