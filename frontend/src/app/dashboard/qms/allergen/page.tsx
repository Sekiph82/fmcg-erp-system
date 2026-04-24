"use client";
import { useEffect, useState } from "react";
import { qmsApi, AllergenValidationRecord } from "@/lib/qms";

export default function AllergenValidationPage() {
  const [records, setRecords] = useState<AllergenValidationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>({
    allergens_present: "", cleaning_method: "",
  });

  const load = () => {
    setLoading(true);
    qmsApi.listAllergenValidations().then(setRecords).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    await qmsApi.createAllergenValidation(form);
    setShowNew(false);
    setForm({ allergens_present: "", cleaning_method: "" });
    load();
  };

  const passed = records.filter(r => r.validation_passed === true).length;
  const failed = records.filter(r => r.validation_passed === false).length;
  const pending = records.filter(r => r.validation_passed === null).length;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Allergen Validation</h1>
          <p className="text-sm text-gray-500 mt-0.5">Cleaning validation and allergen clearance between production runs</p>
        </div>
        <button onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
          + Record Validation
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Passed</p>
          <p className="text-2xl font-bold text-green-700">{passed}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Failed</p>
          <p className={`text-2xl font-bold ${failed > 0 ? "text-red-700" : "text-gray-800"}`}>{failed}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Pending</p>
          <p className={`text-2xl font-bold ${pending > 0 ? "text-amber-700" : "text-gray-800"}`}>{pending}</p>
        </div>
      </div>

      {showNew && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">Record Allergen Validation</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Allergens Present</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                placeholder="e.g. Gluten, Peanuts, Milk"
                value={form.allergens_present as string}
                onChange={e => setForm(p => ({ ...p, allergens_present: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Swab Test Result</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                placeholder="Negative / <5 ppm / Positive"
                value={(form.swab_test_result as string) || ""}
                onChange={e => setForm(p => ({ ...p, swab_test_result: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Cleaning Method</label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                value={form.cleaning_method as string}
                onChange={e => setForm(p => ({ ...p, cleaning_method: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Cleaning Completed At</label>
              <input type="datetime-local" className="border rounded-lg px-3 py-2 text-sm w-full"
                value={(form.cleaning_completed_at as string) || ""}
                onChange={e => setForm(p => ({ ...p, cleaning_completed_at: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Validation Result</label>
              <select className="border rounded-lg px-3 py-2 text-sm w-full"
                value={form.validation_passed === undefined ? "" : String(form.validation_passed)}
                onChange={e => setForm(p => ({ ...p, validation_passed: e.target.value === "" ? null : e.target.value === "true" }))}>
                <option value="">Pending</option>
                <option value="true">Passed</option>
                <option value="false">Failed</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Evidence Notes</label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                value={(form.evidence_notes as string) || ""}
                onChange={e => setForm(p => ({ ...p, evidence_notes: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
              Save
            </button>
            <button onClick={() => setShowNew(false)}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <p className="px-5 py-8 text-gray-400 text-sm">Loading…</p>
        ) : records.length === 0 ? (
          <p className="px-5 py-8 text-gray-400 text-sm">No allergen validation records yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Validation #", "Previous Product", "Current Product", "Allergens", "Cleaning Method", "Swab Test", "Result", "Date"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {records.map(r => (
                <tr key={r.id} className={`hover:bg-gray-50 ${r.validation_passed === false ? "bg-red-50" : ""}`}>
                  <td className="px-4 py-3 font-medium text-gray-700">{r.validation_no}</td>
                  <td className="px-4 py-3 text-gray-600">{r.previous_product_name || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{r.current_product_name || "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{r.allergens_present || "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">{r.cleaning_method || "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{r.swab_test_result || "—"}</td>
                  <td className="px-4 py-3">
                    {r.validation_passed === true && <span className="px-2 py-0.5 bg-green-100 text-green-800 rounded text-xs">Passed</span>}
                    {r.validation_passed === false && <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded text-xs">Failed</span>}
                    {r.validation_passed === null && <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs">Pending</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{new Date(r.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
