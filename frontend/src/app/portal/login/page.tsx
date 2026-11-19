"use client";
// Distributor / customer portal sign-in (separate from the staff login).
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { post } from "@/lib/portalSelf";

export default function PortalLogin() {
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
      await post("/auth/login", { email, password });
      router.replace("/portal");
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <form onSubmit={submit} aria-label="Partner sign in" className="w-full max-w-sm bg-white rounded-2xl shadow p-6 space-y-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Partner portal</h1>
          <p className="text-sm text-gray-500">Distributors and customers: order, track deliveries and see your statement.</p>
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
        <p className="text-xs text-gray-500">Forgot your password or no account yet? Ask your sales representative for a set-password link.</p>
        <p className="text-xs text-gray-400"><Link href="/login" className="underline">Staff sign-in</Link></p>
      </form>
    </main>
  );
}
