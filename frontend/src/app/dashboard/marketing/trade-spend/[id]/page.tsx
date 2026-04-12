"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  marketingApi, TradeSpend, TradeSpendType, ApprovalStatus,
  APPROVAL_STATUS_COLORS,
} from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const SPEND_TYPES: TradeSpendType[] = [
  "DISCOUNT_SUPPORT", "DISPLAY_FEE", "SHELF_PLACEMENT",
  "ACTIVATION_SUPPORT", "REBATE", "DISTRIBUTOR_SUPPORT", "MERCHANDISING",
];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p className="text-sm text-white">{value ?? <span className="text-slate-600">—</span>}</p>
    </div>
  );
}

export default function TradeSpendDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<TradeSpend>>({});
  const [error, setError] = useState("");

  const { data: ts, isLoading } = useQuery({
    queryKey: ["trade-spend", id],
    queryFn: () => marketingApi.tradeSpend.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const updateMut = useMutation({
    mutationFn: () => marketingApi.tradeSpend.update(id, form as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trade-spend", id] });
      qc.invalidateQueries({ queryKey: ["trade-spend"] });
      setEditing(false);
      setForm({});
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const approveMut = useMutation({
    mutationFn: () => marketingApi.tradeSpend.approve(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trade-spend", id] });
      qc.invalidateQueries({ queryKey: ["trade-spend"] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.tradeSpend.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/trade-spend"),
  });

  const startEdit = () => {
    if (!ts) return;
    setForm({
      spend_type: ts.spend_type,
      amount: ts.amount,
      currency: ts.currency,
      spend_date: ts.spend_date,
      campaign_id: ts.campaign_id ?? undefined,
      customer_id: ts.customer_id ?? undefined,
      distributor_id: ts.distributor_id ?? undefined,
      notes: ts.notes ?? undefined,
    });
    setEditing(true);
  };

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  if (isLoading) return <div className="p-8 text-slate-400">Loading...</div>;
  if (!ts) return <div className="p-8 text-red-400">Trade spend record not found.</div>;

  return (
    <RequirePermission permission="trade_spend.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-3xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Trade Spend
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">{ts.spend_type.replace(/_/g, " ")}</h1>
              <p className="text-slate-400 text-sm mt-1">{ts.spend_date}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${APPROVAL_STATUS_COLORS[ts.approval_status as ApprovalStatus]}`}>
                {ts.approval_status}
              </span>
              {ts.approval_status === "PENDING" && (
                <RequirePermission permission="trade_spend.edit">
                  <button onClick={() => approveMut.mutate()}
                    disabled={approveMut.isPending}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-400 text-sm font-medium">
                    {approveMut.isPending ? "Approving..." : "Approve"}
                  </button>
                </RequirePermission>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        {!editing ? (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
            <div className="grid grid-cols-2 gap-x-8 gap-y-5 mb-6">
              <Field label="Amount" value={`${ts.currency} ${Number(ts.amount).toLocaleString()}`} />
              <Field label="Spend Date" value={ts.spend_date} />
              <Field label="Spend Type" value={ts.spend_type.replace(/_/g, " ")} />
              <Field label="Currency" value={ts.currency} />
              <Field label="Campaign ID" value={ts.campaign_id} />
              <Field label="Customer ID" value={ts.customer_id} />
              <Field label="Distributor ID" value={ts.distributor_id} />
              <Field label="Approved By" value={ts.approved_by_id} />
            </div>
            {ts.notes && (
              <div className="border-t border-slate-700/50 pt-4">
                <p className="text-xs text-slate-400 mb-1">Notes</p>
                <p className="text-sm text-slate-300">{ts.notes}</p>
              </div>
            )}
            <div className="border-t border-slate-700/50 pt-4 mt-4 flex justify-between items-center">
              <p className="text-xs text-slate-600">Created: {ts.created_at ? new Date(ts.created_at).toLocaleString() : "—"}</p>
              <div className="flex gap-2">
                <RequirePermission permission="trade_spend.edit">
                  <button onClick={startEdit}
                    className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 text-sm">
                    Edit
                  </button>
                  <button
                    onClick={() => { if (confirm("Delete this trade spend record?")) deleteMut.mutate(); }}
                    disabled={deleteMut.isPending}
                    className="px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 text-sm">
                    Delete
                  </button>
                </RequirePermission>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Spend Type</label>
                <select value={form.spend_type} onChange={(e) => set("spend_type", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {SPEND_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Currency</label>
                <select value={form.currency} onChange={(e) => set("currency", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {["KES", "USD", "EUR", "GBP", "TRY"].map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Amount</label>
                <input type="number" step="0.01" value={form.amount ?? ""}
                  onChange={(e) => set("amount", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Spend Date</label>
                <input type="date" value={form.spend_date ?? ""}
                  onChange={(e) => set("spend_date", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Campaign ID</label>
              <input type="text" value={form.campaign_id ?? ""}
                onChange={(e) => set("campaign_id", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Notes</label>
              <textarea value={form.notes ?? ""} onChange={(e) => set("notes", e.target.value)}
                rows={3}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
            </div>

            <div className="flex justify-end gap-3">
              <button onClick={() => { setEditing(false); setForm({}); setError(""); }}
                className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">
                Cancel
              </button>
              <button onClick={() => updateMut.mutate()} disabled={updateMut.isPending}
                className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium">
                {updateMut.isPending ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
