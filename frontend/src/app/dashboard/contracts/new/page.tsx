"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { contractsApi } from "@/lib/contracts";
import { useRouter } from "next/navigation";

const CONTRACT_TYPES = ["CUSTOMER_SALES","DISTRIBUTOR","SUPPLIER","REBATE","VOLUME_INCENTIVE","LISTING_DISPLAY","SERVICE_FEE","FRAMEWORK"];
const PARTY_TYPES = ["CUSTOMER","DISTRIBUTOR","SUPPLIER"];

export default function NewContractPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    contract_code: "", contract_name: "", contract_type: "CUSTOMER_SALES",
    party_type: "CUSTOMER", party_id: "", start_date: "", end_date: "",
    currency: "KES", auto_renew: false, renewal_notice_days: "30", notes: "",
  });
  const [error, setError] = useState("");
  const upd = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const mut = useMutation({
    mutationFn: (data: any) => contractsApi.create(data),
    onSuccess: (c) => { qc.invalidateQueries({ queryKey: ["contracts"] }); router.push(`/dashboard/contracts/list/${c.id}`); },
    onError: (e: any) => setError(e?.message ?? "Failed"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault(); setError("");
    mut.mutate({
      contract_code: form.contract_code,
      contract_name: form.contract_name,
      contract_type: form.contract_type,
      party_type: form.party_type,
      party_id: form.party_id,
      start_date: form.start_date,
      end_date: form.end_date || undefined,
      currency: form.currency,
      auto_renew: form.auto_renew,
      renewal_notice_days: parseInt(form.renewal_notice_days) || 30,
      notes: form.notes || undefined,
      terms: [], rebates: [],
    });
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6 min-h-screen bg-[#060d18] text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">New Contract</h1>
        <p className="text-slate-500 text-sm mt-0.5">Create a commercial agreement</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Contract Info</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Contract Code *</label>
              <input value={form.contract_code} onChange={(e) => upd("contract_code", e.target.value)} required
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" placeholder="CT-2026-001" />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Currency</label>
              <input value={form.currency} onChange={(e) => upd("currency", e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" placeholder="KES" maxLength={3} />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Contract Name *</label>
            <input value={form.contract_name} onChange={(e) => upd("contract_name", e.target.value)} required
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" placeholder="Annual supply agreement — Nairobi Distributor" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Contract Type *</label>
              <select value={form.contract_type} onChange={(e) => upd("contract_type", e.target.value)}
                className="w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
                {CONTRACT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Party Type *</label>
              <select value={form.party_type} onChange={(e) => upd("party_type", e.target.value)}
                className="w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
                {PARTY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Party ID *</label>
            <input value={form.party_id} onChange={(e) => upd("party_id", e.target.value)} required
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono" placeholder="UUID of customer/distributor/supplier" />
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Duration & Renewal</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Start Date *</label>
              <input type="date" value={form.start_date} onChange={(e) => upd("start_date", e.target.value)} required
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">End Date (optional)</label>
              <input type="date" value={form.end_date} onChange={(e) => upd("end_date", e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <input type="checkbox" id="auto_renew" checked={form.auto_renew} onChange={(e) => upd("auto_renew", e.target.checked)}
              className="w-4 h-4 rounded border-white/20 bg-white/[0.04]" />
            <label htmlFor="auto_renew" className="text-sm text-slate-300">Auto-renew on expiry</label>
            <span className="text-slate-600 text-xs">|</span>
            <label className="text-xs text-slate-400">Notice days:</label>
            <input type="number" value={form.renewal_notice_days} onChange={(e) => upd("renewal_notice_days", e.target.value)}
              className="w-20 bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1 text-xs text-white focus:outline-none" min={1} />
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
          <label className="text-xs text-slate-400 mb-1 block">Notes</label>
          <textarea value={form.notes} onChange={(e) => upd("notes", e.target.value)} rows={3}
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 resize-none" />
        </div>

        {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={() => router.back()} className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm">Cancel</button>
          <button type="submit" disabled={mut.isPending} className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
            {mut.isPending ? "Creating…" : "Create Contract"}
          </button>
        </div>
      </form>
    </div>
  );
}
