"use client";

/**
 * RecipeBulkImportModal
 * ─────────────────────
 * Single "Import Recipes / BOM" button that opens a tabbed modal supporting
 * bulk-import of all three recipe CSV types:
 *
 *   Tab 1 – Recipe Headers   (module: "recipes")
 *   Tab 2 – BOM Items        (module: "recipe_items")
 *   Tab 3 – Process Steps    (module: "recipe_steps")
 *
 * Import order matters:
 *   1. Import Recipe Headers first (creates DRAFT recipes)
 *   2. Then import BOM Items and Process Steps (linked via product_sku + version)
 *
 * Update behaviour for BOM Items and Process Steps:
 *   - If a row with the same recipe + line_no / step_no already exists → UPDATED.
 *   - If not → INSERTED.
 *   - Only DRAFT recipes can receive new or updated lines/steps.
 */

import { useRef, useState } from "react";
import { importApi, type ImportMode, type ImportResult } from "@/lib/importApi";
import { ImportResultView } from "./ImportResultView";

type Tab = "headers" | "items" | "steps";
type Step = "idle" | "validating" | "validated" | "importing" | "done";

interface TabState {
  step:    Step;
  file:    File | null;
  result:  ImportResult | null;
  error:   string | null;
  mode:    ImportMode;
}

const EMPTY_TAB: TabState = {
  step: "idle", file: null, result: null, error: null, mode: "import_valid_only",
};

const TAB_CONFIG = {
  headers: {
    label:       "Recipe Headers",
    module:      "recipes",
    filename:    "recipe_headers_template.csv",
    description: "Create or identify recipes. Each row is one recipe for a finished product.",
    fields:      "*product_sku, *version, *name, description, is_active, valid_from, valid_to",
    example:     "product_sku: HH-001 · version: v1.0 · name: Hand-Wash Powder 20g",
    note:        null,
  },
  items: {
    label:       "BOM Items",
    module:      "recipe_items",
    filename:    "recipe_items_template.csv",
    description: "Add or update BOM / Formulation Items for DRAFT recipes.",
    fields:      "*product_sku, *version, *line_no, *material_code, *quantity, *unit, loss_percent, optional, alternative_group, notes",
    example:     "product_sku: HH-001 · version: v1.0 · line_no: 1 · material_code: MAT001 · quantity: 120 · unit: KG",
    note:        "Recipe headers must be imported (or already exist as DRAFT) before BOM items.",
  },
  steps: {
    label:       "Process Steps",
    module:      "recipe_steps",
    filename:    "recipe_steps_template.csv",
    description: "Add or update Process Parameters / steps for DRAFT recipes.",
    fields:      "*product_sku, *version, *step_no, *step_name, temperature_c, target_ph, viscosity_cp, mix_time_min, rpm, notes",
    example:     "product_sku: HH-001 · version: v1.0 · step_no: 1 · step_name: Dry Premix · mix_time_min: 15 · rpm: 120",
    note:        "Recipe headers must be imported (or already exist as DRAFT) before process steps.",
  },
} as const;

interface Props {
  onSuccess?: () => void;
}

