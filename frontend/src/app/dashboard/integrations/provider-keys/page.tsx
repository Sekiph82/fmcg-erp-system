"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

interface ProviderField { field: string; label: string; secret: boolean; is_set: boolean; value: string | null }
interface Provider { provider: string; label: string; configured: boolean; fields: ProviderField[] }

const WHAT_FOR: Record<string, string> = {
  mpesa: "Shops pay their orders with M-Pesa (STK push) and payments reconcile automatically.",
  sms: "“Your order is on the way” messages when no WhatsApp sender is set up.",
  whatsapp: "“Your order is on the way” messages to shops on WhatsApp.",
  email: "Invoices e-mailed to shops at delivery and to marketplace buyers on payment; campaigns.",
};

export default function ProviderKeysPage() {
  const { data: providers = [], isError } = useQuery<Provider[]>({
    queryKey: ["provider-credentials"],
    queryFn: async () => (await apiClient.get("/api/v1/integrations/provider-credentials")).data,
  });
  const [open, setOpen] = useState<Provider | null>(null);

  if (isError) return <div className="p-6 text-sm text-red-600">{tx("Only a system administrator can manage provider keys.")}</div>;
  return (
    <div className="p-4 md:p-6 space-y-4 max-w-4xl">
      <div>
        <h2 className="text-lg font-semibold">{tx("Provider keys")}</h2>
        <p className="text-sm text-gray-500">
          {tx("Enter the keys you receive from each provider. They are stored encrypted and take effect within a minute; secrets are never shown again.")}
        </p>
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        {providers.map((p) => (
          <div key={p.provider} className="border rounded-lg p-4 bg-white space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-sm">{p.label}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${p.configured ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-800"}`}>
                {p.configured ? tx("Set up") : tx("Waiting for keys")}
              </span>
            </div>
            <p className="text-xs text-gray-500">{WHAT_FOR[p.provider]}</p>
            <button type="button" onClick={() => setOpen(p)} className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
              {p.configured ? tx("Change keys") : tx("Enter keys")}
            </button>
          </div>
        ))}
      </div>
      {open && <KeysDialog provider={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function KeysDialog({ provider, onClose }: { provider: Provider; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Record<string, string>>(
    Object.fromEntries(provider.fields.map((f) => [f.field, f.secret ? "" : f.value ?? ""])),
  );
  const save = useMutation({
    mutationFn: async () => (await apiClient.put(`/api/v1/integrations/provider-credentials/${provider.provider}`, form)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["provider-credentials"] }); onClose(); },
  });
  const err = (save.error as { response?: { data?: { detail?: unknown } } } | null)?.response?.data?.detail;

  return (
    <div role="dialog" aria-modal="true" aria-label={provider.label} className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <form className="bg-white rounded-xl p-5 w-full max-w-lg space-y-3 max-h-[90vh] overflow-y-auto"
        onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <h3 className="font-semibold">{provider.label}</h3>
        {provider.fields.map((f) => (
          <label key={f.field} className="block text-sm">
            <span className="text-gray-700">{f.label}</span>
            <input
              type={f.secret ? "password" : "text"} autoComplete="off" value={form[f.field] ?? ""}
              placeholder={f.secret && f.is_set ? tx("•••••• (stored — leave blank to keep)") : ""}
              onChange={(e) => setForm((s) => ({ ...s, [f.field]: e.target.value }))}
              className="mt-1 w-full border rounded-lg px-3 py-2"
            />
          </label>
        ))}
        {typeof err === "string" && <p className="text-sm text-red-600">{err}</p>}
        <div className="flex gap-2 pt-1">
          <button type="button" onClick={onClose} className="flex-1 py-2 border rounded-lg text-sm">{tx("Cancel")}</button>
          <button type="submit" disabled={save.isPending} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50">
            {save.isPending ? tx("Saving…") : tx("Save keys")}
          </button>
        </div>
      </form>
    </div>
  );
}
