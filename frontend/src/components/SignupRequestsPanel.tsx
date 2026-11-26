"use client";
// Staff review of shops that asked for an ordering account from the app: approve → customer + account + set-password link.
import { useCallback, useEffect, useState } from "react";
import { portalApi, type SignupRequest } from "@/lib/portal";
import { tx } from "@/lib/i18n/core";

export function SignupRequestsPanel() {
  const [rows, setRows] = useState<SignupRequest[]>([]);
  const [done, setDone] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { portalApi.signupRequests().then(setRows).catch((e) => setError(String(e?.message ?? e))); }, []);
  useEffect(() => { load(); }, [load]);

  async function approve(r: SignupRequest) {
    setError(null);
    try {
      const out = await portalApi.approveSignup(r.id);
      setDone((d) => ({ ...d, [r.id]: `Customer ${out.customer_code} created. Send this link to ${out.email}: ${out.activation_link}` }));
    } catch (e) { setError((e as { message?: string })?.message ?? tx("Approval failed")); }
  }

  if (!rows.length && !error) return null;
  return (
    <section aria-label={tx("Shop sign-up requests")} className="bg-white rounded-xl border p-4 space-y-3">
      <h2 className="font-semibold text-gray-900">{tx("Shop sign-up requests (")}{rows.length})</h2>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <ul className="divide-y">
        {rows.map((r) => (
          <li key={r.id} className="py-2 flex flex-wrap items-start justify-between gap-2">
            <span className="min-w-0">
              <span className="block font-medium">{r.shop_name}</span>
              <span className="block text-xs text-gray-500">{r.contact_name} · {r.phone} · {r.email}</span>
              <span className="block text-xs text-gray-500">{r.address}{r.lat && r.lng ? tx(" · GPS {lat}, {lng}", { lat: r.lat, lng: r.lng }) : tx(" · no GPS")}</span>
              {done[r.id] && <span role="status" className="block text-xs text-emerald-700 break-all">{done[r.id]}</span>}
            </span>
            {!done[r.id] && <button onClick={() => approve(r)} className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-sm">{tx("Approve")}</button>}
          </li>))}
      </ul>
      <p className="text-xs text-gray-500">{tx("Approving creates a retail customer on cash on delivery; finance can grant credit terms later.")}</p>
    </section>
  );
}
