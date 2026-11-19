"use client";
// One-time set-password link (invitation or forgotten password), shared by the distributor and supplier portals.
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { partnerFetch } from "@/lib/portalSelf";

function Activate({ base, loginPath }: { base: "portal-self" | "supplier-self"; loginPath: string }) {
  const token = useSearchParams().get("token") ?? "";
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (pw !== pw2) { setMsg({ ok: false, text: "The passwords do not match." }); return; }
    try {
      const r = await partnerFetch<{ detail: string }>(base, "/auth/activate", { method: "POST", body: JSON.stringify({ token, new_password: pw }) });
      setMsg({ ok: true, text: r.detail });
    } catch (err) { setMsg({ ok: false, text: (err as Error).message }); }
  }

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <form onSubmit={submit} aria-label="Set password" className="w-full max-w-sm bg-white rounded-2xl shadow p-6 space-y-4">
        <h1 className="text-xl font-bold text-gray-900">Set your password</h1>
        {msg && <p role={msg.ok ? "status" : "alert"} className={`rounded-lg p-3 text-sm border ${msg.ok ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-700"}`}>{msg.text}</p>}
        {msg?.ok ? <Link href={loginPath} className="block text-center py-2.5 rounded-lg bg-indigo-600 text-white">Go to sign in</Link> : (<>
          {!token && <p className="text-sm text-red-700">This link has no token. Use the full link you received.</p>}
          <label className="block text-sm">New password (at least 10 characters)
            <input type="password" required minLength={10} autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} className="mt-1 w-full border rounded-lg px-3 py-2" />
          </label>
          <label className="block text-sm">Repeat password
            <input type="password" required minLength={10} autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} className="mt-1 w-full border rounded-lg px-3 py-2" />
          </label>
          <button disabled={!token} className="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium disabled:opacity-50">Set password</button>
        </>)}
      </form>
    </main>
  );
}

export function PartnerActivate(props: { base: "portal-self" | "supplier-self"; loginPath: string }) {
  return <Suspense><Activate {...props} /></Suspense>;
}
