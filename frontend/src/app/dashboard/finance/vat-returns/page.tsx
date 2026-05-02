"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

type VATReturnStatus = "DRAFT" | "SUBMITTED" | "ACKNOWLEDGED";

interface VATReturn {
  id: string;
  period_ym: string;
  status: VATReturnStatus;
  standard_rated_sales: number;
  zero_rated_sales: number;
  exempt_sales: number;
  output_vat: number;
  standard_rated_purchases: number;
  input_vat: number;
  net_vat_payable: number;
  filed_at?: string;
  acknowledgement_ref?: string;
  notes?: string;
  created_at: string;
}

const STATUS_PILL: Record<VATReturnStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  SUBMITTED: "bg-blue-100 text-blue-700",
  ACKNOWLEDGED: "bg-green-100 text-green-700",
};

const vatApi = {
  async list(): Promise<VATReturn[]> {
    const res = await apiClient.get<VATReturn[]>("/api/v1/tax/vat-returns");
    return res.data;
  },
  async generate(period_ym: string): Promise<VATReturn> {
    const res = await apiClient.post<VATReturn>("/api/v1/tax/vat-returns/generate", { period_ym });
    return res.data;
  },
  async file(id: string): Promise<VATReturn> {
    const res = await apiClient.post<VATReturn>(`/api/v1/tax/vat-returns/${id}/file`);
    return res.data;
  },
};

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function VATReturnsPage() {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 7);
  const [genPeriod, setGenPeriod] = useState(today);

  const { data: returns, isLoading } = useQuery<VATReturn[]>({
    queryKey: ["vat-returns"],
    queryFn: vatApi.list,
    staleTime: 30_000,
  });

  const genMut = useMutation({
    mutationFn: (period: string) => vatApi.generate(period),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vat-returns"] }),
  });

  const fileMut = useMutation({
    mutationFn: (id: string) => vatApi.file(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vat-returns"] }),
  });

  const [selected, setSelected] = useState<VATReturn | null>(null);

  return (
    <div className="max-w-6xl mx-auto space-y-5 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">VAT Returns (VAT3)</h1>
        <p className="text-sm text-gray-400 mt-0.5">Monthly KRA VAT3 return auto-generated from invoices</p>
      </div>

      {/* Generate */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Generate VAT Return</h2>
        <div className="flex gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Period (YYYY-MM)</label>
            <input type="month" value={genPeriod} onChange={(e) => setGenPeriod(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
          </div>
          <button
            onClick={() => genMut.mutate(genPeriod)}
            disabled={genMut.isPending}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {genMut.isPending ? "Generating…" : "Generate / Update"}
          </button>
        </div>
        {genMut.isError && <p className="text-sm text-red-500 mt-2">Failed to generate return.</p>}
        {genMut.data && (
          <div className="mt-3 bg-blue-50 border border-blue-100 rounded-lg p-3 text-sm text-blue-800">
            Generated for {genMut.data.period_ym}: Output VAT KES {fmt(genMut.data.output_vat)} —
            Input VAT KES {fmt(genMut.data.input_vat)} —
            Net Payable KES {fmt(genMut.data.net_vat_payable)}
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Returns list */}
        <div className="md:col-span-2 bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Period</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Output VAT</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Input VAT</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Net Payable</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && <tr><td colSpan={6} className="text-center py-8 text-gray-400">Loading…</td></tr>}
              {!isLoading && (returns ?? []).length === 0 && (
                <tr><td colSpan={6} className="text-center py-8 text-gray-400">No VAT returns yet.</td></tr>
              )}
              {(returns ?? []).map((r) => (
                <tr key={r.id} className={`hover:bg-gray-50 cursor-pointer ${selected?.id === r.id ? "bg-indigo-50" : ""}`}
                  onClick={() => setSelected(r)}>
                  <td className="px-4 py-2.5 font-mono font-semibold text-gray-800">{r.period_ym}</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${STATUS_PILL[r.status]}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right text-gray-700">{fmt(r.output_vat)}</td>
                  <td className="px-4 py-2.5 text-right text-gray-700">{fmt(r.input_vat)}</td>
                  <td className={`px-4 py-2.5 text-right font-semibold ${r.net_vat_payable > 0 ? "text-red-700" : "text-green-700"}`}>
                    {fmt(r.net_vat_payable)}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {r.status === "DRAFT" && (
                      <button
                        onClick={(e) => { e.stopPropagation(); fileMut.mutate(r.id); }}
                        disabled={fileMut.isPending}
                        className="text-xs bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full hover:bg-indigo-200 disabled:opacity-50"
                      >
                        File
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Detail panel */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 mb-4">
            {selected ? `Detail: ${selected.period_ym}` : "Select a period"}
          </h2>
          {selected ? (
            <div className="space-y-3 text-sm">
              <div className="border-b border-gray-100 pb-2">
                <p className="text-xs text-gray-400 uppercase mb-1">Sales</p>
                <div className="flex justify-between"><span>Standard-Rated</span><span>{fmt(selected.standard_rated_sales)}</span></div>
                <div className="flex justify-between"><span>Zero-Rated</span><span>{fmt(selected.zero_rated_sales)}</span></div>
                <div className="flex justify-between"><span>Exempt</span><span>{fmt(selected.exempt_sales)}</span></div>
                <div className="flex justify-between font-semibold mt-1"><span>Output VAT (16%)</span><span className="text-red-700">{fmt(selected.output_vat)}</span></div>
              </div>
              <div className="border-b border-gray-100 pb-2">
                <p className="text-xs text-gray-400 uppercase mb-1">Purchases</p>
                <div className="flex justify-between"><span>Standard-Rated</span><span>{fmt(selected.standard_rated_purchases)}</span></div>
                <div className="flex justify-between font-semibold mt-1"><span>Input VAT</span><span className="text-green-700">{fmt(selected.input_vat)}</span></div>
              </div>
              <div className="pt-1">
                <div className="flex justify-between font-bold text-base">
                  <span>Net VAT Payable</span>
                  <span className={selected.net_vat_payable >= 0 ? "text-red-700" : "text-green-700"}>
                    {fmt(selected.net_vat_payable)}
                  </span>
                </div>
              </div>
              {selected.filed_at && (
                <p className="text-xs text-gray-400">Filed: {selected.filed_at.slice(0, 10)}</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">Click a row to see details</p>
          )}
        </div>
      </div>
    </div>
  );
}
