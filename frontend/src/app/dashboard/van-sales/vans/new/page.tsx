"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { vanSalesApi } from "@/lib/van_sales";
import { useRouter } from "next/navigation";

export default function NewVanPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [form, setForm] = useState({ van_code: "", plate_number: "", capacity_kg: "", notes: "" });
  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: (data: any) => vanSalesApi.createVan(data),
    onSuccess: (v) => { qc.invalidateQueries({ queryKey: ["vans"] }); router.push(`/dashboard/van-sales/vans/${v.id}`); },
    onError: (e: any) => setError(e?.message ?? "Failed"),
  });

  const upd = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="p-6 max-w-lg mx-auto space-y-6 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">New Van</h1>
        <p className="text-slate-500 text-sm mt-0.5">Register a delivery van</p>
      </div>
      <form onSubmit={(e) => { e.preventDefault(); setError(""); mut.mutate({ van_code: form.van_code, plate_number: form.plate_number || undefined, capacity_kg: form.capacity_kg || undefined, notes: form.notes || undefined }); }}
        className="glow-card p-5 space-y-4">
        {[
          { key: "van_code", label: "Van Code *", placeholder: "VAN-001", required: true },
          { key: "plate_number", label: "Plate Number", placeholder: "KBX 123A" },
          { key: "capacity_kg", label: "Capacity (kg)", placeholder: "1500" },
        ].map(({ key, label, placeholder, required }) => (
          <div key={key}>
            <label className="text-xs text-slate-400 mb-1 block">{label}</label>
            <input value={(form as any)[key]} onChange={(e) => upd(key, e.target.value)} required={required}
              placeholder={placeholder}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
          </div>
        ))}
        <div>
          <label className="text-xs text-slate-400 mb-1 block">Notes</label>
          <textarea value={form.notes} onChange={(e) => upd("notes", e.target.value)} rows={3}
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 resize-none" />
        </div>
        {error && <div className="text-sm text-red-400">{error}</div>}
        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={() => router.back()} className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm">Cancel</button>
          <button type="submit" disabled={mut.isPending} className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50">
            {mut.isPending ? "Creating…" : "Create Van"}
          </button>
        </div>
      </form>
    </div>
  );
}
