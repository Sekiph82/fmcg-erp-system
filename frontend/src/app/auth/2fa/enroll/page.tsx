"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  setupRequired2FA,
  TwoFAEnableResponse,
  TwoFASetupResponse,
  verifyRequired2FASetup,
} from "@/lib/twoFactor";

export default function RequiredTwoFAEnrollmentPage() {
  const router = useRouter();
  const { completeTwoFA } = useAuth();
  const [sessionToken, setSessionToken] = useState("");
  const [setup, setSetup] = useState<TwoFASetupResponse | null>(null);
  const [result, setResult] = useState<TwoFAEnableResponse | null>(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = sessionStorage.getItem("2fa_required_setup_token");
    if (!token) {
      router.replace("/login");
      return;
    }
    setSessionToken(token);
    setLoading(true);
    setupRequired2FA(token)
      .then(setSetup)
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "2FA setup could not be started.";
        setError(message);
      })
      .finally(() => setLoading(false));
  }, [router]);

  const verify = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setResult(await verifyRequired2FASetup(sessionToken, code.trim()));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "The authenticator code was not accepted.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const continueToERP = async () => {
    sessionStorage.removeItem("2fa_required_setup_token");
    await completeTwoFA();
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-xl items-center px-4 py-10">
      <section className="w-full rounded-xl border bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold">Set up required two-factor authentication</h1>
        <p className="mt-2 text-sm text-gray-600">
          This account has administrator or finance access. Set up an authenticator app before entering the ERP.
        </p>

        {loading && <p className="mt-5 text-sm" role="status">Loading secure setup…</p>}
        {error && <p className="mt-5 rounded bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}

        {!result && setup && (
          <>
            {setup.qr_code_image && (
              <div className="mt-5 flex justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element -- This is a local QR image generated for TOTP enrollment. */}
                <img src={`data:image/png;base64,${setup.qr_code_image}`} alt="Authenticator app setup QR code" className="h-48 w-48" />
              </div>
            )}
            {setup.secret_key && (
              <p className="mt-4 break-all rounded bg-gray-50 p-3 text-sm">
                Manual setup key: <strong>{setup.secret_key}</strong>
              </p>
            )}
            <form onSubmit={verify} className="mt-5 space-y-3">
              <label htmlFor="totp-code" className="block text-sm font-medium">Authenticator code</label>
              <input
                id="totp-code"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                className="w-full rounded border px-3 py-2"
              />
              <button type="submit" disabled={loading || code.trim().length !== 6} className="w-full rounded bg-blue-700 px-4 py-2 font-medium text-white disabled:opacity-50">
                Verify and continue
              </button>
            </form>
          </>
        )}

        {result && (
          <div className="mt-5 space-y-4">
            <p className="font-medium text-green-800">Two-factor authentication is enabled.</p>
            <p className="text-sm text-gray-700">Save these recovery codes somewhere secure. Each code can be used once.</p>
            <ul className="grid grid-cols-2 gap-2 rounded bg-gray-50 p-4 font-mono text-sm">
              {result.recovery_codes.map((recoveryCode) => <li key={recoveryCode}>{recoveryCode}</li>)}
            </ul>
            <button type="button" onClick={continueToERP} className="w-full rounded bg-blue-700 px-4 py-2 font-medium text-white">
              Continue to the ERP
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