export function RecipeBulkImportModal({ onSuccess }: Props) {
  const [open,    setOpen]    = useState(false);
  const [tab,     setTab]     = useState<Tab>("headers");
  const [states,  setStates]  = useState<Record<Tab, TabState>>({
    headers: { ...EMPTY_TAB },
    items:   { ...EMPTY_TAB },
    steps:   { ...EMPTY_TAB },
  });

  const fileRefs = {
    headers: useRef<HTMLInputElement>(null),
    items:   useRef<HTMLInputElement>(null),
    steps:   useRef<HTMLInputElement>(null),
  };

  function setTabState(t: Tab, patch: Partial<TabState>) {
    setStates(prev => ({ ...prev, [t]: { ...prev[t], ...patch } }));
  }

  function resetTab(t: Tab) {
    setTabState(t, { ...EMPTY_TAB });
    if (fileRefs[t].current) fileRefs[t].current!.value = "";
  }

  function close() {
    setOpen(false);
    setTab("headers");
    (["headers", "items", "steps"] as Tab[]).forEach(resetTab);
  }

  async function handleValidate(t: Tab) {
    const s = states[t];
    if (!s.file) return;
    setTabState(t, { step: "validating", error: null });
    try {
      const result = await importApi.validate(TAB_CONFIG[t].module, s.file);
      setTabState(t, { step: "validated", result });
    } catch (e: any) {
      setTabState(t, {
        step:  "idle",
        error: e?.response?.data?.detail ?? "Validation failed",
      });
    }
  }

  async function handleImport(t: Tab) {
    const s = states[t];
    if (!s.file) return;
    setTabState(t, { step: "importing", error: null });
    try {
      const result = await importApi.runImport(TAB_CONFIG[t].module, s.file, s.mode);
      setTabState(t, { step: "done", result });
      if (result.imported && onSuccess) onSuccess();
    } catch (e: any) {
      setTabState(t, {
        step:  "validated",
        error: e?.response?.data?.detail ?? "Import failed",
      });
    }
  }

  function downloadErrors(t: Tab) {
    const result = states[t].result;
    if (!result) return;
    const rows = [
      "row,field,message",
      ...result.errors.map(
        e => `${e.row},${e.field ?? ""},${JSON.stringify(e.message)}`
      ),
    ].join("\n");
    const blob = new Blob([rows], { type: "text/csv" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url;
    a.download = `errors_${TAB_CONFIG[t].module}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const cfg = TAB_CONFIG[tab];
  const s   = states[tab];

  return (
    <>
      {/* Trigger */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 rounded-lg border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06] transition-colors"
      >
        <UploadIcon /> Import Recipes / BOM
      </button>

      {/* Modal */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={close} />

          <div className="relative z-10 w-full max-w-2xl rounded-2xl border border-white/[0.08] bg-[#0f172a] shadow-2xl flex flex-col max-h-[90vh]">

            {/* Header */}
            <div className="flex items-start justify-between px-6 pt-5 pb-4 border-b border-white/[0.06] shrink-0">
              <div>
                <h2 className="text-base font-semibold text-white">Bulk Import — Recipes / BOM</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Import recipe headers first, then BOM items and process steps.
                </p>
              </div>
              <button onClick={close} className="text-slate-600 hover:text-slate-300 text-xl leading-none ml-4">×</button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/[0.06] px-6 shrink-0">
              {(["headers", "items", "steps"] as Tab[]).map(t => {
                const done    = states[t].step === "done";
                const hasFile = !!states[t].file;
                return (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={[
                      "py-3 px-4 text-xs font-medium border-b-2 -mb-px transition-colors relative",
                      tab === t
                        ? "border-indigo-500 text-indigo-300"
                        : "border-transparent text-slate-500 hover:text-slate-300",
                    ].join(" ")}
                  >
                    {TAB_CONFIG[t].label}
                    {done && (
                      <span className="ml-1.5 inline-flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-500/20 text-[9px] text-emerald-400">✓</span>
                    )}
                    {hasFile && !done && (
                      <span className="ml-1.5 inline-flex h-1.5 w-1.5 rounded-full bg-amber-400" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

              {/* Description + fields reference */}
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 space-y-1.5">
                <p className="text-xs text-slate-300 font-medium">{cfg.description}</p>
                <p className="text-[11px] text-slate-500 font-mono leading-relaxed">{cfg.fields}</p>
                <p className="text-[11px] text-slate-600 italic">{cfg.example}</p>
              </div>

              {/* Dependency note */}
              {cfg.note && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-300">
                  ⚠ {cfg.note}
                </div>
              )}

              {/* Step: idle / validating */}
              {(s.step === "idle" || s.step === "validating") && (
                <div className="space-y-4">
                  {/* Template download */}
                  <div className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3">
                    <div>
                      <p className="text-sm text-slate-300 font-medium">Step 1 – Download Template</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        CSV template with headers, type hints and example rows.
                      </p>
                    </div>
                    <button
                      onClick={() =>
                        importApi.downloadTemplate(cfg.module).catch(e =>
                          setTabState(tab, { error: `Template download failed: ${e?.message ?? e}` })
                        )
                      }
                      className="shrink-0 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs text-indigo-300 hover:bg-indigo-500/20 transition-colors"
                    >
                      ↓ Template
                    </button>
                  </div>

                  {/* File picker */}
                  <div>
                    <p className="text-xs text-slate-500 mb-1.5">Step 2 – Select your CSV file</p>
                    <input
                      ref={fileRefs[tab]}
                      type="file"
                      accept=".csv"
                      onChange={e => setTabState(tab, { file: e.target.files?.[0] ?? null })}
                      className="block w-full text-xs text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-white/[0.05] file:px-3 file:py-1.5 file:text-xs file:text-slate-300 file:cursor-pointer hover:file:bg-white/[0.08] cursor-pointer"
                    />
                    {s.file && (
                      <p className="mt-1 text-[11px] text-slate-600">
                        {s.file.name} · {(s.file.size / 1024).toFixed(1)} KB
                      </p>
                    )}
                  </div>

                  {s.error && (
                    <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">{s.error}</p>
                  )}

                  <div className="flex gap-2 pt-1">
                    <button onClick={close} className="flex-1 rounded-lg border border-white/[0.07] py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                      Cancel
                    </button>
                    <button
                      onClick={() => handleValidate(tab)}
                      disabled={!s.file || s.step === "validating"}
                      className="flex-1 rounded-lg bg-indigo-600 py-2 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      {s.step === "validating" ? "Validating…" : "Validate"}
                    </button>
                  </div>
                </div>
              )}

              {/* Step: validated / importing */}
              {(s.step === "validated" || s.step === "importing") && s.result && (
                <div className="space-y-4">
                  <ImportResultView
                    result={s.result}
                    onDownloadErrors={s.result.failed_rows > 0 ? () => downloadErrors(tab) : undefined}
                  />

                  {s.result.valid_rows > 0 && (
                    <div>
                      <p className="text-[11px] text-slate-500 mb-1.5">Import mode</p>
                      <div className="flex gap-2">
                        <ModeBtn current={s.mode} value="import_valid_only" label="Import valid rows only"    onChange={m => setTabState(tab, { mode: m })} />
                        <ModeBtn current={s.mode} value="strict"            label="Strict (abort on any error)" onChange={m => setTabState(tab, { mode: m })} />
                      </div>
                    </div>
                  )}

                  {s.error && (
                    <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">{s.error}</p>
                  )}

                  <div className="flex gap-2">
                    <button onClick={() => resetTab(tab)} className="rounded-lg border border-white/[0.07] px-4 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                      ← Back
                    </button>
                    <button onClick={close} className="rounded-lg border border-white/[0.07] px-4 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                      Cancel
                    </button>
                    {s.result.valid_rows > 0 && (
                      <button
                        onClick={() => handleImport(tab)}
                        disabled={s.step === "importing"}
                        className="flex-1 rounded-lg bg-emerald-600 py-2 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        {s.step === "importing"
                          ? "Importing…"
                          : `Import ${s.result.valid_rows} row${s.result.valid_rows !== 1 ? "s" : ""}`}
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Step: done */}
              {s.step === "done" && s.result && (
                <div className="space-y-4">
                  <ImportResultView
                    result={s.result}
                    onDownloadErrors={s.result.failed_rows > 0 ? () => downloadErrors(tab) : undefined}
                  />

                  <div className="flex gap-2">
                    <button
                      onClick={() => resetTab(tab)}
                      className="rounded-lg border border-white/[0.07] px-4 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      Import Another
                    </button>
                    {/* Advance to next tab if not on last */}
                    {tab !== "steps" && (
                      <button
                        onClick={() => setTab(tab === "headers" ? "items" : "steps")}
                        className="flex-1 rounded-lg bg-indigo-600 py-2 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
                      >
                        Next: {tab === "headers" ? "BOM Items →" : "Process Steps →"}
                      </button>
                    )}
                    {tab === "steps" && (
                      <button
                        onClick={close}
                        className="flex-1 rounded-lg bg-indigo-600 py-2 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
                      >
                        Done
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Footer: import-order reminder */}
            <div className="px-6 py-3 border-t border-white/[0.06] shrink-0">
              <p className="text-[10px] text-slate-600">
                Import order: <span className="text-slate-500">1 Recipe Headers</span>
                {" → "}
                <span className="text-slate-500">2 BOM Items</span>
                {" → "}
                <span className="text-slate-500">3 Process Steps</span>
                {" · "}
                BOM items and process steps can only be added to <span className="text-slate-500">DRAFT</span> recipes.
                Existing line_no / step_no entries are updated in-place.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ModeBtn({
  current, value, label, onChange,
}: {
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
