"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { loginVerify, useRecoveryCode, TwoFAMethod } from "@/lib/twoFactor";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export default function TwoFAPage() {
  const router = useRouter();
  const { completeTwoFA } = useAuth();
  const [code, setCode] = useState("");
  const [sessionToken, setSessionToken] = useState("");
  const [method, setMethod] = useState<TwoFAMethod>("totp");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showRecovery, setShowRecovery] = useState(false);

  useEffect(() => {
    const token = sessionStorage.getItem("2fa_session_token");
    const m = sessionStorage.getItem("2fa_method") as TwoFAMethod;
    if (!token) { router.replace("/login"); return; }
    setSessionToken(token);
    if (m) setMethod(m);
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const fn = showRecovery ? useRecoveryCode : loginVerify;
      const res = await fn(sessionToken, code);
      await completeTwoFA(res.access_token);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail || "Verification failed. Check your code.");
    } finally {
      setLoading(false);
    }
  };

  const methodLabel: Record<TwoFAMethod, string> = {
    totp: "your authenticator app",
    sms: "your phone via SMS",
    email: "your email",
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white font-bold text-lg mb-3">
            2FA
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Verify your identity</h1>
          <p className="text-sm text-gray-500 mt-1">
            {showRecovery
              ? "Enter a recovery code"
              : `Enter the 6-digit code from ${methodLabel[method]}`}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <Input
              id="code"
              label={showRecovery ? "Recovery Code" : "Verification Code"}
              type="text"
              placeholder={showRecovery ? "XXXX-XXXX" : "000000"}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
              autoComplete="one-time-code"
              autoFocus
              maxLength={showRecovery ? 9 : 6}
            />

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <Button type="submit" loading={loading} className="w-full">
              {showRecovery ? "Use Recovery Code" : "Verify"}
            </Button>

            <button
              type="button"
              onClick={() => { setShowRecovery(!showRecovery); setCode(""); setError(""); }}
              className="w-full text-center text-sm text-indigo-600 hover:text-indigo-800"
            >
              {showRecovery ? "Use authenticator code instead" : "Use recovery code"}
            </button>

            <button
              type="button"
              onClick={() => router.push("/login")}
              className="w-full text-center text-sm text-gray-500 hover:text-gray-700"
            >
              Back to login
            </button>
          </form>
        </div>

        {!showRecovery && method === "totp" && (
          <p className="mt-4 text-center text-xs text-gray-400">
            Open Google Authenticator, Authy, or similar app to get your code.
          </p>
        )}
      </div>
    </div>
  );
}
