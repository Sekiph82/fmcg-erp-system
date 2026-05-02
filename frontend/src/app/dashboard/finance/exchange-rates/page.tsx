"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { financeApi, ExchangeRate, RateSource } from "@/lib/finance";

const COMMON_CURRENCIES = ["USD", "EUR", "GBP", "CNY", "INR", "AED", "ZAR", "TZS", "UGX", "ETB"];

const SOURCE_LABELS: Record<RateSource, string> = {
  MANUAL: "Manual",
  CBK: "CBK",
  ECB: "ECB",
  API: "API",
};

export default function ExchangeRatesPage() {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);

  const [form, setForm] = useState({
    currency: "USD",
    rate_date: today,
    rate_to_kes: "",
    source: "MANUAL" as RateSource,
    notes: "",
  });

  const [convertForm, setConvertForm] = useState({
    amount: "",
    currency: "USD",
  });

  const { data: latest, isLoading } = useQuery<ExchangeRate[]>({
    queryKey: ["fx-rates-latest"],
    queryFn: financeApi.latestExchangeRates,
    staleTime: 60_000,
  });

  const { data: history } = useQuery<ExchangeRate[]>({
    queryKey: ["fx-rates-history"],
    queryFn: () => financeApi.listExchangeRates({ limit: 100 }),
    staleTime: 30_000,
  });

  const createMut = useMutation({
    mutationFn: (data: object) => financeApi.createExchangeRate(data as Parameters<typeof financeApi.createExchangeRate>[0]),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fx-rates-latest"] });
      qc.invalidateQueries({ queryKey: ["fx-rates-history"] });
      setForm((f) => ({ ...f, rate_to_kes: "", notes: "" }));
    },
  });

  const { data: convertResult, refetch: runConvert } = useQuery({
    queryKey: ["fx-convert", convertForm],
    queryFn: () => financeApi.convertCurrency(
      parseFloat(convertForm.amount) || 0,
      convertForm.currency,
    ),
    enabled: false,
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Exchange Rates</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Manage daily foreign exchange rates vs KES base currency
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Add Rate */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">Add / Update Rate</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Currency</label>
              <select value={form.currency} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
                {COMMON_CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Date</label>
              <input type="date" value={form.rate_date} onChange={(e) => setForm((f) => ({ ...f, rate_date: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Rate to KES *</label>
              <input type="number" value={form.rate_to_kes}
                onChange={(e) => setForm((f) => ({ ...f, rate_to_kes: e.target.value }))}
                placeholder="e.g. 130.50"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Source</label>
              <select value={form.source} onChange={(e) => setForm((f) => ({ ...f, source: e.target.value as RateSource }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
                {(Object.keys(SOURCE_LABELS) as RateSource[]).map((s) => (
                  <option key={s} value={s}>{SOURCE_LABELS[s]}</option>
                ))}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">Notes</label>
              <input value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
          </div>
          {createMut.isError && <p className="text-sm text-red-500">Failed to save rate.</p>}
          <button
            onClick={() => createMut.mutate({ ...form, rate_to_kes: parseFloat(form.rate_to_kes) })}
            disabled={!form.rate_to_kes || createMut.isPending}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {createMut.isPending ? "Saving…" : "Save Rate"}
          </button>
        </div>

        {/* Currency Converter */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">Currency Converter</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Amount</label>
              <input type="number" value={convertForm.amount}
                onChange={(e) => setConvertForm((f) => ({ ...f, amount: e.target.value }))}
                placeholder="100"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">From Currency</label>
              <select value={convertForm.currency}
                onChange={(e) => setConvertForm((f) => ({ ...f, currency: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
                {COMMON_CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <button
            onClick={() => runConvert()}
            disabled={!convertForm.amount}
            className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          >
            Convert to KES
          </button>
          {convertResult && (
            <div className="bg-green-50 rounded-lg p-4 text-sm">
              <p className="font-semibold text-green-800">
                {convertResult.amount.toLocaleString()} {convertResult.from_currency}
                {" = "}
                <span className="text-lg">
                  KES {convertResult.converted_amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </span>
              </p>
              <p className="text-green-600 text-xs mt-1">
                Rate: 1 {convertResult.from_currency} = {convertResult.rate} KES
                (as of {convertResult.rate_date})
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Latest Rates Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-800">Latest Rates</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Currency</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Rate (1 unit → KES)</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Date</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && (
              <tr><td colSpan={4} className="text-center py-8 text-gray-400">Loading…</td></tr>
            )}
            {!isLoading && (latest ?? []).length === 0 && (
              <tr><td colSpan={4} className="text-center py-8 text-gray-400">No exchange rates entered yet.</td></tr>
            )}
            {(latest ?? []).map((r) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono font-bold text-gray-800">{r.currency}</td>
                <td className="px-4 py-2.5 text-right font-semibold text-indigo-700">
                  {r.rate_to_kes.toLocaleString(undefined, { minimumFractionDigits: 4 })}
                </td>
                <td className="px-4 py-2.5 text-gray-600">{r.rate_date}</td>
                <td className="px-4 py-2.5 text-xs text-gray-400">{SOURCE_LABELS[r.source]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Rate History */}
      {history && history.length > (latest?.length ?? 0) && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Rate History (recent 100)</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Currency</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Rate → KES</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Date</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Source</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {history.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-mono font-semibold text-gray-700">{r.currency}</td>
                  <td className="px-4 py-2.5 text-right text-gray-800">
                    {r.rate_to_kes.toLocaleString(undefined, { minimumFractionDigits: 4 })}
                  </td>
                  <td className="px-4 py-2.5 text-gray-600">{r.rate_date}</td>
                  <td className="px-4 py-2.5 text-xs text-gray-400">{SOURCE_LABELS[r.source]}</td>
                  <td className="px-4 py-2.5 text-xs text-gray-400">{r.notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
