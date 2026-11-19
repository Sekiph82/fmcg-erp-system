"use client";
// Partner sign-in form shared by the distributor (/portal) and supplier (/supplier) portals.
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { partnerFetch } from "@/lib/portalSelf";

export interface PartnerAuthProps { base: "portal-self" | "supplier-self"; home: string; title: string; subtitle: string; helper: string; signupHref?: string }

export function PartnerLogin({ base, home, title, subtitle, helper, signupHref }: PartnerAuthProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await partnerFetch(base, "/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      router.replace(home);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <form onSubmit={submit} aria-label="Partner sign in" className="w-full max-w-sm bg-white rounded-2xl shadow p-6 space-y-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{title}</h1>
          <p className="text-sm text-gray-500">{subtitle}</p>
        </div>
        {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
        <label className="block text-sm">E-mail
          <input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full border rounded-lg px-3 py-2" />
        </label>
        <label className="block text-sm">Password
          <input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full border rounded-lg px-3 py-2" />
        </label>
        <button disabled={busy} className="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium disabled:opacity-50">
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-xs text-gray-500">{helper}</p>
        {signupHref && <p className="text-sm"><Link href={signupHref} className="font-medium text-indigo-700 underline">New shop? Request an account</Link></p>}
        <p className="text-xs text-gray-400"><Link href="/login" className="underline">Staff sign-in</Link></p>
      </form>
    </main>
  );
}
