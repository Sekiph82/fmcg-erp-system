"use client";

import { useRef, useState } from "react";
import { importApi, MODULE_LABELS, type ImportMode, type ImportResult } from "@/lib/importApi";
import { ImportResultView } from "./ImportResultView";

interface Props {
  module:      string;   // e.g. "products"
  onSuccess?:  () => void;
  trigger?:    React.ReactNode;  // custom trigger button; defaults to generic "Import" button
}

type Step = "idle" | "validating" | "validated" | "importing" | "done";

export function ImportModal({ module, onSuccess, trigger }: Props) {
  const [open,        setOpen]        = useState(false);
  const [step,        setStep]        = useState<Step>("idle");
  const [file,        setFile]        = useState<File | null>(null);
  const [mode,        setMode]        = useState<ImportMode>("import_valid_only");
  const [result,      setResult]      = useState<ImportResult | null>(null);
  const [error,       setError]       = useState<string | null>(null);
  const [historyId,   setHistoryId]   = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const label = MODULE_LABELS[module] ?? module;

  function reset() {
    setStep("idle");
    setFile(null);
    setResult(null);
    setError(null);
    setHistoryId(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  function close() {
    setOpen(false);
    reset();
  }

  async function handleValidate() {
    if (!file) return;
    setStep("validating");
    setError(null);
    try {
      const res = await importApi.validate(module, file);
      setResult(res);
      setStep("validated");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Validation failed");
      setStep("idle");
    }
  }

  async function handleImport() {
    if (!file) return;
    setStep("importing");
    setError(null);
    try {
      const res = await importApi.runImport(module, file, mode);
      setResult(res);
      setStep("done");
      if (res.imported && onSuccess) onSuccess();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Import failed");
      setStep("validated");
    }
  }

  function downloadErrors() {
    if (!historyId && result) {
      // If we have errors but no history id yet, build a client-side error CSV
      const rows = ["row,field,message", ...result.errors.map(
        e => `${e.row},${e.field ?? ""},${JSON.stringify(e.message)}`
      )].join("\n");
      const blob = new Blob([rows], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `errors_${module}.csv`;
      a.click(); URL.revokeObjectURL(url);
    }
  }

  return (
    <>
      {/* Trigger */}
      <span onClick={() => setOpen(true)}>
        {trigger ?? (
          <button className="flex items-center gap-1.5 rounded-lg border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06] transition-colors">
            <UploadIcon /> Import CSV
          </button>
        )}
      </span>

      {/* Backdrop + Modal */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={close} />
          <div className="relative z-10 w-full max-w-lg rounded-2xl border border-white/[0.08] bg-[#0f172a] p-6 shadow-2xl">
            {/* Header */}
            <div className="flex items-start justify-between mb-5">
              <div>
                <h2 className="text-base font-semibold text-white">Import {label}</h2>
                <p className="text-xs text-slate-500 mt-0.5">Upload a CSV file to bulk-import records.</p>
              </div>
              <button onClick={close} className="text-slate-600 hover:text-slate-300 text-xl leading-none">×</button>
            </div>

            {/* Step: idle / file selection */}
            {(step === "idle" || step === "validating") && (
              <div className="space-y-4">
                {/* Template download */}
                <div className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3">
                  <div>
                    <p className="text-sm text-slate-300 font-medium">Step 1 – Download Template</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Get the CSV template with required fields and examples.</p>
                  </div>
                  <button
                    onClick={() =>
                      importApi.downloadTemplate(module).catch((e) =>
                        setError(`Template download failed: ${e?.message ?? e}`)
                      )
                    }
                    className="shrink-0 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs text-indigo-300 hover:bg-indigo-500/20 transition-colors"
                  >
                    ↓ Template
                  </button>
                </div>

                {/* File input */}
                <div>
                  <p className="text-xs text-slate-500 mb-1.5">Step 2 – Select your CSV file</p>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".csv"
                    onChange={e => setFile(e.target.files?.[0] ?? null)}
                    className="block w-full text-xs text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-white/[0.05] file:px-3 file:py-1.5 file:text-xs file:text-slate-300 file:cursor-pointer hover:file:bg-white/[0.08] cursor-pointer"
                  />
                  {file && (
                    <p className="mt-1 text-[11px] text-slate-600">{file.name} · {(file.size / 1024).toFixed(1)} KB</p>
                  )}
                </div>

                {error && (
                  <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">{error}</p>
                )}

                <div className="flex gap-2 pt-1">
                  <button onClick={close} className="flex-1 rounded-lg border border-white/[0.07] py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                    Cancel
                  </button>
                  <button
                    onClick={handleValidate}
                    disabled={!file || step === "validating"}
                    className="flex-1 rounded-lg bg-indigo-600 py-2 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {step === "validating" ? "Validating…" : "Validate"}
                  </button>
                </div>
              </div>
            )}

            {/* Step: validated */}
            {(step === "validated" || step === "importing") && result && (
              <div className="space-y-4">
                <ImportResultView result={result} onDownloadErrors={result.failed_rows > 0 ? downloadErrors : undefined} />

                {/* Import mode selector */}
                {result.valid_rows > 0 && (
                  <div>
                    <p className="text-[11px] text-slate-500 mb-1.5">Import mode</p>
                    <div className="flex gap-2">
                      <ModeBtn current={mode} value="import_valid_only" label="Import valid rows only" onChange={setMode} />
                      <ModeBtn current={mode} value="strict"           label="Strict (abort on any error)" onChange={setMode} />
                    </div>
                  </div>
                )}

                {error && (
                  <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">{error}</p>
                )}

                <div className="flex gap-2">
                  <button onClick={reset} className="rounded-lg border border-white/[0.07] px-4 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                    ← Back
                  </button>
                  <button onClick={close} className="rounded-lg border border-white/[0.07] px-4 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                    Cancel
                  </button>
                  {result.valid_rows > 0 && (
                    <button
                      onClick={handleImport}
                      disabled={step === "importing"}
                      className="flex-1 rounded-lg bg-emerald-600 py-2 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      {step === "importing" ? "Importing…" : `Import ${result.valid_rows} row${result.valid_rows !== 1 ? "s" : ""}`}
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Step: done */}
            {step === "done" && result && (
              <div className="space-y-4">
                <ImportResultView result={result} onDownloadErrors={result.failed_rows > 0 ? downloadErrors : undefined} />
                <div className="flex gap-2">
                  <button onClick={close} className="flex-1 rounded-lg bg-indigo-600 py-2 text-xs font-medium text-white hover:bg-indigo-500 transition-colors">
                    Done
                  </button>
                  <button onClick={reset} className="rounded-lg border border-white/[0.07] px-4 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                    Import Another
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function ModeBtn({ current, value, label, onChange }: {
  current: ImportMode; value: ImportMode; label: string;
  onChange: (v: ImportMode) => void;
}) {
  const active = current === value;
  return (
    <button
      onClick={() => onChange(value)}
      className={[
        "flex-1 rounded-lg border px-2 py-1.5 text-[11px] text-left transition-colors",
        active
          ? "border-indigo-500/40 bg-indigo-500/10 text-indigo-300"
          : "border-white/[0.06] bg-white/[0.02] text-slate-500 hover:text-slate-300",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function UploadIcon() {
  return (
    <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
    </svg>
  );
}
