"use client";
import { useEffect, useState } from "react";
import { portalApi, PortalAccount } from "@/lib/portal";

export default function SellThroughUploadPage() {
  const [accounts, setAccounts] = useState<PortalAccount[]>([]);
  const [form, setForm] = useState({
    account_id: "",
    period_start: "",
    period_end: "",
    total_units_sold: "",
    total_value: "",
    notes: "",
    upload_reference: "",
  });
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    portalApi.getAccounts({ status: "ACTIVE" }).then(setAccounts as (v: unknown) => void);
  }, []);

  const submit = async () => {
    if (!form.account_id || !form.period_start || !form.period_end || !form.total_units_sold) return;
    setSaving(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/portal/sell-through-upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          total_units_sold: Number(form.total_units_sold),
          total_value: form.total_value ? Number(form.total_value) : null,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setResult(await r.json());
      setForm({ account_id: "", period_start: "", period_end: "", total_units_sold: "", total_value: "", notes: "", upload_reference: "" });
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sell-Through Upload</h1>
        <p className="text-sm text-gray-500 mt-0.5">Distributor self-service sell-through data submission</p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-700 font-semibold text-sm">Submitted successfully</p>
          <p className="text-green-600 text-xs mt-1">{(result as Record<string, unknown>).message as string}</p>
          <p className="text-green-500 text-xs">Upload ID: {(result as Record<string, unknown>).upload_id as string}</p>
        </div>
      )}

      <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Submission Form</h2>

        <div>
          <label className="text-xs text-gray-500 block mb-1">Portal Account *</label>
          <select
            value={form.account_id}
            onChange={(e) => setForm((p) => ({ ...p, account_id: e.target.value }))}
            className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">— Select account —</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.primary_contact_name || a.id} ({a.account_type})
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Period Start *</label>
            <input type="date" value={form.period_start}
              onChange={(e) => setForm((p) => ({ ...p, period_start: e.target.value }))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Period End *</label>
            <input type="date" value={form.period_end}
              onChange={(e) => setForm((p) => ({ ...p, period_end: e.target.value }))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Total Units Sold *</label>
            <input type="number" min={0} value={form.total_units_sold}
              onChange={(e) => setForm((p) => ({ ...p, total_units_sold: e.target.value }))}
              placeholder="e.g. 1500"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Total Value (KES)</label>
            <input type="number" min={0} step="0.01" value={form.total_value}
              onChange={(e) => setForm((p) => ({ ...p, total_value: e.target.value }))}
              placeholder="e.g. 250000"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Reference / File Name</label>
            <input type="text" value={form.upload_reference}
              onChange={(e) => setForm((p) => ({ ...p, upload_reference: e.target.value }))}
              placeholder="e.g. sell-thru-apr-2026.xlsx"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Notes</label>
            <input type="text" value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
              placeholder="Optional notes"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
        </div>

        <button
          onClick={submit}
          disabled={saving || !form.account_id || !form.period_start || !form.period_end || !form.total_units_sold}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-5 py-2 rounded disabled:opacity-50"
        >
          {saving ? "Submitting…" : "Submit Sell-Through Data"}
        </button>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">What happens next?</p>
        <p className="text-xs text-blue-700">
          Your submission is received with status PENDING. The sales operations team will review,
          validate, and post the data to the secondary sales tracking system. You will be notified
          upon completion.
        </p>
      </div>
    </div>
  );
}
