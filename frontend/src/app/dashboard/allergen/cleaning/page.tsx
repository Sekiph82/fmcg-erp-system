"use client";
import { useEffect, useState } from "react";

interface CVLog { id: string; validation_ref: string; line_name: string | null; previous_product: string | null; previous_allergens: string[] | null; next_product: string | null; cleaning_method: string | null; cleaned_by: string | null; validated_by: string | null; swab_test_result: string | null; result: string; created_at: string; }

const RESULT_COLOR: Record<string, string> = {
  PASS: "bg-green-100 text-green-700", FAIL: "bg-red-100 text-red-700",
  CONDITIONAL: "bg-amber-100 text-amber-600", PENDING: "bg-blue-100 text-blue-600",
};

interface LogForm { line_id: string; line_name: string; previous_product: string; previous_allergens: string; next_product: string; cleaning_method: string; cleaning_agent: string; cleaned_by: string; validated_by: string; swab_test_result: string; swab_threshold: string; result: string; notes: string; }
const EMPTY: LogForm = { line_id: "", line_name: "", previous_product: "", previous_allergens: "", next_product: "", cleaning_method: "", cleaning_agent: "", cleaned_by: "", validated_by: "", swab_test_result: "", swab_threshold: "", result: "PENDING", notes: "" };

export default function CleaningValidationPage() {
  const [logs, setLogs] = useState<CVLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<LogForm>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    fetch("/api/v1/allergen/cleaning-validations?limit=50")
      .then(r => r.json()).then(setLogs).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const save = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/allergen/cleaning-validations", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          line_id: form.line_id || undefined, line_name: form.line_name || undefined,
          previous_product: form.previous_product || undefined,
          previous_allergens: form.previous_allergens ? form.previous_allergens.split(",").map(s => s.trim()).filter(Boolean) : undefined,
          next_product: form.next_product || undefined,
          cleaning_method: form.cleaning_method || undefined, cleaning_agent: form.cleaning_agent || undefined,
          cleaned_by: form.cleaned_by || undefined, validated_by: form.validated_by || undefined,
          swab_test_result: form.swab_test_result || undefined, swab_threshold: form.swab_threshold || undefined,
          result: form.result, notes: form.notes || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setShowForm(false); setForm(EMPTY); load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const passCount = logs.filter(l => l.result === "PASS").length;
  const failCount = logs.filter(l => l.result === "FAIL").length;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cleaning Validation Logs</h1>
          <p className="text-sm text-gray-500 mt-0.5">Verify allergen removal between production runs on shared equipment</p>
        </div>
        <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded">+ Log Validation</button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      <div className="grid grid-cols-3 gap-4">
        {[{ label: "Total Logs", value: logs.length, c: "text-gray-800" }, { label: "Pass", value: passCount, c: "text-green-600" }, { label: "Fail", value: failCount, c: "text-red-600" }].map(k => (
          <div key={k.label} className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.c}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3 max-w-2xl">
          <h2 className="text-sm font-semibold text-gray-700">Log Cleaning Validation</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {([["Line Name","line_name","e.g. Filling Line A"],["Previous Product","previous_product","e.g. Peanut Butter"],["Previous Allergens","previous_allergens","comma-sep: peanut, tree nuts"],["Next Product","next_product","e.g. Mango Juice"],["Cleaning Method","cleaning_method","CIP | dry | wet | swab"],["Cleaning Agent","cleaning_agent","e.g. Caustic NaOH 2%"],["Cleaned By","cleaned_by","e.g. John Mwangi"],["Validated By","validated_by","e.g. QA Supervisor"],["Swab Result","swab_test_result","e.g. <10 RLU"],["Swab Threshold","swab_threshold","e.g. <50 RLU"],["Notes","notes","Optional"]] as const).map(([label,key,ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph} value={(form as unknown as Record<string,string>)[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Result *</label>
              <select value={form.result} onChange={(e) => setForm((p) => ({ ...p, result: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {["PASS","FAIL","CONDITIONAL","PENDING"].map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={saving} className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Saving…" : "Log Validation"}</button>
            <button onClick={() => setShowForm(false)} className="border border-gray-300 text-sm px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">Validation Records ({logs.length})</h2></div>
        {loading ? <div className="p-6 text-sm text-gray-400 text-center">Loading…</div> : logs.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No records.</div> : (
          <div className="divide-y">
            {logs.map((lg) => (
              <div key={lg.id} className={`px-4 py-3 ${lg.result === "FAIL" ? "bg-red-50" : ""}`}>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="font-mono text-xs text-blue-600">{lg.validation_ref}</span>
                  <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${RESULT_COLOR[lg.result] ?? "bg-gray-100"}`}>{lg.result}</span>
                  {lg.line_name && <span className="text-xs text-gray-500">{lg.line_name}</span>}
                </div>
                <div className="text-xs text-gray-500 mt-1 flex gap-3 flex-wrap">
                  {lg.previous_product && <span>From: <strong>{lg.previous_product}</strong></span>}
                  {lg.next_product && <span>→ To: <strong>{lg.next_product}</strong></span>}
                  {lg.previous_allergens && lg.previous_allergens.length > 0 && <span className="text-red-600">Allergens: {lg.previous_allergens.join(", ")}</span>}
                </div>
                <div className="text-xs text-gray-400 mt-0.5 flex gap-3">
                  {lg.cleaned_by && <span>Cleaned: {lg.cleaned_by}</span>}
                  {lg.validated_by && <span>Validated: {lg.validated_by}</span>}
                  {lg.swab_test_result && <span>Swab: {lg.swab_test_result}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">Cross-Contamination Prevention</p>
        <p className="text-xs">Log cleaning validations every time a production line switches from an allergen-containing product to a non-allergen product. Swab tests (ATP or allergen-specific ELISA) verify cleaning effectiveness before next production run.</p>
      </div>
    </div>
  );
}
